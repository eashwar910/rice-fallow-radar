# Decisions

A record of choices made so far and the reasoning behind them. The point is to make it easy to revisit a decision *knowingly* — every entry can be reopened if the reason no longer holds. Add a new entry rather than editing an old one; mark superseded entries.

Format: date · decision · why · what would change it.

---

### D-001 · Oct 2026 · Frame the project around four ML problems
**Decision:** present the work as forecasting, domain adaptation, diagnostic explainability and PU learning, with agriculture as the application.
**Why:** supervisor's main critique was that earlier drafts read like agronomy and didn't justify a computational solution.
**Revisit if:** — (framing, not method; keep).

### D-002 · Oct 2026 · Three objectives, O1 primary
**Decision:** O1 (forecast + transfer) is the core; O2 (window + ranking) and O3 (system + replay) are extensions.
**Why:** supervisor advised 2–3 strong objectives for a 10-month project; O1 holds most of the research novelty.
**Revisit if:** O1 finishes early and an extension proves more interesting.

### D-003 · Oct 2026 · Study districts: Bolangir and Baleswar
**Decision:** two Odisha districts.
**Why:** Bolangir (western uplands) is limited by lack of irrigation → dry edge; Baleswar (coastal plain) by waterlogging → wet edge. Together they exercise both window edges. Chandna & Mondal (2020) list both among districts holding much of Odisha's permanent rice fallow.
**Revisit if:** FTW polygons or data coverage are unusable in one district.

### D-004 · Oct 2026 · SICKLE as M1's label source
**Decision:** train/test M1 on SICKLE (Tamil Nadu).
**Why:** only public dataset found with field-recorded harvest dates for Indian smallholder rice.
**Revisit if:** another labelled Indian source appears (e.g., IRRI shares Odisha ground truth).

### D-005 · Oct 2026 · Hand-labelled Odisha test set instead of CSISA
**Decision:** 150–200 Odisha fields with harvest week labelled from cloud-free Sentinel-2.
**Why:** CSISA 2018 truncates coordinates to ~1 km, probably too coarse to match fields. Optical labels are also independent of the radar input.
**Revisit if:** the 2017 CSISA file has usable coordinates.

### D-006 · Oct 2026 · LightGBM + temporal CNN for M1, LSTM as comparison
**Why:** ~350 labelled seasons suits trees and a compact CNN; LSTM is the closest prior work's model.
**Revisit if:** a different framing (e.g., survival model) or architecture clearly outperforms.

### D-007 · Oct 2026 · Conformalised quantile regression, recalibrated on Odisha
**Why:** distribution-free intervals; recalibration because covariate shift breaks the coverage guarantee.
**Revisit if:** weighted conformal or another method gives better conditional coverage.

### D-008 · Oct 2026 · TimeMatch-style temporal-shift estimation for M2
**Why:** the shift between regions is expected to be mainly in crop calendar, which this models directly.
**Revisit if:** the ablation shows the shift is mostly spectral/water-regime driven.

### D-009 · Oct 2026 · M3 as rules + FAO-56 water balance, not learned
**Why:** no establishment labels exist to learn from.
**Revisit if:** a usable proxy label source emerges.

### D-010 · Oct 2026 · nnPU for M4, Elkan–Noto as comparison
**Why:** non-negative risk resists overfitting with flexible models.
**Revisit if:** the biased-positives problem dominates — consider propensity-aware PU.

### D-011 · Oct 2026 · Evaluate by replaying 2026–27, not by live field trial
**Why:** development starts after the 2026 harvest begins; a live trial isn't feasible. Replay with a frozen protocol keeps the test honest.
**Revisit if:** — .

### D-012 · Oct 2026 · Alerts generated, not sent
**Why:** RM0–100 budget has no messaging gateway; keeps the project free of human participants (simpler ethics).
**Revisit if:** a partner offers to pilot.

### D-013 · Oct 2026 · AlphaEarth embeddings from previous year only
**Why:** annual embedding for year Y contains that winter's crop → leakage.
**Revisit if:** — (correctness).

---

## New decisions

_Add below as the project moves._

### D-014 · 5 Nov 2026 · Environment: uv + Python 3.12, deps added per phase
**Decision:** `uv` with `uv.lock` for a pinned, reproducible env; Python 3.12; ruff + pre-commit; GitHub Actions runs lint + pytest. Only P0/P1 dependencies installed now; ML libraries are added in the phase that first needs them.
**Why:** one lockfile gives exact reproducibility for the dissertation; 3.12 has wheels for every planned library (3.13/3.14 support for geo/ML stacks is less certain); small env keeps CI fast.
**Revisit if:** a needed library lacks 3.12 wheels on Apple Silicon or Colab forces a different version.

### D-015 · 5 Nov 2026 · Earth Engine Community tier
**Decision:** register the GEE noncommercial project on the Community tier (150 EECU-hours/month, no billing account).
**Why:** matches undergraduate eligibility; per-field table exports should fit; avoids attaching a billing account on an RM0–100 budget.
**Revisit if:** the step-5 pilot extrapolates to >150 EECU-h/month after cutting time span and caching exports → consider Contributor tier.

### D-016 · 10 Nov 2026 · Field unit: FTW polygons ≥ 0.1 ha (provisional), grid cells as fallback
**Decision:** use FTW polygons of at least 0.1 ha (1000 m²) as the field unit for P1, with the valid-pixel count kept as a quality flag. Add a cropland filter in P1 (not yet chosen or tested) because the visual check found false polygons on non-field land.
**Why:** the 12-cell visual check rated dense cells usable and sparse cells poor; fragmentation is severe (median 0.04 ha). The 0.1 ha cut matches SICKLE plot scale and keeps the EE cost at ~10 EECU-h/season, while still covering 60–70% of FTW area. Fixed grid cells are cheaper to trust but break the "per field" claim, so they are the fallback, not the default.
**Revisit if:** P1 shows merged/split polygons blur harvest dates (e.g. within-polygon S1 variance is bimodal), or the cropland filter removes too much of Bolangir. The 12-cell sample is small, so re-rate more cells if the choice looks shaky.

### D-017 · 13 Nov 2026 · EE export route: pull per-field tables with `ee.data.computeFeatures`, in chunks
**Decision:** P1 pulls per-field tables straight back with `ee.data.computeFeatures` (PANDAS_DATAFRAME), chunked and cached to local parquet. No Drive/asset export, no IAM fix.
**Why:** the service account has no Drive quota and cannot see the asset root, so batch export to storage is blocked. A direct pull needs no storage and no extra permissions. Tested 13 Nov on the 5 km Bolangir block (950 fields, S1 VV/VH/angle): 1 scene = 9 s, 5 scenes = 45 s, 20 scenes = 364 s (19,000 rows), no size error. Time grows linearly with scenes, so chunks should stay small (≤ ~5 scenes or a few hundred fields per call) to keep each call short.
**Cost to know about:** 540 k fields ≈ 570 blocks of this size; serial wall-clock for one S1 season is roughly 50+ hours, so the pull loop needs parallel requests and resumable caching. The CHIRPS/ERA5 rule in DATA.md (sample once per coarse pixel, join locally) still applies.
**Revisit if:** parallel pulls hit EE request-rate limits or one season takes more than ~a day of wall-clock, then fix IAM (EE writer role on the SA) and use batch export instead.

### D-018 · 17 Nov 2026 · Odisha hand labels: past seasons only, ~200 fields, by Eashwar
**Decision:** Eashwar labels the harvest dates (Option A): ~200 fields ≥ 0.1 ha from **2025–26** (plus some 2024–25), sampled at random within strata (district × field size × spatial spread), plus ~40 re-labelled about a week later for self-agreement. Budget 5–6 h. Each label is an interval (last clear green image → first clear brown image) from Sentinel-2 L2A, via a small labelling tool (per-field NDVI curve + image chips). ~50 fields go to M2 fine-tuning/recalibration; ~100+ are locked away until final evaluation. No 2026–27 labels for now.
**Why:** a quick check in Copernicus Browser (17 Nov) showed that a non-expert can see the green → brown change. Visual labelling of imagery is the standard way remote-sensing studies make reference data (Olofsson et al., 2014). Semester 2 time goes to development, so a second labelling session in January isn't planned.
**Cost to know about:** the 2026–27 replay has no Odisha hand labels, so replay harvest accuracy can only be checked against the radar harvest detector (itself validated on these past-season labels). That's weaker, and the dissertation should say so. Label precision is ~±5 days (S2 revisit plus cloud), which sets a floor on the Odisha errors we can claim.
**Revisit (Jan 2027):** if time allows, add ~50 2026–27 fields for the replay (Option C).

### D-019 · 17 Nov 2026 · No 2026–27 data before the protocol freeze, enforced in code
**Decision:** until `protocol-v1` is tagged, the pipeline refuses any date on or after **1 Jun 2026** (start of the 2026–27 kharif season). The cut-off lives in config and is checked in `build_features` and the ingest pulls; it can only be lifted by an explicit replay mode after the freeze. All P1/P2 development uses 2024–25 and 2025–26.
**Why:** the 2026–27 replay is only a fair test if nothing was tuned on that season. A hard guard is easier to defend than "I promise I didn't look", and it means the freeze date (30 Nov) can slip without contaminating the replay.
**Cost to know about:** bugs that only appear on newer data (e.g. new Sentinel-1 satellites, a new product version) will surface at replay time, not earlier. With no 2026–27 hand labels (D-018), the protocol must state that replay harvest "truth" comes from the radar harvest detector, validated on past-season labels.
**Revisit if:** a pipeline bug needs 2026–27 data to reproduce; then document the exception in LOG.md and touch only raw inputs, never model outputs.

### D-020 · 17 Nov 2026 · No land-cover filter on FTW; keep WorldCover cropland fraction as a flag
**Decision:** don't drop FTW polygons with a land-cover map. Keep the ≥ 0.1 ha cut (D-016), store each polygon's ESA WorldCover 2021 cropland fraction as a quality column (like the valid-pixel count), and let the rice mask (open question #8) remove the remaining non-fields.
**Why:** blind per-polygon ratings of 205 polygons ≥ 0.1 ha (DATA.md §FTW) found only 5 false polygons (~2–3%). Every filter tested threw away more real fields than fakes it caught: WorldCover < 0.5 drops 14/194 real fields to catch 4/5 fakes; Dynamic World is worse (23–29 real fields lost at thresholds that catch 4 fakes). Roads and trees won't show a rice radar signature, so the rice mask should catch what's left.
**Revisit if:** the rice mask lets non-fields through (check on the P1b labels), or a larger rating sample shows more fakes than 2–3%.

### D-021 · 17 Nov 2026 · Rice mask: hybrid rule → pseudo-labels → classifier, early-season only
**Decision:** build the kharif rice mask in four steps, using only Sentinel-1 data up to the first forecast issue date (~end of September) so the mask can't leak harvest information:
1. A **strict S1 rule** labels high-confidence rice (transplanting-flood dip in VH, then a sustained rise) and high-confidence non-rice (no rise). Uncertain fields stay unlabelled.
2. **Cluster** the early-season VH curves to find a "no dip but rice-like rise" group (likely direct-seeded/beushened rice). Name clusters by inspecting examples and Eashwar's rice ticks; add the rice-like cluster to the positives.
3. Train **LightGBM** on early-season S1 features from those pseudo-labels; predict every FTW polygon ≥ 0.1 ha.
4. **Validate** on (a) Eashwar's "rice? yes/no/unsure" tick added to the P1b labelling, (b) Open-SARice-10 for 2021, (c) official district kharif rice area, and (d) AgriFieldNet if it has usable fields nearby. IRRI ground truth is an optional extra if they reply.
**Why:** ~53% of Odisha rice is direct-seeded (IRRI, 2016–17), so a flood-dip rule alone would probably under-map rice, worst in Bolangir; a national S1 rice map scores only 71% in Odisha. The rule → pseudo-label → classifier pattern follows FARM (Computers and Electronics in Agriculture, 2023), which needs no manual samples. No open Odisha kharif labels exist (DATA.md §Rice mask).
**Cost to know about:** ~2–3 days more than a rule alone. Rule-picked pseudo-labels are not a random sample of rice (easy, flooded fields), so the classifier can inherit that bias; the cluster step and the independent checks are there to catch it. Same selection-bias issue as M4's PU positives: worth linking in the dissertation.
**Revisit if:** the rule alone already agrees with all checks (then drop the classifier for simplicity), or the checks show the mask misses a large share of rice.

### D-022 · 17 Nov 2026 · SICKLE split: neighbour-group CV with a locked test set
**Decision:** split SICKLE's 319 exact harvest dates by **neighbour group** (plots sharing any 320 m mask patch, chained; 43 groups, `scripts/sickle_neighbour_groups.py`). Lock ~20% of groups (~9 groups, ~60 dates, season-balanced, fixed seed) as the **final test set**, untouched until final evaluation. On the remaining 80%, run **5-fold `StratifiedGroupKFold`** (groups = neighbour group, stratified by season). Report results per season as well as pooled, with bootstrap CIs. Secondary check: train 2019 → test 2020 within the held-out groups. Planned extra experiment: score the same model on SICKLE's official split vs this split, to measure how much leakage inflates results.
**Why:** the official split has neighbours on both sides (137/319 dates) and its test split is empty. Grouping by plot alone still leaks between neighbours. The neighbour graph has no giant component (largest group = 9% of dates), so grouping costs little. may-sep harvests vary far less than sep-feb, so unbalanced folds would distort the pooled error.
**Cost to know about:** the groups only capture neighbours within ~320 m. Plots further apart can still be correlated (village, weather), so this is a minimum spatial block; say so in the dissertation. A ~60-date test set gives wide confidence intervals.
**Revisit if:** coordinates become available (then use true spatial blocks), or fold sizes turn out too uneven to compare.

### D-023 · 19 Nov 2026 · SICKLE weather is one regional series, not per plot
**Decision:** close open question #11 with option (a). SICKLE plots get **one weather series per season for the whole SICKLE study area** (Cauvery delta, Tamil Nadu — confirm the exact districts from Sani et al. (2024) before building), sampled from CHIRPS and ERA5-Land over that extent and joined to every plot of that season. Do **not** attempt to recover plot locations from the Sentinel-1 scene IDs in the patch filenames (option b). Odisha fields keep genuinely per-field weather, so `build_features` must mark which rows have regional vs per-field weather (a column, not a silent difference).
**Why:** SICKLE withholds plot coordinates and the mask GeoTIFFs have their georeferencing stripped (DATA.md §SICKLE), so per-plot sampling is impossible without reverse-engineering locations. CHIRPS is ~5 km and ERA5-Land ~9 km, and the SICKLE plots sit in one irrigated delta, so per-plot values would differ little from a regional mean — the information lost is small. Option (b) is fiddly and works against the authors' stated privacy intent.
**Cost to know about:** within-season, between-plot weather variation is invisible to M1 on the training side, so weather features will look weaker in training than they are in Odisha, and part of the measured transfer gap (M2) will be a *feature-quality* shift rather than a climate shift. That confound must be stated, and the per-field-vs-regional flag makes it testable (e.g. retrain with Odisha weather coarsened to regional).
**Revisit if:** the authors release coordinates (then sample per plot and re-run the weather ablation).

### D-024 · 19 Nov 2026 · The 588 "rough" SICKLE dates stay out of M1
**Decision:** close open question #12. M1 trains and is evaluated on the **319 exact harvest dates only**. The 588 recalled "typical" dates are excluded from training, validation and test. Optionally revisit them later as **down-weighted weak labels in a single ablation**, reported separately and never mixed into the headline numbers.
**Why:** they are a farmer's typical-year date, not an observation of that season, so they carry no year-specific signal — the thing M1 is being asked to predict. They also come from a disjoint set of plots from the exact labels (DATA.md §SICKLE), so including them changes the population as well as the label quality. Keeping them out means every reported M1 number has the same label definition behind it.
**Cost to know about:** M1 trains on ~319 dates instead of ~900, which is small for a deep model and is part of why LightGBM leads (ROADMAP P2). If the temporal CNN underfits, the weak-label ablation is the first thing to try.
**Revisit if:** M1 is clearly label-starved (deep models far behind LightGBM), or a weak-label ablation shows a real gain on the locked test set.

### D-025 · 19 Nov 2026 · Odisha hand labels: two sampling strata, not one uniform sample
**Decision:** split the ~200 P1b fields (D-018) into two strata of ~100, both drawn with a fixed seed from the same 498-field candidate pool (stratified by district × area tercile × 5 km block, one field per block per cell). **Stratum U** is uniform within those cells. **Stratum K** is restricted to fields whose Sentinel-2 NDVI shows a monsoon crop (peak > 0.45 in Sep–Oct, falling by > 0.2 by Jan–Feb). Every Odisha result is reported per stratum, headline on U. Protocol: `docs/LABELLING_PROTOCOL.md`.
**Why:** a uniform sample of the registry spends the labelling budget on fields that are not kharif rice. Open-SARice maps only 19–23% of real Bolangir outlines as rice (vs 65–71% in Baleswar), so ~200 uniform fields would have yielded very few Bolangir harvest dates — the district the dry edge of the window depends on. Keeping stratum U intact preserves every unbiased claim (rice prevalence, FTW false-positive rate, cloud-driven exclusion); stratum K buys statistical power for the harvest-date comparisons.
**Cost to know about:** stratum K is selected on *visible phenology*, so errors measured on it are optimistic and it cannot be used to estimate how often the pipeline meets a field it cannot read. The selection uses Sentinel-2 while M1/M2 and the harvest detector use Sentinel-1, so it does not leak the models' own inputs — but that argument must be made explicitly in the dissertation, not assumed. Weighted estimates need the per-stratum inclusion probabilities, which are recorded in `selected.parquet`.
**Revisit if:** the rice mask (D-021) lands before labelling finishes, in which case stratum K could be redrawn from the mask's positives and compared against the S2 criterion as a validation of both.

**Amended the same day, after drawing the sample.** The premise was wrong. The kharif-signature
criterion turned out to be **non-selective: 88% of Bolangir and 94% of Baleswar pool fields pass
it**, and 91% of the fields drawn into stratum U meet it too. The two strata are
indistinguishable on every covariate (median green peak 0.75 vs 0.74, NDVI fall 0.48 vs 0.44,
WorldCover cropland 1.0 both), so **stratum K is in practice a second uniform draw**. The 200
fields stand as drawn (no re-pull), but they should be treated as one near-uniform sample: pool
them for the headline, report per stratum only as a check, and keep `green_peak` /
`ndvi_fall` / `kharif_signature` as recorded covariates rather than as a sampling filter.

Why the premise failed, and why it matters: Open-SARice's "19–23% of Bolangir outlines mapped as
rice" is about *rice specifically*. Most Bolangir fields evidently grow **something** in the
monsoon — an NDVI rise and fall does not distinguish rice from any other kharif crop. So the
scarcity the stratification was meant to fix is not scarcity of monsoon crops but scarcity of
*rice*, which no cheap optical rule resolves. **That raises the value of the labeller's
rice yes/no/unsure tick**, which becomes the only independent read on rice prevalence in the
frame, and is the thing D-021's mask will be validated against. A separate finding from the same
pull: **0 of 498 pool fields had fewer than 4 clear Sentinel-2 images** (median 37–39), so
cloud-driven exclusion is not the risk the protocol assumed.

### D-026 · 19 Nov 2026 · Field registry keeps one FTW vintage (2025), not both
**Decision:** `data/processed/fields.parquet` keeps only polygons with `determination:datetime` in **2025**. 292,060 fields (Bolangir 159,005 / Baleswar 133,055), 71,292 ha.
**Why:** the FTW `results-by-admin-conf` parquet for Odisha **stacks two annual prediction layers** (2024 and 2025) in one file. This was found on 19 Nov by measuring polygon overlap: 41–53% of polygons ≥ 0.1 ha overlap another, median overlap is 67–72% of their own area, and a vintage crosstab shows **zero within-vintage overlaps — every overlap is 2024 against 2025**. Two stacked layers are not a field map: they double-count area, break any per-field join, and make `id` non-unique. The 2025 layer is the more complete of the two (Baleswar 50,205 ha vs 35,227 ha raw; Bolangir 60,171 vs 57,710) and both cover the same 5 km blocks, so 2025 is the one to keep. Its imagery predates the D-019 cut-off, so no replay contamination.
**Cost to know about / correction to earlier findings:** the P0 visual FTW check (10 Nov, 12 cells) and the cropland filter check (17 Nov, 205 polygons) were both run on the **stacked** set, so Eashwar was rating two vintages drawn on top of each other. That plausibly inflates the "over-split" (9/12 cells) and "merged" (9/12) flags and explains the ~15 unclickable overlapped polygons. **The FTW quality verdict in D-016 should be treated as a lower bound on quality until re-rated on the single vintage.**
**Revisit:** re-run `scripts/ftw_sample_map.py` and `scripts/cropland_filter_check.py` on the 2025 vintage before the dissertation quotes a fragmentation figure. If 2024 turns out to be the better-aligned layer for a particular season, the constant is `registry.fields.VINTAGE`.

### D-027 · 19 Nov 2026 · SICKLE regional weather is per MGRS tile, not one series for the whole area
**Decision:** refine D-023 option (a). Instead of one weather series for the entire SICKLE study area, pull one CHIRPS/ERA5-Land series **per Sentinel-2 MGRS tile** and attach to each plot the mean over the tiles its own patch came from. The exact-label samples fall in four tiles — T44PKS, T44PKT, T44PLS, T44PLT — spanning 78.61–80.18 °E, 9.85–11.76 °N (the Cauvery basin in Tamil Nadu). `scripts/sickle_weather_pull.py`; the feature table keeps the `weather_regional` and `weather_tiles` columns.
**Why:** D-023 asked for the study extent to be confirmed from Sani et al. (2024) before building. It can instead be *measured*: the S2 patch filenames carry the MGRS tile, which is shipped with the dataset. That is better evidence than a district list read from a paper, and it costs nothing. A 110 km tile localises nothing about an individual plot, so this stays on the right side of D-023's rejection of option (b) (recovering *plot* locations from scene IDs) and of the authors' privacy intent.
**Cost to know about:** the confound D-023 flagged is reduced but not removed — plots within one 110 km tile still share a weather series, so between-plot weather variation is still invisible to M1 on the Tamil Nadu side, and part of any M2 transfer gap remains a feature-quality shift. Six distinct tile sets occur across the 319 samples, so the weather features do now vary between plots in the same season, which makes the planned "coarsen Odisha weather to regional" ablation a sharper test.
**Revisit if:** the authors release coordinates, or if the tile assignment turns out to correlate with something else that matters (e.g. delta vs upstream), in which case it is a confound to report rather than a feature.

### D-028 · 22 Nov 2026 · Sentinel-2 indices go into M1's feature set, not an optional extra
**Decision:** cloud-masked S2 indices (NDVI, NDWI, MNDWI) are part of M1's inputs. `ingest.sickle.s2_series` builds the per-plot series locally from the shipped patches, `features/sickle_m1.py` turns it into 15 columns, and point C of `FREEZE_PLAN.md` reports S1-only against S1+S2 as a feature-set ablation rather than shipping one model. MNDWI gets two columns rather than the full battery because it measured flat across harvest; it is kept as a waterlogging input for M3.
**Why:** the S1 harvest signature on SICKLE is weak and season-dependent — median **+0.51 dB, present in only 60% of samples, and *inverted* in may-sep** (19 Nov, DATA.md). No architecture recovers a signal the data does not contain, so the honest fix is a sensor that does carry it. Measured on the same plots and the same pre/post windows (22 Nov), NDVI drops a median **+0.121 in 75% of samples**, and — the part that matters for forecasting rather than detection — the decline starts *inside* the forecast window: pooled mean NDVI runs 0.569 at 21–30 d before harvest → 0.464 (14–21 d) → 0.457 (7–14 d) → 0.406 at harvest, where S1's drop only happens at harvest itself. The cloud objection was checked before deciding and does not bind: half the S2 scenes are lost entirely (worst Sep–Jan, the NE monsoon), but **every sample keeps ≥ 10 clear scenes** (median 21) and 0 of the 2,745 feature rows lack a clear scene in its 120-day lookback.
**Cost to know about:** three things. (a) **Feature count rises 42 → 57 against an unchanged effective n of 43 neighbour groups**, so overfitting risk rises and point C's nested tuning inside train folds is not optional. (b) **S2 does not fix may-sep** (−0.028, dropping in only 37%, against S1's −0.49 dB / 42%) — the monsoon harvest is hidden from both sensors, so the per-season split stays mandatory and may-sep stays M1's weak point. (c) The Odisha side must now build the same optical features from Earth Engine rather than from local patches, which is P3 work and adds a sensor to the M2 transfer surface: a cloud-regime shift between Tamil Nadu and Odisha is a new candidate explanation for transfer failure, and an explainability target for objective 3.
**Revisit if:** point C shows the S1+S2 arm does not beat S1+weather outside its bootstrap CI, in which case S2 is reported as a negative result (with the attribution evidence for why) and M1 ships on radar plus weather.
**Amended 22 Nov 2026, same day, by the point-C ablation — the revisit clause fired.** S1+S2+weather scores **8.23 d against S1+weather's 7.65 d** out of fold (overlapping CIs), so S2 does **not** earn its place on pooled MAE, and nor does S1: the calendar-only arm is the best of all seven at **7.41 d** and nothing separates from it. **S2 nevertheless stays in the feature table**, for two reasons that the pooled number hides. (a) With no calendar features at all, `s1+weather+s2` reaches **7.86 d** while `s1` alone reaches only 10.43 d — so weather and optical do contribute *on top of radar*; what they are redundant with is the clock, not each other. (b) The whole M2 hypothesis now rests on the sensor arm existing on the Odisha side (see LOG 22 Nov): the Cauvery calendar is informative because the delta is irrigated and tightly scheduled, and a rainfed district's should not be. Removing S2 now would delete the arm that is supposed to survive the transfer. **What changes is the claim, not the code:** S2 is reported as "no measurable pooled gain on SICKLE, retained as the transfer hypothesis", and point E (L8 thermal) does not run.
