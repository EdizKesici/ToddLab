"""tests/test_score.py — the score layer's unit tests (§6 of the briefs).

Synthetic mini-dists ONLY, no real data: every rule is tested on hand-built
fixtures where the expected value is computable by head. The live invariants
(the 30 byte-identical dist files, the anchors against the reference
prototype) live in scripts/verify_v28_diff.py — these tests are the RULES,
that verifier is the STATE.

v28 sections: the carry rule (decision 16 — age cap, latest-wins, no carry
across entities, max_obs_year cap, the ghost guard, max_age_years 0 = the
exact-year behaviour), the amended delta (same-observation exclusion), the
bounds' independence from the carry, and decision 15's official-only
refusal of illegitimate_births in the modelled score.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schema.score import ScoreComponent, ScoreConfig, ScoreName
from src.schema.todd_refs import ToddCorpus
from src.score.core import (
    aggregate,
    ages_from_obs_years,
    compute_bounds,
    delta,
    fresh_points,
    max_obs_year_of,
    normalise_series,
    pct,
    preset_weights,
    resolve_carry,
    score_and_coverage,
    select_source,
)
from src.score.emit import BoundsDriftError, build_score_layer
from src.config_loader import ConfigError, cross_validate_score


# ---------------------------------------------------------------------------
# helpers: hand-built fixtures
# ---------------------------------------------------------------------------


def _ind(data, witnesses=(), sources=()):
    return {
        "data": list(data),
        "witnesses": list(witnesses),
        "sources": list(sources),
    }


def _pt(entity, year, value, sex=None):
    p = {"entity_id": entity, "year": year, "value": value}
    if sex is not None:
        p["sex"] = sex
    return p


def _config(**overrides):
    base = dict(
        version="test",
        bounds_from_year=1990,
        percentiles=[0.01, 0.99],
        coverage_threshold=0.60,
        delta_min_common_weight=0.50,
        fertility_target=2.1,
        rounding=2,
        presets=["equal", "todd"],
        components=[
            ScoreComponent(
                indicator="alpha",
                direction="lower",
                transform="linear",
                sex_mode="both",
                scores=["official", "modelled"],
                basis="consensus",
                corpus_metric="alpha",
            )
        ],
    )
    base.update(overrides)
    return ScoreConfig.model_validate(base)


# ---------------------------------------------------------------------------
# §6 percentile interpolation
# ---------------------------------------------------------------------------


def test_pct_interpolation_matches_the_linear_formula():
    # numpy's default: linear interpolation between order statistics
    v = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert pct(v, 0.5) == 3.0
    assert pct(v, 0.0) == 1.0
    assert pct(v, 1.0) == 5.0
    # (n-1)*q = 3*0.99 = 2.97 -> v[2] + 0.97*(v[3]-v[2])
    assert abs(pct([10.0, 20.0, 30.0, 40.0], 0.99) - (30.0 + 0.97 * 10.0)) < 1e-12
    # the two-point degenerate case
    assert pct([0.0, 100.0], 0.01) == pytest.approx(1.0)


def test_pct_of_empty_sample_refuses():
    with pytest.raises(ValueError):
        pct([], 0.5)


# ---------------------------------------------------------------------------
# §6 the log floor with p1 = 0
# ---------------------------------------------------------------------------


def test_log_floor_with_zero_p1():
    cfg = _config()
    # a sample where the 1st percentile IS 0 (the HIV shape)
    points = [_pt("a", 2000, v) for v in [0.0] * 3 + [1.0, 2.0, 4.0, 8.0]]
    b = compute_bounds(points, transform="log", config=cfg)
    positive = [1.0, 2.0, 4.0, 8.0]
    # floor = p1 of the strictly positive sample
    assert b.floor == pytest.approx(pct(positive, 0.01))
    # a zero value normalises at the floor (ln(floor) == floor's own log),
    # never crashes, never negative
    series = normalise_series(points, direction="lower", transform="log", bounds=b, config=cfg)
    assert series["a"][2000] is not None
    assert 0.0 <= series["a"][2000] <= 100.0


# ---------------------------------------------------------------------------
# §6 the target distance and v <= 0
# ---------------------------------------------------------------------------


def test_target_distance_symmetry_and_nonpositive_unavailable():
    cfg = _config()
    points = [
        _pt("at_target", 2000, 2.1),   # exactly at replacement -> best (100)
        _pt("above", 2000, 4.2),       # 2x  -> |ln 2|
        _pt("below", 2000, 1.05),      # 0.5x -> |ln 0.5| = |ln 2| (symmetric)
        _pt("zero", 2000, 0.0),        # unavailable
        _pt("neg", 2000, -3.0),        # unavailable
    ]
    b = compute_bounds(points, transform="target", config=cfg)
    assert b.lo == 0.0
    assert b.n_sample == 3 and b.n_unavailable == 2
    series = normalise_series(points, direction="target", transform="target", bounds=b, config=cfg)
    assert series["at_target"][2000] == 100.0
    assert series["above"][2000] == pytest.approx(series["below"][2000], abs=0.02)
    assert "zero" not in series and "neg" not in series


# ---------------------------------------------------------------------------
# §6 each direction
# ---------------------------------------------------------------------------


def test_directions_higher_lower_target():
    cfg = _config()
    pts = [_pt("e", 2000, 1.0), _pt("e", 2001, 5.0)]
    b = compute_bounds(pts, transform="linear", config=cfg)
    hi = normalise_series(pts, direction="higher", transform="linear", bounds=b, config=cfg)
    lo = normalise_series(pts, direction="lower", transform="linear", bounds=b, config=cfg)
    assert hi["e"][2001] == 100.0 and hi["e"][2000] == 0.0
    assert lo["e"][2001] == 0.0 and lo["e"][2000] == 100.0
    tgt = normalise_series(
        [_pt("e", 2000, 2.1)], direction="target", transform="target",
        bounds=compute_bounds([_pt("e", 2000, 2.1)], transform="target", config=cfg), config=cfg,
    )
    assert tgt["e"][2000] == 100.0


def test_clip_at_frozen_bounds():
    # values beyond the frozen p1/p99 clip to [0, 100] — the absolute scale
    cfg = _config()
    b = compute_bounds([_pt("a", 2000, v) for v in (10.0, 20.0)], transform="linear", config=cfg)
    pts = [_pt("out_high", 2000, 999.0), _pt("out_low", 2000, -999.0)]
    s = normalise_series(pts, direction="higher", transform="linear", bounds=b, config=cfg)
    assert s["out_high"][2000] == 100.0 and s["out_low"][2000] == 0.0


# ---------------------------------------------------------------------------
# §6 one source per component, never mixed
# ---------------------------------------------------------------------------


def test_modelled_never_mixes_sources():
    """The fixture: canonical says country X improved, witness says it
    collapsed — a MIXED series would average lies; the rule picks ONE."""
    cfg = _config()
    canonical = [_pt("x", 2000, 10.0), _pt("x", 2010, 2.0)]   # improved (lower=better)
    witness_pts = [_pt("x", 2000, 2.0), _pt("x", 2005, 50.0), _pt("x", 2010, 90.0)]
    ind = _ind(
        canonical,
        witnesses=[{
            "provider": "worldbank", "source_ref": "W", "root": "r",
            "root_label": "R", "layer": "harmonized", "data": witness_pts,
        }],
    )
    # modelled: the witness has 3 points >= 1990, the canonical 2 -> witness
    sel = select_source(ind, "both", ScoreName.modelled, 1990)
    assert sel.name == "worldbank:W" and sel.source_class == "modelled"
    b = compute_bounds(list(sel.points), transform="linear", config=cfg)
    s = normalise_series(list(sel.points), direction="lower", transform="linear", bounds=b, config=cfg)
    # the score rides the WITNESS alone: 2010 (90, worst) scores BELOW 2000 (2, best)
    assert s["x"][2010] == 0.0 and s["x"][2000] == 100.0
    # and every stored value derives from the witness's own numbers — a
    # mixed series (canonical 2000=10 with witness 2010=90) would have
    # scored 2000 LOWER than 2010: the opposite ranking. Never mixed.


def test_official_prefers_canonical_even_when_witness_is_bigger():
    cfg = _config()
    canonical = [_pt("x", 2000, 10.0)]
    witness_pts = [_pt("y", 2000, 5.0), _pt("y", 2001, 6.0), _pt("y", 2002, 7.0)]
    ind = _ind(canonical, witnesses=[{
        "provider": "owid", "source_ref": "O", "root": "r", "root_label": "R",
        "layer": "harmonized", "data": witness_pts,
    }])
    from src.schema.score import ScoreName

    sel = select_source(ind, "both", ScoreName.official, 1990)
    assert sel.name == "canonical" and sel.source_class == "canonical"


def test_official_fallback_to_witness_carries_the_badge():
    """The official fallback: no canonical point for the component -> the
    modelled rule among witnesses, badged source_class: modelled."""
    from src.schema.score import ScoreName

    ind = _ind(
        [_pt("x", 1989, 1.0)],  # pre-1990 only: still a non-null point...
        witnesses=[
            {"provider": "owid", "source_ref": "A", "root": "r1", "root_label": "R1",
             "layer": "harmonized", "data": [_pt("x", 2000, 1.0)]},
            {"provider": "who_gho", "source_ref": "B", "root": "r2", "root_label": "R2",
             "layer": "harmonized", "data": [_pt("x", 2000, 1.0), _pt("x", 2001, 2.0)]},
        ],
    )
    # an EMPTY canonical data block (the honest fallback case)
    ind["data"] = []
    sel = select_source(ind, "both", ScoreName.official, 1990)
    assert sel.name == "who_gho:B"  # most points >= 1990 among witnesses
    assert sel.source_class == "modelled"  # THE BADGE


# ---------------------------------------------------------------------------
# §6 sex split halves and equal total weight
# ---------------------------------------------------------------------------


def test_sex_split_half_weights():
    cfg = _config(
        components=[
            ScoreComponent(indicator="beta", direction="higher", transform="linear",
                           sex_mode="split", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="beta"),
            ScoreComponent(indicator="alpha", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="alpha"),
        ]
    )
    from src.schema.score import ScoreName

    w = preset_weights(cfg, ScoreName.official, None, "equal")
    assert w[("beta", "male")] == 0.5 and w[("beta", "female")] == 0.5
    assert w[("alpha", "both")] == 1.0
    assert sum(w.values()) == 2.0  # two indicators, total weight 2


# ---------------------------------------------------------------------------
# §6 the todd weights from a fixture corpus, with the floor
# ---------------------------------------------------------------------------


def _corpus(metrics: dict) -> ToddCorpus:
    total = sum(sum(r["citations"] for r in refs) for refs in metrics.values())
    return ToddCorpus.model_validate({
        "meta": {
            "source_csv_sha256": "a" * 64,
            "rows": sum(len(r) for r in metrics.values()),
            "metrics": len(metrics),
            "books": 16,
            "total_citations": total,
        },
        "metrics": {
            mid: {"family": "society", "refs": refs}
            for mid, refs in metrics.items()
        },
    })


def test_todd_weights_book_counts_with_floor():
    cfg = _config(
        components=[
            ScoreComponent(indicator="alpha", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="alpha"),
            ScoreComponent(indicator="gamma", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"],
                           basis="consensus", corpus_metric=None),  # null -> floor 1
            ScoreComponent(indicator="delta", direction="higher", transform="linear",
                           sex_mode="split", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="delta"),
        ]
    )
    corpus = _corpus({
        "alpha": [{"book": "B1", "year": 1976, "citations": 3, "label": "l", "note": "n"},
                  {"book": "B2", "year": 1979, "citations": 2, "label": "l", "note": "n"},
                  {"book": "B3", "year": 1988, "citations": 1, "label": "l", "note": "n"}],
        "delta": [{"book": "B1", "year": 1976, "citations": 5, "label": "l", "note": "n"}],
    })
    from src.schema.score import ScoreName

    w = preset_weights(cfg, ScoreName.official, corpus, "todd")
    assert w[("alpha", "both")] == 3.0       # 3 distinct books
    assert w[("gamma", "both")] == 1.0       # null corpus_metric -> floor 1
    assert w[("delta", "male")] == 0.5       # 1 book, split -> half
    assert w[("delta", "female")] == 0.5


# ---------------------------------------------------------------------------
# §6 coverage threshold edge (just below / at)
# ---------------------------------------------------------------------------


def test_coverage_threshold_edge():
    normalised = {
        ("a", "both"): {"e": {2000: 50.0, 2001: 60.0}},
        ("b", "both"): {"e": {2000: 50.0, 2001: 60.0}},
        ("c", "both"): {"e": {2000: 50.0}},  # 2001 missing
        ("d", "both"): {"e": {2000: 50.0, 2001: 60.0}},
        ("e", "both"): {"e": {2000: 50.0, 2001: 60.0}},
    }
    weights = {("a", "both"): 1.0, ("b", "both"): 1.0, ("c", "both"): 1.0,
               ("d", "both"): 1.0, ("e", "both"): 1.0}
    # 2000: 5/5 available -> coverage 1.0; 2001: 4/5 -> 0.8 (c is missing)
    sc_full = score_and_coverage(normalised, weights, "e", 2000)
    sc_four = score_and_coverage(normalised, weights, "e", 2001)
    assert sc_full[1] == 1.0 and sc_four[1] == 0.8
    # exactly at the threshold: drop one more (d) -> 3 of 5 = 0.60 -> a score EXISTS
    normalised[("d", "both")]["e"].pop(2001)
    at = score_and_coverage(normalised, weights, "e", 2001)
    assert at[1] == pytest.approx(0.6)
    assert at[1] >= 0.60  # the emit rule: >= threshold
    # just below: drop e too -> 2 of 5 = 0.4 -> no score
    normalised[("e", "both")]["e"].pop(2001)
    below = score_and_coverage(normalised, weights, "e", 2001)
    assert below[1] < 0.60


# ---------------------------------------------------------------------------
# §6 the delta rule (common set, refusal)
# ---------------------------------------------------------------------------


def test_delta_rule_common_set_and_refusal():
    normalised = {
        ("a", "both"): {"e": {2000: 40.0, 2010: 60.0}},
        ("b", "both"): {"e": {2000: 40.0, 2010: 60.0}},
        ("c", "both"): {"e": {2000: 40.0, 2010: 60.0}},
        ("d", "both"): {"e": {2000: 40.0}},              # not at 2010
        ("e", "both"): {"e": {2000: 40.0, 2010: 60.0}},
    }
    weights = {k: 1.0 for k in normalised}
    d = delta(normalised, weights, "e", 2000, 2010, 0.50)
    assert d["refused"] is False
    assert d["delta"] == 20.0 and d["n_components"] == 4
    assert d["common_weight_share"] == 0.8
    # every decomposition term = w*(v2-v1)/w_common = 20/4 = 5.0 each
    assert all(abs(v - 5.0) < 1e-9 for v in d["decomposition"].values())
    # refusal: only 2 common of 5 -> share 0.4 < 0.50
    normalised[("c", "both")]["e"].pop(2010)
    normalised[("e", "both")]["e"].pop(2010)
    d2 = delta(normalised, weights, "e", 2000, 2010, 0.50)
    assert d2["refused"] is True
    assert d2["reason"] == "common_weight_below_threshold"
    # empty common set -> None
    for k in list(normalised):
        normalised[k]["e"].pop(2010, None)
    assert delta(normalised, weights, "e", 2000, 2010, 0.50) is None


# ---------------------------------------------------------------------------
# §6 presets computed from rounded stored values
# ---------------------------------------------------------------------------


def test_presets_from_rounded_stored_values():
    cfg = _config(rounding=2)
    pts = [_pt("a", 2000, v) for v in (1.0, 2.0, 3.0, 4.0)]
    b = compute_bounds(pts, transform="linear", config=cfg)
    s = normalise_series([_pt("a", 2000, 2.5)], direction="higher",
                          transform="linear", bounds=b, config=cfg)
    # the stored value is rounded to 2 decimals BEFORE any aggregate reads it
    stored = s["a"][2000]
    assert stored == round(stored, 2)
    # full precision would give 50.0 (midpoint of 1..4); rounding cannot drift it here
    assert stored == 50.0
    # a value whose full-precision normalisation is not 2-decimal-exact:
    b2 = compute_bounds([_pt("a", 2000, v) for v in (0.0, 7.0)], transform="linear", config=cfg)
    s2 = normalise_series([_pt("a", 2000, 3.0)], direction="higher",
                          transform="linear", bounds=b2, config=cfg)
    expected = round(100.0 * (3.0 - b2.lo) / (b2.hi - b2.lo), 2)
    assert s2["a"][2000] == expected  # the STORED value, rounded at the boundary
    agg = aggregate({("a", "both"): {"a": {2000: s2["a"][2000]}}},
                    {("a", "both"): 1.0})
    assert agg["a"]["2000"][0] == expected  # the aggregate rides the stored value


# ---------------------------------------------------------------------------
# §6 gini refused in the config
# ---------------------------------------------------------------------------


def test_gini_refused_in_config():
    with pytest.raises(ValidationError, match="EXCLUDED"):
        _config(components=[
            ScoreComponent(indicator="gini_index", direction="lower", transform="linear",
                           sex_mode="both", scores=["official"], basis="consensus"),
        ])


def test_incarceration_refused_in_config():
    # decision 11 (v27.1): the prison population measures policing and the
    # justice system, not crime or well-being — no defensible monotone
    # direction, so it can never be a score component (stays an indicator)
    with pytest.raises(ValidationError, match="EXCLUDED"):
        _config(components=[
            ScoreComponent(indicator="incarceration_rate", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"], basis="editorial"),
        ])


def test_withdrawn_ids_refused_too():
    for iid in ("immigration_stock", "illegitimate_births", "maternal_deaths"):
        with pytest.raises(ValidationError):
            _config(components=[
                ScoreComponent(indicator=iid, direction="lower", transform="linear",
                               sex_mode="both", scores=["modelled"], basis="consensus"),
            ])


# ---------------------------------------------------------------------------
# §6 zero disagreement between higher_is_better and the score direction
# ---------------------------------------------------------------------------


class _Ind:
    def __init__(self, id, higher_is_better):
        self.id = id
        self.higher_is_better = higher_is_better


def test_direction_agreement_zero_disagreement():
    cfg = _config(
        components=[
            ScoreComponent(indicator="alpha", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"], basis="consensus",
                           corpus_metric=None),
            ScoreComponent(indicator="beta", direction="higher", transform="linear",
                           sex_mode="split", scores=["official", "modelled"], basis="consensus",
                           corpus_metric=None),
        ]
    )
    indicators = {"alpha": _Ind("alpha", False), "beta": _Ind("beta", True)}
    cross_validate_score(cfg, indicators, None)  # agrees -> passes

    bad = _config(
        components=[
            ScoreComponent(indicator="alpha", direction="higher", transform="linear",
                           sex_mode="both", scores=["official", "modelled"], basis="consensus",
                           corpus_metric=None),
        ]
    )
    with pytest.raises(ConfigError, match="DISAGREES"):
        cross_validate_score(bad, {"alpha": _Ind("alpha", False)}, None)

    # the TARGET direction is the only exclusion (no higher_is_better reading)
    tgt = _config(
        components=[
            ScoreComponent(indicator="alpha", direction="target", transform="target",
                           sex_mode="both", scores=["official", "modelled"], basis="editorial",
                           corpus_metric=None),
        ]
    )
    cross_validate_score(tgt, {"alpha": _Ind("alpha", False)}, None)  # target never disagrees


def test_unknown_indicator_refused():
    cfg = _config()
    with pytest.raises(ConfigError, match="names no indicator"):
        cross_validate_score(cfg, {}, None)


# ---------------------------------------------------------------------------
# §6 determinism + the drift guard (mini end-to-end through build_score_layer)
# ---------------------------------------------------------------------------


def _mini_dist(tmp_path: Path):
    """Two indicators on a synthetic dist: alpha (lower/linear/both) with a
    canonical + a witness, beta (higher/linear/split) canonical-only."""
    ind_dir = tmp_path / "indicators"
    ind_dir.mkdir(parents=True)
    alpha = {
        "id": "alpha", "sources": [
            {"provider": "eurostat", "source_ref": "A", "role": "canonical",
             "layer": "collector", "root": "rt_a", "root_label": "RT-A"},
        ],
        "data": [_pt("x", 2000, 4.0), _pt("x", 2005, 2.0), _pt("y", 2000, 2.0)],
        "witnesses": [{
            "provider": "worldbank", "source_ref": "WA", "root": "rt_w",
            "root_label": "RT-W", "layer": "harmonized",
            "data": [_pt("x", 2000, 5.0), _pt("y", 2000, 1.0), _pt("z", 2000, 3.0)],
        }],
    }
    beta = {
        "id": "beta", "sources": [
            {"provider": "eurostat", "source_ref": "B", "role": "canonical",
             "layer": "collector", "root": "rt_b", "root_label": "RT-B"},
        ],
        "data": [_pt("x", 2000, 60.0, sex="male"), _pt("x", 2000, 64.0, sex="female"),
                 _pt("y", 2000, 70.0, sex="male"), _pt("y", 2000, 74.0, sex="female")],
        "witnesses": [],
    }
    (ind_dir / "alpha.json").write_text(json.dumps(alpha), encoding="utf-8")
    (ind_dir / "beta.json").write_text(json.dumps(beta), encoding="utf-8")

    cfg = _config(
        components=[
            ScoreComponent(indicator="alpha", direction="lower", transform="linear",
                           sex_mode="both", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="alpha"),
            ScoreComponent(indicator="beta", direction="higher", transform="linear",
                           sex_mode="split", scores=["official", "modelled"],
                           basis="consensus", corpus_metric="beta"),
        ]
    )
    return tmp_path, cfg


def _mini_bounds_doc(tmp_path: Path, cfg: ScoreConfig):
    """Hand-computed frozen bounds matching the mini-dist's §4.4 picks."""
    # modelled alpha: witness (3 pts >= 1990) beats canonical (3 pts but
    # canonical is 3 vs witness 3 -> tie -> canonical wins!). Recount:
    # canonical non-null >=1990: x2000, x2005, y2000 = 3; witness: 3 -> TIE
    # -> canonical. To make the witness win, give it more points below.
    # (The fixture above ties; the pick is canonical for BOTH scores.)
    from src.score.core import compute_bounds, select_source
    from src.schema.score import ScoreName

    doc = {"meta": {"bounds_version": "test.1", "generated": "2026-10-05",
                    "score_config_sha256": "0" * 64, "score_config_version": "test"},
           "bounds": {"official": {}, "modelled": {}}}
    for score in (ScoreName.official, ScoreName.modelled):
        for comp in cfg.components_for(score):
            ind = json.loads((tmp_path / "indicators" / f"{comp.indicator}.json").read_text())
            sexes = ("male", "female") if comp.sex_mode == "split" else ("both",)
            for sex in sexes:
                sel = select_source(ind, sex, score, cfg.bounds_from_year)
                b = compute_bounds(list(sel.points), comp.transform, cfg)
                doc["bounds"][score.value][f"{comp.indicator}/{sex}"] = {
                    "source": sel.name, "source_class": sel.source_class,
                    "floor": b.floor, "lo": b.lo, "hi": b.hi,
                    "n_sample": b.n_sample, "n_unavailable": b.n_unavailable,
                    "bounds_version": "test.1",
                }
    return doc


def test_build_score_layer_deterministic_and_drift_guard(tmp_path):
    dist, cfg = _mini_dist(tmp_path)  # dist IS the dist root: indicators/ lives in it
    bounds_doc = _mini_bounds_doc(dist, cfg)

    # a config dir with the yaml files the meta fingerprints read
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "score.yaml").write_text("version: test", encoding="utf-8")
    (cfg_dir / "score_bounds.yaml").write_text("meta: {}", encoding="utf-8")
    (cfg_dir / "todd_refs.yaml").write_text("meta: {}", encoding="utf-8")

    s1 = build_score_layer(cfg, bounds_doc, dist, cfg_dir, None)
    out = dist / "score"
    bytes1 = {f.name: f.read_bytes() for f in out.iterdir()}
    # rebuild -> byte-identical
    s2 = build_score_layer(cfg, bounds_doc, dist, cfg_dir, None)
    bytes2 = {f.name: f.read_bytes() for f in out.iterdir()}
    assert bytes1 == bytes2
    assert s1["n_components"]["official"] == 3  # alpha/both + beta/male + beta/female
    assert s1["n_components"]["modelled"] == 3

    # the emitted scores respect the threshold: with the mini fixture every
    # entity-year has all components -> coverage 1.0 >= 0.60
    official = json.loads((out / "official.json").read_text())
    assert set(official["normalised"]) == {"alpha/both", "beta/male", "beta/female"}

    # THE DRIFT GUARD: freeze a WRONG source -> the build refuses, loudly
    doc_wrong = json.loads(json.dumps(bounds_doc))
    doc_wrong["bounds"]["official"]["alpha/both"]["source"] = "worldbank:WA"
    with pytest.raises(BoundsDriftError, match="BOUNDS DRIFT"):
        build_score_layer(cfg, doc_wrong, dist, cfg_dir, None)


# ---------------------------------------------------------------------------
# v28 THE CARRY RULE (decision 16) — synthetic normalised maps, hand-computed
# ---------------------------------------------------------------------------


def _norm():
    """alpha/both: x observed 2000 (50.0) and 2004 (70.0); z observed 2004
    only (60.0). max_obs_year over the score = 2004."""
    return {
        ("alpha", "both"): {
            "x": {2000: 50.0, 2004: 70.0},
            "z": {2004: 60.0},
        }
    }


def test_carry_age_cap_exact():
    resolved, obs_years = resolve_carry(_norm(), 3, 1990, 2004)
    # x: 2000 fresh; 2001-2003 carried from 2000 (ages 1-3); 2004 fresh
    assert resolved[("alpha", "both")]["x"] == {
        2000: 50.0, 2001: 50.0, 2002: 50.0, 2003: 50.0, 2004: 70.0,
    }
    assert obs_years[("alpha", "both")]["x"] == {
        2000: 2000, 2001: 2000, 2002: 2000, 2003: 2000, 2004: 2004,
    }
    # THE CAP: with max_age_years = 3, an observation at 2004 does NOT
    # fill 2000-2003 (backward carry never happens: the window is
    # [Y - max_age, Y]) and 2000's value does NOT reach 2004+1 anywhere.


def test_carry_age_four_is_not_carried():
    # a 5-year gap: 2000 observed, next candidate year 2005 > 2000 + 3
    norm = {("alpha", "both"): {"x": {2000: 50.0, 2005: 70.0}}}
    resolved, _ = resolve_carry(norm, 3, 1990, 2005)
    # 2004 would need the 2000 observation at age 4 — refused
    assert 2004 not in resolved[("alpha", "both")]["x"]
    assert resolved[("alpha", "both")]["x"] == {
        2000: 50.0, 2001: 50.0, 2002: 50.0, 2003: 50.0, 2005: 70.0,
    }


def test_carry_latest_observation_wins():
    # two candidates inside the window at Y=2003 (the score's max_obs_year
    # pushed to 2003 by ANOTHER component's observation): the LATER wins
    norm = {("alpha", "both"): {"x": {2000: 50.0, 2002: 62.0}}}
    resolved, obs_years = resolve_carry(norm, 3, 1990, 2003)
    assert resolved[("alpha", "both")]["x"][2003] == 62.0  # 2002 beats 2000
    assert obs_years[("alpha", "both")]["x"][2003] == 2002
    assert resolved[("alpha", "both")]["x"][2001] == 50.0  # 2002 not yet seen
    assert obs_years[("alpha", "both")]["x"][2001] == 2000


def test_carry_fresh_beats_older():
    # a fresh observation at Y always wins over an older one in the window
    norm = {("alpha", "both"): {"x": {2000: 50.0, 2002: 62.0}}}
    resolved, obs_years = resolve_carry(norm, 3, 1990, 2002)
    assert resolved[("alpha", "both")]["x"][2002] == 62.0
    assert obs_years[("alpha", "both")]["x"][2002] == 2002  # age 0


def test_nothing_carried_across_entities():
    resolved, _ = resolve_carry(_norm(), 3, 1990, 2004)
    # z is observed 2004 only: 2001-2003 stay absent (x's 2000 never fills z)
    assert resolved[("alpha", "both")]["z"] == {2004: 60.0}


def test_max_obs_year_cap():
    # no resolved year beyond the score's max_obs_year (2004 here)
    resolved, _ = resolve_carry(_norm(), 3, 1990, 2004)
    every_year = [y for e in resolved[("alpha", "both")].values() for y in e]
    assert every_year and max(every_year) == 2004
    # and max_obs_year_of reads it from the fresh map itself
    assert max_obs_year_of(_norm()) == 2004


def test_carry_before_bounds_from_year_never_resolved():
    # observations before bounds_from_year are outside the score's range:
    # the 1985 point never fills 1990 (its window ends at 1988), and the
    # 1995 observation carries only within [1990, max_obs_year=1995]
    norm = {("alpha", "both"): {"x": {1985: 10.0, 1995: 30.0}}}
    resolved, _ = resolve_carry(norm, 3, 1990, 1995)
    assert 1990 not in resolved[("alpha", "both")]["x"]
    assert resolved[("alpha", "both")]["x"] == {1995: 30.0}


def test_max_age_years_zero_equals_exact_year():
    norm = _norm()
    resolved, obs_years = resolve_carry(norm, 0, 1990, 2004)
    # window [Y, Y]: only fresh observations survive, identical to v27
    assert resolved == {k: {e: {y: v for y, v in ys.items()} for e, ys in s.items()} for k, s in norm.items()}
    assert ages_from_obs_years(obs_years) == {}


def test_ages_map_is_sparse_and_consistent():
    resolved, obs_years = resolve_carry(_norm(), 3, 1990, 2004)
    ages = ages_from_obs_years(obs_years)
    assert ages == {("alpha", "both"): {"x": {2001: 1, 2002: 2, 2003: 3}}}
    # absent = fresh: every emitted age is >= 1 and < = max_age_years
    for key, ents in ages.items():
        for entity, years in ents.items():
            for year, age in years.items():
                assert 1 <= age <= 3
                assert resolved[key][entity][year] == resolved[key][entity][year - age]


def test_fresh_guard_refuses_ghost_scores():
    # x reaches coverage 1.0 in 2001-2003 on CARRIED values alone — ghosts,
    # refused; only 2000 (fresh) and 2004 (fresh) are emitted
    resolved, obs_years = resolve_carry(_norm(), 3, 1990, 2004)
    weights = {("alpha", "both"): 1.0}
    agg = aggregate(resolved, weights)
    fresh = fresh_points(obs_years)
    emitted = {
        e: {y: p for y, p in ys.items() if p[1] >= 0.60 and (e, int(y)) in fresh}
        for e, ys in agg.items()
    }
    assert set(emitted["x"]) == {"2000", "2004"}
    assert set(emitted["z"]) == {"2004"}
    # the ghost years DID reach the coverage threshold — the guard, not the
    # threshold, refuses them
    assert all(agg["x"][y][1] >= 0.60 for y in ("2001", "2002", "2003"))


def test_delta_excludes_same_observation_components():
    # alpha moves 40->50 between 2000 and 2001; beta is CARRIED into 2001
    # (same 2000 observation): its zero term must NOT dilute the delta
    resolved = {
        ("alpha", "both"): {"x": {2000: 40.0, 2001: 50.0}},
        ("beta", "both"): {"x": {2000: 30.0, 2001: 30.0}},
    }
    weights = {("alpha", "both"): 1.0, ("beta", "both"): 1.0}
    ages = {("beta", "both"): {"x": {2001: 1}}}

    d = delta(resolved, weights, "x", 2000, 2001, 0.50, ages=ages)
    assert d["refused"] is False
    assert d["n_components"] == 1
    assert d["delta"] == 10.0  # 50 - 40, undamped by beta's zero term
    assert d["common_weight_share"] == 0.5

    # without the age map (the pre-v28 caller): beta counts, delta damped
    d_old = delta(resolved, weights, "x", 2000, 2001, 0.50)
    assert d_old["n_components"] == 2
    assert d_old["delta"] == 5.0

    # the refusal still rides the AMENDED common weight: threshold 0.75
    # refuses the share-0.5 pair even though coverage is full
    d_ref = delta(resolved, weights, "x", 2000, 2001, 0.75, ages=ages)
    assert d_ref["refused"] is True
    assert d_ref["common_weight_share"] == 0.5

    # every common component resting on the same observation -> C empty
    resolved2 = {
        ("alpha", "both"): {"x": {2000: 40.0, 2001: 40.0}},
        ("beta", "both"): {"x": {2000: 30.0, 2001: 30.0}},
    }
    ages2 = {
        ("alpha", "both"): {"x": {2001: 1}},
        ("beta", "both"): {"x": {2001: 1}},
    }
    assert delta(resolved2, weights, "x", 2000, 2001, 0.50, ages=ages2) is None


def test_bounds_unaffected_by_the_carry_rule(tmp_path):
    # end-to-end on the mini dist: the emitted component bounds are the
    # FROZEN ones — the carried years (2001-2003 now in normalised) never
    # feed lo/hi/n_sample
    dist, cfg = _mini_dist(tmp_path)
    bounds_doc = _mini_bounds_doc(dist, cfg)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "score.yaml").write_text("version: test", encoding="utf-8")
    (cfg_dir / "score_bounds.yaml").write_text("meta: {}", encoding="utf-8")
    (cfg_dir / "todd_refs.yaml").write_text("meta: {}", encoding="utf-8")
    build_score_layer(cfg, bounds_doc, dist, cfg_dir, None)
    official = json.loads((dist / "score" / "official.json").read_text())
    for key, block in bounds_doc["bounds"]["official"].items():
        emitted = official["components"][key]
        assert emitted["lo"] == block["lo"]
        assert emitted["hi"] == block["hi"]
        assert emitted["n_sample"] == block["n_sample"]
        assert emitted["bounds_version"] == block["bounds_version"]
    # the carry DID add years to normalised (the resolved range is wider
    # than the fresh one) while the bounds stayed frozen
    assert "2001" in official["normalised"]["alpha/both"]["x"]
    assert official["age"]["alpha/both"]["x"] == {"2001": 1, "2002": 2, "2003": 3}


# ---------------------------------------------------------------------------
# v28 decisions 12-15 at the config level
# ---------------------------------------------------------------------------


def _ib_component(scores):
    return ScoreComponent(
        indicator="illegitimate_births", direction="lower", transform="linear",
        sex_mode="both", scores=scores, basis="todd", provisional=False,
        corpus_metric="illegitimate_births",
    )


def test_illegitimate_births_accepted_official_refused_modelled():
    # accepted: official only (decision 15)
    cfg = _config(components=[_ib_component(["official"])])
    assert cfg.components[0].indicator == "illegitimate_births"
    # refused loudly on the modelled side
    with pytest.raises(ValidationError, match="OFFICIAL-SCORE-ONLY"):
        _config(components=[_ib_component(["official", "modelled"])])
    with pytest.raises(ValidationError, match="OFFICIAL-SCORE-ONLY"):
        _config(components=[_ib_component(["modelled"])])


def test_gini_and_incarceration_still_refused():
    for bad_id in ("gini_index", "incarceration_rate"):
        with pytest.raises(ValidationError, match="EXCLUDED"):
            _config(components=[
                ScoreComponent(indicator=bad_id, direction="lower", transform="linear",
                               sex_mode="both", scores=["official"], basis="consensus")
            ])


def test_max_age_years_schema():
    cfg = _config()
    assert cfg.max_age_years == 3  # the shipped default (decision 16)
    with pytest.raises(ValidationError):
        _config(**{"max_age_years": -1})
    with pytest.raises(ValidationError):
        _config(**{"max_age_years": 1.5})
    zero = _config(**{"max_age_years": 0})
    assert zero.max_age_years == 0  # the tested exact-year configuration


def test_shipped_score_config_has_no_editorial_basis():
    # decisions 12-14 confirmed in the books: every component now carries
    # basis in {todd, consensus} and no provisional flag remains — asserted
    # on the REAL config, not a fixture (the brief's "assert it")
    from src.config_loader import load_score_config

    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_score_config(repo_root / "config")
    assert cfg.max_age_years == 3
    assert all(c.basis.value in ("todd", "consensus") for c in cfg.components)
    assert not any(c.provisional for c in cfg.components)
    for iid in ("birth_rate_fertility", "top_income_share",
                "tertiary_education_share", "industrial_employment_share"):
        comp = next(c for c in cfg.components if c.indicator == iid)
        assert comp.basis.value == "todd", iid
        assert comp.provisional is False, iid
    ib = next(c for c in cfg.components if c.indicator == "illegitimate_births")
    assert [s.value for s in ib.scores] == ["official"]
    assert ib.basis.value == "todd" and ib.provisional is False
