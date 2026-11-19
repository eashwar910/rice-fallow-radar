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
- **Done:** literature search for the rice mask (DATA.md §Rice mask): ~53% of Odisha rice is direct-seeded; no open Odisha kharif labels; FARM-style rule → pseudo-label → classifier fits. Email sent to IRRI Odisha for ground truth (optional). **Decided:** D-021, hybrid rice mask.
- **Changed:** Eashwar: no step may depend on a reply from outside people; replies are bonuses.
- **Done:** checked AgriFieldNet (214 Odisha chips, all in southern Odisha, none in our districts; mostly fallow + some rice, season undocumented, probably rabi: M4 use only) and Open-SARice (2024 EE assets readable; 0/5 fakes mapped as rice; Baleswar 65–71% vs Bolangir 19–23% of real outlines mapped as rice).
- **Done:** SICKLE neighbour groups (`scripts/sickle_neighbour_groups.py`): 131 exact plots → 43 groups, largest 9% of dates. **Decided:** D-022, neighbour-group CV + locked ~20% test.
- **Next:** open questions #11–12; then P1.

## 2026-11-19

- **Decided:** D-023 (SICKLE weather = one regional series for the study area, with a regional-vs-per-field flag in the feature table) and D-024 (the 588 rough recalled dates stay out of M1; optional down-weighted ablation later). Open questions #11 and #12 closed; #10 (licence/test set) stays parked — plan assumes no reply.
- **Changed:** target for the 3 Dec interim report is "midway through P2" — baselines plus a first LightGBM on SICKLE, not a finished M1.
- **Next:** P1 field registry (`registry/fields.py` → `data/processed/fields.parquet` + area stats), then the P1b labelling protocol so Eashwar can start labelling while SICKLE features and the M1 baselines are built. Protocol freeze still due 30 Nov.

## 2026-11-19 (second session) — P1 registry, P1b tool, first M1 numbers

- **Done (P2 step 1): SICKLE extracts into usable per-plot radar series.** `ingest/sickle.py` + `scripts/sickle_extract_check.py` → `data/interim/sickle_s1_series.parquet` (5,782 rows, 5,499 usable). Findings in `DATA.md` §SICKLE: patch/mask shapes wobble by a pixel and the alignment is ambiguous but near-harmless (median 0.52 dB on 3.7% of scenes); 283 edge-clipped scenes drop out, taking 14 samples with them (305 of 319 left).
- **Learned (important):** the S1 harvest drop is **weak (median +0.51 dB, present in 60% of samples)** and **negative in may-sep (−0.49 dB, 42%)** — monsoon harvests leave a wet field, so VH rises. Plot size doesn't explain it. This sets expectations for M1 and is a real dissertation point: the season with the tightest date spread is the one where radar helps least.
- **Done (P1): field registry.** `registry/fields.py` + `scripts/build_field_registry.py` → `data/processed/fields.parquet` (292,060 fields) and `field_registry_stats.csv`. Stable `field_id` from a geometry hash; `block` (5 km) for spatial splits; WorldCover cropland fraction computed locally from cached COG windows in 11 s instead of ~550 EE chunks, validated against the 17 Nov EE values (91% within 0.01).
- **Learned (important): the FTW parquet stacks two annual layers (2024 and 2025).** 41–53% of polygons ≥ 0.1 ha overlap another, median overlap 67–72% of own area, and *every* overlap is cross-vintage. Also 1,902 duplicate ids in Baleswar and 331 duplicate geometries. **Decided D-026:** keep the 2025 vintage only. This also means the P0 FTW quality ratings and the 17 Nov cropland check were made on a doubled map, so D-016's verdict is pessimistic and the checks are worth re-running.
- **Done (P1b): protocol + sample + tool.** `docs/LABELLING_PROTOCOL.md` written before any labelling. 498-field pool → NDVI/Cloud-Score+ series → 200 fields in two strata (**D-025**: 100 uniform, 100 kharif-signature) + 20 repeats, interleaved and hidden behind `row_id`. `scripts/odisha_label_pull.py` (resumable, `--pilot`) and `scripts/odisha_label_tool.py` → offline `index.html`: date-ordered chip strip, click = first harvested image (previous clear image auto-marked as last green), shift-click to move the green end, rice yes/no/unsure, five status codes, NDVI curve with the interval shaded, localStorage, CSV download, Copernicus Browser link per field.
- **Learned: the chip pilot was worth doing.** First attempt was unusable — a 500 m window lost a 0.1 ha field in context, the 300–2800 stretch rendered standing rice almost black, and fields on an MGRS boundary came back half white (read as bare soil). Fixed to a 200 m window, 150–2500 stretch, and a same-day scene mosaic; the green→brown change is then unmistakable at 10 m. **No Copernicus Browser fallback needed**, though the per-field link stays as an escape hatch.
- **Done (P2 step 1): the two M1 baselines.** Feature table `data/processed/sickle_m1_features.parquet` (2,745 rows × 42 features, weekly issue dates, leakage-tested). Out-of-fold on the dev split (D-022 neighbour groups, test groups locked in `configs/sickle_test_groups.json` and untouched): **seasonal mean 12.0 d [9.9, 14.3]**, **VH-peak rule 17.1 d [16.1, 18.2]**. Results in `runs/sickle_m1_baselines.csv`.
- **Learned:** the radar phenology rule **loses to the calendar**. With the peak searched over the full 120-day lookback it scores 31.8 d, because the Cauvery delta is multi-cropped and the highest VH is often the *previous* crop's canopy peak; windowing the search to 45 days gets it to 17.1 d, still behind. The seasonal mean is lead-invariant by construction (it ignores `as_of`), so **any lead-dependence in later models is the part that is actually forecasting**.
- **Decided:** D-025 (two labelling strata), D-026 (FTW vintage), D-027 (SICKLE weather per MGRS tile — the tile is recoverable from the S2 patch filenames, so the study extent is measured: 78.61–80.18 °E, 9.85–11.76 °N).
- **Risk to flag:** the proposal's success criterion is MAE ≤ 7 days at the 14-day horizon. The calendar baseline is already 12.0 d and the labels carry farmer-recall noise on 16-pixel plots. Halving the baseline error may not be reachable on SICKLE; the interim report should say so and propose reporting improvement-over-baseline alongside the absolute target.
- **Next:** LightGBM on this feature table (the headline interim number), then conformalised quantile intervals. Eashwar to start labelling. Protocol freeze 30 Nov.
