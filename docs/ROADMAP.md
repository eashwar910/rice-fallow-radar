# Roadmap

Last updated: 5 November 2026

This is the current plan of work, built from the submitted proposal (Section 8, Figure 2) and the university deadlines. It shows what needs to exist by when, what depends on what, and where there's slack. Dates for internal milestones are estimates; move them when reality says so, and note why in `LOG.md`.

---

## Fixed dates

These come from outside the project and don't move.

| Date | What | Notes |
|---|---|---|
| 29 Oct 2026 | Proposal submitted | Done |
| 12 Nov 2026 | Ethics application | Expected to be low-risk: public data, no human participants, alerts not sent |
| 3 Dec 2026 | Interim report | Needs: working pipeline, Odisha test set under way, first M1 results |
| 15 Apr 2027 | Final dissertation | |
| 29 Apr 2027 | Presentation slides | |

Dates the university hasn't confirmed in our notes: autumn exam period and winter break. Add them here when known — they eat into December–January.

## Commitments made in the proposal

These are what the proposal told the reader would happen. They shape the plan but can be renegotiated with the supervisor if there's a good reason.

| Date | Commitment |
|---|---|
| 3 Dec 2026 | Pipeline and M1 baseline ready for interim report |
| 30 Nov 2026 | Replay evaluation protocol frozen, before any 2026–27 imagery is used |
| 11 Dec 2026 | M1 held-out results complete |
| mid-Dec 2026 → | M2, M3, M4 |
| 5 Mar 2027 | Model freeze |
| ~8 Apr 2027 | One week of buffer before final report |

---

## Phases at a glance

```
Nov 2026          Dec            Jan 2027        Feb            Mar            Apr
|-- P0 setup --|
|------ P1 data pipeline + registry ------|
     |---- P1b Odisha hand labels ----|
         |------ P2 M1 forecaster ------|
                        ◆ 30 Nov protocol freeze
                              ◆ 3 Dec interim   ◆ 11 Dec M1 held-out
                                  |------ P3 M2 transfer + XAI ------|
                                                 |---- P4 M3 window + M4 PU ----|
                                                              |-- P5 integrate, replay, dashboard --|
                                                                               ◆ 5 Mar model freeze
                                                                          |------- P6 writing -------|
                                                                                        ◆ 15 Apr  ◆ 29 Apr
```

The critical path runs P1 → P2 → P3 → P5 → P6. M3 and M4 (P4) are extensions per the proposal ("O1 is the main goal, while O2 and O3 are extensions"), so they have more room to shrink if time runs short.

---

## P0 — Setup (5–12 Nov)

**Goal:** be able to pull data and run code without friction.

- Repo scaffold, environment pinned (`pyproject.toml` or `environment.yml`), pre-commit, basic CI running tests.
- Earth Engine noncommercial project registered; check which quota tier applies and measure cost on a tiny area (see `DATA.md` on quotas).
- NASA Earthdata login (NISAR, SMAP).
- Download SICKLE; confirm what's actually in it (plot count, which dates, which sensors, licence).
- Ethics application submitted (12 Nov).

**Useful output for the dissertation:** a short "environment and reproducibility" paragraph.

## P1 — Data pipeline and field registry (5–25 Nov)

**Goal:** for any set of fields and any `as_of` date, produce a clean feature table using only data that existed on that date.

- **Field registry.** Fields of The World polygons for Bolangir and Baleswar; quality gates (minimum area, shape sanity, overlap, coverage); a stable `field_id`. The October review found FTW polygons can be fragmented on smallholder plots — measure that here before building on it.
- **Rice mask.** Which polygons were kharif rice this year (radar-based rule or existing product).
- **Per-field time series.** Sentinel-1 VV/VH backscatter (with time since last pass, because revisit varies), Sentinel-2 indices and cloud mask, weather (CHIRPS rainfall, ERA5-Land temperature and evaporation), moisture (SMAP, NISAR).
- **SICKLE in the same format** so M1 trains on exactly the features it will see in Odisha.
- **`build_features(field_ids, as_of)`** as the single entry point for both training and live/replay rows, failing loudly if any input post-dates `as_of`.
- **Tests:** schema tests, leakage tests, a small fixture area that runs end-to-end in seconds.

**Possible shortcuts if this drags:** start with Sentinel-1 + CHIRPS only (enough for an M1 baseline) and add the rest after the interim report.

## P1b — Odisha hand-labelled test set (mid-Nov → early Dec)

**Goal:** 150–200 fields in the two districts with harvest week labelled from cloud-free Sentinel-2.

- Write down the labelling protocol first (what visual change counts as "harvested", how to record uncertainty, what to skip). It goes in the dissertation.
- Sample across both districts and across land types, not just the easy, cloud-free fields — note the sampling scheme because it limits what conclusions can be drawn.
- Label a subset twice (or after a gap) to estimate your own label noise.
- Keep a held-out portion that no model ever touches until final evaluation.
- Ask IRRI whether their Odisha ground-truth points can be shared; treat as a bonus, not a dependency.

This set is the backbone of M2 and also validates the radar harvest detector that produces pseudo-labels, so it's worth doing carefully.

## P2 — M1 harvest forecaster (10 Nov → 11 Dec)

**Goal:** a forecaster with held-out SICKLE results at 7/14/21-day horizons, beating the baselines, with calibrated intervals.

1. Baselines first: average harvest date; phenology rule from the radar curve. These are fast and give the interim report something solid even if the models wobble.
2. LightGBM on hand-built time-series features at each horizon.
3. Conformalised quantile regression for intervals; check coverage.
4. Temporal CNN; LSTM as a comparison if time allows.
5. Grouped splits by plot, year and spatial block; bootstrap CIs.

**For the interim report (3 Dec):** pipeline diagram, field registry stats, SICKLE baseline + first LightGBM numbers, Odisha labelling progress, revised plan.

**By 11 Dec:** full held-out results per horizon.

## Protocol freeze (30 Nov)

Write `EVALUATION.md` §Replay protocol as a frozen version (git tag `protocol-v1`): issue dates, which data each issue may use, metrics, reference labels, baselines. After this, 2026–27 imagery can be ingested but not used to choose models or thresholds.

## P3 — M2 transfer and diagnosis (mid-Dec → end Jan)

**Goal:** quantify the Tamil Nadu → Odisha transfer gap and how much of it adaptation recovers, and explain the remaining gap.

- Zero-shot M1 on Odisha labels → gap measurement.
- Radar harvest detector validated on Odisha hand labels → pseudo-labels.
- Temporal-shift estimation (TimeMatch-style) and pseudo-label training.
- Few-shot fine-tuning on a small labelled Odisha subset.
- Conformal recalibration on Odisha labels; coverage before and after.
- Attributions (SHAP for trees, integrated gradients for the CNN), deletion test for faithfulness, and the masking ablation (does masking the post-irrigation drying period shrink the 7-day gap?).

This phase produces the most distinctive research result. If time is short, protect the gap measurement and the ablation; drop model variants first.

## P4 — M3 window and M4 success model (Jan → mid-Feb)

**M3:** wet edge from Sentinel-1 waterlogging after harvest; dry edge from an FAO-56 soil-water balance initialised from NISAR/SMAP and driven by weather; field state per week. Evaluate against observed state vs. the fixed 1 Nov–15 Dec window.

**M4:** positives from past winter green-up on the rice mask (excluding irrigated wheat/mustard); nnPU with Elkan–Noto as the simpler comparison; class-prior sensitivity; SHAP reason codes; validate against AgriFieldNet and SMAP-threshold baseline.

These are extensions. A smaller, honest version of each (e.g., M3 rules only, M4 with one learner) is still a complete result.

## P5 — Integration, replay, dashboard (Feb → 5 Mar)

- Weekly job that runs the whole chain for an issue date.
- Replay every weekly issue date Nov 2026–Jan 2027 using only data available on each date; score against observations gathered afterwards.
- Alert templates (Odia + English) from state crop guidelines — native-speaker check on Odia text if possible.
- Streamlit dashboard: map, per-field forecast with interval, window state, rank and reason codes.
- Model freeze 5 Mar (git tag).

## P6 — Writing (Mar → 15 Apr), slides (16–29 Apr)

Writing should start earlier in pieces: the literature review is mostly done from the proposal; methods sections can be drafted as each phase ends. `LOG.md` entries and saved figures make this much faster.

---

## If things slip

Options in rough order of least damage, to pick from as needed:

1. Drop the LSTM and keep LightGBM + temporal CNN.
2. M4 with nnPU only, no Elkan–Noto comparison.
3. M3 dry edge from SMAP only if NISAR is unreliable.
4. Dashboard as a minimal Streamlit page; alerts as generated text files.
5. M2 limited to zero-shot vs. few-shot fine-tuning (no pseudo-labelling).
6. Narrow the replay to fewer issue dates.

Any of these should be noted in `DECISIONS.md` and acknowledged as a limitation.

## Status

| Phase | Status | Notes |
|---|---|---|
| P0 Setup | Not started | |
| P1 Pipeline | Not started | |
| P1b Odisha labels | Not started | |
| P2 M1 | Not started | |
| Protocol freeze | Not started | |
| P3 M2 | Not started | |
| P4 M3/M4 | Not started | |
| P5 Integration | Not started | |
| P6 Writing | Not started | |
