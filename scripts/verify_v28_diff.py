#!/usr/bin/env python3
"""verify_v28_diff.py — the v28 score-layer surgery's invariant checks.

Every check PASSES loud or FAILS loud. Run from the repo root:
    python scripts/verify_v28_diff.py

Baseline: the V27.1 commit (b2ed1c5, Ediz's own push — the audited baseline
of the v28 brief, verified live at session start; the V27.1 audit found no
discrepancy). The v28 surgery, Ediz's decisions 12-16 (2026-10-06):
directions confirmed in the books (industrial employment, tertiary
attainment, the fertility target 2.1, top income share — all basis: todd,
no provisional flag left), `illegitimate_births` joins the OFFICIAL score
only (47 entities, almost all European — the modelled side refuses it
loudly), and THE CARRY RULE: a component's value for year Y is the latest
real observation with obs_year in [Y - 3, Y], its age recorded in the new
sparse `age` maps, a score emitted only where coverage >= 0.60 AND at
least one component is fresh, no year beyond the score's max_obs_year, and
the two-year delta computed on components whose UNDERLYING OBSERVATION
differs (decision 3 amended: no interpolation — a real observation may be
carried forward, capped, labelled).

§2 invariants: the 30 non-score dist files byte-identical to V27.1 (27
indicators + catalog + entities + corpus — the indicator layer untouched,
`illegitimate_births.json` included: it was ALREADY a dist indicator, only
the score layer changed); illegitimate_births still todd_core true in the
catalog and still a corpus metric (6 books / 16 citations); corpus 22
metrics / 115 rows / 16 books / 470 citations, sha256 unchanged.

§4 the frozen bounds: regenerated (2026-10-06.2, the house date+sequence
rule — the second deliberate freeze of that day) with the 37-block
INVARIANT — for every pre-existing block, source / source_class / floor /
lo / hi / n_sample / n_unavailable are IDENTICAL to V27.1's frozen file;
only bounds_version moved; exactly ONE block added:
official/illegitimate_births/both (canonical, floor null, lo 2.2, hi
64.176, n_sample 1263). The drift guard accepts the new file (rebuild runs
clean, §9) and bounds are computed on FRESH observations only (the carry
rule never moves the scale).

§5-§6: the score files carry 20/18 components (18/16 indicators, total
weight 18/16), the age maps, meta's max_age_years / carry_rule /
max_obs_year (2025/2025), no gini or incarceration key anywhere, todd
preset totals 99/92 (illegitimate_births weight 6); every §5 anchor of the
v28 brief reproduced from the EMITTED layer (the explained difference
stays: the shipped layer STORES 2-decimal values and aggregates the stored
values; the reference prototype computes at full precision).

§7: the golden vectors recomputed by an independent code path from the
emitted normalised values AND age maps — including the amended delta rule.

§8-§9: 401 tests collected (385 at v27.1 + 16 v28 tests); check-config
prints BOTH units (18 indicators -> 20/18 components); rebuild ×2
byte-stable including the score layer; exactly ONE living score verifier
(this one — verify_v27_diff.py was git-mv'd here, the V26.1/V27.1
precedent now inverted: the name follows the surgery).
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
V271 = "b2ed1c5"  # Ediz's V27.1 push — the audited baseline

results: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def _bytes_at(ref: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{ref}:{path}"], capture_output=True, check=True
    ).stdout


def _parse_at(ref: str, path: str) -> object:
    return json.loads(_bytes_at(ref, path))


# --- 1. the score layer's files are present, one living verifier ---
for path in (
    "config/score.yaml",
    "config/score_bounds.yaml",
    "scripts/freeze_score_bounds.py",
    "src/schema/score.py",
    "src/score/__init__.py",
    "src/score/core.py",
    "src/score/emit.py",
    "tests/test_score.py",
    "data/dist/score/meta.json",
    "data/dist/score/official.json",
    "data/dist/score/modelled.json",
    "data/dist/score/golden_vectors.json",
):
    check(f"present: {path}", (ROOT / path).is_file())
check(
    "exactly one living score verifier (verify_v27_diff.py renamed by git mv)",
    (ROOT / "scripts/verify_v28_diff.py").is_file()
    and not (ROOT / "scripts/verify_v27_diff.py").exists(),
)
_tracked_verifiers = sorted(
    p for p in git("ls-files", "scripts/").splitlines() if "verify_v" in p and "archive" not in p
)
check(
    "the index tracks exactly ONE living score verifier (verify_v28_diff.py; the "
    "v27.1 name gone, the archived ones under scripts/archive/)",
    _tracked_verifiers == ["scripts/verify_v28_diff.py"],
    str(_tracked_verifiers),
)
check(
    "the v26 verifier still archived (the rename precedent's own history)",
    (ROOT / "scripts/archive/verify_v26_diff.py").is_file(),
)

# --- 2. the 30 non-score dist files byte-identical to V27.1 ---
v271_dist = git("ls-tree", "-r", "--name-only", V271, "data/dist/").splitlines()
nonscore_expected = [f for f in v271_dist if not f.startswith("data/dist/score/")]
mismatched = [f for f in nonscore_expected if (ROOT / f).read_bytes() != _bytes_at(V271, f)]
check(
    "30 non-score dist files byte-identical to V27.1 (27 indicators + catalog + entities + corpus)",
    len(nonscore_expected) == 30 and not mismatched,
    f"expected 30, got {len(nonscore_expected)}; mismatched: {mismatched}",
)
check(
    "illegitimate_births.json (the dist file) byte-identical to V27.1 — the indicator "
    "layer untouched (it was already an indicator; only the score layer changed)",
    (ROOT / "data/dist/indicators/illegitimate_births.json").read_bytes()
    == _bytes_at(V271, "data/dist/indicators/illegitimate_births.json"),
)

cur_cat = json.loads((ROOT / "data/dist/catalog.json").read_text(encoding="utf-8"))
cur_by_id = {e["id"]: e for e in cur_cat}
check("catalog carries 27 entries (illegitimate_births among them)", len(cur_cat) == 27 and "illegitimate_births" in cur_by_id)
check(
    "illegitimate_births: still todd_core true in the catalog (decision 15 — score only)",
    cur_by_id["illegitimate_births"]["todd_core"] is True,
)
old_cat = _parse_at(V271, "data/dist/catalog.json")
check(
    "catalog: every entry field-for-field IDENTICAL to V27.1 (nothing moved at the indicator layer)",
    cur_cat == old_cat,
)

corpus = json.loads((ROOT / "data/dist/todd_corpus.json").read_text(encoding="utf-8"))
meta = corpus["meta"]
check("corpus: 22 metrics", meta["metrics"] == 22, str(meta.get("metrics")))
check("corpus: 115 rows", meta["rows"] == 115, str(meta.get("rows")))
check("corpus: 16 books", meta["books"] == 16, str(meta.get("books")))
check("corpus: 470 citations", meta["total_citations"] == 470, str(meta.get("total_citations")))
check(
    "corpus: the owner's CSV sha256 unchanged",
    meta["source_csv_sha256"].startswith("e30304cf6dca"),
)
_corpus_ids = {m["id"] for m in corpus["metrics"]}
check(
    "illegitimate_births: still a corpus metric (6 books / 16 citations — the todd "
    "weight that ENTERED the official preset)",
    "illegitimate_births" in _corpus_ids
    and next(m for m in corpus["metrics"] if m["id"] == "illegitimate_births")["books"] == 6,
)

# --- 3. the config: decisions 12-16 as written, refusals loud ---
_score_yaml_parsed = yaml.safe_load((ROOT / "config/score.yaml").read_text(encoding="utf-8"))
_score_indicators = {c["indicator"] for c in _score_yaml_parsed["components"]}
check(
    "score.yaml: 18 components listed, illegitimate_births among them, "
    "gini/incarceration absent (parsed, not text-searched)",
    len(_score_yaml_parsed["components"]) == 18
    and "illegitimate_births" in _score_indicators
    and "gini_index" not in _score_indicators
    and "incarceration_rate" not in _score_indicators,
    f"n={len(_score_yaml_parsed['components'])}",
)
check("score.yaml: max_age_years: 3 (decision 16)", _score_yaml_parsed.get("max_age_years") == 3)
check(
    "score.yaml: no basis: editorial and no provisional: true left "
    "(decisions 12-14 — confirmed in the books)",
    all(c.get("basis") != "editorial" for c in _score_yaml_parsed["components"])
    and all(not c.get("provisional", False) for c in _score_yaml_parsed["components"]),
)
_ib_cfg = next(c for c in _score_yaml_parsed["components"] if c["indicator"] == "illegitimate_births")
check(
    "score.yaml: illegitimate_births official-only, direction lower, basis todd",
    _ib_cfg["scores"] == ["official"] and _ib_cfg["direction"] == "lower"
    and _ib_cfg["basis"] == "todd" and _ib_cfg["transform"] == "linear"
    and _ib_cfg["sex_mode"] == "both",
)

# the schema-level refusals, exercised live
sys.path.insert(0, str(ROOT))
from src.schema.score import (  # noqa: E402
    EXCLUDED_INDICATORS,
    OFFICIAL_ONLY_INDICATORS,
    ScoreComponent,
    ScoreConfig,
)
from pydantic import ValidationError  # noqa: E402


def _try_config(component_kwargs) -> str:
    try:
        ScoreConfig.model_validate(
            {
                "version": "probe",
                "components": [ScoreComponent.model_validate(component_kwargs)],
                "presets": ["equal"],
            }
        )
        return "accepted"
    except ValidationError as e:
        return str(e)


check(
    "schema: gini_index and incarceration_rate still refused loudly (decisions 7/11 stand)",
    "EXCLUDED" in _try_config(
        {"indicator": "gini_index", "direction": "lower", "transform": "linear",
         "sex_mode": "both", "scores": ["official"], "basis": "consensus"}
    )
    and "EXCLUDED" in _try_config(
        {"indicator": "incarceration_rate", "direction": "lower", "transform": "linear",
         "sex_mode": "both", "scores": ["official"], "basis": "consensus"}
    ),
)
check(
    "schema: illegitimate_births accepted official-only, REFUSED in the modelled "
    "score (decision 15)",
    _try_config(
        {"indicator": "illegitimate_births", "direction": "lower", "transform": "linear",
         "sex_mode": "both", "scores": ["official"], "basis": "todd"}
    ) == "accepted"
    and "OFFICIAL-SCORE-ONLY" in _try_config(
        {"indicator": "illegitimate_births", "direction": "lower", "transform": "linear",
         "sex_mode": "both", "scores": ["official", "modelled"], "basis": "todd"}
    ),
)
def _try_full_config(payload) -> str:
    try:
        ScoreConfig.model_validate(payload)
        return "accepted"
    except ValidationError as e:
        return str(e)


_probe_bad_age = _try_full_config(
    {"version": "probe", "max_age_years": -1,
     "components": [{"indicator": "infant_mortality", "direction": "lower",
                     "transform": "log", "sex_mode": "both", "scores": ["official"],
                     "basis": "consensus"}]}
)
_probe_frac_age = _try_full_config(
    {"version": "probe", "max_age_years": 1.5,
     "components": [{"indicator": "infant_mortality", "direction": "lower",
                     "transform": "log", "sex_mode": "both", "scores": ["official"],
                     "basis": "consensus"}]}
)
check(
    "schema: max_age_years validated (integer >= 0, default 3; 0 = the exact-year "
    "configuration — both refusal probes raise)",
    "max_age_years" in ScoreConfig.model_fields
    and ScoreConfig.model_fields["max_age_years"].default == 3
    and "max_age_years" in _probe_bad_age
    and "max_age_years" in _probe_frac_age,
)
check(
    "schema: illegitimate_births left the EXCLUDED set (it is a component now), "
    "still listed in OFFICIAL_ONLY with the decision-15 reason",
    "illegitimate_births" not in EXCLUDED_INDICATORS
    and "illegitimate_births" in OFFICIAL_ONLY_INDICATORS,
)

# --- 4. the frozen bounds: the 37+1-block invariant vs V27.1 ---
old_bounds = yaml.safe_load(_bytes_at(V271, "config/score_bounds.yaml"))
new_bounds = yaml.safe_load((ROOT / "config/score_bounds.yaml").read_text(encoding="utf-8"))
FIELDS = ("source", "source_class", "floor", "lo", "hi", "n_sample", "n_unavailable")
_bounds_problems = []
_preexisting = 0
_added = []
for score in ("official", "modelled"):
    ob, nb = old_bounds["bounds"][score], new_bounds["bounds"][score]
    for key, blk in nb.items():
        if key not in ob:
            _added.append(f"{score}/{key}")
            continue
        _preexisting += 1
        for f in FIELDS:
            if blk[f] != ob[key][f]:
                _bounds_problems.append(f"{score}/{key}.{f}: {ob[key][f]!r} -> {blk[f]!r}")
check(
    "bounds: 38 blocks (20 official + 18 modelled); the 37 pre-existing blocks keep "
    "the 7 fields IDENTICAL to V27.1 — only bounds_version moved",
    not _bounds_problems
    and _preexisting == 37
    and _added == ["official/illegitimate_births/both"]
    and len(new_bounds["bounds"]["official"]) == 20
    and len(new_bounds["bounds"]["modelled"]) == 18,
    f"preexisting={_preexisting}; added={_added}; problems: {'; '.join(_bounds_problems[:5])}",
)
_ib_block = new_bounds["bounds"]["official"]["illegitimate_births/both"]
check(
    "the new block: official/illegitimate_births/both — canonical, floor null, "
    "lo 2.2, hi 64.176, n_sample 1263 (the brief's anchor at 4 decimals)",
    _ib_block["source"] == "canonical"
    and _ib_block["source_class"] == "canonical"
    and _ib_block["floor"] is None
    and abs(_ib_block["lo"] - 2.2) < 1e-9
    and abs(round(_ib_block["hi"], 4) - 64.176) < 1e-9
    and _ib_block["n_sample"] == 1263
    and _ib_block["n_unavailable"] == 0,
    str({f: _ib_block[f] for f in FIELDS}),
)
check(
    "bounds_version bumped (2026-10-06.1 -> 2026-10-06.2, the house date+sequence "
    "rule — the second deliberate freeze of that day)",
    new_bounds["meta"]["bounds_version"] == "2026-10-06.2"
    and old_bounds["meta"]["bounds_version"] == "2026-10-06.1",
    str(new_bounds["meta"].get("bounds_version")),
)
_all_block_versions = {
    blk["bounds_version"]
    for score in ("official", "modelled")
    for blk in new_bounds["bounds"][score].values()
}
check(
    "every block carries the new bounds_version (the freezer is the only writer)",
    _all_block_versions == {"2026-10-06.2"},
    str(_all_block_versions),
)

# --- 5. the score files: parse, size cap, contract ---
score_dir = ROOT / "data/dist/score"
SIZE_CAP = 8 * 1024 * 1024
docs = {}
for f in sorted(score_dir.glob("*.json")):
    size = f.stat().st_size
    try:
        docs[f.name] = json.loads(f.read_text(encoding="utf-8"))
        parsed = True
    except json.JSONDecodeError:
        parsed = False
    check(f"{f.name}: parses, {size} bytes under the ~8MB cap", parsed and size < SIZE_CAP)

s_meta = docs.get("meta.json", {})
s_official = docs.get("official.json", {})
s_modelled = docs.get("modelled.json", {})
s_golden = docs.get("golden_vectors.json", {})
check("meta.json: derived: true, the honest notice (the carry rule is NOT interpolation)",
      s_meta.get("derived") is True and "carry rule" in s_meta.get("notice", ""))
check(
    "meta.json: fingerprints match the actual config files",
    s_meta.get("fingerprints", {}).get("score_yaml_sha256", "")
    == hashlib.sha256((ROOT / "config/score.yaml").read_bytes()).hexdigest()
    and s_meta.get("fingerprints", {}).get("score_bounds_yaml_sha256", "")
    == hashlib.sha256((ROOT / "config/score_bounds.yaml").read_bytes()).hexdigest(),
)
check(
    "meta.json: max_age_years 3 in global, carry_rule described, "
    "max_obs_year 2025/2025 (the brief's anchors)",
    s_meta.get("global", {}).get("max_age_years") == 3
    and bool(s_meta.get("carry_rule"))
    and s_meta.get("max_obs_year") == {"official": 2025, "modelled": 2025},
    str(s_meta.get("max_obs_year")),
)
check(
    "meta.json: the excluded map still carries gini/incarceration with their reasons, "
    "and illegitimate_births LEFT it (a component now)",
    "gini_index" in s_meta.get("excluded", {})
    and "incarceration_rate" in s_meta.get("excluded", {})
    and "illegitimate_births" not in s_meta.get("excluded", {}),
)
check(
    "official.json: 20 components / modelled.json: 18 components",
    len(s_official.get("components", {})) == 20 and len(s_modelled.get("components", {})) == 18,
)
_absent_keys = []
for doc_name, doc in (("official", s_official), ("modelled", s_modelled)):
    for section in ("components", "normalised", "age"):
        for key in doc.get(section, {}):
            if "incarceration" in key or "gini" in key:
                _absent_keys.append((doc_name, section, key))
    for preset, weights in s_meta.get("presets", {}).get(doc_name, {}).items():
        for key in weights:
            if "incarceration" in key or "gini" in key:
                _absent_keys.append((doc_name, preset, key))
check(
    "gini/incarceration absent from components, normalised, age and BOTH presets of both scores",
    not _absent_keys, str(_absent_keys[:5]),
)
check(
    "illegitimate_births/both: present in official's components, normalised and age; "
    "ABSENT from the modelled file entirely",
    "illegitimate_births/both" in s_official.get("components", {})
    and "illegitimate_births/both" in s_official.get("normalised", {})
    and "illegitimate_births/both" in s_official.get("age", {})
    and "illegitimate_births" not in json.dumps(s_modelled),
)
_bases = {c.get("basis") for c in s_meta.get("components", {}).values()}
_provisional = [k for k, c in s_meta.get("components", {}).items() if c.get("provisional")]
check(
    "every emitted component carries basis in {todd, consensus}, none provisional "
    "(decisions 12-15)",
    _bases <= {"todd", "consensus"} and not _provisional,
    f"bases={sorted(_bases)} provisional={_provisional}",
)
_eq_totals = {
    f"{s}/{p}": round(sum(w.values()), 1)
    for s, presets in s_meta.get("presets", {}).items()
    for p, w in presets.items()
}
check(
    "preset totals: equal 18/16 (the official score gained the 18th indicator), "
    "todd 99/92 (V27.1's 93/92 + illegitimate_births' 6 books)",
    _eq_totals.get("official/equal") == 18.0 and _eq_totals.get("modelled/equal") == 16.0
    and _eq_totals.get("official/todd") == 99.0 and _eq_totals.get("modelled/todd") == 92.0,
    str(_eq_totals),
)
check(
    "todd weight of illegitimate_births = 6 (the corpus's book count, read live)",
    s_meta.get("presets", {}).get("official", {}).get("todd", {}).get("illegitimate_births/both") == 6.0,
)
_bad_range = []
for score_doc in (s_official, s_modelled):
    for key, series in score_doc.get("normalised", {}).items():
        for entity, years in series.items():
            for year, v in years.items():
                if not (0.0 <= v <= 100.0):
                    _bad_range.append((key, entity, year, v))
check("every stored normalised value in [0, 100]", not _bad_range, str(_bad_range[:3]))


def _fresh_from_ages(doc, entity, year):
    """Any available component fresh at (entity, year)? absent from the age
    map = fresh — the emitted contract."""
    for key, series in doc.get("age", {}).items():
        if year in series.get(entity, {}):
            continue
        if year in doc["normalised"].get(key, {}).get(entity, {}):
            return True
    return False


_below = []
_ghosts = []
for score_doc in (s_official, s_modelled):
    for preset, entities in score_doc.get("scores", {}).items():
        for entity, years in entities.items():
            for year, pair in years.items():
                if pair[1] < 0.60:
                    _below.append((preset, entity, year, pair[1]))
                if not _fresh_from_ages(score_doc, entity, year):
                    _ghosts.append((preset, entity, year))
check(
    "every emitted score: coverage >= 0.60 AND at least one fresh component "
    "(the ghost guard, recomputed from the age maps)",
    not _below and not _ghosts,
    f"below={_below[:3]} ghosts={_ghosts[:3]}",
)
_max_years = {
    doc_name: max(
        (int(y) for series in doc.get("normalised", {}).values()
         for ys in series.values() for y in ys),
        default=None,
    )
    for doc_name, doc in (("official", s_official), ("modelled", s_modelled))
}
check(
    "no emitted score year beyond the score's max_obs_year (2025/2025)",
    _max_years == {"official": 2025, "modelled": 2025}
    and s_meta.get("max_obs_year") == {"official": 2025, "modelled": 2025},
    str(_max_years),
)
_age_bad = []
for doc_name, doc in (("official", s_official), ("modelled", s_modelled)):
    for key, series in doc.get("age", {}).items():
        for entity, years in series.items():
            for year, age in years.items():
                y = int(year)
                if not (1 <= age <= 3):
                    _age_bad.append((doc_name, key, entity, year, age))
                # consistency: the resolved value equals the value at obs_year
                obs = y - age
                if doc["normalised"][key][entity][year] != doc["normalised"][key][entity].get(str(obs)):
                    _age_bad.append((doc_name, key, entity, year, "value-mismatch"))
check(
    "the age maps are sparse (1 <= age <= 3) and every carried value equals the "
    "value at its observation year",
    not _age_bad, str(_age_bad[:5]),
)

# the direction agreement, live on the real configs (the drift test)
score_yaml_text = (ROOT / "config/score.yaml").read_text(encoding="utf-8")
_disagreements = []
for eid, entry in cur_by_id.items():
    m = re.search(rf"^\s*- indicator: {re.escape(eid)}\n\s+direction: (\w+)", score_yaml_text, re.M)
    if m and m.group(1) in ("higher", "lower"):
        if entry["higher_is_better"] != (m.group(1) == "higher"):
            _disagreements.append(eid)
check(
    "zero disagreement between higher_is_better and the score direction "
    "(fertility, a target, excluded)",
    not _disagreements, str(_disagreements),
)

# --- 6. the v28 brief's §5 anchors, recomputed from the EMITTED layer ---
# The explained difference vs the reference prototype: the shipped layer
# STORES 2-decimal values and computes aggregates from the stored values;
# the prototype computes at full precision. Counts are exact; scores and
# deltas within the rounding tail.
ANCHORS = {
    "official": {"scored": {2000: 21, 2005: 29, 2010: 40, 2015: 42, 2019: 40, 2022: 41, 2025: 32}},
    "modelled": {"scored": {2000: 143, 2005: 159, 2010: 165, 2015: 165, 2019: 166, 2022: 163, 2025: 74}},
}
for score_name, spec in ANCHORS.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    for year, expected in spec["scored"].items():
        n = sum(1 for entity, years in scores_eq.items() if str(year) in years)
        check(f"{score_name}: scored countries {year} = {expected} (the anchor)", n == expected, f"got {n}")

TOP5 = {
    "official": [("australia", 75.5), ("israel", 74.3), ("canada", 72.3),
                 ("switzerland", 72.0), ("new_zealand", 71.6)],
    "modelled": [("japan", 84.4), ("singapore", 80.2), ("norway", 78.3),
                 ("israel", 77.3), ("australia", 77.1)],
}
for score_name, expected5 in TOP5.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    ranked = sorted(
        ((years["2015"][0], entity) for entity, years in scores_eq.items() if "2015" in years),
        reverse=True,
    )[:5]
    ok = all(e == be and abs(s - bs) <= 0.15 for (s, e), (be, bs) in zip(ranked, expected5))
    check(f"{score_name}: 2015 top-5 within the rounding tail of the reference", ok,
          f"got {[(e, round(s, 1)) for s, e in ranked]} vs {expected5}")

POSITIONS = {
    "modelled": {"japan": 1, "france": 30, "united_states": 46, "china": 9,
                 "russian_federation": 85, "chile": 70, "sweden": 14},
    "official": {"france": 17, "chile": 39, "sweden": 6},
}
for score_name, spec in POSITIONS.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    ranked = [e for _, e in sorted(
        ((years["2015"][0], entity) for entity, years in scores_eq.items() if "2015" in years),
        reverse=True,
    )]
    for entity, expected in spec.items():
        got = ranked.index(entity) + 1 if entity in ranked else None
        check(f"{score_name}: 2015 position of {entity} = {expected}", got == expected, f"got {got}")

# the Russian deltas under the AMENDED rule (same-observation components
# excluded; obs_year = year - age, fresh when absent from the age map)


def _recompute_delta(doc, entity, y1, y2, preset="equal"):
    score_name = "official" if doc is s_official else "modelled"
    weights = s_meta["presets"][score_name][preset]
    norm = doc["normalised"]
    ages = doc.get("age", {})

    def _obs_year(key, year):
        return year - ages.get(key, {}).get(entity, {}).get(str(year), 0)

    common = []
    for key, series in norm.items():
        a = series.get(entity, {}).get(str(y1))
        b = series.get(entity, {}).get(str(y2))
        if a is not None and b is not None and _obs_year(key, y1) != _obs_year(key, y2):
            common.append((weights[key], a, b))
    if not common:
        return None
    total = sum(weights.values())
    w_common = sum(w for w, _, _ in common)
    d = sum(w * (b - a) for w, a, b in common) / w_common
    return round(d, 1), round(w_common / total, 2), len(common)


for y1, y2, bd, bs, bn in ((1995, 2000, -4.6, 0.56, 10), (2000, 2010, 8.8, 0.69, 13), (2010, 2019, 8.1, 0.75, 14)):
    got = _recompute_delta(s_modelled, "russian_federation", y1, y2)
    ok = got is not None and abs(got[0] - bd) <= 0.15 and abs(got[1] - bs) <= 0.02 and got[2] == bn
    check(f"modelled: Russia {y1}->{y2} delta {bd} ({bs}, {bn}) — the AMENDED rule",
          ok, f"got {got}")
for y1, y2, bs in ((1995, 2000, 0.22), (2000, 2010, 0.22), (2010, 2019, 0.33)):
    got = _recompute_delta(s_official, "russian_federation", y1, y2)
    check(f"official: Russia {y1}->{y2} REFUSED (common weight {bs} < 0.50)",
          got is not None and got[1] < 0.50 and got[1] == bs, f"got {got}")

# composition noise (mean points per year, 2000-2020) and carried share —
# the measured WHY of decision 16
for score_name, ref_noise, ref_carried in (
    ("official", 0.33, 0.135), ("modelled", 0.34, 0.093),
):
    doc = s_official if score_name == "official" else s_modelled
    weights = s_meta["presets"][score_name]["equal"]
    norm = doc["normalised"]
    sc = doc["scores"]["equal"]
    gaps = []
    for e, ys in sc.items():
        for y_str, (s, _cov) in ys.items():
            y = int(y_str)
            if 2000 <= y <= 2020 and str(y + 1) in ys:
                com = [k for k in norm if str(y) in norm[k].get(e, {}) and str(y + 1) in norm[k].get(e, {})]
                wc = sum(weights[k] for k in com)
                dc = sum(weights[k] * (norm[k][e][str(y + 1)] - norm[k][e][str(y)]) for k in com) / wc
                gaps.append(abs((ys[str(y + 1)][0] - s) - dc))
    noise = round(sum(gaps) / len(gaps), 2) if gaps else None
    check(f"{score_name}: composition noise ~ {ref_noise} (V27.1 exact-year: "
          f"{'0.86' if score_name == 'official' else '0.95'})",
          noise is not None and abs(noise - ref_noise) <= 0.02, f"got {noise}")
    carried = sum(
        1 for e, ys in sc.items() for y_str in ys
        for k in norm
        if y_str in norm[k].get(e, {}) and y_str in doc.get("age", {}).get(k, {}).get(e, {})
    )
    total = sum(1 for e, ys in sc.items() for y_str in ys for k in norm if y_str in norm[k].get(e, {}))
    share = round(carried / total, 3) if total else None
    check(f"{score_name}: carried value share ~ {ref_carried}", share == ref_carried, f"got {share}")

# the fresh guard's measured effect: 3 ghost country-years in 2025, official
w_off = s_meta["presets"]["official"]["equal"]
total_off = sum(w_off.values())
_by_ey = {}
for k, series in s_official["normalised"].items():
    for e, ys in series.items():
        for y_str in ys:
            _by_ey[(e, y_str)] = _by_ey.get((e, y_str), 0.0) + w_off[k]
_ghosts_2025 = sorted(
    e for (e, y_str), wsum in _by_ey.items()
    if y_str == "2025" and wsum / total_off >= 0.60
    and "2025" not in s_official["scores"]["equal"].get(e, {})
)
check(
    "the fresh guard's measured effect: exactly 3 ghost country-years in 2025 "
    "official (coverage >= 0.60, nothing fresh)",
    _ghosts_2025 == ["australia", "canada", "chile"],
    str(_ghosts_2025),
)

# --- 7. the golden vectors, recomputed by an independent path ---
n_vec = s_golden.get("n", 0)
check("golden_vectors.json: <= 20 cases", 0 < n_vec <= 20, str(n_vec))
_golden_fail = []
for vec in s_golden.get("vectors", []):
    score_name = vec["score"]
    doc = s_official if score_name == "official" else s_modelled
    preset = vec["preset"]
    weights = s_meta["presets"][score_name][preset]
    norm = doc["normalised"]
    ages = doc.get("age", {})
    entity = vec["entity"]
    if "year" in vec:  # a score/coverage case
        year = str(vec["year"])
        pairs = [
            (weights[key], series.get(entity, {}).get(year))
            for key, series in norm.items()
            if series.get(entity, {}).get(year) is not None
        ]
        w_sum = sum(w for w, _ in pairs)
        total = sum(weights.values())
        score = round(sum(w * v for w, v in pairs) / w_sum, 2)
        coverage = round(w_sum / total, 4)
        exp = vec["expected"]
        if abs(score - exp["score"]) > 0.005 or abs(coverage - exp["coverage"]) > 0.0001:
            _golden_fail.append((score_name, entity, year, "score/coverage"))
        # the emission rule mirrored: coverage >= 0.60 AND fresh
        emitted = year in doc.get("scores", {}).get(preset, {}).get(entity, {})
        if emitted != (coverage >= 0.60 and _fresh_from_ages(doc, entity, year)):
            _golden_fail.append((score_name, entity, year, "emission-rule"))
    if "years" in vec:  # a delta case — the AMENDED rule
        y1, y2 = (str(y) for y in vec["years"])
        exp = vec["expected"]["delta"]

        def _oy(key, year):
            return int(year) - ages.get(key, {}).get(entity, {}).get(year, 0)

        common = [
            (weights[key], series.get(entity, {}).get(y1), series.get(entity, {}).get(y2))
            for key, series in norm.items()
            if series.get(entity, {}).get(y1) is not None
            and series.get(entity, {}).get(y2) is not None
            and _oy(key, y1) != _oy(key, y2)
        ]
        if not common:
            _golden_fail.append((score_name, entity, vec["years"], "empty-common"))
            continue
        total = sum(weights.values())
        w_common = sum(w for w, _, _ in common)
        if exp.get("refused") is True:
            if not w_common / total < 0.50:
                _golden_fail.append((score_name, entity, vec["years"], "should-refuse"))
        else:
            d = round(sum(w * (b - a) for w, a, b in common) / w_common, 2)
            if abs(d - exp["delta"]) > 0.005:
                _golden_fail.append((score_name, entity, vec["years"], "delta"))
check(
    "every golden vector recomputed from the emitted values AND age maps "
    "(independent path, the amended delta rule)",
    not _golden_fail, str(_golden_fail[:5]),
)
_just_below = [v for v in s_golden.get("vectors", []) if "just-below" in v.get("why", "")]
check(
    "the coverage-just-below vector present with coverage in [0.55, 0.60) and NOT emitted",
    len(_just_below) == 1 and 0.55 <= _just_below[0]["expected"]["coverage"] < 0.60,
    str([(v["entity"], v["year"], v["expected"]["coverage"]) for v in _just_below]),
)
_required_shapes = {
    "the refused delta": lambda v: "years" in v and v["expected"]["delta"].get("refused"),
    "a todd-preset case": lambda v: v.get("preset") == "todd",
    "a split-sex case": lambda v: "split-sex" in v.get("why", ""),
    "a log case": lambda v: "log component" in v.get("why", ""),
    "a target case": lambda v: "target component" in v.get("why", ""),
    "a carried-component case (age >= 1)": lambda v: "carried-component" in v.get("why", ""),
    "a same-observation-exclusion delta": lambda v: "amended delta" in v.get("why", ""),
    "a right-edge case (2022 carried)": lambda v: "right-edge" in v.get("why", ""),
    "an illegitimate_births official case": lambda v: "illegitimate_births case" in v.get("why", ""),
    "a ghost-guard case (not emitted)": lambda v: "ghost-guard" in v.get("why", ""),
}
_missing_shapes = [name for name, pred in _required_shapes.items()
                   if not any(pred(v) for v in s_golden.get("vectors", []))]
check(
    "the golden set covers every required shape (the v28 additions included)",
    not _missing_shapes, f"missing: {_missing_shapes}",
)

# --- 8. tests + config state (the self-diagnosing count check, v26.1.1) ---
test_count = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only"],
    capture_output=True, text=True, cwd=str(ROOT),
)
n_tests = None
for _s in (l.strip() for l in test_count.stdout.splitlines()):
    _m = (
        re.match(r"^(\d+) tests? collected", _s)
        or re.match(r"^(\d+) tests? selected", _s)
        or re.match(r"^collected (\d+) items", _s)
    )
    if _m:
        n_tests = int(_m.group(1))
        break
    if _s.endswith("collected") and _s.split() and _s.split()[0].isdigit():
        n_tests = int(_s.split()[0])
        break
if n_tests is None:
    _ids = [l for l in test_count.stdout.splitlines() if "::" in l and not l.lstrip().startswith("=")]
    if _ids:
        n_tests = len(_ids)
_diag = [f"returncode={test_count.returncode}"]
_diag += [f"stdout: {_s}" for _s in map(str.strip, test_count.stdout.splitlines()[-4:]) if _s][:3]
_diag += [f"stderr: {_s}" for _s in map(str.strip, test_count.stderr.splitlines()[-4:]) if _s][:3]
check(
    "401 tests collected (385 at v27.1 + 16 v28 tests: the carry rule, the amended "
    "delta, the bounds' independence, decisions 12-15)",
    n_tests == 401,
    f"parsed={n_tests}; " + " | ".join(_diag),
)
cfg = subprocess.run(
    [sys.executable, "-m", "src.cli", "check-config"], capture_output=True, text=True, cwd=str(ROOT)
)
check(
    "cli check-config: 27 indicators, corpus 22/470, score layer in BOTH units "
    "(18 indicators -> 20/18 components, frozen)",
    "OK: 27 indicator(s)" in cfg.stdout
    and "todd corpus: 22 metrics, 470 citations" in cfg.stdout
    and "score layer: 18 indicators (18 official / 16 modelled), 20/18 components" in cfg.stdout
    and "(frozen)" in cfg.stdout,
    cfg.stdout.splitlines()[0] if cfg.stdout else cfg.stderr[:120],
)

# --- 9. rebuild ×2 byte-stability, INCLUDING the score layer ---


def _dist_md5s() -> dict:
    return {
        str(f.relative_to(ROOT)): hashlib.md5(f.read_bytes()).hexdigest()
        for f in sorted((ROOT / "data/dist").rglob("*.json"))
    }


before = _dist_md5s()
rc1 = subprocess.run([sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
                     capture_output=True, text=True)
after1 = _dist_md5s()
rc2 = subprocess.run([sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
                     capture_output=True, text=True)
after2 = _dist_md5s()
check(
    "rebuild ×2: all dist files byte-stable (34 files incl. the score layer with "
    "the carry rule)",
    rc1.returncode == 0 and rc2.returncode == 0
    and before == after1 == after2 and len(after2) == 34,
    f"n={len(after2)}; rc1={rc1.returncode} rc2={rc2.returncode}; "
    f"drift1={[k for k in after1 if after1[k] != before.get(k)][:3]} "
    f"drift2={[k for k in after2 if after2[k] != after1.get(k)][:3]}",
)
check(
    "rebuild prints the score layer line (official 20 / modelled 18, carry <= 3y, "
    "max_obs_year 2025/2025, frozen)",
    "Score layer ->" in rc1.stdout and "official 20 / modelled 18" in rc1.stdout
    and "carry <= 3y" in rc1.stdout and "max_obs_year 2025/2025" in rc1.stdout,
    rc1.stdout.strip().splitlines()[-1] if rc1.stdout else rc1.stderr[:120],
)

# --- report ---
print()
n_pass = sum(1 for _, ok, _ in results if ok)
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{n_pass}/{len(results)} PASS")
sys.exit(0 if n_pass == len(results) else 1)
