"""make_v25_fixtures.py — les fixtures de la V25, GÉNÉRÉES des APIs live
à travers le build_url des connecteurs EUX-MÊMES (la discipline
v16..v24 : chaque ancre est LUE des octets de la réponse, jamais tapée).

Sept fixtures (les portes nouvelles de la V25) :

1. tests/fixtures/eurostat_lfsa_urgacob_t_sample.json — la face
   NAISSANCE complète : la réponse intégrale de
   lfsa_urgacob/Y15-74/T (36 géos imprimants, la codelist c_birth
   ouverte, les classes natives/foreign_born/eu_born/non_eu_born,
   TOTAL/NRP chutées loggées) — les ancres FR 2015 : natives 9.4,
   foreign_born 17.1, eu_born 10.7, non_eu_born 19.0.

2. tests/fixtures/eurostat_lfsa_urgan_t_sample.json — la face
   CIToyenneté complète : lfsa_urgan/Y15-74/T (35 géos, la codelist
   citizen ouverte, STLS/NRP/TOTAL chutées loggées) — les ancres
   FR 2015 : nationals 9.7, foreigners 20.5, eu_foreigners 12.6,
   non_eu_foreigners 24.5 (la planche Destin).

3. tests/fixtures/eurostat_unert_m_sample.json — la ventilation
   MASCULINE du taux simple : une_rt_a/Y15-74/PC_ACT/M — l'ancre
   FR M 2015 = 10.8 (l'anc v17, re-lu live).

4. tests/fixtures/eurostat_unert_f_sample.json — la ventilation
   FÉMININE : une_rt_a/Y15-74/PC_ACT/F — l'ancre FR F 2015 = 9.9.

5. tests/fixtures/ilostat_cbr_sample.json — le témoin NAISSANCE :
   la réponse intégrale du flux DF_UNE_DEAP_SEX_AGE_CBR_RT sur la
   clé câblée (145 aires, NATIVE/FOREIGN, les deux sexes, la coupe)
   — l'ancre FR 2025 : natives 7.023, foreign_born 12.003.

6. tests/fixtures/ilostat_cct_sample.json — le témoin CIToyenneté :
   DF_UNE_DEAP_SEX_AGE_CCT_RT (137 aires, CITIZEN/NONCIT, les deux
   sexes) — les ancres FR 2025 : nationals 7.162, foreigners 13.902
   ; le KOS->XKX quirck (6 enregistrements Kosovo).

7. tests/fixtures/itf_10p4veh_sample.csv — la face par véhicule
   INTÉGRALE : DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD (534 lignes,
   38 aires, 1994-2024) — les ancres FRA 2010 = 0.9497, FRA 2024 =
   0.6512, CHE 1994 = 1.6303, CHL 1998 = 13.1494.

Le script imprime les ancres lues — les tests les citent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.connectors import eurostat as eurostat_mod  # noqa: E402
from src.connectors import ilostat as ilostat_mod  # noqa: E402
from src.connectors import oecd as oecd_mod  # noqa: E402

OUT = ROOT / "tests" / "fixtures"
S = requests.Session()
S.headers.update({"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"})


def make_eurostat_fixture(ref: str, out_name: str) -> dict:
    url = eurostat_mod.build_url(ref)
    r = S.get(url, timeout=180)
    r.raise_for_status()
    (OUT / out_name).write_text(r.text, encoding="utf-8")
    payload = json.loads(r.text)
    records = eurostat_mod.parse_eurostat(r.text, expected_ref=ref)
    n_cells = len(payload.get("value") or {})
    print(f"[eurostat] {ref}: {len(r.content):,} octets, {n_cells} cellules non vides")
    classes = {}
    for rec in records:
        classes.setdefault(rec.population_class, set()).add(rec.iso3_raw)
    for cls in sorted(classes):
        print(f"  classe {cls}: {len(classes[cls])} géos")
    if "lfsa" in ref:
        got = {(rec.iso3_raw, rec.population_class): rec.value for rec in records if rec.year == 2015 and rec.iso3_raw == "FRA"}
        print(f"  ANCRE FR 2015: { {k[1]: v for k, v in sorted(got.items())} }")
    if "une_rt_a" in ref:
        got = sorted((rec.year, rec.value) for rec in records if rec.iso3_raw == "FRA" and rec.year in (2015, 2024))
        print(f"  ANCRE FR: {got}")
        print(f"  sex={ {rec.sex for rec in records} }")
    return {"n_records": len(records), "n_cells": n_cells}


def make_ilostat_fixture(ref: str, out_name: str) -> dict:
    url = ilostat_mod.build_url(ref)
    r = S.get(url, timeout=300)
    r.raise_for_status()
    (OUT / out_name).write_text(r.text, encoding="utf-8")
    records = ilostat_mod.parse_ilostat(r.text, expected_ref=ref)
    areas = {rec.iso3_raw for rec in records}
    classes = {rec.population_class for rec in records}
    sexes = {rec.sex for rec in records}
    print(f"[ilostat] {ref}: {len(r.content):,} octets, {len(records)} enregistrements, "
          f"{len(areas)} aires, classes={sorted(classes)}, sexes={sorted(str(s) for s in sexes)}")
    anchors = sorted(
        (rec.year, rec.population_class, rec.sex or "_T", rec.value)
        for rec in records if rec.iso3_raw == "FRA" and rec.year == 2025
    )
    print(f"  ANCRE FR 2025: {anchors}")
    kosovo = [rec for rec in records if rec.iso3_raw == "XKX"]
    print(f"  Kosovo (KOS->XKX): {len(kosovo)} enregistrements, ex. "
          f"{[(k.year, k.population_class, k.value) for k in kosovo[:3]]}")
    return {"n_records": len(records), "n_areas": len(areas)}


def make_itf_fixture(out_name: str) -> dict:
    ref = "DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD"
    url = oecd_mod.build_url(ref)
    r = S.get(
        url,
        headers={"Accept": "application/vnd.sdmx.data+csv; version=2.0"},
        timeout=300,
    )
    r.raise_for_status()
    (OUT / out_name).write_text(r.text, encoding="utf-8")
    from src.connectors.oecd import parse_safety_csv

    records = parse_safety_csv(r.text, measure="FATALITIES", unit="10P4VEH_MOT_ROAD")
    areas = {rec.iso3_raw for rec in records}
    print(f"[oecd/itf] {ref}: {len(r.content):,} octets, {len(records)} enregistrements, {len(areas)} aires")
    got = {(rec.iso3_raw, rec.year): rec.value for rec in records}
    for area, year in (("FRA", 2010), ("FRA", 2024), ("CHE", 1994), ("CHL", 1998), ("USA", 2023)):
        print(f"  ANCRE {area} {year}: {got.get((area, year))}")
    return {"n_records": len(records), "n_areas": len(areas)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats: dict = {}
    stats["urgacob_t"] = make_eurostat_fixture(
        "lfsa_urgacob/Y15-74/T", "eurostat_lfsa_urgacob_t_sample.json"
    )
    stats["urgan_t"] = make_eurostat_fixture(
        "lfsa_urgan/Y15-74/T", "eurostat_lfsa_urgan_t_sample.json"
    )
    stats["unert_m"] = make_eurostat_fixture(
        "une_rt_a/Y15-74/PC_ACT/M", "eurostat_unert_m_sample.json"
    )
    stats["unert_f"] = make_eurostat_fixture(
        "une_rt_a/Y15-74/PC_ACT/F", "eurostat_unert_f_sample.json"
    )
    stats["ilo_cbr"] = make_ilostat_fixture(
        "DF_UNE_DEAP_SEX_AGE_CBR_RT", "ilostat_cbr_sample.json"
    )
    stats["ilo_cct"] = make_ilostat_fixture(
        "DF_UNE_DEAP_SEX_AGE_CCT_RT", "ilostat_cct_sample.json"
    )
    stats["itf_veh"] = make_itf_fixture("itf_10p4veh_sample.csv")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
