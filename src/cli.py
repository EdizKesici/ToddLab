"""Pipeline CLI.

Usage:
    python -m src.cli fetch [--strict]   # network -> data/raw (needs outbound internet access)
    python -m src.cli rebuild            # data/raw -> data/dist (NO network access needed)
    python -m src.cli all [--strict]     # fetch then rebuild
    python -m src.cli check-config       # validates config/*.yaml without fetching or building anything

`rebuild` is the command to use to replay the pipeline after fixing a bug in
normalize/merge/validate/build, without re-downloading the sources. `fetch`
is the only command that needs the network.

`fetch`/`all` exit 0 on partial success (at least one source fetched) by
design: a single broken source (e.g. an HTTP 403 on one slug) must not
block the sources that do work. Pass --strict to make ANY source failure a
non-zero exit, e.g. for a CI job that should fail loudly on regressions.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DIST_DIR = ROOT / "data" / "dist"
REPORTS_DIR = ROOT / "reports"

sys.path.insert(0, str(ROOT))

from src.config_loader import ConfigError, load_entities, load_indicators  # noqa: E402
from src.pipeline.build import build_all  # noqa: E402
from src.pipeline.fetch import fetch_all  # noqa: E402
from src.pipeline.merge import merge_all  # noqa: E402
from src.pipeline.normalize import normalize_all  # noqa: E402
from src.pipeline.validate import validate_all  # noqa: E402


def _load_config():
    indicators = load_indicators(CONFIG_DIR)
    entities = load_entities(CONFIG_DIR)
    return indicators, entities


def cmd_check_config(_args) -> int:
    try:
        indicators, entities = _load_config()
    except ConfigError as e:
        print(f"INVALID CONFIG:\n{e}", file=sys.stderr)
        return 1
    print(f"OK: {len(indicators)} indicator(s), {len(entities.entities)} entities.")
    for ind in indicators.values():
        mode = "Todd+Extra" if ind.todd_core else "Extra only"
        print(f"  - {ind.id} [{mode}] ({len(ind.sources)} source(s), reliability={ind.reliability.value})")
    return 0


def cmd_fetch(args) -> int:
    indicators, _ = _load_config()
    outcome = fetch_all(indicators, RAW_DIR)

    print(f"Fetch done: {len(outcome.written)} snapshot(s) written, {len(outcome.failures)} failure(s).")
    for failure in outcome.failures:
        print(f"  FAILED  {failure.indicator_id} / {failure.provider}:{failure.source_ref} -> {failure.error}", file=sys.stderr)

    if not outcome.written and outcome.failures:
        return 1  # total failure: nothing usable came out of this run
    if getattr(args, "strict", False) and outcome.failures:
        return 1  # --strict: any failure at all is a hard stop
    return 0


def cmd_rebuild(_args) -> int:
    indicators, entities = _load_config()

    norm_summary = normalize_all(indicators, RAW_DIR, PROCESSED_DIR, entities)
    for iid, s in norm_summary.items():
        n_gap = sum(len(v.get("possible_mapping_gap", [])) for v in s["unresolved"].values())
        n_special = sum(len(v.get("owid_special", [])) for v in s["unresolved"].values())
        if n_gap:
            logging.warning("%s: %d likely mapping gap(s) in entities.yaml -> see %s.unresolved.json", iid, n_gap, iid)
        if n_special:
            logging.info("%s: %d OWID aggregate/special entity name(s), expected -> see %s.unresolved.json", iid, n_special, iid)

    merge_all(list(indicators.keys()), PROCESSED_DIR)
    validate_results = validate_all(indicators, PROCESSED_DIR, entities, REPORTS_DIR)
    for r in validate_results:
        if r["range_violations"] or r["duplicate_entity_year"]:
            logging.warning("%s: anomalies detected, see reports/coverage_report.md", r["indicator_id"])

    build_all(indicators, PROCESSED_DIR, DIST_DIR, entities)
    print(f"Build done -> {DIST_DIR}")
    print(f"Coverage report -> {REPORTS_DIR / 'coverage_report.md'}")
    return 0


def cmd_all(args) -> int:
    rc = cmd_fetch(args)
    if rc != 0:
        return rc
    return cmd_rebuild(args)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Interface Todd data collection/normalization pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-config").set_defaults(func=cmd_check_config)

    fetch_parser = sub.add_parser("fetch")
    fetch_parser.add_argument("--strict", action="store_true", help="Exit 1 if any source fails, even on partial success.")
    fetch_parser.set_defaults(func=cmd_fetch)

    sub.add_parser("rebuild").set_defaults(func=cmd_rebuild)

    all_parser = sub.add_parser("all")
    all_parser.add_argument("--strict", action="store_true", help="Exit 1 if any source fails, even on partial success.")
    all_parser.set_defaults(func=cmd_all)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
