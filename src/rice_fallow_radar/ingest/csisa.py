"""CSISA rice Landscape Diagnostic Survey (CIMMYT Dataverse) -- farmer-reported crop calendars.

Two public surveys, no login needed, fetched through the Dataverse access API:
  2017  hdl:11529/10548605  (6,857 farmers; Bihar / UP / Odisha)
  2018  hdl:11529/10548656  (8,355 farmers; 8 states incl. 784 in Odisha)

Why this exists: D-031 pre-registers a prediction about Odisha's transplanting-date spread, and
these are the only public farmer-reported Odisha rice calendars we have found. The 2018 file
carries ~110 m coordinates (3 dp), which is what reopens D-005.

Two traps the raw files set:
  * 2018 stores latitude and longitude in two columns with **empty headers** (pandas names them
    `Unnamed: N`). Position is not stable across file revisions, so `coord_columns` finds them by
    value range and asserts, rather than trusting an index.
  * `D-q415_seedingSowingTransDate` is the *transplanting* date on transplanted fields and the
    *sowing* date on direct-seeded ones. Pooling the two inflates the spread by ~2x (measured:
    Odisha 2017, 23 d pooled vs 11.8 d transplanted-only), so `transplanted` is a required
    filter for any calendar statistic, not a covariate.

Terms of use: both datasets are published with no licence and the note "made available without
information on how it can be used ... communicate with the Contact(s) before use". Raw and
row-level derived data therefore stay local (OPEN_QUESTIONS #10 territory). Checked 23 Nov 2026.
"""

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

ACCESS_URL = "https://data.cimmyt.org/api/access/datafile/{id}?format=original"

# Dataverse file ids and the md5 of what they served on 23 Nov 2026. A changed digest means the
# depositor revised the file: re-check the counts in DATA.md before trusting any number here.
FILES = {
    2017: {"id": 16323, "name": "csisa_2017_data.csv", "md5": "f28190bea115d7900a43384a824b2a0c"},
    2018: {"id": 20843, "name": "csisa_2018_data.csv", "md5": "d61e6fe94d20e5a8362d1d9943c8fdb8"},
    # documentation, not read by this module -- kept so the download is self-contained
    "2017_variable_details": {
        "id": 16325,
        "name": "csisa_2017_variable_details.xlsx",
        "md5": "2b35f3cf73b69fbd44c42cde4e40eaf3",
    },
    "2018_variable_details": {
        "id": 18769,
        "name": "csisa_2018_variable_details.xlsx",
        "md5": "71dcf8b3973576990fb4649924385231",
    },
    "2018_codebook": {
        "id": 18773,
        "name": "csisa_2018_codebook.pdf",
        "md5": "0755cb661b3cd0729434e862a58e992f",
    },
}

SURVEY_COLS = {
    "A-q102_state": "state",
    "A-q103_district": "district",
    "A-q104_subDistrict": "sub_district",
    "A-q105_village": "village",
    "D-q409_varType": "var_type",
    "D-q410_varName": "var_name",
    "D-q413_CropEst": "crop_est",
    "D-q414_rcNursEstDate": "nursery_date",
    "D-q415_seedingSowingTransDate": "estab_date",
    "L-q601_harvestDate": "harvest_date",
}
DATE_COLS = ("nursery_date", "estab_date", "harvest_date")
# 2017 names its coordinates; 2018 leaves the headers empty (see module docstring).
COORD_COLS_2017 = ("O-largestPlotGPS-Latitude", "O-largestPlotGPS-Longitude")
LAT_RANGE, LON_RANGE = (8.0, 36.0), (68.0, 98.0)  # India's bounding box
COORD_DP = {2017: 2, 2018: 3}  # written decimal places -> ~1 km (2017), ~110 m (2018)
MAX_DURATION_D = 250  # establishment -> harvest; anything longer is a recall or entry error
# 2018 writes "00-01-00" for an unharvested/unknown harvest date (417 rows, all Haryana, none in
# Odisha). Anything else that fails to parse should fail loudly rather than coerce to NaT.
MISSING_DATE = "00-01-00"


def download(out_dir: Path, force: bool = False) -> dict[str, Path]:
    """Fetch every file in FILES into out_dir, verifying the recorded md5."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, f in FILES.items():
        dest = out_dir / f["name"]
        if force or not dest.exists():
            with urllib.request.urlopen(ACCESS_URL.format(id=f["id"]), timeout=300) as r:
                dest.write_bytes(r.read())
        got = hashlib.md5(dest.read_bytes()).hexdigest()  # noqa: S324 -- integrity, not security
        assert got == f["md5"], f"{f['name']}: md5 {got}, expected {f['md5']} (file revised?)"
        paths[key] = dest
    return paths


def coord_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Find the (latitude, longitude) columns by value range, not by name or position."""

    def fits(col, lo, hi):
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        return len(s) > 0.5 * len(df) and s.between(lo, hi).all()

    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    named = [c for c in COORD_COLS_2017 if c in df.columns]
    lats = [c for c in named + unnamed if fits(c, *LAT_RANGE)]
    lons = [c for c in named + unnamed if fits(c, *LON_RANGE)]
    # India's lat and lon ranges do not overlap, so each candidate can only be one of the two
    assert len(lats) == 1 and len(lons) == 1, f"coords ambiguous: lat {lats}, lon {lons}"
    return lats[0], lons[0]


def written_decimals(path: Path, col: str) -> int:
    """Max decimal places as written in the file -- pandas' float does not preserve them."""
    s = pd.read_csv(path, usecols=[col], dtype=str, low_memory=False)[col].dropna()
    return int(s.str.split(".").str[-1].str.len().max())


def normalise_variety(name: pd.Series) -> pd.Series:
    """Collapse the survey's free-text variety spellings onto one label per variety.

    shortcut: handles the MTU codes and the Pooja/Swarna spellings that actually recur in Odisha;
    everything else is only de-prefixed and whitespace-cleaned. Upgrade (regenerate the per-variety
    duration table) if a variety outside this list ever reaches n >= 5 in a study district.
    """
    s = name.fillna("").astype(str).str.replace(r"^Other", "", regex=True).str.strip()
    s = s.str.replace(r"[\s_]+", " ", regex=True).str.strip()
    # Mansuri_MTU7029, MiniMansuri_MTU7029, Golden_MTU7029 -> MTU 7029
    s = s.str.replace(r".*\bMTU\s*(\d{4})\b.*", r"MTU \1", regex=True, case=False)
    aliases = {"PUJA": "Pooja", "POOJA": "Pooja", "PUJAS": "Pooja", "SWARNA": "Swarna"}
    key = s.str.upper().str.replace(" ", "")
    return pd.Series(
        [aliases.get(k, v) if v else pd.NA for k, v in zip(key, s, strict=True)], index=s.index
    )


def is_transplanted(crop_est: pd.Series) -> pd.Series:
    """Puddled/Transplanted establishment -- for these rows `estab_date` is a transplanting date."""
    return crop_est.fillna("").str.contains("Puddled|Transplant", case=False, regex=True)


def load_year(path: Path, year: int) -> pd.DataFrame:
    """Read one survey file down to the calendar columns, parsed and cleaned."""
    raw = pd.read_csv(path, low_memory=False)
    lat_col, lon_col = coord_columns(raw)
    for col, want in ((lat_col, COORD_DP[year]), (lon_col, COORD_DP[year])):
        got = written_decimals(path, col)
        assert got == want, f"{year} {col}: {got} dp, expected {want} (precision changed?)"

    df = raw[list(SURVEY_COLS)].rename(columns=SURVEY_COLS)
    df["year"] = year
    df["lat"] = pd.to_numeric(raw[lat_col], errors="coerce")
    df["lon"] = pd.to_numeric(raw[lon_col], errors="coerce")
    df["coord_dp"] = COORD_DP[year]
    for c in DATE_COLS:
        text = df[c].replace(MISSING_DATE, pd.NA)
        parsed = pd.to_datetime(text, format="%d-%m-%Y", errors="coerce")
        assert (parsed.isna() == text.isna()).all(), f"{year} {c}: unparsed dates (format change?)"
        df[c] = parsed
    df["var_name_norm"] = normalise_variety(df.var_name)
    df["transplanted"] = is_transplanted(df.crop_est)
    df["duration_days"] = (df.harvest_date - df.estab_date).dt.days
    return df


def implausible(df: pd.DataFrame) -> pd.Series:
    """Rows whose reported calendar cannot be true: no harvest, harvest before/on establishment,
    or a season longer than MAX_DURATION_D days."""
    return df.duration_days.isna() | (df.duration_days <= 0) | (df.duration_days >= MAX_DURATION_D)


def build(raw_dir: Path, dest: Path, cutoff: pd.Timestamp | None = None) -> pd.DataFrame:
    """Both years -> one table of plausible rows. Returns it; also writes dest."""
    df = pd.concat(
        [load_year(raw_dir / FILES[y]["name"], y) for y in (2017, 2018)], ignore_index=True
    )
    bad = implausible(df)
    print(f"{len(df)} rows, dropping {bad.sum()} implausible (harvest <= estab, or >= 250 d)")
    df = df[~bad].reset_index(drop=True)
    if cutoff is not None:  # D-019: nothing from the 2026-27 season may enter the pipeline
        late = df[list(DATE_COLS)].ge(cutoff).any(axis=1)
        assert not late.any(), f"{late.sum()} rows on/after the D-019 cutoff {cutoff:%Y-%m-%d}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest)
    return df
