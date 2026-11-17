# Progress log

A running record of what happened, what was learned and what's next. Short entries are fine. This becomes raw material for the dissertation and the interim report, and it tells a future reader (or Claude) where things stand.

Suggested shape per entry — use whatever is useful:

- **Done:** what got finished
- **Learned:** surprises, numbers, things that didn't work
- **Changed:** any plan or decision change (and a `DECISIONS.md` entry if it matters)
- **Next:** what's up next

---

## 2026-11-05

- **Done:** proposal submitted (29 Oct). Repo docs created: CLAUDE.md, roadmap, architecture, models, data, evaluation, decisions, open questions, glossary.
- **Next:** P0 setup — environment, Earth Engine project, Earthdata login, SICKLE download; ethics application due 12 Nov. First look at FTW polygon quality in the study districts.
- **Done (P0):** GEE noncommercial project (Community tier), NASA Earthdata login, SICKLE access form, GitHub repo. Repo scaffold: uv/Python 3.12 env with lockfile, ruff + pre-commit, pytest smoke tests, GitHub Actions CI, `configs/districts.yaml`, Makefile (D-014, D-015).
- **Learned:** SICKLE phenology/yield labels exist for only 351 paddy samples from 145 plots (not 388 plots); test split withheld (authors said "working on hosting" Oct 2024, no update since); plot coordinates withheld for privacy; labels from farmer recall in 2021–22 surveys; no dataset licence published. Email to authors drafted (test set, coordinates, S1 pre-processing, terms).
- **Next:** authenticate GEE + Earthdata locally, then GEE smoke test and EECU cost pilot (step 5).

## 2026-11-06

- **Done (P0):** GEE service-account auth (browser OAuth was blocked); district boundaries switched to FAO GAUL 2025; Earthdata login; NISAR coverage + one granule inspected; FTW polygons for both districts downloaded (`ingest/ftw.py`); SICKLE downloaded and profiled. All findings in `DATA.md`.
- **Learned:** usable SICKLE labels are 319 seasons / 131 plots / 2 years (588 more are recalled "typical" dates). FTW polygons look heavily fragmented (median ~0.04 ha) and carry no confidence in India. S1 passes ~every 12 days. NISAR: none before Oct 2025, ~36% valid cells over Bolangir, uncertainty ~0.04 m³/m³.
- **Blocked → resolved (later 6 Nov):** EE cost pilot rerun with a Drive export. The write failed (service accounts have no Drive quota), but EECU was reported: S1 ≈ 10 EECU-h/season for both districts; CHIRPS per field ~300 h/season → sample coarse rasters per pixel. Asset root still not visible to the SA even after opening the Code Editor.
- **Next:** visual FTW check (step 8), EECU pilot rerun, decide field unit if FTW fails.
- **Done (P0 step 7, redo):** `scripts/sickle_profile.py` now reproduces the SICKLE profile. Corrected earlier notes: the test split is empty, not just unlabelled, and the masks have only 3m/10m/30m folders.
- **Learned:** exact and rough labels come from disjoint plot sets. Masks contain neighbouring plots, and 137/319 exact samples share a patch with a plot from the other official split (spatial leakage). Patches extend ~2 scenes past harvest. Authors' harvest-date runs: S1 UNet3D 8.7 d val MAE (an optimistic hindcast). The may-sep season has a much tighter spread (sd 6–8 d) than sep-feb (15–17 d).

## 2026-11-10

- **Done (P0 step 8):** Eashwar rated the 12 FTW sample cells. Verdict written to `DATA.md` §FTW; field-unit decision D-016.
- **Learned:** ratings were 1 good / 4 usable / 2 usable-poor / 4 poor / 1 can't tell; over-split and missed fields were the most common flags, and sparse cells hold false polygons. ≥ 0.1 ha keeps 60–70% of FTW area but only 19–24% of polygons.
- **Next:** decide SICKLE grouped-split (record in `DECISIONS.md`) and the EE export route (`computeFeatures` vs fixing IAM); ethics due 12 Nov; reproducibility paragraph; commit the P0 scaffold.

## 2026-11-13

- **Done (P0 close-out):** ethics submitted (by 12 Nov). Reproducibility paragraph drafted (ROADMAP §P0). EE export route decided: D-017. Tracker rows for repo scaffold and docs corrected (scaffold was already committed, CI green).
- **Learned:** `computeFeatures` works on the service account. 950 fields × 20 S1 scenes = 19,000 rows in 364 s, linear in scenes. Full-district S1 for one season is ~50+ h serial, so the P1 pull must run requests in parallel and cache chunks.
- **Next:** SICKLE grouped-split decision (D-018), then P1 field registry + `build_features`.

## 2026-11-17

- **Done:** P0 docs committed and pushed (`e426987`); P0 marked done in ROADMAP. Stock-take of data on hand vs. needed.
- **Have:** SICKLE (labels + S1/S2/L8 patches), FTW polygons for both districts, one NISAR granule. **Still to pull (P1):** Odisha S1/S2 per field, CHIRPS, ERA5-Land, SMAP, NISAR series, AlphaEarth, AgriFieldNet, CSISA; Odisha hand labels to make.
- **Learned:** SICKLE's withheld coordinates also block per-plot weather, not just spatial blocking. Weather for SICKLE will likely be regional (OPEN_QUESTIONS #11).
- **Changed:** Eashwar: internal ROADMAP dates are formalities; do the full P1, no S1+CHIRPS-only shortcut. Open questions list updated (#1, #2, #5 answered; #7–12 added: cropland filter, rice mask, SICKLE split, licence, SICKLE weather, rough labels).
- **Decided:** D-018, Odisha hand labels: past seasons only, ~200 fields, labelled by Eashwar (Copernicus Browser check showed the green → brown change is visible). 2026–27 labels reconsidered in Jan 2027.
- **Decided:** D-019, no 2026–27 data before the protocol freeze, enforced by a date cut-off (1 Jun 2026) in code.
- **Done:** cropland filter check (`scripts/cropland_filter_check.py`): Eashwar rated 205 FTW polygons ≥ 0.1 ha blind; 194 real / 5 fake / 6 unsure. **Decided:** D-020, no land-cover filter; WorldCover fraction kept as a column.
- **Next:** go through open questions #8–12 one at a time, then P1.
