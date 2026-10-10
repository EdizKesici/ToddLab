#!/usr/bin/env python3
"""freeze_score_bounds: the dist at this instant -> config/score_bounds.yaml.

WHAT THIS SCRIPT IS
The score layer's numbers are FROZEN, never recomputed at build time
(ADR-0011): the absolute scale's bounds (p1/p99 of the transformed sample),
the log floors, and — per (score, component) — WHICH source the §4.4
selection rules retained, the sample's SIZE (n_sample) and its ENTITY
COUNT (n_entities, v28.2). This script is the ONLY writer of
config/score_bounds.yaml; `rebuild` only READS it (and fails loudly if
the frozen source drifts from what the rules would pick on the current
dist, or if the bounds sample's n_sample / n_entities drifts beyond
config/score.yaml's bounds_drift_tolerance — the drift is a
regeneration decision, never an auto-refresh).

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
The guard trips on TWO conditions (v28.2, decision 18): the frozen
source NAME no longer matching the live §4.4 selection, or the bounds
sample's n_sample / n_entities drifting beyond bounds_drift_tolerance
(a source that keeps its name while its COVERAGE changes — the v28.1
blind spot: the DYB wiring moved the official fertility sample
1278 -> 2523 observations / 47 -> 177 entities under the same
'canonical' name and the guard stayed silent). v28.3: the freezer
REFUSES to freeze an empty sample (n_sample or n_entities of 0) —
every block is written with integer, strictly-positive counts, the
same contract load_score_bounds enforces at load time. The version is a date
plus a sequence: the FIRST regeneration of a
given day takes .1, the second .2, and so on (read from the existing
file — the v28 rule; before v28 the script hardcoded .1, which would
have re-frozen the same version twice on a two-regeneration day).
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
from src.score.core import ComponentBounds, bounds_sample_counts, compute_bounds, select_source  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _next_bounds_version() -> str:
    """date + sequence: today's first freeze is '<date>.1'; a file already
    frozen TODAY bumps its sequence (2026-10-06.1 -> 2026-10-06.2). The
    version must MOVE on every deliberate regeneration."""
    today = date.today().isoformat()
    existing = REPO_ROOT / "config" / "score_bounds.yaml"
    if existing.is_file():
        try:
            current = yaml.safe_load(existing.read_text(encoding="utf-8"))
            prev = str((current or {}).get("meta", {}).get("bounds_version", ""))
        except yaml.YAMLError:
            prev = ""
        if prev.startswith(f"{today}."):
            try:
                return f"{today}.{int(prev.rsplit('.', 1)[1]) + 1}"
            except ValueError:
                pass
    return f"{today}.1"


def freeze(dry_run: bool) -> int:
    config = load_score_config(REPO_ROOT / "config")
    dist_indicators = REPO_ROOT / "data" / "dist" / "indicators"

    bounds_version = _next_bounds_version()
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
                # v28.3: the freezer refuses to freeze an EMPTY sample —
                # checked BEFORE compute_bounds (which would die on a raw
                # pct-of-nothing ValueError). A block with n_sample 0 or
                # n_entities 0 would be refused by load_score_bounds at
                # every door (strictly positive), so this file would be
                # dead on arrival. An absolute scale over no sample is
                # meaningless; fix the selection or the dist, then re-run.
                n_sample, n_entities = bounds_sample_counts(
                    list(selected.points), comp.transform, config
                )
                if n_sample <= 0 or n_entities <= 0:
                    raise SystemExit(
                        f"REFUSED — {score.value}/{comp.indicator}/{sex}: the retained "
                        f"source '{selected.name}' yields an EMPTY bounds sample "
                        f"(n_sample {n_sample}, n_entities {n_entities}). The "
                        "freezer never freezes an empty sample: every block must "
                        "carry strictly positive counts (the same contract "
                        "load_score_bounds enforces). Fix the selection or the "
                        "dist, then re-run."
                    )
                b: ComponentBounds = compute_bounds(list(selected.points), comp.transform, config)
                block[f"{comp.indicator}/{sex}"] = {
                    "source": selected.name,
                    "source_class": selected.source_class,
                    "floor": b.floor,
                    "lo": b.lo,
                    "hi": b.hi,
                    "n_sample": b.n_sample,
                    "n_unavailable": b.n_unavailable,
                    "n_entities": b.n_entities,
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
