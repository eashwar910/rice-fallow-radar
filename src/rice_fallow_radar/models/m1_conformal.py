"""Conformalised quantile regression for M1 (FREEZE_PLAN point D).

CQR (Romano, Patterson & Candès, *Conformalized Quantile Regression*, NeurIPS 2019): fit
quantile regressors at `alpha/2` and `1-alpha/2`, then on a held-out calibration set score each
row by how far outside the interval the truth fell,

    E = max(q_lo - y, y - q_hi)        (negative when y is comfortably inside)

and widen the interval by the `ceil((n+1)(1-alpha))`-th smallest score. Marginal coverage is
then `>= 1-alpha` in finite samples for *exchangeable* data, whatever the quantile model does --
the model controls the width, the calibration controls the coverage.

Two reasons the textbook version is not enough here:

* M1's forecast is **pooled over issue dates** (D-030): a field's first forecast averages one
  estimate and its ninth averages nine, and pooling cuts the error by ~1 d by the fourth. A
  first-issue residual is therefore not exchangeable with a ninth-issue one, so the calibration
  is **Mondrian** (group-conditional, Vovk 2012): one offset per accumulation stratum,
  `acc_stratum`. Pooling the quantiles rather than only the median is what keeps the interval
  consistent with the point forecast that is actually published.
* SICKLE's dev split is a mixture of a 4.9 d and an 8.3 d error regime by label quality (C',
  D-031), so one marginal offset is badly conditioned by construction. That is a property of
  the labels, not of the method, and the conditional-coverage table exists to expose it.

**The guarantee is approximate here, and the dissertation has to say so.** Exchangeability is
assumed at the *row* level, but rows cluster by field (~9 issue dates each) and the calibration
fold is group-disjoint from the test fold, so the effective calibration size is the number of
fields, not rows. Treat the coverage numbers as measured, not certified.
"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from ..eval import splits
from .m1_lightgbm import FIXED, TARGET, pool_predictions

ALPHA = 0.10  # target 90% intervals
QUANTILES = (ALPHA / 2, 0.5, 1 - ALPHA / 2)
# Fixed, not tuned. Conformal coverage does not depend on the fit, and tuning these on MAE (point
# C's criterion) would be the wrong loss for a quantile model; this is point C's modal pick for
# the base arm. Width is what tuning could improve, and that is left as named future work.
PARAMS = dict(num_leaves=31, min_child_samples=20, n_estimators=500)
ACC_EDGES = (0, 2, 4, np.inf)  # pooling is neutral at 1-2 estimates and worth ~1 d by the fourth
ACC_LABELS = ("1-2", "3-4", "5+")


def fit(train: pd.DataFrame, cols: list[str], seed: int = splits.SEED) -> list:
    """One LightGBM per quantile. `objective="quantile"` optimises the pinball loss at `alpha`."""
    return [
        lgb.LGBMRegressor(
            **{**FIXED, "objective": "quantile"}, alpha=q, **PARAMS, random_state=seed
        ).fit(train[cols], train[TARGET])
        for q in QUANTILES
    ]


def predict(models: list, df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """`(n, 3)` of lo/median/hi. Sorted per row: independent fits can cross at the tails."""
    return np.sort(np.column_stack([m.predict(df[cols]) for m in models]), axis=1)


def pooled(df: pd.DataFrame, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pool each quantile over a field's issue dates at or before `as_of` (D-030).

    Returns the pooled `(n, 3)` and the accumulation count the pooling used, which the Mondrian
    calibration then conditions on. Pooling is a mean, so it cannot cross the quantiles.
    """
    out = [pool_predictions(df, q[:, j]) for j in range(q.shape[1])]
    return np.column_stack([o.pooled.to_numpy() for o in out]), out[0].n_acc.to_numpy()


def acc_stratum(n_acc: np.ndarray) -> pd.Categorical:
    """Accumulation strata for the Mondrian calibration: 1-2, 3-4, 5+ pooled estimates."""
    return pd.cut(np.asarray(n_acc), list(ACC_EDGES), labels=list(ACC_LABELS))


def offset(lo: np.ndarray, hi: np.ndarray, y: np.ndarray, alpha: float = ALPHA) -> float:
    """Split-conformal widening from calibration rows. `inf` when too few rows to certify."""
    e = np.maximum(np.asarray(lo) - np.asarray(y), np.asarray(y) - np.asarray(hi))
    k = int(np.ceil((len(e) + 1) * (1 - alpha)))
    return np.inf if k > len(e) else float(np.sort(e)[k - 1])


def offsets_by_stratum(
    lo: np.ndarray, hi: np.ndarray, y: np.ndarray, strata, alpha: float = ALPHA
) -> pd.Series:
    """One offset per stratum, plus a `marginal` row for strata absent or too thin to certify."""
    s = pd.Series(np.asarray(strata, dtype=object))
    out = {k: offset(lo[i], hi[i], np.asarray(y)[i], alpha) for k, i in s.groupby(s).groups.items()}
    out["marginal"] = offset(lo, hi, y, alpha)
    return pd.Series(out, dtype=float)


def apply_offsets(table: pd.Series, strata) -> np.ndarray:
    """Each row's own stratum offset, falling back to `marginal` if missing or uncertifiable."""
    off = table.reindex(pd.Index(np.asarray(strata, dtype=object)))
    return off.fillna(table["marginal"]).replace(np.inf, table["marginal"]).to_numpy()
