"""src/score/core.py — the score layer's pure computation (ADR-0011).

No network, no data/raw, no data/processed: the input is the FROZEN
indicator dist (data/dist/indicators/*.json), config/score.yaml and the
frozen config/score_bounds.yaml. The output is data/dist/score/ (emit.py).

The rules here are the SINGLE implementation of the source selection
(§4.4), the normalisation (§4.6), the v28 CARRY RULE (decision 16) and
the aggregation/delta rules (§4.8-4.9): scripts/freeze_score_bounds.py
uses them to WRITE the frozen bounds, rebuild uses them to read and apply
the frozen bounds, and the drift guard uses them to compare the frozen
source — and, since v28.2, the frozen bounds SAMPLE'S SIZE AND ENTITY
COUNT — with what the rules would pick today. One implementation,
three consumers — the rules can never fork.

Determinism contract: every iteration is over sorted keys; every stored
value is rounded at the config's `rounding` decimals and every later
aggregate reads the STORED values; the same dist + config bytes give the
same output bytes.

THE CARRY RULE (v28, decision 16 — amends decision 3): no interpolation;
a real observation may be carried forward for at most `max_age_years`,
with its age recorded. For each (score, component, entity) and each year
Y in [bounds_from_year, max_obs_year(score)]: the value used is the
LATEST real observation with obs_year in [Y - max_age_years, Y]; age =
Y - obs_year (0 = fresh). Carrying NEVER crosses entities, sources or
sexes (the resolution is per component key and entity), a null point is
never an observation, and the frozen bounds are computed on fresh
observations only — the carry rule never moves the scale.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from src.schema.score import Direction, ScoreConfig, ScoreName, SexMode, Transform
from src.schema.todd_refs import ToddCorpus

ComponentKey = tuple[str, str]  # (indicator, sex) with sex in both|male|female


# ---------------------------------------------------------------------------
# §4.4 source selection — deterministic, logged, never mixed within a component
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectedSource:
    """The ONE series a component reads, for all countries and all years."""

    name: str  # "canonical" or "provider:source_ref"
    source_class: str  # "canonical" | "modelled" (the badge: a witness inside a score)
    points: tuple = field(repr=False, default=())
    root: str | None = None
    root_label: str | None = None
    layer: str | None = None

    def meta(self) -> dict:
        """The per-component provenance block the output carries: chosen
        source, root, class, n points, n entities, year range."""
        entities = {p["entity_id"] for p in self.points}
        years = [p["year"] for p in self.points]
        return {
            "source": self.name,
            "source_class": self.source_class,
            "root": self.root,
            "root_label": self.root_label,
            "layer": self.layer,
            "n_points": len(self.points),
            "n_entities": len(entities),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        }


def _sex_points(block: list, sex: str) -> list:
    """Non-null points of one series block for one sex. An absent `sex`
    key means both sexes (the house convention); explicit male/female
    points of the same block never leak into a both-sexes component."""
    if sex == "both":
        return [p for p in block if p.get("value") is not None and p.get("sex") in (None, "both")]
    return [p for p in block if p.get("value") is not None and p.get("sex") == sex]


def _candidate_blocks(ind_dist: dict, sex: str) -> list:
    """Every candidate series for (indicator, sex): the canonical data
    block plus each witness block, in the file's own declaration order
    (order is only the fallback of the last tie-break, never the winner)."""
    cands = [{"name": "canonical", "is_canonical": True, "block": ind_dist["data"]}]
    for w in ind_dist.get("witnesses", []):
        cands.append(
            {
                "name": f"{w['provider']}:{w['source_ref']}",
                "is_canonical": False,
                "block": w["data"],
                "root": w.get("root"),
                "root_label": w.get("root_label"),
                "layer": w.get("layer"),
            }
        )
    return cands


def _canonical_meta(ind_dist: dict) -> dict:
    """Provenance for the canonical choice: the roots/layers the dist's
    own `sources` block declares for role=canonical (a multi-door
    canonical prints every door's root; one label when they agree)."""
    entries = [s for s in ind_dist.get("sources", []) if s.get("role") == "canonical"]

    def _one(key: str):
        vals = sorted({s.get(key) for s in entries if s.get(key)})
        return vals[0] if len(vals) == 1 else (vals or None)

    return {"root": _one("root"), "root_label": _one("root_label"), "layer": _one("layer")}


def select_source(ind_dist: dict, sex: str, score: ScoreName, bounds_from_year: int) -> SelectedSource:
    """§4.4: ONE source per (score, component), for all countries and years.

    - official: the canonical series; if it has no non-null point for the
      component, fall back to the witness chosen as in modelled and badge
      the component source_class: modelled (the fallback is exercised on
      a fixture even though no component needs it today).
    - modelled: the candidate with the most non-null country-years at
      year >= bounds_from_year; tie -> canonical; tie -> alphabetically
      first name. Null-valued points are gaps and never count.
    """
    cands = [
        {**cand, "points": _sex_points(cand["block"], sex)} for cand in _candidate_blocks(ind_dist, sex)
    ]
    if score == ScoreName.official:
        canonical = cands[0]
        if canonical["points"]:
            return SelectedSource(
                name="canonical",
                source_class="canonical",
                points=tuple(canonical["points"]),
                **_canonical_meta(ind_dist),
            )
        cands = [c for c in cands[1:] if c["points"]]  # the fallback: witnesses only

    def rank(c: dict) -> tuple[int, int]:
        return (
            sum(1 for p in c["points"] if p["year"] >= bounds_from_year),
            1 if c["is_canonical"] else 0,
        )

    cands = [c for c in cands if c["points"]]
    if not cands:
        raise ValueError(
            "no candidate series carries a non-null point — the component has no face at all"
        )
    best = max(rank(c) for c in cands)
    chosen = sorted((c for c in cands if rank(c) == best), key=lambda c: c["name"])[0]
    meta = (
        _canonical_meta(ind_dist)
        if chosen["is_canonical"]
        else {
            "root": chosen.get("root"),
            "root_label": chosen.get("root_label"),
            "layer": chosen.get("layer"),
        }
    )
    return SelectedSource(
        name=chosen["name"],
        source_class="canonical" if chosen["is_canonical"] else "modelled",
        points=tuple(chosen["points"]),
        **meta,
    )


# ---------------------------------------------------------------------------
# §4.6 normalisation — the absolute scale with frozen bounds
# ---------------------------------------------------------------------------


def pct(values: list, q: float) -> float:
    """The p-quantile with linear interpolation between order statistics
    (numpy's default method) — the same formula the reference prototype
    and the frozen bounds use, so the three never disagree."""
    if not values:
        raise ValueError("pct of an empty sample")
    v = sorted(values)
    k = (len(v) - 1) * q
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


@dataclass(frozen=True)
class ComponentBounds:
    floor: float | None  # log components only: p1 of the strictly positive sample
    lo: float
    hi: float
    n_sample: int
    n_unavailable: int = 0  # target components: points dropped for v <= 0
    n_entities: int = 0  # v28.2: distinct entity_id in the bounds sample


def bounds_sample(points: list, transform: Transform, config: ScoreConfig) -> list:
    """The ONE sampling rule of the frozen bounds (v28.2): the non-null
    points of the retained source with year >= bounds_from_year; a target
    transform additionally drops non-positive values (counted in
    n_unavailable). The freezer's n_sample AND n_entities, and the drift
    guard's live recomputation of both, read THIS function — the guard
    never re-derives its own sampling, so the two sides can never disagree
    on what "the bounds sample" means."""
    sample = [
        p for p in points
        if p["year"] >= config.bounds_from_year and p.get("value") is not None
    ]
    if transform == Transform.target:
        sample = [p for p in sample if float(p["value"]) > 0]
    return sample


def bounds_sample_counts(points: list, transform: Transform, config: ScoreConfig) -> tuple[int, int]:
    """(n_sample, n_entities) of the bounds sample — the drift guard's two
    live measures, computed by the freezer's own sampling rule (the shared
    bounds_sample above). v28.2's guard compares these against the frozen
    block's recorded values."""
    sample = bounds_sample(points, transform, config)
    return len(sample), len({p["entity_id"] for p in sample})


def compute_bounds(points: list, transform: Transform, config: ScoreConfig) -> ComponentBounds:
    """The bounds computation the FREEZER runs (rebuild never recomputes —
    it reads config/score_bounds.yaml; changing bounds = a deliberate
    regeneration plus a bounds_version bump).

    Sample = bounds_sample(points) — all non-null values of the retained
    source with year >= bounds_from_year (the target transform
    additionally drops non-positive values, counted in n_unavailable);
    n_entities counts the distinct entity_id in that sample (v28.2).
    """
    p_lo, p_hi = config.percentiles
    sample_points = bounds_sample(points, transform, config)
    sample = [float(p["value"]) for p in sample_points]
    n_entities = len({p["entity_id"] for p in sample_points})
    n_unavailable = 0
    if transform == Transform.target:
        # the target's positive filter (inside bounds_sample) drops the
        # non-positive points — n_unavailable records how many there were
        # among the year-filtered non-null points of the retained source.
        n_unavailable = sum(
            1
            for p in points
            if p["year"] >= config.bounds_from_year
            and p.get("value") is not None
            and float(p["value"]) <= 0
        )
    if transform == Transform.log:
        positive = [v for v in sample if v > 0]
        if not positive:
            raise ValueError("log component with no strictly positive sample value")
        floor = pct(positive, p_lo)
        t = [math.log(max(v, floor)) for v in sample]
        return ComponentBounds(
            floor=floor, lo=pct(t, p_lo), hi=pct(t, p_hi), n_sample=len(t), n_entities=n_entities
        )
    if transform == Transform.target:
        t = [abs(math.log(v / config.fertility_target)) for v in sample]
        return ComponentBounds(
            floor=None,
            lo=0.0,
            hi=pct(t, p_hi),
            n_sample=len(t),
            n_unavailable=n_unavailable,
            n_entities=n_entities,
        )
    return ComponentBounds(
        floor=None, lo=pct(sample, p_lo), hi=pct(sample, p_hi),
        n_sample=len(sample), n_entities=n_entities,
    )


def normalise_series(
    points: list,
    direction: Direction,
    transform: Transform,
    bounds: ComponentBounds,
    config: ScoreConfig,
) -> dict:
    """entity_id -> year -> the STORED normalised value (0..100, rounded
    to config.rounding decimals — every later aggregate reads the stored
    values, never full-precision ghosts)."""
    out: dict = {}
    for p in points:
        y = p["year"]
        if y < config.bounds_from_year:
            continue
        v = float(p["value"])
        if transform == Transform.target:
            if v <= 0:
                continue  # a non-positive target value is unavailable, never a zero
            t = abs(math.log(v / config.fertility_target))
        elif transform == Transform.log:
            t = math.log(max(v, bounds.floor if bounds.floor is not None else 1.0))
        else:
            t = v
        n = (t - bounds.lo) / (bounds.hi - bounds.lo) if bounds.hi > bounds.lo else 0.0
        n = min(1.0, max(0.0, n))
        if direction in (Direction.lower, Direction.target):
            n = 1.0 - n
        stored = round(100.0 * n, config.rounding)
        out.setdefault(p["entity_id"], {})[y] = stored
    return out


# ---------------------------------------------------------------------------
# §4.8 aggregation — presets, coverage, the two-year delta
# ---------------------------------------------------------------------------


def max_obs_year_of(normalised: dict) -> int | None:
    """The score's max_obs_year (v28): the greatest year with a real
    (fresh, non-null) observation in ANY retained source of the score —
    no score year is emitted beyond it. None when the score has no
    observation at all."""
    years = [y for series in normalised.values() for ey in series.values() for y in ey]
    return max(years) if years else None


def resolve_carry(
    normalised: dict,  # ComponentKey -> entity -> year -> stored FRESH value
    max_age_years: int,
    bounds_from_year: int,
    max_obs_year: int | None,
) -> tuple[dict, dict]:
    """The v28 carry rule (decision 16). Returns (resolved, obs_years):

    - resolved: ComponentKey -> entity -> year -> the STORED value in use
      (fresh, or the latest fresh observation within max_age_years — the
      stored rounded value is carried as-is, so every later aggregate
      still reads stored values only);
    - obs_years: ComponentKey -> entity -> year -> the underlying
      observation's year (== year when fresh).

    Nothing is carried across entities or component keys (the loops are
    per key and entity); a year with no candidate in the window stays
    absent (a gap is a gap, never interpolated); no year beyond
    max_obs_year is ever emitted. max_age_years == 0 reproduces the
    exact-year behaviour identically (the window [Y, Y] holds only a
    fresh observation).
    """
    resolved: dict = {key: {} for key in normalised}
    obs_years: dict = {key: {} for key in normalised}
    if max_obs_year is None or max_obs_year < bounds_from_year:
        return resolved, obs_years
    for key in sorted(normalised):
        series = normalised[key]
        for entity in sorted(series):
            years = sorted(series[entity])
            if not years:
                continue
            ent_res: dict = {}
            ent_obs: dict = {}
            for year in range(bounds_from_year, max_obs_year + 1):
                candidates = [y for y in years if year - max_age_years <= y <= year]
                if not candidates:
                    continue
                y0 = candidates[-1]  # the LATEST observation in the window wins
                ent_res[year] = series[entity][y0]
                ent_obs[year] = y0
            resolved[key][entity] = ent_res
            obs_years[key][entity] = ent_obs
    return resolved, obs_years


def ages_from_obs_years(obs_years: dict) -> dict:
    """The EMITTED sparse age map: ComponentKey -> entity -> year -> age,
    present only where age >= 1 (absent = fresh). This is the exact shape
    data/dist/score/*.json carry and the frontend contract documents."""
    ages: dict = {}
    for key in sorted(obs_years):
        for entity in sorted(obs_years[key]):
            sparse = {
                year: year - obs
                for year, obs in sorted(obs_years[key][entity].items())
                if obs != year
            }
            if sparse:
                ages.setdefault(key, {})[entity] = sparse
    return ages


def fresh_points(obs_years: dict) -> set:
    """The ghost guard's set: (entity, year) where at least one available
    component is FRESH (obs_year == year). A country-year with coverage
    above the threshold but NO fresh component is a ghost — not emitted."""
    fresh: set = set()
    for key in sorted(obs_years):
        for entity, years in obs_years[key].items():
            for year, obs in years.items():
                if obs == year:
                    fresh.add((entity, year))
    return fresh


def component_keys(config: ScoreConfig, score: ScoreName) -> list:
    """The (indicator, sex) keys of one score, in deterministic order."""
    keys: list = []
    for c in config.components_for(score):
        if c.sex_mode == SexMode.split:
            keys.append((c.indicator, "male"))
            keys.append((c.indicator, "female"))
        else:
            keys.append((c.indicator, "both"))
    return sorted(keys)


def preset_weights(
    config: ScoreConfig,
    score: ScoreName,
    corpus: ToddCorpus | None,
    preset: str,
) -> dict:
    """equal: weight 1 per indicator (0.5 per sex component).
    todd: the indicator's weight = DISTINCT BOOKS citing its corpus_metric
    in todd_refs (floor 1 when null or 0); sex components carry half."""
    weights: dict = {}
    for c in config.components_for(score):
        if preset == "todd":
            metric = c.corpus_metric
            if metric and corpus is not None and metric in corpus.metrics:
                w = float(max(1, corpus.metrics[metric].books_count))
            else:
                w = 1.0
        else:  # equal
            w = 1.0
        if c.sex_mode == SexMode.split:
            w = w / 2.0
        for sex in (("male", "female") if c.sex_mode == SexMode.split else ("both",)):
            weights[(c.indicator, sex)] = w
    return weights


def aggregate(
    normalised: dict,  # ComponentKey -> entity -> year -> stored value
    weights: dict,  # ComponentKey -> weight
) -> dict:
    """entity -> year(str) -> [score, coverage] over the components with
    a stored value that year. score = weighted mean of STORED values;
    coverage = available weight / total weight (exact — the weights are
    exact, only the normalised values are rounded)."""
    total_w = sum(weights.values())
    by_ey: dict = {}
    for key in sorted(normalised):
        w = weights[key]
        for entity, years in normalised[key].items():
            for year, value in years.items():
                by_ey.setdefault(entity, {}).setdefault(year, []).append((w, value))
    out: dict = {}
    for entity in sorted(by_ey):
        for year in sorted(by_ey[entity]):
            pairs = by_ey[entity][year]
            w_sum = sum(w for w, _ in pairs)
            score = sum(w * v for w, v in pairs) / w_sum
            out.setdefault(entity, {})[str(year)] = [round(score, 2), round(w_sum / total_w, 4)]
    return out


def score_and_coverage(
    normalised: dict,
    weights: dict,
    entity: str,
    year: int,
) -> tuple[float, float] | None:
    """The single (score, coverage) pair for one entity-year — the
    verifier's independent recomputation path and the golden vectors'
    generator."""
    total_w = sum(weights.values())
    pairs = []
    for key in sorted(normalised):
        value = normalised[key].get(entity, {}).get(year)
        if value is not None:
            pairs.append((weights[key], value))
    if not pairs:
        return None
    w_sum = sum(w for w, _ in pairs)
    return (round(sum(w * v for w, v in pairs) / w_sum, 2), round(w_sum / total_w, 4))


def delta(
    normalised: dict,
    weights: dict,
    entity: str,
    year1: int,
    year2: int,
    delta_min_common_weight: float,
    ages: dict | None = None,
) -> dict | None:
    """§4.9's frontend contract, AMENDED in v28: C = the components with a
    stored value at BOTH years whose UNDERLYING OBSERVATION YEAR differs
    between the two dates — a component resting on the same observation at
    both dates is excluded (otherwise the delta would be artificially
    damped by a term of zero that still dilutes the common weight).

    `ages` is the EMITTED sparse map (component -> entity -> year -> age,
    present only where age >= 1): obs_year = year - age, fresh when
    absent. None means no age information — every common component
    counts (the pre-v28 behaviour, kept for callers without the map).

    Refused when C is empty or the common-weight share is below
    delta_min_common_weight. Returns the delta, the share, |C| and the
    per-component decomposition (each term already divided by the common
    weight — the additive form the frontend displays)."""
    def _obs_year(key: tuple, year: int) -> int:
        if ages is None:
            return year  # no age information: treat every component as fresh
        return year - ages.get(key, {}).get(entity, {}).get(year, 0)

    common: list = []
    for key in sorted(normalised):
        s = normalised[key].get(entity, {})
        if year1 in s and year2 in s and _obs_year(key, year1) != _obs_year(key, year2):
            common.append((key, s[year1], s[year2]))
    if not common:
        return None
    total_w = sum(weights.values())
    w_common = sum(weights[k] for k, _, _ in common)
    share = w_common / total_w
    if share < delta_min_common_weight:
        return {
            "refused": True,
            "reason": "common_weight_below_threshold",
            "common_weight_share": round(share, 4),
            "n_components": len(common),
        }
    d = sum(weights[k] * (v2 - v1) for k, v1, v2 in common) / w_common
    return {
        "refused": False,
        "delta": round(d, 2),
        "common_weight_share": round(share, 4),
        "n_components": len(common),
        "decomposition": {
            f"{k[0]}/{k[1]}": round(weights[k] * (v2 - v1) / w_common, 4) for k, v1, v2 in common
        },
    }


def load_indicator_file(dist_indicators_dir: Path, indicator: str) -> dict:
    return json.loads((dist_indicators_dir / f"{indicator}.json").read_text(encoding="utf-8"))
