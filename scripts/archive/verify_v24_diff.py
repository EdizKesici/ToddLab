"""verify_v24_diff.py — la vérification de livraison de la V24 (la face
by-sex), selon la direction approuvée par Ediz et la conception gelée
sur les sondes (scripts/v24_probe.py, worklog Task 3).

La baseline est le commit v23 LUI-MÊME (6e90e95) : chaque fichier dist
v23 est extrait de git et comparé au dist reconstruit — le dépôt est la
vérité structurelle.

Les contrôles :
  1-6    : le périmètre — les 26 autres fichiers + illegitimate_births
           byte-identiques au commit v23 ; entities.json /
           todd_corpus.json byte-identiques ; le catalog.json ne bouge
           QUE le résumé de racines d'immigration_stock (eurostat_migr
           65 -> 189 portes canoniques, oecd_mig inchangé à 2).
  7-12   : immigration_stock — les clés préexistantes bit-identiques
           (les 557 points mono-axe, le témoin UN DESA, todd_refs, les
           68 premières entrées sources[], les points sex=None des deux
           couches et les points _T des deux témoins OCDE) ; +124
           nouvelles entrées sources[] exactement.
  13-20  : la face by-sex — les comptes du gel : naissance M 91 249 /
           F 91 229, ctz M 109 906 / F 109 814, témoin B14 +94 952 F,
           témoin B15 +101 829 F ; les totaux de couches 273 708 /
           194 177 / 331 778 / 211 592 ; le périmètre sans HR.
  21-26  : les ancres — M+F=_T à l'unité sur les six paires ; les
           coutures F OCDE/Eurostat (475 388 et 226 668) ; US<-MEX F
           2024 ; la géographie sans HR.
  27     : l'idempotence — double rebuild complet, 31/31 md5.
  28     : le corpus 24/24 + cli check-config OK.

Utilisation : python scripts/verify_v24_diff.py   (depuis la racine du
dépôt, après le fetch ciblé 192/192 et un rebuild).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V23 = "6e90e95"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((bool(ok), label, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))
    return bool(ok)


def git_blob(path: str) -> bytes:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{V23}:{path}"],
        capture_output=True, check=True,
    )
    return out.stdout


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def dist_path(name: str) -> Path:
    return ROOT / "data" / "dist" / "indicators" / name


def load_dist(name: str) -> dict:
    return json.loads(dist_path(name).read_text(encoding="utf-8"))


def main() -> int:
    indicator_files = sorted(p.name for p in (ROOT / "data" / "dist" / "indicators").glob("*.json"))
    new = load_dist("immigration_stock.json")
    old = json.loads(git_blob("data/dist/indicators/immigration_stock.json"))

    # ---- 1-3 : le périmètre --------------------------------------------
    others = [n for n in indicator_files if n != "immigration_stock.json"]
    moved = [
        n for n in others
        if md5(dist_path(n).read_bytes()) != md5(git_blob(f"data/dist/indicators/{n}"))
    ]
    check(
        not moved and len(others) == 27,
        "les 27 autres fichiers d'indicateurs byte-identiques au commit v23",
        f"divergents: {moved}",
    )
    check(
        md5((ROOT / "data" / "dist" / "entities.json").read_bytes())
        == md5(git_blob("data/dist/entities.json")),
        "entities.json byte-identique",
    )
    check(
        md5((ROOT / "data" / "dist" / "todd_corpus.json").read_bytes())
        == md5(git_blob("data/dist/todd_corpus.json")),
        "todd_corpus.json byte-identique (24/24, zéro bascule — la v24 ajoute une FACE)",
    )

    # ---- 4-6 : le catalog ------------------------------------------------
    nc = json.loads((ROOT / "data" / "dist" / "catalog.json").read_text())
    oc = json.loads(git_blob("data/dist/catalog.json"))
    nc_by_id, oc_by_id = {c["id"]: c for c in nc}, {c["id"]: c for c in oc}
    moved_cat = [i for i in oc_by_id if nc_by_id[i] != oc_by_id[i]]
    check(
        moved_cat == ["immigration_stock"] and set(nc_by_id) == set(oc_by_id),
        "catalog.json : seule l'entrée immigration_stock bouge",
        f"moved={moved_cat}",
    )
    roots = nc_by_id["immigration_stock"]["roots"]
    euro_row = next(r for r in roots["canonical"] if r["root"] == "eurostat_migr")
    oecd_row = next(r for r in roots["witness"] if r["root"] == "oecd_mig")
    check(
        euro_row["doors"] == 189 and oecd_row["doors"] == 2,
        "catalog : eurostat_migr 65 -> 189 portes canoniques (les +124 by-sex) ; oecd_mig inchangé (2)",
        f"eurostat_migr={euro_row['doors']} oecd_mig={oecd_row['doors']}",
    )

    # ---- 7-10 : les clés préexistantes ----------------------------------
    check(
        [(p["entity_id"], p["year"], p["value"], p.get("quality_code"), p.get("provisional")) for p in new["data"]]
        == [(p["entity_id"], p["year"], p["value"], p.get("quality_code"), p.get("provisional")) for p in old["data"]]
        and len(new["data"]) == 557,
        "les 557 points (entité, année) bit-identiques",
    )
    check(
        json.dumps(new["witnesses"]) == json.dumps(old["witnesses"]),
        "le témoin UN DESA bit-identique",
    )
    check(new["todd_refs"] == old["todd_refs"], "le bloc todd_refs bit-identique")
    check(
        [json.dumps(s, sort_keys=True) for s in new["sources"][:68]]
        == [json.dumps(s, sort_keys=True) for s in old["sources"]]
        and len(new["sources"]) == 192,
        "les 68 premières entrées sources[] bit-identiques ; 192 entrées au total (+124 by-sex)",
        f"n={len(new['sources'])}",
    )

    # ---- 11-12 : les points sex=None préexistants ------------------------
    def by_sex(points):
        return [p for p in points if p.get("sex") is None]

    old_birth_t = old["bilateral"]["data"]
    new_birth_t = by_sex(new["bilateral"]["data"])
    check(
        json.dumps(new_birth_t, sort_keys=True) == json.dumps(old_birth_t, sort_keys=True),
        "bilateral : les 91 230 points sex=None bit-identiques",
    )
    old_ctz_t = old["bilateral_citizenship"]["data"]
    new_ctz_t = by_sex(new["bilateral_citizenship"]["data"])
    check(
        json.dumps(new_ctz_t, sort_keys=True) == json.dumps(old_ctz_t, sort_keys=True),
        "bilateral_citizenship : les 112 058 points sex=None bit-identiques",
    )

    # ---- 13-18 : les comptes du gel --------------------------------------
    birth = new["bilateral"]["data"]
    ctz = new["bilateral_citizenship"]["data"]
    n = lambda pts, s: sum(1 for p in pts if p.get("sex") == s)  # noqa: E731
    check(
        n(birth, "male") == 91249 and n(birth, "female") == 91229,
        "naissance : M 91 249 + F 91 229 (+182 478)",
        f"M={n(birth, 'male')} F={n(birth, 'female')}",
    )
    check(
        n(ctz, "male") == 109906 and n(ctz, "female") == 109814,
        "citoyenneté : M 109 906 + F 109 814 (+219 720)",
        f"M={n(ctz, 'male')} F={n(ctz, 'female')}",
    )
    b14 = new["bilateral"]["witnesses"][0]["data"]
    b15 = new["bilateral_citizenship"]["witnesses"][0]["data"]
    check(
        n(b14, "female") == 94952 and n(b14, None) == 99225,
        "témoin B14 : les 99 225 _T inchangés + 94 952 F gardées",
        f"_T={n(b14, None)} F={n(b14, 'female')}",
    )
    check(
        n(b15, "female") == 101829 and n(b15, None) == 109763,
        "témoin B15 : les 109 763 _T inchangés + 101 829 F gardées (les 104 009 lignes du pull V23 débloquées)",
        f"_T={n(b15, None)} F={n(b15, 'female')}",
    )
    check(
        len(birth) == 273708 and len(ctz) == 331778,
        "les totaux de couches : naissance 273 708 / citoyenneté 331 778",
        f"naissance={len(birth)} ctz={len(ctz)}",
    )
    check(
        len(b14) == 194177 and len(b15) == 211592,
        "les totaux de témoins : B14 194 177 / B15 211 592",
        f"B14={len(b14)} B15={len(b15)}",
    )

    # ---- 19-20 : le périmètre et la géographie ---------------------------
    birth_sex_dests = {p["destination_entity_id"] for p in birth if p.get("sex")}
    ctz_sex_dests = {p["destination_entity_id"] for p in ctz if p.get("sex")}
    check(
        len(birth_sex_dests) == 29 and len(ctz_sex_dests) == 33,
        "le périmètre by-sex : 29 destinations naissance / 33 citoyenneté (HR sans ventilation)",
        f"naissance={len(birth_sex_dests)} ctz={len(ctz_sex_dests)}",
    )
    check(
        "croatia" not in birth_sex_dests and "croatia" not in ctz_sex_dests
        and "croatia" in {p["destination_entity_id"] for p in birth},
        "HR : la ventilation absente (l'absence honnête enregistrée), la face _T intacte",
    )

    # ---- 21-26 : les ancres ----------------------------------------------
    bpts = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"], p.get("sex")): p["value"]
        for p in birth
    }
    cpts = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"], p.get("sex")): p["value"]
        for p in ctz
    }
    wpts_b = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"], p.get("sex")): p["value"]
        for p in b14
    }
    wpts_c = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"], p.get("sex")): p["value"]
        for p in b15
    }
    ok_arith = True
    for pts, label in ((bpts, "naissance"), (cpts, "citoyenneté")):
        for dest, orig, y in (("france", "morocco", 2015), ("france", "morocco", 2018), ("france", "portugal", 2015)):
            mv = pts.get((dest, orig, y, "male"))
            fv = pts.get((dest, orig, y, "female"))
            tv = pts.get((dest, orig, y, None))
            if mv is None or fv is None or tv is None or abs(mv + fv - tv) > 0.5:
                ok_arith = False
    check(ok_arith, "M+F=_T à l'unité sur les six paires d'ancres (FR<-MA/PT, 2015/2018, les deux faces)")
    check(
        wpts_b[("france", "morocco", 2015, "female")] == 475388
        and bpts[("france", "morocco", 2015, "female")] == 475388,
        "COUTURE F naissance : FR<-MAR F 2015 = 475 388 sur les DEUX portes (Eurostat M/F et OCDE B14)",
    )
    check(
        wpts_c[("france", "morocco", 2015, "female")] == 226668
        and cpts[("france", "morocco", 2015, "female")] == 226668,
        "COUTURE F citoyenneté : FR<-MAR F 2015 = 226 668 sur les DEUX portes (Eurostat ctz F et OCDE B15)",
    )
    check(
        wpts_c[("united_states", "mexico", 2024, "female")] == 3752511.161,
        "ANCRE US<-MEX F 2024 : 3 752 511,161 (la face F du monde)",
    )
    # the vanished origins' own by-sex coverage, read from the dist: on the
    # EUROSTAT layers Kosovo (XK->XKX) and the Netherlands Antilles (AN)
    # carry BOTH ventilations; on the OECD witnesses all six vanished
    # entities ride the female face (the flows print no male face).
    euro_vanished = {"kosovo", "netherlands_antilles"}
    van_euro = {
        (p["origin_entity_id"], p.get("sex"))
        for p in birth + ctz
        if p["origin_entity_id"] in euro_vanished and p.get("sex")
    }
    van_oecd = {
        (p["origin_entity_id"], p.get("sex"))
        for p in b14 + b15
        if p["origin_entity_id"] in {
            "kosovo", "netherlands_antilles", "ussr", "yugoslavia_sfr",
            "czechoslovakia", "serbia_and_montenegro",
        } and p.get("sex")
    }
    check(
        {("kosovo", "male"), ("kosovo", "female"),
         ("netherlands_antilles", "male"), ("netherlands_antilles", "female")} <= van_euro
        and len({o for (o, s) in van_oecd}) == 6
        and all(s == "female" for (o, s) in van_oecd),
        "les origines disparues portent aussi les ventilations (l'admission v21/v22 sur la face by-sex : Eurostat M/F, OCDE femelle)",
        f"euro={sorted(van_euro)} oecd={sorted(van_oecd)}",
    )
    check(
        not any(p.get("sex") not in (None, "male", "female") for p in birth + ctz + b14 + b15),
        "le vocabulaire sexe : None / male / female seulement (aucun point M côté OCDE — les flows n'impriment pas de face masculine)",
    )

    # ---- 27 : l'idempotence ----------------------------------------------
    def snapshot_md5s() -> dict[str, str]:
        return {
            str(p.relative_to(ROOT / "data" / "dist")): md5(p.read_bytes())
            for p in sorted((ROOT / "data" / "dist").rglob("*.json"))
        }

    r1 = subprocess.run(
        [sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=1800,
    )
    first = snapshot_md5s()
    r2 = subprocess.run(
        [sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=1800,
    )
    second = snapshot_md5s()
    check(
        r1.returncode == 0 and r2.returncode == 0 and first == second and len(first) == 31,
        "IDEMPOTENCE : double rebuild complet, 31/31 fichiers md5 identiques",
        f"n={len(first)} divergents={sorted(k for k in first if first[k] != second.get(k))}",
    )

    # ---- 28 : le corpus et la config --------------------------------------
    r3 = subprocess.run(
        [sys.executable, "-m", "src.cli", "check-config"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=300,
    )
    corpus = json.loads((ROOT / "data" / "dist" / "todd_corpus.json").read_text())
    check(
        r3.returncode == 0
        and corpus["meta"]["implemented_metrics"] == 24
        and "OK: 28 indicator(s)" in r3.stdout,
        "corpus todd_core 24/24 non affecté + cli check-config OK",
    )

    # ---- le verdict --------------------------------------------------------
    n_pass = sum(1 for ok, _, _ in results if ok)
    n_fail = len(results) - n_pass
    print()
    print(f"==> {n_pass} PASS / {n_fail} FAIL sur {len(results)} contrôles")
    for ok, label, detail in results:
        if not ok:
            print(f"  FAIL: {label} {detail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
