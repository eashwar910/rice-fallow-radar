"""Alignment and dedupe checks for the SICKLE S2 series (FREEZE_PLAN point A).

The 20 m bands (B11, SCL, MSK_CLDPRB) are upsampled onto the 10 m grid, so a shape or origin
slip would silently mask the wrong pixels. These run on the toy release, which ships the same
patch/mask layout.
"""

import os

import pytest

from rice_fallow_radar.ingest import sickle

ROOT = "sickle_toy_dataset"
pytestmark = pytest.mark.skipif(not os.path.isdir(ROOT), reason="needs the SICKLE toy release")


@pytest.fixture(scope="module")
def series():
    ex = sickle.exact_labels(ROOT).head(15)
    s = sickle.s2_series(ROOT, ex)
    assert len(s) > 100, "toy fixture produced almost no scenes"
    return s


def test_indices_and_masks_are_consistent(series):
    good = series[~series.edge_clipped]
    for col in ("ndvi", "ndwi", "mndwi"):
        v = good[col].dropna()
        assert v.between(-1, 1).all(), f"{col} outside [-1, 1]: cloud/band alignment is off"
    assert (good.n_clear <= good.n_px).all(), "more clear pixels than plot pixels"
    # an index is computable exactly when some plot pixel survived the cloud mask
    assert (good.ndvi.notna() == good.n_clear.gt(0)).all()
    assert good.n_clear.gt(0).any(), "nothing survived masking at all"


def test_best_per_date_keeps_one_row_and_never_a_worse_copy(series):
    one = sickle.best_per_date(series)
    assert not one.duplicated(["unique_id", "date"]).any()
    assert set(one.scene) <= set(series.scene) and len(one) <= len(series)
    # the clearest copy wins, but a usable patch beats an edge-clipped one however clear it looks
    usable = series[~series.edge_clipped]
    best = usable.groupby(["unique_id", "date"]).n_clear.max()
    kept = one[~one.edge_clipped].set_index(["unique_id", "date"]).n_clear
    assert (kept == best.reindex(kept.index)).all(), "dedupe kept a more-clouded copy"
    assert (
        set(one[one.edge_clipped].set_index(["unique_id", "date"]).index) & set(best.index) == set()
    )
