from pathlib import Path

import yaml

import rice_fallow_radar

ROOT = Path(__file__).resolve().parents[1]


def test_package_imports():
    assert rice_fallow_radar.__doc__


def test_districts_config():
    cfg = yaml.safe_load((ROOT / "configs" / "districts.yaml").read_text())
    assert set(cfg["districts"]) == {"bolangir", "baleswar"}
    assert cfg["horizons_days"] == [7, 14, 21]
