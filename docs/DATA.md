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
- Revisit has varied over the years: Sentinel-1B failed in Dec 2021 (ESA, 2022); 1C and later 1D have since joined *(checked Oct 2026)*. Earth Engine listed 6 days. Expect irregular spacing in the time series — model it rather than hide it.
- Use a consistent orbit direction / relative orbit per field where possible, or include it as a feature; incidence angle affects backscatter.
- Speckle: per-field aggregation reduces it; very small polygons will still be noisy — use the valid-pixel count as a quality flag.

### Sentinel-2
- Cloud is the main constraint during the monsoon, which is exactly why radar drives M1. In the dry winter, S2 is much more usable.
- Level-2A surface reflectance in Earth Engine was not global for 2017–2018 *(checked Oct 2026)*; backtests that need those years may need Level-1C (+ own atmospheric correction) or should start from 2019.
- Scene Classification Layer (SCL) gives cloud/shadow/water classes; useful for waterlogging labels.

### NISAR soil moisture
- Provisional product; quality and coverage over Odisha should be checked before M3 relies on it.
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
- If FTW is poor here, alternatives: run the FTW model with a different threshold, simple segmentation on S2, or fixed-size grid cells as a fallback unit.

### AlphaEarth embeddings
- Annual, summarising the full calendar year's surface — so year Y's embedding already "knows" year Y's winter crop. **Use year Y−1 for anything predicting year Y.**
- Catalog covered 2017–2024 when checked *(Oct 2026)*.

### SICKLE
- The authoritative label source for M1. Confirm: number of plots and seasons with harvest dates (proposal says 388 plots; the dataset paper also reports ~351 paddy seasons with dates — reconcile), coordinate precision, licence for derived data.
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

## Weather forecasts (open)
For a truly live system, M3 would need forecast rainfall/temperature. GFS 0.25° is in Earth Engine but has no evaporation band (compute reference ET from its variables). For the replay, a decision is needed: use forecasts as they were issued (honest, harder) or observed weather (optimistic upper bound). See `OPEN_QUESTIONS.md`.
