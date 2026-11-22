"""SICKLE splits (D-022): neighbour-group CV with a locked test set.

Groups are connected components of the "plots share a 320 m mask patch" graph
(`scripts/sickle_neighbour_groups.py`). ~20% of groups are locked away as the final test set and
written to `configs/sickle_test_groups.json`, which is the frozen artefact -- recomputing it is
only allowed to reproduce the same file.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

GROUPS_CSV = Path("data/interim/sickle_neighbour_groups.csv")
LOCK_FILE = Path("configs/sickle_test_groups.json")
TEST_FRAC = 0.2
SEED = 20261119
N_FOLDS = 5


def group_of_plot() -> pd.Series:
    g = pd.read_csv(GROUPS_CSV)
    return g.set_index("PLOT_ID").group


def with_groups(labels: pd.DataFrame) -> pd.DataFrame:
    """Add a `group` column to the exact-label table."""
    return labels.assign(group=labels.PLOT_ID.map(group_of_plot()))


def choose_test_groups(labels: pd.DataFrame, frac: float = TEST_FRAC, seed: int = SEED) -> list:
    """Pick whole groups holding ~`frac` of samples with a season mix close to the full set.

    Random search rather than anything clever: with 43 groups of very uneven size, an exact
    balanced partition does not exist, so draw candidates and keep the closest.
    """
    lab = with_groups(labels)
    want = lab.STANDARD_SEASON.value_counts(normalize=True)
    by_group = lab.groupby("group")
    sizes = by_group.size()
    rng = np.random.default_rng(seed)
    best, best_cost = None, np.inf
    n_pick = max(1, round(len(sizes) * frac))
    for _ in range(5000):
        pick = rng.choice(sizes.index, size=n_pick, replace=False)
        sub = lab[lab.group.isin(pick)]
        share = len(sub) / len(lab)
        mix = sub.STANDARD_SEASON.value_counts(normalize=True).reindex(want.index).fillna(0)
        cost = abs(share - frac) * 10 + float(np.abs(mix - want).sum())
        if cost < best_cost:
            best, best_cost = sorted(int(p) for p in pick), cost
    return best


def test_groups(labels: pd.DataFrame | None = None) -> list:
    """The locked test groups, created on first call and read from disk afterwards."""
    if LOCK_FILE.exists():
        return json.loads(LOCK_FILE.read_text())["test_groups"]
    assert labels is not None, f"{LOCK_FILE} missing and no labels given to create it"
    picked = choose_test_groups(labels)
    LOCK_FILE.write_text(
        json.dumps(
            {
                "decision": "D-022",
                "seed": SEED,
                "frac": TEST_FRAC,
                "created": "2026-11-19",
                "note": "Final SICKLE test set. Do not evaluate on these groups before the end.",
                "test_groups": picked,
            },
            indent=2,
        )
        + "\n"
    )
    return picked


def dev_test(labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    lab = with_groups(labels)
    locked = test_groups(labels)
    return lab[~lab.group.isin(locked)].copy(), lab[lab.group.isin(locked)].copy()


def assign_folds(features: pd.DataFrame, n: int = N_FOLDS, seed: int = SEED) -> pd.Series:
    """Fold index per feature row, stratified by season over neighbour groups.

    Assigned per *sample*, so every issue date of a sample lands on the same side of the split --
    issue dates of one plot-season share almost all their scenes. Shared by the baselines and the
    LightGBM ablation so their out-of-fold numbers are comparable rather than merely similar.
    """
    per = features.drop_duplicates("unique_id")[["unique_id", "group", "season"]]
    cv = StratifiedGroupKFold(n, shuffle=True, random_state=seed)
    fold = pd.Series(np.nan, index=features.index)
    for k, (_, te) in enumerate(cv.split(per, per.season, per.group)):
        fold[features.unique_id.isin(per.unique_id.iloc[te]).to_numpy()] = k
    assert fold.notna().all(), "a feature row was left unassigned"
    return fold
