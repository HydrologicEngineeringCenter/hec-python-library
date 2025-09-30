import os
import warnings
from datetime import datetime
from typing import Generator, Optional, cast

import numpy as np
import pytest

from hec import Combine, CwmsDataStore, HecTime, Parameter, TimeSeries, UnitQuantity
from hec.rating import AbstractRatingSet, ReferenceRatingSet
from hec.shared import import_cwms

_db: Optional[CwmsDataStore] = None
_multi_param_rating_set: Optional[AbstractRatingSet] = None

import pytest


@pytest.fixture(scope="session", autouse=True)
def before_all_after_all() -> Generator[None, None, None]:
    global _multi_param_rating_set
    # ---- before all tests ----
    yield
    # ---- after all tests ----
    if _multi_param_rating_set is not None:
        _multi_param_rating_set = None
        if _db is not None:
            _db.close()


def can_use_cda() -> bool:
    try:
        import_cwms()
    except:
        return False
    if os.getenv("cda_api_root") != "https://wm.swt.ds.usace.army.mil:8243/swt-data/":
        return False
    if os.getenv("cda_api_office") != "SWT":
        return False
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


def test_elev_stor_rating_set() -> None:
    global _db
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    if _db is None:
        _db = CwmsDataStore.open()
        _db.time_window = "t-1d, t"
    # ----------------------------------- #
    # get a time series from the database #
    # ----------------------------------- #
    elev_ts_29 = cast(TimeSeries, _db.retrieve("ARCA.Elev.Inst.1Hour.0.Ccp-Rev"))
    for method in "REFERENCE", "EAGER":
        # ---------------------------------- #
        # get a rating set from the database #
        # ---------------------------------- #
        rating_set = cast(
            ReferenceRatingSet,
            _db.retrieve("ARCA.Elev;Stor.Linear.Production", method=method),
        )
        _test_elev_stor_rating_set(rating_set, elev_ts_29)


def _test_complex_rating_set(
    rs: AbstractRatingSet, p1_val: float, p2_val: float, expected_val: float, units: str
) -> None:
    dep_vals = rs.rate_values([[p1_val], [p2_val]], units=units)
    assert round(dep_vals[0], 5) == expected_val


@pytest.mark.parametrize(
    "stage, speed_index, expected_flow",
    [
        [24, 0.9, 26073.54308],  # values are from database schema test
        [24, 1.0, 29206.94457],
        [24, 1.1, 32340.34606],
        [25, 0.9, 27056.06359],
        [25, 1.0, 30307.53999],
        [25, 1.1, 33559.01639],
        [26, 0.9, 251578.80378],  # speed not used if stage > 25 ft
        [26, 1.0, 251578.80378],  #
        [26, 1.1, 251578.80378],  #
    ],
)
def test_complex_reference_rating_set(
    stage: float, speed_index: float, expected_flow: float
) -> None:
    """
    This test uses a transitional rating that uses two different virtual ratings (one if the stage
    <= 25 feet and the other stage > 25 feet). Both source ratings to the transitional rating are
    virtual ratings. One virtual rating uses two table ratings and a rating expression (formula),
    while the other virtual rating uses a single table rating and a rating expression.

    Args:
        stage (float): The stage value in ft
        speed_index (float): The index speed value in mph
        expected_flow (float): The expected flow value in cfs
    """
    global _db, _multi_param_rating_set
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    if _multi_param_rating_set is None:
        if _db is None:
            _db = CwmsDataStore.open()
        _db.time_window = "t-1d, t"
        # -------------------------------------------- #
        # get a reference rating set from the database #
        # -------------------------------------------- #
        _multi_param_rating_set = cast(
            ReferenceRatingSet,
            _db.retrieve(
                "FSMI.Stage,Speed-Water Index;Flow.Transitional.Production",
                method="REFERENCE",
            ),
        )
    # --------------------------------------------------------- #
    # rate the input values and compare with the expected value #
    # --------------------------------------------------------- #
    _test_complex_rating_set(
        _multi_param_rating_set, stage, speed_index, expected_flow, "ft,mph;cfs"
    )


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


def generate_rating_error_info2() -> None:
    import re

    with open("ratings_test2.txt", "w") as f:

        def output(msg: str) -> None:
            print(msg)
            f.write(f"{msg}\n")
            f.flush()

        recent = HecTime.now() - "P2D"
        with CwmsDataStore.open() as db:
            cwms = db.native_data_store
            response = cwms.api.get(endpoint="offices", params={"has-data": True})
            offices = sorted([item["name"] for item in response])
            for office in offices:
                output(office)
                db.office = office
                template_cat = db.catalog(
                    "RATING_TEMPLATE", pattern="*,*", fields="name, rating-ids"
                )
                for template_item in template_cat:
                    parts = template_item.split("\t")
                    template_id = parts[0]
                    rating_ids = eval(parts[1])
                    for rating_id in rating_ids:
                        spec_cat = db.catalog(
                            "RATING_SPECIFICATION",
                            pattern=rating_id,
                            fields="name,effective-date",
                        )
                        for spec_item in spec_cat:
                            rating_id, dates = spec_item.split("\t")
                            if dates == "<None>":
                                output(f"\t{rating_id}\tNO EFFECTIVE DATES")
                                continue
                            output(f"\t{rating_id}\t{dates}")
                            location_id = rating_id.split(".")[0]
                            ind_params = template_id.split(";")[0].split(",")
                            tsids = []
                            has_ts = True
                            for ind_param in ind_params:
                                ts_cat = db.catalog(
                                    "TIMESERIES",
                                    pattern=f"{location_id}.{ind_param}.*",
                                    fields="name,earliest-time,latest-time",
                                )
                                for ts_item in ts_cat:
                                    tsid, earliest, latest = ts_item.split("\t")
                                    latest_time = HecTime(latest)
                                    if latest_time > recent:
                                        tsids.append(tsid)
                                        break
                                else:
                                    output(
                                        f"\t\tNo time series for parameter {ind_param}"
                                    )
                                    has_ts = False
                                    break
                            if not has_ts:
                                continue
                            try:
                                rs = cast(
                                    AbstractRatingSet,
                                    db.retrieve(rating_id, method="REFERENCE"),
                                )
                            except Exception as e:
                                output(f"\t\t===> {e}")
                                continue
                            try:
                                output(f"\t\t{rs}")
                                input_values = []
                                ind_units = []
                                for tsid in tsids:
                                    ts = cast(
                                        TimeSeries,
                                        db.retrieve(
                                            tsid,
                                            start_time=latest_time,
                                            end_time=latest_time,
                                        ),
                                    )
                                    output(f"\t\t{ts} = {ts.values[0]}")
                                    input_values.append([ts.values[0]])
                                    ind_units.append(ts.unit)
                                dep_unit = Parameter(rs.template.dep_param).unit_name
                                rated = rs.rate_values(
                                    input_values,
                                    units=f"{','.join(ind_units)};{dep_unit}",
                                )
                                output(f"\t\trated = {rated[0]}")
                            except Exception as e:
                                output(f"\t\t===> {e}")


if __name__ == "__main__":
    pass
