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
    # optional `weight` column: M2 up-weights target-domain rows (absent on SICKLE -> unweighted)
    return m.fit(train[cols], train[TARGET], sample_weight=train.get("weight"))


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


def pool_predictions(df: pd.DataFrame, pred: np.ndarray) -> pd.DataFrame:
    """Average a field's repeated estimates of the same harvest date (D-030).

    `lead` is predicted independently at each of a field's ~9 weekly issue dates, which throws
    away eight estimates of one quantity. Each prediction is converted to an implied harvest
    date and the forecast at `as_of` is the running mean of the implied dates from the issue
    dates **at or before `as_of`**; plain equal weighting beat every recency weighting tested.

    Returns `pooled` (the pooled prediction, in days to harvest, on `df`'s own index) and
    `n_acc` (how many estimates that row averages -- pooling is neutral at 1-2 and worth ~1 d
    by the fourth, so anything calibrated on these predictions must condition on it).

    `build()` emits rows lead-ascending, i.e. **`as_of` descending**, so an expanding window
    over the table's own row order would read the future; hence the explicit sort.
    """
    as_of = df.as_of.map(pd.Timestamp.toordinal).astype(float)
    order = df.sort_values(["unique_id", "as_of"]).index
    implied = (as_of + np.asarray(pred, float)).loc[order]
    by_field = implied.groupby(df.unique_id.loc[order])
    pooled = by_field.expanding().mean().reset_index(level=0, drop=True) - as_of.loc[order]
    out = pd.DataFrame({"pooled": pooled, "n_acc": by_field.cumcount() + 1})
    return out.reindex(df.index)
