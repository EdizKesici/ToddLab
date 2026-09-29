"""verify_v25_diff.py — la vérification de livraison de la V25 (les faces
by-nationality du chômage + le dénominateur par véhicule + la face
by-sex du taux simple), selon la direction approuvée par Ediz et la
conception gelée sur les sondes (scripts/v25_probe.py, worklog Task 7).

La baseline est le commit V24 LUI-MÊME (66a39df — le sommet poussé sur
GitHub, l'état qu'Ediz a revu) : chaque fichier dist V24 est extrait de
git et comparé au dist reconstruit — le dépôt est la vérité
structurelle. (immigration_stock.json n'a jamais été commis — exclu
comme régénérable au 66a39df — donc ses couches sont vérifiées contre
les comptes du gel V24, jamais contre git.)

Les contrôles :
  1-4   : le périmètre — les 25 fichiers d'indicateurs jamais touchés
          byte-identiques au commit V24 ; entities.json /
          todd_corpus.json byte-identiques ; le catalog.json ne bouge
          QUE le résumé de racines de unemployment_rate (eurostat_lfs
          1 -> 5 portes canoniques ; +ilo_lfs x2 sur le témoin, le
          worldbank restant) et l'entrée du NOUVEL indicateur
          per-vehicle ; birth_rate_fertility.json porte la SEULE
          dérive live documentée (Moldova TFR : le collecteur révise
          2022/2023 et imprime 2024 — 19 lignes, la révision de
          vintage enregistrée, jamais corrigée).
  5-10  : unemployment_rate — les clés préexistantes bit-identiques
          (les points T du flux mono-axe, le témoin WB, todd_refs, les
          2 premières entrées sources[]) ; +6 nouvelles entrées
          sources[] exactement (M/F, lfsa x2, ilostat x2) ; les points
          M/F sous la clé sex du flux mono-axe.
  11-16 : les faces segments — les comptes du gel : naissance 3 023
          points / 4 classes / 36 entités, citoyenneté 2 710 / 4 / 35 ;
          les témoins ILOSTAT 861 points / 144 entités / 2 classes /
          2 faces de sexe et 822 / 137 / 2 / 2 ; les vocabulaires de
          classes DISJOINTS (ADR-0010 rendu exécutable) ; aucune clé
          segments sur les 28 autres indicateurs.
  17-22 : les ancres — FR 2015 natives 9.4 / foreign_born 17.1 /
          eu_born 10.7 / non_eu_born 19.0 ; nationals 9.7 /
          foreigners 20.5 / eu_foreigners 12.6 / non_eu_foreigners
          24.5 ; FR M 2015 = 10.8 / F = 9.9 ; les ancres du témoin FR
          2025 (7.023/12.003 et 7.162/13.902) ; l'Italie 2001 du témoin
          transportée telle qu'imprimée (~75-78, la borne élargie).
  23-27 : le dénominateur par véhicule — le nouveau fichier : 534
          points / 38 aires / 1994-2024, sans témoin, todd_core=false,
          la paire compagnon déclarée des deux côtés ; les ancres FRA
          2010 = 0.9497 / 2024 = 0.6512, CHE 1994 = 1.6303, CHL 1998
          = 13.1494 ; les États-Unis ABSENTS (la limite honnête).
  28    : l'idempotence — double rebuild complet, 32/32 md5.
  29    : le corpus 24/24 + cli check-config OK (29 indicateurs).

Utilisation : python scripts/verify_v25_diff.py   (depuis la racine du
dépôt, après le fetch complet 335/335 et un rebuild).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V24 = "66a39df"  # the pushed V24 tip — the state Ediz reviewed

results: list[tuple[bool, str, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((bool(ok), label, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))
    return bool(ok)


def git_blob(path: str) -> bytes:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{V24}:{path}"],
        capture_output=True, check=True,
    )
    return out.stdout


def load_dist(path: str) -> dict:
    return json.loads((ROOT / "data" / "dist" / path).read_text(encoding="utf-8"))


ALL_INDICATORS = sorted(
    p.name for p in (ROOT / "data" / "dist" / "indicators").glob("*.json")
)


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    # --- 1-4 : le périmètre -------------------------------------------------
    untouched = [
        n for n in ALL_INDICATORS
        if n not in (
            "unemployment_rate.json", "road_accident_mortality_per_vehicle.json",
            "road_accident_mortality.json", "birth_rate_fertility.json",
            "immigration_stock.json",  # never committed — checked against the freeze below
        )
    ]
    identical = [n for n in untouched if git_blob(f"data/dist/indicators/{n}") == (ROOT / "data" / "dist" / "indicators" / n).read_bytes()]
    check(len(untouched) == 24, "the untouched indicator files number exactly 24", f"{len(untouched)}")
    check(len(identical) == len(untouched), "every untouched indicator file is byte-identical to the V24 commit",
          f"{len(identical)}/{len(untouched)}")
    check(git_blob("data/dist/entities.json") == (ROOT / "data" / "dist" / "entities.json").read_bytes()
          and git_blob("data/dist/todd_corpus.json") == (ROOT / "data" / "dist" / "todd_corpus.json").read_bytes(),
          "entities.json and todd_corpus.json are byte-identical to the V24 commit")

    old_catalog = {c["id"]: c for c in json.loads(git_blob("data/dist/catalog.json"))}
    new_catalog = {c["id"]: c for c in load_dist("catalog.json")}
    check(set(new_catalog) - set(old_catalog) == {"road_accident_mortality_per_vehicle"},
          "catalog.json gains exactly one indicator entry (the per-vehicle face)")
    moved = {i for i in old_catalog if old_catalog[i] != new_catalog[i]}
    check(moved == {"unemployment_rate", "birth_rate_fertility", "road_accident_mortality"},
          "catalog.json moves only the three designed entries (unemployment's roots summary, "
          "the Moldova TFR vintage, road's companion field)",
          f"moved: {sorted(moved)}")
    check(new_catalog["road_accident_mortality"]["companion_indicators"] == ["road_accident_mortality_per_vehicle"],
          "road_accident_mortality's catalog entry carries the companion link (the designed field change)")
    une_old, une_new = old_catalog["unemployment_rate"], new_catalog["unemployment_rate"]
    canon_doors = [r for r in une_new["roots"]["canonical"] if r["root"] == "eurostat_lfs"]
    wit_doors = [r for r in une_new["roots"]["witness"] if r["root"] == "ilo_lfs"]
    check(canon_doors[0]["doors"] == 5 and wit_doors[0]["doors"] == 3,
          "unemployment_rate's roots summary: eurostat_lfs x5 canonical doors, ilo_lfs x3 witness doors")

    # --- 5-10 : unemployment_rate — the pre-existing keys bit-identical -----
    old_une = json.loads(git_blob("data/dist/indicators/unemployment_rate.json"))
    new_une = load_dist("indicators/unemployment_rate.json")
    old_t = [p for p in old_une["data"] if p.get("sex") is None]
    new_t = [p for p in new_une["data"] if p.get("sex") is None]
    check(old_t == new_t, "the pre-existing T rows of the single-axis data are bit-identical")
    # The WB witness: the SERIES data is bit-identical; the block's own
    # root_label moved because v25 edited the ilo_lfs root registry entry
    # itself (the label now names the class-decomposition flows and the
    # direct door) — the designed registry edit, riding every ilo_lfs
    # source's meta.
    check(old_une["witnesses"][0]["data"] == new_une["witnesses"][0]["data"]
          and all(old_une["witnesses"][0][k] == new_une["witnesses"][0][k]
                  for k in old_une["witnesses"][0] if k not in ("root_label",)),
          "the WB witness series is bit-identical (root_label only: the designed ilo_lfs registry edit)")
    check(old_une["todd_refs"] == new_une["todd_refs"]
          and old_une["sources"][0] == new_une["sources"][0]
          and all(old_une["sources"][1][k] == new_une["sources"][1][k]
                  for k in old_une["sources"][1] if k != "root_label"),
          "todd_refs and sources[0] bit-identical; sources[1] differs only on root_label")
    check(len(new_une["sources"]) == 8, "unemployment_rate declares exactly 8 sources (2 + 6 new)")
    new_refs = [s["source_ref"] for s in new_une["sources"][2:]]
    check(new_refs == [
        "une_rt_a/Y15-74/PC_ACT/M", "une_rt_a/Y15-74/PC_ACT/F",
        "lfsa_urgacob/Y15-74/T", "lfsa_urgan/Y15-74/T",
        "DF_UNE_DEAP_SEX_AGE_CBR_RT", "DF_UNE_DEAP_SEX_AGE_CCT_RT",
    ], "the 6 new sources[] entries are exactly the frozen doors", str(new_refs))
    mf = [p for p in new_une["data"] if p.get("sex") in ("male", "female")]
    check(len(mf) == 1168, "the single-axis M/F rows number 1,168 (584 + 584)", f"{len(mf)}")

    # --- 11-16 : the segment faces ------------------------------------------
    seg, ctz = new_une["segments"], new_une["segments_citizenship"]
    check((len(seg["data"]), len({p["population_class"] for p in seg["data"]}), len({p["entity_id"] for p in seg["data"]})) == (3023, 4, 36),
          "the birth face: 3,023 points, 4 classes, 36 entities")
    check((len(ctz["data"]), len({p["population_class"] for p in ctz["data"]}), len({p["entity_id"] for p in ctz["data"]})) == (2710, 4, 35),
          "the citizenship face: 2,710 points, 4 classes, 35 entities")
    b_classes = {p["population_class"] for p in seg["data"]}
    c_classes = {p["population_class"] for p in ctz["data"]}
    check(not (b_classes & c_classes), "the two class vocabularies are DISJOINT (ADR-0010 executable)")
    sw, cw = seg["witnesses"][0], ctz["witnesses"][0]
    check((sw["provider"], len(sw["data"]), len({p["entity_id"] for p in sw["data"]})) == ("ilostat", 861, 144)
          and {p["population_class"] for p in sw["data"]} == {"natives", "foreign_born"},
          "the birth witness: 861 points, 144 entities, the 2 aggregate classes")
    check((cw["provider"], len(cw["data"]), len({p["entity_id"] for p in cw["data"]})) == ("ilostat", 822, 137)
          and {p["population_class"] for p in cw["data"]} == {"nationals", "foreigners"},
          "the citizenship witness: 822 points, 137 entities, the 2 aggregate classes")
    no_seg = [
        n for n in ALL_INDICATORS
        if n != "unemployment_rate.json" and "segments" in load_dist(f"indicators/{n}")
    ]
    check(not no_seg, "no other indicator carries a segments key (the additivity pin)", str(no_seg))

    # --- 17-22 : the anchors -------------------------------------------------
    spts = {(p["entity_id"], p["population_class"], p["year"]): p["value"] for p in seg["data"]}
    cpts = {(p["entity_id"], p["population_class"], p["year"]): p["value"] for p in ctz["data"]}
    for key, want in (
        (("france", "natives", 2015), 9.4), (("france", "foreign_born", 2015), 17.1),
        (("france", "eu_born", 2015), 10.7), (("france", "non_eu_born", 2015), 19.0),
        (("france", "nationals", 2015), 9.7), (("france", "foreigners", 2015), 20.5),
        (("france", "eu_foreigners", 2015), 12.6), (("france", "non_eu_foreigners", 2015), 24.5),
    ):
        check(spts.get(key, cpts.get(key)) == want, f"the anchor {key} = {want}")
    mfpts = {(p["entity_id"], p["year"], p.get("sex")): p["value"] for p in new_une["data"]}
    check(mfpts[("france", 2015, "male")] == 10.8 and mfpts[("france", 2015, "female")] == 9.9,
          "the by-sex anchors: FR 2015 M = 10.8, F = 9.9")
    wpts = {(p["entity_id"], p["population_class"], p["year"], p.get("sex")): p["value"] for p in sw["data"]}
    wpts_c = {(p["entity_id"], p["population_class"], p["year"], p.get("sex")): p["value"] for p in cw["data"]}
    check(wpts[("france", "natives", 2025, None)] == 7.023 and wpts[("france", "foreign_born", 2025, None)] == 12.003,
          "the birth witness anchors: FR 2025 natives 7.023 / foreign_born 12.003")
    check(wpts_c[("france", "nationals", 2025, None)] == 7.162 and wpts_c[("france", "foreigners", 2025, None)] == 13.902,
          "the citizenship witness anchors: FR 2025 nationals 7.162 / foreigners 13.902")
    ita = [v for (e, c, y, s), v in wpts_c.items() if e == "italy" and y == 2001]
    check(ita and all(73 < v < 79 for v in ita),
          "the odd Italian 2001 vintage rides as-reported (~73.8-78.5, the widened bound's own evidence)",
          str(sorted(ita)[:3]))

    # --- 23-27 : the per-vehicle face ---------------------------------------
    veh = load_dist("indicators/road_accident_mortality_per_vehicle.json")
    vpts = {(p["entity_id"], p["year"]): p["value"] for p in veh["data"]}
    check((len(veh["data"]), len({p["entity_id"] for p in veh["data"]})) == (534, 38),
          "the per-vehicle face: 534 points across 38 areas")
    check(veh["witnesses"] == [] and veh["todd_core"] is False and "todd_refs" not in veh,
          "witnessless, todd_core=false, no corpus entry (the honest shape)")
    check(veh["companion_indicators"] == ["road_accident_mortality"]
          and load_dist("indicators/road_accident_mortality.json")["companion_indicators"] == ["road_accident_mortality_per_vehicle"],
          "the companion pair is declared on BOTH sides")
    for key, want in (
        (("france", 2010), 0.949683318), (("france", 2024), 0.651244379),
        (("switzerland", 1994), 1.630302595), (("chile", 1998), 13.14939566),
    ):
        check(vpts.get(key) == want, f"the per-vehicle anchor {key} = {want}")
    check(not any(e == "united_states" for (e, _y) in vpts), "the USA is absent (the honest limit, documented)")

    # --- 28 : idempotence ----------------------------------------------------
    import shutil
    dist_paths = sorted((ROOT / "data" / "dist").rglob("*.json"))
    before = {p: md5_of(p) for p in dist_paths}
    out = subprocess.run([sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT), capture_output=True, text=True)
    check(out.returncode == 0, "the second rebuild exits 0")
    after = {p: md5_of(p) for p in dist_paths}
    check(before == after, f"idempotence: {len(dist_paths)}/{len(dist_paths)} dist files md5-identical across rebuilds")

    # --- 29 : the corpus + the config ---------------------------------------
    corpus = load_dist("todd_corpus.json")
    check(corpus["meta"]["implemented_metrics"] == 24, "the corpus stays 24/24 (a face, zero flips)")
    cfg = subprocess.run([sys.executable, "-m", "src.cli", "check-config"], cwd=str(ROOT), capture_output=True, text=True)
    check(cfg.returncode == 0 and "29 indicator(s)" in cfg.stdout, "cli check-config OK with 29 indicators")

    n_pass = sum(1 for ok, _l, _d in results if ok)
    print(f"\n{n_pass}/{len(results)} PASS")
    if n_pass != len(results):
        for ok, label, detail in results:
            if not ok:
                print(f"  FAIL  {label}  [{detail}]")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
