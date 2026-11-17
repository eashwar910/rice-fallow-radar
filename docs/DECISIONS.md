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
