"""src/score/emit.py — builds data/dist/score/ from the frozen inputs.

Reads: data/dist/indicators/*.json + config/score.yaml +
config/score_bounds.yaml (+ config/todd_refs.yaml for the todd preset's
book counts). Writes: data/dist/score/{meta,official,modelled,
golden_vectors}.json — deterministic bytes (sorted keys, compact
separators, fixed rounding), every file under the ~8 MB cap.

The drift guard: the frozen bounds record WHICH source the selection
retained at freeze time; if the live selection on the current dist would
pick another source, the build REFUSES to run (loudly) — a fetch moved
the coverage under the score, and re-freezing is a deliberate
bounds_version bump, never an auto-refresh.

THE CARRY RULE (v28, decision 16): after the fresh normalisation, each
component's stored value for year Y is RESOLVED to the latest real
observation with obs_year in [Y - max_age_years, Y] (src/score/
core.resolve_carry — one implementation shared by every consumer). The
emitted `normalised` maps hold the RESOLVED values; a sparse `age` map
(component -> entity -> year -> age, present only where age >= 1)
records the carry; `scores` are computed from the resolved values and
emitted only where coverage >= threshold AND at least one component is
fresh (the ghost guard); no year beyond the score's max_obs_year is
emitted. Bounds are NEVER recomputed here and never affected by the
carry (fresh observations only, at freeze time).
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
    ages_from_obs_years,
    component_keys,
    delta,
    fresh_points,
    load_indicator_file,
    max_obs_year_of,
    normalise_series,
    preset_weights,
    resolve_carry,
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
        fresh_normalised: dict = {}
        component_meta: dict = {}
        for key in component_keys(config, score):
            ind_id, sex = key
            comp = comps[ind_id]
            ind_dist = load_indicator_file(indicators_dir, ind_id)
            selected = select_source(ind_dist, sex, score, config.bounds_from_year)

            # --- the drift guard: frozen source vs live selection ---
            frozen_block = bounds_doc["bounds"][score.value].get(f"{ind_id}/{sex}")
            if frozen_block is None or frozen_block["source"] != selected.name:
                frozen_name = frozen_block["source"] if frozen_block else "(absent)"
                raise BoundsDriftError(
                    f"BOUNDS DRIFT — {score.value}/{ind_id}/{sex}: the frozen bounds retain "
                    f"'{frozen_name}' but the selection rules would now pick '{selected.name}'. "
                    "A fetch moved the sources' coverage under the score. The scale never "
                    "moves silently: re-run scripts/freeze_score_bounds.py DELIBERATELY, "
                    "bump bounds_version, and record the change in the changelog."
                )
            bounds = _frozen_bounds_for(score, key, bounds_doc)

            series = normalise_series(
                list(selected.points), comp.direction, comp.transform, bounds, config
            )
            fresh_normalised[key] = series
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

        # --- the v28 carry rule (decision 16): resolve every year to the
        # latest real observation within max_age_years, record the ages ---
        max_obs = max_obs_year_of(fresh_normalised)
        resolved, obs_years = resolve_carry(
            fresh_normalised, config.max_age_years, config.bounds_from_year, max_obs
        )
        ages = ages_from_obs_years(obs_years)
        fresh = fresh_points(obs_years)

        weights = {
            preset: preset_weights(config, score, corpus, preset) for preset in config.presets
        }
        scores = {
            preset: {
                entity: {
                    year: pair
                    for year, pair in years.items()
                    if pair[1] >= config.coverage_threshold and (entity, int(year)) in fresh
                }
                for entity, years in aggregate(resolved, weights[preset]).items()
            }
            for preset in config.presets
        }
        state[score] = {
            "normalised": resolved,
            "ages": ages,
            "fresh": fresh,
            "max_obs_year": max_obs,
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
            "interpolation, no derivation, no reconciliation) are untouched; the v28 "
            "carry rule is NOT interpolation — a real observation is reused, capped "
            "at max_age_years, its age recorded in the age maps and displayed. Custom "
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
            "max_age_years": config.max_age_years,
        },
        "carry_rule": (
            "decision 16 (v28): a component's value for year Y is the LATEST real "
            "observation with obs_year in [Y - max_age_years, Y]; age = Y - obs_year "
            "lives in each score file's sparse 'age' map (absent = fresh); a score is "
            "emitted only where coverage >= threshold AND at least one component is "
            "fresh; no year beyond the score's max_obs_year"
        ),
        "max_obs_year": {
            score.value: state[score]["max_obs_year"]
            for score in (ScoreName.official, ScoreName.modelled)
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
            "age": {
                f"{k[0]}/{k[1]}": {e: {str(y): a for y, a in sorted(years.items())} for e, years in sorted(series.items())}
                for k, series in sorted(state[score]["ages"].items())
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
        "max_obs_year": {
            score.value: state[score]["max_obs_year"]
            for score in (ScoreName.official, ScoreName.modelled)
        },
        "out_dir": out_dir,
    }


def _golden_vectors(config: ScoreConfig, state: dict) -> list:
    """<= 20 hand-checkable cases: the frontend unit-tests its
    implementation against these. The verifier recomputes every one by an
    independent code path from the EMITTED normalised values and age maps.

    v27.1: every `why` label is GENERATED from live readings of the state
    (the v27 audit's fix 4 — two labels had drifted from the truth), so a
    later recomputation can never ship a stale reason.

    v28 adds the carry rule's four contract cases — a carried component
    (age >= 1), a delta that EXCLUDES a component resting on the same
    observation at both dates, the right edge (2022 modelled, suicide and
    life expectancy at 60 carried), and an illegitimate_births official
    point — plus the ghost-guard case (coverage above the threshold, no
    fresh component: NOT emitted).
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
            d = delta(
                normalised, weights, entity, year, with_delta_to,
                config.delta_min_common_weight, ages=state[score]["ages"],
            )
            if d is not None:
                vec["delta_to_year"] = with_delta_to
                vec["expected"]["delta"] = d
        vectors.append(vec)

    def add_delta(score, entity, y1, y2, preset, why):
        normalised = state[score]["normalised"]
        weights = state[score]["weights"][preset]
        d = delta(
            normalised, weights, entity, y1, y2,
            config.delta_min_common_weight, ages=state[score]["ages"],
        )
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

    def age_of(score, ind, sex, entity, year):
        """The live age of one component at one point (0 = fresh). The
        internal state keys components as (indicator, sex) TUPLES and
        years as INTs — the string forms exist only in the emitted JSON."""
        return state[score]["ages"].get((ind, sex), {}).get(entity, {}).get(year, 0)

    def obs_year_of(score, ind, sex, entity, year):
        """The underlying observation's year: year - age (fresh when 0)."""
        return year - age_of(score, ind, sex, entity, year)

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
    # 6-7. the two 2015 heads (the anchors the changelog quotes — the label
    # rides the LIVE value, never a typed number). v28.1: the head ENTITY is
    # picked live too (the #1 of the emitted equal-preset scores at 2015,
    # ties broken alphabetically) — the DYB TFR door put japan atop the
    # official 2015 ranking where australia stood at v28, and a hardcoded
    # head can silently stop being the head (the modelled-only case's own
    # lesson, applied one case earlier).
    for score in (ScoreName.modelled, ScoreName.official):
        _head_rank = sorted(
            ((ys["2015"][0], e) for e, ys in state[score]["scores"]["equal"].items()
             if "2015" in ys),
            key=lambda t: (-t[0], t[1]),
        )
        _fallback = "japan" if score == ScoreName.modelled else "australia"
        entity = _head_rank[0][1] if _head_rank else _fallback
        sc = score_and_coverage(
            state[score]["normalised"], state[score]["weights"]["equal"], entity, 2015
        )
        why = (
            f"the 2015 {score.value} head ({sc[0]} live, the anchor the changelog quotes)"
            if sc is not None
            else f"the 2015 {score.value} head"
        )
        add(score, entity, 2015, "equal", why)
    # 8. the todd preset on the same point (the book-count weights)
    add(ScoreName.modelled, "japan", 2015, "todd", "the todd preset: book-count weights on the same point")
    # 9-12. a few plain countries at the coverage boundary. The
    # modelled-only case is RE-PICKED LIVE (v28.1's lesson, the case-13
    # discipline extended): the case's premise — a modelled-scored
    # country with NO official score — is a property of the data, and the
    # v28.1 DYB TFR wiring moved the US across the official threshold at
    # 2015 (coverage 0.61, fertility arrived via the Yearbook), silently
    # invalidating the hardcoded choice's label. The picker now takes the
    # CLOSEST MISS among 2015's modelled-scored entities (the highest
    # official coverage still under the threshold, ties alphabetical) —
    # the most informative representative of what the modelled layer is
    # FOR, re-derived at every generation so a later config change can
    # never leave a stale premise behind.
    _official_2015 = state[ScoreName.official]["scores"]["equal"]
    _candidates = [
        e for e in state[ScoreName.modelled]["scores"]["equal"]
        if 2015 in {int(y) for y in state[ScoreName.modelled]["scores"]["equal"][e]}
        and "2015" not in _official_2015.get(e, {})
    ]
    _closest = None
    for _e in sorted(_candidates):
        sc_c = score_and_coverage(
            state[ScoreName.official]["normalised"],
            state[ScoreName.official]["weights"]["equal"],
            _e, 2015,
        )
        if sc_c is None:
            continue
        if _closest is None or sc_c[1] > _closest[2]:
            _closest = (_e, sc_c[0], sc_c[1])
    if _closest is not None:
        _entity, _score, _cov = _closest
        n_present = sum(
            1 for key in state[ScoreName.official]["normalised"]
            if 2015 in state[ScoreName.official]["normalised"][key].get(_entity, {})
        )
        n_total = len(state[ScoreName.official]["weights"]["equal"])
        why_closest = (
            f"the modelled-only case (no official score — official coverage "
            f"{_cov:.2f}, {n_present} of {n_total} components present)"
        )
        modelled_only_case = (_entity, 2015, why_closest)
    else:
        modelled_only_case = ("nigeria", 2015, "the modelled-only case (no official score at this point)")
    for entity, year, why in (
        ("germany", 2010, "a plain mid-coverage case"),
        modelled_only_case,
        ("sweden", 2000, "an early-year case on the MODELLED score"),
        ("nigeria", 2015, "a low-coverage modelled case"),
    ):
        add(ScoreName.modelled, entity, year, "equal", why)

    # 13. the coverage-just-below-threshold case (search live over ALL
    # resolved aggregate points — the emitted scores only carry the
    # above-threshold-and-fresh; re-picked at every generation: a case
    # invalidated by a later config change can never survive)
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

    # 14. the CARRIED component case: a scored modelled point where PISA
    # (math_test_scores) rests on an older observation (age >= 1) — the
    # v28 contract's badge "data from YYYY". First match in a deterministic
    # (entity, year) order; the label rides the live age.
    carried = None
    for entity in sorted(state[ScoreName.modelled]["scores"]["equal"]):
        for year_str in sorted(state[ScoreName.modelled]["scores"]["equal"][entity]):
            year = int(year_str)
            a = age_of(ScoreName.modelled, "math_test_scores", "both", entity, year)
            if a >= 1:
                carried = (entity, year, a)
                break
        if carried:
            break
    if carried:
        entity, year, a = carried
        why = (
            f"the carried-component case: math_test_scores at {year} rests on the "
            f"{year - a} observation (age {a} <= {config.max_age_years}) — display "
            f"'data from {year - a}'"
        )
        add(ScoreName.modelled, entity, year, "equal", why)

    # 15. the delta that EXCLUDES a same-observation component: an accepted
    # consecutive-year modelled delta where at least one component present
    # at both dates rests on the SAME observation (its zero term must NOT
    # dilute the common weight). First match in deterministic order.
    same_obs = None
    for entity in sorted(state[ScoreName.modelled]["scores"]["equal"]):
        years = sorted(int(y) for y in state[ScoreName.modelled]["scores"]["equal"][entity])
        for y1, y2 in zip(years, years[1:]):
            if y2 != y1 + 1:
                continue
            d = delta(
                state[ScoreName.modelled]["normalised"],
                state[ScoreName.modelled]["weights"]["equal"],
                entity, y1, y2, config.delta_min_common_weight,
                ages=state[ScoreName.modelled]["ages"],
            )
            if d is None or d.get("refused"):
                continue
            resting = [
                key for key in sorted(state[ScoreName.modelled]["normalised"])
                if y1 in state[ScoreName.modelled]["normalised"][key].get(entity, {})
                and y2 in state[ScoreName.modelled]["normalised"][key].get(entity, {})
                and obs_year_of(ScoreName.modelled, key[0], key[1], entity, y1)
                == obs_year_of(ScoreName.modelled, key[0], key[1], entity, y2)
            ]
            # same underlying observation at both dates (the delta's C
            # excludes exactly these; includes the fresh-at-y1-carried-to-y2)
            if resting:
                same_obs = (entity, y1, y2, resting)
                break
        if same_obs:
            break
    if same_obs:
        entity, y1, y2, resting = same_obs
        first = f"{resting[0][0]}/{resting[0][1]}"
        why = (
            f"the amended delta: {len(resting)} component(s) (e.g. {first}) rest on the "
            f"same observation at {y1} and {y2} and are EXCLUDED from C — their zero "
            "term must not dilute the common weight"
        )
        add_delta(ScoreName.modelled, entity, y1, y2, "equal", why)

    # 16. the RIGHT-EDGE case: a scored 2022 modelled point where suicide
    # and life expectancy at 60 (both faces) are carried — the honest
    # picture of the series' last years. First match in deterministic order.
    right_edge = None
    for entity in sorted(state[ScoreName.modelled]["scores"]["equal"]):
        if "2022" in state[ScoreName.modelled]["scores"]["equal"][entity]:
            a_s = age_of(ScoreName.modelled, "suicide_rate", "both", entity, 2022)
            a_m = age_of(ScoreName.modelled, "life_expectancy_60", "male", entity, 2022)
            a_f = age_of(ScoreName.modelled, "life_expectancy_60", "female", entity, 2022)
            if a_s >= 1 and a_m >= 1 and a_f >= 1:
                right_edge = (entity, a_s, a_m, a_f)
                break
    if right_edge:
        entity, a_s, a_m, a_f = right_edge
        why = (
            f"the right-edge case: modelled 2022 with suicide_rate carried (age {a_s}) "
            f"and life_expectancy_60 carried (male age {a_m}, female age {a_f}) — "
            "the last years of a series are largely carried, display the ages"
        )
        add(ScoreName.modelled, entity, 2022, "equal", why)

    # 17. the illegitimate_births official case (decision 15, v28): a scored
    # official point carrying the new component. France 2015 first, else the
    # first match in deterministic order.
    ib = ("france", 2015)
    if not (
        "france" in state[ScoreName.official]["scores"]["equal"]
        and "2015" in state[ScoreName.official]["scores"]["equal"]["france"]
        and 2015 in state[ScoreName.official]["normalised"]
        .get(("illegitimate_births", "both"), {})
        .get("france", {})
    ):
        ib = None
        for entity in sorted(state[ScoreName.official]["scores"]["equal"]):
            for year_str in sorted(state[ScoreName.official]["scores"]["equal"][entity]):
                year = int(year_str)
                if year in (
                    state[ScoreName.official]["normalised"]
                    .get(("illegitimate_births", "both"), {})
                    .get(entity, {})
                ):
                    ib = (entity, year)
                    break
            if ib:
                break
    if ib:
        add(
            ScoreName.official, ib[0], ib[1], "equal",
            "the illegitimate_births case (decision 15, v28): Todd's "
            "illégitimité in the OFFICIAL score only — the modelled score "
            "refuses it (47 entities, almost all European)",
        )

    # 18. the GHOST-GUARD case: a point with coverage >= threshold and NO
    # fresh component — NOT emitted (decision 16's safety). The latest such
    # year wins (ties: first entity in sorted order).
    ghost = None
    fresh = state[ScoreName.official]["fresh"]
    official_points = _agg(
        state[ScoreName.official]["normalised"],
        state[ScoreName.official]["weights"]["equal"],
    )
    for entity in sorted(official_points):
        for year_str, (_s, cov) in sorted(official_points[entity].items()):
            year = int(year_str)
            if cov >= config.coverage_threshold and (entity, year) not in fresh:
                if ghost is None or year > ghost[1]:
                    ghost = (entity, year, cov)
    if ghost:
        sc = score_and_coverage(
            state[ScoreName.official]["normalised"],
            state[ScoreName.official]["weights"]["equal"],
            ghost[0], ghost[1],
        )
        vectors.append(
            {
                "score": "official",
                "entity": ghost[0],
                "year": ghost[1],
                "preset": "equal",
                "expected": {"score": sc[0], "coverage": sc[1]},
                "why": (
                    f"the ghost-guard case: coverage {sc[1]} >= {config.coverage_threshold} "
                    f"but NO component is fresh at {ghost[1]} — the score is NOT emitted"
                ),
            }
        )
    return vectors[:20]
