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
- **Learned (and amended D-025 the same day):** the kharif-signature criterion meant to make stratum K rice-rich is **non-selective — 88% (Bolangir) / 94% (Baleswar) of pool fields pass it**, and the two strata are indistinguishable. Open-SARice's "19–23% of Bolangir outlines are rice" does not mean few fields grow a monsoon crop; it means few grow *rice*, and no cheap optical rule separates the two. The 200 fields stand but are treated as one near-uniform sample, and **the labeller's rice tick is now the main independent read on rice prevalence** (and on D-021's mask). Also: 0 of 498 pool fields had fewer than 4 clear S2 images (median 37–39), so cloud exclusion is not the risk the protocol assumed.
- **Decided:** D-025 (two labelling strata, amended same day), D-026 (FTW vintage), D-027 (SICKLE weather per MGRS tile — the tile is recoverable from the S2 patch filenames, so the study extent is measured: 78.61–80.18 °E, 9.85–11.76 °N).
- **Risk to flag:** the proposal's success criterion is MAE ≤ 7 days at the 14-day horizon. The calendar baseline is already 12.0 d and the labels carry farmer-recall noise on 16-pixel plots. Halving the baseline error may not be reachable on SICKLE; the interim report should say so and propose reporting improvement-over-baseline alongside the absolute target.
- **Done:** all **6,156 chips** generated for the 200 fields (42 MB, median 28 clear dates per field, range 24–55; 0 clear dates missing a chip). 3 of ~6,100 requests hit a transient Earth Engine 503; the fetch now retries once and the stage is resumable, so a re-run fills any gap. `data/interim/odisha_labels/index.html` is ready to open — **labelling can start**.
- **Next:** LightGBM on this feature table (the headline interim number), then conformalised quantile intervals. Eashwar to start labelling. Protocol freeze 30 Nov.

## 2026-11-20 — P1b labelling done

- **Done: all 220 queue rows labelled in one sitting** (19–20 Nov, ~6 h), exported to
  `data/interim/odisha_labels/labels_2026-11-20.csv`. `scripts/odisha_label_ingest.py` joins the
  sampling frame, splits off the repeats, recomputes each interval and midpoint, and writes
  `data/processed/odisha_labels.parquet` (200 first-labellings, `eval_lock` assigned from the
  config seed before any model has seen a label: **92 locked / 61 free** of 153 `ok` rows,
  balanced over district × stratum). The CSV is now a deliberate exception to the `data/`
  gitignore — it is the only copy of work that cannot be redone identically.
- **Result: 153 harvest intervals of 200 fields.** 33 `cant_tell` (24 Bolangir vs 9 Baleswar),
  13 `not_rice`, 1 `never_green`, **0 `not_a_field`**. Intervals are tighter than the protocol
  assumed (median 5 d, max 10, against a predicted 5–15), and midpoints span 8 Nov 2025 –
  9 Feb 2026, a 13-week spread. Good table for the interim report.
- **Learned (important): the binding precision floor is the labeller, not the imagery.** Over the
  20 repeats, `status` agreement is 90% and `|midpoint₁ − midpoint₂|` averages **8.8 d**
  (median 4; 6 pairs exact; one 49-day pair, `bol-0b1bf23444d0`, where the two passes picked
  different brown transitions — 6.1 d without it). So Odisha MAE should be read against ~6–9 d,
  not the 2.3-day interval half-width. Protocol §5 amended with the measured figures.
- **Learned (important): the `rice` tick did not survive contact.** Only 77 of the 153 `ok` rows
  are `rice = yes`; 75 are `unsure`, and repeat agreement on the tick is **55%** (nearly all of it
  `yes` ↔ `unsure` churn; `no` vs not-`no` agrees 80%). Since D-025's amendment made this tick the
  project's only independent read on rice prevalence, that read is now a range — **40–82% of
  stratum-U fields** — and too loose to score the D-021 rice mask against. New open question #13,
  with a cheap fix: re-tick `rice` from the full-season NDVI series (kharif rice floods *before*
  it greens, and the labeller was only ever shown the harvest-window chips). It touches no harvest
  date, so it is not a protocol change.
- **Next:** LightGBM on the SICKLE feature table (the interim headline), then decide #13 before
  the 30 Nov freeze.

## 2026-11-22 (second session) — FREEZE_PLAN point A: S2 per-plot series

- **Done (point A):** `ingest.sickle.s2_series` + `scripts/sickle_s2_extract_check.py` →
  `data/interim/sickle_s2_series.parquet` (17,625 rows, 12,560 after de-duplicating overlapping
  tiles). NDVI/NDWI/MNDWI per plot per scene, cloud-masked from `SCL` + `MSK_CLDPRB`, reusing
  `s1_series`' index-only mask alignment and `edge_clipped` rule; the 20 m bands are upsampled 2×
  onto the 10 m mask grid. Runs in 10 s with no Earth Engine call. Tests in `tests/test_sickle_s2.py`.
  All numbers in `DATA.md` §SICKLE.
- **Learned: decision 1 of the freeze plan holds.** NDVI falls monotonically *through* the forecast
  window (0.569 at 21–30 d before harvest → 0.457 at 7–14 d → 0.384 after), and the per-sample drop
  across harvest is **+0.121 in 75% of samples** against S1's +0.51 dB in 60%. Crucially, the
  optical decline starts before harvest, where S1's drop only happens at it — so S2 is forecast
  signal, not just detection signal.
- **Learned: S2 does not rescue may-sep** (−0.028, dropping in 37% — S1 was −0.49 dB, 42%). The
  monsoon harvest is hidden from both sensors. The per-season split stays mandatory and may-sep
  stays the honest weak point of M1.
- **Learned: cloud costs half the S2 record but blocks nothing.** 51.7% of scenes lose every plot
  pixel and the unclear rate peaks Sep–Jan (77% in Sept) — the north-east monsoon, i.e. exactly
  the window for Jan–Mar harvests. Even so every sample keeps ≥ 10 clear scenes (median 21), and
  only 28 of 305 have no clear scene inside 7–21 days. A 2,123-scene audit confirms the loss is
  real cloud (53.7% SCL cloud classes) and **0.0% no-data**, so the upsampled mask is landing
  correctly. `MSK_CLDPRB` adds 0.3% over SCL, so SCL alone would do.
- **Learned (trap): tile overlap double-counts 121 of 305 samples** — the same acquisition ships
  under two MGRS tiles (5,065 of 17,625 rows). Copies agree to a median 0.0035 NDVI, so
  `sickle.best_per_date` keeps the less-clouded one. Feature code must call it.
- **Next:** point B — NDVI/NDWI/MNDWI features in `features/sickle_m1.py` (last value, deltas,
  slopes, days-since-green-peak, days-since-last-clear-scene) under the same `as_of` truncation
  and leakage assert, then point C's feature-set ablation.

## 2026-11-22 (third session) — FREEZE_PLAN point B: S2 features in the M1 table

- **Done (point B):** `features/sickle_m1.py` takes an optional `s2=` series and adds **15 optical
  columns** — NDVI last/delta/mean/slope at 30 and 60 d, the smoothed green peak in a 45-day
  window (`days_since_ndvi_max_45`, `ndvi_last_minus_max_sm_45`), NDWI last/slope, MNDWI
  last/mean, plus `n_scenes_s2` and `days_since_clear_s2`. Table is now **2,745 rows x 57
  features** (was 42) over the same 305 samples. Leakage test extended to poison `ndvi/ndwi/mndwi`
  after `as_of`; both baselines re-score **byte-identical**, which is the check that the S1 side
  and the row set were not disturbed.
- **Design: S2 adds columns, never rows** (`test_s2_adds_columns_but_never_rows`). If an S1+S2 arm
  dropped rows where cloud left nothing, point C's ablation would compare arms on different test
  sets and the MAE delta would be meaningless. Measured: **0 of 2,745 rows** lack a clear S2 scene
  in their 120-day lookback (median 9, min 2), so nothing is lost by keeping the row set fixed.
- **Learned: the relative optical features carry the signal, the absolute ones carry none.**
  |Spearman| with lead: `ndvi_slope_60` 0.37, `ndvi_last_minus_max_sm_45` 0.32, `ndvi_slope_30`
  0.30 — but `ndvi_max_sm_45` 0.008 and `ndvi_mean_60` 0.013. Absolute greenness varies by plot
  and variety; the *change* tracks phenology. Kept both (LightGBM tolerates dead columns) but this
  is the explanation to give if S2 underperforms.
- **Learned (matters for point C): the strongest feature in the whole table is a clock.**
  `gdd_season` 0.75 and `days_since_season_start` 0.64 dwarf every sensor feature. LightGBM can
  therefore reproduce the 12.0 d seasonal-mean baseline from the calendar alone and show a
  "win" that contains no remote sensing at all. **Point C's ablation ladder should start with a
  calendar-only arm** (calendar + weather, no sensor), so S1's and S2's contributions are measured
  against the clock rather than against nothing. Added to the plan.
- **Learned: cloud shows up as 18% missingness** on `ndvi_slope_30` / `ndwi_slope_30` — a 30-day
  window often holds fewer than 2 clear scenes. Left as NaN (LightGBM splits on missing natively);
  it is also the honest number for how often a 30-day optical trend is unavailable.
- **Next:** point C — LightGBM as a feature-set ablation (calendar-only → S1 → S1+weather →
  S1+S2+weather), nested tuning inside train folds, group bootstrap CIs on the dev split.

## 2026-11-22 (fourth session) — FREEZE_PLAN point C: the LightGBM ablation, and it is a negative result

- **Done (point C):** `models/m1_lightgbm.py` + `scripts/sickle_m1_lightgbm.py` →
  `runs/sickle_m1_lightgbm.csv` (+ `_tuning`, `_importance`). Seven arms, identical rows and
  identical folds, nested CV (inner 3-fold tuning over a 12-point grid inside each outer fold's
  training rows only), L1 objective, 95% CIs bootstrapped over neighbour groups, dev split only.
  Folds now come from `splits.assign_folds`, shared with the baselines script so the two sets of
  numbers are comparable rather than merely similar.

| arm | features | out-of-fold MAE (d) |
|---|---|---|
| base (calendar + plot size + season) | 5 | **7.41 [5.67, 9.26]** |
| base + s1 | 31 | 7.58 [6.33, 8.93] |
| base + s1 + weather | 43 | 7.65 [6.31, 8.98] |
| base + s2 + weather | 32 | 8.23 [6.94, 9.58] |
| all (base + s1 + s2 + weather) | 58 | 7.85 [6.45, 9.21] |
| s1 only (no calendar) | 26 | 10.43 [9.19, 11.85] |
| sensors only (s1 + s2 + weather, no calendar) | 53 | 7.86 [6.56, 9.18] |
| seasonal-mean baseline | — | 11.99 [9.87, 14.29] |
| VH-peak baseline | — | 17.15 [16.12, 18.22] |

- **Learned (the headline, and it is not the one the plan expected): LightGBM beats the baseline
  by 4.6 days and none of that comes from remote sensing.** Paired over the same rows, every arm
  improves on the seasonal mean by +4.58 d [+3.24, +6.32] — but the **calendar-only arm is the
  best of all seven**, and no arm carrying satellite data separates from it (`base+s1` +0.17 d
  [−0.78, +1.21]; `all` +0.44 d [−0.48, +1.40]). **The calendar-only arm is exactly why this is
  reportable:** without it, "S1+S2+weather LightGBM gets 7.85 d against a 12.0 d baseline" would
  have read as evidence that the remote sensing works.
- **Learned (what makes it a result rather than a failure): the sensors are redundant with the
  clock, not empty.** With no calendar features at all, `s1 only` scores 10.43 d — already better
  than the seasonal-mean baseline, so radar genuinely carries harvest information — and
  `sensors only` reaches **7.86 d, statistically indistinguishable from calendar-only 7.41 d**
  (+0.46 d [−0.60, +1.53]). Two disjoint information sources reach the same accuracy
  independently, and their union adds nothing.
- **Why, and the hypothesis it generates for P3.** The Cauvery delta is irrigated and tightly
  scheduled, so the calendar *is* a good harvest model there; the satellite is spending its
  signal re-deriving a date the calendar already knows. Rainfed Odisha should not behave that way
  — monsoon onset moves sowing by weeks, which is the entire premise of the project. **So M2 stops
  being "measure the transfer gap" and becomes "measure which information source survives the
  shift": the prediction is that the calendar arm degrades sharply on Odisha while the sensor arm
  holds.** That is a sharper CS question than the original framing and it is testable with the
  labels already in hand.
- **Learned: the proposal's MAE ≤ 7 d criterion is not a usable success test.** 7.41 d is reached
  with no satellite data at all. An absolute day count cannot distinguish a working forecaster
  from a calendar, so the frozen protocol (point F) should state the criterion as *beating the
  calendar-only arm on the same folds*. This is the Eashwar item-4 conversation with a number
  attached, and it is worth raising with Dr Chandesa before the interim report.
- **Learned (diagnostic, needs following up): acquisition geometry outranks phenology.**
  `angle_last` is the second-largest total gain after `gdd_season`, ahead of every VH or NDVI
  feature, and `px_valid_last` is sixth. Incidence angle encodes the orbit track and therefore
  roughly where the plot is; plot pixel count encodes which plot it is. Both are legal at `as_of`
  (no temporal leakage) and the folds are grouped, so this is not leakage — but a model leaning on
  plot identity over crop state is consistent with the pooled null. **Worth one ablation: drop
  `angle_last` and `px_*` and see whether the sensor arms move.**
- **Consequences recorded:** D-028 amended the same day (its own revisit clause fired — S2 stays
  in the table, but the claim becomes "no measurable pooled gain on SICKLE, retained as the
  transfer hypothesis"). **Point E (L8 thermal) does not run**: its gate was "only if C shows
  optical earns its place". The gate worked and saved the time.
- **Honest limitation:** 33 neighbour groups give CI half-widths of ~1.8 d, so this ablation
  cannot resolve a sub-day effect. "Not separated" means not separated at this sample size, not
  proven equal. Say so wherever the table appears.
- **Also:** `n_jobs=-1` made LightGBM **5x slower** on 2k rows than `n_jobs=1` (5.2 s vs 0.96 s
  per 500-tree fit) — thread contention on tiny data. Pinned to 1; the full 7-arm run is ~12 min.
- **Next:** point D — conformalised quantile regression on the best arm, coverage and width by
  lead and season. Then F, the freeze, where the success criterion needs rewording.

## 2026-11-23 — re-opening point C: why the sensors lost, and a 7.41 → 6.32 d point model

Asked to find a way back on track after point C's negative result, disregarding what the docs
prescribed. Everything below is dev-split only; the locked test groups were never read. Diagnostic
scripts are in the session scratchpad (`diag2`–`diag8`, `select`, `pool2`, `base_abl`, `final`) and
are **not** in the repo — the findings that survive are recorded here, in `DATA.md` §SICKLE, and in
D-030/D-031. Absolute MAEs from the exploratory scripts use fixed hyperparameters; every number
quoted as a result is from `final.py`, which uses the published nested-tuning protocol and
reproduces `runs/sickle_m1_lightgbm.csv` exactly (base-5 7.41, all-57 7.85, seasonal mean 11.99).

### The mechanism behind the pooled null: the labels collapse onto village dates

**Learned: 56% of dev feature rows belong to plots sharing a harvest date with ≥ 2 others**, and a
shared-date cluster spans a mean of **3.4 neighbour groups** — so D-022's grouped folds do not
contain it. Stratify on it and point C's null splits into two significant, opposite results:
calendar-only scores **4.94 d on shared-date plots** where every sensor arm is **worse** (+1.5 to
+1.8 d), and **10.29 d on unique-date plots** where `base+s1` is **better** (−1.26 d
[−1.99, −0.12]). Crossing with distance from the season median shows the sign tracks the label and
not the difficulty (sensors lose on shared dates in both halves, +1.54/+1.45; win on unique dates
in both, −1.52/−1.06, including on the *easier* unique half). Full numbers in DATA.md §SICKLE.
**So the radar does earn its place — on the plots whose labels admit it.** The split conditions on
the label, so it is a label-quality diagnostic, never an operational selector; say so every time.

### What determines harvest date here, and why the satellite cannot have it

**Learned: `VARIETY` and `TRANSPLANTING_DATE` were sitting unused in the tabular CSV, and together
they are worth −3.09 d.** `harvest = transplanting + median duration per (season, variety)` scores
**6.39 d leave-one-group-out**, beating the whole 58-feature model; given both, LightGBM reaches
**4.60 d** [−3.93, −2.48]. Variety nearly determines duration (IR 50 deviates 0.0 d, CR 1009 2.3).
**Learned: that ceiling is unreachable, and the reason is the finding.** Transplanting
day-of-season has sd **10.0 d**; a learned detector scores 6.03 d and *loses to the season median*
(5.94 d). Duration is the input that matters, and the coarse 3-class version classifies at 79.7%
(63.5% majority) — but a perfect coarse class is worth only 0.52 d and at 79.7% the end-to-end gain
is **0.00 d**. Harvest date in the Cauvery delta is set by a planting decision plus genetics; the
delta is irrigated and scheduled, so there is no timing variation for a satellite to see. **This is
the measured source-domain result that M2's rainfed prediction now rests on** (D-031).

### Feature selection: nothing beats the clock, and the search is not at fault

Ran Boruta (shadow features), greedy forward and simulated annealing, every selection nested inside
the outer folds, each subset scored on two inner splits of the *pooled* objective with a 0.05 d
minimum-improvement threshold. **Every method lost to the 5 base columns** (base-5 7.31 fixed-param;
Boruta survivors 7.74; annealing 7.82; greedy **8.18, significantly worse**, +0.87 [+0.39, +1.48]).
**Learned (the strongest form of the null): the *leaky* searches, allowed to select on all dev rows,
reached only 6.73 and 6.77 d pooled against plain base-5 + pooling at 6.27.** When a search that can
see the answers cannot beat five calendar columns, the problem is not the search.

**Learned: 22 of 53 features cannot beat a random permutation of themselves** (≤ 20% of Boruta runs),
and they fall into families: every `days_since_*` column, every `last_minus_max` difference, and most
single-date values (`vh_last`, `vv_last`, `ndwi_last`, `mndwi_last`), plus `px_plot`, `n_scenes_30/60`,
`rain_14d_mm`, `vh_slope_30`, `vh_sd_60`, `ndvi_mean_60`, `ndvi_max_sm_45`. Survival by block:
**weather 10/12, S1 11/26, S2 5/15** — the optical block from point B survives worst, which is a
sharper close-out for D-028 than "no measurable pooled gain".
**Learned (worth a methods paragraph): relevance is not utility.** Boruta *confirmed* 26 features as
carrying genuine signal and feeding exactly those 26 made the model 0.43 d worse than feeding five.
Boruta tests association with the target, not whether a feature improves generalisation once the
clock already explains the target.
Per-feature, added to base one at a time: 16 of 53 improve MAE, **1** has a CI excluding zero
(`days_since_scene`, −0.22 [−0.36, −0.00] — the radar revisit counter, not crop state), and **14 are
significantly worse**, led by the S2 block (`ndvi_mean_30` +0.44 [+0.25, +0.65]).

### What did work: temporal pooling, and dropping `area_acres`

**Learned: the model threw away eight estimates of the same quantity.** Each field gets ~9 weekly
issue dates and `lead` was predicted independently at each. Converting each prediction to an implied
harvest date and taking the running mean over issue dates **at or before `as_of`** improves every
feature set tested (−0.96, −0.92, −0.67 d for calendar-4, base-5, all-57). Plain equal weighting beat
every alternative (expanding mean 6.27 fixed-param, EWM half-life 8 6.37, trimmed 6.41, median 6.57,
shrinkage to the season mean 7.04) — **older estimates are as good as recent ones, which is itself
another confirmation that the signal is the clock and not a ripening crop.** Pooling needs ≥ 3
accumulated estimates to pay (n=1 7.51 → 7.51; n=4 6.94 → 5.75), so the forecaster is weakest in its
first fortnight on a field; an argument for starting rows at transplanting rather than 57 d out.
**Learned: `area_acres` is a noise feature.** All 31 subsets of the base block were scored: the six
best all exclude it, and keeping it costs 0.24 d.

### The point model, under the published protocol

| arm | MAE (d) | unique-date | 7 d | 14 d | 21 d |
|---|---|---|---|---|---|
| **calendar-4 + pooling** | **6.32 [4.97, 7.99]** | 8.42 | 6.16 | 6.16 | 6.08 |
| base-5 + pooling | 6.49 [5.17, 8.16] | 8.61 | 6.37 | 6.36 | 6.22 |
| all-57 + pooling | 7.17 [5.88, 8.66] | 8.47 | 6.62 | 6.69 | 6.82 |
| calendar-4 | 7.29 [5.48, 9.20] | 10.27 | 7.81 | 7.57 | 7.70 |
| base-5 (published best) | 7.41 [5.67, 9.26] | 10.40 | 7.58 | 7.85 | 8.02 |
| all-57 (published) | 7.85 [6.45, 9.21] | 9.36 | 7.67 | 7.51 | 7.73 |
| seasonal mean | 11.99 [9.87, 14.29] | 13.89 | 11.99 | 11.99 | 11.99 |

**7.41 → 6.32 d, and 8.02 → 6.08 d at the 21-day horizon; the proposal's ≤ 7 d is met at all three.**
Features: `days_since_season_start`, `doy_sin`, `doy_cos`, `season` — **no satellite data at all.**
Honest layering of that claim, because it will be asked: the *forecaster's inputs* are empty of Earth
observation (`season` comes from SICKLE's survey column), the satellite gates **126 of 2,871**
candidate rows (4.4%, via 14 plots with no usable S1 series), and the system around M1 is entirely
satellite-dependent — field boundaries, the rice mask, whether the field is still standing (M1's own
precondition), and in Odisha the season assignment too. **The satellite decides which field to ask
about and when the question expires; it does not help answer "how many days left".**

### Honest limitations

Every CI on the pooling and selection results includes zero — the evidence is consistency across
three feature sets, three lead buckets and nine accumulation levels, plus the leaky-search null.
The `area_acres` drop and the choice of pooling rule were made on dev without nesting that choice,
so ~0.2 d of the 6.32 is selection optimism; the robust claims are "pooling helps by ~1 d" and
"`area_acres` hurts across every cut". 33 groups still give ±1.5 d half-widths. Two things I tested
and will not pursue: widening `MAX_LEAD` to 120 (base 7.31 → 9.17, and the sensor advantage inside
the lead buckets vanishes) and dropping `angle_last`/`px_*` from the S1 arm (worse by +0.67 d — the
LOG 22 Nov open ablation, now closed).

### Next

Point C2 (wire the two changes in), then point D on the pooled predictions — see FREEZE_PLAN.

## 2026-11-23 (second session) — FREEZE_PLAN C″ and D: the pooled model in the code, and intervals

Both points landed. Dev split only; the locked test groups were never read.

### C″ — the C′ findings are now code, not notes

* `BASE_COLS` loses `area_acres`, which becomes its own `area` block. The column stays in the
  table (and in the ablation, as the `base-5` arm that reproduces point C's published 7.41 d row)
  and leaves the model, per D-030.
* `models.m1_lightgbm.pool_predictions()` + `tests/test_m1_pooling.py`.
* `scripts/sickle_m1_lightgbm.py` now reports **every arm twice, raw and pooled**, and cuts every
  subset by **shared/unique harvest date** and by **accumulation count** (`n_acc`).
* `features.sickle_m1.shared_harvest_date()` fixes the label-quality stratum in code.

**The leakage trap FREEZE_PLAN warned about was real, and the test caught it.** The first
`pool_predictions` added the prediction vector *in table order* to the `as_of` column *in sorted
order*, so almost every pooled value belonged to a different issue date than the row it was
written to. Nothing in the MAE looked wrong (it moved by tenths); the synthetic test — a field
whose three estimates agree, so pooling must be a no-op — failed immediately. **This is the fifth
leakage check going into the frozen protocol as a CI test** (FREEZE_PLAN F(b)).

**The re-run reproduces D-030 exactly** (`runs/sickle_m1_lightgbm.csv`, 16 arms × 17 subsets):

| arm | all leads | 7 d | 14 d | 21 d | shared-date | unique-date |
|---|---|---|---|---|---|---|
| **calendar-4 + pool** | **6.32 [4.97, 7.99]** | 6.16 | 6.16 | 6.08 | 4.90 | 8.34 |
| base-5 + pool | 6.49 [5.17, 8.16] | 6.37 | 6.36 | 6.22 | 5.12 | 8.42 |
| base+s1 + pool | 6.85 [5.62, 8.48] | 6.31 | 6.42 | 6.59 | 6.43 | 7.44 |
| all + pool | 7.05 [5.75, 8.51] | 6.56 | 6.61 | 6.75 | 6.40 | 7.96 |
| calendar-4 | 7.29 [5.48, 9.20] | 7.81 | 7.57 | 7.70 | 5.34 | 10.04 |
| base-5 (point C's best) | 7.41 [5.67, 9.26] | 7.58 | 7.85 | 8.02 | 5.51 | 10.09 |
| all | 7.76 [6.35, 9.13] | 7.61 | 7.42 | 7.74 | 6.84 | 9.05 |
| seasonal mean | 11.99 [9.87, 14.29] | 11.99 | 11.99 | 11.99 | 11.10 | 13.24 |

Two things to note when quoting this table. The `all` arm is now **56 features, not 57**
(`area_acres` left), which is why it reads 7.76 against the published 7.85 — the same model minus
one measured noise feature. And **pooling is not free early**: it is an identity at `n_acc` 1, a
small loss at 2 (6.69 vs 6.13 raw for calendar-4) and only pays from 3 on (6.20 / 5.89 / 6.09 at
3 / 4 / 5+), exactly as D-030 says.

**The stratified result is now in the published run, and it still has the sign C′ found.** Against
`calendar-4` on the same rows: on **unique-date plots** `base+s1` is **−1.44 d [−2.27, −0.22]** and
the pooled sensor arms −2.1 to −2.6 d, all significant; on **shared-date plots** every sensor arm
is **worse** (+1.21 to +1.75 d, all significant). This is the table FREEZE_PLAN F(a) needs — the
success criterion is only measurable inside a stratum.

**Correction to the 23 Nov figure.** The shared-date share is **58.5% of dev rows / 141 of 241
samples**, not the 56% / 134 quoted this morning. The definition is now fixed in code (`k=3`
distinct plots on the same exact date, computed on the dev feature table); the morning's scratch
script is gone and none of the variants I tried reproduces 134, so the number is restated rather
than defended. Nothing downstream changes: it is still a majority of rows, clusters still span
neighbour groups, and the two strata still carry opposite signs.

### D — conformalised quantile regression, and what the intervals actually cost

`models/m1_conformal.py` + `scripts/sickle_m1_conformal.py` → `runs/sickle_m1_conformal.csv`.
CQR (Romano et al., NeurIPS 2019) on the D-030 point model: LightGBM quantile at 0.05/0.5/0.95,
split conformal on a calibration fold taken from an **inner, group-disjoint split of each outer
fold's training rows**, so no row is calibrated on a model that saw it. Three variants on
identical folds, because the question is which ingredient earns its place:

| variant | coverage (90% target) | mean width |
|---|---|---|
| raw + marginal offset | 91.2% [87, 95] | 39.0 d |
| pooled + marginal offset | 97.2% [94, 100] | 31.6 d |
| **pooled + offset per `n_acc` stratum** | **92.3% [89, 96]** | **24.8 d** |

**(a) The honest width of a 90% interval here is about 25 days, and that is the number the interim
report needs next to 6.32 d.** It is not a calibration artefact: the 90th percentile of the pooled
absolute error is **15.3 d**, the central 90% of signed error spans **[−20.3, +9.9] d**, and an
oracle constant-width interval would need **30.3 d**. So the adaptive interval is already 18%
narrower than the oracle fixed one — the width is the task, not the method. A 6.3 d MAE with a
tail like that means **the decision-grade interval is wider than the sowing window it feeds**,
which is a result about what M1 can and cannot support, and an argument for M3 consuming the
distribution rather than the point.

**(b) Marginal calibration on pooled predictions is badly conditioned, as C′ predicted.** It
over-covers at 97.2% and pays 31.6 d for it, because a row averaging one estimate and a row
averaging nine are not exchangeable. One conformal offset per accumulation stratum gets coverage
back to 92.3% and the interval **21% narrower**. The fitted offsets say the same thing: ~0 d at
`n_acc` 1–2 (the raw quantiles are already about right) and −2.4 to −7.0 d at 3–4 and 5+, i.e.
conformal spends most of its work *tightening*.

**(c) Pooling the bounds does not tighten with evidence — a design flaw worth naming.** `n_acc` 5+
intervals are **wider** (27.3 d) than `n_acc` 3–4 (16.9 d), because the running mean keeps the wide
early-season bounds in the average for ever; averaging bounds gets no √n. The point forecast
improves with accumulation and the interval does not. Future work, not in this freeze: pool the
point estimate only and set the width per `n_acc` stratum from its own conformal scores.

**Failures to report rather than tune away.** Conditioning on `n_acc` buys nothing
lead-conditional or season-conditional: the 7-day bucket covers **86.3% [81, 92]** and may-sep
**84.6%**, oct-mar **84.4%**. With 33 neighbour groups there is not enough calibration data to
condition on lead *and* season *and* accumulation, so the frozen protocol reports all three cuts
and conditions the calibration on one. **And the guarantee is approximate here**: conformal
assumes exchangeable *rows*, but rows cluster ~9 per field and folds are group-disjoint, so the
effective calibration size is fields, not rows. The coverage numbers are measured, not certified —
stated in the module docstring and in `EVALUATION.md`.

Hyperparameters for the quantile fits are **fixed, not tuned** (point C's modal pick): conformal
coverage does not depend on the fit, and tuning on MAE would be the wrong loss for a quantile
model. Width is what tuning could buy, and it is named as future work rather than claimed.

### Next

Point F — the freeze itself: `EVALUATION.md` §Replay protocol as v1, the five leakage checks as
real CI tests, the interval-censored scoring rule written in, and the `protocol-v1` tag.

## 23 Nov 2026 (third session) — CSISA brought into the repo, and it argues with D-031

An external review found the public CSISA rice Landscape Diagnostic Surveys on CIMMYT Dataverse and
computed Odisha crop-calendar statistics in a browser. This session made that reproducible and
checked every figure. Code: `ingest/csisa.py`, `scripts/csisa_ingest.py`,
`features/odisha_calendar.py`, `scripts/csisa_odisha_calendar.py`,
`scripts/csisa_calendar_stats.py`, `tests/test_csisa.py` (11 tests). Decisions: **D-033** (CSISA
returns, revisiting D-005) and **D-034** (the pre-freeze disclosure for D-031).

**D-005's premise was backwards.** It dropped CSISA because "the 2018 survey truncates coordinates
to about 1 km". It is **2017** that is coarse (2 dp); **2018 carries 3 dp ≈ 110 m**, and all **185
Balasore farmers** fall inside the Baleswar registry bbox. The reason this was missed is visible in
the file: the 2018 coordinates sit in **two columns with empty headers**. `coord_columns` finds them
by value range (India's lat and lon ranges do not overlap) and asserts, rather than trusting the
column index the review quoted.

**The review reproduces almost exactly.** All seven transplanted-only transplanting SDs to the
decimal (Odisha 2017 11.80, Odisha 2018 11.14, Balasore 12.68, Bihar 2017 11.26, UP 2017 13.25),
the robust 10.4 d, the 22.9 d all-method Odisha 2017 figure and its 35.7% direct-seeded share, the
three harvest SDs, Balasore duration SD 7.45, the 118 co-located cells with up to 7 farmers, and
Bihar 2017's harvest-MAE pair (11.30 → 9.26 against 11.3 → 9.4). Five differ, all explained in
`reports/csisa_calendar_stats.md` §8: the 2018 row count is **8,355 not 8,393** (8,393 is the line
count; 38 records contain embedded newlines), Balasore has 36 village names not 30 (30 is the
≥ 3-farmer subset), MTU 7029 is n = 124 under our variety normalisation and n = 120 / SD 5.67 d on
the literal string (the review's number exactly), the within-village SD depends on a definition the
review did not state (pooled 9.04 d reproduces its 9.0; mean-of-village-SDs is 5.73 d), and Odisha
2017's harvest MAE is 13.49 → 10.42 d on cleaned rows against its 19.8 → 17.1, which is
reproducible only without the plausibility filter (17.16 → 14.60). **The conclusion survives every
version: transplanting + per-variety duration beats a median-harvest baseline.**

**The finding the review did not have, and it cuts against D-031.** Balasore's 12.68 d transplanting
SD is **one field** — village Kasida, transplanted 10 Feb 2018, harvested 13 May, 92 days, which is
*summer (boro) rice* and not kharif at all. Excluding it by rule (establishment within 0–180 d of
1 June) takes Balasore to **5.70 d** (robust 4.45, within-village 3.77) and Odisha 2018 as a whole
from 11.14 to 9.39 d. Across all seven Odisha districts the pooled spread is **10.4 d against
SICKLE's 10.0 d** — indistinguishable — and **our own study district is roughly half** SICKLE's:

| scope | n | transplanting SD | vs SICKLE |
|---|---|---|---|
| Odisha, all districts, both years | 1,049 | 10.4 d | +0.4 |
| **Baleswar (Balasore 2018)** | 184 | **5.7 d** | **−4.3** |
| Cuttack / Khordha 2017 | 133 / 112 | 12.2 / 11.5 d | +2.2 / +1.5 |
| Jagatsinghpur 2018 | 208 | 8.2 d | −1.8 |

**D-031 is kept exactly as written** and D-034 records that this was seen seven days before the
freeze. The reasons to keep it are in that entry: CSISA measures a farmer's *recalled* transplanting
date over 36 purposively surveyed villages in 2017/2018, D-031's test is a *radar-observed* flooding
date over 133,055 registry fields in 2025–26, and 56% of Balasore's spread is between villages so a
36-village sample can understate a district. Rewriting the prediction now to match CSISA would make
the P3 measurement unfalsifiable after the fact; keeping it means the P3 number decides it either
way. **The freeze's point F(d) has to drop its claim that the prediction was written "before any
Odisha number is drawn."**

**What CSISA supports strongly is the other half of D-031** — that harvest date is set by
transplanting *and variety*. On every group tested, transplanting + per-variety median duration
beats the median-harvest baseline, and in Balasore **MTU 7029 covers 124 of 185 fields with a
duration SD of 5.6 d**. That is what the new `features/odisha_calendar.py` prior encodes, and what
the zero-shot **"Odisha-calendar" arm** (MODELS.md §M2 design note) will test: one harvest date for
the whole district, read off a 2018 farmer survey, as the floor a transferred M1 must beat. For
2025–26 Baleswar it says **12 Dec, 90% interval 30 Nov – 21 Dec (21 d)**. Not scored against the
hand labels — D-031 requires the registry measurement first.

**Two things that cost the protocol something.** The heaping analysis was meant to pin the recall
tolerance τ for the Balasore evaluation set; Odisha 2017 and Bihar 2017 heap at 36–43% against ~23%
by chance, but **Balasore 2018 does not heap at all** (18.4% / 22.2%, at or below chance), so τ is
frozen as a declared sensitivity sweep {0, 3, 5, 7, 10} d with a τ = 7 headline rather than as a
measured constant. And the datasets carry **no licence** (OPEN_QUESTIONS #14, contact not yet made),
so the Balasore set and the calendar prior are both provisional, nothing is redistributed, and only
group-level statistics go in `reports/`.

### Next

Unchanged: point F, the freeze. It now has two more things to carry — the Balasore secondary set's
six scoring rules and D-034's disclosure.

## 25–26 Nov 2026 — Point F: the protocol is frozen (`protocol-v1`), and M2 is ready to start

Everything repo-side for the freeze, plus what M2's first steps need. Code:
`eval/availability.py` (source-lag table + D-019 cut-off), `eval/interval_scoring.py`,
`features/odisha_m1.py` (Odisha rows with interval targets), `ingest/s1.py` (per-field S1 puller),
`m1_conformal.widen`, `scripts/interval_rule_check.py`, `scripts/odisha_transplant_spread.py`,
`tests/test_leakage.py` + `tests/test_m2_scoring.py` (46 tests, all CI-runnable). Decisions:
**D-029** (the #13 three-annotator design, recorded), **D-035** (the freeze), D-031 amended.

**The leakage checks were not running in CI.** Every SICKLE-backed leakage test skips on a fresh
clone because the data is never committed, so CI had been green without testing any of them. The
five checks now run on synthetic inputs, poisoning inputs after *every* issue date rather than only
the last week, and were mutation-tested: a 3-day weather leak, a 6-day S1 leak and an unsorted
pooling each turn the suite red. Weather had no leakage test at all before this.

**Rerunning the published M1 scripts reproduced them byte-for-byte**, and turned up two things.

1. **The stratified O1 comparison was not like-for-like.** The stratum table compared pooled sensor
   arms with the *raw* calendar arm, so pooling's ~1 d was credited to the sensors. Like-for-like
   on unique-date plots, `base+s1+pool` vs `calendar-4+pool` is **−0.90 d [−1.76, +0.14], not
   separated**, while on shared-date plots every pooled sensor arm is still significantly worse.
   The raw-vs-raw −1.44 d stands. So the defensible SICKLE claim is now "sensors help on
   unique-date plots before pooling, and pooling closes most of that gap". D-031's Odisha
   prediction is untouched; its SICKLE half is weaker (amended).
2. **0.4% of D-032's intervals were crossed** (lo > hi): the `n_acc` 3–4 stratum's conformal
   offsets reach −7 d. They now collapse to their centre; headline unchanged (92.3% / 24.8 d).

**Rule 5 measured before freezing it — the draft would have decided O1 by itself.** SICKLE's exact
dates, widened into synthetic intervals from the free Odisha label widths, rescored 200 times:

| calendar-4+pool | exact | intersection (draft) | midpoint | uniform-expected |
|---|---|---|---|---|
| MAE | 6.32 d | 4.74 | 6.58 | 6.73 |
| coverage | 92.3% | 95.3% | 81.8% | 80.8% |

No score is unbiased, but they bracket the truth, and each fails differently: intersection flatters
MAE by 1.6 d and coverage by 3 points, while midpoint is nearly exact on MAE but reads coverage 10
points low. Strict containment (label wholly inside the interval) reads 62.8%. Frozen: midpoint
MAE, intersection coverage minus 3.0 points, both with brackets, and a transfer gap computed against
SICKLE scored the same way. **Good dissertation material:** a ±2.5 d label moves the measured
coverage of a 90% interval by ~10 points, so the proposal's "coverage within 5 points" criterion is
only testable on Odisha with an explicit label-noise correction.

**Two transfer choices pre-registered before any Odisha score.** (a) Zero-shot M1 tells Odisha
kharif it is SICKLE's `sep-feb` (samba analogue), counting days from 1 Sep; the other four mappings
are a reported sensitivity. (b) Odisha S1 features use descending passes: SICKLE is 96% descending
at a median 36° incidence, Baleswar gets descending track 48 at 42.8° *and* ascending track 85 at
37.5° (smoke pull, 3 fields, July 2025 VH −23 to −29 dB — the transplanting flood).

**D-031's measurement rule was tightened before the tag.** A VH minimum alone can land on dry
pre-monsoon bare soil, so a flood must also be followed by a ≥ 3 dB rise within 60 days (D-021's
strict signature). The script implements the frozen rule; it has not been run.

Housekeeping: `FREEZE_PLAN.md` archived to `docs/archive/`; `.DS_Store` untracked; personal PDFs in
`reports/` ignored. The M1 scripts now also write per-row predictions (`runs/*_rows.parquet`).

### Next

P3 step 1: `uv run python scripts/odisha_transplant_spread.py` (2 × 2,000 fields, resumable). Its
verdict on D-031 decides where the dissertation's weight goes. Then the zero-shot arms on the free
40%. SICKLE locked-test unlock around 11 Dec.
