"""The two M1 baselines from ROADMAP P2, both fitted out of fold.

1. **Seasonal average date.** Predicts the mean harvest day-of-season of the training samples in
   the same `STANDARD_SEASON`; nothing about the field is used. This is the number any model has
   to beat, and DATA.md's in-sample spread (sd 6-17 days by season) says it will be hard.
2. **Phenology rule on the radar curve.** Rice VH peaks at maximum canopy and falls at harvest,
   so predict harvest = date of the recent VH maximum + a lag fitted per season on the training
   rows (may-sep and sep-feb have different canopy durations). One interpretable parameter, and
   the first baseline that can react to a specific field. The peak is taken from the smoothed
   curve inside a 45-day window (`features.sickle_m1.PEAK_W`): over the full 120-day lookback the
   highest VH is often the previous crop's peak, which triples the error.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..features.sickle_m1 import PEAK_W


def seasonal_mean(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Predicted days to harvest = (season's mean harvest date) - as_of."""
    per_sample = train.drop_duplicates("unique_id")
    # harvest date as a day-of-season offset, so years can be pooled within a season
    off = (per_sample.harvest - per_sample.as_of - pd.to_timedelta(per_sample.lead, "D")).dt.days
    assert (off == 0).all(), "as_of + lead should equal harvest"
    doy = per_sample.assign(
        soy=(
            per_sample.harvest - pd.to_datetime(dict(year=per_sample.year, month=1, day=1))
        ).dt.days
    )
    mean_soy = doy.groupby("season").soy.mean()
    fallback = doy.soy.mean()
    pred_soy = test.season.map(mean_soy).fillna(fallback)
    as_of_soy = (test.as_of - pd.to_datetime(dict(year=test.year, month=1, day=1))).dt.days
    return (pred_soy - as_of_soy).to_numpy(dtype=float)


def vh_peak_rule(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Predicted days to harvest = fitted peak-to-harvest lag - days since the VH peak."""
    col = f"days_since_vh_max_{PEAK_W}"
    lag = train.lead + train[col]  # = days from the VH peak to harvest
    per_season = train.assign(lag=lag).groupby("season").lag.median()
    overall = float(lag.median())
    return (test.season.map(per_season).fillna(overall) - test[col]).to_numpy(dtype=float)


def bootstrap_mean(
    x: np.ndarray, groups: np.ndarray, n: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """Mean of `x` with a 95% CI, resampling whole groups (rows within a group are correlated)."""
    x, groups = np.asarray(x, float), np.asarray(groups)
    keep = ~np.isnan(x)
    x, groups = x[keep], groups[keep]
    if not len(x):
        return (np.nan,) * 3
    uniq = np.unique(groups)
    idx = {g: np.flatnonzero(groups == g) for g in uniq}
    rng = np.random.default_rng(seed)
    draws = [
        x[np.concatenate([idx[g] for g in rng.choice(uniq, len(uniq))])].mean() for _ in range(n)
    ]
    return float(x.mean()), *np.percentile(draws, [2.5, 97.5]).tolist()


def bootstrap_mae(
    err: np.ndarray, groups: np.ndarray, n: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """MAE with a 95% CI. Paired arm-vs-arm differences want `bootstrap_mean` on the signed gap."""
    return bootstrap_mean(np.abs(np.asarray(err, float)), groups, n, seed)
