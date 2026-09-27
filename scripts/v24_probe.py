"""v24_probe.py — les sondes de la face by-sex (V24), selon la direction
approuvée par Ediz (§6) : « brancher les ventilations M/F des mêmes
portes migr_pop, sur les deux faces (lieu de naissance et
citoyenneté) » côté Eurostat, et « débloquer plutôt que re-télécharger »
les lignes F côté OCDE. La conception détaillée se gèle sur ces sorties.

Sondes :
  A. la rangée FR en M et en F sur CHAQUE face Eurostat (migr_pop3ctb,
     migr_pop1ctz) : cellules, origines, années, ancres — la ventilation
     existe-t-elle et que dit-elle ?
  B. le périmètre M/F réel : les 64 portes câblées (30 naissance +
     34 citoyenneté) interrogées en sex=M puis sex=F — quelles
     destinations impriment la ventilation ?
  C. le contenu exact des lignes F de B15 (le téléchargement complet
     déjà en cache) : compte, couverture, ancres, et la vérification
     qu'AUCUNE ligne M n'existe sur le flow.
  D. le contenu exact des lignes F de B14 (téléchargement live — le
     snapshot ne porte que les enregistrements parsés _T, les lignes F
     ne vivent que dans la réponse) : compte, couverture, ancres.

Chaque fait est LU de la réponse live, jamais tapé.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

S = requests.Session()
S.headers.update({"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"})

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest/data"
OECD_DF_MIGF_FLOW = "OECD.ELS.IMD,DSD_MIG_F@DF_MIG_POPF,1.0"
OECD_DF_MIG_FLOW = "OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0"

BIRTH_GEOS = [
    "BE", "BG", "CZ", "DK", "EE", "IE", "ES", "FR", "HR", "IT", "CY", "LV",
    "LT", "LU", "HU", "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI", "SE",
    "IS", "LI", "NO", "CH", "UK", "TR",
]
CTZ_GEOS = BIRTH_GEOS[:10] + BIRTH_GEOS[11:] + ["DE", "EL", "ME", "MD", "AD"]  # -CY, +4 (= 34)


def row_url(dataset: str, geo: str, sex: str) -> str:
    return f"{EUROSTAT_API}/{dataset}?format=JSON&lang=EN&geo={geo}&age=TOTAL&sex={sex}&unit=NR"


def fetch_json(url: str, timeout: int = 120) -> dict:
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return json.loads(r.text)


def row_stats(payload: dict, geo: str) -> dict:
    """Cellules pays (hors diagonale, hors STLS/synthèse/agrégats) d'une
    rangée — la même classification que le parseur ROW."""
    dim_order, size = payload["id"], payload["size"]
    sizes = dict(zip(dim_order, size))
    strides = {}
    mult = 1
    for d in reversed(dim_order):
        strides[d] = mult
        mult *= sizes[d]
    origin_dim = "citizen" if "citizen" in sizes else "c_birth"
    inv_o = {v: k for k, v in payload["dimension"][origin_dim]["category"]["index"].items()}
    inv_t = {v: k for k, v in payload["dimension"]["time"]["category"]["index"].items()}
    n_country = 0
    origins = set()
    years = set()
    values = {}
    for pos_text in (payload.get("value") or {}):
        pos = int(pos_text)
        code = inv_o.get((pos // strides[origin_dim]) % sizes[origin_dim])
        year = int(inv_t[(pos // strides["time"]) % sizes["time"]])
        if code is None or len(code) != 2 or not code.isalpha() or not code.isupper():
            continue
        if code == geo or code in ("NAT", "TOTAL", "UNK", "FOR", "OTH", "RNC", "STLS"):
            continue
        n_country += 1
        origins.add(code)
        years.add(year)
        values[(code, year)] = (payload["value"])[pos_text]
    return {
        "n_cells": len(payload.get("value") or {}),
        "n_country": n_country,
        "n_origins": len(origins),
        "years": (min(years), max(years)) if years else None,
        "values": values,
    }


def probe_a_fr_rows() -> None:
    print("=" * 72)
    print("SONDE A — la rangée FR en M et en F, les deux faces Eurostat")
    print("=" * 72)
    for dataset, face in (("migr_pop3ctb", "naissance"), ("migr_pop1ctz", "citoyenneté")):
        for sex in ("M", "F"):
            p = fetch_json(row_url(dataset, "FR", sex))
            st = row_stats(p, "FR")
            print(f"  {dataset} FR sex={sex} ({face}): {st['n_cells']} cellules, "
                  f"{st['n_country']} cellules pays, {st['n_origins']} origines, "
                  f"{st['years'] and (st['years'][0], st['years'][1])}")
            # les ancres M/F de FR<-MA et FR<-PT
            for origin in ("MA", "PT"):
                pts = sorted((y, v) for (o, y), v in st["values"].items() if o == origin and y in (2015, 2018))
                print(f"    FR<-{origin} sex={sex}: {pts}")


def probe_b_perimeter() -> dict:
    print()
    print("=" * 72)
    print("SONDE B — le périmètre M/F réel (64 portes x 2 sexes)")
    print("=" * 72)
    results = {}
    for dataset, geos, face in (
        ("migr_pop3ctb", BIRTH_GEOS, "naissance"),
        ("migr_pop1ctz", CTZ_GEOS, "citoyenneté"),
    ):
        for sex in ("M", "F"):
            printing = []
            for geo in geos:
                try:
                    p = fetch_json(row_url(dataset, geo, sex))
                except Exception as e:  # noqa: BLE001
                    print(f"  {dataset} {geo} sex={sex}: ÉCHEC {e}")
                    continue
                st = row_stats(p, geo)
                if st["n_country"] > 0:
                    printing.append((geo, st["n_country"]))
                time.sleep(0.08)
            results[(dataset, sex)] = printing
            print(f"  {dataset} sex={sex} ({face}): {len(printing)}/{len(geos)} géos impriment "
                  f"le détail M/F")
            print(f"    {[(g, n) for g, n in printing]}")
    return results


def _oecd_f_analysis(text: str, label: str, origin_col: str = "CITIZENSHIP") -> dict:
    reader = csv.DictReader(io.StringIO(text))
    sex_counts = {}
    f_rows = []
    for row in reader:
        ra = (row.get("REF_AREA") or "").strip()
        if not ra or ra == "REF_AREA":
            continue
        year_raw = (row.get("TIME_PERIOD") or "").strip()
        if not year_raw:
            continue
        sex = (row.get("SEX") or "").strip()
        sex_counts[sex] = sex_counts.get(sex, 0) + 1
        if sex == "F":
            val_raw = (row.get("OBS_VALUE") or "").strip()
            f_rows.append((ra, (row.get(origin_col) or "").strip(), int(year_raw),
                           float(val_raw) if val_raw else None))
    print(f"  [{label}] répartition SEX : {dict(sorted(sex_counts.items()))}")
    f_dests = {r[0] for r in f_rows}
    f_origins = {r[1] for r in f_rows}
    f_years = {r[2] for r in f_rows}
    print(f"  [{label}] lignes F : {len(f_rows):,} | {len(f_dests)} destinations x "
          f"{len(f_origins)} origines | {min(f_years)}-{max(f_years)}")
    # les ancres F : FR<-MAR 2015/2018, US<-MEX 2024
    for dest, orig, y in (("FRA", "MAR", 2015), ("FRA", "MAR", 2018), ("USA", "MEX", 2024), ("FRA", "PRT", 2015)):
        hits = [r for r in f_rows if r[0] == dest and r[1] == orig and r[2] == y]
        print(f"    {dest}<-{orig} F {y}: {[h[3] for h in hits]}")
    return {"n_f": len(f_rows), "n_dests": len(f_dests), "n_origins": len(f_origins), "sex_counts": sex_counts}
    print()
    print("=" * 72)
    print("SONDE C — les lignes F de B15 (le téléchargement en cache)")
    print("=" * 72)
    text = (ROOT / "data" / "tmp" / "oecd_mig_b15_full.csv").read_text(encoding="utf-8")
    return _oecd_f_analysis(text, "B15")


def probe_d_b14_f() -> dict:
    print()
    print("=" * 72)
    print("SONDE D — les lignes F de B14 (téléchargement live)")
    print("=" * 72)
    url = f"{OECD_SDMX_BASE}/{OECD_DF_MIGF_FLOW}/all?dimensionAtObservation=AllDimensions"
    r = S.get(url, headers={"Accept": "application/vnd.sdmx.data+csv; version=2.0"}, timeout=600)
    r.raise_for_status()
    print(f"  téléchargement : {len(r.content):,} octets")
    (ROOT / "data" / "tmp").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "tmp" / "oecd_migf_b14_full.csv").write_text(r.text, encoding="utf-8")
    return _oecd_f_analysis(r.text, "B14", origin_col="BIRTH_COUNTRY")


def main() -> None:
    probe_a_fr_rows()
    probe_b_perimeter()
    probe_c_b15_f()
    probe_d_b14_f()


if __name__ == "__main__":
    main()
