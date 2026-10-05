#!/usr/bin/env python3
"""verify_v27_diff.py — the v27 score layer's invariant checks.

Every check PASSES loud or FAILS loud. Run from the repo root:
    python scripts/verify_v27_diff.py

Baseline: the V26.1.1 commit (58509e3, Ediz's own push). The design: the
score layer is ADDED (data/dist/score/, config/score*.yaml, src/score/,
src/schema/score.py, scripts/freeze_score_bounds.py, tests/test_score.py,
the cli/config_loader wiring) with exactly ONE indicator-layer change —
decision 10's higher_is_better flip on industrial_employment_share — and
exactly ONE move — this verifier's predecessor archived to scripts/archive/.

§4.1 invariants: 28 of the 30 pre-existing dist files byte-identical
(26 indicators + entities.json + todd_corpus.json); the other two differ
ONLY by the flag (proved by parse-compare of every other key AND a
byte-level diff confined to those lines); corpus 22 metrics / 470
citations / sha256 unchanged; gini_index present, todd_core, absent from
the score config; rebuild ×2 byte-stable INCLUDING the new files.

§6: the score files parse and sit under the size cap; the §8 anchors
recomputed from the EMITTED layer match the reference prototype (the
explained difference: aggregates ride the STORED 2-decimal values); the
golden vectors recomputed by an independent code path; the test-count
check keeps the v26.1.1 self-diagnosing behaviour.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2611 = "58509e3"  # Ediz's V26.1.1 push — the audited baseline

results: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


# --- 1. the additions are present and the move happened ---
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
    "the v26 verifier archived (the single move of this version)",
    (ROOT / "scripts/archive/verify_v26_diff.py").is_file()
    and not (ROOT / "scripts/verify_v26_diff.py").exists(),
)

# --- 2. the 28 untouched dist files are byte-identical to V26.1.1 ---
dist_ind = ROOT / "data/dist/indicators"
v2611_files = git("ls-tree", "-r", "--name-only", V2611, "data/dist/").splitlines()
untouched_expected = [f for f in v2611_files if Path(f).name not in
                      ("industrial_employment_share.json", "catalog.json")]
mismatched = [
    f for f in untouched_expected
    if (ROOT / f).read_bytes() != subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{V2611}:{f}"], capture_output=True, check=True
    ).stdout
]
check(
    "28 dist files byte-identical to V26.1.1 (26 indicators + entities + corpus)",
    len(untouched_expected) == 28 and not mismatched,
    f"expected 28, got {len(untouched_expected)}; mismatched: {mismatched}",
)

# --- 3. the two designed changes differ ONLY by the flag ---


def _parse_at(ref: str, path: str) -> object:
    return json.loads(subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{ref}:{path}"], capture_output=True, check=True
    ).stdout)


cur_ind = json.loads((dist_ind / "industrial_employment_share.json").read_text(encoding="utf-8"))
old_ind = _parse_at(V2611, "data/dist/indicators/industrial_employment_share.json")
cur_ind_flip = dict(cur_ind); cur_ind_flip.pop("higher_is_better")
old_ind_flip = dict(old_ind); old_ind_flip.pop("higher_is_better")
check(
    "industrial_employment_share.json: every key EXCEPT the flag unchanged",
    cur_ind_flip == old_ind_flip and cur_ind["higher_is_better"] is True
    and old_ind["higher_is_better"] is False,
)
diff_lines = git("diff", V2611, "--", "data/dist/indicators/industrial_employment_share.json")
content_lines = [l for l in diff_lines.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
check(
    "industrial_employment_share.json: the byte-diff is exactly the one flag line",
    len(content_lines) == 2
    and content_lines[0] == '-  "higher_is_better": false,'
    and content_lines[1] == '+  "higher_is_better": true,',
    f"diff lines: {content_lines}",
)

cur_cat = json.loads((ROOT / "data/dist/catalog.json").read_text(encoding="utf-8"))
old_cat = _parse_at(V2611, "data/dist/catalog.json")
check("catalog carries 27 entries", len(cur_cat) == 27 and len(old_cat) == 27)
cur_by_id = {e["id"]: e for e in cur_cat}
old_by_id = {e["id"]: e for e in old_cat}
changed_entries = []
for eid in cur_by_id:
    a, b = dict(cur_by_id[eid]), dict(old_by_id[eid])
    a.pop("higher_is_better"); b.pop("higher_is_better")
    if a != b:
        changed_entries.append(eid)
check(
    "catalog: every entry EXCEPT industrial's flag unchanged field-for-field",
    not changed_entries
    and cur_by_id["industrial_employment_share"]["higher_is_better"] is True
    and old_by_id["industrial_employment_share"]["higher_is_better"] is False,
    f"unexpected changed entries: {changed_entries}",
)

# --- 4. the corpus and gini are untouched ---
import yaml

corpus = json.loads((ROOT / "data/dist/todd_corpus.json").read_text(encoding="utf-8"))
meta = corpus["meta"]
check("corpus: 22 metrics", meta["metrics"] == 22, str(meta.get("metrics")))
check("corpus: 470 citations", meta["total_citations"] == 470, str(meta.get("total_citations")))
check("corpus: 16 books", meta["books"] == 16, str(meta.get("books")))
check(
    "corpus: the owner's CSV sha256 unchanged",
    meta["source_csv_sha256"].startswith("e30304cf6dca"),
)
_score_yaml_parsed = yaml.safe_load((ROOT / "config/score.yaml").read_text(encoding="utf-8"))
_score_indicators = {c["indicator"] for c in _score_yaml_parsed["components"]}
check(
    "gini_index: still an indicator, todd_core true, absent from the score config "
    "(parsed, not text-searched — the header comment documents the exclusion)",
    "gini_index" in cur_by_id and cur_by_id["gini_index"]["todd_core"] is True
    and "gini_index" not in _score_indicators,
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
    "official.json: 20 components / modelled.json: 19 components",
    len(s_official.get("components", {})) == 20 and len(s_modelled.get("components", {})) == 19,
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

# --- 6. the §8 anchors, recomputed from the EMITTED layer ---
# The explained difference vs the reference prototype: the shipped layer
# STORES 2-decimal values and computes aggregates from the stored values;
# the prototype computes at full precision. Counts are exact; scores and
# deltas within the rounding tail.
ANCHORS = {
    "official": {"scored": {2000: 20, 2005: 18, 2010: 36, 2015: 37, 2019: 33, 2022: 34}},
    "modelled": {"scored": {2000: 104, 2005: 103, 2010: 133, 2015: 110, 2019: 101, 2022: 58}},
}
for score_name, spec in ANCHORS.items():
    doc = s_official if score_name == "official" else s_modelled
    scores_eq = doc.get("scores", {}).get("equal", {})
    for year, expected in spec["scored"].items():
        n = sum(1 for entity, years in scores_eq.items() if str(year) in years)
        check(f"{score_name}: scored countries {year} = {expected} (the anchor)", n == expected, f"got {n}")

TOP5 = {
    "official": [("australia", 74.7), ("czechia", 73.7), ("canada", 73.3),
                 ("sweden", 72.9), ("switzerland", 71.4)],
    "modelled": [("japan", 85.2), ("singapore", 81.0), ("israel", 79.0),
                 ("qatar", 78.8), ("norway", 78.4)],
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


for y1, y2, bd, bs, bn in ((1995, 2000, -4.6, 0.53, 10), (2000, 2010, 8.2, 0.71, 14), (2010, 2019, 9.2, 0.59, 12)):
    got = _recompute_delta(s_modelled, "russian_federation", y1, y2)
    ok = got is not None and abs(got[0] - bd) <= 0.15 and abs(got[1] - bs) <= 0.02 and got[2] == bn
    check(f"modelled: Russia {y1}->{y2} delta {bd} ({bs}, {bn})", ok, f"got {got}")
for y1, y2 in ((1995, 2000), (2000, 2010), (2010, 2019)):
    got = _recompute_delta(s_official, "russian_federation", y1, y2)
    check(f"official: Russia {y1}->{y2} REFUSED (common weight < 0.50)",
          got is not None and got[1] < 0.50, f"got {got}")

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
    "384 tests collected (365 at V26.1.1 + 19 score-layer tests)",
    n_tests == 384,
    f"parsed={n_tests}; " + " | ".join(_diag),
)
cfg = subprocess.run(
    [sys.executable, "-m", "src.cli", "check-config"], capture_output=True, text=True, cwd=str(ROOT)
)
check(
    "cli check-config: 27 indicators, corpus 22/470, score layer 18 components (frozen bounds)",
    "OK: 27 indicator(s)" in cfg.stdout
    and "todd corpus: 22 metrics, 470 citations" in cfg.stdout
    and "score layer: 18 components" in cfg.stdout
    and "(frozen)" in cfg.stdout,
    cfg.stdout.splitlines()[0] if cfg.stdout else cfg.stderr[:120],
)

# --- 9. rebuild ×2 byte-stability, INCLUDING the new files ---

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
    "rebuild prints the score layer line (official 20 / modelled 19, frozen)",
    "Score layer ->" in rc1.stdout and "official 20 / modelled 19" in rc1.stdout,
    rc1.stdout.strip().splitlines()[-1] if rc1.stdout else rc1.stderr[:120],
)

# --- report ---
print()
n_pass = sum(1 for _, ok, _ in results if ok)
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{n_pass}/{len(results)} PASS")
sys.exit(0 if n_pass == len(results) else 1)
