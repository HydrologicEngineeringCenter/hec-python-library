import os
import platform
import time
import warnings
from datetime import datetime
from typing import Optional, cast

import numpy as np
import pandas as pd

from hec import (
    CwmsDataStore,
    DeleteAction,
    DssDataStore,
    HecTime,
    Interval,
    Location,
    StoreRule,
    TimeSeries,
    datastore,
    shared,
)
from hec.shared import import_cwms, import_hecdss

import_cwms()
import_hecdss()

STORE_TIMESERIES_STORES_VDI_OFFSETS = False
CDA_ERRORS_ON_LOCAL_DATUM_NAME = True

if CDA_ERRORS_ON_LOCAL_DATUM_NAME:
    vdi = """<vertical-datum-info office="SWT" unit="ft">
    <location>:location</location>
    <native-datum>NGVD-29</native-datum>
    <elevation>615.23</elevation>
    <offset estimate="true">
        <to-datum>NAVD-88</to-datum>
        <value>0.3625</value>
    </offset>
    </vertical-datum-info>"""
else:
    vdi = """<vertical-datum-info office="SWT" unit="ft">
    <location>:location</location>
    <native-datum>OTHER</native-datum>
    <local-datum-name>LocalDatum</local-datum-name>
    <elevation>615.23</elevation>
    <offset estimate="false">
        <to-datum>NGVD-29</to-datum>
        <value>1.07</value>
    </offset>
    <offset estimate="true">
        <to-datum>NAVD-88</to-datum>
        <value>1.3625</value>
    </offset>
    </vertical-datum-info>"""


def test_cwms_datastore() -> None:
    global vdi
    if not shared.cwms_imported:
        return
    api_root = os.getenv("cda_api_root")
    api_key = os.getenv("cda_api_key")
    api_office = os.getenv("cda_api_office")
    if not all([api_root, api_key, api_office]):
        skip_test_message = "Test test_cwms_datastore is skipped because not all of 'api_root', 'api_key' and 'api_office' are set in the environment"
        warnings.warn(skip_test_message)
        return
    number_values = 120
    t = HecTime("15Mar2025 01:00").label_as_time_zone("UTC")
    times = [(t + 1440 * i).datetime() for i in range(number_values)]
    values = [100 + i for i in range(number_values)]
    qualities = number_values * [0]
    timestrs = list(map(str, times))
    loc_id = f"TestLoc_{str(int(time.time()))}"
    rts = TimeSeries(f"{loc_id}.Flow.Ave.1Day.1Day.Regular")
    rts._data = pd.DataFrame(
        {"value": values, "quality": qualities}, index=pd.Index(times, name="time")
    )
    its = TimeSeries(f"{loc_id}.Flow.Ave.~1Day.0.Irregular")
    its._data = pd.DataFrame(
        {"value": values, "quality": qualities}, index=pd.Index(times, name="time")
    )
    # --------------------------------------------- #
    # use in context manager to test implicit close #
    # --------------------------------------------- #
    with CwmsDataStore.open(
        api_root,
        api_key=api_key,
        office=api_office,
        units="EN",
        time_zone="UTC",
        read_only=False,
    ) as db:
        vdi = vdi.replace(":location", loc_id)
        # -------------------------- #
        # store and catalog location #
        # -------------------------- #
        loc_ids = db.catalog("location", pattern=loc_id)
        assert 0 == len(loc_ids)
        loc = Location(
            name=loc_id,
            office=db.office,
            horizontal_datum="NAD83",
            elevation=615.23,
            elevation_unit="ft",
            vertical_datum="NAVD88",
            vertical_datum_info=vdi,
        )
        db.store(loc)
        loc_ids = db.catalog("location", pattern=loc_id)
        assert 1 == len(loc_ids)
        # ----------------------- #
        # get vertical datum info #
        # ----------------------- #
        db_vdi = cast(CwmsDataStore, db).get_vertical_datum_info(loc_id)
        if STORE_TIMESERIES_STORES_VDI_OFFSETS:
            assert db_vdi == loc.vertical_datum_json
        # ----------------------------- #
        # store and catalog time series #
        # ----------------------------- #
        ts_ids = db.catalog("timeseries", pattern=f"{loc_id}.*")
        assert 0 == len(ts_ids), f"0 == {len(ts_ids)}"
        db.store(rts)
        db.store(its)
        catalog = db.catalog(
            "timeseries",
            pattern=f"{loc_id}.*",
            fields="identifier,earliest-time,latest-time,last-update",
        )
        ts_ids, earliest_times, latest_times = [], {}, {}
        for i in range(len(catalog)):
            ts_id, earliest_time, latest_time, last_update = catalog[i].split("\t")
            ts_ids.append(ts_id)
            earliest_times[ts_id] = HecTime(earliest_time)
            latest_times[ts_id] = HecTime(latest_time)
        assert 2 == len(ts_ids), f"2 == {len(ts_ids)}"
        assert rts.name in ts_ids, f"{rts.name} in {ts_ids}"
        assert (
            times[0] == earliest_times[rts.name]
        ), f"{times[0]} == {earliest_times[rts.name]}"
        assert (
            times[-1] == latest_times[rts.name]
        ), f"{times[-1]} == {latest_times[rts.name]}"
        assert its.name in ts_ids, f"{its.name} in {ts_ids}"
        assert (
            times[0] == earliest_times[its.name]
        ), f"{times[0]} == {earliest_times[its.name]}"
        assert (
            times[-1] == latest_times[its.name]
        ), f"{times[-1]} == {latest_times[its.name]}"
        # ---------------------------------- #
        # retrieve time series - use extents #
        # ---------------------------------- #
        for ts_id in (rts.name, its.name):
            extent_times = db.get_extents(ts_id)
            assert extent_times[0] == times[0], f"{extent_times[0]} == {times[0]}"
            assert extent_times[1] == times[-1], f"{extent_times[1]} == {times[-1]}"
            ts = cast(
                TimeSeries,
                db.retrieve(
                    ts_id, start_time=extent_times[0], end_time=extent_times[1]
                ),
            )
            assert len(times) == len(ts), f"{len(times)} == {len(ts)}"
            timestrs2 = ts.times
            assert timestrs == timestrs2, f"{times} == {timestrs2}"
            assert np.allclose(
                values, ts.values, equal_nan=True
            ), f"np.allclose({values}, {ts.values}, equal_nan=True)"
            assert qualities == ts.qualities, f"{qualities} == {ts.qualities}"
        # --------------------------------------------- #
        # retrieve time series - with other time window #
        # --------------------------------------------- #
        start_time = times[1]
        end_time = times[-2]
        for ts_name in (rts.name, its.name):
            ts = cast(
                TimeSeries,
                db.retrieve(ts_name, start_time=start_time, end_time=end_time),
            )
            assert len(times) - 2 == len(ts), f"{len(times) - 2} == {len(ts)}"
            assert timestrs[1:-1] == ts.times, f"{timestrs[1:-1]} == {ts.times}"
            assert np.allclose(
                values[1:-1], ts.values, equal_nan=True
            ), f"np.allclose({values[1:-1]}, {ts.values}, equal_nan=True)"
            assert (
                qualities[1:-1] == ts.qualities
            ), f"{qualities[1:-1]} == {ts.qualities}"
        # ------------------ #
        # delete time series #
        # ------------------ #
        db.delete(rts.name, delete_action=DeleteAction.DELETE_ALL)
        db.delete(its.name, delete_action=DeleteAction.DELETE_ALL)
        ts_ids = db.catalog("timeseries", pattern=f"{loc_id}.*")
        assert 0 == len(ts_ids), f"0 == {len(ts_ids)}"
        # --------------------- #
        # retrieve the location #
        # --------------------- #
        loc2 = cast(Location, db.retrieve(loc_id))
        assert loc.office == loc2.office
        assert loc.name == loc2.name
        assert loc.horizontal_datum == loc2.horizontal_datum
        if STORE_TIMESERIES_STORES_VDI_OFFSETS:
            assert db_vdi == loc2.vertical_datum_json
        # --------------- #
        # delete location #
        # --------------- #
        db.delete(loc_id, delete_action=DeleteAction.DELETE_ALL.name)
        loc_ids = db.catalog("location", pattern=loc_id)
        assert 0 == len(loc_ids)


def test_dss_datastore() -> None:

    if not shared.dss_imported:
        return

    def clean_block_start(pathname: str) -> str:
        parts = pathname.split("/")
        try:
            HecTime(parts[4])
        except:
            pass
        else:
            parts[4] = ""
        return "/".join(parts)

    dss_file_name = "./tester.dss"
    number_values = 120
    t = HecTime("15Mar2025 01:00")
    times = [(t + 1440 * i).datetime() for i in range(number_values)]
    values = [100 + i for i in range(number_values)]
    qualities = number_values * [0]
    # --------------------------------------------- #
    # irregular extents are the actual data extents #
    # --------------------------------------------- #
    irregular_extent_start = HecTime(times[0])
    irregular_extent_end = HecTime(times[-1])

    if os.path.exists(dss_file_name):
        os.remove(dss_file_name)

    rts = TimeSeries("//TestLoc/Flow//1Day/Regular/")
    rts._data = pd.DataFrame(
        {"value": values, "quality": qualities},
        index=pd.DatetimeIndex(times, name="time"),
    )
    # ----------------------------------------------------------------------- #
    # regular extents are the end of the interval containing the extent times #
    # ----------------------------------------------------------------------- #
    regular_extent_start = (
        HecTime(times[0]).adjust_to_interval_offset(rts.interval, 0) + rts.interval
    )
    regular_extent_end = (
        HecTime(times[-1]).adjust_to_interval_offset(rts.interval, 0) + rts.interval
    )

    its1 = TimeSeries("//TestLoc/Flow//IR-Year/Irregular/")
    its1._data = pd.DataFrame(
        {"value": values, "quality": qualities},
        index=pd.DatetimeIndex(times, name="time"),
    )
    its2 = TimeSeries("//TestLoc/Flow//IR-Month/Irregular/")
    its2._data = pd.DataFrame(
        {"value": values, "quality": qualities},
        index=pd.DatetimeIndex(times, name="time"),
    )
    DssDataStore.set_message_level(0)
    # --------------------------------------------- #
    # use in context manager to test implicit close #
    # --------------------------------------------- #
    with DssDataStore.open(dss_file_name, read_only=False) as dss:
        # ----------------- #
        # store and catalog #
        # ----------------- #
        pathnames = dss.catalog("timeseries")
        assert 0 == len(pathnames), f"0 == {len(pathnames)}"
        dss.store(rts)
        dss.store(its1)
        dss.store(its2)
        pathnames = dss.catalog("timeseries")
        assert 3 == len(pathnames), f"3 == {len(pathnames)}"
        assert 7 == len(
            dss.catalog(condensed=False)
        ), f"7 == {len(dss.catalog(condensed=False))}"
        clean_pathnames = list(map(clean_block_start, pathnames))
        assert rts.name in clean_pathnames, f"{rts.name} in {clean_pathnames}"
        assert its1.name in clean_pathnames, f"{its1.name} in {clean_pathnames}"
        assert its2.name in clean_pathnames, f"{its2.name} in {clean_pathnames}"
        # ----------- #
        # get extents #
        # ----------- #
        for pathname in pathnames:
            first_time, last_time = dss.get_extents(pathname)
            if TimeSeries(pathname).is_regular:
                assert (
                    first_time == regular_extent_start
                ), f"{first_time} == {regular_extent_start}"
                assert (
                    last_time == regular_extent_end
                ), f"{last_time} == {regular_extent_end}"
            else:
                assert (
                    first_time == irregular_extent_start
                ), f"{first_time} == {irregular_extent_start}"
                assert irregular_extent_end, f"{last_time} == {irregular_extent_end}"
        # ------------------------- #
        # retrieve - no time window #
        # ------------------------- #
        for ts_name in (rts.name, its1.name, its2.name):
            ts = cast(TimeSeries, dss.retrieve(ts_name))
            assert len(times) == len(ts), f"{len(times)} == {len(ts)}"
            assert times == list(
                map(HecTime, ts.times)
            ), f"{times} == {list(map(HecTime, ts.times))}"
            assert values == ts.values, f"{values} == {ts.values}"
            assert qualities == ts.qualities, f"{qualities} == {ts.qualities}"
        # --------------------------- #
        # retrieve - with time window #
        # --------------------------- #
        start_time = times[1]
        end_time = times[-2]
        for ts_name in (rts.name, its1.name, its2.name):
            ts = cast(
                TimeSeries,
                dss.retrieve(ts_name, start_time=start_time, end_time=end_time),
            )
            assert len(times) - 2 == len(ts), f"{len(times) - 2} == {len(ts)}"
            assert times[1:-1] == list(
                map(HecTime, ts.times)
            ), f"{times[1:-1]} == {list(map(HecTime, ts.times))}"
            assert values[1:-1] == ts.values, f"{values[1:-1]} == {ts.values}"
            assert (
                qualities[1:-1] == ts.qualities
            ), f"{qualities[1:-1]} == {ts.qualities}"
        # ------ #
        # delete #
        # ------ #
        dss.delete(rts.name)
        dss.delete(its1.name)
        dss.delete(its2.name)
        # ------------------------------------------------------------ #
        # the above deletes SHOULD remove the records, but they don't  #
        #                                                              #
        # the tests below are for how the hecdss package works now,    #
        # but should fail if the package is updated to actually delete #
        # the records                                                  #
        # ------------------------------------------------------------ #
        regular_extent_start = (
            HecTime(regular_extent_start).adjust_to_interval_offset(
                Interval.get_dss_block_for_interval(rts.interval), 0
            )
            + rts.interval
        )
        regular_extent_end = regular_extent_start
        pathnames = dss.catalog("timeseries")
        for pathname in pathnames:
            first_time, last_time = dss.get_extents(pathname)
            ts = cast(TimeSeries, dss.retrieve(pathname))
            if ts.is_regular:
                assert (
                    first_time == regular_extent_start
                ), f"{first_time} == {regular_extent_start}"
                assert (
                    last_time == regular_extent_end
                ), f"{last_time} == {regular_extent_end}"
            else:
                assert (
                    first_time == irregular_extent_start
                ), f"{first_time} == {irregular_extent_start}"
                assert irregular_extent_end, f"{last_time} == {irregular_extent_end}"
            assert 0 == len(ts), f"0 == {len(ts)}"
        assert 3 == len(pathnames), f"3 == {len(pathnames)}"
    assert False == dss.is_open  # context manager should close it

    os.remove(dss_file_name)


def test_to_from_native_timeseries() -> None:
    ts: Optional[TimeSeries] = None
    api_root = os.getenv("cda_api_root")
    api_office = os.getenv("cda_api_office")
    if shared.cwms_imported and all([api_root, api_office]):
        with CwmsDataStore.open() as db:
            # ------------------------------------------ #
            # test CWMS round-trip to_native/from_native #
            # ------------------------------------------ #
            db.time_window = "t-1d, t"
            ts = cast(TimeSeries, db.retrieve("KEYS.Elev.Inst.1Hour.0.Ccp-Rev"))
            reg_ts = ts.copy()
            native_ts = reg_ts.to_native(db)
            reg_ts2 = TimeSeries.from_native(db, native_ts)
            assert reg_ts2.name == reg_ts.name
            assert reg_ts2.times == reg_ts.convert_to_time_zone("UTC").times
            assert np.allclose(reg_ts.values, reg_ts2.values)
            assert reg_ts2.qualities == ts.qualities
            irreg_ts = reg_ts.set_interval("0")
            native_ts = irreg_ts.to_native(db)
            irreg_ts2 = TimeSeries.from_native(db, native_ts)
            assert irreg_ts2.name == irreg_ts.name
            assert irreg_ts2.times == irreg_ts.convert_to_time_zone("UTC").times
            assert np.allclose(irreg_ts.values, irreg_ts2.values)
            assert irreg_ts2.qualities == ts.qualities
            # ------------------------------------------ #
            # test CWMS round-trip from_native/to_native #
            # ------------------------------------------ #
            cwms = db.native_data_store
            native_ts = cwms.get_timeseries(
                ts_id="KEYS.Elev.Inst.1Hour.0.Ccp-Rev",
                office_id=db.office,
                unit=db._unit_system,
                begin=cast(HecTime, db.time_window[0]).datetime(),
                end=cast(HecTime, db.time_window[1]).datetime(),
                trim=db.trim,
            )
            reg_ts = TimeSeries.from_native(db, native_ts)
            native_ts2 = reg_ts.to_native(db)
            for item in [
                "name",
                "office-id",
                "units",
                "value-columns",
                "values",
                "vertical-datum-info",
            ]:
                assert (item in native_ts.json) == (
                    item in native_ts2.json
                ), f"json.['{item}'] exists"
                assert (
                    native_ts.json[item] == native_ts2.json[item]
                ), f"json.['{item}'] equals"
            native_ts.json["interval"] = "PT0S"
            native_ts.json["name"] = "KEYS.Elev.Inst.0.0.Ccp-Rev"
            irreg_ts = TimeSeries.from_native(db, native_ts)
            native_ts2 = irreg_ts.to_native(db)
            for item in [
                "name",
                "office-id",
                "units",
                "value-columns",
                "values",
                "vertical-datum-info",
            ]:
                assert (item in native_ts.json) == (
                    item in native_ts2.json
                ), f"json.['{item}'] exists"
                assert (
                    native_ts.json[item] == native_ts2.json[item]
                ), f"json.['{item}'] equals"
    if ts and shared.dss_imported:
        dss_file_name = (
            r"C:\TEMP\test.dss"
            if platform.platform().startswith("Windows")
            else "/var/tmp/test.dss"
        )
        DssDataStore.set_message_level(1)
        with DssDataStore.open(dss_file_name, read_only=False) as dss:
            ts.context = "DSS"
            reg_ts = ts
            dss.store(reg_ts)
            irreg_ts = reg_ts.set_interval("IR-Month")
            dss.store(irreg_ts)
            # ----------------------------------------- #
            # test DSS round-trip to_native/from_native #
            # ----------------------------------------- #
            native_ts = reg_ts.to_native(dss)
            reg_ts2 = TimeSeries.from_native(dss, native_ts)
            assert reg_ts2.name == reg_ts.name
            assert reg_ts2.times == reg_ts.times
            assert np.allclose(reg_ts.values, reg_ts2.values)
            assert reg_ts2.qualities == reg_ts.qualities
            native_ts = irreg_ts.to_native(dss)
            irrreg_ts2 = TimeSeries.from_native(dss, native_ts)
            assert irrreg_ts2.name == irreg_ts.name
            assert irrreg_ts2.times == irreg_ts.times
            assert np.allclose(irreg_ts.values, irrreg_ts2.values)
            assert irrreg_ts2.qualities == irreg_ts.qualities
            # ----------------------------------------- #
            # test DSS round-trip from_native/to_native #
            # ----------------------------------------- #
            hecdss = dss.native_data_store
            native_ts = hecdss.get(reg_ts.name)
            reg_ts = TimeSeries.from_native(dss, native_ts)
            native_ts2 = reg_ts.to_native(dss)
            for item in [
                "id",
                "data_type",
                "interval",
                "units",
                "time_zone_name",
                "times",
                "values",
                "quality",
            ]:
                assert eval(f"native_ts.{item} == native_ts2.{item}"), f"{item} equals"
            native_ts = hecdss.get(irreg_ts.name)
            irreg_ts = TimeSeries.from_native(dss, native_ts)
            native_ts2 = irreg_ts.to_native(dss)
            for item in [
                "id",
                "data_type",
                "interval",
                "units",
                "time_zone_name",
                "times",
                "values",
                "quality",
            ]:
                assert eval(f"native_ts.{item} == native_ts2.{item}"), f"{item} equals"


if __name__ == "__main__":
    test_to_from_native_timeseries()
