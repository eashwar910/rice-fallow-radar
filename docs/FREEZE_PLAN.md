# Plan to the protocol freeze (22 → 30 Nov 2026)

Scope: everything between the P1b labelling close-out and a tagged `protocol-v1`. Agreed with
Eashwar on 22 Nov 2026. Retire this file once the tag exists; the durable record is `ROADMAP.md`
§P2, `DECISIONS.md` and `LOG.md`.

## Why the plan changed on 22 Nov

Two things were approved:

1. **Sentinel-2 goes into M1's features.** The S1 harvest drop measured on SICKLE is weak
   (median +0.51 dB, present in 60% of samples, *inverted* in may-sep). No architecture fixes a
   missing signal; NDVI collapse at harvest is stronger. The cloud objection does not hold here —
   0 of 498 Odisha pool fields had fewer than 4 clear S2 images (median 37–39).
2. **Open question #13 (the `rice` tick) is answered by a three-annotator design, deferred to P3.**
   Re-tick all 200 fields blind on S2-only full-season evidence (NDVI + a water index, ~40
   repeats), then add the automated S2 rule as a second annotator and Open-SARice as a third, with
   pairwise κ. Plus expand the Bolangir sample (~200 more fields): 100 Bolangir fields with 71
   uncommitted ticks cannot separate "23% rice" from "60% rice", and that number underwrites
   D-021, M4's eligible set and the dry-edge story. Nothing here is a protocol change *provided a
   re-tick moves `rice` only and never `status`* — 2 of the 20 repeats already flipped
   `not_rice` ↔ `ok`, and moving status would alter an eval-locked harvest-label set.

**Gate checked 22 Nov, before planning around it.** SICKLE's S2 patches (126,503 npz) carry the
full band set — `B1`–`B12` including B8 (NIR) and B11/B12 (SWIR) — plus `MSK_CLDPRB` and `SCL`.
So NDVI, NDWI and MNDWI with a per-pixel cloud mask are all computable **locally, with no Earth
Engine pull**. L8 is also present (44,879 npz) with thermal `ST_B10`; the authors' best single
sensor for harvest date was L8 (7.3 d MAE vs S1's 8.7, both optimistic hindcasts), and bare soil
heats once the canopy is cut, so thermal is a candidate feature nobody had considered.

## Repo side (Claude)

| | Work | Produces |
|---|---|---|
| A ✅ | **Done 22 Nov.** **S2 per-plot series.** Extend `ingest/sickle.py`, reusing `s1_series`' mask alignment and `edge_clipped` logic. Cloud from `SCL` + `MSK_CLDPRB`; record clear-scene counts | `data/interim/sickle_s2_series.parquet` (17,625 rows; 12,560 after `best_per_date`). DATA.md §SICKLE now carries the cloud numbers: half the scenes lost, every sample still ≥ 10 clear, NDVI drops +0.121 in 75% of samples vs S1's 60% — and still fails in may-sep |
| B ✅ | **Done 22 Nov.** **S2 features** in `features/sickle_m1.py`: NDVI/NDWI/MNDWI last value, deltas, slopes, days-since-green-peak, days-since-last-clear-scene. Same `as_of` truncation; extend the leakage assert | `sickle_m1_features.parquet` rebuilt: 2,745 rows x 57 features, 15 from S2, **same rows as before** so the ablation is honest; baselines byte-identical |
| C ✅ | **Done 22 Nov.** **LightGBM as a feature-set ablation**, not one model: **calendar-only** → S1-only → S1+weather → S1+S2+weather, same lead buckets, group bootstrap CIs, out of fold on the dev split, nested tuning inside train folds | `runs/sickle_m1_lightgbm.csv` (+ `_tuning`, `_importance`). **Decision 1 is not justified on pooled MAE:** calendar-only 7.41 d is the best arm and no sensor arm separates from it. But sensors-only (no calendar) reaches 7.86 d — the signal is *redundant*, not absent. See LOG 22 Nov |
| | *Why the calendar arm:* `gdd_season` (Spearman 0.75 with lead) and `days_since_season_start` (0.64) dominate every sensor feature, so LightGBM can reproduce the 12.0 d seasonal-mean baseline from the clock alone. Without that arm, a "win" could contain no remote sensing at all | |
| D | **Conformalised quantile regression.** LightGBM quantile 0.05/0.5/0.95 + split conformal on a calibration fold inside dev. Coverage and width overall **and by lead and season** | The conditional-coverage table `EVALUATION.md` promises |
| E ✖ | **Does not run.** Its gate was "only if C shows optical earns its place". C shows S2 does not beat S1+weather (8.23 vs 7.65, CIs overlapping), so adding a fourth sensor block to 33 neighbour groups would add variance, not evidence. Revisit only if the Odisha side shows the sensor arm carrying the load | — |
| | *New input to F from C:* the proposal's **MAE ≤ 7 d** criterion is met (7.41 d) by a model with **no satellite data at all**, so an absolute day count cannot be the success test. The protocol should state the criterion as *beating the calendar-only arm on the same folds*. This is the Eashwar item 4 conversation, now with a number | |
| F | **Frozen protocol:** `EVALUATION.md` §Replay protocol as v1, the four leakage checks as real CI tests (they are currently aspirational), git tag `protocol-v1` | The deliverable this phase is named after |
| G ◐ | **Docs:** D-028 (S2 into M1) ✅, DATA.md S2/cloud facts ✅, LOG entries ✅, `ROADMAP.md` §P2 tracker ✅, MODELS.md M1 inputs ✅. Left: D-029 (#13 design, deferred) and OPEN_QUESTIONS #13 marked decided | |

## Manual side (Eashwar)

1. **Review the frozen-protocol draft** — the only hard gate. Two defaults written in to be
   overridden: issue dates on **Tuesdays** (CHIRPS preliminary and ERA5-Land are both in by then),
   and the SICKLE locked test groups get **one single unlock** around 11 Dec, after which every
   number drawn from them is spent.
2. **Nothing to label** before the freeze — the re-tick is P3 by decision 2 above.
3. Optional: send Dr Chandesa the frozen protocol and C's first numbers before 3 Dec, so the
   ≤ 7 d conversation happens with him rather than being announced in the report.
4. Deferred to interim-writing time: how to state the proposal's **MAE ≤ 7 d** criterion, given a
   12.0 d calendar baseline and a measured 6–9 d labeller noise floor on the Odisha side.

## Deliberately out of this window

All approved, all P3: self-supervised pretraining on unlabelled Odisha S1 (the version of the
deep model worth running — 292k unlabelled fields against 255 labelled dev samples), the
interval-censored loss, the 588 rough SICKLE dates under a noise-aware loss, the rice re-tick and
Bolangir expansion, the Odisha feature builder, and D-021's mask itself.

**One exception that does touch the freeze:** the protocol must say *how* a predicted interval is
scored against an interval-valued label, because the Odisha labels are intervals and frozen text
cannot be silent on it. The interval-censored rule is therefore written into the protocol now and
implemented in P3.
