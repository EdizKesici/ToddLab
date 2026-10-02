"""v23_probe.py — les cinq sondes de la face citoyenneté (V23), selon la
conception gelée §5. Chaque fait est LU de la réponse live, jamais tapé.

Sondes :
  A. grammaire de ref — migr_pop1ctz/ROW/{geo} : layout, pins, codelist
     citizen ; + le témoin OCDE B15 : DSD_MIG@DF_MIG, clé positionnelle
     '..A.B15.._Z._Z.PS', en-tête CSV, titre du flow au registre.
  B. dimensions et périmètre — la rangée FR parsée : cellules, classes de
     drop, enregistrements émis, origines pays.
  C. années couvertes — min/max Eurostat (attendu 1998-2025) et OCDE
     (attendu 1995-2024).
  D. géographie de la face — les 44 géos candidats de la face naissance,
     chacune sa porte ctz épinglée : lesquelles impriment le détail par
     origine (attendu 34, Allemagne dedans, Chypre dehors).
  E. témoin OCDE B15 — le téléchargement keyed complet : lignes brutes,
     vocabulaire de drop appliqué (STLS, diagonale citizen==geo, agrégats
     NAT/TOTAL/UNK, codes éteints XKV/ANT_F/CSK_F/SCG_F/SUN_F/YUG_F,
     lignes F), points, destinations x origines, ancres.

Le script imprime chaque fait lu ; la conception se gèle sur ces sorties.
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
OECD_DF_MIG_FLOW = "OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0"
B15_KEY = "..A.B15.._Z._Z.PS"

# Les 44 géos candidats = l'univers de la face naissance (v22 : 30 cablées
# + 14 totals-seuls). La sonde D les interroge toutes sur la face ctz.
CANDIDATE_GEOS = [
    "BE", "BG", "CZ", "DK", "EE", "IE", "ES", "FR", "HR", "IT", "CY", "LV",
    "LT", "LU", "HU", "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI", "SE",
    "IS", "LI", "NO", "CH", "UK", "TR",  # les 30 cablées v22
    "DE", "EL", "MT", "ME", "MD", "MK", "GE", "AL", "RS", "UA", "AD", "MC",
    "AM", "AZ",  # les 14 totals-seuls v22
]


def ctz_row_url(geo: str) -> str:
    """La porte ROW ctz : geo épinglé, citizen NON épinglé, le cadre
    age=TOTAL/sex=T/unit=NR épinglé (miroir exact de la face naissance)."""
    return f"{EUROSTAT_API}/migr_pop1ctz?format=JSON&lang=EN&geo={geo}&age=TOTAL&sex=T&unit=NR"


def fetch_json(url: str, timeout: int = 120) -> dict:
    r = S.get(url, timeout=timeout)
    r.raise_for_status()
    return json.loads(r.text)


def classify_citizen_codes(payload: dict) -> dict:
    """Classe la codelist citizen en : pays 2 lettres, codes-synthèse,
    STLS, agrégats/régions (codes plus longs)."""
    idx = payload["dimension"]["citizen"]["category"]["index"]
    labels = payload["dimension"]["citizen"]["category"]["label"]
    classes = {"country": [], "summary": [], "stateless": [], "aggregate": []}
    for code in idx:
        if len(code) == 2 and code.isalpha() and code.isupper():
            classes["country"].append(code)
        elif code in ("NAT", "TOTAL", "UNK", "FOR", "OTH", "RNC"):
            classes["summary"].append(code)
        elif code == "STLS":
            classes["stateless"].append(code)
        else:
            classes["aggregate"].append(code)
    return {"codes": classes, "labels": labels, "n": len(idx)}


def probe_a_grammar() -> dict:
    print("=" * 72)
    print("SONDE A — grammaire de ref")
    print("=" * 72)
    p = fetch_json(ctz_row_url("FR"))
    print(f"[eurostat] migr_pop1ctz/ROW/FR : {len(json.dumps(p)):,} chars")
    print(f"  label      : {p.get('label')}")
    print(f"  id         : {p.get('id')}")
    print(f"  size       : {p.get('size')}")
    print(f"  cellules non vides : {len(p.get('value') or {})}")
    dim = p["dimension"]
    print(f"  freq       : {dim['freq']['category']['index']}")
    for d in ("age", "unit", "sex"):
        print(f"  pin {d:<6}: {dim[d]['category']['index']}")
    print(f"  pin geo    : {dim['geo']['category']['index']}")
    years = sorted(dim["time"]["category"]["index"])
    print(f"  années     : {years[0]}..{years[-1]} ({len(years)} entrées)")
    cls = classify_citizen_codes(p)
    print(f"  codelist citizen : {cls['n']} codes -> "
          f"{len(cls['codes']['country'])} pays, {len(cls['codes']['summary'])} synthèse "
          f"{cls['codes']['summary']}, STLS={cls['codes']['stateless']}, "
          f"{len(cls['codes']['aggregate'])} agrégats/régions")
    # Les codes retirés du ISO 3166 que la codelist porte-t-elle ?
    import pycountry
    quirks = [c for c in cls["codes"]["country"] if pycountry.countries.get(alpha_2=c) is None]
    print(f"  codes 2 lettres sans pycountry (overrides nécessaires) : {quirks}")
    for q in quirks:
        print(f"    {q} = {cls['labels'].get(q)!r}")
    # Le registre OCDE : le titre du flow DSD_MIG@DF_MIG
    title = None
    for accept in (
        "application/vnd.sdmx.structure+json; version=2.0",
        "application/vnd.sdmx.structure+json",
    ):
        try:
            r = S.get(
                "https://sdmx.oecd.org/public/rest/dataflow/OECD.ELS.IMD/DSD_MIG@DF_MIG/1.0",
                headers={"Accept": accept},
                timeout=60,
            )
            if r.status_code == 200:
                reg = r.json()
                flows = reg.get("data", {}).get("dataflows", [])
                for f in flows:
                    if f.get("id") == "DF_MIG":
                        names = f.get("name") or []
                        title = names[0].get("value") if names else None
                break
        except Exception as e:  # noqa: BLE001 — la sonde essaie, elle ne devine pas
            print(f"  registry essai ({accept[:40]}...) : {e}")
    print(f"[oecd] registre DSD_MIG@DF_MIG v1.0 : titre = {title!r}")
    return {"payload": p, "classes": cls, "oecd_title": title}


def probe_b_perimeter(p_fr: dict, cls: dict) -> dict:
    print()
    print("=" * 72)
    print("SONDE B — dimensions et périmètre (la rangée FR)")
    print("=" * 72)
    # Décode row-major : [freq, citizen, age, unit, sex, geo, time]
    dim_order = p_fr["id"]
    size = p_fr["size"]
    sizes = dict(zip(dim_order, size))
    strides = {}
    mult = 1
    for d in reversed(dim_order):
        strides[d] = mult
        mult *= sizes[d]
    inv_cit = {v: k for k, v in p_fr["dimension"]["citizen"]["category"]["index"].items()}
    inv_time = {v: k for k, v in p_fr["dimension"]["time"]["category"]["index"].items()}
    values = p_fr["value"]
    status = p_fr.get("status") or {}
    summary = set(cls["codes"]["summary"])
    aggregates = set(cls["codes"]["aggregate"])
    stateless = set(cls["codes"]["stateless"])
    n_country = n_summary = n_agg = n_stls = n_diag = 0
    origins = set()
    records = []
    for pos_text, val in values.items():
        pos = int(pos_text)
        citizen = inv_cit[(pos // strides["citizen"]) % sizes["citizen"]]
        year = int(inv_time[(pos // strides["time"]) % sizes["time"]])
        if citizen == "FR":
            n_diag += 1
            continue
        if citizen in stateless:
            n_stls += 1
            continue
        if citizen in summary:
            n_summary += 1
            continue
        if citizen in aggregates:
            n_agg += 1
            continue
        n_country += 1
        origins.add(citizen)
        records.append((citizen, year, val, status.get(pos_text)))
    print(f"  cellules non vides      : {len(values)}")
    print(f"  diagonal FR<-FR         : {n_diag}")
    print(f"  STLS                    : {n_stls}")
    print(f"  codes synthèse droppés  : {n_summary}")
    print(f"  agrégats/régions droppés: {n_agg}")
    print(f"  cellules pays émises    : {n_country} -> {len(origins)} origines distinctes pour FR")
    # Les ancres v18 : la face ctz de FR<-MA
    for target, years_wanted in (("MA", (2015, 2016, 2017, 2018)),):
        pts = [(y, v) for (c, y, v, _) in records if c == target and y in years_wanted]
        print(f"  ANCRE v18 FR<-{target} ctz : {sorted(pts)}")
    # Le témoin croisé Eurostat/OECD : FR<-MA 2015 (458 561 attendu des deux côtés)
    ma15 = [v for (c, y, v, _) in records if c == "MA" and y == 2015]
    print(f"  ANCRE couture FR<-MA 2015 ctz : {ma15}")
    # Le contraste FR<-PT (§5.4 : 648 112 citoyenneté)
    pt = sorted((y, v) for (c, y, v, _) in records if c == "PT")
    print(f"  FR<-PT ctz série : {pt}")
    # Contraste FR<-MA naissance (§5.4 : 954 742) lu du dist v22 commité
    dist = json.loads((ROOT / "data" / "dist" / "indicators" / "immigration_stock.json").read_text())
    b = dist["bilateral"]["data"]
    fr_ma_birth = sorted((p["year"], p["value"]) for p in b
                         if p["destination_entity_id"] == "france" and p["origin_entity_id"] == "morocco")
    print(f"  FR<-MA naissance (dist v22) : {[(y, v) for y, v in fr_ma_birth if y in (2015, 2018)]}")
    fr_pt_birth = sorted((p["year"], p["value"]) for p in b
                         if p["destination_entity_id"] == "france" and p["origin_entity_id"] == "portugal")
    print(f"  FR<-PT naissance (dist v22) : {fr_pt_birth[:3]}...{fr_pt_birth[-3:]}")
    return {"n_cells": len(values), "n_country": n_country, "n_origins_fr": len(origins)}


def probe_c_years(p_fr: dict) -> None:
    print()
    print("=" * 72)
    print("SONDE C — années couvertes")
    print("=" * 72)
    years = sorted(int(y) for y in p_fr["dimension"]["time"]["category"]["index"])
    print(f"  Eurostat ctz (rangée FR) : {years[0]}-{years[-1]}")


def probe_d_geography() -> dict:
    print()
    print("=" * 72)
    print("SONDE D — géographie de la face (44 géos candidats)")
    print("=" * 72)
    rows = []
    for geo in CANDIDATE_GEOS:
        try:
            p = fetch_json(ctz_row_url(geo))
        except Exception as e:  # noqa: BLE001
            print(f"  {geo}: ÉCHEC {e}")
            continue
        values = p.get("value") or {}
        dim_order, size = p["id"], p["size"]
        sizes = dict(zip(dim_order, size))
        strides = {}
        mult = 1
        for d in reversed(dim_order):
            strides[d] = mult
            mult *= sizes[d]
        inv_cit = {v: k for k, v in p["dimension"]["citizen"]["category"]["index"].items()}
        inv_time = {v: k for k, v in p["dimension"]["time"]["category"]["index"].items()}
        country_codes = {
            c for c in p["dimension"]["citizen"]["category"]["index"]
            if len(c) == 2 and c.isalpha() and c.isupper()
        }
        n_country = n_other = 0
        origins = set()
        years = set()
        for pos_text in values:
            pos = int(pos_text)
            citizen = inv_cit[(pos // strides["citizen"]) % sizes["citizen"]]
            if citizen in country_codes and citizen != geo:
                n_country += 1
                origins.add(citizen)
                years.add(int(inv_time[(pos // strides["time"]) % sizes["time"]]))
            else:
                n_other += 1
        rows.append({
            "geo": geo, "n_cells": len(values), "n_country_cells": n_country,
            "n_origins": len(origins),
            "years": (min(years), max(years)) if years else None,
        })
        print(f"  {geo}: {len(values):>4} cellules, {n_country:>4} cellules pays, "
              f"{len(origins):>3} origines, {years and (min(years), max(years))}")
        time.sleep(0.15)
    full = [r["geo"] for r in rows if r["n_country_cells"] > 0]
    totals_only = [r["geo"] for r in rows if r["n_country_cells"] == 0]
    print(f"  ==> {len(full)} géos impriment le détail par origine : {full}")
    print(f"  ==> {len(totals_only)} géos totals-seuls : {totals_only}")
    return {"rows": rows, "full": full, "totals_only": totals_only}


def probe_e_oecd_b15() -> dict:
    print()
    print("=" * 72)
    print("SONDE E — témoin OCDE B15 (DSD_MIG@DF_MIG, clé '..A.B15.._Z._Z.PS')")
    print("=" * 72)
    url = f"{OECD_SDMX_BASE}/{OECD_DF_MIG_FLOW}/{B15_KEY}?dimensionAtObservation=AllDimensions"
    print(f"  GET {url}")
    r = S.get(url, headers={"Accept": "application/vnd.sdmx.data+csv; version=2.0"}, timeout=600)
    r.raise_for_status()
    print(f"  téléchargement : {len(r.content):,} octets")
    text = r.text
    (ROOT / "data" / "tmp").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "tmp" / "oecd_mig_b15_full.csv").write_text(text, encoding="utf-8")
    print(f"  sauvegardé : data/tmp/oecd_mig_b15_full.csv (matière des sondes/fixtures)")

    reader = csv.DictReader(io.StringIO(text))
    print(f"  en-tête : {reader.fieldnames}")
    n_raw = 0
    sex_counts: dict[str, int] = {}
    citizen_counts: dict[str, int] = {}
    dests = set()
    years = set()
    frame = {"FREQ": "A", "MEASURE": "B15", "BIRTH_PLACE": "_Z", "EDUCATION_LEV": "_Z", "UNIT_MEASURE": "PS"}
    frame_violations: dict[str, int] = {}
    anchor_fr_mar = []
    anchor_us_mex = []
    anchor_fr_pt = []
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        if not ref_area or ref_area == "REF_AREA":
            continue
        year_raw = (row.get("TIME_PERIOD") or "").strip()
        if not year_raw:
            continue
        n_raw += 1
        sex = (row.get("SEX") or "").strip()
        sex_counts[sex] = sex_counts.get(sex, 0) + 1
        citizen = (row.get("CITIZENSHIP") or "").strip()
        citizen_counts[citizen] = citizen_counts.get(citizen, 0) + 1
        dests.add(ref_area)
        years.add(int(year_raw))
        for col, want in frame.items():
            got = (row.get(col) or "").strip()
            if got != want:
                frame_violations[col] = frame_violations.get(col, 0) + 1
        if ref_area == "FRA" and citizen == "MAR" and sex == "_T" and year_raw in ("2015", "2016", "2017", "2018"):
            anchor_fr_mar.append((int(year_raw), float(row["OBS_VALUE"])))
        if ref_area == "USA" and citizen == "MEX" and year_raw == "2024" and sex == "_T":
            anchor_us_mex.append((int(year_raw), float(row["OBS_VALUE"])))
        if ref_area == "FRA" and citizen == "PRT" and sex == "_T" and float(row.get("OBS_VALUE") or 0) == 648112:
            anchor_fr_pt.append((int(year_raw), float(row["OBS_VALUE"])))

    print(f"  lignes de données brutes : {n_raw:,}")
    print(f"  répartition SEX : {dict(sorted(sex_counts.items()))}")
    print(f"  violations du cadre épinglé : {frame_violations or 'aucune'}")
    print(f"  destinations : {len(dests)} | années : {min(years)}-{max(years)}")
    extinct = {"XKV", "ANT_F", "CSK_F", "SCG_F", "SUN_F", "YUG_F"}
    summary_codes = {"NAT", "TOTAL", "UNK"}
    iso3 = sorted(c for c in citizen_counts if len(c) == 3 and c.isalpha() and c.isupper() and c not in extinct)
    non_iso = sorted(c for c in citizen_counts if c not in iso3 and c not in extinct)
    print(f"  codelist CITIZENSHIP : {len(citizen_counts)} codes -> {len(iso3)} ISO3-like, "
          f"éteints {sorted(c for c in extinct if c in citizen_counts)}, autres {non_iso}")
    for code in non_iso:
        print(f"    {code}: {citizen_counts[code]:,} lignes")
    for code in sorted(extinct & set(citizen_counts)):
        print(f"    (éteint) {code}: {citizen_counts[code]:,} lignes")

    # Application du vocabulaire de drop (§3) + split SEX
    n_kept = n_f_dropped = n_stls = n_diag = n_summary = n_extinct = 0
    kept_origins = set()
    kept_dests = set()
    kept_pairs = set()
    kept_years = set()
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        if not ref_area or ref_area == "REF_AREA":
            continue
        year_raw = (row.get("TIME_PERIOD") or "").strip()
        if not year_raw:
            continue
        sex = (row.get("SEX") or "").strip()
        citizen = (row.get("CITIZENSHIP") or "").strip()
        if sex == "F":
            n_f_dropped += 1
            continue
        if sex != "_T":
            raise SystemExit(f"SEX inattendu {sex!r} — layout change")
        if citizen == "STLS":
            n_stls += 1
            continue
        if citizen == ref_area:
            n_diag += 1
            continue
        if citizen in summary_codes:
            n_summary += 1
            continue
        if citizen in extinct:
            n_extinct += 1
            continue
        n_kept += 1
        kept_origins.add(citizen)
        kept_dests.add(ref_area)
        kept_pairs.add((ref_area, citizen))
        kept_years.add(int(year_raw))
    print(f"  VOCABULAIRE DE DROP appliqué :")
    print(f"    lignes F droppées        : {n_f_dropped:,}")
    print(f"    STLS droppées            : {n_stls:,}")
    print(f"    diagonales droppées      : {n_diag:,}")
    print(f"    agrégats NAT/TOTAL/UNK   : {n_summary:,}")
    print(f"    codes éteints droppés    : {n_extinct:,}")
    print(f"  ==> POINTS gardés : {n_kept:,} | {len(kept_dests)} destinations x "
          f"{len(kept_origins)} origines | {len(kept_pairs):,} paires | "
          f"{min(kept_years)}-{max(kept_years)}")
    print(f"  ANCRES : FR<-MAR _T ctz : {sorted(anchor_fr_mar)}")
    print(f"  ANCRES : US<-MEX 2024 ctz : {anchor_us_mex}")
    print(f"  ANCRES : FR<-PRT 648112 trouvé à : {anchor_fr_pt}")
    # La face naissance B14 du dist v22 pour le contraste US<-MEX
    dist = json.loads((ROOT / "data" / "dist" / "indicators" / "immigration_stock.json").read_text())
    us_mex_birth = [
        (p["year"], p["value"]) for w in dist["bilateral"]["witnesses"] for p in w["data"]
        if w["source_ref"] == "DF_MIG_POPF" and p.get("origin_entity_id") == "mexico"
        and p["entity_id"] == "united_states" and p["year"] == 2024
    ]
    print(f"  ANCRES : US<-MEX 2024 naissance (dist v22) : {us_mex_birth}")
    return {
        "n_raw": n_raw, "n_kept": n_kept, "sex_counts": sex_counts,
        "n_dests": len(kept_dests), "n_origins": len(kept_origins),
        "n_pairs": len(kept_pairs),
    }


def main() -> None:
    a = probe_a_grammar()
    b = probe_b_perimeter(a["payload"], a["classes"])
    probe_c_years(a["payload"])
    d = probe_d_geography()
    e = probe_e_oecd_b15()
    print()
    print("=" * 72)
    print("RÉCAPITULATIF DES ANCRES (conception gelée §5 vs lu en live)")
    print("=" * 72)
    print(f"  Eurostat ctz : {b['n_country']} cellules pays sur la rangée FR, "
          f"{b['n_origins_fr']} origines FR")
    print(f"  Géographie   : {len(d['full'])} géos complètes (attendu 34), "
          f"DE {'dedans' if 'DE' in d['full'] else 'DEHORS'}, CY {'dedans' if 'CY' in d['full'] else 'DEHORS'}")
    print(f"  OECD B15     : {e['n_raw']:,} lignes brutes -> {e['n_kept']:,} points, "
          f"{e['n_dests']} x {e['n_origins']}")


if __name__ == "__main__":
    main()
