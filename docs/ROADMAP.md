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

**Useful output for the dissertation:** a short "environment and reproducibility" paragraph. Draft (13 Nov 2026; update the data-version details as P1 lands):

> All code is in a version-controlled repository. The Python environment (3.12) is managed with `uv` and pinned by a lockfile, so `uv sync` rebuilds the exact package versions used for every reported result. Formatting and lint checks (ruff) run as pre-commit hooks, and a GitHub Actions workflow runs the same checks plus the test suite on every push. Study areas, field filters and other settings live in versioned config files rather than in code. Heavy raster processing runs in Google Earth Engine (noncommercial Community tier) and per-field tables are pulled to local disk; every external dataset is recorded with the date its availability and processing level were checked. Credentials (Earth Engine service-account key, NASA Earthdata login) are kept outside the repository. Reported results are tied to git tags (`protocol-v1`, model freeze), so each figure can be traced to the code and configuration that produced it.

### P0 step tracker (agreed 5 Nov 2026; status as of 6 Nov)

| # | Who | Step | Status | Notes / where to pick up |
|---|---|---|---|---|
| 1 | Eashwar (Claude drafts) | Ethics application | ✅ Done (13 Nov) | Submitted by the 12 Nov deadline |
| 2 | Eashwar | Accounts: GEE noncommercial project, Earthdata, SICKLE form, GitHub repo | ✅ Done | GEE project `rice-fallow-radar`, Community tier (D-015). SICKLE email to authors drafted (licence, test set, coordinates) |
| 3 | Claude | Repo scaffold (uv/Py 3.12, ruff, pre-commit, pytest, CI, Makefile, configs) | ✅ Done, committed and pushed | D-014. CI green on `main` (11 Nov) |
| 4 | Eashwar | Local auth | ✅ Done | Browser OAuth blocked → GEE uses service account `rfr-earthengine` (key at `~/.config/earthengine/rfr-sa.json`, loaded by `ingest/earth_engine.init()`). Earthdata creds in `~/.netrc` |
| 5 | Claude | GEE smoke test + EECU cost pilot | ✅ Done (cost measured; export destination open) | Pilot measured EECU (tasks failed only at write: SA has no Drive quota). S1 ≈ 10 EECU-h/season for both districts; CHIRPS per-field is ~300 h → must sample per coarse pixel. Asset root still not writable by SA → use `computeFeatures` pulls in P1 or fix IAM. See DATA.md §Earth Engine compute |
| 6 | Claude | Earthdata / NISAR check | ✅ Done | See DATA.md §NISAR: no data before Oct 2025; ~36% valid cells, uncertainty ~0.04 m³/m³ |
| 7 | Eashwar → Claude | SICKLE download + inspection | ✅ Done (licence pending from authors) | `scripts/sickle_profile.py` reproduces DATA.md §SICKLE. 319 exact labels / 131 plots / 2019–20; test split empty; patches run past harvest (truncate at `as_of`); official split leaks spatially (137/319) → propose neighbour-graph grouped split; authors' S1 hindcast 8.7 d MAE |
| 8 | Claude → Eashwar | FTW quality check (stats + sample map; Eashwar eyeballs) | ✅ Done (provisional unit: D-016) | Stats: median ~0.04 ha, no confidence in India. `scripts/ftw_sample_map.py` → `data/interim/ftw_check/index.html` (12 cells, 6 per district). Eashwar's ratings: 1 good, 4 usable, 2 usable/poor, 4 poor, 1 can't tell. Verdict + filter in DATA.md §FTW and D-016 |
| 9 | Claude | Docs: LOG, DATA, DECISIONS, reproducibility paragraph | ✅ Done | Reproducibility paragraph drafted above (13 Nov); EE export route in D-017 |

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

0. **Done 22 Nov (FREEZE_PLAN A):** per-plot S2 series (`data/interim/sickle_s2_series.parquet`).
   NDVI's pre-harvest decline is stronger and earlier than S1's VH drop, which is what justifies
   putting optical into M1's features (decision 1 of `FREEZE_PLAN.md`). See LOG 22 Nov.
1. Baselines first: average harvest date; phenology rule from the radar curve. These are fast and give the interim report something solid even if the models wobble. **Done 19 Nov:** 12.0 d [9.9, 14.3] and 17.1 d [16.1, 18.2] out of fold on the dev split (`runs/sickle_m1_baselines.csv`). The radar rule loses to the calendar; see LOG 19 Nov for why, and note the proposal's ≤ 7 d target now looks demanding.
2. LightGBM on hand-built time-series features at each horizon. **Done 22 Nov** as a 7-arm
   feature-set ablation (`runs/sickle_m1_lightgbm.csv`): best arm **7.41 d**, which more than
   beats the 12.0 d baseline — but it is the **calendar-only** arm, and no arm carrying satellite
   data separates from it. Sensors with no calendar reach 7.86 d, so the two information sources
   are redundant rather than one being useless. See LOG 22 Nov; this reframes P3.
2b. **Re-opened 23 Nov (FREEZE_PLAN C′) and the null now has a mechanism and a better model.**
   (a) 56% of dev rows sit on harvest dates **shared across plots** — farmer recall rounding to a
   village date, spanning 3.4 neighbour groups, so grouped folds do not contain it. Stratify and the
   null splits in two: calendar **4.94 d** where sensors are significantly *worse*, **10.29 d** where
   `base+s1` is significantly *better*. (b) Harvest date here is set by **variety + transplanting**
   (oracle **4.60 d**), and the delta is too tightly scheduled for a satellite to recover either
   (transplanting sd 10.0 d; a learned detector loses to the season median) — D-031 turns that into a
   pre-registered prediction for Odisha. (c) **A better point model: 7.41 → 6.32 d** [4.97, 7.99], and
   6.16 / 6.16 / 6.08 d at 7/14/21 days, from temporal pooling across issue dates plus dropping 53
   features — D-030. No feature-selection algorithm beat the clock, including ones allowed to cheat.
2c. **Done 23 Nov (FREEZE_PLAN C″): C′ is now code.** `area_acres` out of the base block, temporal
   pooling in `models.m1_lightgbm.pool_predictions` with a leakage test that caught a real
   misalignment bug, and `runs/sickle_m1_lightgbm.csv` regenerated as 16 arms × 17 subsets.
   Reproduces D-030 exactly (**6.32 d** [4.97, 7.99]; 6.16 / 6.16 / 6.08 at 7/14/21 d) and puts the
   stratified arm comparison in the published run: on unique-date plots `base+s1` beats the
   calendar by **−1.44 d** [−2.27, −0.22], on shared-date plots every sensor arm is worse. The
   shared-date share is restated 56% → **58.5%** (definition now fixed in code).
3. **Done 23 Nov (FREEZE_PLAN D): conformalised quantile regression.** CQR on the D-030 model with
   the conformal offset calibrated **per accumulation stratum** (D-032):
   **92.3% coverage [89, 96] at 24.8 d mean width**, 90% target, against 97.2% / 31.6 d for a
   single marginal offset. Conditional coverage is reported by lead, season, `n_acc` and
   shared/unique harvest date; the 7-day bucket (86.3%) and two seasons (~84%) miss nominal and are
   reported as such. **The width is the task, not the method** — |err| p90 is 15.3 d and an oracle
   fixed-width interval needs 30.3 d, so M1's interval is wider than the sowing window it feeds.
   `runs/sickle_m1_conformal.csv`; rules frozen in `EVALUATION.md` §Interval quality.
4. Temporal CNN; LSTM as a comparison if time allows.
5. Grouped splits by plot, year and spatial block; bootstrap CIs.

**For the interim report (3 Dec):** pipeline diagram, field registry stats, SICKLE baseline + first LightGBM numbers, Odisha labelling progress, revised plan.

**By 11 Dec:** full held-out results per horizon.

## Protocol freeze (30 Nov)

Week-by-week plan for this window, agreed 22 Nov: `FREEZE_PLAN.md`.

Write `EVALUATION.md` §Replay protocol as a frozen version (git tag `protocol-v1`): issue dates, which data each issue may use, metrics, reference labels, baselines. After this, 2026–27 imagery can be ingested but not used to choose models or thresholds.

## P3 — M2 transfer and diagnosis (mid-Dec → end Jan)

**Goal:** quantify the Tamil Nadu → Odisha transfer gap and how much of it adaptation recovers, and explain the remaining gap.

- Zero-shot M1 on Odisha labels → gap measurement.
- Radar harvest detector validated on Odisha hand labels → pseudo-labels.
- Temporal-shift estimation (TimeMatch-style) and pseudo-label training.
- Few-shot fine-tuning on a small labelled Odisha subset.
- Conformal recalibration on Odisha labels; coverage before and after.
- Attributions (SHAP for trees, integrated gradients for the CNN), deletion test for faithfulness, and the masking ablation (does masking the post-irrigation drying period shrink the 7-day gap?).

**Added 23 Nov 2026 (D-033/D-034), in priority order:**

- **The D-031 measurement comes first.** Transplanting/flooding-date spread across the Odisha field
  registry from Sentinel-1, before any Odisha harvest model is tuned. CSISA now gives it a
  disclosed prior to be checked against (**10.4 d pooled Odisha, 5.7 d in Baleswar**, against
  SICKLE's 10.0 d — D-034), which makes the measurement more interesting, not less: the two sources
  measure different things and currently disagree with D-031's prediction.
- **The "Odisha-calendar" zero-shot arm** in the transfer ablation (MODELS.md §M2 design note).
  Built already (`features/odisha_calendar.py`); needs only to be scored.
- **A Sentinel-1 per-geometry puller** — `ingest/s1.py`, which does not exist yet; `ee_cost_pilot.py`
  is the only S1 reducer in the repo and it samples coarse cells, not arbitrary geometries. Needed
  anyway for the Odisha feature builder, and separately for the CSISA Balasore cells: **110 m boxes
  around the 118 3-dp cells, 2018 season**. Note there are **no 2018 FTW polygons**, so this is
  boxes-not-fields by necessity, and the boxes mix neighbouring fields — which is a reason to treat
  the Balasore set as secondary (EVALUATION.md). Reuse D-017's `computeFeatures` route and D-027's
  per-tile weather pattern.
- **Scoring the CSISA Balasore secondary set** (185 farmers, 118 cells, interval-valued, τ sweep),
  provisional on the licence question (OPEN_QUESTIONS #14).
- *Stretch, not in scope:* training M1 on CSISA labels. 1,049 Odisha transplanted rows is more
  labels than SICKLE has, but at ~110 m boxes, the wrong years and no field boundaries, so it is a
  separate experiment rather than a drop-in label source.

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
| P0 Setup | ✅ Done (13 Nov) | See P0 step tracker |
| P1 Pipeline | ✅ Field registry done (19 Nov) | `data/processed/fields.parquet`, 292,060 fields; feature builder exists for SICKLE, not yet for Odisha |
| P1b Odisha labels | ✅ Labelled (20 Nov) | 153 harvest intervals of 200 fields; `data/processed/odisha_labels.parquet`, 60% eval-locked. See DATA.md §Odisha hand labels |
| P2 M1 | In progress | FREEZE_PLAN A–D done. Point model **6.32 d** [4.97, 7.99] (four calendar features + temporal pooling, D-030) with **92.3% / 24.8 d** conformal intervals (D-032); the sensor arms earn their place only on the **unique-harvest-date** stratum (−1.44 d), which is why the success criterion is stratified (O1). Left in this window: **F, the freeze** — protocol v1, five leakage checks as CI tests, `protocol-v1` tag |
| Protocol freeze | Not started | **New input (23 Nov):** F(d) must disclose that CSISA Odisha transplanting spreads were seen before the freeze and point the other way (D-034); the Balasore secondary evaluation set and its scoring rule are now written into `EVALUATION.md` and need to be frozen with the rest |
| CSISA (D-033) | Ingested | Both surveys downloaded, md5-pinned and tested; `data/processed/csisa_rice.parquet` (14,746 rows), `reports/csisa_calendar_stats.md` reproduces the 23 Nov review, calendar prior built. Blocked only on the licence contact (OPEN_QUESTIONS #14), which nothing waits for |
| P3 M2 | Not started | |
| P4 M3/M4 | Not started | |
| P5 Integration | Not started | |
| P6 Writing | Not started | |
