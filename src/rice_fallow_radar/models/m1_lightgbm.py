"""LightGBM for M1, fitted with nested CV so the ablation is not tuned on its own test folds.

Why nested: the feature table has 2,745 rows but only 43 neighbour groups, so the effective
sample size for generalisation is 43. Picking hyperparameters on the outer test fold would make
every arm of the point-C ablation look better by an amount that depends on how many features it
has -- which is exactly the quantity the ablation is trying to measure. So each outer fold tunes
on an inner 3-fold split of its own training rows only.

`objective="regression_l1"` because the reported metric is MAE; squared error would chase the
long tail of early-season rows. Predictions are left unclipped, like the baselines, so the
arms stay directly comparable.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from ..eval import splits

TARGET = "lead"
INNER_FOLDS = 3
# n_jobs=1 deliberately: on 2k rows LightGBM's threading costs 5x more than it saves
FIXED = dict(objective="regression_l1", learning_rate=0.05, verbosity=-1, n_jobs=1)
# small on purpose: 12 configs is what 43 groups can support without tuning into the noise
GRID = [
    dict(num_leaves=leaves, min_child_samples=mcs, n_estimators=trees)
    for leaves in (7, 15, 31)
    for mcs in (20, 50)
    for trees in (200, 500)
]


def _fit(train: pd.DataFrame, cols: list[str], params: dict, seed: int) -> lgb.LGBMRegressor:
    m = lgb.LGBMRegressor(**FIXED, **params, random_state=seed)
    return m.fit(train[cols], train[TARGET])


def _tune(train: pd.DataFrame, cols: list[str], seed: int) -> dict:
    """Pick the grid point with the lowest inner-fold MAE, using training rows only."""
    inner = splits.assign_folds(train, n=INNER_FOLDS, seed=seed + 1)
    scores = []
    for params in GRID:
        err = [
            np.abs(
                _fit(train[inner != k], cols, params, seed).predict(train.loc[inner == k, cols])
                - train.loc[inner == k, TARGET]
            ).mean()
            for k in sorted(inner.unique())
        ]
        scores.append(float(np.mean(err)))
    return GRID[int(np.argmin(scores))]


def oof_predict(
    dev: pd.DataFrame, cols: list[str], fold: pd.Series, seed: int = splits.SEED
) -> tuple[np.ndarray, list[dict]]:
    """Out-of-fold predictions over `fold`, tuning inside each fold's training rows."""
    pred = np.full(len(dev), np.nan)
    chosen = []
    for k in sorted(fold.unique()):
        tr, te = dev[fold != k], dev[fold == k]
        params = _tune(tr, cols, seed)
        pred[np.flatnonzero((fold == k).to_numpy())] = _fit(tr, cols, params, seed).predict(
            te[cols]
        )
        chosen.append(params)
    assert not np.isnan(pred).any(), "a row got no out-of-fold prediction"
    return pred, chosen


def gain_importance(dev: pd.DataFrame, cols: list[str], seed: int = splits.SEED) -> pd.Series:
    """Total-gain importance from one fit on all dev rows. Diagnostic only, never a result."""
    m = _fit(dev, cols, _tune(dev, cols, seed), seed)
    return pd.Series(m.booster_.feature_importance("gain"), index=cols).sort_values(ascending=False)
