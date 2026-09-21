"""`cli stats` (added v9.1): the numbers a changelog "Verified" section may
quote, emitted from the dist files themselves — never memory, never a
fixture.

Born from the two v9-review findings:
1. The IMR base count "1,419" looked wrong to the reviewer because their
   recount (1,398 / 117 entities) measured the un_dyb-only subset — the
   21 curated USSR points (1970-1990) make the canonical tier
   multi-provider without the bare number saying so. The stats line
   carries the per-provider split so any recount reconciles at a glance.
2. The v9 changelog cited "the MMEIG witness carries 5.2" for France 2022
   — a value that never existed in the fetched data (the real witness
   stops at 2020; the 5.2 lived only in this repo's TEST FIXTURE,
   retracted in v9.1). The witness coverage line (points / entities /
   year range) exists so such a claim is checkable against one line of
   tool output instead of trust.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.conftest import (
    seed_curated_snapshot,
    seed_dyb_snapshot,
    seed_dyb_table17_snapshot,
    seed_dyb_table4_snapshot,
    seed_oecd_snapshot,
    seed_owid_snapshot,
)

from src.pipeline.build import build_all
from src.pipeline.merge import merge_all
from src.pipeline.normalize import normalize_all
from src.pipeline.stats import render_stats
from src.pipeline.validate import validate_all


def _build_mini_dist(tmp_path: Path, real_indicators, real_entities) -> Path:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    dist_dir = tmp_path / "dist"
    reports_dir = tmp_path / "reports"

    seed_curated_snapshot(raw_dir, "infant_mortality")
    seed_dyb_snapshot(raw_dir, "infant_mortality")
    seed_dyb_table4_snapshot(raw_dir, "life_expectancy")
    seed_dyb_table17_snapshot(raw_dir, "maternal_mortality_ratio")
    seed_owid_snapshot(raw_dir, "infant_mortality", "infant-mortality", "owid_infant_mortality.csv")
    seed_owid_snapshot(raw_dir, "life_expectancy", "life-expectancy", "owid_life_expectancy.csv")
    seed_owid_snapshot(raw_dir, "homicide_rate", "homicide-rate-unodc", "owid_homicide_rate.csv")
    seed_owid_snapshot(
        raw_dir, "maternal_mortality_ratio", "maternal-mortality", "owid_maternal_mortality.csv",
        value_field="Maternal mortality ratio",
    )
    seed_oecd_snapshot(raw_dir, "homicide_rate")

    normalize_all(real_indicators, raw_dir, processed_dir, real_entities)
    merge_all(list(real_indicators.keys()), processed_dir)
    validate_all(real_indicators, processed_dir, real_entities, reports_dir)
    build_all(real_indicators, processed_dir, dist_dir, real_entities)
    return dist_dir


def test_stats_carries_the_provider_split_that_makes_recounts_reconcile(tmp_path, real_indicators, real_entities):
    # A bare canonical count hid the curated tier: the v9 review recounted
    # 1,398 un_dyb points where the dist (and its changelog) said 1,419 —
    # the delta was exactly the 21 curated USSR points. The stats line must
    # therefore always name every provider, its count and its year range.
    dist_dir = _build_mini_dist(tmp_path, real_indicators, real_entities)
    imr_line = next(l for l in render_stats(dist_dir).splitlines() if l.startswith("infant_mortality:"))

    # Structure: totals + gap accounting + the split, in one greppable line
    # (providers ordered by count; every provider named with count+years).
    assert re.match(
        r"^infant_mortality: canonical [\d,]+ points = [\d,]+ valued \+ [\d,]+ explicit gaps; "
        r"valued by provider: [a-z_]+ [\d,]+ \(\d{4}-\d{4}\)"
        r"( \+ [a-z_]+ [\d,]+ \(\d{4}-\d{4}\))*",
        imr_line,
    ), imr_line
    # The real committed catalog is deterministic: the curated USSR series
    # is 21 points over 1970-1990 — the exact series a provider filter or a
    # 2007-2024 year window silently drops.
    assert "curated 21 (1970-1990)" in imr_line
    assert re.search(r"un_dyb [\d,]+ \(\d{4}-\d{4}\)", imr_line)  # split names every provider


def test_stats_shows_witness_coverage_and_clean_zero_gap_rendering(tmp_path, real_indicators, real_entities):
    # The witness lines carry points / entities / YEAR RANGE: the failure
    # mode of v9 (citing a 2022 witness value) would have confronted its
    # author with the coverage in plain sight. The fixture witness runs
    # 2019-2021 (deliberately past the real snapshot's 2020 cap — see
    # tests/fixtures/README.md).
    dist_dir = _build_mini_dist(tmp_path, real_indicators, real_entities)
    out = render_stats(dist_dir)

    maternal_witness = next(
        l for l in out.splitlines() if l.strip().startswith("witness owid:maternal-mortality:")
    )
    assert maternal_witness.strip() == "witness owid:maternal-mortality: 15 points, 7 entities, 2019-2021"

    # The no-null real dataflow vs the honest fixture: the REAL OECD
    # response carries no null OBS_VALUE rows (the real dist's homicide
    # line reads 7,193 = 7,193 + 0), while the fixture deliberately embeds
    # one empty OBS_VALUE row — so the mini-dist line pins the gap
    # accounting "7 valued + 1 explicit gaps" exactly.
    homicide_line = next(l for l in out.splitlines() if l.startswith("homicide_rate:"))
    assert "7 valued + 1 explicit gaps" in homicide_line


def test_stats_carries_the_roots_line_the_genealogy_of_agreement(tmp_path, real_indicators, real_entities):
    # v11: one line per indicator naming the roots and the doors — the line
    # that prevents "four witnesses agree" from reading as "four
    # independent confirmations". IMR's four agreeing witnesses are ONE
    # IGME root; LE's two witnesses carry DIFFERENT roots (the mixed OWID
    # long-run compilation vs pure WPP) — the line must say both.
    dist_dir = _build_mini_dist(tmp_path, real_indicators, real_entities)
    out = render_stats(dist_dir)

    imr_roots = next(
        l for l in out.splitlines() if l.strip().startswith("roots canonical:")
    )
    # IMR: the roots line follows its canonical line (order of file lines).
    imr_block = out.split("infant_mortality:")[1].split("\nlife_expectancy:")[0]
    assert "roots canonical: soviet_official (curated) + unsd_dyb (un_dyb x13); witness: un_igme (owid, who_gho, worldbank x2)" in imr_block

    le_block = out.split("life_expectancy:")[1].split("\nmaternal")[0] if "\nmaternal" in out else out.split("life_expectancy:")[1]
    assert "witness: owid_longrun_composite (owid) + un_wpp (worldbank x2)" in le_block
