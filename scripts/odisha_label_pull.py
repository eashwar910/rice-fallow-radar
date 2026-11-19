"""P1b: sample fields to label and pull the Sentinel-2 series and chips they need.

Four resumable stages, each skipped if its output exists (delete to redo):
  1 sample.parquet   candidate pool, stratified by district x area tercile x 5 km block
  2 ndvi.parquet     per-field NDVI + Cloud Score+ cloudiness for every S2 scene of the season
  3 selected.parquet the 200 fields to label (stratum U uniform, stratum K kharif-signature,
                     D-025) plus the repeat subset
  4 chips/           one true-colour PNG per field and usable date

Usage:
  uv run python scripts/odisha_label_pull.py --pilot 5   # chips for 5 fields, to check quality
  uv run python scripts/odisha_label_pull.py             # chips for all selected fields
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlretrieve

import ee
import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from rice_fallow_radar.ingest import s2
from rice_fallow_radar.ingest.earth_engine import init

OUT = Path("data/interim/odisha_labels")
CFG = yaml.safe_load(Path("configs/districts.yaml").read_text())
L = CFG["labelling"]
CHUNK = 40  # fields per computeFeatures call (D-017: keep calls short)


def stage1_sample() -> gpd.GeoDataFrame:
    reg = gpd.read_parquet("data/processed/fields.parquet")
    per_cell = L["pool"] // 6  # 2 districts x 3 area terciles
    reg["tercile"] = reg.groupby("district").area_m2.transform(
        lambda s: pd.qcut(s, 3, labels=[0, 1, 2])
    )
    # one field per 5 km block per stratum, so the pool is spread over each district
    parts = [
        g.sample(frac=1, random_state=L["seed"]).drop_duplicates("block").head(per_cell)
        for _, g in reg.groupby(["district", "tercile"], observed=True)
    ]
    pool = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=reg.crs)
    pool.to_parquet(OUT / "sample.parquet")
    print(f"1: pool {len(pool)} fields, {pool.block.nunique()} blocks")
    return pool


def stage2_ndvi(pool: gpd.GeoDataFrame) -> pd.DataFrame:
    init()
    start, end = str(L["season_start"]), str(L["season_end"])
    assert end < str(CFG["data_cutoff"]), "D-019: season window must end before the data cut-off"
    pool = pool.sort_values(["district", "block"]).reset_index(drop=True)
    frames = []
    for i in range(0, len(pool), CHUNK):
        sub = pool.iloc[i : i + CHUNK]
        fc = ee.FeatureCollection(json.loads(sub[["field_id", "geometry"]].to_json()))
        aoi = ee.Geometry.Rectangle(list(sub.total_bounds))
        col = s2.collection(aoi, start, end)
        table = col.map(lambda img, fc=fc: s2.per_image(fc, img, ["ndvi", "cloud"])).flatten()
        df = ee.data.computeFeatures({"expression": table, "fileFormat": "PANDAS_DATAFRAME"})
        frames.append(df.drop(columns=[c for c in ("geo",) if c in df]))
        print(f"2: {i + len(sub)}/{len(pool)} fields, {sum(map(len, frames))} rows", flush=True)
    ndvi = pd.concat(frames, ignore_index=True).dropna(subset=["ndvi_mean"])
    ndvi["date"] = pd.to_datetime(ndvi.date)
    ndvi.to_parquet(OUT / "ndvi.parquet")
    return ndvi


def stage3_select(pool: gpd.GeoDataFrame, ndvi: pd.DataFrame) -> pd.DataFrame:
    """Stratum U: uniform. Stratum K: a monsoon-crop NDVI shape (green Sep-Oct, brown by Jan)."""
    clear = ndvi[ndvi.cloud_mean <= L["cloud_max"]]
    m = clear.assign(mon=clear.date.dt.to_period("M").astype(str)).pivot_table(
        index="field_id", columns="mon", values="ndvi_mean"
    )
    green = m[[c for c in m if c in ("2025-09", "2025-10")]].max(axis=1)
    brown = m[[c for c in m if c in ("2026-01", "2026-02")]].min(axis=1)
    kharif = (green > 0.45) & (green - brown > 0.2)
    p = pool.set_index("field_id")
    p["n_clear"] = clear.groupby("field_id").size().reindex(p.index).fillna(0).astype(int)
    p["green_peak"] = green.reindex(p.index).round(3)
    p["ndvi_fall"] = (green - brown).reindex(p.index).round(3)
    p["kharif_signature"] = kharif.reindex(p.index).fillna(False)
    half = L["n_label"] // 2
    rng = np.random.default_rng(L["seed"])
    usable = p[p.n_clear >= 4]  # need some clear images to label at all
    u = pd.concat(
        [
            g.sample(min(half // 2, len(g)), random_state=L["seed"])
            for _, g in usable.groupby("district")
        ]
    )
    rest = usable.drop(index=u.index)
    k = pd.concat(
        [
            g.sample(min(half // 2, len(g)), random_state=L["seed"] + 1)
            for _, g in rest[rest.kharif_signature].groupby("district")
        ]
    )
    sel = pd.concat([u.assign(stratum="U"), k.assign(stratum="K")]).reset_index()
    sel["order"] = rng.permutation(len(sel))  # labelling order, so strata are interleaved
    rep = rng.choice(sel.index, size=min(L["n_repeat"], len(sel)), replace=False)
    sel["repeat_of"] = pd.NA
    dupes = sel.loc[rep].copy()
    dupes["repeat_of"] = dupes.field_id
    dupes["order"] = len(sel) + np.arange(len(dupes))  # repeats go to the end of the queue
    sel = pd.concat([sel, dupes], ignore_index=True).sort_values("order", ignore_index=True)
    sel["row_id"] = [f"f{i:03d}" for i in range(len(sel))]  # what the tool shows; hides repeats
    sel.to_parquet(OUT / "selected.parquet")
    print(
        f"3: {int((sel.repeat_of.isna()).sum())} fields to label "
        f"(U {int((sel.stratum == 'U').sum())}, K {int((sel.stratum == 'K').sum())}) "
        f"+ {len(dupes)} repeats; kharif signature in pool: {p.kharif_signature.mean():.0%}"
    )
    return sel


def stage4_chips(sel: pd.DataFrame, ndvi: pd.DataFrame, pilot: int | None) -> None:
    init()
    lo, hi = (str(d) for d in L["chip_window"])
    jobs = []
    rows = sel[sel.repeat_of.isna()]
    rows = rows.head(pilot) if pilot else rows
    usable = ndvi[(ndvi.cloud_mean <= L["cloud_max"]) & ndvi.date.between(lo, hi)]
    geom = gpd.read_parquet(OUT / "sample.parquet").set_index("field_id").geometry
    for r in rows.itertuples():
        d = OUT / "chips" / r.field_id
        d.mkdir(parents=True, exist_ok=True)
        g = geom.loc[r.field_id]
        half = L["chip_m"] / 2 / 111_320
        win = ee.Geometry.Rectangle(
            [g.centroid.x - half, g.centroid.y - half, g.centroid.x + half, g.centroid.y + half]
        )
        outline = ee.Geometry(g.__geo_interface__)
        mine = usable[usable.field_id == r.field_id]
        # a field on an MGRS boundary has two scenes per date; both are needed for one chip
        for date, scenes in mine.groupby(mine.date.dt.strftime("%Y-%m-%d")).scene:
            p = d / f"{date}.png"
            if not p.exists():
                jobs.append((p, list(scenes), win, outline))
    print(f"4: {len(jobs)} chips to fetch for {rows.field_id.nunique()} fields", flush=True)

    def fetch(job):
        p, scenes, win, outline = job
        try:
            urlretrieve(s2.chip_url(scenes, win, outline), p)
        except Exception as e:  # a dead scene id should not kill the batch
            print(f"  failed {p.parent.name}/{p.name}: {e}", flush=True)

    with ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(fetch, jobs), 1):
            if i % 100 == 0:
                print(f"   {i}/{len(jobs)}", flush=True)
    on_disk = list((OUT / "chips").rglob("*.png"))
    mb = sum(p.stat().st_size for p in on_disk) / 1e6
    print(f"4: {len(on_disk)} chips on disk, {mb:.1f} MB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, help="only fetch chips for the first N fields")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    pool = (
        gpd.read_parquet(OUT / "sample.parquet")
        if (OUT / "sample.parquet").exists()
        else stage1_sample()
    )
    ndvi = (
        pd.read_parquet(OUT / "ndvi.parquet")
        if (OUT / "ndvi.parquet").exists()
        else stage2_ndvi(pool)
    )
    sel = (
        pd.read_parquet(OUT / "selected.parquet")
        if (OUT / "selected.parquet").exists()
        else stage3_select(pool, ndvi)
    )
    stage4_chips(sel, ndvi, a.pilot)


if __name__ == "__main__":
    sys.exit(main())
