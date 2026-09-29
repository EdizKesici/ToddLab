"""v25_probe.py — les sondes de la V25, selon la direction approuvée par
Ediz : la porte « Destin des immigrés » du chômage (les flux ILOSTAT
DEAP par nationalité / lieu de naissance, enregistrés en v17 comme THE
FUTURE door), plus les deux portes compactes enregistrées non câblées
(le dénominateur par véhicule de Todd 1974 chez ITF, et les ventilations
M/F d'une_rt_a). La conception détaillée se gèle sur ces sorties.

Sondes :
  A. ILOSTAT DF_UNE_DEAP_SEX_AGE_CCT_RT / _CBR_RT — le flux existe-t-il
     toujours, quelle est sa grammaire de clés, sa couverture réelle
     (destinations x nationalités x années x sexes), et les ancres FR ?
  B. Eurostat — existe-t-il une PORTE COLLECTEUR du chômage par
     nationalité / lieu de naissance (les tables LFS lfsa_urgan /
     lfsa_urgacob et leurs sœurs) ? En RATE (PC_ACT) ou en COUNTS
     (THS_PER) ? Le Table of Contents de l'API dit-il autre chose ?
     + re-vérification des ventilations M/F d'une_rt_a (les ancres v17).
  C. OECD.ITF — le dénominateur par véhicule 10P4VEH_MOT_ROAD répond-il
     toujours, et avec quelle couverture (la v19 disait 38 aires,
     1994-2024) ?

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
OECD_DF_SAFETY_FLOW = "OECD.ITF,DSD_INDICATORS@DF_SAFETY,1.0"
ILO_SDMX_BASE = "https://sdmx.ilo.org/rest"


def try_get(url: str, accept: str | None = None, timeout: int = 90) -> tuple[int, str, str]:
    headers = {"Accept": accept} if accept else {}
    r = S.get(url, headers=headers, timeout=timeout)
    return r.status_code, r.headers.get("Content-Type", ""), r.text


# ---------------------------------------------------------------------------
# SONDE A — ILOSTAT : les flux DEAP par nationalité / lieu de naissance
# ---------------------------------------------------------------------------

def probe_a_ilostat() -> None:
    print("=" * 72)
    print("SONDE A — ILOSTAT DF_UNE_DEAP_SEX_AGE_CCT_RT / _CBR_RT")
    print("=" * 72)
    for flow in ("DF_UNE_DEAP_SEX_AGE_CCT_RT", "DF_UNE_DEAP_SEX_AGE_CBR_RT"):
        print(f"\n--- {flow} ---")
        # Les formes candidates : SDMX 2.1 (/rest/data) et 3.0 (/rest/v2/data),
        # clé partielle A.FRA (préfixe gauche), formats jsondata / CSV.
        found = None
        for base in (f"{ILO_SDMX_BASE}/data", f"{ILO_SDMX_BASE}/v2/data"):
            for fmt in ("?format=jsondata", ""):
                url = f"{base}/ILO,{flow}/A.FRA{fmt}&startPeriod=2015&endPeriod=2018" if fmt else \
                      f"{base}/ILO,{flow}/A.FRA?startPeriod=2015&endPeriod=2018"
                accept = None if fmt else "application/vnd.sdmx.data+csv; version=2.0"
                try:
                    code, ctype, body = try_get(url, accept=accept)
                except Exception as e:  # noqa: BLE001
                    print(f"  {url} -> EXC {e}")
                    continue
                print(f"  {url} -> HTTP {code} [{ctype[:40]}] {len(body):,} octets")
                if code == 200 and len(body) > 500:
                    found = (url, ctype, body)
                    break
            if found:
                break
        if not found:
            print("  => AUCUNE forme n'a répondu — le flux a-t-il changé de nom ?")
            continue
        url, ctype, body = found
        if "json" in ctype:
            _read_ilostat_json(flow, body)
        else:
            _read_ilostat_csv(flow, body)


def _read_ilostat_json(flow: str, body: str) -> None:
    d = json.loads(body)
    # SDMX-JSON : structure.dimensions.series[].dimensions + dataSets[0].
    # Observations par série : une seule dimension d'observation (TIME).
    try:
        series_dims = d["structure"]["dimensions"]["series"]
        obs_dim = d["structure"]["dimensions"]["observation"]
    except KeyError:
        print(f"  JSON illisible (clés: {list(d)[:6]})")
        return
    print(f"  dimensions de série : {[s['id'] for s in series_dims]}")
    print(f"  dimension d'observation : {[o['id'] for o in obs_dim]}")
    srcs = d.get("structure") or {}
    attrs = (srcs.get("attributes") or {}).get("dataSet") or []
    for a in attrs:
        if a.get("id") in ("SOURCE", "MEASURE", "UNIT_MEASURE"):
            print(f"  attribut {a['id']}: {a.get('name', '')[:80]}")
    ds = (d.get("dataSets") or [{}])[0]
    series = ds.get("series") or {}
    print(f"  séries dans la tranche 2015-2018 : {len(series):,}")
    for k in list(series)[:6]:
        idx = [int(x) for x in k.split(":")]
        labels = []
        for pos, dim in enumerate(series_dims):
            cat = dim.get("values", [{}])[idx[pos]] if idx[pos] < len(dim.get("values", [])) else {}
            labels.append(f"{dim['id']}={cat.get('id', '?')}")
        obs = series[k].get("observations") or {}
        sample = list(obs.items())[:3]
        print(f"    {' '.join(labels)} | obs: {sample}")


def _read_ilostat_csv(flow: str, body: str) -> None:
    reader = csv.DictReader(io.StringIO(body))
    cols = reader.fieldnames or []
    print(f"  colonnes CSV : {cols}")
    n = 0
    rows = []
    for row in reader:
        ra = (row.get("REF_AREA") or "").strip()
        if not ra:
            continue
        n += 1
        rows.append(row)
    print(f"  lignes de données (tranche demandée) : {n:,}")
    dests = sorted({r["REF_AREA"] for r in rows})
    print(f"  REF_AREA: {dests}")
    for r in rows[:8]:
        keep = {k: v for k, v in r.items() if k in (
            "REF_AREA", "SEX", "AGE", "CITIZEN", "COUNTRY_OF_BIRTH", "MEASURE",
            "MEASURE_UNIT", "UNIT_MEASURE", "TIME_PERIOD", "OBS_VALUE", "SOURCE")}
        print(f"    {keep}")


# ---------------------------------------------------------------------------
# SONDE B — Eurostat : la porte collecteur du chômage par nationalité ?
# ---------------------------------------------------------------------------

LFS_CANDIDATES = [
    "lfsa_urgan",     # unemployed by nationality (counts ?)
    "lfsa_urgacob",   # unemployed by country of birth (counts ?)
    "lfsa_argan",     # activity rate by nationality (rates ?)
    "lfsa_argacob",   # activity rate by country of birth
    "lfsa_ergan",     # employed by nationality (counts ?)
    "lfsa_ergacob",   # employed by country of birth
    "une_rt_a",       # re-vérification M/F (les ancres v17)
]


def probe_b_eurostat() -> None:
    print()
    print("=" * 72)
    print("SONDE B — Eurostat : les portes chômage par nationalité / naissance")
    print("=" * 72)
    for ds in LFS_CANDIDATES:
        url = f"{EUROSTAT_API}/{ds}?format=JSON&lang=EN&geo=FR&time=2015&time=2018"
        try:
            code, ctype, body = try_get(url, timeout=120)
        except Exception as e:  # noqa: BLE001
            print(f"  {ds}: EXC {e}")
            continue
        if code != 200:
            snippet = body[:200].replace("\n", " ")
            print(f"  {ds}: HTTP {code} — {snippet}")
            continue
        d = json.loads(body)
        dims = d.get("id") or []
        n_values = len(d.get("value") or {})
        label = (d.get("label") or "")[:70]
        print(f"  {ds}: HTTP 200 « {label} »")
        print(f"    dimensions : {dims} | taille : {d.get('size')} | cellules : {n_values}")
        for dim in dims:
            cat = (d.get("dimension") or {}).get(dim) or {}
            idx = (cat.get("category") or {}).get("index") or {}
            if dim in ("sex", "age", "unit", "citizen", "c_birth", "citizen_1", "nationality"):
                print(f"    codelist {dim}: {sorted(idx.keys())[:14]}{'...' if len(idx) > 14 else ''} ({len(idx)})")
        if n_values:
            # imprimer les cellules par les strides
            strides, mult = {}, 1
            sizes = dict(zip(dims, d["size"]))
            for dim in reversed(dims):
                strides[dim] = mult
                mult *= sizes[dim]
            inv = {dim: {v: k for k, v in ((d["dimension"][dim]["category"]["index"]) or {}).items()}
                   for dim in dims}
            shown = 0
            for pos_text, val in (d.get("value") or {}).items():
                pos = int(pos_text)
                parts = []
                for dim in dims:
                    code_v = inv[dim].get((pos // strides[dim]) % sizes[dim])
                    if code_v is not None and dim != "time" and dim != "freq":
                        parts.append(f"{dim}={code_v}")
                year = inv["time"].get((pos // strides["time"]) % sizes["time"]) if "time" in dims else "?"
                print(f"    cellule {year}: {' '.join(parts)} = {val}")
                shown += 1
                if shown >= 8:
                    break
        time.sleep(0.15)


def probe_b_toc() -> None:
    print()
    print("  --- recherche TOC : unemployment + nationality / country of birth ---")
    for shape in (
        f"{EUROSTAT_API.replace('/data', '')}/catalog/toc/search?query=unemployment%20by%20nationality",
        f"{EUROSTAT_API.replace('/data', '')}/catalog/toc",
    ):
        try:
            code, ctype, body = try_get(shape, timeout=120)
        except Exception as e:  # noqa: BLE001
            print(f"  {shape} -> EXC {e}")
            continue
        print(f"  {shape} -> HTTP {code} [{ctype[:40]}] {len(body):,} octets")
        if code == 200:
            (ROOT / "data" / "tmp").mkdir(parents=True, exist_ok=True)
            out = ROOT / "data" / "tmp" / "eurostat_toc.json"
            out.write_text(body, encoding="utf-8")
            try:
                d = json.loads(body)
            except json.JSONDecodeError:
                print("    (pas du JSON — brut sauvegardé)")
                return
            print(f"    sauvegardé : {out}")
            _grep_toc(d)
            return


def _grep_toc(d) -> None:
    """Cherche les jeux de données dont le titre parle de chômage ET de
    nationalité / pays de naissance — dans l'arbre TOC quelle qu'en soit
    la forme (liste plate ou arborescence)."""
    flat: list[dict] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("code") or node.get("id"):
                flat.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(d)
    print(f"    nœuds TOC parcourus : {len(flat):,}")
    hits = 0
    seen = set()
    for node in flat:
        title = " ".join(str(node.get(k, "")) for k in ("title", "label", "name"))
        low = title.lower()
        if ("unemploy" in low or "chômage" in low or "chomage" in low) and \
           ("national" in low or "countr" in low or "birth" in low or "origin" in low):
            code = node.get("code") or node.get("id")
            if code and code not in seen:
                seen.add(code)
                print(f"    CANDIDAT: {code} — {title[:90]}")
                hits += 1
    if not hits:
        print("    aucun candidat chômage+nationalité dans le TOC")


# ---------------------------------------------------------------------------
# SONDE C — OECD.ITF : le dénominateur par véhicule de Todd 1974
# ---------------------------------------------------------------------------

def probe_c_itf_vehicles() -> None:
    print()
    print("=" * 72)
    print("SONDE C — ITF 10P4VEH_MOT_ROAD (le dénominateur par véhicule)")
    print("=" * 72)
    key = ".A.FATALITIES.10P4VEH_MOT_ROAD.ROAD._Z._Z._Z"
    url = f"{OECD_SDMX_BASE}/{OECD_DF_SAFETY_FLOW}/{key}?dimensionAtObservation=AllDimensions"
    code, ctype, body = try_get(
        url, accept="application/vnd.sdmx.data+csv; version=2.0", timeout=300
    )
    print(f"  HTTP {code} [{ctype[:40]}] {len(body):,} octets")
    if code != 200:
        print(f"  corps : {body[:300]}")
        return
    (ROOT / "data" / "tmp").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "tmp" / "itf_10p4veh_full.csv").write_text(body, encoding="utf-8")
    reader = csv.DictReader(io.StringIO(body))
    rows = []
    for row in reader:
        ra = (row.get("REF_AREA") or "").strip()
        if not ra:
            continue
        rows.append(row)
    dests = sorted({r["REF_AREA"] for r in rows})
    years = sorted({int(r["TIME_PERIOD"]) for r in rows if r.get("TIME_PERIOD")})
    print(f"  {len(rows):,} lignes | {len(dests)} aires | {years[0]}-{years[-1]}" if years else "  vide")
    print(f"  aires : {dests}")
    for ra, y in (("FRA", "1994"), ("FRA", "2024"), ("DEU", "1994"), ("USA", "2023")):
        hits = [r for r in rows if r["REF_AREA"] == ra and r["TIME_PERIOD"] == y]
        print(f"    {ra} {y}: {[h.get('OBS_VALUE') for h in hits]}")


def main() -> None:
    probe_a_ilostat()
    probe_b_eurostat()
    probe_b_toc()
    probe_c_itf_vehicles()


if __name__ == "__main__":
    main()
