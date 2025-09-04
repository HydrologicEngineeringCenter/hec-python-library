import os
import warnings
from datetime import datetime
from typing import cast

import numpy as np

from hec import Combine, CwmsDataStore, HecTime, TimeSeries, UnitQuantity
from hec.rating import AbstractRatingSet, ReferenceRatingSet
from hec.shared import import_cwms


def can_use_cda() -> bool:
    try:
        import_cwms()
    except:
        return False
    # if os.getenv("cda_api_root") != "https://wm.swt.ds.usace.army.mil:8243/swt-data/":
    #     return False
    # if os.getenv("cda_api_office") != "SWT":
    #     return False
    return os.getenv("USERNAME", "").lower() == "q0hecmdp"


def _test_elev_stor_rating_set(
    rating_set: AbstractRatingSet, elev_ts_29: TimeSeries
) -> None:
    assert elev_ts_29.unit == "ft"
    assert elev_ts_29.vertical_datum_info
    assert elev_ts_29.vertical_datum_info.current_datum == "NGVD-29"
    elev_ts_88 = elev_ts_29.to("NAVD-88")
    assert elev_ts_88.unit == "ft"
    assert elev_ts_88.vertical_datum_info
    assert elev_ts_88.vertical_datum_info.current_datum == "NAVD-88"
    # -------------------- #
    # rate the time series #
    # -------------------- #
    stor_ts = cast(TimeSeries, rating_set.rate(elev_ts_29))
    assert stor_ts.unit == "ac-ft"
    assert len(stor_ts) == len(elev_ts_29)
    assert stor_ts.has_same_times(elev_ts_29)
    stor_ts2 = cast(TimeSeries, rating_set.rate(elev_ts_88))
    assert stor_ts2.unit == "ac-ft"
    assert len(stor_ts2) == len(elev_ts_29)
    assert stor_ts2.has_same_times(elev_ts_29)
    assert np.allclose(stor_ts2.values, stor_ts.values, equal_nan=True)
    # ---------------------------------- #
    # reverse rate the rated time series #
    # ---------------------------------- #
    elev_ts_29_2 = cast(TimeSeries, rating_set.reverse_rate(stor_ts))
    assert elev_ts_29_2.unit == elev_ts_29.unit
    assert elev_ts_29_2.vertical_datum_info
    assert elev_ts_29_2.vertical_datum_info.current_datum == "NGVD-29"
    assert len(elev_ts_29_2) == len(elev_ts_29)
    assert elev_ts_29.has_same_times(elev_ts_29)
    assert np.allclose(elev_ts_29.values, elev_ts_29_2.values, equal_nan=True)
    elev_ts_88_2 = cast(
        TimeSeries, rating_set.reverse_rate(stor_ts, vertical_datum="NAVD88")
    )
    assert elev_ts_88_2.unit == elev_ts_88.unit
    assert elev_ts_88_2.vertical_datum_info
    assert elev_ts_88_2.vertical_datum_info.current_datum == "NAVD-88"
    assert len(elev_ts_88_2) == len(elev_ts_88)
    assert elev_ts_88.has_same_times(elev_ts_88)
    assert np.allclose(elev_ts_88.values, elev_ts_88_2.values, equal_nan=True)
    # ----------------------------- #
    # introduce some missing values #
    # ----------------------------- #
    undefined_positions = (len(elev_ts_29) // 3, 2 * len(elev_ts_29) // 3)
    elev_ts3 = elev_ts_29.copy()
    for i in undefined_positions:
        elev_ts3.iselect(i, Combine.OR)
    elev_ts3.iset_value_quality(np.nan, 5)
    # -------------------- #
    # rate the time series #
    # -------------------- #
    stor_ts = cast(TimeSeries, rating_set.rate(elev_ts3))
    assert stor_ts.unit == "ac-ft"
    assert len(stor_ts) == len(elev_ts_29)
    assert stor_ts.has_same_times(elev_ts_29)
    for i in undefined_positions:
        assert np.isnan(stor_ts.values[i])
        assert stor_ts.qualities[i] == 5
    # ---------------------------------- #
    # reverse rate the rated time series #
    # ---------------------------------- #
    elev_ts4 = cast(TimeSeries, rating_set.reverse_rate(stor_ts))
    assert elev_ts4.unit == elev_ts3.unit
    assert len(elev_ts4) == len(elev_ts3)
    assert elev_ts4.has_same_times(elev_ts3)
    assert np.allclose(elev_ts4.values, elev_ts3.values, equal_nan=True)
    for i in undefined_positions:
        assert np.isnan(elev_ts4.values[i])
        assert elev_ts4.qualities[i] == 5
    # ------------------------- #
    # rate with different units #
    # ------------------------- #
    elev_ts_m = elev_ts3.to("m")
    stor_ts_mcm = stor_ts.to("mcm")
    # EN -> SI
    stor_ts3 = cast(TimeSeries, rating_set.rate(elev_ts3, units="mcm"))
    assert stor_ts3.unit == "mcm"
    assert np.allclose(stor_ts3.values, stor_ts_mcm.values, equal_nan=True)
    # SI -> SI
    stor_ts4 = cast(TimeSeries, rating_set.rate(elev_ts_m, units="mcm"))
    assert stor_ts4.unit == "mcm"
    assert np.allclose(stor_ts4.values, stor_ts_mcm.values, equal_nan=True)
    # SI -> EN
    stor_ts5 = cast(TimeSeries, rating_set.rate(elev_ts_m))
    assert stor_ts5.unit == "ac-ft"
    assert np.allclose(stor_ts5.values, stor_ts.values, equal_nan=True)
    # --------------------------------- #
    # reverse rate with different units #
    # --------------------------------- #
    # EN -> SI
    elev_ts5 = cast(TimeSeries, rating_set.reverse_rate(stor_ts, units="m"))
    assert elev_ts5.unit == "m"
    assert np.allclose(elev_ts5.values, elev_ts_m.values, equal_nan=True)
    # SI -> SI
    elev_ts6 = cast(TimeSeries, rating_set.reverse_rate(stor_ts_mcm, units="m"))
    assert elev_ts6.unit == "m"
    assert np.allclose(elev_ts6.values, elev_ts_m.values, equal_nan=True)
    # SI -> EN
    elev_ts7 = cast(TimeSeries, rating_set.reverse_rate(stor_ts_mcm))
    assert elev_ts7.unit == "ft"
    assert np.allclose(elev_ts7.values, elev_ts3.values, equal_nan=True)


def test_reference_rating_set() -> None:
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    cwbi_dev = "https://water.dev.cwbi.us/cwms-data"
    cwbi_test = "https://cwms-data-test.cwbi.us/cwms-data"
    with CwmsDataStore.open(cwbi_test) as db:
        db.office = "LRH"
        db.time_window = "t-1d, t"
        # -------------------------------------------- #
        # get a reference rating set from the database #
        # -------------------------------------------- #
        rating_set = cast(
            ReferenceRatingSet,
            db.retrieve("BeechFk-Lake.Elev;Stor.Standard.Production"),
        )
        # ----------------------------------- #
        # get a time series from the database #
        # ----------------------------------- #
        elev_ts_29 = cast(
            TimeSeries, db.retrieve("BeechFk-Lake.Elev.Inst.15Minutes.0.GOES3-raw")
        )
        _test_elev_stor_rating_set(rating_set, elev_ts_29)


def generate_rating_error_info() -> None:
    with open("ratings_test.txt", "w") as f:

        def output(msg: str) -> None:
            print(msg)
            f.write(f"{msg}\n")
            f.flush()

        cwbi_dev = "https://water.dev.cwbi.us/cwms-data"
        cwbi_test = "https://cwms-data-test.cwbi.us/cwms-data"
        recent = HecTime.now() - "P1D"
        with CwmsDataStore.open(cwbi_test) as db:
            for office in [
                "LRB",
                "LRC",
                "LRD",
                "LRE",
                "LRH",
                "LRL",
                "LRN",
                "LRP",
                "MVD",
                "MVK",
                "MVM",
                "MVN",
                "MVP",
                "MVR",
                "MVS",
                "NAB",
                "NAD",
                "NAE",
                "NAN",
                "NAO",
                "NAP",
                "NDC",
                "NWDM",
                "NWDP",
                "NWK",
                "NWO",
                "NWP",
                "NWS",
                "NWW",
                "POA",
                "POD",
                "POH",
                "SAC",
                "SAD",
                "SAJ",
                "SAM",
                "SAS",
                "SAW",
                "SPA",
                "SPD",
                "SPK",
                "SPL",
                "SPN",
                "SWD",
                "SWF",
                "SWG",
                "SWL",
                "SWT",
            ]:
                output(office)
                db.office = office
                for letter in "ABCDEFGHIGHLMNOPQRSTUVWXYZ":
                    output(f"\t{letter}")
                    rating_cat = db.catalog(
                        "RATING_SPECIFICATION",
                        pattern=f"{letter}*.Elev*;Stor*",
                        fields="name,effective-date",
                    )
                    for rat_item in rating_cat:
                        rating_id, dates = rat_item.split("\t")
                        if "," in rating_id.split(".")[1]:
                            continue
                        if dates != "<None>":
                            if len(eval(dates)) == 1:
                                continue
                            output(f"\t\t{rating_id}\t{dates}")
                            ts_cat = db.catalog(
                                "TIMESERIES",
                                pattern=f"{rating_id.split(';')[0]}.*",
                                fields="name,earliest-time,latest-time",
                            )
                            for ts_item in ts_cat:
                                tsid, earliest, latest = ts_item.split("\t")
                                latest_time = HecTime(latest)
                                if latest_time > recent:
                                    try:
                                        rs = db.retrieve(rating_id)
                                        output(f"\t\t\t{rs}")
                                        ts = db.retrieve(
                                            tsid,
                                            start_time=latest_time,
                                            end_time=latest_time,
                                        )
                                        output(f"\t\t\t{ts} = {ts.values[0]}")
                                        rated = rs.rate(ts)
                                        output(f"\t\t\t{rated} = {rated.values[0]}")
                                        ts2 = rs.reverse_rate(rated)
                                        output(
                                            f"\t\t\t{ts2} = {ts2.values[0]} ({'TRUE' if np.isclose(ts2.values[0], ts.values[0]) else 'FALSE'})"
                                        )
                                    except Exception as e:
                                        output(f"\t\t\t===> {e}")
                                    break


if __name__ == "__main__":
    test_reference_rating_set()
