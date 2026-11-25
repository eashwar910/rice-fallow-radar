# Evaluation

> **Frozen as `protocol-v1` on 26 Nov 2026** (D-035). The sections marked *(v1)* are the frozen
> protocol; anything changed after the tag gets a dated amendment here, an entry in
> `DECISIONS.md` and a sentence in the dissertation. Everything else in this file is guidance.

How results will be judged, and why. The success criteria come from the proposal (Table 2) — they're what we told the reader we'd measure. How we get there is open: better metrics, extra baselines, or more honest splits are always welcome additions.

---

## Research questions and how each is answered

| RQ | Question (short) | Data | Metric | Baseline |
|---|---|---|---|---|
| RQ1 | How accurately can harvest be forecast 7/14/21 days ahead, and how much transfer loss can pseudo-labelling + few-shot recover? | SICKLE held-out; Odisha hand labels | MAE, RMSE per horizon; interval coverage and width; transfer gap | Average harvest date; phenology rule; zero-shot M1 |
| RQ2a | Does the two-edged window match observed field state better than a fixed window? | Observed state from S2 (wet) and NISAR (dry) | Agreement rate (and per-class precision/recall) | Fixed 1 Nov–15 Dec window |
| RQ2b | Does PU ranking find fields that later grew a winter crop better than moisture thresholds? | AgriFieldNet; S2 green-up | Precision@k, AUC (as lower bounds) | SMAP 30%/35% classes |
| RQ3 | Using only data available each week of 2026–27, how well do pre-harvest alerts match what happened? | 2026–27 replay | Forecast vs. observed harvest and green-up | SMAP-threshold targeting |

## Success criteria (from the proposal)

- **O1:** MAE ≤ 7 days at the 14-day horizon on held-out SICKLE years; Odisha interval coverage within 5 percentage points of nominal; transfer gap reported with 95% CIs.
  - **Restated 23 Nov 2026 (D-030, D-031; FREEZE_PLAN point F).** The absolute day count is kept as the proposal's promise but is **not** the test of whether the system works, because **7.41 d was reached by a model with no satellite data at all**, and the current best (6.32 d, four calendar features + temporal pooling) still has none. The operative criterion is therefore: **beat the calendar-only arm on the same folds, reported separately on the shared-harvest-date and unique-harvest-date strata.** The split is required rather than optional — 56% of SICKLE dev rows sit on harvest dates shared across plots (farmer recall rounding to a village date, spanning 3.4 neighbour groups so grouped folds do not contain it), and pooled MAE averages a regime where the sensors are **significantly worse** than the clock with one where they are **significantly better**, so a pooled number cannot answer the question. The stratification uses the label, so it is a diagnostic of label quality and never an operational selector; state that wherever it appears.
  - **Frozen 26 Nov 2026 (v1): the comparison is like-for-like.** A pooled arm is compared with the pooled calendar arm and a raw arm with the raw one. Until 25 Nov the published stratum table compared pooled sensor arms against the *raw* calendar arm, which credited pooling's ~1 d to the sensors. Like-for-like, on unique-date plots, `base+s1+pool` against `calendar-4+pool` is **−0.90 d [−1.76, +0.14], not separated**; the raw-vs-raw −1.44 d [−2.27, −0.22] stands. So on SICKLE the sensors' unique-date advantage is significant only before pooling (D-035, `runs/sickle_m1_lightgbm.csv` rerun 26 Nov).
- **O2:** Window agrees with observed state more often than the fixed window; PU ranking beats SMAP classes on precision@k; both with 95% CIs.
- **O3:** Replay completes for every weekly issue date Nov 2026 – Jan 2027 and is scored against held-out observations.

Missing a criterion is a result, not a failure, as long as it's measured honestly and explained.

## Splits

Splits are grouped so that test fields, seasons and neighbours are unseen in training:

- **By plot:** no plot appears in both train and test.
- **By year:** hold out whole seasons (tests generalisation to a new year's weather).
- **By spatial block:** nearby plots share soils, weather and management; block-wise holdout prevents neighbours leaking.

With ~350 SICKLE seasons, leave-one-year-out or grouped k-fold over blocks are both workable. Report which, and keep the final held-out test untouched until the end.

**SICKLE, as implemented (19 Nov 2026).** Groups are the neighbour groups of D-022. Nine groups
(64 of 319 samples, season mix within 2 points of the full set) are locked in
`configs/sickle_test_groups.json` and are not read by any training or tuning script; the
remaining 34 groups (255 samples) are the dev split, cross-validated with 5-fold
`StratifiedGroupKFold` stratified by season. `src/rice_fallow_radar/eval/splits.py`.

**Horizons are lead-time buckets, not issue-date offsets.** Rows are built on a weekly issue
grid and the target is the true days to harvest at that date; building rows at `harvest - h`
would make the target the constant `h`. The proposal's 7/14/21-day horizons are therefore scored
on rows whose true lead falls in 4-10, 11-17 and 18-24 days
(`features.sickle_m1.LEAD_BUCKETS`). M1 rows are also conditioned on the field not yet being
harvested — deciding that is the harvest detector's job — which must be stated when quoting M1
numbers.

Hyperparameter tuning happens inside the training folds (nested CV or a validation split within training groups).

## Uncertainty in the results themselves

Headline metrics carry **95% bootstrap confidence intervals**, resampling at the group level (plot or block), not the row level — rows from the same plot are not independent.

For model comparisons, paired bootstrap on the same test fields is more sensitive than comparing two separate CIs.

## Interval quality (M1/M2)

- **Coverage:** fraction of true harvest dates inside the interval; target = nominal (90% for M1, D-032).
- **Width:** average interval width in days — narrow and well-covered is the goal.
- **Conditional coverage:** coverage by horizon, district and land type — marginal coverage can hide systematic failure in a subgroup.

**Frozen rules for M1's intervals (23 Nov 2026, D-032; `runs/sickle_m1_conformal.csv`).**

1. The published interval is **CQR** on the point model of the day, widened by a split-conformal
   offset estimated on a calibration fold taken from an **inner, group-disjoint split of each
   outer fold's training rows**. Calibrating on rows the point model trained on, or on the test
   fold, voids the interval.
2. Where the forecast aggregates several issue dates, the calibration is **conditioned on the
   number of aggregated estimates**. Residuals from a field's first and ninth forecast are not
   exchangeable, and a single marginal offset over their mixture over-covers at a wide interval
   (measured: 97.2% at 31.6 d, against 92.3% at 24.8 d when conditioned).
3. Coverage and width are reported **by lead bucket, by season, by `n_acc`, and by shared/unique
   harvest date** (O1). Marginal coverage alone is not a result.
4. Coverage is reported as **measured, not certified**: rows cluster ~9 per field, so conformal's
   exchangeability assumption holds at field level at best and the effective calibration size is
   fields, not rows.
5. **Scoring against an interval-valued label** (every Odisha label; `eval.interval_scoring`).
   The draft rule — covered if the intervals intersect, error = the gap between them — was the one
   rule with no measurement behind it, so it was measured before freezing (26 Nov,
   `scripts/interval_rule_check.py`, SICKLE dev only): SICKLE's exact dates were widened into
   synthetic intervals drawn from the free Odisha label widths (median 5 d), truth uniform inside,
   200 draws, and the published out-of-fold predictions rescored.

   | calendar-4+pool, 90% CQR | exact | intersection | **midpoint** | uniform-expected |
   |---|---|---|---|---|
   | MAE | 6.32 d | 4.74 (−1.58) | **6.58 (+0.26)** | 6.73 (+0.41) |
   | coverage | 92.3% | **95.3% (+3.0)** | 81.8% (−10.5) | 80.8% (−11.5) |
   | O1 unique-date gap | −0.90 d | −0.81 | **−0.87** | −0.85 |

   Arm rankings survive every variant (Spearman ρ 0.95; swaps only between arms 0.01 d apart).
   Frozen:
   - **Error headline = midpoint error**, |forecast − label midpoint|: the least biased (+0.1 to
     +0.3 d across five arms) and it keeps the O1 gap. Reported with the bracket
     [intersection gap, uniform-expected], which contains the exact error — the lower end for any
     forecast, the upper end in expectation because the labeller never saw a forecast.
   - **Coverage headline = intersection**, quoted with its measured **+3.0-point optimism**, and
     with the uniform-expected coverage as the lower end of the bracket. **O1's Odisha coverage
     criterion is judged on intersection coverage minus 3.0 points.** A 90% interval scored
     against a 5-day label cannot be pinned more tightly than that: a ±2.5 d label already moves
     coverage by ~10 points, which is itself a finding about how precisely O1 can be tested.
   - **The transfer gap compares like with like:** Odisha midpoint MAE against SICKLE midpoint MAE
     under the same synthetic widening (6.58 d for calendar-4+pool), never against exact 6.32 d.
6. **A crossed interval collapses to its centre** (`m1_conformal.widen`). A negative conformal
   offset larger than the half-width crosses the bounds; 9 of 2,169 dev rows (0.4%, all `n_acc`
   3–4, whose offsets reach −7 d) did so in D-032's published run. Fixed 25 Nov; coverage
   unchanged, mean width 24.80 → 24.81 d.

Measured on SICKLE dev, 90% target: **92.3% [89, 96] at 24.8 d mean width**. The width is the task
and not the method — the 90th percentile of the absolute error is 15.3 d and an oracle
constant-width interval would need 30.3 d — so **M1's decision-grade interval is wider than the
sowing window it feeds**, and M3 should consume the distribution rather than the point.

## Explainability checks

An attribution counts only if it is **faithful**: removing the top-ranked inputs should raise error more than removing random inputs (deletion test; Samek et al., 2017). Report the deletion curves.

The transfer diagnosis is tested by **ablation**, not by attribution alone: mask the hypothesised period (soil drying after irrigation stops) and measure whether the 7-day transfer gap shrinks.

## Leakage tests (automated) *(v1)*

Five checks, each a test that **runs in CI on synthetic data** (`tests/test_leakage.py`): the
SICKLE-backed versions in `test_m1_features.py` skip on a fresh clone because the data is never
committed. Each poisons what a row must not see and asserts the row does not move, and each was
mutation-checked on 25 Nov (injecting a 3-day weather leak, a 6-day S1 leak and an unsorted
pooling each turns the suite red).

1. **Features at `as_of` ignore inputs dated after it** — S1, S2 and weather, poisoned after
   *every* issue date in turn, not only after the last.
2. **Train/test overlap is zero** — SICKLE folds never split a sample or a neighbour group; the
   locked SICKLE groups (`configs/sickle_test_groups.json`) never reach dev; the Odisha eval-locked
   60% is excluded unless `include_locked=True` is passed by name.
3. **AlphaEarth for a season comes from strictly before the season** — `alphaearth_year(Y) = Y−1`
   for a season starting in June of Y, because the year-Y embedding contains that season's harvest.
4. **Product availability lags and the D-019 cut-off are enforced** — `eval.availability`: a
   source's value for day `d` is usable on issue date `as_of` only if `available_on(source, d) <=
   as_of`; an unknown source raises; dates on or after 1 Jun 2026 are refused outside replay mode.
5. **Cross-issue-date aggregation reads only `as_of` at or before the row's own** — pooling
   (`test_m1_pooling.py`) and the pooled conformal interval built on it.

**Known deviation, disclosed rather than fixed:** the SICKLE hindcast table reads weather up to
`as_of` with no publication lag (check 4 binds the Odisha and replay paths, not SICKLE). It affects
only the weather-carrying ablation arms, which lost anyway, so its only possible effect is to
flatter arms that did not win; the point model (D-030) and its intervals (D-032) use no weather.

---

## Secondary evaluation set: CSISA Balasore 2018 (provisional, D-033)

An independent, farmer-reported check on M2 in our own district, named in the frozen protocol so it
cannot be added later once the numbers are known. **185 farmers, Balasore (= Baleswar), 2018
kharif, all transplanted**, at 3-dp (~110 m) coordinates. It is *secondary*: the hand labels
(D-018) remain M2's primary test, and nothing here unlocks them.

**Marked provisional.** The dataset carries no licence (DATA.md §CSISA, OPEN_QUESTIONS #14). If the
data owner declines, this section is struck and the protocol notes that it was struck — the
protocol is not silently rewritten.

Frozen rules:

1. **Unit of evaluation is the 3-dp cell, not the field.** Up to 7 farmers share one cell (185
   farmers → 118 cells → 36 villages), and there are **no 2018 FTW polygons**, so a cell is
   scored as a 110 m box. Any per-FTW-polygon score on this set would be a fiction.
2. **Labels are interval-valued** — a reported date `d` becomes `[d − τ, d + τ]` for a recall
   tolerance τ — and are scored by **§Interval quality rule 5**. *(Amended at the freeze, 26 Nov:
   rule 5 became midpoint error plus a bracket.)* The midpoint of `[d − τ, d + τ]` is `d`, so the
   headline error is |forecast − reported date| for every τ; τ moves only the bracket and the
   coverage, and the coverage correction is re-measured for width 2τ with the same synthetic
   check rather than borrowed from the hand labels' 3.0 points.
3. **τ is reported as a sensitivity sweep, not assumed:** τ ∈ {0, 3, 5, 7, 10} days, headline at
   **τ = 7** (one week, the granularity M3's window actually consumes). This is weaker than the
   plan intended and the reason is measured: the heaping analysis was *supposed* to pin τ, and in
   this sample there is **no heaping to pin it with** — Balasore 2018 reports round days of the
   month 18.4% of the time for establishment and 22.2% for harvest, both **at or below** the
   ~22.6% chance share, against 36–43% in the Odisha 2017 and Bihar 2017 samples
   (`reports/csisa_calendar_stats.md` §7). So τ is a declared parameter with its sensitivity
   published, not a constant derived from the data.
4. **Aggregate by village, not by farmer.** Farmers in a village share a monsoon, a labour pool and
   often a recall anchor; 56% of Balasore's transplanting spread is between villages. Every CI on
   this set bootstraps **villages** (36 of them — so expect wide intervals and quote them).
5. **One out-of-season row is excluded by rule, before scoring:** establishment must fall 0–180
   days after 1 June. The single Balasore row outside it is a *summer (boro) rice* field
   (transplanted 10 Feb, harvested 13 May), and keeping it moves the district's transplanting SD
   from 5.7 d to 12.7 d. The filter is in `features/odisha_calendar.kharif_transplanted` and
   tested, so it cannot be quietly relaxed once results are in.
6. **The baseline this set is scored against is the zero-shot Odisha-calendar arm** (D-033) — one
   harvest date and interval for every field, read off the survey. A transferred M1 that cannot
   beat it on Odisha has not transferred anything the satellites contributed.

## M2 protocol *(v1)*

The order of operations is part of the protocol: each step may only read what the steps before it
have released.

1. **D-031's measurement comes first**, before any Odisha harvest model is scored or tuned.
   Transplanting/flooding-date spread across the registry: **2,000 fields per district**, drawn
   uniformly from `fields.parquet`; Sentinel-1 VH, **descending passes**, 1 Jun – 30 Sep 2025; a
   field's flooding date is the date of its VH minimum, kept only if that minimum is below
   **−20 dB** *and* VH then rises by **≥ 3 dB within 60 days** — the flood-then-canopy signature of
   D-021's strict rule, which separates a transplanting flood from dry pre-monsoon bare soil
   (sensitivity: threshold −18 / −22 dB). `scripts/odisha_transplant_spread.py`, seed 20261126. The statistic is the SD and the
   robust SD (1.4826 × MAD) of flooding season-day, per district and pooled. **D-031 is falsified if
   the pooled robust SD is under 15 d**; per-district values are reported either way. Two biases
   are stated with the number: the 12-day revisit of one track adds roughly √(12²/12) ≈ 3.5 d of
   spread, and the −20 dB filter keeps only fields that visibly flood, which under-represents
   direct-seeded rice (~53% of Odisha's). **The prediction, unchanged from D-031:** the spread is
   materially larger than SICKLE's 10.0 d, so the sensor arm separates from the calendar arm in
   Odisha. **Disclosure (D-034):** this was frozen *before any Odisha harvest model was scored*, but
   *not* before every Odisha number was seen — CSISA's farmer-reported transplanting SD (10.4 d
   pooled, 5.7 d in Baleswar) was measured on 23 Nov and points the other way. The prediction was
   kept as written; rewriting it to match CSISA would have made this step unfalsifiable. The only
   other Odisha quantity read before the freeze is the label-width distribution (already in
   DATA.md), used by the interval-scoring check.
2. **Zero-shot arms, scored on the free 40% only** (61 `ok` fields: Baleswar 33, Bolangir 28; 58
   blocks): zero-shot M1 (`calendar-4+pool` trained on all SICKLE dev, with its D-032 interval),
   the Odisha-calendar arm (D-033), and the seasonal-mean baseline. Rows from
   `features.odisha_m1.build`: real Tuesdays, `as_of < last_green`, midpoint lead ≤ 60 d.
   - **Season mapping, pre-registered:** Odisha kharif is told it is SICKLE's **`sep-feb`**
     (the samba analogue: main monsoon crop, long-duration, Nov–Jan harvest), with
     `days_since_season_start` from 1 Sep. The other four mappings are reported as the *clock
     sensitivity* and never selected.
   - **Sensor features, when they arrive:** headline on **descending passes only**, because 96% of
     SICKLE's S1 scenes are descending (00 UTC) at 31–45° incidence (median 36°), while Baleswar
     sees descending track 48 at ~42.8° *and* ascending track 85 at ~37.5° (25 Nov). All-pass is a
     sensitivity. Every Odisha sensor value goes through `eval.availability.visible`.
3. **Adaptation** (pseudo-labels, TimeMatch-style shift, few-shot) is developed on the free 40%
   with grouped CV over 0.05° blocks; the conformal recalibration uses an inner, block-disjoint
   split of the same 40%.
4. **One unlock of the locked 60%** (92 fields) at the end of P3. Every arm is scored once;
   numbers drawn from it are spent.

Metrics for every Odisha arm (§Interval quality rule 5): midpoint MAE overall and per lead bucket
(by midpoint lead) with its bracket; intersection coverage minus 3.0 points, with its bracket; the
**transfer gap** against SICKLE's midpoint MAE under the same synthetic widening; 95% CIs by **block** bootstrap. The like-for-like arm comparison
(O1) uses the same rows and the same pooling. Primary test set: the hand labels. Secondary: CSISA
Balasore (§Secondary evaluation set), provisional.

## Replay protocol *(v1, frozen 26 Nov 2026)*

Purpose: test the whole system as if it had run live in 2026–27, without peeking.

- **Issue dates:** every **Tuesday from 3 Nov 2026 to 26 Jan 2027** — 13 issues. Tuesday because
  CHIRPS preliminary and ERA5-Land for the previous week are in by then.
- **Data rule:** on each issue date, a value is usable only if `eval.availability.available_on`
  says so. The lag table there is part of the protocol (S1 3 d, S2 5 d, ERA5-Land 8 d, CHIRPS
  preliminary 3 d, CHIRPS final ~25 d after month end, NISAR 14 d, SMAP 3 d, AlphaEarth Y from
  1 Jul Y+1 *and* only years before the season). The lags are conservative estimates; after the
  freeze they may be **raised** if replay ingest shows a longer real lag, **never lowered**.
- **Models:** trained only on data before 1 Jun 2026 (D-019). Models may still be developed after
  the freeze on pre-2026–27 data, but 2026–27 imagery may be ingested and never used to choose a
  model, threshold or hyperparameter. The replay runs the versions tagged **`replay-models`**,
  which must exist before any model reads a 2026–27 value; replay mode (`replay=True`) is only
  used after that tag.
- **Fields in scope:** the registry as frozen (`data/processed/fields.parquet`, 292,060 fields,
  md5 `f3bfa01eef5cbb0411ac768d6f68f87c`), filtered by the D-021 rice mask built from data up to
  the first issue date only.
- **Reference observations:** there are no 2026–27 hand labels (D-018), so replay harvest truth is
  the radar harvest detector validated on the past-season labels, plus S2 green→brown where a clear
  pair exists, read with the labelling protocol (`docs/LABELLING_PROTOCOL.md`) after 15 Feb 2027.
  Winter-crop green-up (M4) is S2 NDVI after harvest, read after 15 Mar 2027. If D-018's Option C
  (~50 2026–27 hand labels) happens in Jan 2027, those labels are made *blind to every forecast*
  and become the primary replay reference.
- **Metrics and baselines:** exactly those above — midpoint MAE and corrected coverage for harvest,
  window agreement against the fixed 1 Nov – 15 Dec window (RQ2a), precision@k against the SMAP
  classes (RQ2b), all with block-bootstrap CIs.
- **Weather inputs to M3:** the primary arm uses **no future weather** — observed ERA5-Land up to
  the lag, then 2000–2025 daily climatology for the days ahead. The upper bound is the oracle arm
  with observed 2026–27 weather. An as-issued forecast archive, if one is found, is an added arm,
  never a replacement.
- **Locked sets:** the SICKLE locked groups get **one unlock around 11 Dec 2026** (the default the
  freeze review left unchanged); the Odisha locked 60% gets one unlock at the end of P3.

Anything changed after the freeze gets a dated note in `DECISIONS.md` and a sentence in the dissertation.

---

## Ideas for stronger evaluation (optional)

- Learning curves: M1 error vs. number of training seasons — shows whether more labels would help.
- Error by field size and valid-pixel count — shows where radar runs out of signal.
- Calibration plots per horizon.
- A "decision value" view: if officers acted on the top-k fields each week, how many would have been in window?
- Sensitivity of M4 results to the class-prior estimate.
