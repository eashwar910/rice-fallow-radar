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
