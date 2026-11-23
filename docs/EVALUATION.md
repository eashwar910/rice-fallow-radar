# Evaluation

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
5. A predicted interval scored against an **interval-valued label** (every Odisha label) counts as
   covered only if the two intervals intersect, and the error is the distance between them — zero
   when they intersect. Written in now, implemented in P3 (FREEZE_PLAN, "one exception").
   **Provisional: this is the one rule here chosen without a measurement behind it, so it is the
   first thing to argue with at the point-F review.**

Measured on SICKLE dev, 90% target: **92.3% [89, 96] at 24.8 d mean width**. The width is the task
and not the method — the 90th percentile of the absolute error is 15.3 d and an oracle
constant-width interval would need 30.3 d — so **M1's decision-grade interval is wider than the
sowing window it feeds**, and M3 should consume the distribution rather than the point.

## Explainability checks

An attribution counts only if it is **faithful**: removing the top-ranked inputs should raise error more than removing random inputs (deletion test; Samek et al., 2017). Report the deletion curves.

The transfer diagnosis is tested by **ablation**, not by attribution alone: mask the hypothesised period (soil drying after irrigation stops) and measure whether the 7-day transfer gap shrinks.

## Leakage tests (automated)

- `build_features` rejects any input dated after `as_of`.
- Train/test group overlap = 0 for plot, block and (where relevant) year.
- AlphaEarth features for year Y come from Y−1.
- In replay, product availability lags are respected (CHIRPS preliminary vs. final, ERA5-Land lag).

These should be unit tests that run in CI.

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
   tolerance τ — and are scored by **§Interval quality rule 5**: covered if the predicted and
   label intervals intersect, error = the distance between them, zero when they intersect.
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

## Replay protocol (to be frozen on 30 Nov 2026)

Purpose: test the whole system as if it had run live in 2026–27, without peeking.

To fix in the frozen version (git tag `protocol-v1`):

- **Issue dates:** weekly, Nov 2026 – Jan 2027 (exact weekday).
- **Data rule:** on each issue date, use only data published by that date (per-source lag table).
- **Models:** which versions run (trained only on pre-2026–27 data).
- **Reference observations:** how observed harvest week and green-up are determined afterwards (S2 protocol), and when they are collected.
- **Metrics and baselines:** exactly those listed above.
- **Fields:** which fields are in scope (registry version) and the held-out set.
- **Weather inputs to M3:** as-issued forecasts or observed weather (see `OPEN_QUESTIONS.md`).

Anything changed after the freeze gets a dated note in `DECISIONS.md` and a sentence in the dissertation.

---

## Ideas for stronger evaluation (optional)

- Learning curves: M1 error vs. number of training seasons — shows whether more labels would help.
- Error by field size and valid-pixel count — shows where radar runs out of signal.
- Calibration plots per horizon.
- A "decision value" view: if officers acted on the top-k fields each week, how many would have been in window?
- Sensitivity of M4 results to the class-prior estimate.
