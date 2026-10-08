#!/usr/bin/env python3
"""verify_v28_diff.py — the v28.2 surgery's invariant checks.

Every check PASSES loud or FAILS loud. Run from the repo root:
    python scripts/verify_v28_diff.py

Baseline: the V28.1 commit (b394ea6, Ediz's own push — the reviewed
baseline of this delivery, tree-identical to the delivered d4e8ffc).
The v28.2 surgery, from the auditor's brief of 2026-10-08 (Ediz's
decision 18): (1) the official fertility bounds REGENERATED on the
worldwide canonical sample the v28.1 DYB wiring had built — the shipped
freezer alone, bounds_version 2026-10-08.1, exactly ONE block changing
(official/birth_rate_fertility/both: hi 0.611 -> 0.9903 on 2,523
observations / 177 entities); (2) the drift guard HARDENED: the freezer
records n_entities per block, and rebuild recomputes both n_sample and
n_entities live with the freezer's own sampling rule, refusing the
build beyond bounds_drift_tolerance (0.25) — the guard now trips on
the source NAME and on the sample's COVERAGE (the v28.1 blind spot:
47 -> 177 entities under the same 'canonical' name passed silently).

§2 invariants: ALL 30 non-score dist files byte-identical to V28.1 —
the surgery touches nothing outside config/ + src/ + the four score
files. The corpus is untouched (22 / 115 / 16 / 470, sha e30304cf...).

§4 the frozen bounds: exactly one block changes as above; every other
block keeps source, source_class, floor, lo, hi, n_sample,
n_unavailable (only the version moves), and n_entities appears on all
38 blocks. The modelled blocks' numbers are unchanged.

§5-§6: the MODELLED score file's normalised / scores / age maps are
value-identical to V28.1 (only the per-component bounds_version moved —
compare values, not bytes); the official score's SCORED COUNTRY-YEAR
SETS are identical at every year (no gains, no losses), while the
fertility component values and therefore the official scores change:
1,077 of the 1,093 scored official country-years' fertility components
move by more than 0.5 points (1,017 by more than 5, up to 38.3), and
970 shipped official scores move by more than 0.5 points (mean absolute
change 1.35 on the stored values — 971 / 1.36 at the reference
prototype's full-precision basis, the divergence recorded in the
changelog's Corrections; max 3.49 stored / 3.48 full-precision; 49
entities). The §5 anchors: official top-5 2015 japan 83.5 / australia
76.2 / new_zealand 73.6 / israel 73.2 / switzerland 73.1, positions
japan 1 / sweden 8 / france 22 / united_states 31 / chile 44, Russian
deltas all refused; modelled identical to V28.1.

§7: the golden vectors recomputed by an independent code path — 20
cases now: the v28 coverage kept, the official head's label carries the
live-checked DYB-only fact, and the beyond-the-old-scale case
(a scored official point whose TFR distance exceeded the v28.1 European
freeze and now reads non-zero) is present with its premise verified.

§8-§9: 416 tests collected (409 at v28.1 + 7 v28.2 tests); check-config
unchanged; the drift guard's live-vs-frozen ratios on all 38 blocks are
0.0 (the calibration — no block trips, the full margin visible); the
guard REFUSES a tampered doc live (both triggers); rebuild ×2
byte-stable across all 34 dist files; exactly ONE living score verifier
(updated in place, the V27.1 precedent).
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = "b394ea6"  # Ediz's V28.1 push — the reviewed baseline of this delivery

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

# --- 2. the 30 non-score dist files: ALL byte-identical (the surgery
# touches config/ + src/ + the four score files only) ---
base_dist = git("ls-tree", "-r", "--name-only", BASE, "data/dist/").splitlines()
nonscore_expected = [f for f in base_dist if not f.startswith("data/dist/score/")]
mismatched = [f for f in nonscore_expected if (ROOT / f).read_bytes() != _bytes_at(BASE, f)]
check(
    "ALL 30 non-score dist files byte-identical to V28.1 — the bounds "
    "regeneration reads the SAME indicator dist the v28.1 wiring emitted "
    "(birth_rate_fertility.json and catalog.json untouched THIS time)",
    len(nonscore_expected) == 30 and not mismatched,
    f"expected 30 files, 0 changed; got {len(nonscore_expected)} files; "
    f"mismatched: {mismatched}",
)
check(
    "the four score files are the ONLY dist changes (official / modelled / "
    "meta / golden_vectors)",
    sorted(
        f for f in git("ls-tree", "-r", "--name-only", BASE, "data/dist/").splitlines()
        if (ROOT / f).read_bytes() != _bytes_at(BASE, f)
    ) == [
        "data/dist/score/golden_vectors.json",
        "data/dist/score/meta.json",
        "data/dist/score/modelled.json",
        "data/dist/score/official.json",
    ],
    "",
)

cur_cat = json.loads((ROOT / "data/dist/catalog.json").read_text(encoding="utf-8"))
cur_by_id = {e["id"]: e for e in cur_cat}
check("catalog carries 27 entries (illegitimate_births among them)", len(cur_cat) == 27 and "illegitimate_births" in cur_by_id)
check(
    "illegitimate_births: still todd_core true in the catalog (decision 15 — score only)",
    cur_by_id["illegitimate_births"]["todd_core"] is True,
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
    "score.yaml: bounds_drift_tolerance: 0.25 (decision 18, v28.2 — the drift "
    "guard's refusal threshold on n_sample / n_entities)",
    _score_yaml_parsed.get("bounds_drift_tolerance") == 0.25,
    str(_score_yaml_parsed.get("bounds_drift_tolerance")),
)
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
    ScoreName,
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
_probe_bad_tol = _try_full_config(
    {"version": "probe", "bounds_drift_tolerance": 1.0,
     "components": [{"indicator": "infant_mortality", "direction": "lower",
                     "transform": "log", "sex_mode": "both", "scores": ["official"],
                     "basis": "consensus"}]}
)
_probe_neg_tol = _try_full_config(
    {"version": "probe", "bounds_drift_tolerance": -0.01,
     "components": [{"indicator": "infant_mortality", "direction": "lower",
                     "transform": "log", "sex_mode": "both", "scores": ["official"],
                     "basis": "consensus"}]}
)
check(
    "schema: bounds_drift_tolerance validated (0 <= x < 1, default 0.25 — both "
    "out-of-range probes raise: 1.0 and -0.01)",
    "bounds_drift_tolerance" in ScoreConfig.model_fields
    and ScoreConfig.model_fields["bounds_drift_tolerance"].default == 0.25
    and "bounds_drift_tolerance" in _probe_bad_tol
    and "bounds_drift_tolerance" in _probe_neg_tol,
)
check(
    "schema: illegitimate_births left the EXCLUDED set (it is a component now), "
    "still listed in OFFICIAL_ONLY with the decision-15 reason",
    "illegitimate_births" not in EXCLUDED_INDICATORS
    and "illegitimate_births" in OFFICIAL_ONLY_INDICATORS,
)

# --- 4. the frozen bounds: REGENERATED by the shipped freezer, exactly one
# block changing (decision 18) ---
old_bounds = yaml.safe_load(_bytes_at(BASE, "config/score_bounds.yaml"))
new_bounds_bytes = (ROOT / "config/score_bounds.yaml").read_bytes()
new_bounds = yaml.safe_load(new_bounds_bytes)
FIELDS = ("source", "source_class", "floor", "lo", "hi", "n_sample", "n_unavailable")
_changed_blocks = []
_problems = []
for score in ("official", "modelled"):
    for key in sorted(set(old_bounds["bounds"][score]) | set(new_bounds["bounds"][score])):
        ob = old_bounds["bounds"][score].get(key)
        nb = new_bounds["bounds"][score].get(key)
        if ob is None or nb is None:
            _problems.append(f"{score}/{key}: block added/removed")
            continue
        if any(ob.get(f) != nb.get(f) for f in FIELDS):
            _changed_blocks.append(f"{score}/{key}")
        if "n_entities" not in nb:
            _problems.append(f"{score}/{key}: n_entities MISSING")
check(
    "bounds: exactly ONE block changes its numbers — official/"
    "birth_rate_fertility/both — every other block keeps source, "
    "source_class, floor, lo, hi, n_sample, n_unavailable (only the version "
    "moves, and n_entities appears on all of them)",
    _changed_blocks == ["official/birth_rate_fertility/both"] and not _problems,
    f"changed={_changed_blocks}; problems={_problems[:4]}",
)
check(
    "bounds: 38 blocks (20 official + 18 modelled), all at 2026-10-08.1 "
    "(the freezer's own date+sequence rule — the first regeneration of the day)",
    len(new_bounds["bounds"]["official"]) == 20
    and len(new_bounds["bounds"]["modelled"]) == 18
    and {blk["bounds_version"] for score in ("official", "modelled")
         for blk in new_bounds["bounds"][score].values()} == {"2026-10-08.1"},
)
_fert_block = new_bounds["bounds"]["official"]["birth_rate_fertility/both"]
check(
    "the official fertility block reads the REGENERATED worldwide scale "
    "(canonical, floor null, lo 0.0, hi 0.9902959932984179, n_sample 2523, "
    "n_entities 177 — the anchor of the brief's Part 1)",
    _fert_block["source"] == "canonical"
    and _fert_block["source_class"] == "canonical"
    and _fert_block["floor"] is None
    and abs(_fert_block["lo"]) < 1e-12
    and _fert_block["hi"] == 0.9902959932984179
    and _fert_block["n_sample"] == 2523
    and _fert_block["n_entities"] == 177,
    str({f: _fert_block[f] for f in (*FIELDS, "n_entities")}),
)
check(
    "the MODELLED fertility block unchanged (worldbank witness, hi "
    "1.2487535788317012, n_sample 7542) — the modelled scale never moves",
    new_bounds["bounds"]["modelled"]["birth_rate_fertility/both"]["hi"] == 1.2487535788317012
    and new_bounds["bounds"]["modelled"]["birth_rate_fertility/both"]["n_sample"] == 7542
    and new_bounds["bounds"]["modelled"]["birth_rate_fertility/both"]["n_entities"] == 216,
)
check(
    "bounds meta: score_config_sha256 matches the CURRENT config/score.yaml "
    "(the tolerance key moved it) and generated is the freeze date",
    new_bounds["meta"]["score_config_sha256"]
    == hashlib.sha256((ROOT / "config/score.yaml").read_bytes()).hexdigest()
    and new_bounds["meta"]["generated"] == "2026-10-08",
    str(new_bounds["meta"].get("generated")),
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
    "meta.json: max_age_years 3 in global, bounds_drift_tolerance 0.25 (the "
    "v28.2 guard parameter, EMITTED), carry_rule described, "
    "max_obs_year 2025/2025 (the brief's anchors)",
    s_meta.get("global", {}).get("max_age_years") == 3
    and s_meta.get("global", {}).get("bounds_drift_tolerance") == 0.25
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

# --- 6. the v28.2 anchors: the modelled VALUES identical, the official
# scores re-scaled on the same scored sets (the explained difference vs a
# full-precision prototype stands: the shipped layer STORES 2-decimal
# values and aggregates those).
_old_modelled = _parse_at(BASE, "data/dist/score/modelled.json")
check(
    "modelled.json: normalised / scores / age maps VALUE-IDENTICAL to V28.1 "
    "(the modelled fertility reads the unchanged World Bank witness — only "
    "the per-component bounds_version metadata moved with the freeze)",
    _old_modelled["normalised"] == s_modelled["normalised"]
    and _old_modelled["scores"] == s_modelled["scores"]
    and _old_modelled["age"] == s_modelled["age"],
)
_meta_diffs = [
    (k, f) for k in s_modelled["components"]
    for f in s_modelled["components"][k]
    if _old_modelled["components"].get(k, {}).get(f) != s_modelled["components"][k][f]
]
check(
    "modelled.json: the ONLY component-meta change is bounds_version "
    "(2026-10-06.2 -> 2026-10-08.1) on all 18 components",
    all(f == "bounds_version" for _, f in _meta_diffs)
    and len({k for k, _ in _meta_diffs}) == 18,
    str(sorted(set(_meta_diffs))[:4]),
)
_old_official = _parse_at(BASE, "data/dist/score/official.json")
ANCHORS = {
    "official": {"scored": {2000: 21, 2005: 29, 2010: 46, 2015: 47, 2019: 42,
                            2021: 46, 2022: 47, 2023: 45, 2024: 43, 2025: 32}},
    "modelled": {"scored": {2000: 143, 2005: 159, 2010: 165, 2015: 165, 2019: 166, 2022: 163, 2025: 74}},
}
for score_name, spec in ANCHORS.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    for year, expected in spec["scored"].items():
        n = sum(1 for entity, years in scores_eq.items() if str(year) in years)
        check(f"{score_name}: scored countries {year} = {expected} (the anchor)", n == expected, f"got {n}")

# the scored country-year SETS are identical at EVERY year — no gains, no
# losses anywhere (the regeneration moves VALUES on a scale, never coverage)
_set_diffs = []
for year in range(1990, 2026):
    old_set = {e for e, ys in _old_official["scores"]["equal"].items() if str(year) in ys}
    new_set = {e for e, ys in s_official["scores"]["equal"].items() if str(year) in ys}
    if old_set != new_set:
        _set_diffs.append((year, sorted(new_set - old_set), sorted(old_set - new_set)))
check(
    "official: the scored country-year sets IDENTICAL to V28.1 at every year "
    "(the scale regeneration changes values, never who is scored)",
    not _set_diffs, str(_set_diffs[:3]),
)

# the corrections numbers (the changelog's Corrections section, on the
# SHIPPED stored values): 1,077 of 1,093 fertility components move > 0.5
# (1,017 by > 5, up to 38.3); 970 official scores move > 0.5 (mean 1.35,
# max 3.49, 49 entities) — the reference prototype's full-precision basis
# gives 971 / 1.36 / 3.48, the divergence recorded in the changelog
_o_tfr = _old_official["normalised"]["birth_rate_fertility/both"]
_n_tfr = s_official["normalised"]["birth_rate_fertility/both"]
_n_scored = sum(len(ys) for ys in s_official["scores"]["equal"].values())
_comp_moved = _comp_moved5 = 0
_comp_max = 0.0
_score_moved = 0
_score_abs = 0.0
_score_max = 0.0
_score_ents = set()
for e, ys in s_official["scores"]["equal"].items():
    for y, pair in ys.items():
        ov = _o_tfr.get(e, {}).get(y)
        nv = _n_tfr.get(e, {}).get(y)
        if ov is not None and nv is not None:
            d = abs(nv - ov)
            if d > 0.5:
                _comp_moved += 1
            if d > 5:
                _comp_moved5 += 1
            _comp_max = max(_comp_max, d)
        op = _old_official["scores"]["equal"][e][y]
        ds = abs(pair[0] - op[0])
        _score_abs += ds
        _score_max = max(_score_max, ds)
        if ds > 0.5:
            _score_moved += 1
            _score_ents.add(e)
check(
    "corrections (shipped files): 1,093 scored official country-years; "
    "1,077 fertility components move > 0.5 (1,017 by > 5, up to 38.3); "
    "970 official scores move > 0.5 (mean |change| 1.35, max 3.49, "
    "49 entities)",
    _n_scored == 1093 and _comp_moved == 1077 and _comp_moved5 == 1017
    and round(_comp_max, 1) == 38.3 and _score_moved == 970
    and round(_score_abs / _n_scored, 2) == 1.35
    and round(_score_max, 2) == 3.49 and len(_score_ents) == 49,
    f"n={_n_scored} comp>0.5={_comp_moved} comp>5={_comp_moved5} max={_comp_max:.1f} "
    f"scores>0.5={_score_moved} mean={_score_abs / _n_scored:.3f} max={_score_max:.2f} "
    f"ents={len(_score_ents)}",
)

# the fertility normalised map: same 177 entities / 3,037 keys as V28.1
# (the v28.1 wiring's map) — the VALUES re-scaled on the worldwide sample
check(
    "the official fertility normalised map: same 177 entities / 3,037 keys as "
    "V28.1 — the VALUES re-scaled (the regeneration moves the scale, not the "
    "coverage)",
    len(_n_tfr) == 177 and sum(len(v) for v in _n_tfr.values()) == 3037
    and set(_n_tfr) == set(_o_tfr),
    f"entities={len(_n_tfr)} keys={sum(len(v) for v in _n_tfr.values())}",
)

TOP5 = {
    "official": [("japan", 83.5), ("australia", 76.2), ("new_zealand", 73.6),
                 ("israel", 73.2), ("switzerland", 73.1)],
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
    "official": {"japan": 1, "sweden": 8, "france": 22, "united_states": 31,
                 "chile": 44},
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
# the measured WHY of decision 16 (v28.2: the official noise reads 0.31-0.32
# on the regenerated scale — the re-scaled fertility components move it a
# hundredth; the modelled side is untouched)
for score_name, ref_noise, ref_carried in (
    ("official", 0.31, 0.14), ("modelled", 0.34, 0.093),
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
    check(f"{score_name}: composition noise ~ {ref_noise} (the regenerated "
          "official scale moves it a hundredth at most)",
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
    "the fresh guard's measured effect: exactly 4 ghost country-years in 2025 "
    "official (costa_rica joins australia/canada/chile — fertility coverage "
    "arrived, nothing fresh did)",
    _ghosts_2025 == ["australia", "canada", "chile", "costa_rica"],
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
# v28.1: the LIVE-PICKED cases' premises hold on the emitted layer
_modelled_only = [v for v in s_golden.get("vectors", []) if "modelled-only" in v.get("why", "")]
check(
    "the modelled-only case: its entity has a modelled 2015 score and NO official "
    "2015 score (the premise, re-picked live — the US crossed the official "
    "threshold when the DYB TFR landed and can no longer carry the case)",
    len(_modelled_only) == 1
    and "2015" in s_modelled["scores"]["equal"].get(_modelled_only[0]["entity"], {})
    and "2015" not in s_official["scores"]["equal"].get(_modelled_only[0]["entity"], {}),
    str([(v["entity"], v["year"]) for v in _modelled_only]),
)
_heads = [v for v in s_golden.get("vectors", []) if "head" in v.get("why", "")]
_official_rank = sorted(
    ((ys["2015"][0], e) for e, ys in s_official["scores"]["equal"].items() if "2015" in ys),
    key=lambda t: (-t[0], t[1]),
)
check(
    "the two 2015 head cases: picked live from the emitted rankings (the official "
    "head is japan 83.54 on the regenerated worldwide scale — and its label "
    "carries the live-checked DYB-only fact; the modelled head japan 84.45 "
    "unchanged)",
    len(_heads) == 2
    and {v["score"]: v["entity"] for v in _heads} == {"modelled": "japan", "official": "japan"}
    and _official_rank[0][1] == "japan"
    and abs(_official_rank[0][0] - 83.54) <= 0.01
    and any("DYB-only entity" in v.get("why", "") for v in _heads if v["score"] == "official"),
    str([(v["score"], v["entity"], v["expected"]["score"]) for v in _heads]),
)
# v28.2: the beyond-the-old-scale case — its premise verified live: the
# fertility component reads NON-ZERO now and read 0 under the v28.1 European
# freeze (distance > 0.6109)
_btos = [v for v in s_golden.get("vectors", []) if "beyond-the-old-scale" in v.get("why", "")]
_btok = (
    (_btos[0]["entity"], str(_btos[0]["year"])) if _btos else (None, None)
)
_btok_ok = False
if _btos:
    _e, _y = _btok
    _v_new = s_official["normalised"]["birth_rate_fertility/both"].get(_e, {}).get(_y)
    _v_old = _old_official["normalised"]["birth_rate_fertility/both"].get(_e, {}).get(_y)
    _btok_ok = (
        _v_new is not None and _v_new > 0 and _v_old == 0
        and _y in s_official["scores"]["equal"].get(_e, {})
    )
check(
    "the beyond-the-old-scale case: a SCORED official point whose fertility "
    "component read 0 under the v28.1 European freeze and reads NON-ZERO on "
    "the worldwide scale (the premise verified against the emitted layer AND "
    "the V28.1 baseline)",
    len(_btos) == 1 and _btok_ok,
    str([(v["entity"], v["year"], v["expected"]["score"]) for v in _btos]),
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
    "the beyond-the-old-scale case (v28.2)": lambda v: "beyond-the-old-scale" in v.get("why", ""),
    "the DYB-only fact on the official head (v28.2)": lambda v: "DYB-only entity" in v.get("why", ""),
}
_missing_shapes = [name for name, pred in _required_shapes.items()
                   if not any(pred(v) for v in s_golden.get("vectors", []))]
check(
    "the golden set covers every required shape (the v28 additions and the "
    "two v28.2 additions included)",
    not _missing_shapes, f"missing: {_missing_shapes}",
)
check(
    "golden_vectors.json: exactly 20 cases (19 v28/v28.1 cases + the "
    "beyond-the-old-scale case)",
    s_golden.get("n") == 20 and len(s_golden.get("vectors", [])) == 20,
    str(s_golden.get("n")),
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
    "416 tests collected (409 at v28.1 + 7 v28.2 tests: the two drift-guard "
    "refusals, the boundary accept, the configurable tolerance, the tolerance "
    "schema, the freezer's n_entities, the two-collector percentile fixture)",
    n_tests == 416,
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

# --- 8b. the HARDENED drift guard, exercised live on the real config and
# dist: the calibration table (all 38 blocks live == frozen) and BOTH
# refusal triggers (a tampered doc refuses BEFORE any file is written —
# the writes happen only after the component loop completes)
from src.config_loader import load_score_config, load_todd_refs  # noqa: E402
from src.score.core import bounds_sample_counts, component_keys, select_source  # noqa: E402
from src.score.emit import BoundsDriftError, build_score_layer  # noqa: E402

_score_config = load_score_config(ROOT / "config")
_corpus = load_todd_refs(ROOT / "config")
_ratios = []
_trips = []
for _score in (ScoreName.official, ScoreName.modelled):
    _comps = {c.indicator: c for c in _score_config.components_for(_score)}
    for _key in component_keys(_score_config, _score):
        _ind_id, _sex = _key
        _comp = _comps[_ind_id]
        _ind_dist = json.loads(
            (ROOT / "data/dist/indicators" / f"{_ind_id}.json").read_text(encoding="utf-8")
        )
        _sel = select_source(_ind_dist, _sex, _score, _score_config.bounds_from_year)
        _live_s, _live_e = bounds_sample_counts(list(_sel.points), _comp.transform, _score_config)
        _blk = new_bounds["bounds"][_score.value][f"{_ind_id}/{_sex}"]
        _fs, _fe = int(_blk["n_sample"]), int(_blk["n_entities"])
        _rs = abs(_live_s - _fs) / _fs if _fs else 0.0
        _re = abs(_live_e - _fe) / _fe if _fe else 0.0
        _ratios.append(max(_rs, _re))
        if _rs > _score_config.bounds_drift_tolerance or _re > _score_config.bounds_drift_tolerance:
            _trips.append(f"{_score.value}/{_ind_id}/{_sex}")
check(
    "the guard's calibration: all 38 blocks' live-vs-frozen ratios are 0.0 "
    "(the file was regenerated on THIS dist — the full 0.25 margin stands; "
    "no block trips)",
    len(_ratios) == 38 and not _trips and all(r == 0.0 for r in _ratios),
    f"blocks={len(_ratios)} max_ratio={max(_ratios) if _ratios else None} trips={_trips}",
)

# trigger 1 (the coverage check): tamper n_entities on the fertility block
_doc_tampered = json.loads(json.dumps(new_bounds))
_doc_tampered["bounds"]["official"]["birth_rate_fertility/both"]["n_entities"] = 100
_guard1 = None
try:
    build_score_layer(_score_config, _doc_tampered, ROOT / "data/dist", ROOT / "config", _corpus)
except BoundsDriftError as e:
    _guard1 = str(e)
check(
    "guard trigger 1 (v28.2): a coverage drift beyond the tolerance REFUSES "
    "the build — the message names the score, the component, both measures' "
    "frozen and live values (n_entities frozen 100, live 177 — the tripped "
    "measure; n_sample frozen 2523, live 2523 — the agreeing one, both named) "
    "and the deliberate re-freeze prescription",
    _guard1 is not None
    and "official/birth_rate_fertility/both" in _guard1
    and "n_entities: frozen 100, live 177" in _guard1
    and "n_sample frozen 2523, live 2523" in _guard1
    and "n_entities frozen 100, live 177" in _guard1
    and "bounds_drift_tolerance" in _guard1
    and "re-freeze deliberately" in _guard1,
    (_guard1 or "NO REFUSAL — the guard is blind")[:200],
)
# trigger 2 (the source-name check, unchanged since v27): tamper the source
_doc_named = json.loads(json.dumps(new_bounds))
_doc_named["bounds"]["modelled"]["homicide_rate/both"]["source"] = "owid:WRONG"
_guard2 = None
try:
    build_score_layer(_score_config, _doc_named, ROOT / "data/dist", ROOT / "config", _corpus)
except BoundsDriftError as e:
    _guard2 = str(e)
check(
    "guard trigger 2: a frozen source-NAME change still REFUSES (the v27 "
    "check stays — both triggers run on every rebuild)",
    _guard2 is not None and "modelled/homicide_rate/both" in _guard2
    and "owid:WRONG" in _guard2,
    (_guard2 or "NO REFUSAL — the name check regressed")[:200],
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
