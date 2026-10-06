"""src/score/emit.py — builds data/dist/score/ from the frozen inputs.

Reads: data/dist/indicators/*.json + config/score.yaml +
config/score_bounds.yaml (+ config/todd_refs.yaml for the todd preset's
book counts). Writes: data/dist/score/{meta,official,modelled,
golden_vectors}.json — deterministic bytes (sorted keys, compact
separators, fixed rounding), every file under the ~8 MB cap.

The drift guard: the frozen bounds record WHICH source §4.4 retained at
freeze time; if the live selection on the current dist would pick another
source, the build REFUSES to run (loudly) — a fetch moved the coverage
under the score, and re-freezing is a deliberate bounds_version bump,
never an auto-refresh.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from src.schema.score import Direction, ScoreConfig, ScoreName, SexMode, Transform
from src.schema.todd_refs import ToddCorpus
from src.score.core import (
    ComponentBounds,
    aggregate,
    component_keys,
    delta,
    load_indicator_file,
    normalise_series,
    preset_weights,
    select_source,
)

logger = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compact_json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class BoundsDriftError(Exception):
    """The frozen source no longer matches what §4.4 would pick today."""


def _frozen_bounds_for(score: ScoreName, key: tuple, bounds_doc: dict) -> ComponentBounds:
    block = bounds_doc["bounds"][score.value].get(f"{key[0]}/{key[1]}")
    if block is None:
        raise BoundsDriftError(
            f"config/score_bounds.yaml carries no entry for {score.value}/{key[0]}/{key[1]} — "
            "regenerate: python scripts/freeze_score_bounds.py"
        )
    return ComponentBounds(
        floor=block["floor"],
        lo=float(block["lo"]),
        hi=float(block["hi"]),
        n_sample=int(block["n_sample"]),
        n_unavailable=int(block.get("n_unavailable", 0)),
    )


def build_score_layer(
    config: ScoreConfig,
    bounds_doc: dict,
    dist_dir: Path,
    config_dir: Path,
    corpus: ToddCorpus | None,
) -> dict:
    """Returns the summary the CLI prints; writes the four output files."""
    indicators_dir = dist_dir / "indicators"
    out_dir = dist_dir / "score"
    out_dir.mkdir(parents=True, exist_ok=True)

    # per-score working state
    state: dict = {}
    for score in (ScoreName.official, ScoreName.modelled):
        comps = {c.indicator: c for c in config.components_for(score)}
        normalised: dict = {}
        component_meta: dict = {}
        for key in component_keys(config, score):
            ind_id, sex = key
            comp = comps[ind_id]
            ind_dist = load_indicator_file(indicators_dir, ind_id)
            selected = select_source(ind_dist, sex, score, config.bounds_from_year)

            # --- the drift guard (§4.5): frozen source vs live selection ---
            frozen_block = bounds_doc["bounds"][score.value].get(f"{ind_id}/{sex}")
            if frozen_block is None or frozen_block["source"] != selected.name:
                frozen_name = frozen_block["source"] if frozen_block else "(absent)"
                raise BoundsDriftError(
                    f"BOUNDS DRIFT — {score.value}/{ind_id}/{sex}: the frozen bounds retain "
                    f"'{frozen_name}' but the §4.4 rules would now pick '{selected.name}'. "
                    "A fetch moved the sources' coverage under the score. The scale never "
                    "moves silently: re-run scripts/freeze_score_bounds.py DELIBERATELY, "
                    "bump bounds_version, and record the change in the changelog."
                )
            bounds = _frozen_bounds_for(score, key, bounds_doc)

            series = normalise_series(
                list(selected.points), comp.direction, comp.transform, bounds, config
            )
            normalised[key] = series
            meta = selected.meta()
            meta.update(
                {
                    "direction": comp.direction.value,
                    "transform": comp.transform.value,
                    "basis": comp.basis.value,
                    "provisional": comp.provisional,
                    "sex": sex,
                    "floor": bounds.floor,
                    "lo": bounds.lo,
                    "hi": bounds.hi,
                    "n_sample": bounds.n_sample,
                    "bounds_version": frozen_block["bounds_version"],
                }
            )
            component_meta[f"{ind_id}/{sex}"] = meta
        weights = {
            preset: preset_weights(config, score, corpus, preset) for preset in config.presets
        }
        scores = {
            preset: {
                entity: {
                    year: pair
                    for year, pair in years.items()
                    if pair[1] >= config.coverage_threshold
                }
                for entity, years in aggregate(normalised, weights[preset]).items()
            }
            for preset in config.presets
        }
        state[score] = {
            "normalised": normalised,
            "component_meta": component_meta,
            "weights": weights,
            "scores": {p: {e: y for e, y in s.items() if y} for p, s in scores.items()},
        }

    # --- meta.json: the layer's own contract, fingerprints first ---
    from src.schema.score import EXCLUDED_INDICATORS

    excluded_reasons = {
        "gini_index": "decision 7 — double counting with top_income_share over the shared "
        "survey universe (stays an indicator, todd_core true, on the site)",
        "incarceration_rate": "decision 11 (v27.1) — no defensible monotone direction: the "
        "prison population measures policing and the justice system, not crime or "
        "well-being; the same movement reads in opposite ways (stays an indicator, "
        "todd_core true, on the site)",
        "maternal_deaths": "a count of deaths — maternal_mortality_ratio is the component",
        "same_sex_marriage": "a marker, not a rate",
        "universal_suffrage": "a marker, not a rate",
        "male_height_trend": "an anthropometric trend, out by earlier decision",
        "consanguineous_marriage_rate": "out by earlier decision",
        "crude_birth_rate": "birth_rate_fertility (the TFR) is the component",
        "road_accident_mortality": "the per-vehicle face is the component (official only)",
        "illegitimate_births": "postponed by Ediz — not included, not deleted",
        "immigration_stock": "withdrawn in v26 (a count of persons, not a rate)",
        "agricultural_employment_share": "withdrawn in v26",
    }
    meta_payload = {
        "version": config.version,
        "bounds_version": bounds_doc["meta"]["bounds_version"],
        "derived": True,
        "notice": (
            "DERIVED PRODUCT — the score layer is computed from the indicator dist "
            "(data/dist/indicators/), it is not a measurement: weighted arithmetic means "
            "of normalised values on a frozen absolute scale (p1/p99 of the retained "
            "source since 1990). The indicator layer's three prohibitions (no "
            "interpolation, no derivation, no reconciliation) are untouched. Custom "
            "weights are the frontend's job — docs/score-contract.md is the exact "
            "contract to re-implement."
        ),
        "global": {
            "bounds_from_year": config.bounds_from_year,
            "percentiles": config.percentiles,
            "coverage_threshold": config.coverage_threshold,
            "delta_min_common_weight": config.delta_min_common_weight,
            "fertility_target": config.fertility_target,
            "rounding": config.rounding,
            "presets": config.presets,
        },
        "fingerprints": {
            "score_yaml_sha256": _sha256(config_dir / "score.yaml"),
            "score_bounds_yaml_sha256": _sha256(config_dir / "score_bounds.yaml"),
            "todd_refs_yaml_sha256": _sha256(config_dir / "todd_refs.yaml"),
            "todd_core_csv_sha256": corpus.meta.source_csv_sha256 if corpus else None,
            "indicators": {
                c.indicator: _sha256(indicators_dir / f"{c.indicator}.json")[:12]
                for c in sorted(config.components, key=lambda c: c.indicator)
            },
        },
        "components": {
            f"{c.indicator}/{sex}": {
                "indicator": c.indicator,
                "direction": c.direction.value,
                "transform": c.transform.value,
                "sex_mode": c.sex_mode.value,
                "sex": sex,
                "scores": [s.value for s in c.scores],
                "basis": c.basis.value,
                "provisional": c.provisional,
                "corpus_metric": c.corpus_metric,
            }
            for c in sorted(config.components, key=lambda c: c.indicator)
            for sex in (("male", "female") if c.sex_mode == SexMode.split else ("both",))
        },
        "presets": {
            score.value: {
                preset: {f"{k[0]}/{k[1]}": w for k, w in sorted(weights.items())}
                for preset, weights in state[score]["weights"].items()
            }
            for score in (ScoreName.official, ScoreName.modelled)
        },
        "excluded": {k: excluded_reasons[k] for k in sorted(EXCLUDED_INDICATORS)},
    }
    (out_dir / "meta.json").write_text(_compact_json(meta_payload), encoding="utf-8")

    # --- the two score files ---
    for score in (ScoreName.official, ScoreName.modelled):
        payload = {
            "components": state[score]["component_meta"],
            "normalised": {
                f"{k[0]}/{k[1]}": {e: {str(y): v for y, v in sorted(years.items())} for e, years in sorted(series.items())}
                for k, series in sorted(state[score]["normalised"].items())
            },
            "scores": state[score]["scores"],
        }
        (out_dir / f"{score.value}.json").write_text(_compact_json(payload), encoding="utf-8")

    # --- golden_vectors.json: hand-checkable cases for the frontend ---
    vectors = _golden_vectors(config, state)
    (out_dir / "golden_vectors.json").write_text(
        _compact_json({"n": len(vectors), "vectors": vectors}), encoding="utf-8"
    )

    return {
        "n_components": {
            score.value: len(state[score]["component_meta"])
            for score in (ScoreName.official, ScoreName.modelled)
        },
        "n_scored": {
            f"{score.value}/{preset}": sum(len(years) for years in state[score]["scores"][preset].values())
            for score in (ScoreName.official, ScoreName.modelled)
            for preset in config.presets
        },
        "out_dir": out_dir,
    }


def _golden_vectors(config: ScoreConfig, state: dict) -> list:
    """<= 20 hand-checkable cases: the frontend unit-tests its
    implementation against these. The verifier recomputes every one by an
    independent code path from the EMITTED normalised values.

    v27.1: every `why` label is GENERATED from live readings of the state
    (the v27 audit's fix 4 — two labels had drifted from the truth), so a
    later recomputation can never ship a stale reason.
    """
    from src.score.core import aggregate as _agg
    from src.score.core import score_and_coverage

    vectors: list = []

    def add(score, entity, year, preset, why, with_delta_to=None):
        normalised = state[score]["normalised"]
        weights = state[score]["weights"][preset]

        sc = score_and_coverage(normalised, weights, entity, year)
        if sc is None:
            return
        vec = {
            "score": score.value,
            "entity": entity,
            "year": year,
            "preset": preset,
            "expected": {"score": sc[0], "coverage": sc[1]},
            "why": why,
        }
        if with_delta_to is not None:
            d = delta(normalised, weights, entity, year, with_delta_to, config.delta_min_common_weight)
            if d is not None:
                vec["delta_to_year"] = with_delta_to
                vec["expected"]["delta"] = d
        vectors.append(vec)

    def add_delta(score, entity, y1, y2, preset, why):
        normalised = state[score]["normalised"]
        weights = state[score]["weights"][preset]
        d = delta(normalised, weights, entity, y1, y2, config.delta_min_common_weight)
        if d is None:
            return
        if callable(why):  # the label rides the live delta dict
            why = why(d)
        vectors.append(
            {
                "score": score.value,
                "entity": entity,
                "years": [y1, y2],
                "preset": preset,
                "expected": {"delta": d},
                "why": why,
            }
        )

    # 1. the REFUSED delta (the official Russian pair — common weight under 0.50)
    add_delta(ScoreName.official, "russian_federation", 2000, 2010, "equal",
              lambda d: f"the refused delta: official common weight {d['common_weight_share']} "
                        f"< delta_min_common_weight {config.delta_min_common_weight}")
    # 2. the accepted delta with decomposition (the modelled Russian pair)
    add_delta(ScoreName.modelled, "russian_federation", 2010, 2019, "equal",
              lambda d: f"the accepted delta with per-component decomposition "
                        f"({d['n_components']} common components)")
    add_delta(ScoreName.modelled, "russian_federation", 1995, 2000, "equal",
              "a negative delta (the 1990s collapse decade)")
    # 3. the split-sex case (life expectancy male+female, equal half weights)
    add(ScoreName.official, "france", 2015, "equal", "the split-sex case: life_expectancy male+female half weights")
    # 4. the log component (infant mortality)
    add(ScoreName.modelled, "japan", 2015, "equal", "the log component: infant_mortality floor/clip scale")
    # 5. the target component (fertility — distance to 2.1)
    add(ScoreName.modelled, "france", 2015, "equal", "the target component: fertility distance to 2.1")
    # 6-7. the two 2015 heads (the anchors the changelog quotes)
    add(ScoreName.modelled, "japan", 2015, "equal", "the 2015 modelled head (85.2 in the reference run)")
    add(ScoreName.official, "australia", 2015, "equal", "the 2015 official head (74.7 in the reference run)")
    # 8. the todd preset on the same point (the book-count weights)
    add(ScoreName.modelled, "japan", 2015, "todd", "the todd preset: book-count weights on the same point")
    # 9-12. a few plain countries at the coverage boundary. The US label is
    # GENERATED from the live official coverage at the same point (audit
    # fix 4: v27 blamed 'per-vehicle absent', the real cause is coverage).
    sc_us = score_and_coverage(
        state[ScoreName.official]["normalised"],
        state[ScoreName.official]["weights"]["equal"],
        "united_states", 2015,
    )
    if sc_us is not None:
        n_present = sum(
            1 for key in state[ScoreName.official]["normalised"]
            if 2015 in state[ScoreName.official]["normalised"][key].get("united_states", {})
        )
        n_total = len(state[ScoreName.official]["weights"]["equal"])
        why_us = (
            f"the modelled-only case (no official score — official coverage "
            f"{sc_us[1]:.2f}, {n_present} of {n_total} components present)"
        )
    else:
        why_us = "the modelled-only case (no official score at this point)"
    for entity, year, why in (
        ("germany", 2010, "a plain mid-coverage case"),
        ("united_states", 2015, why_us),
        ("sweden", 2000, "an early-year case on the MODELLED score (the official "
                       "score effectively starts around 2005)"),
        ("nigeria", 2015, "a low-coverage modelled case"),
    ):
        add(ScoreName.modelled, entity, year, "equal", why)

    # 13. the coverage-just-below-threshold case (search live over ALL
    # aggregate points — the emitted scores only carry the above-threshold;
    # v27.1 re-picks from live data: the v27 case is invalid under the
    # new total weight)
    best = None

    all_points = _agg(state[ScoreName.modelled]["normalised"], state[ScoreName.modelled]["weights"]["equal"])
    for entity, years in all_points.items():
        for year_str, (_s, cov) in years.items():
            year = int(year_str)  # aggregate emits string year keys; the score API speaks int
            if config.coverage_threshold - 0.05 <= cov < config.coverage_threshold:
                if best is None or cov > best[2]:
                    best = (entity, year, cov)
    if best:
        normalised = state[ScoreName.modelled]["normalised"]
        weights = state[ScoreName.modelled]["weights"]["equal"]

        sc = score_and_coverage(normalised, weights, best[0], best[1])
        vectors.append(
            {
                "score": "modelled",
                "entity": best[0],
                "year": best[1],
                "preset": "equal",
                "expected": {"score": sc[0], "coverage": sc[1]},
                "why": (
                    f"the coverage-just-below-threshold case: {sc[1]} < {config.coverage_threshold} "
                    "— the score is NOT emitted for this point"
                ),
            }
        )
    return vectors[:20]
