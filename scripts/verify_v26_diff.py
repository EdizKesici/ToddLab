#!/usr/bin/env python3
"""verify_v26_diff.py — the v26 withdrawal's invariant checks.

Every check PASSES loud or FAILS loud. Run from the repo root:
    python scripts/verify_v26_diff.py

Baseline: the V25 commit (a9ef7eb, Ediz's push). The design: the two
withdrawn indicators (immigration_stock, agricultural_employment_share)
leave NOTHING behind — configs, corpus lines, fixtures, machinery — and
every SURVIVING indicator's dist file stays byte-identical, with exactly
two dist files allowed to change (catalog.json, todd_corpus.json — the
entries/metrics that went away).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V25 = "a9ef7eb"  # Ediz's V25 push (tree-identical to 0bd640c)

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


# --- 1. the two indicators are gone, root and branch ---
for name in ("immigration_stock", "agricultural_employment_share"):
    check(
        f"config gone: config/indicators/{name}.yaml",
        not (ROOT / f"config/indicators/{name}.yaml").exists(),
    )
    check(
        f"dist gone: data/dist/indicators/{name}.json",
        not (ROOT / f"data/dist/indicators/{name}.json").exists(),
    )
    check(
        f"raw gone: data/raw/*/{name}/",
        not any((ROOT / "data/raw").glob(f"*/{name}")),
    )
    check(
        f"processed gone: data/processed/{name}.*",
        not any(ROOT.glob(f"data/processed/{name}.*")),
    )
    check(
        f"no fixture carries the name: tests/fixtures/*{name}*",
        not any((ROOT / "tests/fixtures").glob(f"*{name}*")),
    )

# --- 2. the surviving dist files are byte-identical to V25 ---
# NOTE: immigration_stock.json was GITIGNORED at V25 (the 228 MB exclusion)
# so it never rides git ls-tree — its absence is checked directly in §1.
dist_dir = ROOT / "data/dist/indicators"
v25_files = git("ls-tree", "-r", "--name-only", V25, "data/dist/indicators/").splitlines()
v25_names = {Path(f).name for f in v25_files}
current_names = {f.name for f in dist_dir.glob("*.json")}
gone = (v25_names | {"immigration_stock.json"}) - current_names
check(
    "exactly the two withdrawn dist files are gone vs V25",
    gone == {"immigration_stock.json", "agricultural_employment_share.json"},
    f"gone: {sorted(gone)}",
)
check(
    "no NEW indicator dist files appeared (27 survive)",
    current_names - v25_names == set(),
    f"unexpected new: {sorted(current_names - v25_names)}",
)
check("27 indicator dist files", len(current_names) == 27, f"{len(current_names)}")
mismatched = []
for name in sorted(current_names):
    v25_blob = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{V25}:data/dist/indicators/{name}"],
        capture_output=True,
    ).stdout
    current = (dist_dir / name).read_bytes()
    if v25_blob != current:
        mismatched.append(name)
check(
    "all 27 surviving indicator files byte-identical to the V25 commit",
    not mismatched,
    f"mismatched: {mismatched}",
)

# --- 3. catalog.json: exactly the two entries removed ---
catalog = json.loads((ROOT / "data/dist/catalog.json").read_text(encoding="utf-8"))
ids = {c["id"] for c in catalog}
check(
    "catalog carries 27 entries",
    len(catalog) == 27 and len(ids) == 27,
    f"{len(catalog)} entries",
)
check(
    "catalog: the two withdrawn ids absent",
    not ({"immigration_stock", "agricultural_employment_share"} & ids),
)
v25_catalog = json.loads(
    git("show", f"{V25}:data/dist/catalog.json").encode()  # noqa: F841
) if False else json.loads(subprocess.run(
    ["git", "-C", str(ROOT), "show", f"{V25}:data/dist/catalog.json"],
    capture_output=True, check=True,
).stdout)
v25_ids = {c["id"] for c in v25_catalog}
check(
    "catalog diff vs V25 = exactly the two removals",
    v25_ids - ids == {"immigration_stock", "agricultural_employment_share"}
    and ids - v25_ids == set(),
)
# every surviving catalog ENTRY byte-identical
changed_entries = [
    c["id"] for c in catalog
    if json.dumps(c, sort_keys=True, ensure_ascii=False)
    != json.dumps(next(x for x in v25_catalog if x["id"] == c["id"]), sort_keys=True, ensure_ascii=False)
]
check(
    "every surviving catalog entry is unchanged field-for-field",
    not changed_entries,
    f"changed: {changed_entries}",
)

# --- 4. todd_corpus.json: the two metrics gone, 22/22 ---
corpus = json.loads((ROOT / "data/dist/todd_corpus.json").read_text(encoding="utf-8"))
meta = corpus["meta"]
check("corpus meta: 22 metrics", meta["metrics"] == 22, str(meta["metrics"]))
check("corpus meta: 22 implemented", meta["implemented_metrics"] == 22, str(meta["implemented_metrics"]))
check("corpus meta: 470 citations", meta["total_citations"] == 470, str(meta["total_citations"]))
check(
    "corpus meta: the owner's CSV sha256",
    meta["source_csv_sha256"].startswith("e30304cf6dca3b7ca1e3923e49e709167444edef42dcb63add656b8a72395d4b"),
)
metric_ids = {m["id"] for m in corpus["metrics"]}
check(
    "corpus: the two withdrawn metric ids absent",
    not ({"immigration_stock", "agricultural_employment_share"} & metric_ids),
)
check(
    "corpus: all remaining metrics implemented (22/22, the closure holds)",
    all(m["implemented"] for m in corpus["metrics"]) and len(metric_ids) == 22,
)

# --- 5. the surviving indicators' payloads carry no bilateral keys ---
bad_payloads = []
for f in dist_dir.glob("*.json"):
    d = json.loads(f.read_text(encoding="utf-8"))
    if "bilateral" in d or "bilateral_citizenship" in d:
        bad_payloads.append(f.name)
check(
    "no dist payload carries bilateral/bilateral_citizenship keys",
    not bad_payloads,
    f"offenders: {bad_payloads}",
)
# the segment layers SURVIVE on unemployment (the v25 faces untouched)
unemp = json.loads((dist_dir / "unemployment_rate.json").read_text(encoding="utf-8"))
check(
    "unemployment_rate keeps its segment layers (the v25 faces untouched)",
    "segments" in unemp and "segments_citizenship" in unemp,
    f"segments data: {len(unemp['segments']['data'])} / "
    f"{len(unemp['segments_citizenship']['data'])} points",
)
check(
    "unemployment segment counts unchanged vs V25 (3,023 / 2,710)",
    len(unemp["segments"]["data"]) == 3023
    and len(unemp["segments_citizenship"]["data"]) == 2710,
)

# --- 6. the source registry and the corpus CSV ---
check(
    "todd_core.csv is the owner's upload (sha256 anchored)",
    subprocess.run(["sha256sum", str(ROOT / "todd_core.csv")], capture_output=True, text=True, check=True)
    .stdout.split()[0] == "e30304cf6dca3b7ca1e3923e49e709167444edef42dcb63add656b8a72395d4b",
)
sources_yaml = (ROOT / "config/sources.yaml").read_text(encoding="utf-8")
check(
    "sources.yaml carries the withdrawal record (the honest death note)",
    "immigration_stock: WITHDRAWN v26" in sources_yaml,
)
check(
    "sources.yaml: no ACTIVE migr door documentation left "
    "(the historical CHANGELOG keeps its copies)",
    "migr_pop3ctb/ROW" not in sources_yaml and "DF_MIG/B15" not in sources_yaml,
)

# --- 7. the code: no bilateral machinery left in src/ (comments excluded) ---
import re as _re
_code_hits = []
for _f in (ROOT / "src").rglob("*.py"):
    for _i, _line in enumerate(_f.read_text(encoding="utf-8").splitlines(), 1):
        _stripped = _line.strip()
        if _stripped.startswith("#") or _stripped.startswith('"""'):
            continue  # history notes are legitimate; machinery is not
        if "v26" in _line or "REMOVED" in _line or "CHANGELOG" in _line:
            continue  # the withdrawal notes name the dead symbols deliberately
        if _re.search(r"origin_axis|_bilateral|bilateral_points|parse_migf|parse_mig_csv|_MIGR_|_MIGF_", _line):
            _code_hits.append(f"{_f.relative_to(ROOT)}:{_i}: {_stripped[:80]}")
check(
    "no bilateral/migr machinery left in src/ (code lines only)",
    not _code_hits,
    "\n".join(_code_hits),
)

# --- 8. the entity registry is additive: the vanished entities stay ---
entities = json.loads((ROOT / "data/dist/entities.json").read_text(encoding="utf-8"))
ent_ids = {e["entity_id"] for e in entities}
for eid in ("netherlands_antilles", "serbia_and_montenegro", "czechoslovakia", "ussr", "yugoslavia_sfr", "kosovo"):
    check(f"registry keeps the vanished entity '{eid}' (additive discipline)", eid in ent_ids)

# --- 9. tests + config state (announced, read live) ---
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--co", "-t", ""],
    capture_output=True, text=True, cwd=str(ROOT),
) if False else None
test_count = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only"],
    capture_output=True, text=True, cwd=str(ROOT),
)
n_tests = None
for line in test_count.stdout.splitlines():
    if "tests collected" in line or "test selected" in line:
        n_tests = int(line.split()[0])
        break
    if line.strip().endswith("collected") and line.strip().split()[0].isdigit():
        n_tests = int(line.strip().split()[0])
check(
    "365 tests collected (420 at V25 - 55 withdrawn with the machinery)",
    n_tests == 365,
    f"{n_tests}",
)
cfg = subprocess.run(
    [sys.executable, "-m", "src.cli", "check-config"], capture_output=True, text=True, cwd=str(ROOT)
)
check(
    "cli check-config: 27 indicators, corpus 22 metrics / 470 citations",
    "OK: 27 indicator(s)" in cfg.stdout and "todd corpus: 22 metrics, 470 citations" in cfg.stdout,
    cfg.stdout.splitlines()[0] if cfg.stdout else cfg.stderr[:100],
)

# --- report ---
print()
n_pass = sum(1 for _, ok, _ in results if ok)
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{n_pass}/{len(results)} PASS")
sys.exit(0 if n_pass == len(results) else 1)
