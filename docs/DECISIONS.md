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
**Revisited 23 Nov 2026 by D-033 — and the premise was backwards.** It is the **2017** file that is coarse (2 dp, ~1 km); the **2018** file carries **3 dp, ~110 m** and 185 farmers in Balasore = Baleswar. The hand labels stay M2's primary test; CSISA comes back as a secondary set and a calendar prior.

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
**Amended again 23 Nov 2026 — the claim gets weaker and more specific.** S2 is not merely redundant on SICKLE, it is **measurably harmful**: added to the calendar arm one column at a time, 7 of the 15 optical features make MAE *significantly* worse (`ndvi_mean_30` +0.44 d [+0.25, +0.65], `ndwi_last` +0.49, `ndvi_last` +0.45), and only **5 of 15 survive a Boruta shadow test** against 10 of 12 weather and 11 of 26 radar columns — the optical block is the worst-surviving block in the table. The retained-for-transfer argument (b) above still holds and is now sharpened by D-031: on the **unique-date stratum** the sensor-carrying arms do beat the calendar (8.26–8.47 d against 8.61), so the signal is real and is being outvoted by shared-date plots in the pooled metric. **S2 therefore stays in the extraction pipeline and in the published ablation, and leaves M1's point model** (D-030). Point E (L8 thermal) remains cancelled.

### D-029 · 22 Nov 2026 (recorded 26 Nov) · The `rice` tick is re-made by three annotators in P3, and Bolangir's sample grows
**Decision:** answer OPEN_QUESTIONS #13 with a three-annotator design, run in P3, not before the freeze. (1) Eashwar re-ticks `rice` on all 200 labelled fields **blind**, from full-season S2 evidence (NDVI plus a water index, so the flood-then-green signature the harvest-window chips never showed is visible), with ~40 repeats for self-agreement. (2) An automated S2 rule is the second annotator and Open-SARice-10 the third; pairwise Cohen's κ is reported. (3) ~200 more Bolangir fields are sampled under the same strata (D-025). **Invariant:** a re-tick may move `rice` and never `status` — status decides which fields carry harvest labels, 60% of which are eval-locked, so moving it would change a frozen test set.
**Why:** 75 of 153 harvest-labelled fields are `rice = unsure` and repeat agreement on the tick is 55% (DATA.md §Odisha hand labels), so kharif-rice prevalence is a 40–82% range, too loose to validate D-021's mask or to fix M4's eligible set. A single labeller re-ticking would still be a single labeller; agreement with two independent annotators is what makes the prevalence publishable. 100 Bolangir fields with 71 uncommitted ticks cannot separate "23% rice" from "60% rice", and that number underwrites the dry-edge story.
**Cost to know about:** ~3–4 h of labelling plus an S2 pull for 200 extra fields. 2 of the 20 repeats already flipped `not_rice` ↔ `ok`, which is exactly why the status invariant is written down rather than assumed.
**Revisit if:** the S2 rule and Open-SARice agree with each other at κ > 0.8 and with the confident `yes`/`no` ticks, in which case the human re-tick can shrink to the `unsure` fields only.

### D-030 · 23 Nov 2026 · M1's point model is four calendar features plus temporal pooling, not the 57-feature table
**Decision:** M1's SICKLE point model is `days_since_season_start`, `doy_sin`, `doy_cos`, `season` — **four features, no satellite data** — with a **temporal pooling** step: each weekly prediction is converted to an implied harvest date and the forecast at `as_of` is the running mean of the implied dates from all issue dates **at or before `as_of`**. Out of fold under the published nested-tuning protocol this scores **6.32 d [4.97, 7.99]** against the previous best 7.41 d, and 6.16 / 6.16 / 6.08 d at the 7/14/21-day horizons against 7.58 / 7.85 / 8.02. `area_acres` is dropped. **The 57-column table stays in the extraction pipeline and in the published ablation; it just stops being the model's input.**
**Why:** three measured things (LOG 23 Nov). (a) **No feature subset beats the clock, and the search is not at fault** — Boruta, greedy forward and simulated annealing, every selection nested inside the outer folds and scored on the pooled objective, all lost to the base columns (greedy significantly: +0.87 d [+0.39, +1.48]); the *leaky* searches, allowed to select on all dev rows, reached only 6.73–6.77 d against plain base + pooling at 6.27. (b) **22 of 53 features cannot beat a random permutation of themselves** (Boruta ≤ 20% of runs), and 14 of them are *significantly worse* than base when added alone, led by the S2 block (`ndvi_mean_30` +0.44 d [+0.25, +0.65]). (c) **Pooling is where the gain is**: it improves every feature set (−0.96, −0.92, −0.67 d for 4, 5 and 57 features) because the old design predicted `lead` independently at ~9 issue dates per field and discarded eight estimates of the same quantity. Plain equal weighting beats every recency weighting, which is itself evidence that the signal is the clock rather than a ripening crop.
**Cost to know about:** four things. (a) **The model contains no Earth observation**, so "M1 beats the ≤ 7 d criterion" must always be stated with what the satellite *does* do — gate 4.4% of rows, and supply the field boundaries, the rice mask and the still-standing precondition the forecaster assumes. (b) Pooling needs **≥ 3 accumulated estimates** to pay off (neutral at 1–2), so the forecaster is weakest in its first fortnight on a field; this argues for building rows from transplanting rather than 57 days out. (c) It assumes **harvest is a single per-field event** — it would break on a field harvested in stages. (d) The `area_acres` drop and the choice of pooling rule were made on dev **without nesting that choice**, so roughly 0.2 d of the 6.32 is selection optimism; the robust claims are "pooling helps by ~1 d" and "`area_acres` hurts across every cut".
**Revisit if:** Odisha's sensor arm separates from its calendar arm (D-031), in which case the point model gains sensor features for that domain and this decision becomes SICKLE-specific; or a field is found to be harvested in stages, which breaks the pooling assumption.

### D-031 · 23 Nov 2026 · Point C's null is a property of the Cauvery delta, and M2 pre-registers the contrast
**Decision:** record point C's null as **"harvest date in the Cauvery delta is determined by variety and transplanting date, neither of which is observable from orbit, and neither of which varies much there"** — not as "remote sensing does not forecast harvest". The frozen protocol carries the pre-registered prediction that **Odisha's transplanting-date spread is materially larger than SICKLE's 10.0 d**, and that the sensor arm therefore separates from the calendar arm in Odisha while it does not here. The deciding measurement — the spread of flooding/transplanting dates across the Odisha field registry — is written into P3 and must be made *before* any Odisha harvest-date model is tuned.
**Why:** measured, not inferred (LOG 23 Nov, DATA.md §SICKLE). `harvest = transplanting + median duration per (season, variety)` scores **6.39 d leave-one-group-out**, beating the entire 58-feature model, and giving LightGBM both inputs reaches **4.60 d** [−3.09 d, CI −3.93 to −2.48]; variety nearly determines duration (IR 50 deviates 0.0 d, CR 1009 2.3 d). Those inputs are unreachable from satellite *here* because the delta is irrigated and centrally scheduled: transplanting day-of-season has sd **10.0 d**, and a learned detector on the S1+S2 curves (6.03 d) **loses to predicting the season median** (5.94 d). Duration is the binding unknown and its coarse 3-class form classifies at 79.7% against a 63.5% majority — but a perfect coarse class is worth only 0.52 d, so the realised end-to-end gain is 0.00 d. Bolangir and Baleswar are rainfed, monsoon onset moves transplanting by weeks, and that variation is the project's entire premise; so the component that is useless on SICKLE is the one that should carry Odisha.
**Cost to know about:** this makes an explicit, falsifiable prediction that can fail. If Odisha's transplanting spread is also ~10 d, the sensor arm will not separate there either, and the dissertation's emphasis must move to M3/M4 — which do not depend on this. That is a cheaper failure than discovering it after building a detector, which is why the measurement is pre-registered rather than assumed. The transplanting-detector route also has 907 SICKLE labels available rather than 319 (all 588 rough rows carry `TRANSPLANTING_DATE` and have S1 patches and masks on disk), but **0 of them carry `VARIETY`**, so they cannot train the duration component.
**Revisit if:** the Odisha transplanting-spread measurement comes back under ~15 d, which would falsify the prediction and should be reported as such rather than worked around.
**Amended 26 Nov 2026 (D-035): the SICKLE half of the evidence is weaker than stated above.** The "sensors significantly better on unique-date plots" figure (−1.44 d [−2.27, −0.22]) is raw-vs-raw. Like-for-like after pooling it is **−0.90 d [−1.76, +0.14], not separated**; the published table had compared pooled sensor arms with the *raw* calendar arm. The mechanism (variety + transplanting set the date; the delta is scheduled) is untouched, and so is the Odisha prediction — but the dissertation must not claim a significant pooled sensor gain on SICKLE.

### D-032 · 23 Nov 2026 · M1's intervals are conformalised quantile regression, calibrated per accumulation stratum
**Decision:** M1 publishes a **90% interval** from **CQR** (Romano, Patterson & Candès, NeurIPS 2019) — LightGBM quantile fits at 0.05/0.5/0.95 on D-030's point model, widened by a split-conformal offset — with the offset estimated **separately for each accumulation stratum** (`n_acc` 1–2, 3–4, 5+; Mondrian conformal, Vovk 2012) on a calibration fold drawn from an **inner, group-disjoint split of each outer fold's training rows**. Measured on dev: **92.3% coverage [89, 96] at 24.8 d mean width**, against 97.2% / 31.6 d for the same model with one marginal offset. Conditional coverage is **reported** by lead bucket, season, shared/unique harvest date and `n_acc`, and the calibration is **conditioned** on `n_acc` only.
**Why:** D-030's forecast is a running mean over a field's issue dates, so a row averaging one estimate and a row averaging nine have different error distributions and are not exchangeable — the assumption split conformal rests on. Stratifying the offset is the cheapest fix that keeps the finite-sample argument intact, and it buys a **21% narrower** interval at better-centred coverage (LOG 23 Nov, second session). CQR rather than a residual-based interval because the error is skewed (central 90% of signed error spans [−20.3, +9.9] d), so a symmetric ± band is the wrong shape; CQR is also already 18% narrower than an oracle constant-width interval (24.8 vs 30.3 d).
**Cost to know about:** four things. (a) **The guarantee is approximate**: conformal assumes exchangeable rows, but rows cluster ~9 per field, so the effective calibration size is fields (~60), not rows. Quote coverage as measured, never as certified. (b) **Lead- and season-conditional coverage are below nominal** — 86.3% [81, 92] in the 7-day bucket, 84.6% may-sep, 84.4% oct-mar — and 33 neighbour groups cannot support conditioning on everything at once. (c) **The interval does not tighten as evidence accumulates**: pooling averages the *bounds*, so `n_acc` 5+ intervals (27.3 d) are wider than `n_acc` 3–4 (16.9 d). (d) Quantile hyperparameters are fixed, not tuned — coverage does not depend on them, but width probably does.
**Revisit if:** the `n_acc` width inversion in (c) matters operationally, in which case pool only the point estimate and set the width per stratum from its own scores; or Odisha coverage misses nominal by more than the 5 points O1 allows, which is a recalibration question, not a method question.

### D-033 · 23 Nov 2026 · CSISA returns as an Odisha calendar prior and a secondary evaluation set (revisits D-005)
**Decision:** ingest both public CSISA rice Landscape Diagnostic Surveys (`scripts/csisa_ingest.py`, `ingest/csisa.py`) and give them two jobs, neither of which displaces the hand labels:
1. **An Odisha crop-calendar prior** (`features/odisha_calendar.py`, `data/processed/csisa_odisha_calendar.parquet`) — the transplanting-date and duration distributions of transplanted kharif fields, per district. It becomes a **zero-shot "Odisha-calendar" arm** in M2's ablation, the target-domain analogue of the calendar-only arm that beat every sensor arm on SICKLE (D-030).
2. **A secondary, independent evaluation set**: the **185 Balasore 2018 farmers**, scored at 3-dp cell level and interval-valued (EVALUATION.md §Secondary evaluation set). **Provisional pending licence confirmation.**

**Why D-005 can be reopened:** its stated revisit condition was "the 2017 CSISA file has usable coordinates", and the answer is no — 2017 is 2 dp (~1 km). But the premise behind the condition was wrong in the other direction: **2018, the file D-005 called coarse, is the precise one** (3 dp, ~110 m), and all 185 of its Balasore points fall inside the Baleswar registry bbox. Verified in this repo on 23 Nov 2026, not read off a paper: the coordinates live in **two columns with empty headers**, which is presumably why they were missed. Two further reasons this is worth the time now: D-030 made M1 a *calendar* model, so a second independent calendar for the target region is directly on the critical path; and the hand labels are a single labeller's reading of optical imagery, so an independent farmer-reported set is the only external check on them we can get for free.

**Cost to know about:** four things.
(a) **No licence.** Both datasets say "made available without information on how it can be used… communicate with the Contact(s) before use". Raw files and row-level derivatives stay in `data/`; only group-level statistics go in `reports/`. Everything built on CSISA is **provisional until the contact replies**, and per the standing rule no step waits on that reply.
(b) **A point is not a plot.** Up to 7 farmers share one 3-dp cell (185 farmers → 118 cells → 36 villages), so the evaluation unit is the 110 m cell, never an FTW polygon. There are also **no 2018 FTW polygons**, so a 2018 comparison has to use boxes.
(c) **Wrong years.** 2017 and 2018, against a registry built on 2025 imagery and hand labels from 2025–26. The calendar prior assumes the planting calendar is stationary over seven years, which is exactly the assumption a rainfed district most threatens.
(d) **`D-q415` is two quantities** — transplanting date on transplanted fields, sowing date on direct-seeded ones. Mixing them roughly doubles the measured spread (Odisha 2017: 22.9 d pooled vs 11.8 d transplanted-only). Every statistic here is transplanted-only and in-season, enforced in `odisha_calendar.kharif_transplanted` and tested.
**Revisit if:** the contact refuses permission (then the prior and the secondary set both come out, and D-005 stands as written); or the 2026–27 replay makes a stationarity test possible and the 2017/2018 calendar turns out not to hold.

### D-034 · 23 Nov 2026 · Disclosure: CSISA Odisha transplanting spreads were seen before the freeze
**Decision:** **D-031's pre-registered prediction stands exactly as written** — "Odisha's transplanting-date spread is materially larger than SICKLE's 10.0 d", to be decided by measuring flooding/transplanting spread across the Odisha field registry in P3. This entry records that **related evidence was in hand on 23 Nov 2026, seven days before the freeze**, and what it says, so the disclosure is in the record rather than discovered later.

**What was seen** (`reports/csisa_calendar_stats.md`, `scripts/csisa_odisha_calendar.py`; farmer-reported, transplanted-only, in-season, days since 1 Jun):

| scope | n | transplanting SD | robust SD | vs SICKLE's 10.0 d |
|---|---|---|---|---|
| Odisha, both years, all districts | 1,049 | **10.4 d** | 7.4 | +0.4 |
| **Balasore 2018** (= Baleswar) | 184 | **5.7 d** | 4.4 | **−4.3** |
| Cuttack 2017 | 133 | 12.2 d | 10.4 | +2.2 |
| Khordha 2017 | 112 | 11.5 d | 11.9 | +1.5 |
| Jajpur 2018 | 126 | 10.9 d | 5.9 | +0.9 |
| Bhadrak 2018 | 176 | 9.7 d | 7.4 | −0.3 |
| Mayurbhanj 2017 | 110 | 9.3 d | 7.4 | −0.7 |
| Jagatsinghpur 2018 | 208 | 8.2 d | 3.0 | −1.8 |

**This cuts against D-031, and it should be said plainly.** Pooled across Odisha the spread is **10.4 d against SICKLE's 10.0 d** — indistinguishable, not "materially larger" — and in **our own study district it is roughly half** SICKLE's. Within-village spread in Balasore is 3.8 d. If the P3 registry measurement agrees, D-031's revisit clause fires ("comes back under ~15 d… report as such rather than worked around") and the dissertation's emphasis moves to M3/M4.

**Why the prediction is not rewritten anyway.** Four reasons, and they are reasons to keep the prediction live, not to dismiss the evidence. (a) **Different quantity**: CSISA is a farmer's recalled transplanting date, which heaps on round days (36–43% in the 2017 samples against ~23% by chance); D-031's test is a radar-observed flooding date over the registry. (b) **Different frame**: 185 farmers in 36 purposively surveyed villages, not a sample of 133,055 Baleswar fields — and between-village variation is 56% of Balasore's total spread, so a 36-village sample can understate a district. (c) **Different years**: 2017/2018, two monsoons, against the 2025–26 season the labels come from. (d) **The spread is not the mechanism anyway** — D-031's claim is that harvest date is set by transplanting *and variety*, and CSISA supports that half strongly: on every group tested, transplanting + per-variety median duration beats a median-harvest baseline (Odisha 2017 13.5 → 10.4 d, Bihar 2017 11.3 → 9.3 d), and in Balasore MTU 7029 (n = 124, 67% of the district's fields) has a duration SD of just **5.6 d**.
**Cost to know about:** the freeze's point F(d) said D-031's prediction was written in "before any Odisha number is drawn". **That is no longer strictly true** and the frozen text must say so: a farmer-survey prior for the same districts was seen first, it pointed the other way, and the prediction was kept unchanged with this entry as the disclosure. Keeping it is the more falsifiable choice — rewriting it now to match CSISA would make the P3 measurement unfalsifiable after the fact.
**Revisit if:** the P3 registry transplanting-spread measurement lands; then D-031 is decided on that number, with this entry as the record of what was known beforehand.

### D-035 · 26 Nov 2026 · The evaluation protocol is frozen as `protocol-v1`
**Decision:** `EVALUATION.md`'s sections marked *(v1)* — O1's like-for-like stratified criterion, §Interval quality rules 1–6, §Leakage tests, §Secondary evaluation set, §M2 protocol and §Replay protocol — are frozen at git tag `protocol-v1`. Five choices were made in the freeze itself rather than earlier, and each is a place a reviewer could push:
1. **Like-for-like O1.** Pooled arms are compared with the pooled calendar arm. The stratum table had compared them with the raw one; corrected, the unique-date sensor gain on SICKLE is −0.90 d [−1.76, +0.14], not separated (D-031 amended).
2. **Rule 5 replaced by a measured scoring design.** The drafted intersection rule shrinks MAE by 1.6–2.0 d and inflates coverage by 3 points on SICKLE with Odisha-width synthetic intervals. Frozen instead: error is scored against the **label midpoint** (+0.1–0.3 d bias) with an [intersection, uniform-expected] bracket that contains the exact error; coverage is **intersection minus its measured 3.0-point optimism**, bracketed below by uniform-expected coverage; the transfer gap is computed against SICKLE scored the same way.
3. **Season mapping `sep-feb`** for zero-shot M1 on Odisha, chosen by agronomic analogy (samba ≈ Odisha kharif) before any Odisha score; the other four mappings are a reported sensitivity.
4. **Descending S1 passes** for the headline Odisha sensor features, because SICKLE is 96% descending and Baleswar's ascending track sits 5° shallower.
5. **A source-lag table in code** (`eval.availability`), raise-only after the freeze, used by every Odisha and replay feature, with D-019's cut-off in the same module.
Also fixed in the freeze: crossed conformal intervals collapse to their centre (0.4% of rows; headline 92.3% / 24.8 d unchanged). Defaults left as drafted: Tuesday issue dates, one SICKLE unlock around 11 Dec.
**Why:** the protocol is only a protocol if it is fixed before the numbers it governs exist. Two of the five choices (season mapping, pass direction) would otherwise have been made after looking at Odisha errors, and the rule-5 measurement turned up biases (−1.6 d on MAE, +3 points on coverage for the draft rule; −10 points on coverage for the obvious alternative, midpoint) large enough to decide O1 by themselves.
**Cost to know about:** (a) the freeze happened after CSISA's Odisha spreads were seen (D-034), so the D-031 step is pre-registered against the model, not against all Odisha evidence; (b) the lag table is estimated, not measured, and only its direction of error is controlled; (c) the SICKLE hindcast's weather arms read weather with no lag — disclosed, not rerun, because those arms lost and the point model uses no weather; (d) 61 free Odisha fields over 58 blocks is a small development set and every Odisha CI will be wide.
**Revisit if:** anything in a *(v1)* section has to change — then add a dated amendment there and an entry here, and say so in the dissertation. Raising a lag is the one change allowed without a new decision.
