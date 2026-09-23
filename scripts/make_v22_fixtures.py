"""make_v22_fixtures.py — les fixtures de la face bilatérale v22, GÉNÉRÉES
des APIs live à travers les build_url des connecteurs EUX-MÊMES (la
discipline v16/v19/v20 : chaque ancre est LUE des octets de la réponse,
jamais tapée).

Deux portes, deux fixtures :

1. tests/fixtures/eurostat_migr_row_fr_sample.json — la RANGÉE BILATÉRALE
   FR de migr_pop3ctb TELLE QUE l'API la sert (32,976 octets, la réponse
   entière : la codelist c_birth de 307 codes, les 1,450 cellules non
   vides, les flags b/e/p). Le parseur ROW y lit : les trois classes de
   drop (150 cellules agrégats/régions, 76 cellules codes-synthèse,
   4 cellules diagonales), les 1,220 enregistrements émis, les ancres
   Todd (FR<-MA 2015 = 954,742 ; FR<-DZ 2018 = 1,390,284 ; FR<-PT 2025 =
   599,492 ; FR<-AN 1999 = 78, la entité disparue des Antilles), les
   overrides d'axe origine (AN->ANT, EL->GRC).

2. tests/fixtures/oecd_migf_sample.csv — une TRANCHE RÉELLE du
   téléchargement empty-key /all de DF_MIG_POPF (les lignes copiées
   octet-par-octet du CSV live, jamais tapées) : toutes les rangées FR et
   US (les deux sexes — les rangées F y exercent le drop loggé by-sex),
   les rangées portant chaque code résiduel (W, W_X, EEA, EU15, A4,
   STLS) et chaque code d'entité disparue (XKV, ANT_F, CSK_F, SCG_F,
   SUN_F, YUG_F), et les diagonales (FR<-FR, US<-US). Les ancres y sont
   lues : la couture FR<-MAR _T 2015 = 954,742 (l'ancienne l'impression
   Eurostat EXACTE), l'extension 2019-2021, US<-MEX 2024.

Le script imprime les ancres lues — les tests les citent.
"""
from __future__ import annotations

import csv
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


def make_eurostat_row_fixture() -> dict:
    """La rangée FR entière, servie par le build_url du connecteur."""
    ref = "migr_pop3ctb/ROW/FR"
    url = eurostat_mod.build_url(ref)
    r = S.get(url, timeout=120)
    r.raise_for_status()
    (OUT / "eurostat_migr_row_fr_sample.json").write_text(r.text, encoding="utf-8")
    payload = json.loads(r.text)

    # Les ancres LUES (imprimées pour le compte-rendu — les tests les citent).
    records = eurostat_mod.parse_eurostat(r.text, expected_ref=ref)
    anchors: dict[str, list] = {}
    for origin, years in (("MAR", (2015, 2018)), ("DZA", (1999, 2018)), ("TUN", (2018,)), ("TUR", (2018,)), ("PT", (1999, 2025)), ("ANT", (1999, 2005)), ("GRC", (1999,))):
        anchors[origin] = [
            (rec.year, rec.value)
            for rec in records
            if rec.origin_iso3_raw == origin and rec.year in years
        ]
    print(f"[eurostat] ROW/FR: {len(r.content):,} bytes, {len(records)} records parsed")
    for origin, pts in anchors.items():
        print(f"  FR<-{origin}: {pts}")
    flags = sorted({rec.quality_code for rec in records if rec.quality_code})
    print(f"  flags carried: {flags}")
    return {"n_records": len(records)}


def make_oecd_migf_fixture() -> dict:
    """La tranche du /all : FR + US complets + les classes de codes."""
    url = oecd_mod.build_url("DF_MIG_POPF")
    r = S.get(
        url,
        headers={
            "User-Agent": "toddlab-pipeline/0.1 (contact: see README)",
            "Accept": "application/vnd.sdmx.data+csv; version=2.0",
        },
        timeout=300,
    )
    r.raise_for_status()
    lines = r.text.splitlines()
    header, rows = lines[0], lines[1:]

    reader = csv.DictReader(r.text.splitlines())
    fieldnames = reader.fieldnames
    # Les classes à couvrir : les deux destinations complètes (FR/US, tous
    # sexes), chaque code résiduel, chaque code disparu, quelques diagonales
    # d'autres destinations pour la garde par rangée.
    residual = {"W", "W_X", "EEA", "EU15", "A4", "STLS"}
    vanished = {"XKV", "ANT_F", "CSK_F", "SCG_F", "SUN_F", "YUG_F"}
    kept: list[dict] = []
    n_fr = n_us = n_residual = n_vanished = n_diag = 0
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        birth = (row.get("BIRTH_COUNTRY") or "").strip()
        if ref_area in ("FRA", "USA"):
            kept.append(row)
            n_fr += ref_area == "FRA"
            n_us += ref_area == "USA"
        elif birth in residual or birth in vanished:
            kept.append(row)
            n_residual += birth in residual
            n_vanished += birth in vanished
        elif birth == ref_area and ref_area in ("DEU", "ESP", "ITA", "GBR"):
            kept.append(row)  # diagonales d'autres destinations
            n_diag += 1

    out = [header]
    for row in kept:
        out.append(",".join(row[col] if row[col] is not None else "" for col in fieldnames))
    (OUT / "oecd_migf_sample.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[oecd] DF_MIG_POPF /all: {len(r.content):,} bytes live -> fixture {len(kept)} rows")
    print(f"  FRA rows: {n_fr} (both sexes) | USA rows: {n_us} | residual-code rows: {n_residual} | vanished-code rows: {n_vanished} | diagonals: {n_diag}")

    # Les ancres LUES depuis le fixture lui-même (pas depuis le live — le
    # fixture EST la matière de test) : la couture et l'extension.
    fixture_text = (OUT / "oecd_migf_sample.csv").read_text(encoding="utf-8")
    records = oecd_mod.parse_migf_csv(fixture_text)
    seam = [
        (rec.year, rec.value)
        for rec in records
        if rec.iso3_raw == "FRA" and rec.origin_iso3_raw == "MAR" and rec.year in (2015, 2018, 2019, 2020, 2021)
    ]
    us_mex = [(rec.year, rec.value) for rec in records if rec.iso3_raw == "USA" and rec.origin_iso3_raw == "MEX" and rec.year == 2024]
    us_w = [rec for rec in records if rec.iso3_raw == "USA" and rec.origin_iso3_raw == "W"]
    vanished_hits = sorted({rec.origin_iso3_raw for rec in records if rec.origin_iso3_raw in ("XKX", "ANT", "CSK", "SCG", "SUN", "YUG")})
    print(f"  FR<-MAR (seam + extension): {sorted(seam)}")
    print(f"  US<-MEX 2024: {us_mex}")
    print(f"  US<-W kept (must be 0): {len(us_w)}")
    print(f"  vanished origins landed: {vanished_hits}")
    return {"n_records": len(records), "n_rows": len(kept)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    stats["eurostat"] = make_eurostat_row_fixture()
    stats["oecd"] = make_oecd_migf_fixture()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
