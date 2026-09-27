"""make_v24_fixtures.py — les fixtures de la face by-sex (V24), GÉNÉRÉES
des APIs live à travers le build_url du connecteur EUX-MÊME (la
discipline v16..v23 : chaque ancre est LUE des octets de la réponse,
jamais tapée).

Deux fixtures (une par face, un sexe chacune — le matériel minimal qui
exerce la grammaire ROW/{geo}/{sex} sur les deux datasets) :

1. tests/fixtures/eurostat_migr3ctb_row_fr_m_sample.json — la
   VENTILATION MASCULINE de la rangée FR de migr_pop3ctb (sex=M épinglé
   dans l'URL, le reste identique à la porte _T) : 1,220 enregistrements
   émis, sex="male", origin_axis="birth", les ancres FR<-MA M 2015/2018
   = 479,354/492,723 (et M + F = le _T à l'unité : 479,354 + 475,388 =
   954,742, l'anc _T de la fixture v22).

2. tests/fixtures/eurostat_migr1ctz_row_fr_f_sample.json — la
   VENTILATION FÉMININE de la rangée FR de migr_pop1ctz (sex=F) : 714
   enregistrements, sex="female", origin_axis="citizenship", les ancres
   FR<-MA F 2015/2018 = 226,668/243,044 (l'accord à l'unité avec la
   face F du témoin OCDE B15, la même paire d'impressions).

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

OUT = ROOT / "tests" / "fixtures"
S = requests.Session()
S.headers.update({"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"})


def make_row_sex_fixture(ref: str, out_name: str) -> dict:
    url = eurostat_mod.build_url(ref)
    r = S.get(url, timeout=120)
    r.raise_for_status()
    (OUT / out_name).write_text(r.text, encoding="utf-8")
    payload = json.loads(r.text)
    records = eurostat_mod.parse_eurostat(r.text, expected_ref=ref)
    print(f"[eurostat] {ref}: {len(r.content):,} octets, {len(payload.get('value') or {})} cellules non vides")
    print(f"  {len(records)} enregistrements, sex={ {rec.sex for rec in records} }, "
          f"axis={ {rec.origin_axis for rec in records} }")
    got = {(rec.origin_iso3_raw, rec.year): rec.value for rec in records}
    for origin, years in (("MAR", (2015, 2018)), ("PRT", (2015,))):
        pts = sorted((y, v) for (o, y), v in got.items() if o == origin and y in years)
        print(f"  ANCRE FR<-{origin}: {pts}")
    return {"n_records": len(records)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    stats["birth_m"] = make_row_sex_fixture(
        "migr_pop3ctb/ROW/FR/M", "eurostat_migr3ctb_row_fr_m_sample.json"
    )
    stats["ctz_f"] = make_row_sex_fixture(
        "migr_pop1ctz/ROW/FR/F", "eurostat_migr1ctz_row_fr_f_sample.json"
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
