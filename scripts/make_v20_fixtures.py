"""make_v20_fixtures.py — les fixtures des cinq indicateurs v20, GÉNÉRÉES
des APIs live à travers le build_url du connecteur LUI-MÊME (la discipline
v16/v19 : chaque ancre est LUE des octets de la réponse, jamais tapée).

Chaque porte est re-téléchargée puis taillée (carve) en sous-ensemble
ancré : les pays Todd en série complète + les calibrateurs de borne
(queue/plancher) + les rangées non-COUNTRY/agrégats que le parseur
droppera loggé (la discipline de drop doit vivre dans le fixture).
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

from src.connectors import gho as gho_mod  # noqa: E402
from src.connectors import owid as owid_mod  # noqa: E402

OUT = ROOT / "tests" / "fixtures"
S = requests.Session()
S.headers.update({"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"})


def fetch_owid(slug: str) -> str:
    url = owid_mod.build_url(slug)
    r = S.get(url, timeout=120)
    r.raise_for_status()
    print(f"[owid] {slug}: {len(r.content)} bytes")
    return r.text


def carve_owid(text: str, keep_ents: dict[str, set[int] | None], out_name: str) -> None:
    """keep_ents: entity -> set of years to keep (None = all)."""
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames
    rows = list(reader)
    kept = []
    for row in rows:
        ent = row["Entity"]
        years = keep_ents.get(ent)
        if years is None and ent in keep_ents:
            kept.append(row)
        elif years is not None and int(float(row["Year"])) in years:
            kept.append(row)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(kept)
    (OUT / out_name).write_text(out.getvalue(), encoding="utf-8")
    print(f"  -> {out_name}: {len(kept)} rows / {len(rows)} live")


def fetch_gho(code: str) -> dict:
    url = gho_mod.build_url(code)
    r = S.get(url, timeout=180)
    r.raise_for_status()
    payload = json.loads(r.text)
    print(f"[gho] {code}: {len(payload['value'])} rows")
    return payload


def carve_gho(payload: dict, keep: set[tuple[str, int]], extra_non_country: int, out_name: str) -> None:
    """keep: (SpatialDim, TimeDim) pairs; plus the first extra_non_country
    non-COUNTRY rows verbatim (the parser's drop discipline)."""
    rows = payload["value"]
    kept = [
        row
        for row in rows
        if row.get("SpatialDimType") == "COUNTRY"
        and (row.get("SpatialDim"), row.get("TimeDim")) in keep
    ]
    non_country = [row for row in rows if row.get("SpatialDimType") != "COUNTRY"][:extra_non_country]
    out = {"value": kept + non_country}
    (OUT / out_name).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {out_name}: {len(kept)} country rows + {len(non_country)} non-COUNTRY rows / {len(rows)} live")


# ---------------------------------------------------------------------------
# (1) incarceration — la porte ICPR/WPB
text = fetch_owid("prison-population-rate")
all_years = None
carve_owid(
    text,
    {
        "France": all_years,
        "United States": all_years,
        "Russia": all_years,
        "Germany": all_years,
        "Japan": all_years,
        "United Kingdom": all_years,
        "El Salvador": all_years,
        "Cuba": all_years,
        "Seychelles": all_years,
        "Kosovo": all_years,
        "Yemen": all_years,
        "England and Wales": all_years,  # résout à rien — droppé loggé, la discipline vit dans le fixture
    },
    "owid_prison_population_rate.csv",
)

# ---------------------------------------------------------------------------
# (2) math — la porte PISA (colonne Mathematics épinglée)
text = fetch_owid("average-performance-of-15-year-olds-in-mathematics-reading-and-science")
carve_owid(
    text,
    {
        "France": all_years,
        "United States": all_years,
        "Russia": all_years,
        "Germany": all_years,
        "Japan": all_years,
        "United Kingdom": all_years,
        "Singapore": all_years,
        "Qatar": all_years,
        "Dominican Republic": all_years,
    },
    "owid_pisa_math.csv",
)

# ---------------------------------------------------------------------------
# (3) HIV — la porte UNAIDS
text = fetch_owid("share-of-the-population-infected-with-hiv")
carve_owid(
    text,
    {
        "France": all_years,
        "Germany": all_years,
        "United Kingdom": all_years,
        "Eswatini": all_years,
        "Botswana": all_years,
        "Zambia": all_years,
        "South Africa": {1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024},
        "Zimbabwe": {1990, 1995, 1996, 2000, 2010, 2020, 2024},
        "World": {2024},  # agrégat — droppé loggé, la discipline vit dans le fixture
        "Latin America (UNAIDS)": {2024},  # agrégat régional UNAIDS — droppé loggé
    },
    "owid_hiv_prevalence.csv",
)

# ---------------------------------------------------------------------------
# (4) hauteur — la porte canonique NCD-RisC
text = fetch_owid("average-height-of-men")
decades = {1896, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1985, 1990, 1996}
carve_owid(
    text,
    {
        "France": all_years,  # 101 points — l'arc Todd complet
        "United States": decades,
        "Russia": decades,
        "Germany": decades,
        "Japan": decades,
        "United Kingdom": decades,
        "Netherlands": {1896, 1950, 1984, 1985, 1996},
        "South Korea": {1896, 1950, 1996},
        "Laos": {1896, 1996},  # le plancher
        "East Germany": {1896, 1996},
        "World": {1896, 1996},  # agrégat — droppé loggé
    },
    "owid_height_men.csv",
)

# ---------------------------------------------------------------------------
# (5) hauteur — la porte témoin Baten-Blum
text = fetch_owid("average-height-of-men-by-year-of-birth")
carve_owid(
    text,
    {
        "France": all_years,  # 27 points — la série Européenne clairsemée
        "United States": all_years,
        "Russia": all_years,
        "Germany": {1550, 1700, 1800, 1896, 1980},
        "Papua New Guinea": {1880, 1930},  # le plancher
        "Denmark": {1980},  # le plafond
    },
    "owid_height_baten_blum.csv",
)

# ---------------------------------------------------------------------------
# (6) obésité — la porte GHO NCD_BMI_30C (pin d'âge YEARS18-PLUS)
payload = fetch_gho("NCD_BMI_30C")
keep = set()
for c in ("FRA", "USA", "RUS", "JPN", "DEU"):
    for y in (1980, 1990, 2000, 2010, 2022, 2024):
        for _sex in ("MLE", "FMLE", "BTSX"):
            keep.add((c, y))
for c, y in (("ASM", 2024), ("VNM", 1980)):  # la queue et le plancher
    keep.add((c, y))
carve_gho(payload, keep, extra_non_country=4, out_name="gho_ncd_bmi_30c.json")

# ---------------------------------------------------------------------------
# (7) prison — la coupe GHO WHO Health in Prisons
payload = fetch_gho("PRISON_A2_PRISIONERS_PER100KPOP")
keep = {(c, 2020) for c in ("FRA", "DEU", "GBR", "GEO", "MDA", "SMR", "MCO", "ESP", "ITA", "POL", "UKR", "SWE")}
carve_gho(payload, keep, extra_non_country=0, out_name="gho_prison_a2.json")

# ---------------------------------------------------------------------------
# LES ANCHORS LUES (imprimées pour les tests — jamais tapées)
print()
print("=" * 60)
print("ANCHORS LUS DES FIXTURES:")


def anchors_owid(name: str, col: str, wants: list[tuple[str, str]]) -> None:
    rows = list(csv.DictReader(io.StringIO((OUT / name).read_text(encoding="utf-8"))))
    for ent, year in wants:
        hit = [r for r in rows if r["Entity"] == ent and r["Year"] == year]
        v = hit[0].get(col) if hit else "ABSENT"
        print(f"  {name} {ent} {year} = {v}")


anchors_owid("owid_prison_population_rate.csv", "Prison population rate", [
    ("France", "2000"), ("France", "2025"), ("United States", "2000"), ("United States", "2023"),
    ("Russia", "2000"), ("Russia", "2023"), ("El Salvador", "2024"), ("Kosovo", "2000"),
    ("Japan", "2024"), ("United Kingdom", "2025"),
])
anchors_owid("owid_pisa_math.csv", "Mathematics", [
    ("France", "2003"), ("France", "2022"), ("United States", "2003"), ("United States", "2022"),
    ("Russia", "2018"), ("Singapore", "2022"), ("Qatar", "2006"), ("Japan", "2003"),
    ("France", "2000"),
])
anchors_owid("owid_hiv_prevalence.csv", "HIV Prevalence in adults (15-49)", [
    ("France", "1990"), ("France", "2023"), ("Eswatini", "2024"), ("South Africa", "2024"),
    ("Zimbabwe", "1995"), ("Botswana", "1990"),
])
anchors_owid("owid_height_men.csv", "Mean male height (cm)", [
    ("France", "1896"), ("France", "1996"), ("United States", "1896"), ("Netherlands", "1985"),
    ("South Korea", "1996"), ("Japan", "1896"), ("Laos", "1896"), ("Russia", "1996"),
])
anchors_owid("owid_height_baten_blum.csv", "Height (Baten and Blum 2015)", [
    ("France", "1660"), ("France", "1900"), ("France", "1980"), ("United States", "1710"),
    ("Papua New Guinea", "1880"), ("Denmark", "1980"), ("Russia", "1700"),
])

for name, wants in (
    ("gho_ncd_bmi_30c.json", [("FRA", 2024), ("FRA", 1980), ("USA", 2024), ("RUS", 2024), ("JPN", 2024), ("ASM", 2024), ("VNM", 1980)]),
    ("gho_prison_a2.json", [("FRA", 2020), ("DEU", 2020), ("GBR", 2020), ("GEO", 2020), ("SMR", 2020)]),
):
    payload = json.loads((OUT / name).read_text(encoding="utf-8"))
    rows = payload["value"]
    for area, year in wants:
        hits = [r for r in rows if r.get("SpatialDim") == area and r.get("TimeDim") == year]
        if not hits:
            print(f"  {name} {area} {year} = ABSENT")
        for r in hits:
            print(f"  {name} {area} {year} Dim1={r.get('Dim1')} = {r.get('NumericValue')}")

# parse validation: les fixtures doivent passer les parseurs réels
print()
print("=" * 60)
print("VALIDATION PARSE:")
p30c = json.loads((OUT / "gho_ncd_bmi_30c.json").read_text(encoding="utf-8"))
recs = gho_mod.parse_gho(json.dumps(p30c), code="NCD_BMI_30C")
print(f"  gho NCD_BMI_30C parse: {len(recs)} records (sexes: {sorted({str(r.sex) for r in recs})})")
pprison = json.loads((OUT / "gho_prison_a2.json").read_text(encoding="utf-8"))
recs = gho_mod.parse_gho(json.dumps(pprison), code="PRISON_A2_PRISIONERS_PER100KPOP")
print(f"  gho PRISON_A2 parse: {len(recs)} records (sexes: {sorted({str(r.sex) for r in recs})})")
for name, field in (
    ("owid_prison_population_rate.csv", None),
    ("owid_pisa_math.csv", "Mathematics"),
    ("owid_hiv_prevalence.csv", None),
    ("owid_height_men.csv", None),
    ("owid_height_baten_blum.csv", None),
):
    text = (OUT / name).read_text(encoding="utf-8")
    recs = owid_mod.parse_csv(text, value_field=field)
    print(f"  owid {name} parse: {len(recs)} records")
print("DONE")
