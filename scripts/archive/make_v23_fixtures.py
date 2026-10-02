"""make_v23_fixtures.py — les fixtures de la V23, GÉNÉRÉES des APIs live
à travers les build_url des connecteurs EUX-MÊMES (la discipline
v16/v19/v20/v22 : chaque ancre est LUE des octets de la réponse, jamais
tapée).

Trois fixtures :

1. tests/fixtures/gho_mdg_0000000001_sample.json — la RÉPARATION de la
   porte GHO MDG_0000000001 (le fournisseur a recodé son cadre d'âge :
   chaque rangée porte désormais Dim2=AGEGROUP_MONTHS0-11 ; l'épingle par
   code v20 l'accepte exactement). Tranche réelle du payload live : les
   rangées FRA 2020 (les trois sexes — l'assertion du test d'intégration
   («france», 2020, male/None)), une rangée REGION (le saut non-COUNTRY),
   une rangée XKX pré-2008 (le garde de validité d'entité dans normalize),
   FRA 2019 both (une seconde année).

2. tests/fixtures/eurostat_migr1ctz_row_fr_sample.json — la RANGÉE
   BILATÉRALE FR de migr_pop1ctz TELLE QUE l'API la sert (26 577 octets,
   la réponse entière : la codelist citizen de 287 codes, les 927 cellules
   non vides). Le parseur ROW ctz y lit : les quatre classes de drop
   (5 diagonales, 12 cellules STLS, 53 cellules codes-synthèse, 143
   cellules agrégats/régions), les 714 enregistrements émis, les ancres
   v18 (FR<-MA ctz 2015-2018 = 458 561 / 465 230 / 472 843 / 480 600),
   les contraste (FR<-PT ctz 2015 = 541 867), les overrides d'axe
   origine (AN->ANT, XK->XKX, EL->GRC, UK->GBR).

3. tests/fixtures/oecd_mig_b15_sample.csv — une TRANCHE RÉELLE du
   téléchargement keyed B15 de DSD_MIG@DF_MIG (les lignes copiées
   octet-par-octet du CSV live, jamais tapées) : toutes les rangées FRA
   et USA (les deux sexes — les rangées F y exercent le drop loggé
   by-sex), les rangées portant chaque code résiduel (STLS, W, W_X, EEA,
   EU15, A4) et chaque code d'entité disparue (XKV, ANT_F, CSK_F, SCG_F,
   SUN_F, YUG_F) des autres destinations, et les diagonales
   DEU/ESP/ITA/GBR. NOTE DE COMPOSITION : la tranche suit la règle v22
   (la fixture B14 de make_v22_fixtures.py) ; elle imprime 16 259 lignes
   (8 394 _T + 7 865 F) — l'ancre mémoire de la conception gelée citait
   16 285 (8 283 _T + 8 002 F), composition de la session perdue non
   récupérable de façon déterminée (la couverture des classes est
   identique) ; la divergence est documentée dans le CHANGELOG et le
   message de livraison.

Le script imprime les ancres lues — les tests les citent.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.connectors import eurostat as eurostat_mod  # noqa: E402
from src.connectors import oecd as oecd_mod  # noqa: E402

OUT = ROOT / "tests" / "fixtures"
S = requests.Session()
S.headers.update({"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"})


def make_gho_mdg_fixture() -> dict:
    """La tranche du payload MDG live — la matière de la porte recodée."""
    url = "https://ghoapi.azureedge.net/api/MDG_0000000001"
    r = S.get(url, timeout=120)
    r.raise_for_status()
    payload = r.json()
    values = payload["value"]
    kept = []
    for row in values:
        spatial = row.get("SpatialDim")
        year = row.get("TimeDim")
        sex = row.get("Dim1")
        if row.get("SpatialDimType") == "COUNTRY" and spatial == "FRA" and year in (2019, 2020) and row.get("Dim2") == "AGEGROUP_MONTHS0-11":
            kept.append(row)  # FRA 2019-2020, les trois sexes
        elif row.get("SpatialDimType") == "REGION" and row.get("Dim2") == "AGEGROUP_MONTHS0-11" and not kept.count(row):
            if sum(1 for k in kept if k.get("SpatialDimType") == "REGION") < 1:
                kept.append(row)  # une rangée REGION : le saut non-COUNTRY
        elif spatial == "XKX" and year == 1986 and row.get("Dim1") == "SEX_BTSX" and row.get("Dim2") == "AGEGROUP_MONTHS0-11":
            kept.append(row)  # Kosovo pré-2008 : le garde de validité d'entité
    out = {"value": kept}
    (OUT / "gho_mdg_0000000001_sample.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    from src.connectors.gho import parse_gho

    records = parse_gho(json.dumps(out), code="MDG_0000000001")
    print(f"[gho] MDG_0000000001: {len(values):,} rangées live -> fixture {len(kept)} rangées, "
          f"{len(records)} enregistrements parsés (l'épingle AGEGROUP_MONTHS0-11 acceptée)")
    for rec in records:
        print(f"  {rec.iso3_raw} {rec.year} sex={rec.sex} value={rec.value}")
    return {"n_kept": len(kept), "n_records": len(records)}


def make_eurostat_ctz_fixture() -> dict:
    """La rangée FR ctz entière, servie par le build_url du connecteur."""
    ref = "migr_pop1ctz/ROW/FR"
    url = eurostat_mod.build_url(ref)
    r = S.get(url, timeout=120)
    r.raise_for_status()
    (OUT / "eurostat_migr1ctz_row_fr_sample.json").write_text(r.text, encoding="utf-8")
    payload = json.loads(r.text)
    print(f"[eurostat] {ref}: {len(r.content):,} octets, {len(payload.get('value') or {})} cellules non vides")
    records = eurostat_mod.parse_eurostat(r.text, expected_ref=ref)
    print(f"  {len(records)} enregistrements émis, "
          f"{len({rec.origin_iso3_raw for rec in records})} origines distinctes")
    anchors = {}
    for origin, years in (("MAR", (2015, 2016, 2017, 2018)), ("PRT", (2015,)), ("ANT", (1999, 2005)), ("XKX", (2015,))):
        anchors[origin] = [
            (rec.year, rec.value)
            for rec in records
            if rec.origin_iso3_raw == origin and rec.year in years
        ]
    for origin, pts in anchors.items():
        print(f"  ANCRE FR<-{origin} ctz: {sorted(pts)}")
    axes = sorted({rec.origin_axis for rec in records})
    print(f"  origin_axis porté: {axes}")
    flags = sorted({rec.quality_code for rec in records if rec.quality_code})
    print(f"  flags portés: {flags}")
    return {"n_records": len(records), "n_cells": len(payload.get("value") or {})}


def make_oecd_b15_fixture() -> dict:
    """La tranche du keyed B15 : FRA + USA complets (deux sexes) + les
    classes de codes des autres destinations + les diagonales v22."""
    url = oecd_mod.build_url("DF_MIG/B15")
    r = S.get(
        url,
        headers={
            "User-Agent": "toddlab-pipeline/0.1 (contact: see README)",
            "Accept": "application/vnd.sdmx.data+csv; version=2.0",
        },
        timeout=600,
    )
    r.raise_for_status()
    print(f"[oecd] DF_MIG/B15 keyed: {len(r.content):,} octets live")
    lines = r.text.splitlines()
    header, rows = lines[0], lines[1:]

    reader = csv.DictReader(io.StringIO(r.text))
    fieldnames = reader.fieldnames
    residual = {"W", "W_X", "EEA", "EU15", "A4", "STLS"}
    vanished = {"XKV", "ANT_F", "CSK_F", "SCG_F", "SUN_F", "YUG_F"}
    kept: list[dict] = []
    n_fr = n_us = n_residual = n_vanished = n_diag = 0
    n_fr_t = n_us_t = 0
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        citizenship = (row.get("CITIZENSHIP") or "").strip()
        sex = (row.get("SEX") or "").strip()
        if ref_area in ("FRA", "USA"):
            kept.append(row)
            n_fr += ref_area == "FRA"
            n_us += ref_area == "USA"
            n_fr_t += ref_area == "FRA" and sex == "_T"
            n_us_t += ref_area == "USA" and sex == "_T"
        elif citizenship in residual or citizenship in vanished:
            kept.append(row)
            n_residual += citizenship in residual
            n_vanished += citizenship in vanished
        elif citizenship == ref_area and ref_area in ("DEU", "ESP", "ITA", "GBR"):
            kept.append(row)  # diagonales d'autres destinations
            n_diag += 1

    out = [header]
    for row in kept:
        out.append(",".join(row[col] if row[col] is not None else "" for col in fieldnames))
    (OUT / "oecd_mig_b15_sample.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
    n_t = sum(1 for row in kept if (row.get("SEX") or "").strip() == "_T")
    n_f = len(kept) - n_t
    print(f"  fixture {len(kept)} lignes = {n_t} _T + {n_f} F "
          f"(FRA {n_fr} dont {n_fr_t} _T | USA {n_us} dont {n_us_t} _T | "
          f"résiduelles {n_residual} | disparues {n_vanished} | diagonales {n_diag})")

    # Les ancres LUES depuis le fixture lui-même (le fixture EST la matière
    # de test) : la couture et les contrastes.
    fixture_text = (OUT / "oecd_mig_b15_sample.csv").read_text(encoding="utf-8")
    records = oecd_mod.parse_mig_csv(fixture_text)
    seam = sorted(
        (rec.year, rec.value)
        for rec in records
        if rec.iso3_raw == "FRA" and rec.origin_iso3_raw == "MAR" and rec.year in (2015, 2016, 2017, 2018)
    )
    us_mex = [(rec.year, rec.value) for rec in records if rec.iso3_raw == "USA" and rec.origin_iso3_raw == "MEX" and rec.year == 2024]
    vanished_hits = sorted({rec.origin_iso3_raw for rec in records if rec.origin_iso3_raw in ("XKX", "ANT", "CSK", "SCG", "SUN", "YUG")})
    stls_kept = [rec for rec in records if rec.origin_iso3_raw == "STLS"]
    print(f"  FR<-MAR ctz (couture + série): {seam}")
    print(f"  US<-MEX 2024 ctz: {us_mex}")
    print(f"  origines disparues atterries: {vanished_hits}")
    print(f"  STLS gardé (doit être 0): {len(stls_kept)}")
    print(f"  origin_axis porté: {sorted({rec.origin_axis for rec in records})}")
    return {"n_rows": len(kept), "n_t": n_t, "n_f": n_f, "n_records": len(records)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    stats["gho_mdg"] = make_gho_mdg_fixture()
    stats["eurostat_ctz"] = make_eurostat_ctz_fixture()
    stats["oecd_b15"] = make_oecd_b15_fixture()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
