"""Interval-label scoring (rule 5) and the Odisha M1 rows it is applied to."""

import numpy as np
import pandas as pd

from rice_fallow_radar.eval import interval_scoring as S
from rice_fallow_radar.features import odisha_m1 as O
from rice_fallow_radar.models import m1_conformal as C


def test_interval_error_is_the_gap_and_zero_on_overlap():
    # label [10, 15] days; predictions inside, overlapping, left of and right of it
    lo, hi = np.array([11, 14, 2, 20]), np.array([12, 30, 7, 25])
    err = S.interval_error(lo, hi, 10, 15)
    assert err.tolist() == [0, 0, 3, 5]
    assert S.covered(lo, hi, 10, 15).tolist() == [True, True, False, False]
    assert S.midpoint_error(np.array([9.0, 12.5, 20.0]), 10, 15).tolist() == [3.5, 0, 7.5]
    # a point forecast is the degenerate interval
    assert S.point_error(np.array([9.0, 12.0, 18.0]), 10, 15).tolist() == [1, 0, 3]
    # on an exact label (zero-width interval) rule 5 is ordinary absolute error
    p = np.array([3.0, 8.5, 12.0])
    assert np.allclose(S.point_error(p, 8, 8), np.abs(p - 8))


def test_odisha_rows_are_tuesdays_before_the_field_turns_brown(odisha_labels):
    rows = O.build(odisha_labels)
    assert set(rows.field_id) == {"a", "c"}  # b is locked, d has no harvest interval
    assert (rows.as_of.dt.day_of_week == O.ISSUE_WEEKDAY).all()
    assert (rows.as_of < rows.last_green).all() and rows.lead_lo.min() >= 1
    assert (rows.lead_hi - rows.lead_lo == 5).all()
    assert rows.lead.max() <= O.MAX_LEAD
    # days are counted from SICKLE's own start of the mapped season (sep-feb -> 1 Sep 2025)
    r = rows.iloc[0]
    assert r.days_since_season_start == (r.as_of - pd.Timestamp("2025-09-01")).days


def test_every_sickle_season_mapping_builds(odisha_labels):
    """The clock sensitivity reports all mappings; none may silently produce no rows except a
    season that starts after the harvest (dec-may for a Nov-Jan harvest)."""
    lab = odisha_labels
    for s in O.SICKLE_SEASONS:
        rows = O.build(lab, season=s)
        assert (rows.days_since_season_start >= 0).all(), s
    assert len(O.build(lab, season="jun-oct")) > len(O.build(lab, season="oct-mar"))


def test_a_negative_offset_never_crosses_the_interval():
    q = np.array([[10.0, 12.0, 14.0], [10.0, 12.0, 30.0]])
    out = C.widen(q, -3.0)  # half-width 2 < 3 on the first row: it would cross
    assert (out[:, 0] <= out[:, 2]).all()
    assert out[0, 0] == out[0, 2] == 12.0 and out[1].tolist() == [13.0, 12.0, 27.0]


def test_expected_scores_match_a_uniform_truth_and_reduce_to_exact_scoring():
    rng = np.random.default_rng(1)
    t = rng.uniform(10, 15, 200_000)  # truth uniform in the label [10, 15]
    for p in (4.0, 11.0, 12.5, 20.0):
        assert abs(S.expected_error(p, 10, 15) - np.abs(p - t).mean()) < 0.02
    assert abs(S.expected_coverage(12, 30, 10, 15) - ((t >= 12) & (t <= 30)).mean()) < 0.005
    # zero-width label: ordinary absolute error and ordinary coverage
    assert S.expected_error(np.array([3.0, 9.0]), 8, 8).tolist() == [5.0, 1.0]
    assert S.expected_coverage(np.array([5, 9]), np.array([10, 12]), 8, 8).tolist() == [1, 0]
    # the bracket is ordered for any forecast: point_error <= midpoint <= expected
    p = rng.uniform(0, 25, 100)
    e = S.point_error(p, 10, 15), S.midpoint_error(p, 10, 15), S.expected_error(p, 10, 15)
    assert (e[0] <= e[1] + 1e-12).all() and (e[1] <= e[2] + 1e-12).all()
