"""CSISA ingest: the two traps in the raw files, and the cleaning rules.

2018 stores its coordinates in two columns with empty headers, so they are found by value range
rather than by position; and `estab_date` means transplanting on transplanted fields but sowing on
direct-seeded ones, which is the difference between an 11 d and a 23 d measured spread.

The synthetic tests run everywhere; the real-file tests skip unless the raw download is present
(the files carry no licence, so they are never committed -- DATA.md §CSISA).
"""

from pathlib import Path

import pandas as pd
import pytest

from rice_fallow_radar.ingest import csisa

RAW = Path("data/raw/csisa")


def _frame(**extra) -> pd.DataFrame:
    base = {
        "A-q102_state": ["Odisha"] * 4,
        "A-q103_district": ["Balasore"] * 4,
        "A-q104_subDistrict": ["Sadar"] * 4,
        "A-q105_village": ["V1", "V1", "V2", "V2"],
        "D-q409_varType": ["Improved"] * 4,
        "D-q410_varName": ["MTU7029", "Mansuri_MTU7029", "OtherPooja", "OtherPuja"],
        "D-q413_CropEst": [
            "ManualPuddled_Random",
            "MachineTransplanted_Puddled",
            "DirectBroadcast",
            "DirectSown_Beushening",
        ],
        "D-q414_rcNursEstDate": ["01-07-2018", "02-07-2018", None, None],
        "D-q415_seedingSowingTransDate": ["27-07-2018"] * 4,
        "L-q601_harvestDate": ["22-12-2018", "27-12-2018", "22-12-2018", csisa.MISSING_DATE],
    }
    return pd.DataFrame(base | extra)


def test_coord_columns_found_by_range_not_position():
    df = _frame()
    df["Unnamed: 98"] = [87.41, 86.75, 87.0, 86.9]  # longitude first, to break position guessing
    df["Unnamed: 99"] = [21.18, 21.92, 21.5, 21.6]
    assert csisa.coord_columns(df) == ("Unnamed: 99", "Unnamed: 98")


def test_coord_columns_rejects_an_ambiguous_file():
    df = _frame()
    df["Unnamed: 1"] = [21.18, 21.92, 21.5, 21.6]
    df["Unnamed: 2"] = [21.19, 21.93, 21.4, 21.7]  # two latitude-shaped columns, no longitude
    with pytest.raises(AssertionError, match="coords ambiguous"):
        csisa.coord_columns(df)


def test_variety_spellings_collapse():
    out = csisa.normalise_variety(_frame()["D-q410_varName"])
    assert out.tolist() == ["MTU 7029", "MTU 7029", "Pooja", "Pooja"]


def test_transplanted_flag_separates_the_two_meanings_of_estab_date():
    assert csisa.is_transplanted(_frame()["D-q413_CropEst"]).tolist() == [True, True, False, False]


def test_dates_parse_and_round_trip(tmp_path):
    path = tmp_path / "survey.csv"
    _frame().assign(**{"Unnamed: 9": [21.184] * 4, "Unnamed: 10": [86.746] * 4}).to_csv(
        path, index=False
    )
    df = csisa.load_year(path, 2018)
    assert df.harvest_date.dt.strftime("%d-%m-%Y").tolist()[:3] == [
        "22-12-2018",
        "27-12-2018",
        "22-12-2018",
    ]
    assert df.harvest_date.isna().tolist() == [False, False, False, True]  # the 00-01-00 sentinel
    assert df.duration_days.tolist()[:3] == [148, 153, 148]


def test_implausible_rows_are_the_ones_we_mean():
    df = pd.DataFrame({"duration_days": [148.0, None, 0.0, -5.0, 250.0, 249.0]})
    assert csisa.implausible(df).tolist() == [False, True, True, True, True, False]


# --- the real files, when they are on this machine -------------------------------------------

pytestmark_real = pytest.mark.skipif(
    not (RAW / csisa.FILES[2018]["name"]).exists(),
    reason="needs the local CSISA download (uv run python scripts/csisa_ingest.py)",
)
BALESWAR_BBOX = (86.3532, 21.0640, 87.4829, 21.9796)  # registry bbox, D-026 vintage


@pytestmark_real
@pytest.mark.parametrize("year", [2017, 2018])
def test_real_file_precision_and_ordering(year):
    df = csisa.load_year(RAW / csisa.FILES[year]["name"], year)  # asserts dp internally
    assert (df.coord_dp == csisa.COORD_DP[year]).all()
    ok = df[~csisa.implausible(df)]
    assert (ok.harvest_date > ok.estab_date).all(), "harvest on or before establishment survived"


@pytestmark_real
def test_balasore_2018_points_land_in_the_registry_bbox():
    df = csisa.load_year(RAW / csisa.FILES[2018]["name"], 2018)
    bal = df[df.district == "Balasore"]
    xmin, ymin, xmax, ymax = BALESWAR_BBOX
    assert len(bal) == 185
    assert (bal.lon.between(xmin, xmax) & bal.lat.between(ymin, ymax)).all()


# --- the Odisha calendar prior (D-033) --------------------------------------------------------


def _csisa_like() -> pd.DataFrame:
    """Four Balasore kharif fields plus the two rows a prior must refuse."""
    return pd.DataFrame(
        {
            "state": ["Odisha"] * 6,
            "district": ["Balasore"] * 6,
            "village": ["V1", "V1", "V2", "V2", "V3", "V3"],
            "year": [2018] * 6,
            "var_name_norm": ["MTU 7029"] * 6,
            "transplanted": [True, True, True, True, True, False],
            "estab_date": pd.to_datetime(
                [
                    "2018-07-10",
                    "2018-07-14",
                    "2018-07-18",
                    "2018-07-22",
                    "2018-02-10",  # summer (boro) rice -- out of the kharif window
                    "2018-07-16",  # direct-seeded: estab_date is a sowing date, not transplanting
                ]
            ),
            "harvest_date": pd.to_datetime(
                [
                    "2018-12-07",
                    "2018-12-11",
                    "2018-12-15",
                    "2018-12-19",
                    "2018-05-13",
                    "2018-12-13",
                ]
            ),
            "duration_days": [150.0, 150.0, 150.0, 150.0, 92.0, 150.0],
        }
    )


def test_prior_excludes_summer_rice_and_direct_seeding():
    from rice_fallow_radar.features import odisha_calendar as oc

    p = oc.prior(_csisa_like(), "Balasore")
    assert p.n == 4, "the boro row or the direct-seeded row leaked into the prior"
    # 10/14/18/22 July = days 39..51 since 1 Jun; keeping the Feb row would multiply the SD
    assert p.transplant_q50 == 45.0
    assert 4.0 < p.transplant_sd < 6.0
    assert p.transplant_sd_vs_sickle == p.transplant_sd - oc.SICKLE_TRANSPLANT_SD


def test_zero_shot_forecast_is_an_ordered_interval():
    from rice_fallow_radar.features import odisha_calendar as oc

    zs = oc.zero_shot_harvest(oc.prior(_csisa_like(), "Balasore"), year=2018)
    assert zs["lower"] <= zs["harvest_date"] <= zs["upper"]
    assert zs["width_days"] == (zs["upper"] - zs["lower"]).days
    assert zs["harvest_date"].year == 2018
