#!/usr/bin/env python3
"""verify_v27_diff.py — the v27.1 score-layer surgery's invariant checks.

Every check PASSES loud or FAILS loud. Run from the repo root:
    python scripts/verify_v27_diff.py

Baseline: the V27 commit (1275886, Ediz's own push — tree-identical to the
delivered 5f4d9b0, verified live). The v27.1 surgery: `incarceration_rate`
LEAVES THE SCORE ONLY (Ediz's decision 11 — no defensible monotone
direction; it stays an indicator, todd_core true, in the catalog, in the
corpus, on the site, exactly the Gini's treatment) plus the v27 audit's
four text fixes (cadence cause withdrawn, Gini facts restated neutrally,
the cli's indicators/components units, the golden-vector labels regenerated
from live readings).

§2 invariants: the 30 non-score dist files byte-identical to V27 (27
indicators + catalog + entities + corpus — the indicator layer untouched,
`incarceration_rate.json` included); incarceration still todd_core true in
the catalog and still a corpus metric; corpus 22 metrics / 115 rows / 16
books / 470 citations, sha256 unchanged.

§4 the frozen bounds: regenerated (2026-10-06.1) with the 37-block
INVARIANT — for every remaining block, source / source_class / floor /
lo / hi / n_sample / n_unavailable are IDENTICAL to V27's frozen file;
only bounds_version moved; both incarceration blocks gone. The drift
guard accepts the new file (rebuild runs clean, §9) and still refuses a
stale one (the unit test).

§5-§6: the score files carry 19/18 components (17/16 indicators, total
weight 17/16), no incarceration key anywhere, the todd preset totals
93/92 (fertility 16 of 93 official); every §4 anchor of the v27.1 brief
reproduced from the EMITTED layer (the explained difference stays: the
shipped layer STORES 2-decimal values and aggregates the stored values).

§7: the golden vectors recomputed by an independent code path; the
just-below case RE-PICKED live (the v27 Afghanistan-2004 case is invalid
under the 16 total weight and must not survive).

§8-§9: 385 tests collected (384 at v27 + the incarceration-refusal test);
check-config prints BOTH units (17 indicators -> 19/18 components);
rebuild ×2 byte-stable including the score layer.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
V27 = "1275886"  # Ediz's V27 push — the audited baseline

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


# --- 1. the score layer's files are present, the v26 archive intact ---
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
    "the v26 verifier still archived (no move in v27.1 — the verifier was updated in place)",
    (ROOT / "scripts/archive/verify_v26_diff.py").is_file()
    and not (ROOT / "scripts/verify_v26_diff.py").exists(),
)

# --- 2. the 30 non-score dist files byte-identical to V27 ---
v27_dist = git("ls-tree", "-r", "--name-only", V27, "data/dist/").splitlines()
nonscore_expected = [f for f in v27_dist if not f.startswith("data/dist/score/")]
mismatched = [f for f in nonscore_expected if (ROOT / f).read_bytes() != _bytes_at(V27, f)]
check(
    "30 non-score dist files byte-identical to V27 (27 indicators + catalog + entities + corpus)",
    len(nonscore_expected) == 30 and not mismatched,
    f"expected 30, got {len(nonscore_expected)}; mismatched: {mismatched}",
)
check(
    "incarceration_rate.json (the dist file) byte-identical to V27 — the indicator layer untouched",
    (ROOT / "data/dist/indicators/incarceration_rate.json").read_bytes()
    == _bytes_at(V27, "data/dist/indicators/incarceration_rate.json"),
)

cur_cat = json.loads((ROOT / "data/dist/catalog.json").read_text(encoding="utf-8"))
cur_by_id = {e["id"]: e for e in cur_cat}
check("catalog carries 27 entries (incarceration among them)", len(cur_cat) == 27 and "incarceration_rate" in cur_by_id)
check(
    "incarceration_rate: still todd_core true in the catalog (decision 11 — score only)",
    cur_by_id["incarceration_rate"]["todd_core"] is True,
)
check(
    "incarceration_rate's catalog higher_is_better still false (predates decision 11; "
    "the score endorses no direction for it — the contract's frontend note)",
    cur_by_id["incarceration_rate"]["higher_is_better"] is False,
)
old_cat = _parse_at(V27, "data/dist/catalog.json")
old_by_id = {e["id"]: e for e in old_cat}
check(
    "catalog: every entry field-for-field IDENTICAL to V27 (nothing moved at the indicator layer)",
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
    "incarceration_rate: still a corpus metric (3 books / 3 citations — the todd weight "
    "that left the preset)",
    "incarceration_rate" in _corpus_ids
    and next(m for m in corpus["metrics"] if m["id"] == "incarceration_rate")["books"] == 3,
)

# --- 3. the config refuses incarceration, loudly ---
_score_yaml_parsed = yaml.safe_load((ROOT / "config/score.yaml").read_text(encoding="utf-8"))
_score_indicators = {c["indicator"] for c in _score_yaml_parsed["components"]}
check(
    "score.yaml: 17 components listed, incarceration_rate absent (parsed, not text-searched)",
    len(_score_yaml_parsed["components"]) == 17 and "incarceration_rate" not in _score_indicators,
    f"n={len(_score_yaml_parsed['components'])}",
)

# --- 4. the frozen bounds: the 37-block invariant vs V27 ---
old_bounds = yaml.safe_load(_bytes_at(V27, "config/score_bounds.yaml"))
new_bounds = yaml.safe_load((ROOT / "config/score_bounds.yaml").read_text(encoding="utf-8"))
FIELDS = ("source", "source_class", "floor", "lo", "hi", "n_sample", "n_unavailable")
_bounds_problems = []
for score in ("official", "modelled"):
    ob, nb = old_bounds["bounds"][score], new_bounds["bounds"][score]
    if f"incarceration_rate/both" in nb:
        _bounds_problems.append(f"{score}: incarceration block still frozen")
    for key, blk in nb.items():
        if key not in ob:
            _bounds_problems.append(f"{score}/{key}: not in V27's file")
            continue
        for f in FIELDS:
            if blk[f] != ob[key][f]:
                _bounds_problems.append(f"{score}/{key}.{f}: {ob[key][f]!r} -> {blk[f]!r}")
check(
    "bounds: 37 blocks (19 official + 18 modelled), the 7 fields IDENTICAL to V27 "
    "for every block — only bounds_version moved",
    not _bounds_problems
    and len(new_bounds["bounds"]["official"]) == 19
    and len(new_bounds["bounds"]["modelled"]) == 18,
    "; ".join(_bounds_problems[:5]),
)
check(
    "bounds_version bumped (2026-10-05.1 -> 2026-10-06.1, the house date+sequence format)",
    new_bounds["meta"]["bounds_version"] == "2026-10-06.1"
    and old_bounds["meta"]["bounds_version"] == "2026-10-05.1",
    str(new_bounds["meta"].get("bounds_version")),
)
_all_block_versions = {
    blk["bounds_version"]
    for score in ("official", "modelled")
    for blk in new_bounds["bounds"][score].values()
}
check(
    "every block carries the new bounds_version (the freezer is the only writer)",
    _all_block_versions == {"2026-10-06.1"},
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
check("meta.json: derived: true, the honest notice", s_meta.get("derived") is True)
check(
    "meta.json: fingerprints match the actual config files",
    s_meta.get("fingerprints", {}).get("score_yaml_sha256", "")
    == hashlib.sha256((ROOT / "config/score.yaml").read_bytes()).hexdigest()
    and s_meta.get("fingerprints", {}).get("score_bounds_yaml_sha256", "")
    == hashlib.sha256((ROOT / "config/score_bounds.yaml").read_bytes()).hexdigest(),
)
check(
    "meta.json: the excluded map carries incarceration_rate with the decision-11 reason",
    "incarceration_rate" in s_meta.get("excluded", {})
    and "decision 11" in s_meta["excluded"]["incarceration_rate"],
    str(s_meta.get("excluded", {}).get("incarceration_rate"))[:80],
)
check(
    "official.json: 19 components / modelled.json: 18 components",
    len(s_official.get("components", {})) == 19 and len(s_modelled.get("components", {})) == 18,
)
_inc_keys = []
for doc_name, doc in (("official", s_official), ("modelled", s_modelled)):
    for section in ("components", "normalised"):
        for key in doc.get(section, {}):
            if "incarceration" in key:
                _inc_keys.append((doc_name, section, key))
    for preset, weights in s_meta.get("presets", {}).get(doc_name, {}).items():
        for key in weights:
            if "incarceration" in key:
                _inc_keys.append((doc_name, preset, key))
check(
    "incarceration_rate absent from components, normalised and BOTH presets of both scores",
    not _inc_keys, str(_inc_keys[:5]),
)
_eq_totals = {
    f"{s}/{p}": round(sum(w.values()), 1)
    for s, presets in s_meta.get("presets", {}).items()
    for p, w in presets.items()
}
check(
    "preset totals: equal 17/16 (indicators), todd 93/92 (V27's 96/95 minus the weight 3)",
    _eq_totals.get("official/equal") == 17.0 and _eq_totals.get("modelled/equal") == 16.0
    and _eq_totals.get("official/todd") == 93.0 and _eq_totals.get("modelled/todd") == 92.0,
    str(_eq_totals),
)
_bad_range = []
for score_doc in (s_official, s_modelled):
    for key, series in score_doc.get("normalised", {}).items():
        for entity, years in series.items():
            for year, v in years.items():
                if not (0.0 <= v <= 100.0):
                    _bad_range.append((key, entity, year, v))
check("every stored normalised value in [0, 100]", not _bad_range, str(_bad_range[:3]))
_below = []
for score_doc in (s_official, s_modelled):
    for preset, entities in score_doc.get("scores", {}).items():
        for entity, years in entities.items():
            for year, pair in years.items():
                if pair[1] < 0.60:
                    _below.append((preset, entity, year, pair[1]))
check(
    "every emitted score carries coverage >= 0.60 (the threshold rule)",
    not _below, str(_below[:3]),
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

# --- 6. the v27.1 brief's §4 anchors, recomputed from the EMITTED layer ---
# The explained difference vs the reference prototype: the shipped layer
# STORES 2-decimal values and computes aggregates from the stored values;
# the prototype computes at full precision. Counts are exact; scores and
# deltas within the rounding tail.
ANCHORS = {
    "official": {"scored": {2000: 3, 2005: 18, 2010: 32, 2015: 37, 2019: 32, 2022: 33}},
    "modelled": {"scored": {2000: 124, 2005: 139, 2010: 151, 2015: 141, 2019: 140, 2022: 71}},
}
for score_name, spec in ANCHORS.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    for year, expected in spec["scored"].items():
        n = sum(1 for entity, years in scores_eq.items() if str(year) in years)
        check(f"{score_name}: scored countries {year} = {expected} (the anchor)", n == expected, f"got {n}")

TOP5 = {
    "official": [("australia", 74.7), ("czechia", 73.7), ("sweden", 72.9),
                 ("canada", 72.3), ("switzerland", 71.4)],
    "modelled": [("japan", 85.2), ("singapore", 81.0), ("israel", 79.0),
                 ("qatar", 78.8), ("kuwait", 78.6)],
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

# the Russian deltas: modelled accepted within rounding, official refused


def _recompute_delta(doc, entity, y1, y2, preset="equal"):
    score_name = "official" if doc is s_official else "modelled"
    weights = s_meta["presets"][score_name][preset]
    norm = doc["normalised"]
    common = []
    for key, series in norm.items():
        a = series.get(entity, {}).get(str(y1))
        b = series.get(entity, {}).get(str(y2))
        if a is not None and b is not None:
            common.append((weights[key], a, b))
    if not common:
        return None
    total = sum(weights.values())
    w_common = sum(w for w, _, _ in common)
    d = sum(w * (b - a) for w, a, b in common) / w_common
    return round(d, 1), round(w_common / total, 2), len(common)


for y1, y2, bd, bs, bn in ((1995, 2000, -4.6, 0.56, 10), (2000, 2010, 8.8, 0.69, 13), (2010, 2019, 9.2, 0.62, 12)):
    got = _recompute_delta(s_modelled, "russian_federation", y1, y2)
    ok = got is not None and abs(got[0] - bd) <= 0.15 and abs(got[1] - bs) <= 0.02 and got[2] == bn
    check(f"modelled: Russia {y1}->{y2} delta {bd} ({bs}, {bn})", ok, f"got {got}")
for y1, y2, bs in ((1995, 2000, 0.24), (2000, 2010, 0.24), (2010, 2019, 0.18)):
    got = _recompute_delta(s_official, "russian_federation", y1, y2)
    check(f"official: Russia {y1}->{y2} REFUSED (common weight {bs} < 0.50)",
          got is not None and got[1] < 0.50 and got[1] == bs, f"got {got}")

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
        # the threshold rule mirrored: emitted iff coverage >= 0.60
        emitted = year in doc.get("scores", {}).get(preset, {}).get(entity, {})
        if emitted != (coverage >= 0.60):
            _golden_fail.append((score_name, entity, year, "threshold"))
    if "years" in vec:  # a delta case
        y1, y2 = (str(y) for y in vec["years"])
        exp = vec["expected"]["delta"]
        common = [
            (weights[key], series.get(entity, {}).get(y1), series.get(entity, {}).get(y2))
            for key, series in norm.items()
            if series.get(entity, {}).get(y1) is not None and series.get(entity, {}).get(y2) is not None
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
    "every golden vector recomputed from the emitted values (independent path)",
    not _golden_fail, str(_golden_fail[:5]),
)
_just_below = [v for v in s_golden.get("vectors", []) if "just-below" in v.get("why", "")]
check(
    "the coverage-just-below vector RE-PICKED live (not the v27 Afghanistan-2004 case, "
    "invalid under the 16 total weight)",
    len(_just_below) == 1
    and not (_just_below[0]["entity"] == "afghanistan" and _just_below[0]["year"] == 2004)
    and 0.55 <= _just_below[0]["expected"]["coverage"] < 0.60,
    str([(v["entity"], v["year"], v["expected"]["coverage"]) for v in _just_below]),
)
check(
    "the golden set still covers the required shapes: a refused delta, a todd-preset case, "
    "a split-sex case, a log case, a target case",
    any("years" in v and v["expected"]["delta"].get("refused") for v in s_golden.get("vectors", []))
    and any(v.get("preset") == "todd" for v in s_golden.get("vectors", []))
    and any("split-sex" in v.get("why", "") for v in s_golden.get("vectors", []))
    and any("log component" in v.get("why", "") for v in s_golden.get("vectors", []))
    and any("target component" in v.get("why", "") for v in s_golden.get("vectors", [])),
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
    "385 tests collected (384 at v27 + the incarceration-refusal test)",
    n_tests == 385,
    f"parsed={n_tests}; " + " | ".join(_diag),
)
cfg = subprocess.run(
    [sys.executable, "-m", "src.cli", "check-config"], capture_output=True, text=True, cwd=str(ROOT)
)
check(
    "cli check-config: 27 indicators, corpus 22/470, score layer in BOTH units "
    "(17 indicators -> 19/18 components, frozen)",
    "OK: 27 indicator(s)" in cfg.stdout
    and "todd corpus: 22 metrics, 470 citations" in cfg.stdout
    and "score layer: 17 indicators (17 official / 16 modelled), 19/18 components" in cfg.stdout
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
    "rebuild ×2: all dist files byte-stable (34 files incl. the score layer)",
    rc1.returncode == 0 and rc2.returncode == 0
    and before == after1 == after2 and len(after2) == 34,
    f"n={len(after2)}; rc1={rc1.returncode} rc2={rc2.returncode}; "
    f"drift1={[k for k in after1 if after1[k] != before.get(k)][:3]} "
    f"drift2={[k for k in after2 if after2[k] != after1.get(k)][:3]}",
)
check(
    "rebuild prints the score layer line (official 19 / modelled 18, frozen)",
    "Score layer ->" in rc1.stdout and "official 19 / modelled 18" in rc1.stdout,
    rc1.stdout.strip().splitlines()[-1] if rc1.stdout else rc1.stderr[:120],
)

# --- report ---
print()
n_pass = sum(1 for _, ok, _ in results if ok)
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{n_pass}/{len(results)} PASS")
sys.exit(0 if n_pass == len(results) else 1)
