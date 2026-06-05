"""
Pull the DESE E2C datasets the statewide atlas acquired but the Lynn/LEHS deep
dive had **not yet sliced**, straight from the Socrata **SODA JSON API**
(``/resource/{id}.json`` on ``educationtocareer.data.mass.gov``) and reduce each
to this project's peer universe.

Why SODA JSON (not the CSV bulk export ``01_download_e2c.py`` uses): several of
these datasets are *rate* columns (discipline, ACCESS, retention) where the CSV
export's display-rounding would be catastrophic — see ``utils/precise_sources.py``
for the head-to-head proof (CSV ``0.9`` vs SODA ``0.911``). The JSON resource API
returns full precision, and it also exposes the **school-level + subgroup +
all-year** rows the atlas threw away when it collapsed each dataset to a single
district latest-year snapshot.

Peer universe (identical to ``scripts/08_build_master_panel.py``):
    LEHS (01630510) + every Lynn district school + Lynn district (01630000)
    + each of the 26 gateway cities' main comprehensive HS + those districts
    + the Massachusetts ``State`` aggregate row (benchmark).

Every fetch **fails soft** (returns an empty DataFrame) on a network/parse error,
exactly like the build script's ``.exists()`` guards, so a partial run never
clobbers a good parquet.

Datasets (verified live against SODA 2026-06-05):
    2kca-w7rq  Student Discipline
    3etc-hecr  Student Discipline — Days Missed
    puw9-zucz  ACCESS for ELLs (Title III) Reporting Elements
    vxt3-k35x  Where Residents Go to School (sending / outflow)
    rg9w-dkpg  Pre-K & Kindergarten Enrollment
    n62c-bx65  Special Education Program Characteristics (district-grain only)
    c8ur-ajfv  Student Retention Report
    37cp-pad8  AP Participation
    2hei-cc7k  Staff (Teacher) Attendance
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    E2C_DOMAIN,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)

PEER_FILE = PROCESSED_DIR / "_peer_schools.json"

# Minimal SODA JSON client (kept self-contained so this module has no
# cross-dependency; mirrors the helper in utils/precise_sources.py).
_UA = {"User-Agent": "lehs-data-dive/1.0 (gap_sources; github.com/mapzimus/lehs-data-dive)"}


def soda(dataset: str, params: dict) -> list[dict]:
    """GET one page of a Socrata SODA JSON resource (full-precision values)."""
    url = f"https://{E2C_DOMAIN}/resource/{dataset}.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def soda_all(dataset: str, params: dict, page: int = 50000) -> list[dict]:
    """Fetch every row, paging on ``$offset``. Needs a stable ``$order`` in params."""
    rows: list[dict] = []
    offset = 0
    while True:
        p = dict(params, **{"$limit": str(page), "$offset": str(offset)})
        chunk = soda(dataset, p)
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page

# DESE/E2C label variants we collapse to the canonical {School, District, State}
# the rest of data/processed already relies on (same map as 08_build_master_panel).
DISTRICT_ORG_TYPES = {"District", "Public School District", "Charter District"}
ORG_TYPE_CANONICAL_MAP = {
    "Public School": "School",
    "Charter School": "School",
    "Public School District": "District",
    "Charter District": "District",
}

# Columns that must stay strings (codes, names, dimension labels). Everything
# else a fetcher selects is coerced to numeric; SY is coerced to a nullable int.
STRING_COLS = {
    "DIST_CODE", "ORG_CODE", "DIST_NAME", "ORG_NAME", "ORG_TYPE", "STU_GRP",
    "GRADE", "ENR_REASON", "IND_CAT", "IND_DESC", "VALUE_TYPE", "STAFF_GRP",
    "SUBJ", "SUBJ_CAT", "OFFENSE", "TOWN_NAME",
}


def load_peer_codes() -> dict[str, set[str]]:
    """Return {'schools': {8-char org codes}, 'districts': {8-char dist codes}}
    for the LEHS + Lynn + gateway peer universe. Mirrors the two filter-set
    builders in scripts/08_build_master_panel.py."""
    peers = json.loads(PEER_FILE.read_text())
    lynn_schools = set((peers.get("lynn_all_schools") or {}).values())
    gateway_main = {
        i["school_code"] for i in peers.get("gateway_main_hs", {}).values()
        if i.get("school_code")
    }
    gateway_dist = {
        i["district_code"] for i in peers.get("gateway_main_hs", {}).values()
        if i.get("district_code")
    }
    schools = {LEHS_SCHOOL_CODE} | lynn_schools | gateway_main
    districts = {LYNN_DISTRICT_CODE} | gateway_dist
    return {
        "schools": {str(c).zfill(8) for c in schools if c},
        "districts": {str(c).zfill(8) for c in districts if c},
    }


def in_clause(field: str, codes) -> str:
    """SoQL ``field in('a','b',...)`` with sorted, quoted values."""
    vals = ",".join("'" + str(c).replace("'", "''") + "'" for c in sorted(codes))
    return f"{field} in({vals})"


def pull(
    dataset: str,
    select: str,
    district_codes: set[str],
    *,
    has_org_type: bool = True,
    extra_where: str | None = None,
) -> pd.DataFrame:
    """Server-side peer-filtered SODA pull.

    Restricts to ``dist_code in(<peer districts>)`` (which also captures every
    school inside those districts, e.g. LEHS), plus ``org_type='State'`` for the
    benchmark row when the dataset carries one. Pages on a stable ``:id`` order so
    offset paging neither skips nor repeats. Fails soft to an empty DataFrame.
    """
    where = in_clause("dist_code", district_codes)
    if has_org_type:
        where = f"({where} or org_type='State')"
    if extra_where:
        where = f"{where} and ({extra_where})"
    try:
        rows = soda_all(dataset, {"$select": select, "$where": where, "$order": ":id"})
    except Exception as exc:  # noqa: BLE001 — fail soft like the build's guards
        print(f"  [!] pull {dataset} failed ({exc}); skipped")
        return pd.DataFrame()
    return pd.DataFrame(rows)


def canon_peer(df: pd.DataFrame, codes: dict[str, set[str]]) -> pd.DataFrame:
    """Apply 08_build_master_panel's canonical keep-rule and normalize ORG_TYPE.

    Keep a row if it is the State aggregate, a District row for one of our peer
    districts, or a School row for one of our peer schools. Datasets with no
    ``org_type`` column (already district-keyed: choice, sped) pass through —
    the server-side ``dist_code`` filter is the whole filter for them.
    """
    if df.empty:
        return df
    df = df.copy()
    for c in ("dist_code", "org_code"):
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.zfill(8)
    if "org_type" in df.columns:
        sc, dc = df.get("org_code"), df["dist_code"]
        mask = df["org_type"].eq("State")
        mask |= df["org_type"].isin(DISTRICT_ORG_TYPES) & dc.isin(codes["districts"])
        if sc is not None:
            mask |= sc.isin(codes["schools"])
        df = df[mask].copy()
        df["org_type"] = df["org_type"].replace(ORG_TYPE_CANONICAL_MAP)
    return df


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase columns to match data/processed convention, zero-pad code
    columns, coerce SY to Int64 and every non-string column to numeric."""
    if df.empty:
        return df
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]
    for c in ("DIST_CODE", "ORG_CODE"):
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.zfill(8)
    if "SY" in df.columns:
        df["SY"] = pd.to_numeric(df["SY"], errors="coerce").astype("Int64")
    for c in df.columns:
        if c != "SY" and c not in STRING_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df
