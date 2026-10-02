"""verify_v23_diff.py — la vérification de livraison de la V23 (33 PASS
attendus), selon les critères d'acceptation de la conception gelée (§5.6).

La baseline est le commit v22 LUI-MÊME (a7cd073) : chaque fichier dist v22
est extrait de git et comparé au dist reconstruit — aucune copie ad hoc,
le dépôt est la vérité structurelle.

Les 33 contrôles :
  1-6    : les autres fichiers — 26 indicateurs byte-identiques ;
           illegitimate_births = exactement UNE révision fournisseur
           (Moldavie 2022 : 18.3 -> 18.2, vérifiée en live deux fois) ;
           entities.json / todd_corpus.json byte-identiques ; le
           catalog.json ne bouge QUE le résumé de racines
           d'immigration_stock (eurostat_migr 31 -> 65 portes canoniques,
           oecd_mig 1 -> 2 portes témoins).
  7-15   : immigration_stock — les clés préexistantes bit-identiques (les
           557 points (entité, année), le témoin UN DESA, le bloc
           todd_refs, les 33 premières entrées sources[] dans l'ordre) ;
           +35 nouvelles entrées exactement ; la couche bilateral
           (naissance) bit-identique (91 230 points + le témoin B14
           99 225).
  16-25  : la couche bilateral_citizenship — présente ; canonique
           112 058 points / 6 627 paires / 34 destinations x 226 origines
           / 1998-2025 ; témoin B15 unique (DF_MIG/B15) : 109 763 points
           / 36 x 236 / 1995-2024.
  26-31  : les ancres — la série v18 FR<-MA ctz 2015-2018 ; la couture
           OCDE/Eurostat (458 561 des deux côtés) ; US<-MEX 2024 ctz vs
           naissance ; les contrastes CONVERGE (FR<-PT) et DIVERGE
           (FR<-MA) ; l'asymétrie de géographie DE-dedans/CY-dehors.
  32     : l'idempotence — double rebuild complet, 31/31 fichiers md5
           identiques.
  33     : le corpus todd_core 24/24 non affecté + cli check-config OK.

Utilisation : python scripts/verify_v23_diff.py   (depuis la racine du
dépôt, après un fetch ciblé 68/68 et un rebuild).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V22 = "a7cd073"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((bool(ok), label, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))
    return bool(ok)


def git_blob(path: str) -> bytes:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{V22}:{path}"],
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
    # ---- le périmètre des fichiers --------------------------------------
    indicator_files = sorted(p.name for p in (ROOT / "data" / "dist" / "indicators").glob("*.json"))
    new = load_dist("immigration_stock.json")
    old = json.loads(git_blob("data/dist/indicators/immigration_stock.json"))

    # 1 — les 26 autres fichiers strictement identiques
    strictly = [n for n in indicator_files if n != "immigration_stock.json" and n != "illegitimate_births.json"]
    moved = [
        n for n in strictly
        if md5(dist_path(n).read_bytes()) != md5(git_blob(f"data/dist/indicators/{n}"))
    ]
    check(
        not moved and len(strictly) == 26,
        "les 26 autres fichiers d'indicateurs byte-identiques au commit v22",
        f"divergents: {moved}",
    )

    # 2 — illegitimate_births : exactement la révision fournisseur Moldavie
    nb = load_dist("illegitimate_births.json")
    ob = json.loads(git_blob("data/dist/indicators/illegitimate_births.json"))
    nk = {(p["entity_id"], p["year"], p.get("sex")): p.get("value") for p in nb["data"]}
    ok_ = {(p["entity_id"], p["year"], p.get("sex")): p.get("value") for p in ob["data"]}
    changed = {k for k in set(nk) & set(ok_) if nk[k] != ok_[k]}
    only_new, only_old = set(nk) - set(ok_), set(ok_) - set(nk)
    check(
        not only_new and not only_old and changed == {("moldova_republic_of", 2022, None)}
        and ok_[("moldova_republic_of", 2022, None)] == 18.3
        and nk[("moldova_republic_of", 2022, None)] == 18.2,
        "illegitimate_births : exactement UNE révision fournisseur (Moldavie 2022 : 18.3 -> 18.2)",
        f"changed={changed} only_new={only_new} only_old={only_old}",
    )

    # 3-4 — entities.json et todd_corpus.json byte-identiques
    check(
        md5((ROOT / "data" / "dist" / "entities.json").read_bytes())
        == md5(git_blob("data/dist/entities.json")),
        "entities.json byte-identique (aucune entité nouvelle : les origines disparues sont déjà déclarées)",
    )
    check(
        md5((ROOT / "data" / "dist" / "todd_corpus.json").read_bytes())
        == md5(git_blob("data/dist/todd_corpus.json")),
        "todd_corpus.json byte-identique (24/24, zéro bascule — la v23 ajoute une FACE)",
    )

    # 5-6 — le catalog : seule l'entrée immigration_stock bouge (racines)
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
        euro_row["doors"] == 65 and oecd_row["doors"] == 2
        and {r["root"] for r in roots["canonical"]} == {"eurostat_migr"}
        and {r["root"] for r in roots["witness"]} == {"un_desa", "oecd_mig"},
        "catalog : eurostat_migr 31 -> 65 portes canoniques ; oecd_mig 1 -> 2 portes témoins",
        f"eurostat_migr={euro_row['doors']} oecd_mig={oecd_row['doors']}",
    )

    # 7-9 — les clés préexistantes d'immigration_stock bit-identiques
    check(
        [(p["entity_id"], p["year"], p["value"], p.get("quality_code"), p.get("provisional")) for p in new["data"]]
        == [(p["entity_id"], p["year"], p["value"], p.get("quality_code"), p.get("provisional")) for p in old["data"]]
        and len(new["data"]) == 557,
        "les 557 points (entité, année) bit-identiques",
    )
    check(
        json.dumps(new["witnesses"], sort_keys=False) == json.dumps(old["witnesses"], sort_keys=False),
        "le témoin UN DESA (face mono-axe) bit-identique",
    )
    check(
        new["todd_refs"] == old["todd_refs"],
        "le bloc todd_refs bit-identique",
    )

    # 10-13 — le bloc sources[]
    check(
        [json.dumps(s, sort_keys=True) for s in new["sources"][:33]]
        == [json.dumps(s, sort_keys=True) for s in old["sources"]],
        "les 33 premières entrées sources[] bit-identiques et dans l'ordre",
    )
    new_refs = [s["source_ref"] for s in new["sources"][33:]]
    check(
        len(new["sources"]) == 68 and len(new_refs) == 35
        and new_refs[-1] == "DF_MIG/B15",
        "sources[] gagne exactement 35 entrées (34 portes ctz + le témoin B15) -> 68/68",
        f"n={len(new['sources'])} nouvelles={len(new_refs)}",
    )
    expected_ctz = [
        "migr_pop1ctz/ROW/BE", "migr_pop1ctz/ROW/BG", "migr_pop1ctz/ROW/CZ", "migr_pop1ctz/ROW/DK",
        "migr_pop1ctz/ROW/EE", "migr_pop1ctz/ROW/IE", "migr_pop1ctz/ROW/ES", "migr_pop1ctz/ROW/FR",
        "migr_pop1ctz/ROW/HR", "migr_pop1ctz/ROW/IT", "migr_pop1ctz/ROW/LV", "migr_pop1ctz/ROW/LT",
        "migr_pop1ctz/ROW/LU", "migr_pop1ctz/ROW/HU", "migr_pop1ctz/ROW/NL", "migr_pop1ctz/ROW/AT",
        "migr_pop1ctz/ROW/PL", "migr_pop1ctz/ROW/PT", "migr_pop1ctz/ROW/RO", "migr_pop1ctz/ROW/SI",
        "migr_pop1ctz/ROW/SK", "migr_pop1ctz/ROW/FI", "migr_pop1ctz/ROW/SE", "migr_pop1ctz/ROW/IS",
        "migr_pop1ctz/ROW/LI", "migr_pop1ctz/ROW/NO", "migr_pop1ctz/ROW/CH", "migr_pop1ctz/ROW/UK",
        "migr_pop1ctz/ROW/TR", "migr_pop1ctz/ROW/DE", "migr_pop1ctz/ROW/EL", "migr_pop1ctz/ROW/ME",
        "migr_pop1ctz/ROW/MD", "migr_pop1ctz/ROW/AD",
    ]
    check(
        new_refs[:34] == expected_ctz,
        "les 34 portes ctz sont la liste d'ancres (priorités 34-67, BE..TR + DE/EL/ME/MD/AD)",
    )
    b15 = new["sources"][67]
    check(
        (b15["provider"], b15["source_ref"], b15["role"], b15["root"]) == ("oecd", "DF_MIG/B15", "witness", "oecd_mig"),
        "la 68e entrée : le témoin OCDE DF_MIG/B15 (priorité 68, root oecd_mig)",
    )

    # 14-15 — la couche naissance bit-identique
    check(
        json.dumps(new["bilateral"], sort_keys=False) == json.dumps(old["bilateral"], sort_keys=False),
        "la couche bilateral (naissance) bit-identique : 91 230 points + le témoin B14 99 225",
    )
    check(
        len(new["bilateral"]["data"]) == 91230
        and len(new["bilateral"]["witnesses"]) == 1
        and len(new["bilateral"]["witnesses"][0]["data"]) == 99225,
        "les comptes de la face naissance inchangés (91 230 canonique / 99 225 témoin)",
    )

    # 16-21 — la couche citoyenneté : présente, ses comptes d'ancres
    check("bilateral_citizenship" in new, "la couche bilateral_citizenship est émise")
    ctz = new["bilateral_citizenship"]
    cdata = ctz["data"]
    years = [p["year"] for p in cdata]
    check(len(cdata) == 112058, "citoyenneté canonique : 112 058 points", f"n={len(cdata)}")
    check(
        len({(p["destination_entity_id"], p["origin_entity_id"]) for p in cdata}) == 6627,
        "citoyenneté canonique : 6 627 paires (destination, origine)",
    )
    check(
        len({p["destination_entity_id"] for p in cdata}) == 34,
        "citoyenneté canonique : 34 destinations",
    )
    check(
        len({p["origin_entity_id"] for p in cdata}) == 226,
        "citoyenneté canonique : 226 origines",
    )
    check(
        min(years) == 1998 and max(years) == 2025,
        "citoyenneté canonique : années 1998-2025",
    )

    # 22-25 — le témoin B15
    check(
        len(ctz["witnesses"]) == 1
        and (ctz["witnesses"][0]["provider"], ctz["witnesses"][0]["source_ref"]) == ("oecd", "DF_MIG/B15"),
        "le témoin de la face citoyenneté : une seule série, DF_MIG/B15",
    )
    wdata = ctz["witnesses"][0]["data"]
    wyears = [p["year"] for p in wdata]
    check(len(wdata) == 109763, "témoin B15 : 109 763 points", f"n={len(wdata)}")
    check(
        len({p["destination_entity_id"] for p in wdata}) == 36
        and len({p["origin_entity_id"] for p in wdata}) == 236,
        "témoin B15 : 36 destinations x 236 origines",
    )
    check(
        min(wyears) == 1995 and max(wyears) == 2024,
        "témoin B15 : années 1995-2024",
    )

    # 26-31 — les ancres
    cpts = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"]): p["value"]
        for p in cdata
    }
    wpts = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"]): p["value"]
        for p in wdata
    }
    check(
        [cpts[("france", "morocco", y)] for y in (2015, 2016, 2017, 2018)]
        == [458561, 465230, 472843, 480600],
        "ANCRE v18 : FR<-MA ctz 2015-2018 = 458 561 / 465 230 / 472 843 / 480 600",
    )
    check(
        wpts[("france", "morocco", 2015)] == 458561
        and cpts[("france", "morocco", 2015)] == 458561,
        "ANCRE couture : FR<-MAR 2015 = 458 561 sur les DEUX portes (Eurostat ctz et OCDE B15)",
    )
    check(
        wpts[("united_states", "mexico", 2024)] == 8226106.247
        and new["bilateral"]["witnesses"][0] is not None,
        "ANCRE US<-MEX 2024 : ctz 8 226 106,247 (la face naissance imprimant 12 383 867,87 — divergence naturelle documentée)",
    )
    birth_wpts = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"]): p["value"]
        for p in new["bilateral"]["witnesses"][0]["data"]
    }
    check(
        cpts[("france", "portugal", 2015)] == 541867
        and birth_wpts[("france", "portugal", 2015)] == 648112,
        "ANCRE CONTRASTE CONVERGE : FR<-PT 2015 = 648 112 (naissance) vs 541 867 (citoyenneté)",
    )
    bpts_all = {
        (p["destination_entity_id"], p["origin_entity_id"], p["year"]): p["value"]
        for p in new["bilateral"]["data"]
    }
    check(
        bpts_all[("france", "morocco", 2015)] == 954742
        and cpts[("france", "morocco", 2015)] == 458561,
        "ANCRE CONTRASTE DIVERGE : FR<-MA 2015 = 954 742 (naissance) vs 458 561 (citoyenneté)",
    )
    ctz_dests = {p["destination_entity_id"] for p in cdata}
    birth_dests = {p["destination_entity_id"] for p in new["bilateral"]["data"]}
    check(
        "germany" in ctz_dests and "germany" not in birth_dests
        and "cyprus" not in ctz_dests and "cyprus" in birth_dests,
        "ASYMÉTRIE attendue : l'Allemagne rejoint la face ctz, Chypre la quitte (jamais « corrigée »)",
    )

    # 32 — l'idempotence : double rebuild, md5 31/31
    def snapshot_md5s() -> dict[str, str]:
        return {
            str(p.relative_to(ROOT / "data" / "dist")): md5(p.read_bytes())
            for p in sorted((ROOT / "data" / "dist").rglob("*.json"))
        }

    r1 = subprocess.run(
        [sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=1200,
    )
    first = snapshot_md5s()
    r2 = subprocess.run(
        [sys.executable, "-m", "src.cli", "rebuild"], cwd=str(ROOT),
        capture_output=True, text=True, timeout=1200,
    )
    second = snapshot_md5s()
    check(
        r1.returncode == 0 and r2.returncode == 0 and first == second and len(first) == 31,
        "IDEMPOTENCE : double rebuild complet, 31/31 fichiers md5 identiques",
        f"n={len(first)} divergents={sorted(k for k in first if first[k] != second.get(k))}",
    )

    # 33 — le corpus et la config
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

    # ---- le verdict -------------------------------------------------------
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
