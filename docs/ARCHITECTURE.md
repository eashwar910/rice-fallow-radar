# Architecture

How the system fits together, as currently designed. The layout and module names below are a starting point — restructure freely if a cleaner shape emerges once code exists.

---

## Data flow

```
                    ┌──────────────────────────────────────────────┐
  INPUTS            │  Google Earth Engine                         │   Outside GEE
                    │  Sentinel-1 · Sentinel-2 · CHIRPS ·          │   NISAR (Earthdata)
                    │  ERA5-Land · SMAP · AlphaEarth embeddings    │   FTW polygons
                    └──────────────────┬───────────────────────────┘   SICKLE · AgriFieldNet
                                       │                               Odisha hand labels
                                       ▼
  REGISTRY          Field registry: FTW polygons → QA gates → field_id, district, rice mask
                                       │
                                       ▼
  FEATURES          build_features(field_ids, as_of)  ──►  feature store (per field × date)
                    (refuses any input dated after as_of)
                                       │
            ┌──────────────────────────┼───────────────────────────┐
            ▼                          ▼                           ▼
  MODELS    M1 harvest forecaster ──► M3 sowing window          M4 winter-crop success
            (+ intervals)              (wet edge: S1 water;      (PU learning,
            ▲                           dry edge: soil-water      SHAP reason codes)
            │                           balance)
            M2 transfer: TN → Odisha
            (pseudo-labels, shift est., few-shot, recalibration)
                                       │
                                       ▼
  OUTPUTS   Weekly issue: per-field forecast, window state, rank, reasons
            → alert text (Odia/English) · Streamlit dashboard · seed-demand table
                                       │
                                       ▼
  EVAL      Grouped CV on SICKLE · Odisha held-out labels · 2026–27 replay
```

The proposal's Figure 1 shows the same pipeline grouped by objective (O1: M1+M2; O2: M3+M4; O3: integration and evaluation).

## Key design ideas

**The field is the unit.** Every record is keyed by `field_id` (from the registry) and a date. Pixel-level work happens inside Earth Engine; what comes out is per-field aggregates (mean, percentiles, valid-pixel fraction).

**One feature function for training, backtest and replay.** `build_features(field_ids, as_of)` produces training rows (with `as_of` set to each historical cut point), replay rows and live rows. Having one code path is the main defence against train/serve skew and leakage. Every source has an "available on" rule (e.g., a product's publication lag) that the function respects.

**Horizon-cut training rows.** For M1, each labelled season yields rows cut at 7, 14 and 21 days before harvest (or a continuous range of cut points). The model sees only the series up to the cut.

**Irregular time series kept explicit.** Sentinel-1 revisit varies (6–12 days, changed by the loss of Sentinel-1B and the arrival of 1C/1D). Rather than pretending the series is regular, include time-since-last-pass and/or resample with a documented method. Which works better is an open question worth an ablation.

**Earth Engine does the heavy lifting, the laptop does the modelling.** Exports are per-field tables (CSV/Parquet), not rasters, which keeps compute within the noncommercial quota and keeps local data small.

**Everything versioned.** Each run records config hash, data manifest (sources + dates pulled), code commit and seed. MLflow or a plain run table both work; pick whichever is less friction.

## Suggested repository layout

```text
paira-window/
├── CLAUDE.md
├── README.md
├── docs/                    project docs (this folder)
├── configs/                 districts, horizons, thresholds, pinned dataset versions
├── data/                    git-ignored; raw/, interim/, features/, labels/
├── notebooks/               exploration only; anything reused moves into src/
├── src/paira/
│   ├── ingest/              earth_engine.py, nisar.py, sickle.py, ftw.py, agrifieldnet.py
│   ├── registry/            fields.py, qa.py, rice_mask.py
│   ├── features/            build.py, as_of.py, s1.py, s2.py, weather.py, moisture.py
│   ├── labels/              odisha_labelling.py, harvest_detector.py
│   ├── models/              m1_forecast.py, m2_transfer.py, m3_window.py, m4_pu.py
│   ├── calibration/         conformal.py
│   ├── explain/             shap_utils.py, integrated_gradients.py, deletion_test.py
│   ├── eval/                splits.py, metrics.py, bootstrap.py, replay.py
│   ├── outputs/             alerts.py, templates/, seed_demand.py
│   └── app/                 dashboard.py (Streamlit)
├── tests/                   leakage, schema, split, metric and rule tests
├── runs/                    git-ignored run outputs / MLflow
└── Makefile                 common commands (ingest, features, train, eval, app)
```

Data versioning: DVC is one option for `data/`; a manifest file of what was pulled and when may be enough at this scale. Decide during P0.

## Scheduling the weekly run

For the replay, the "weekly job" is just a loop over historical issue dates. If a live demo is wanted later, a scheduled GitHub Actions workflow or a free-tier VM is more reliable than a laptop cron job. Not needed for the core evaluation.

## Things this design doesn't settle yet

- Feature store format (Parquet partitions vs. DuckDB vs. SQLite).
- Whether M1's CNN consumes raw resampled series or the same engineered features as LightGBM plus raw series.
- How M3 handles fields where M1 has very wide intervals.
- How the dashboard is deployed for the viva (local vs. Streamlit Community Cloud).

See `OPEN_QUESTIONS.md`.
