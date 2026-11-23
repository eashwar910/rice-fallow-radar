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

- **Coverage:** fraction of true harvest dates inside the interval; target = nominal (e.g., 80% or 90%).
- **Width:** average interval width in days — narrow and well-covered is the goal.
- **Conditional coverage:** coverage by horizon, district and land type — marginal coverage can hide systematic failure in a subgroup.

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
