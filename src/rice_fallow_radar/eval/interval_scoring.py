"""Scoring a forecast against an interval-valued label (EVALUATION.md §Interval quality rule 5).

Every Odisha hand label is an interval (last clear green image -> first clear brown image) and so
is every CSISA label once a recall tolerance is applied. The label says the harvest happened in
`[lo, hi]` and nothing about where. No single score is unbiased against an exact date, so the
frozen rule picks, per quantity, the one measured to be closest, and reports a bracket that
contains the exact value:

    error     headline `midpoint_error` (+0.1-0.3 d), bracket [`point_error`, `expected_error`]
    coverage  headline `covered` (+3.0 points),      bracket [`expected_coverage`, `covered`]

`point_error` is a lower bound for any forecast; `expected_error` is an upper bound in
expectation, provided the label was placed without seeing the forecast (true of the hand labels).

`point_error`/`covered` give the forecast the benefit of the doubt (gap between intervals, zero
when they intersect); `expected_*` average over a uniform true date in the label, which by
Jensen adds the label's own spread to the error. The figures in brackets are the biases measured
on SICKLE dev with synthetic intervals of the Odisha width distribution
(`scripts/interval_rule_check.py`, LOG 26 Nov); exact MAE 6.32 d sat at 4.74 / 6.58 / 6.73 d
(lower / midpoint / upper) and exact coverage 92.3% at 80.8 / 95.3% (lower / upper).

All quantities are in the same units as the inputs (days to harvest, or ordinal dates).
"""

from __future__ import annotations

import numpy as np


def interval_error(pred_lo, pred_hi, lab_lo, lab_hi) -> np.ndarray:
    """Gap between `[pred_lo, pred_hi]` and `[lab_lo, lab_hi]`; 0 where they intersect."""
    pred_lo, pred_hi, lab_lo, lab_hi = map(np.asarray, (pred_lo, pred_hi, lab_lo, lab_hi))
    assert (pred_lo <= pred_hi).all() and (lab_lo <= lab_hi).all(), "an interval is reversed"
    return np.maximum(0, np.maximum(lab_lo - pred_hi, pred_lo - lab_hi))


def point_error(pred, lab_lo, lab_hi) -> np.ndarray:
    """Distance from a point forecast to the label interval (rule 5 with `pred_lo = pred_hi`)."""
    return interval_error(pred, pred, lab_lo, lab_hi)


def midpoint_error(pred, lab_lo, lab_hi) -> np.ndarray:
    """|pred - label midpoint|: the headline error for interval labels."""
    return np.abs(np.asarray(pred, float) - (np.asarray(lab_lo) + np.asarray(lab_hi)) / 2)


def covered(pred_lo, pred_hi, lab_lo, lab_hi) -> np.ndarray:
    """True where the predicted and label intervals intersect."""
    return interval_error(pred_lo, pred_hi, lab_lo, lab_hi) == 0


def expected_error(pred, lab_lo, lab_hi) -> np.ndarray:
    """E|pred - T| for T uniform on `[lab_lo, lab_hi]`; |pred - lab_lo| on a zero-width label."""
    p, a, b = (np.asarray(x, float) for x in (pred, lab_lo, lab_hi))
    w = b - a
    assert (w >= 0).all(), "a label interval is reversed"
    inside = ((p - a) ** 2 + (b - p) ** 2) / (2 * np.where(w > 0, w, 1))
    outside = np.abs(p - (a + b) / 2)
    out = np.where((p > a) & (p < b), inside, outside)
    return np.where(w > 0, out, np.abs(p - a))


def expected_coverage(pred_lo, pred_hi, lab_lo, lab_hi) -> np.ndarray:
    """P(T in [pred_lo, pred_hi]) for T uniform on the label interval."""
    lo, hi, a, b = (np.asarray(x, float) for x in (pred_lo, pred_hi, lab_lo, lab_hi))
    w = b - a
    overlap = np.clip(np.minimum(hi, b) - np.maximum(lo, a), 0, None)
    point = ((lo <= a) & (a <= hi)).astype(float)
    return np.where(w > 0, overlap / np.where(w > 0, w, 1), point)
