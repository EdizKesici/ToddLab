#!/usr/bin/env python3
"""freeze_score_bounds: the dist at this instant -> config/score_bounds.yaml.

WHAT THIS SCRIPT IS
The score layer's numbers are FROZEN, never recomputed at build time
(ADR-0011): the absolute scale's bounds (p1/p99 of the transformed sample),
the log floors, and — per (score, component) — WHICH source the §4.4
selection rules retained. This script is the ONLY writer of
config/score_bounds.yaml; `rebuild` only READS it (and fails loudly if the
frozen source drifts from what the rules would pick on the current dist —
the drift is a regeneration decision, never an auto-refresh).

    python scripts/freeze_score_bounds.py            # write the frozen file
    python scripts/freeze_score_bounds.py --dry-run  # print, write nothing

The output is DETERMINISTIC: same dist bytes + same score.yaml bytes ->
same YAML bytes (bounds sorted by score, indicator, sex; floats at full
repr). The meta block anchors the generation:

    bounds_version      a date-based version (bump when regenerating
                        deliberately — the changelog records why)
    generated           the generation date
    score_config_sha256 the sha256 of config/score.yaml at freeze time
    score_config_version

REGENERATION PROTOCOL (the ADR's rule): a fetch that moves a source's
coverage can change what §4.4 would pick; the drift guard in the build
then REFUSES to run until this script is re-run deliberately and the
bounds_version bumped — the scale never moves silently under a score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config_loader import load_score_config  # noqa: E402
from src.schema.score import ScoreName, SexMode  # noqa: E402
from src.score.core import ComponentBounds, compute_bounds, select_source  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(dry_run: bool) -> int:
    config = load_score_config(REPO_ROOT / "config")
    dist_indicators = REPO_ROOT / "data" / "dist" / "indicators"

    bounds_version = f"{date.today().isoformat()}.1"
    payload: dict = {
        "meta": {
            "bounds_version": bounds_version,
            "generated": date.today().isoformat(),
            "score_config_sha256": _sha256(REPO_ROOT / "config" / "score.yaml"),
            "score_config_version": config.version,
            "method": (
                "p1/p99 (percentiles key of config/score.yaml) over all non-null "
                "country-years of the retained source since bounds_from_year "
                f"({config.bounds_from_year}); floor = p1 of the strictly positive "
                "sample for log components; target lo = 0; the source per "
                "(score, component) is the §4.4 selection frozen at generation "
                "time — rebuild reads this file and never recomputes"
            ),
        },
        "bounds": {},
    }

    for score in (ScoreName.official, ScoreName.modelled):
        block: dict = {}
        for comp in sorted(config.components_for(score), key=lambda c: c.indicator):
            ind_dist = json.loads(
                (dist_indicators / f"{comp.indicator}.json").read_text(encoding="utf-8")
            )
            sexes = ("male", "female") if comp.sex_mode == SexMode.split else ("both",)
            for sex in sexes:
                selected = select_source(ind_dist, sex, score, config.bounds_from_year)
                b: ComponentBounds = compute_bounds(list(selected.points), comp.transform, config)
                block[f"{comp.indicator}/{sex}"] = {
                    "source": selected.name,
                    "source_class": selected.source_class,
                    "floor": b.floor,
                    "lo": b.lo,
                    "hi": b.hi,
                    "n_sample": b.n_sample,
                    "n_unavailable": b.n_unavailable,
                    "bounds_version": bounds_version,
                }
        payload["bounds"][score.value] = block

    out_path = REPO_ROOT / "config" / "score_bounds.yaml"
    text = yaml.safe_dump(
        payload,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
    if dry_run:
        print(f"[dry-run] would write {out_path} ({len(text)} bytes):")
        print(text)
        return 0
    out_path.write_text(text, encoding="utf-8")
    n = sum(len(block) for block in payload["bounds"].values())
    print(f"Froze {n} component bounds -> {out_path} (bounds_version {bounds_version})")
    for score in (ScoreName.official, ScoreName.modelled):
        witnesses = [
            k
            for k, v in payload["bounds"][score.value].items()
            if v["source_class"] == "modelled"
        ]
        print(
            f"  {score.value}: {len(payload['bounds'][score.value])} components, "
            f"{len(witnesses)} witness-retained {witnesses if witnesses else ''}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze the score layer's bounds (the only writer of config/score_bounds.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="print the frozen YAML without writing")
    args = parser.parse_args()
    return freeze(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
