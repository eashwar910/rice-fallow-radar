# Data

Every data source the project uses, what it is in plain terms, what it's for, and what we've learned about it. Facts marked *(checked Oct 2026)* came from a review of primary documentation in October 2026 — products, quotas and catalogs change, so recheck before relying on them.

Add to this file whenever a dataset surprises you.

---

## Summary

| ID | Source | What it is | Used for | Access |
|---|---|---|---|---|
| S1 | Sentinel-1 (Torres et al., 2012) | European radar satellite; sees through cloud; 10 m | Main M1 input; waterlogging (M3) | Earth Engine |
| S2 | Sentinel-2 (Drusch et al., 2012) | European optical satellite; 10 m, ~5-day revisit | Winter green-up (M4 positives); waterlogging labels; Odisha hand labels | Earth Engine |
| NISAR | NISAR L3 soil moisture (NASA Earthdata, 2026) | NASA–ISRO radar mission (launched 2025); provisional soil moisture at 200 m | M3 dry-edge initialisation and check | NASA Earthdata (`earthaccess`) |
| SMAP | SMAP (Entekhabi et al., 2010) | NASA soil-moisture satellite; ~9 km; since 2015 | Moisture history before NISAR; M4 baseline thresholds | Earth Engine |
| ERA5-Land | ERA5 family (Hersbach et al., 2020) | Reanalysis — gap-free reconstruction of past weather | Temperature, evaporation | Earth Engine |
| CHIRPS | Funk et al. (2015) | Daily rainfall from satellites + gauges, ~5 km | Rainfall | Earth Engine |
| FTW | Fields of The World (Kerner et al., 2025) | Field-boundary polygons | Unit of analysis | Source Coop / download |
| AE | AlphaEarth embeddings (Brown et al., 2025) | DeepMind model summarising each 10 m pixel per year as 64 numbers | Landscape context for M4 | Earth Engine |
| SICKLE | Sani et al. (2024) | ~388 Tamil Nadu plots with field-recorded harvest dates, 2018–2021 | Train/test M1 | Dataset release (check licence) |
| ODL | Odisha hand labels (this project) | 150–200 fields, harvest week from cloud-free S2 | Test transfer (M2); validate radar harvest detector | Made here |
| CSISA | Ajay et al. (2021, 2022) | 2017 survey of 6,857 rice farmers in Bihar, UP, Odisha | District context; plot-level only if coordinates allow | CIMMYT Dataverse |
| AFN | AgriFieldNet (Radiant Earth & IDinsight, 2022) | Ground-surveyed crop types incl. fallow, four Indian states | M4 validation (lower bounds) | Source Coop |

---

## Notes per source

### Sentinel-1
- *(checked 6 Nov 2026)* Only **20 IW scenes in Jun 2025–Jan 2026** over a 5 km Bolangir block, i.e. one pass every ~12 days, not 6. Plan M1 features for ~12-day spacing.
- Revisit has varied over the years: Sentinel-1B failed in Dec 2021 (ESA, 2022); 1C and later 1D have since joined *(checked Oct 2026)*. Earth Engine listed 6 days. Expect irregular spacing in the time series — model it rather than hide it.
- Use a consistent orbit direction / relative orbit per field where possible, or include it as a feature; incidence angle affects backscatter.
- Speckle: per-field aggregation reduces it; very small polygons will still be noisy — use the valid-pixel count as a quality flag.

### Sentinel-2
- Cloud is the main constraint during the monsoon, which is exactly why radar drives M1. In the dry winter, S2 is much more usable.
- Level-2A surface reflectance in Earth Engine was not global for 2017–2018 *(checked Oct 2026)*; backtests that need those years may need Level-1C (+ own atmospheric correction) or should start from 2019.
- Scene Classification Layer (SCL) gives cloud/shadow/water classes; useful for waterlogging labels.

### NISAR soil moisture
- Provisional product; quality and coverage over Odisha should be checked before M3 relies on it.
- *(checked 6 Nov 2026, CMR via `earthaccess`, ASF)* Two collections: `NISAR_L3_SME2_BETA_V1` (Oct 2025 → Jan 2026) and `NISAR_L3_SME2_PROVISIONAL_V1` (Mar/Jun 2026 → latest 20–22 Oct 2026). Granules over Bolangir: beta 14, provisional 24 (~4–6/month); Baleswar: beta 23, provisional 69 (~12–14/month from Jun). ~55–86 MB per granule. **No NISAR history before Oct 2025**, so it cannot feed training/backtests on 2018–2024 seasons — only 2025–26 (beta, lower maturity) and the 2026–27 replay. Newest granule was ~2 weeks old on 6 Nov → apparent publication lag to respect in `as_of`.
- *(checked 6 Nov 2026, one granule: 22 Oct 2026, descending, Bolangir)* HDF5 on a 200 m EASE-Grid 2.0 (1-D `latitude`/`longitude` arrays), path `science/LSAR/SME2/grids/`. `soilMoisture` in m³/m³ is an average of three algorithms (PMI, TSR, DSG — each also stored separately); `retrievalQualityFlag` bit 0 = 0 means "recommended". Swath covered only the western part of the district (lon ≤ 83.56). Within the district bbox: 36% of cells valid, and only 50% of those recommended. Values 0.19–0.33 (5–95%), median uncertainty 0.04 m³/m³ — the same order as the gap between "workable" and "too dry", so M3 must carry this uncertainty, not treat NISAR as truth.
- Keep the granule IDs/version used so a validated reprocessing can be swapped in later.
- ISRO's Bhoonidhi also released a 100 m Indian soil-moisture product in March 2026 — worth checking as an alternative or complement for M3.

### SMAP
- ~9 km pixels against fields of a fraction of a hectare: useful as context and history, not field-level truth.
- The 30% / 35% thresholds used as M4's baseline come from the IRRI–Odisha suitability classes; their exact definition is worth pinning down before the comparison.

### ERA5 / ERA5-Land
- The Earth Engine ERA5 *daily* collection stopped in July 2020; **ERA5-Land daily** is current *(checked Oct 2026)*.
- ERA5-Land's evaporation components were noted as sign/naming-swapped; `total_evaporation_sum` was the recommended band *(checked Oct 2026)*. Verify signs on a known dry week before using.
- Reanalysis has a publication lag of days — respect it in `as_of` logic.

### CHIRPS
- Has a preliminary and a final product with different lags. The final product in Earth Engine ended 31 Aug 2026 when checked *(Oct 2026)* — recheck; it may simply lag. For replay, use only what would have been available on each issue date.

### Fields of The World
- Polygons from a global segmentation model. The October review found reports of fragmented polygons in smallholder settings and confidence cut-offs that emptied some sites. Run QA gates (area, compactness, overlap, coverage of visible fields) on Bolangir and Baleswar before trusting it; visually inspect a sample.
- *(checked 6 Nov 2026)* Global FTW predictions (PRUE model, CC-BY-4.0) are one GeoParquet per Indian state on Source Cooperative (`.../admin:country_code=IN/IN_OD.parquet`, 1.65 GB, 26.5 M polygons); `ingest/ftw.py` reads just a district's bbox via DuckDB. Polygons are from 2024 imagery only. **`confidence` is null for every field in both districts** — the confidence layer doesn't cover India, so there is no model-side quality filter.
- First numbers: Bolangir 1.63 M polygons (118 k ha), Baleswar 0.92 M (85 k ha). Median polygon **0.037 ha / 0.046 ha** (~19–21 m square); 52% / 48% are under 0.04 ha (< 4 Sentinel-1 pixels); only 20–24% are ≥ 0.1 ha. Strong sign of fragmentation (SICKLE's average plot is ~0.15 ha) — visual check pending (P0 step 8).
- Visual check (P0 step 8): `scripts/ftw_sample_map.py` samples 6 × 500 m cells per district (seed 20261106, terciles of polygon density) and maps them over Esri World Imagery. Note that the Esri imagery date varies by tile and isn't the 2024 S2 imagery FTW used, so field edges can legitimately differ.
- **Verdict (10 Nov 2026, Eashwar's visual ratings of the 12 cells, `data/interim/ftw_check/ratings.csv`):** 1 good, 4 usable, 2 usable/poor, 4 poor, 1 can't tell. Failure flags: over-split 9/12 cells, merged 9/12, missed fields 9/12, false fields 6/12 (+1 "not sure"); the two sparse Bolangir cells contain no fields at all. So raw FTW is **not** a clean field map here: dense cells are usable, sparse cells contain false polygons. Only 12 cells, so read as a sanity check, not an error rate.
- **Size filter effect** (from the downloaded parquets): keeping polygons ≥ 0.1 ha retains 19% of polygons / 60% of area in Bolangir and 24% / 70% in Baleswar (≥ 0.04 ha: ~50% of polygons, 85–89% of area). 0.1 ha is about SICKLE's median plot (16 px ≈ 0.16 ha) and matches the ≥ 1000 m² set used in the EECU pilot. A size filter does **not** remove false polygons on non-field land, so a cropland filter is probably also needed (untested).
- If FTW is poor here, alternatives: run the FTW model with a different threshold, simple segmentation on S2, or fixed-size grid cells as a fallback unit.

### AlphaEarth embeddings
- Annual, summarising the full calendar year's surface — so year Y's embedding already "knows" year Y's winter crop. **Use year Y−1 for anything predicting year Y.**
- Catalog covered 2017–2024 when checked *(Oct 2026)*.

### SICKLE
- The authoritative label source for M1. **Reconciled (6 Nov 2026):** "388 plots" (proposal) is not in the release; the release has 351 plots in total, 262 with paddy, and only **131 plots / 319 seasons with observed harvest dates** (below). The paper's "351 paddy samples" figure doesn't match any count in the release either. Coordinates withheld; licence still unknown.
- *(checked 6 Nov 2026, actual release; every number in this section is reproduced by `scripts/sickle_profile.py`)* `sickle_dataset/` (15 GB, git-ignored): `sickle_dataset_tabular.csv` (2,370 samples × 17 cols: `UNIQUE_ID, PLOT_ID, RIVER_PART, STANDARD_SEASON, YEAR, AREA (acres), CROP, VARIETY, PADDY_BIN, SOWING/TRANSPLANTING/HARVESTING_DATE (m/d/Y), *_DAY, YIELD, SPLIT`), `images/{S1,S2,L8}/npy/<UNIQUE_ID>/<scene_id>.npz`, `masks/{3m,10m,30m}/<UNIQUE_ID>.tif`. Split train 1937 / val 227 / test 206 samples. **Test rows are empty apart from season/year** (no PLOT_ID, labels or masks), so the test set is unusable until the authors release it, and whether test plots overlap train can't be checked. `sickle_toy_dataset/` is a 217-sample subset of train/val.
- **Two kinds of harvest date.** 907 paddy samples have a harvest date, but 588 of them have no yield and their date is the *same month-day every year for that plot-season* (99%; mostly 30th/31st). These are the paper's "rough estimates", i.e. typical dates, not observations. **Usable M1 labels = 319 samples with yield > 0, from 131 plots, years 2019 and 2020 only** (train 282 / val 37). The rough set covers a *different* 131 plots (no overlap) and 2018–2020. Seasons: sep-feb 178, oct-mar 82, may-sep 51, other 8. Harvests mostly Jan–Mar, plus Aug for may-sep. `RIVER_PART` is empty for all of these. Sowing → harvest 99–195 days (median 138).
- **`*_DAY` = 1-indexed days since the 1st of the season's start month** (e.g. oct-mar → 1 Oct). Verified against the dates on every exact sample.
- **Baseline floor.** Within one season-year, harvest-day sd is 15–17 days for sep-feb and 11–16 days for oct-mar (MAE vs. the group mean 10–14 days), but only 6–8 days for may-sep (MAE 4–6 days). So a per-season "average date" baseline already gets roughly 10–12 days pooled, and per-season results must be reported separately or may-sep will flatter the pooled number.
- **Masks** are 6-band GeoTIFFs with the georeferencing stripped (identity transform). Band 1 = PLOT_ID, 3/4/5 = sowing/transplanting/harvest day (band 5 equals `HARVESTING_DAY` on every exact sample's pixels); bands 2 and 6 not identified yet (2 looks like a crop class). **The patch includes neighbouring plots**, so features must use `mask == PLOT_ID`, not the whole patch. Plot size at 10 m: median 16 px, min 2, and 21% of exact samples have < 10 px, so speckle matters; keep pixel count as a quality feature (same as for FTW).
- **Spatial leakage in the official split:** 137 of the 319 exact samples have a plot from the *other* split (train ↔ val) inside their 320 m patch. Neighbours are correlated, so the authors' val numbers are optimistic. Coordinates are withheld, but plot co-occurrence in the masks gives a neighbour graph. **Proposal: split M1 by connected components of that graph** (grouped CV), which gives the spatial blocking EVALUATION.md asks for without coordinates.
- **Time coverage vs. harvest (exact set):** 11–23 S1 scenes per sample (median 17); the first scene is 94–178 days before harvest, the last one before harvest is a median 5 days before it, and ~2 scenes fall *after* harvest. Only ~2 scenes (0–4) land in the final 21 days. **Patches run past harvest, so they must be truncated at `as_of`**: the stock patches would leak the harvest signature into a forecast. S2: 30–146 scenes per sample (cloud not yet assessed).
- **Authors' baselines** (`runs/wacv_2024/harvesting_date/*/trainlog.json`, best val epoch): S1-only UNet3D 8.7 d MAE, U-TAE 10.4, ConvLSTM 18.2; S2+L8+S1 UNet3D 7.7; L8 UNet3D 7.3. Read these with care: they are **hindcasts on full-season series (post-harvest scenes included)**, trained and validated with the 588 rough dates mixed in (val = 37 exact + 71 rough), use the best epoch picked *on* val, and use the leaky split. They are an optimistic upper reference, not a target M1 has to beat at 7–21 days lead.
- Labels come from farmer recall in 2021–22 surveys → a few days of label noise; 16% of exact-set plot-seasons still repeat the same month-day across both years.
- **S1 pre-processing is evidently GEE `COPERNICUS/S1_GRD`:** files are named by the original S1 scene IDs, values are in dB (VV median ≈ −7.4, VH ≈ −13.8), and there is an `angle` band — all as in the GEE collection (terrain-corrected, no speckle filter). Patches ~34×33 px at 10 m (320 m), zeros = no-data. 11–23 scenes per season (S1A only, ~12-day spacing). Odisha features can therefore use the same GEE collection with matching per-field mean in dB.
- **Plot coordinates are withheld for privacy** (paper). SICKLE S1 features must be computed from the shipped patches + masks.
- *(noted 17 Nov 2026)* **Consequence for weather:** with no coordinates and georeferencing stripped from the masks, CHIRPS/ERA5-Land can't be sampled per plot. M1's weather inputs for SICKLE will have to be regional (one series per season for the study area) unless locations can be recovered. Options in OPEN_QUESTIONS.md #11. No dataset licence published; authors asked.
- One irrigated delta (Cauvery) — fundamentally different water regime from rainfed Odisha. That difference is the subject of M2.

### Odisha hand labels
- Made in this project from cloud-free Sentinel-2 — independent of the radar input, which is why they can validate a radar harvest detector.
- Keep the labelling protocol, labeller notes and double-labelled subset with the data.

### CSISA
- The 2018 companion survey truncates coordinates to about 1 km (Ajay et al., 2022) — probably too coarse to match fields, which is why the hand-labelled set replaced it as the transfer test. The 2017 file may differ; check before discarding. Any use needs ethics approval and licence compliance.

### AgriFieldNet
- Ground-surveyed crop types including fallow; check which states/seasons overlap usefully with the winter-crop question.
- Fallow is treated as negative *for validation only*, which makes M4's scores lower bounds.

---

## Earth Engine compute
- Noncommercial quota tiers applied from 27 Apr 2026: Community tier 150 EECU-hours/month; Contributor tier 1,000 with a billing account attached (Earth Engine itself not charged) *(checked Oct 2026)*. Noncommercial status needs annual reverification; splitting work across projects to dodge quotas breaks the terms.
- Measure EECU use on a small pilot block in P0, then extrapolate. Export per-field tables, not rasters.
- *(pilot 6 Nov 2026, `scripts/ee_cost_pilot.py`: 950 FTW fields ≥ 1000 m² in a 5 km Bolangir block, Jun 2025–Jan 2026)* The tasks failed only at the write step (service accounts have no Drive quota), but EE still reported the compute used. **S1** (20 scenes, VV/VH/angle mean+count at 10 m): 61 EECU-s ≈ 3.2 ms per field-scene. Both districts have 540 k fields ≥ 1000 m² (Bolangir 317 k, Baleswar 223 k), so one season of S1 ≈ **10 EECU-h**, and ~6 backtest seasons ≈ 60 h, within the 150 h/month Community tier. **CHIRPS done the same way is ~30× worse** (1,893 EECU-s for 245 days ≈ 8 ms per field-day → ~300 h per season): reducing 5.5 km pixels once per tiny polygon per day is wasteful. Sample CHIRPS/ERA5 once per coarse pixel (or stack the days with `toBands()` and run one `reduceRegions`), then join to fields locally. Rough figures: linear extrapolation from one block, and failed-task EECU may slightly undercount a completed export.
- **Export destination: decided 13 Nov, see D-017 (direct `computeFeatures` pull).** Original note: the project asset root (`projects/rice-fallow-radar/assets`) returns "not found" to the service account, even after opening the Code Editor. Either give `rfr-earthengine@…` an Earth Engine writer role / initialise the root from the Cloud console, or skip storage and pull per-field tables directly with `ee.data.computeFeatures` in chunks (no bucket or asset needed). The direct pull is probably simplest for P1.

## Weather forecasts (open)
For a truly live system, M3 would need forecast rainfall/temperature. GFS 0.25° is in Earth Engine but has no evaporation band (compute reference ET from its variables). For the replay, a decision is needed: use forecasts as they were issued (honest, harder) or observed weather (optimistic upper bound). See `OPEN_QUESTIONS.md`.
