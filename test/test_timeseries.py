import copy
import math
import os
import statistics as stat
import sys
import traceback
import warnings
from datetime import datetime, timedelta
from test.shared import dataset_from_file, random_subset, scriptdir, slow_test_coverage
from typing import Any, List, Optional, Union, cast

import numpy as np
import pandas as pd
import pytest

from hec import (
    Combine,
    DssDataStore,
    Duration,
    HecTime,
    Interval,
    Parameter,
    ParameterType,
)
from hec import Quality as Qual
from hec import (
    Select,
    SelectionState,
    TimeSeries,
    TimeSeriesException,
    TimeSeriesValue,
    TimeSpan,
)
from hec import UnitQuantity as UQ


def equal_values(v1: list[float], v2: list[float]) -> bool:
    return np.allclose(v1, v2, equal_nan=True)


def test_time_series_value() -> None:
    # --------------------------------------- #
    # - create TSV without specifying quality #
    # --------------------------------------- #
    tsv = TimeSeriesValue("14Oct2024 10:55", UQ(230, "cfs"))
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 10, 55, 0], MINUTE_GRANULARITY), UnitQuantity(230, 'cfs'), Quality(0))"
    )
    assert str(tsv) == "(2024-10-14T10:55:00, 230 cfs, ~)"
    assert tsv.time == HecTime("2024-10-14T10:55:00")
    assert tsv.value == UQ(230, "cfs")
    # --------------------------------- #
    # create TSV with quality specified #
    # --------------------------------- #
    assert (
        tsv.quality.text
        == "Unscreened Unknown No_Range Original None None None Unprotected"
    )
    tsv = TimeSeriesValue("14Oct2024 10:55", UQ(12.3, "ft"), Qual("okay"))
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 10, 55, 0], MINUTE_GRANULARITY), UnitQuantity(12.3, 'ft'), Quality(3))"
    )
    assert str(tsv) == "(2024-10-14T10:55:00, 12.3 ft, o)"
    assert tsv.time == HecTime("2024-10-14T10:55:00")
    assert tsv.value == UQ(12.3, "ft")
    assert (
        tsv.quality.text == "Screened Okay No_Range Original None None None Unprotected"
    )
    # -------------------------------------- #
    # modify TSV (modify value without unit) #
    # -------------------------------------- #
    tsv.time += timedelta(minutes=65)
    tsv.value += 0.7
    tsv.quality = Qual("missing").set_protection(1)
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 12, 0, 0], MINUTE_GRANULARITY), UnitQuantity(13.0, 'ft'), Quality(-2147483643))"
    )
    assert str(tsv) == "(2024-10-14T12:00:00, 13.0 ft, M)"
    assert tsv.time == HecTime("2024-10-14T12:00:00")
    assert tsv.value == UQ(13, "ft")
    assert (
        tsv.quality.text
        == "Screened Missing No_Range Original None None None Protected"
    )
    # ----------------------------------- #
    # modify TSV (modify value with unit) #
    # ----------------------------------- #
    tsv.value = UQ(3.96, "m")
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 12, 0, 0], MINUTE_GRANULARITY), UnitQuantity(3.96, 'm'), Quality(-2147483643))"
    )
    assert str(tsv) == "(2024-10-14T12:00:00, 3.96 m, M)"
    assert tsv.time == HecTime("2024-10-14T12:00:00")
    assert tsv.value == UQ(3.96, "m")
    assert (
        tsv.quality.text
        == "Screened Missing No_Range Original None None None Protected"
    )


def test_create_time_series_by_name() -> None:
    ts = TimeSeries("SWT/Keystone.Elev-Pool.Inst.1Hour.0.Raw-Goes")
    assert ts.name == "Keystone.Elev-Pool.Inst.1Hour.0.Raw-Goes"
    assert ts.location.office == "SWT"
    assert ts.location.name == "Keystone"
    assert ts.parameter.name == "Elev-Pool"
    assert ts.unit == "ft"
    assert ts.interval.name == "1Hour"
    assert cast(Duration, ts.duration).name == "0"
    assert ts.version == "Raw-Goes"
    assert ts.vertical_datum_info is None
    ts = TimeSeries("//KEYS/ELEV-POOL//1HOUR/OBS/")
    assert ts.name == "//KEYS/ELEV-POOL//1Hour/OBS/"
    assert ts.location.office is None
    assert ts.location.name == "KEYS"
    assert ts.parameter.name == "ELEV-POOL"
    assert ts.unit == "ft"
    assert ts.interval.name == "1Hour"
    assert ts.duration == None
    assert ts.version == "OBS"
    assert ts.vertical_datum_info is None


def test_math_ops_scalar() -> None:
    assert Parameter("Flow").to("EN").unit_name == "cfs"
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    value_count = 24
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    area = TimeSeries(f"Loc1.Area-Xsec.Inst.{intvl.name}.0.Raw-Goes")
    assert area.unit == "ft2"
    area._data = pd.DataFrame(
        {"value": value_count * [10.0], "quality": value_count * [0]}, index=times
    )
    # ---------------- #
    # unitless scalars #
    # ---------------- #
    area2 = area + 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 + 3])
    area2 = area - 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 - 3])
    area2 = area * 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 * 3])
    area2 = area / 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 / 3])
    area2 = area // 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 // 3])
    area2 = area % 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 % 3])
    area2 = area**3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0**3])

    area2 = area.copy()
    area2 += 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 + 3])
    area2 = area.copy()
    area2 -= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 - 3])
    area2 = area.copy()
    area2 *= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 * 3])
    area2 = area.copy()
    area2 /= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 / 3])
    area2 = area.copy()
    area2 //= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 // 3])
    area2 = area.copy()
    area2 %= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 % 3])
    area2 = area.copy()
    area2 **= 3
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0**3])
    # -------------------------------- #
    # scalars with dimensionless units #
    # -------------------------------- #
    scalar = UQ(3, "n/a")
    area2 = area + scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 + 3])
    area2 = area - scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 - 3])
    area2 = area * scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 * 3])
    area2 = area / scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 / 3])
    area2 = area // scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 // 3])
    area2 = area % scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 % 3])
    area2 = area**scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0**3])

    area2 = area.copy()
    area2 += scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 + 3])
    area2 = area.copy()
    area2 -= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 - 3])
    area2 = area.copy()
    area2 *= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 * 3])
    area2 = area.copy()
    area2 /= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 / 3])
    area2 = area.copy()
    area2 //= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 // 3])
    area2 = area.copy()
    area2 %= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0 % 3])
    area2 = area.copy()
    area2 **= scalar
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10.0**3])
    # ------------------------------------ #
    # scalars with non-dimensionless units #
    # ------------------------------------ #
    speed = UQ(4, "mph")
    flow = (area * speed).to("Flow")
    assert flow.name == area.name.replace(area.parameter.name, "Flow")
    assert flow.unit == "cfs"
    assert np.allclose(flow.values, value_count * [58.66666666666667])
    speed2 = (flow / UQ(10, "ft2")).to("Speed-Water")
    assert speed2.name == flow.name.replace("Flow", "Speed-Water")
    assert np.allclose(speed2.values, value_count * [4.0])
    area2 = (flow / speed.to("ft/s")).to("Area-Xsec")
    assert area2.name == flow.name.replace("Flow", "Area-Xsec")
    assert np.allclose(area2.values, value_count * [10.0])


def test_math_ops_ts() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    value_count = 24
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    area = TimeSeries(f"Loc1.Area-Xsec.Inst.{intvl.name}.0.Raw-Goes")
    assert area.unit == "ft2"
    area._data = pd.DataFrame(
        {"value": value_count * [10.0], "quality": value_count * [0]}, index=times
    )
    other_ts = TimeSeries(f"Loc1.Code-Modifier.Inst.{intvl.name}.0.Test")
    assert other_ts.unit == "n/a"
    other_ts._data = pd.DataFrame(
        {"value": value_count * [3.0], "quality": value_count * [0]}, index=times
    )
    # ------------------------------------ #
    # time series with dimensionless units #
    # ------------------------------------ #
    area2 = area + other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 + 3])
    area2 = area - other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 - 3])
    area2 = area * other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 * 3])
    area2 = area / other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 / 3])
    area2 = area // other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 // 3])
    area2 = area % other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 % 3])
    area2 = area**other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10**3])

    area2 = area.copy()
    area2 += other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 + 3])
    area2 = area.copy()
    area2 -= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 - 3])
    area2 = area.copy()
    area2 *= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 * 3])
    area2 = area.copy()
    area2 /= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 / 3])
    area2 = area.copy()
    area2 //= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 // 3])
    area2 = area.copy()
    area2 %= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10 % 3])
    area2 = area.copy()
    area2 **= other_ts
    assert area2.name == area.name
    assert np.allclose(area2.values, value_count * [10**3])
    # ---------------------------------------- #
    # time series with non-dimensionless units #
    # ---------------------------------------- #
    speed = TimeSeries(f"Loc1.Speed-Water.Inst.{intvl.name}.0.Raw-Goes")
    speed._data = pd.DataFrame(
        {"value": [3.0 + i for i in range(value_count)], "quality": value_count * [0]},
        index=times,
    )
    flow = (area * speed).to("Flow")
    assert flow.name == area.name.replace(area.parameter.name, "Flow")
    assert flow.unit == "cfs"
    assert flow.values == np.multiply(area.values, speed.to("ft/s").values).tolist()
    speed2 = (flow / area).to("Speed-Water")
    assert speed2.name == speed.name
    assert np.allclose(speed2.values, speed.values)
    try:
        area2 = (flow / speed).to("Area-Xsec")
        had_exception = False
    except TimeSeriesException as e:
        had_exception = True
        assert str(e).find("Cannot automtically determine conversion") != -1
    assert had_exception
    area2 = (flow / speed.to("ft/s")).to("Area-Xsec")
    assert area2.name == area.name
    assert np.allclose(area.values, area2.values)


def test_selection_and_filter() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_dss("1Hour")
    value_count = 24
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    flow = TimeSeries(f"//Loc1/Flow//{intvl.name}/Computed/")
    flow._data = pd.DataFrame(
        {"value": 6 * [100, 125, 112, -100], "quality": value_count * [0]},
        index=times,
    )
    flow2 = flow.select(lambda tsv: tsv.value < 0)
    flow3 = flow2.filter()
    assert flow3.times == [
        flow2.times[i] for i in range(len(flow2)) if flow2.values[i] < 0
    ]
    assert flow3.values == [v for v in flow2.values if v < 0]
    assert flow3.qualities == [
        flow2.qualities[i] for i in range(len(flow2)) if flow2.values[i] < 0
    ]
    flow2 = flow.select(lambda tsv: tsv.value < 0)
    flow3 = flow2.copy().ifilter(unselected=True)
    assert flow3.times == [
        flow2.times[i] for i in range(len(flow2)) if not flow2.values[i] < 0
    ]
    assert flow3.values == [v for v in flow2.values if not v < 0]
    assert flow3.qualities == [
        flow2.qualities[i] for i in range(len(flow2)) if not flow2.values[i] < 0
    ]
    assert flow2.has_selection
    assert flow2.selected == 6 * [False, False, False, True]
    flow2.iset_value_quality(
        math.nan, Qual(0).set_screened("SCREENED").set_validity("MISSING")
    )
    assert not flow2.has_selection
    assert np.nan_to_num(flow2.values, nan=-1).tolist() == 6 * [100.0, 125.0, 112.0, -1]
    assert flow2.qualities == 6 * [0, 0, 0, 5]
    flow2.selection_state = SelectionState.DURABLE
    flow2.iselect(lambda tsv: tsv.value > 120)
    assert flow2.has_selection
    assert flow2.selected == 6 * [False, True, False, False]
    flow2 -= 5
    assert flow2.has_selection
    assert flow2.selected == 6 * [False, True, False, False]
    assert np.nan_to_num(flow2.values, nan=-1).tolist() == 6 * [100.0, 120.0, 112.0, -1]
    flow2.iselect(Select.INVERT)
    assert flow2.selected == 6 * [True, False, True, True]
    flow2.iselect(Select.ALL)
    assert not flow2.has_selection
    assert flow2.selection_state == SelectionState.DURABLE
    flow2.selection_state = SelectionState.TRANSIENT
    assert flow2.selection_state == SelectionState.TRANSIENT


def test_aggregate_ts() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    value_count = 24
    ts_count = 10
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    timeseries = []
    for i in range(ts_count - 2):
        ts = TimeSeries(f"Loc{i+1}.Flow.Inst.{intvl.name}.0.Computed")
        ts._data = pd.DataFrame(
            {
                "value": [(1000 + i * 10) + j * 15 for j in range(value_count)],
                "quality": value_count * [0],
            },
            index=times,
        )
        timeseries.append(ts)
        if i in (3, 7):
            timeseries.append(ts)
    cast(pd.DataFrame, timeseries[0]._data).loc[
        "2024-10-10 01:00:00", "value"
    ] = math.nan
    test_rows = [
        [timeseries[i].values[j] for i in range(ts_count)] for j in range(value_count)
    ]
    # ----------- #
    # builtin all #
    # ----------- #
    ts = TimeSeries.aggregate_ts(all, timeseries)
    for i in range(value_count):
        assert ts.values[i] == all(test_rows[i])
    # ----------- #
    # builtin any #
    # ----------- #
    ts = TimeSeries.aggregate_ts(any, timeseries)
    for i in range(value_count):
        assert ts.values[i] == any(test_rows[i])
    # ----------- #
    # builtin len #
    # ----------- #
    ts = TimeSeries.aggregate_ts(len, timeseries)
    for i in range(value_count):
        assert ts.values[i] == len(test_rows[i])
    # ----------- #
    # builtin max # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        ts = TimeSeries.aggregate_ts(max, timeseries)
        for i in range(value_count):
            assert ts.values[i] == max([v for v in test_rows[i] if not math.isnan(v)])
    # ----------- #
    # builtin min # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        ts = TimeSeries.aggregate_ts(min, timeseries)
        for i in range(value_count):
            assert ts.values[i] == min([v for v in test_rows[i] if not math.isnan(v)])
    # ----------- #
    # builtin sum # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        ts = TimeSeries.aggregate_ts(sum, timeseries)
        for i in range(value_count):
            assert ts.values[i] == sum([v for v in test_rows[i] if not math.isnan(v)])
    # --------- #
    # math.prod #
    # --------- #
    ts = TimeSeries.aggregate_ts(math.prod, timeseries)
    for i in range(value_count):
        assert ts.values[i] == math.prod(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(math.prod(test_rows[i]))
        )
    # ---------------- #
    # statistics.fmean #
    # ---------------- #
    ts = TimeSeries.aggregate_ts(stat.fmean, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.fmean(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.fmean(test_rows[i]))
        )
    # ------------------------- #
    # statistics.geometric_mean #
    # ------------------------- #
    ts = TimeSeries.aggregate_ts(stat.geometric_mean, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.geometric_mean(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.geometric_mean(test_rows[i]))
        )
    # ------------------------ #
    # statistics.harmonic_mean #
    # ------------------------ #
    ts = TimeSeries.aggregate_ts(stat.harmonic_mean, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.harmonic_mean(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.harmonic_mean(test_rows[i]))
        )
    # --------------- #
    # statistics.mean #
    # --------------- #
    ts = TimeSeries.aggregate_ts(stat.mean, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.mean(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.mean(test_rows[i]))
        )
    # ----------------- #
    # statistics.median #
    # ----------------- #
    ts = TimeSeries.aggregate_ts(stat.median, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.median(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.median(test_rows[i]))
        )
    # ------------------------- #
    # statistics.median_grouped #
    # ------------------------- #
    ts = TimeSeries.aggregate_ts(stat.median_grouped, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.median_grouped(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.median_grouped(test_rows[i]))
        )
    # ---------------------- #
    # statistics.median_high #
    # ---------------------- #
    ts = TimeSeries.aggregate_ts(stat.median_high, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.median_high(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.median_high(test_rows[i]))
        )
    # --------------------- #
    # statistics.median_low #
    # --------------------- #
    ts = TimeSeries.aggregate_ts(stat.median_low, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.median_low(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.median_low(test_rows[i]))
        )
    # --------------- #
    # statistics.mode #
    # --------------- #
    ts = TimeSeries.aggregate_ts(stat.mode, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.mode(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.mode(test_rows[i]))
        )
    # -------------------- #
    # statistics.multimode # generates non-standard TimeSeries
    # -------------------- #
    ts = TimeSeries.aggregate_ts(stat.multimode, timeseries)
    for i in range(value_count):
        assert cast(list[float], ts.values[i]) == stat.multimode(test_rows[i])
    # ----------------- #
    # statistics.pstdev #
    # ----------------- #
    ts = TimeSeries.aggregate_ts(stat.pstdev, timeseries)
    for i in range(value_count):
        assert np.isclose(
            ts.values[i],
            (
                stat.pstdev(test_rows[i])
                if all([np.isfinite(v) for v in test_rows[i]])
                else np.nan
            ),
            equal_nan=True,
        )
    # -------------------- #
    # statistics.pvariance #
    # -------------------- #
    ts = TimeSeries.aggregate_ts(stat.pvariance, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.pvariance(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.pvariance(test_rows[i]))
        )
    # -------------------- #
    # statistics.quantiles # generates non-standard TimeSeries
    # -------------------- #
    ts = TimeSeries.aggregate_ts(stat.quantiles, timeseries)
    for i in range(value_count):
        assert cast(list[float], ts.values[i]) == stat.quantiles(test_rows[i])
    # ------------------- #
    # statistics.variance #
    # ------------------- #
    ts = TimeSeries.aggregate_ts(stat.variance, timeseries)
    for i in range(value_count):
        assert ts.values[i] == stat.variance(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(stat.variance(test_rows[i]))
        )
    # ----- #
    # "all" #
    # ----- #
    ts = TimeSeries.aggregate_ts("all", timeseries)
    for i in range(value_count):
        assert ts.values[i] == all(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(all(test_rows[i]))
        )
    # ----- #
    # "any" #
    # ----- #
    ts = TimeSeries.aggregate_ts("any", timeseries)
    for i in range(value_count):
        assert ts.values[i] == any(test_rows[i]) or (
            math.isnan(ts.values[i]) and math.isnan(any(test_rows[i]))
        )
    # ------- #
    # "count" #
    # ------- #
    ts = TimeSeries.aggregate_ts("count", timeseries)
    for i in range(value_count):
        assert ts.values[i] == len(test_rows[i]) - len(
            [v for v in test_rows[i] if math.isnan(v)]
        )
    # ---------- #
    # "describe" #
    # ---------- #
    ts = TimeSeries.aggregate_ts("describe", timeseries)
    df = cast(pd.DataFrame, ts.data)["value"]
    p25s = []
    p50s = []
    p75s = []
    for i in range(value_count):
        p25, p50, p75 = stat.quantiles(
            [v for v in test_rows[i] if not math.isnan(v)], n=4, method="inclusive"
        )
        p25s.append(p25)
        p50s.append(p50)
        p75s.append(p75)
        assert df.loc[times[i], "count"] == len(test_rows[i]) - len(
            [v for v in test_rows[i] if math.isnan(v)]
        )
        assert df.loc[times[i], "mean"] == stat.mean(
            [v for v in test_rows[i] if not math.isnan(v)]
        )
        assert df.loc[times[i], "std"] == stat.stdev(
            [v for v in test_rows[i] if not math.isnan(v)]
        )
        assert df.loc[times[i], "25%"] == p25
        assert df.loc[times[i], "50%"] == p50
        assert df.loc[times[i], "75%"] == p75
        assert df.loc[times[i], "min"] == min(
            [v for v in test_rows[i] if not math.isnan(v)]
        )
        assert df.loc[times[i], "max"] == max(
            [v for v in test_rows[i] if not math.isnan(v)]
        )
    # ---- #
    # fmod #
    # ---- #
    ts = TimeSeries.aggregate_ts(
        lambda i: math.fmod(i.iloc[0], i.iloc[1]),
        [timeseries[ts_count - 1], timeseries[0]],
    )
    for i in range(value_count):
        expected = math.fmod(
            timeseries[ts_count - 1].values[i], timeseries[0].values[i]
        )
        assert (
            math.isnan(ts.values[i])
            and math.isnan(expected)
            or ts.values[i] == expected
        )
    # --- #
    # rms #
    # --- #
    ts = TimeSeries.aggregate_ts(
        lambda s: np.sqrt(np.mean(np.array(s) ** 2)), timeseries
    )
    for i in range(value_count):
        expected = math.sqrt(stat.mean([v**2 for v in test_rows[i]]))
        assert (
            math.isnan(ts.values[i])
            and math.isnan(expected)
            or ts.values[i] == expected
        )
    # ----------- #
    # percentiles #
    # ----------- #
    pct = {}
    for ts in timeseries:
        ts.selection_state = SelectionState.DURABLE
        ts.iselect(lambda tsv: not math.isnan(tsv.value))
    for p in (1, 2, 5, 10, 20, 25, 50, 75, 80, 90, 95, 98, 99):
        pct[p] = TimeSeries.percentile_ts(p, timeseries)
    ts.selection_state = SelectionState.TRANSIENT
    ts.iselect(Select.ALL)
    pvals = sorted(pct)
    for i in range(1, len(pvals)):
        for j in range(value_count):
            assert pct[pvals[i]].values[j] >= pct[pvals[i - 1]].values[j]
    assert pct[25].values == p25s
    assert pct[50].values == p50s
    assert pct[75].values == p75s
    for ts in timeseries:
        ts.selection_state = SelectionState.TRANSIENT
        ts.iselect(Select.ALL)


def test_aggregate_values() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        1075,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        1285,
        1300,
        1315,
        1330,
        1345,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    # ----------- #
    # builtin all #
    # ----------- #
    assert ts.aggregate(all) == all(values)
    # ----------- #
    # builtin any #
    # ----------- #
    assert ts.aggregate(any) == any(values)
    # ----------- #
    # builtin len #
    # ----------- #
    assert ts.aggregate(len) == len(values)
    # ----------- #
    # builtin max # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        assert ts.aggregate(max) == max([v for v in values if not math.isnan(v)])
    # ----------- #
    # builtin min # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        assert ts.aggregate(min) == min([v for v in values if not math.isnan(v)])
    # ----------- #
    # builtin sum # generates warning
    # ----------- #
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
        assert ts.aggregate(sum) == sum([v for v in values if not math.isnan(v)])
    # --------- #
    # math.prod #
    # --------- #
    assert math.isnan(ts.aggregate(math.prod))
    ts2 = ts / 1000.0
    ts2.iselect(lambda tsv: not math.isnan(tsv.value))
    assert ts2.aggregate(math.prod) == math.prod(
        [v / 1000.0 for v in values if not math.isnan(v)]
    )
    # ---------------- #
    # statistics.fmean #
    # ---------------- #
    assert ts.aggregate(stat.fmean) == stat.fmean(values) or (
        math.isnan(ts.aggregate(stat.fmean)) and math.isnan(stat.fmean(values))
    )
    # ------------------------- #
    # statistics.geometric_mean #
    # ------------------------- #
    assert ts.aggregate(stat.geometric_mean) == stat.geometric_mean(values) or (
        math.isnan(ts.aggregate(stat.geometric_mean))
        and math.isnan(stat.geometric_mean(values))
    )
    # ------------------------ #
    # statistics.harmonic_mean #
    # ------------------------ #
    assert ts.aggregate(stat.harmonic_mean) == stat.harmonic_mean(values) or (
        math.isnan(ts.aggregate(stat.harmonic_mean))
        and math.isnan(stat.harmonic_mean(values))
    )
    # --------------- #
    # statistics.mean #
    # --------------- #
    assert ts.aggregate(stat.mean) == stat.mean(values) or (
        math.isnan(ts.aggregate(stat.mean)) and math.isnan(stat.mean(values))
    )
    # ----------------- #
    # statistics.median #
    # ----------------- #
    assert ts.aggregate(stat.median) == stat.median(values) or (
        math.isnan(ts.aggregate(stat.median)) and math.isnan(stat.median(values))
    )
    # ------------------------- #
    # statistics.median_grouped #
    # ------------------------- #
    assert ts.aggregate(stat.median_grouped) == stat.median_grouped(values) or (
        math.isnan(ts.aggregate(stat.median_grouped))
        and math.isnan(stat.median_grouped(values))
    )
    # ---------------------- #
    # statistics.median_high #
    # ---------------------- #
    assert ts.aggregate(stat.median_high) == stat.median_high(values) or (
        math.isnan(ts.aggregate(stat.median_high))
        and math.isnan(stat.median_high(values))
    )
    # --------------------- #
    # statistics.median_low #
    # --------------------- #
    assert ts.aggregate(stat.median_low) == stat.median_low(values) or (
        math.isnan(ts.aggregate(stat.median_low))
        and math.isnan(stat.median_low(values))
    )
    # --------------- #
    # statistics.mode #
    # --------------- #
    assert ts.aggregate(stat.mode) == stat.mode(values) or (
        math.isnan(ts.aggregate(stat.mode)) and math.isnan(stat.mode(values))
    )
    # -------------------- #
    # statistics.multimode #
    # -------------------- #
    assert ts.aggregate(stat.multimode) == stat.multimode(values)
    # ----------------- #
    # statistics.pstdev #
    # ----------------- #
    assert np.isclose(
        ts.aggregate(stat.pstdev),
        stat.pstdev(values) if all([np.isfinite(v) for v in values]) else np.nan,
        equal_nan=True,
    )
    # -------------------- #
    # statistics.pvariance #
    # -------------------- #
    assert ts.aggregate(stat.pvariance) == stat.pvariance(values) or (
        math.isnan(ts.aggregate(stat.pvariance)) and math.isnan(stat.pvariance(values))
    )
    # -------------------- #
    # statistics.quantiles #
    # -------------------- #
    assert ts.aggregate(stat.quantiles) == stat.quantiles(values)
    # ---------------- #
    # statistics.stdev #
    # ---------------- #
    assert np.isclose(
        ts.aggregate(stat.stdev),
        stat.stdev(values) if all([np.isfinite(v) for v in values]) else np.nan,
        equal_nan=True,
    )
    # ------------------- #
    # statistics.variance #
    # ------------------- #
    assert ts.aggregate(stat.variance) == stat.variance(values) or (
        math.isnan(ts.aggregate(stat.variance)) and math.isnan(stat.variance(values))
    )
    # ----- #
    # "all" #
    # ----- #
    assert ts.aggregate("all") == all([v for v in values if not math.isnan(v)])
    # ----- #
    # "any" #
    # ----- #
    assert ts.aggregate("any") == any([v for v in values if not math.isnan(v)])
    # ------- #
    # "count" #
    # ------- #
    assert ts.aggregate("count") == len([v for v in values if not math.isnan(v)])
    # ---------- #
    # "describe" #
    # ---------- #
    df = ts.aggregate("describe")
    p25, p50, p75 = stat.quantiles(
        [v for v in values if not math.isnan(v)], n=4, method="inclusive"
    )
    assert df["count"] == len(values) - len([v for v in values if math.isnan(v)])
    assert df["mean"] == stat.mean([v for v in values if not math.isnan(v)])
    assert df["std"] == stat.stdev([v for v in values if not math.isnan(v)])
    assert df["min"] == min([v for v in values if not math.isnan(v)])
    assert df["25%"] == p25
    assert df["50%"] == p50
    assert df["75%"] == p75
    assert df["max"] == max([v for v in values if not math.isnan(v)])
    # -------- #
    # kurtosis #
    # -------- #
    assert abs(ts.kurtosis() - -1.284) < 0.05
    # ----------- #
    # percentiles #
    # ----------- #
    pct = {}
    ts.selection_state = SelectionState.DURABLE
    ts.iselect(lambda tsv: not math.isnan(tsv.value))
    for p in (1, 2, 5, 10, 20, 25, 50, 75, 80, 90, 95, 98, 99):
        pct[p] = ts.percentile(p)
    ts.selection_state = SelectionState.TRANSIENT
    ts.iselect(Select.ALL)
    pvals = sorted(pct)
    for i in range(1, len(pvals)):
        assert pct[pvals[i]] >= pct[pvals[i - 1]]
    assert pct[25] == p25
    assert pct[50] == p50
    assert pct[75] == p75


def test_min_max() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    value_count = 24
    values = [10.0 + i for i in range(value_count)]
    values[3] = math.nan
    values[2] = values[8] = -1.0
    values[5] = values[9] = 1000.0
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Code.Inst.{intvl.name}.0.Raw-Goes")
    ts._data = pd.DataFrame(
        {"value": values, "quality": value_count * [0]}, index=times
    )
    assert ts.min_value() == -1.0
    assert ts.max_value() == 1000.0
    assert ts.min_value_time() == start_time + 2 * TimeSpan(intvl.values)
    assert ts.max_value_time() == start_time + 5 * TimeSpan(intvl.values)
    ts.selection_state = SelectionState.DURABLE
    ts.iselect(lambda tsv: 10 < tsv.value < 100)
    assert ts.min_value() == 11.0
    assert ts.max_value() == 33.0
    assert ts.min_value_time() == start_time + TimeSpan(intvl.values)
    assert ts.max_value_time() == start_time + 23 * TimeSpan(intvl.values)


def test_accum_diff() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    # Col 1 = starting values (made up)
    # Col 2 = from TimeSeriesMath.accumualtion() using col 1
    # Col 3 = from TimeSeriesMath.successiveDiffereneces using col 2(except for first value)
    data = [
        [10.0, 10.0, math.nan],
        [11.0, 21.0, 11.0],
        [-1.0, 20.0, -1.0],
        [math.nan, 20.0, 0.0],
        [14.0, 34.0, 14.0],
        [1000.0, 1034.0, 1000.0],
        [16.0, 1050.0, 16.0],
        [17.0, 1067.0, 17.0],
        [-1.0, 1066.0, -1.0],
        [1000.0, 2066.0, 1000.0],
        [20.0, 2086.0, 20.0],
        [21.0, 2107.0, 21.0],
        [22.0, 2129.0, 22.0],
        [23.0, 2152.0, 23.0],
        [24.0, 2176.0, 24.0],
        [25.0, 2201.0, 25.0],
        [26.0, 2227.0, 26.0],
        [27.0, 2254.0, 27.0],
        [28.0, 2282.0, 28.0],
        [29.0, 2311.0, 29.0],
        [30.0, 2341.0, 30.0],
        [31.0, 2372.0, 31.0],
        [32.0, 2404.0, 32.0],
        [33.0, 2437.0, 33.0],
    ]
    value_count = len(data)
    values, accum, diffs = map(list, zip(*data))
    diffs = diffs[1:]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(value_count)
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Code.Inst.{intvl.name}.0.Raw-Goes")
    ts._data = pd.DataFrame(
        {"value": values, "quality": value_count * [0]}, index=times
    )
    try:
        ts_accum = ts.accum()
    except TimeSeriesException as tse:
        assert (
            str(tse).find("Cannot accumulate a time series with parameter of Code")
            != -1
        )
    else:
        raise Exception("Expected exception not raised")
    ts.iset_parameter("Count")
    ts_accum = ts.accum()
    assert ts_accum.values == accum
    ts_accum.iset_parameter("Code")
    try:
        ts_diffs = ts_accum.diff()
    except TimeSeriesException as tse:
        assert (
            str(tse).find(
                "Cannot compute differences on a time series with parameter of Code"
            )
            != -1
        )
    else:
        raise Exception("Expected exception not raised")
    ts_accum.iset_parameter("Count")
    ts_diffs = ts_accum.diff()
    assert ts_diffs.values == diffs
    try:
        ts_time_diffs = ts_accum.time_derivative()
    except TimeSeriesException as tse:
        assert (
            str(tse).find(
                "Cannot compute derivative on a time series with parameter of Count"
            )
            != -1
        )
    else:
        raise Exception("Expected exception not raised")
    for base_param in Parameter.differentiable_base_parameters():
        info = Parameter.differentiation_info(base_param)
        for unit_system in ("EN", "SI"):
            bp = Parameter(base_param, unit_system)
            new_bp = Parameter(info["base_parameter"], unit_system)
            factor = info[unit_system]
            ts_accum.iset_parameter(bp)
            ts_time_diffs = ts_accum.time_derivative()
            expected_vals = list(
                map(lambda x: x * factor / ts_accum.interval.total_seconds(), diffs)
            )
            assert ts_time_diffs.parameter.name == new_bp.name
            assert ts_time_diffs.unit == new_bp.unit_name
            assert np.allclose(expected_vals, ts_time_diffs.values, equal_nan=True)

    accum[10] = math.nan
    diffs[9] = diffs[10] = math.nan
    ts._data = pd.DataFrame({"value": accum, "quality": value_count * [0]}, index=times)
    vals = ts.diff().values
    assert len(vals) == len(diffs)
    assert np.allclose(vals, diffs, equal_nan=True)


def test_value_counts() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        math.inf,
        1300,
        1315,
        1330,
        1345,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    ts._data.loc[ts.index_of(0), "quality"] = Qual("Rejected").code
    ts._data.loc[ts.index_of(1), "quality"] = Qual("Missing").code
    ts._data.loc[ts.index_of(2), "quality"] = Qual("Questionable").code
    # --------------#
    # no selection #
    # --------------#
    assert ts.number_values == len(values)
    assert ts.number_invalid_values == 5
    assert ts.number_valid_values == len(values) - 5
    assert ts.number_missing_values == 2
    assert ts.number_questioned_values == 1
    assert ts.number_rejected_values == 1
    assert ts.first_valid_value == 1030
    assert HecTime("2024-10-10T03:00:00") == ts.first_valid_time
    assert ts.last_valid_value == 1345
    assert HecTime("2024-10-10T24:00:00") == ts.last_valid_time
    # ----------------#
    # with selection #
    # ----------------#
    ts2 = ts.select(
        lambda tsv: HecTime("2024-10-10T11:00:00")
        <= tsv.time
        <= HecTime("2024-10-10T20:00:00"),
    )
    ts2.selection_state = SelectionState.DURABLE
    assert ts2.number_values == 10
    assert ts2.number_invalid_values == 2
    assert ts2.number_valid_values == 8
    assert ts2.number_missing_values == 1
    assert ts2.number_questioned_values == 0
    assert ts2.number_rejected_values == 0
    assert ts2.first_valid_value == 1165
    assert HecTime("2024-10-10T12:00:00") == ts2.first_valid_time
    assert ts2.last_valid_value == 1270
    assert HecTime("2024-10-10T19:00:00") == ts2.last_valid_time


def test_unit() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        math.inf,
        1300,
        1315,
        1330,
        1345,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    assert ts.is_english
    assert not ts.is_metric
    assert ts.can_determine_unit_system
    assert ts.parameter.unit_name == "cfs"
    assert ts.parameter.to("EN").unit_name == "cfs"
    assert ts.parameter.to("SI").unit_name == "cms"


def test_roundoff() -> None:
    data = [
        #       value  prec,  mgntude,       result
        [12345.678912, 1, -5, 10000.0],
        [12345.678912, 1, -4, 10000.0],
        [12345.678912, 1, -3, 10000.0],
        [12345.678912, 1, -2, 10000.0],
        [12345.678912, 1, -1, 10000.0],
        [12345.678912, 1, 0, 10000.0],
        [12345.678912, 1, 1, 10000.0],
        [12345.678912, 1, 2, 10000.0],
        [12345.678912, 1, 3, 10000.0],
        [12345.678912, 1, 4, 10000.0],
        [12345.678912, 1, 5, 0.0],
        [12345.678912, 2, -5, 12000.0],
        [12345.678912, 2, -4, 12000.0],
        [12345.678912, 2, -3, 12000.0],
        [12345.678912, 2, -2, 12000.0],
        [12345.678912, 2, -1, 12000.0],
        [12345.678912, 2, 0, 12000.0],
        [12345.678912, 2, 1, 12000.0],
        [12345.678912, 2, 2, 12000.0],
        [12345.678912, 2, 3, 12000.0],
        [12345.678912, 2, 4, 10000.0],
        [12345.678912, 2, 5, 0.0],
        [12345.678912, 3, -5, 12300.0],
        [12345.678912, 3, -4, 12300.0],
        [12345.678912, 3, -3, 12300.0],
        [12345.678912, 3, -2, 12300.0],
        [12345.678912, 3, -1, 12300.0],
        [12345.678912, 3, 0, 12300.0],
        [12345.678912, 3, 1, 12300.0],
        [12345.678912, 3, 2, 12300.0],
        [12345.678912, 3, 3, 12000.0],
        [12345.678912, 3, 4, 10000.0],
        [12345.678912, 3, 5, 0.0],
        [12345.678912, 4, -5, 12350.0],
        [12345.678912, 4, -4, 12350.0],
        [12345.678912, 4, -3, 12350.0],
        [12345.678912, 4, -2, 12350.0],
        [12345.678912, 4, -1, 12350.0],
        [12345.678912, 4, 0, 12350.0],
        [12345.678912, 4, 1, 12350.0],
        [12345.678912, 4, 2, 12300.0],
        [12345.678912, 4, 3, 12000.0],
        [12345.678912, 4, 4, 10000.0],
        [12345.678912, 4, 5, 0.0],
        [12345.678912, 5, -5, 12346.0],
        [12345.678912, 5, -4, 12346.0],
        [12345.678912, 5, -3, 12346.0],
        [12345.678912, 5, -2, 12346.0],
        [12345.678912, 5, -1, 12346.0],
        [12345.678912, 5, 0, 12346.0],
        [12345.678912, 5, 1, 12350.0],
        [12345.678912, 5, 2, 12300.0],
        [12345.678912, 5, 3, 12000.0],
        [12345.678912, 5, 4, 10000.0],
        [12345.678912, 5, 5, 0.0],
        [12345.678912, 6, -5, 12345.7],
        [12345.678912, 6, -4, 12345.7],
        [12345.678912, 6, -3, 12345.7],
        [12345.678912, 6, -2, 12345.7],
        [12345.678912, 6, -1, 12345.7],
        [12345.678912, 6, 0, 12346.0],
        [12345.678912, 6, 1, 12350.0],
        [12345.678912, 6, 2, 12300.0],
        [12345.678912, 6, 3, 12000.0],
        [12345.678912, 6, 4, 10000.0],
        [12345.678912, 6, 5, 0.0],
        [12345.678912, 7, -5, 12345.68],
        [12345.678912, 7, -4, 12345.68],
        [12345.678912, 7, -3, 12345.68],
        [12345.678912, 7, -2, 12345.68],
        [12345.678912, 7, -1, 12345.7],
        [12345.678912, 7, 0, 12346.0],
        [12345.678912, 7, 1, 12350.0],
        [12345.678912, 7, 2, 12300.0],
        [12345.678912, 7, 3, 12000.0],
        [12345.678912, 7, 4, 10000.0],
        [12345.678912, 7, 5, 0.0],
        [12345.678912, 8, -5, 12345.679],
        [12345.678912, 8, -4, 12345.679],
        [12345.678912, 8, -3, 12345.679],
        [12345.678912, 8, -2, 12345.68],
        [12345.678912, 8, -1, 12345.7],
        [12345.678912, 8, 0, 12346.0],
        [12345.678912, 8, 1, 12350.0],
        [12345.678912, 8, 2, 12300.0],
        [12345.678912, 8, 3, 12000.0],
        [12345.678912, 8, 4, 10000.0],
        [12345.678912, 8, 5, 0.0],
        [12345.678912, 9, -5, 12345.6789],
        [12345.678912, 9, -4, 12345.6789],
        [12345.678912, 9, -3, 12345.679],
        [12345.678912, 9, -2, 12345.68],
        [12345.678912, 9, -1, 12345.7],
        [12345.678912, 9, 0, 12346.0],
        [12345.678912, 9, 1, 12350.0],
        [12345.678912, 9, 2, 12300.0],
        [12345.678912, 9, 3, 12000.0],
        [12345.678912, 9, 4, 10000.0],
        [12345.678912, 9, 5, 0.0],
        [12345.678912, 10, -5, 12345.67891],
        [12345.678912, 10, -4, 12345.6789],
        [12345.678912, 10, -3, 12345.679],
        [12345.678912, 10, -2, 12345.68],
        [12345.678912, 10, -1, 12345.7],
        [12345.678912, 10, 0, 12346.0],
        [12345.678912, 10, 1, 12350.0],
        [12345.678912, 10, 2, 12300.0],
        [12345.678912, 10, 3, 12000.0],
        [12345.678912, 10, 4, 10000.0],
        [12345.678912, 10, 5, 0.0],
        [12345.678912, 11, -5, 12345.67891],
        [12345.678912, 11, -4, 12345.6789],
        [12345.678912, 11, -3, 12345.679],
        [12345.678912, 11, -2, 12345.68],
        [12345.678912, 11, -1, 12345.7],
        [12345.678912, 11, 0, 12346.0],
        [12345.678912, 11, 1, 12350.0],
        [12345.678912, 11, 2, 12300.0],
        [12345.678912, 11, 3, 12000.0],
        [12345.678912, 11, 4, 10000.0],
        [12345.678912, 11, 5, 0.0],
        [12345.678912, 12, -5, 12345.67891],
        [12345.678912, 12, -4, 12345.6789],
        [12345.678912, 12, -3, 12345.679],
        [12345.678912, 12, -2, 12345.68],
        [12345.678912, 12, -1, 12345.7],
        [12345.678912, 12, 0, 12346.0],
        [12345.678912, 12, 1, 12350.0],
        [12345.678912, 12, 2, 12300.0],
        [12345.678912, 12, 3, 12000.0],
        [12345.678912, 12, 4, 10000.0],
        [12345.678912, 12, 5, 0.0],
    ]

    for value, precsion, magnitude, result in data:
        assert TimeSeries._round_off(value, int(precsion), int(magnitude)) == result
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000.123,
        1015.123,
        1030.123,
        1045.123,
        1060.123,
        1075.123,
        1090.123,
        1090.123,
        1120.123,
        1135.123,
        1150.123,
        1165.123,
        1180.123,
        1195.123,
        1210.123,
        1225.123,
        1240.123,
        1240.123,
        1270.123,
        1285.123,
        1300.123,
        1315.123,
        1330.123,
        1345.123,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    assert ts.round_off(4, 0).values == list(
        map(lambda v: TimeSeries._round_off(v, 4, 0), values)
    )
    assert ts.round_off(5, -1).values == list(
        map(lambda v: TimeSeries._round_off(v, 5, -1), values)
    )


def test_smoothing() -> None:
    with open(
        os.path.join(
            os.path.dirname(__file__), "resources", "timeseries", "smoothing.txt"
        )
    ) as f:
        data = eval(f.read())
    values = [data[i][0] for i in range(len(data))]
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    assert equal_values(
        ts.forward_moving_average(window=3, only_valid=False, use_reduced=False).values,
        [data[i][1] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=3, only_valid=False, use_reduced=True).values,
        [data[i][4] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=3, only_valid=True, use_reduced=False).values,
        [data[i][7] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=3, only_valid=True, use_reduced=True).values,
        [data[i][10] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=5, only_valid=False, use_reduced=False).values,
        [data[i][13] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=5, only_valid=False, use_reduced=True).values,
        [data[i][16] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=5, only_valid=True, use_reduced=False).values,
        [data[i][19] for i in range(len(data))],
    )
    assert equal_values(
        ts.forward_moving_average(window=5, only_valid=True, use_reduced=True).values,
        [data[i][22] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(
            window=3, only_valid=False, use_reduced=False
        ).values,
        [data[i][2] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=3, only_valid=False, use_reduced=True).values,
        [data[i][5] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=3, only_valid=True, use_reduced=False).values,
        [data[i][8] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=3, only_valid=True, use_reduced=True).values,
        [data[i][11] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(
            window=5, only_valid=False, use_reduced=False
        ).values,
        [data[i][14] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=5, only_valid=False, use_reduced=True).values,
        [data[i][17] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=5, only_valid=True, use_reduced=False).values,
        [data[i][20] for i in range(len(data))],
    )
    assert equal_values(
        ts.centered_moving_average(window=5, only_valid=True, use_reduced=True).values,
        [data[i][23] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=3, only_valid=False, use_reduced=False).values,
        [data[i][3] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=3, only_valid=False, use_reduced=True).values,
        [data[i][6] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=3, only_valid=True, use_reduced=False).values,
        [data[i][9] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=3, only_valid=True, use_reduced=True).values,
        [data[i][12] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=5, only_valid=False, use_reduced=False).values,
        [data[i][15] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=5, only_valid=False, use_reduced=True).values,
        [data[i][18] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=5, only_valid=True, use_reduced=False).values,
        [data[i][21] for i in range(len(data))],
    )
    assert equal_values(
        ts.olympic_moving_average(window=5, only_valid=True, use_reduced=True).values,
        [data[i][24] for i in range(len(data))],
    )


def test_protected() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        math.inf,
        1300,
        1315,
        1330,
        1345,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    ts.iselect_valid().iset_protected()
    unscreened_code = 0
    protected_code = Qual(
        [
            "Screened",
            "Unknown",
            "No_Range",
            "Original",
            "None",
            "None",
            "None",
            "Protected",
        ]
    ).code
    unprotected_code = Qual(
        [
            "Screened",
            "Unknown",
            "No_Range",
            "Original",
            "None",
            "None",
            "None",
            "Unprotected",
        ]
    ).code
    for tsv in ts.tsv:
        if np.isfinite(tsv.value.magnitude):
            assert tsv.quality.code == protected_code
        else:
            assert tsv.quality.code == unscreened_code
    ts.iset_unprotected()
    for tsv in ts.tsv:
        if np.isfinite(tsv.value.magnitude):
            assert tsv.quality.code == unprotected_code
        else:
            assert tsv.quality.code == unscreened_code


def test_screen_with_value_range() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    min_reject_limit = 1030
    min_question_limit = 1060
    max_question_limit = 1240
    max_reject_limit = 1300
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    question_code = Qual(
        "Screened Questionable No_range Original None None Absolute_Value Unprotected".split()
    ).code
    reject_code = Qual(
        "Screened Rejected No_range Original None None Absolute_Value Unprotected".split()
    ).code
    # ----------------------- #
    # screen_with_value_range #
    # ----------------------- #
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = ts.screen_with_value_range(minr, minq, maxq, maxr)
                    for tsv in ts2.tsv:
                        if tsv.value.magnitude < minr or tsv.value.magnitude > maxr:
                            assert tsv.quality == reject_code
                        elif tsv.value.magnitude < minq or tsv.value.magnitude > maxq:
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude):
                            assert tsv.quality == missing_code
                        else:
                            assert tsv.quality == okay_code
    # --------------------------------------------------- #
    # screen_with_value_range: work with protected values #
    # --------------------------------------------------- #
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = (
                        ts.select(lambda tsv: cast(int, tsv.time.hour) % 2 == 0)
                        .iset_protected()
                        .screen_with_value_range(minr, minq, maxq, maxr)
                    )
                    for tsv in ts2.tsv:
                        if tsv.quality.protection:
                            assert tsv.quality == protected_code
                        elif tsv.value.magnitude < minr or tsv.value.magnitude > maxr:
                            assert tsv.quality == reject_code
                        elif tsv.value.magnitude < minq or tsv.value.magnitude > maxq:
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude):
                            assert tsv.quality == missing_code
                        else:
                            assert tsv.quality == okay_code
    # -------------------------------------------- #
    # screen_with_value_range: work with selection #
    # -------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = ts.select(
                        lambda tsv: tsv.time > time
                    ).screen_with_value_range(minr, minq, maxq, maxr)
                    for tsv in ts2.tsv:
                        if tsv.time <= time:
                            assert tsv.quality == unscreened_code
                        elif tsv.value.magnitude < minr or tsv.value.magnitude > maxr:
                            assert tsv.quality == reject_code
                        elif tsv.value.magnitude < minq or tsv.value.magnitude > maxq:
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude):
                            assert tsv.quality == missing_code
                        else:
                            assert tsv.quality == okay_code


def test_screen_with_value_change_rate() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,  #      0.25, o
        1030,  #      0.25, o
        1045,  #      0.25, o
        1060,  #      0.25, o
        math.inf,  #   inf, r
        1090,  #      -inf, r
        1090,  #      0.00, o
        1120,  #      0.50, q
        1135,  #      0.25, o
        math.nan,  #   nan, m
        1165,  #       nan, m
        1180,  #      0.25, o
        1195,  #      0.25, o
        1210,  #      0.25, o
        1225,  #      0.25, o
        1240,  #      0.25, o
        1240,  #      0.00, o
        1270,  #      0.50, q
        -math.inf,  # -inf, r
        1300,  #       inf, r
        1315,  #      0.25, o
        1330,  #      0.25, o
        1300,  #     -0.50, q
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    min_reject_limit = -0.6
    min_question_limit = -0.4
    max_question_limit = 0.4
    max_reject_limit = 0.6
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    question_code = Qual(
        "Screened Questionable No_range Original None None Rate_of_Change Unprotected".split()
    ).code
    reject_code = Qual(
        "Screened Rejected No_range Original None None Rate_of_Change Unprotected".split()
    ).code
    # ----------------------------- #
    # screen_with_value_change_rate #
    # ----------------------------- #
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = ts.screen_with_value_change_rate(minr, minq, maxq, maxr)
                    tsvs = ts2.tsv
                    for i, tsv in enumerate(tsvs):
                        if i == 0:
                            assert tsv.quality == unscreened_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minr or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxr:
                            assert tsv.quality == reject_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minq or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxq:
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude) or math.isnan(
                            tsvs[i - 1].value.magnitude
                        ):
                            assert tsv.quality == missing_code
                        else:
                            assert tsv.quality == okay_code
    # --------------------------------------------------------- #
    # screen_with_value_change_rate: work with protected values #
    # --------------------------------------------------------- #
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = (
                        ts.select(lambda tsv: cast(int, tsv.time.hour) % 2 == 0)
                        .iset_protected()
                        .screen_with_value_change_rate(minr, minq, maxq, maxr)
                    )
                    tsvs = ts2.tsv
                    for i, tsv in enumerate(tsvs):
                        if i == 0:
                            assert tsv.quality == unscreened_code
                        elif tsv.quality.protection:
                            assert tsv.quality == protected_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minr or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxr:
                            assert tsv.quality == reject_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minq or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxq:
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude) or math.isnan(
                            tsvs[i - 1].value.magnitude
                        ):
                            assert tsv.quality == missing_code
                        else:
                            assert tsv.quality == okay_code
    # -------------------------------------------------- #
    # screen_with_value_change_rate: work with selection #
    # -------------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    for minr in (min_reject_limit, math.nan):
        for minq in (min_question_limit, math.nan):
            for maxq in (max_question_limit, math.nan):
                for maxr in (max_reject_limit, math.nan):
                    ts2 = ts.select(
                        lambda tsv: tsv.time > time
                    ).screen_with_value_change_rate(minr, minq, maxq, maxr)
                    tsvs = ts2.tsv
                    first = True
                    for i, tsv in enumerate(tsvs):
                        if tsv.time <= time:
                            first = True
                            assert tsv.quality == unscreened_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minr or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxr:
                            first = False
                            assert tsv.quality == reject_code
                        elif (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 < minq or (
                            tsv.value.magnitude - tsvs[i - 1].value.magnitude
                        ) / 60.0 > maxq:
                            first = False
                            assert tsv.quality == question_code
                        elif math.isnan(tsv.value.magnitude) or math.isnan(
                            tsvs[i - 1].value.magnitude
                        ):
                            first = False
                            assert tsv.quality == missing_code
                        else:
                            assert (
                                tsv.quality == unscreened_code if first else okay_code
                            )
                            first = False


def test_screen_with_value_range_or_change_rate() -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    min_valid = 1050
    max_valid = 1300
    max_change = 15
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    abs_value_code_original = Qual(
        "Screened Missing No_range Original None None Absolute_Value Unprotected".split()
    ).code
    abs_value_code_missing = Qual(
        "Screened Missing No_range Modified Automatic Missing Absolute_Value Unprotected".split()
    ).code
    abs_value_code_explicit = Qual(
        "Screened Rejected No_range Modified Automatic Explicit Absolute_Value Unprotected".split()
    ).code
    chg_value_code_original = Qual(
        "Screened Missing No_range Original None None Rate_of_Change Unprotected".split()
    ).code
    chg_value_code_missing = Qual(
        "Screened Missing No_range Modified Automatic Missing Rate_of_Change Unprotected".split()
    ).code
    chg_value_code_explicit = Qual(
        "Screened Rejected No_range Modified Automatic Explicit Rate_of_Change Unprotected".split()
    ).code
    # ----------------------------------------------------------- #
    #  screen_with_value_change_rate: don't replace invalid values #
    # ----------------------------------------------------------- #
    for minv in (min_valid, math.nan):
        for maxv in (max_valid, math.nan):
            for maxc in (max_change, math.nan):
                ts2 = ts.screen_with_value_range_or_change(minv, maxv, maxc, False)
                tsvs = ts2.tsv
                for i, tsv in enumerate(tsvs):
                    if tsv.value.magnitude < minv or tsv.value.magnitude > maxv:
                        assert tsv.quality == abs_value_code_original
                    elif (
                        i > 0
                        and abs(tsv.value.magnitude - tsvs[i - 1].value.magnitude)
                        > maxc
                    ):
                        assert tsv.quality == chg_value_code_original
                    elif math.isnan(tsv.value.magnitude):
                        assert tsv.quality == missing_code
                    else:
                        assert tsv.quality == okay_code
    # -------------------------------------------------------------- #
    #  screen_with_value_range_or_change: work with protected values #
    # -------------------------------------------------------------- #
    for minv in (min_valid, math.nan):
        for maxv in (max_valid, math.nan):
            for maxc in (max_change, math.nan):
                ts2 = (
                    ts.select(lambda tsv: cast(int, tsv.time.hour) % 2 == 0)
                    .iset_protected()
                    .iscreen_with_value_range_or_change(minv, maxv, maxc)
                )
                tsvs = ts2.tsv
                for i, tsv in enumerate(tsvs):
                    if tsv.quality.protection:
                        assert tsv.quality == protected_code
                    elif math.isnan(tsv.value.magnitude):
                        assert tsv.quality in (
                            missing_code,
                            abs_value_code_missing,
                            chg_value_code_missing,
                        )
                    else:
                        assert tsv.quality == okay_code
    # ------------------------------------------------------- #
    #  screen_with_value_range_or_change: work with selection #
    # ------------------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    for minv in (min_valid, math.nan):
        for maxv in (max_valid, math.nan):
            for maxc in (max_change, math.nan):
                ts2 = ts.select(
                    lambda tsv: tsv.time > time
                ).screen_with_value_range_or_change(minv, maxv, maxc)
                tsvs = ts2.tsv
                for i, tsv in enumerate(tsvs):
                    if tsv.time <= time:
                        assert tsv.quality == unscreened_code
                    elif math.isnan(tsv.value.magnitude):
                        assert tsv.quality in (
                            missing_code,
                            abs_value_code_missing,
                            chg_value_code_missing,
                        )
                    else:
                        assert tsv.quality == okay_code
    # ------------------------------------------------------------------------------- #
    #  screen_with_value_range_or_change: specify non-NaN value, use Rejected quality #
    # ------------------------------------------------------------------------------- #
    for minv in (min_valid, math.nan):
        for maxv in (max_valid, math.nan):
            for maxc in (max_change, math.nan):
                ts2 = ts.select(
                    lambda tsv: tsv.time > time
                ).screen_with_value_range_or_change(minv, maxv, maxc, True, -901, "R")
                tsvs = ts2.tsv
                for i, tsv in enumerate(tsvs):
                    if tsv.time <= time:
                        assert tsv.quality == unscreened_code
                    elif tsv.value.magnitude == -901:
                        assert tsv.quality in (
                            abs_value_code_explicit,
                            chg_value_code_explicit,
                        )
                    elif math.isnan(tsv.value.magnitude):
                        assert tsv.quality == missing_code
                    else:
                        assert tsv.quality == okay_code


def make_screen_with_duration_magnitude_data() -> list[list[Any]]:
    min_missing_limit = 0.051
    min_reject_limit = 0.101
    min_question_limit = 0.151
    max_question_limit = 0.349
    max_reject_limit = 0.399
    max_missing_limit = 0.449
    data = []
    for hours in 6, 8, 12:
        for pct in 50, 75:
            for minm in (min_missing_limit * hours / 6.0, math.nan):
                for minr in (min_reject_limit * hours / 6.0, math.nan):
                    for minq in (min_question_limit * hours / 6.0, math.nan):
                        for maxq in (max_question_limit * hours / 6.0, math.nan):
                            for maxr in (max_reject_limit * hours / 6.0, math.nan):
                                for maxm in (max_missing_limit * hours / 6.0, math.nan):
                                    data.append(
                                        [hours]
                                        + list(
                                            map(
                                                lambda x: round(x, 9),
                                                [
                                                    pct,
                                                    minm,
                                                    minr,
                                                    minq,
                                                    maxq,
                                                    maxr,
                                                    maxm,
                                                ],
                                            )
                                        )
                                    )
    if slow_test_coverage < 100:
        data = random_subset(data)
    return data


@pytest.mark.parametrize(
    "hours, pct, minm, minr, minq, maxq, maxr, maxm",
    make_screen_with_duration_magnitude_data(),
)
def test_screen_with_duration_magnitude(
    hours: int,
    pct: float,
    minm: float,
    minr: float,
    minq: float,
    maxq: float,
    maxr: float,
    maxm: float,
) -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("6Hours")
    values = [
        0.300,
        0.250,
        0.450,
        0.400,
        0.400,
        math.inf,
        0.350,
        0.450,
        0.500,
        0.375,
        math.nan,
        0.000,
        0.000,
        0.050,
        0.350,
        0.100,
        0.350,
        0.275,
        0.425,
        -math.inf,
        0.125,
        0.075,
        0.225,
        0.150,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Precip.Total.{intvl.name}.{intvl.name}.Raw")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code_unscreened = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    missing_code_screened = Qual(
        "Screened Missing No_Range Modified Automatic Missing Duration_Value Unprotected".split()
    ).code
    question_code = Qual(
        "Screened Questionable No_range Original None None Duration_Value Unprotected".split()
    ).code
    reject_code = Qual(
        "Screened Rejected No_range Original None None Duration_Value Unprotected".split()
    ).code
    # ------------------------------ #
    # screen_with_duration_magnitude #
    # ------------------------------ #
    ts2 = ts.screen_with_duration_magnitude(
        f"{hours}Hours",
        minm,
        minr,
        minq,
        maxq,
        maxr,
        maxm,
        pct,
    )
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        invalid = (
            math.isnan(values[i])
            or math.isinf(values[i])
            or (
                hours > 6
                and pct > 50
                and (math.isnan(values[i - 1]) or math.isinf(values[i - 1]))
            )
        )
        if not invalid:
            if (
                hours == 6
                or i == 0
                or math.isnan(values[i - 1])
                or math.isinf(values[i - 1])
            ):
                accum = values[i]
            else:
                if hours == 8:
                    accum = values[i] + values[i - 1] / 3.0
                else:
                    accum = values[i] + values[i - 1]
        if math.isnan(values[i]):
            assert tsv.quality == unscreened_code
        elif invalid:
            assert tsv.quality == unscreened_code
        elif hours > 6 and i == 0:
            assert tsv.quality == unscreened_code
        elif accum < minm or accum > maxm:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif accum < minr or accum > maxr:
            assert tsv.quality == reject_code
        elif accum < minq or accum > maxq:
            assert tsv.quality == question_code
        elif math.isnan(tsv.value.magnitude):
            assert tsv.quality in (
                missing_code_unscreened,
                missing_code_screened,
            )
        elif all(
            [
                math.isnan(v)
                for v in (
                    minm,
                    maxm,
                    minr,
                    maxr,
                    minq,
                    maxq,
                )
            ]
        ):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code
    # ---------------------------------------------------------- #
    # screen_with_duration_magnitude: work with protected values #
    # ---------------------------------------------------------- #
    ts2 = (
        ts.select(lambda tsv: cast(int, tsv.time.hour) % 24 == 1)
        .iset_protected()
        .iscreen_with_duration_magnitude(
            f"{hours}Hours",
            minm,
            minr,
            minq,
            maxq,
            maxr,
            maxm,
            pct,
        )
    )
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        invalid = (
            math.isnan(values[i])
            or math.isinf(values[i])
            or (
                hours > 6
                and pct > 50
                and (math.isnan(values[i - 1]) or math.isinf(values[i - 1]))
            )
        )
        if not invalid:
            if (
                hours == 6
                or i == 0
                or math.isnan(values[i - 1])
                or math.isinf(values[i - 1])
            ):
                accum = values[i]
            else:
                if hours == 8:
                    accum = values[i] + values[i - 1] / 3.0
                else:
                    accum = values[i] + values[i - 1]
        if tsv.quality.protection:
            assert tsv.quality == protected_code
            assert tsv.value.magnitude == values[i] or (
                math.isnan(tsv.value.magnitude) and math.isnan(values[i])
            )
        elif math.isnan(values[i]):
            assert tsv.quality == unscreened_code
        elif invalid:
            assert tsv.quality == unscreened_code
        elif hours > 6 and i == 0:
            assert tsv.quality == unscreened_code
        elif accum < minm or accum > maxm:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif accum < minr or accum > maxr:
            assert tsv.quality == reject_code
        elif accum < minq or accum > maxq:
            assert tsv.quality == question_code
        elif math.isnan(tsv.value.magnitude):
            assert tsv.quality in (
                missing_code_unscreened,
                missing_code_screened,
            )
        elif all(
            [
                math.isnan(v)
                for v in (
                    minm,
                    maxm,
                    minr,
                    maxr,
                    minq,
                    maxq,
                )
            ]
        ):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code

    # --------------------------------------------------- #
    # screen_with_duration_magnitude: work with selection #
    # --------------------------------------------------- #
    time = HecTime("2024-10-11 07:00")
    ts2 = ts.select(lambda tsv: tsv.time > time).iscreen_with_duration_magnitude(
        f"{hours}Hours",
        minm,
        minr,
        minq,
        maxq,
        maxr,
        maxm,
        pct,
    )
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        invalid = (
            math.isnan(values[i])
            or math.isinf(values[i])
            or (
                hours > 6
                and pct > 50
                and (math.isnan(values[i - 1]) or math.isinf(values[i - 1]))
            )
        )
        if not invalid:
            if (
                hours == 6
                or i == 0
                or math.isnan(values[i - 1])
                or math.isinf(values[i - 1])
            ):
                accum = values[i]
            else:
                if hours == 8:
                    accum = values[i] + values[i - 1] / 3.0
                else:
                    accum = values[i] + values[i - 1]
        if tsv.time <= time:
            assert tsv.quality == unscreened_code
        elif math.isnan(values[i]):
            assert tsv.quality == unscreened_code
        elif invalid:
            assert tsv.quality == unscreened_code
        elif hours > 6 and i == 6:  # first selected index
            assert tsv.quality == unscreened_code
        elif accum < minm or accum > maxm:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif accum < minr or accum > maxr:
            assert tsv.quality == reject_code
        elif accum < minq or accum > maxq:
            assert tsv.quality == question_code
        elif math.isnan(tsv.value.magnitude):
            assert tsv.quality in (
                missing_code_unscreened,
                missing_code_screened,
            )
        elif all(
            [
                math.isnan(v)
                for v in (
                    minm,
                    maxm,
                    minr,
                    maxr,
                    minq,
                    maxq,
                )
            ]
        ):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code


def make_test_screen_with_constant_value_data() -> list[list[Any]]:
    data = []
    missing_limit = {2: 0.001, 4: 0.003, 6: 0.0035}
    reject_limit = {2: 0.005, 4: 0.015, 6: 0.0175}
    question_limit = {2: 0.01, 4: 0.03, 6: 0.035}
    for hours in 2, 4, 6:
        for m in missing_limit[hours], math.nan:
            for r in reject_limit[hours], math.nan:
                for q in question_limit[hours], math.nan:
                    for above in 613.5, 613.51:
                        for pct in 50, 90:
                            data.append(
                                [hours]
                                + list(
                                    map(lambda x: round(x, 9), [m, r, q, above, pct])
                                )
                            )
    if slow_test_coverage < 100:
        data = random_subset(data)
    return data


@pytest.mark.parametrize(
    "hours, m, r, q, above, pct", make_test_screen_with_constant_value_data()
)
def test_screen_with_constant_value(
    hours: int,
    m: float,
    r: float,
    q: float,
    above: float,
    pct: float,
) -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        613.535,
        613.535,
        613.534,
        613.534,
        613.503,
        math.inf,
        613.532,
        613.504,
        613.537,
        613.51,
        math.nan,
        613.504,
        613.511,
        613.546,
        613.535,
        613.539,
        613.545,
        613.512,
        613.524,
        -math.inf,
        613.515,
        613.517,
        613.541,
        613.527,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Elev.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code_unscreened = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    missing_code_screened = Qual(
        "Screened Missing No_range Modified Automatic Missing Constant_Value Unprotected".split()
    ).code
    question_code = Qual(
        "Screened Questionable No_range Original None None Constant_Value Unprotected".split()
    ).code
    reject_code = Qual(
        "Screened Rejected No_range Original None None Constant_Value Unprotected".split()
    ).code
    # -------------------------- #
    # screen_with_constant_value #
    # -------------------------- #
    ts2 = ts.screen_with_constant_value(f"{hours}Hours", m, r, q, above, pct)
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        vals = values[max(i - hours, 0) : i + 1]
        valid_vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
        pct_valid = 100 * len(valid_vals) / len(vals)
        max_change = max(valid_vals) - min(valid_vals)
        if i < hours:
            assert tsv.quality == unscreened_code
        elif pct_valid < pct:
            assert tsv.quality == unscreened_code
        elif math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == unscreened_code
        elif values[i] < above:
            assert tsv.quality == unscreened_code
        elif max_change < m:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif max_change < r:
            assert tsv.quality == reject_code
        elif max_change < q:
            assert tsv.quality == question_code
        elif all([math.isnan(v) for v in (m, r, q)]):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code
    # ------------------------------------------------------ #
    # screen_with_constant_value: work with protected values #
    # ------------------------------------------------------ #
    ts2 = (
        ts.select(lambda tsv: cast(int, tsv.time.hour) % 24 == 1)
        .iset_protected()
        .screen_with_constant_value(f"{hours}Hours", m, r, q, above, pct)
    )
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        vals = values[max(i - hours, 0) : i + 1]
        valid_vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
        pct_valid = 100 * len(valid_vals) / len(vals)
        max_change = max(valid_vals) - min(valid_vals)
        if tsv.quality.protection:
            assert tsv.quality == protected_code
            assert tsv.value.magnitude == values[i] or (
                math.isnan(tsv.value.magnitude) and math.isnan(values[i])
            )
        elif i < hours:
            assert tsv.quality == unscreened_code
        elif pct_valid < pct:
            assert tsv.quality == unscreened_code
        elif math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == unscreened_code
        elif values[i] < above:
            assert tsv.quality == unscreened_code
        elif max_change < m:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif max_change < r:
            assert tsv.quality == reject_code
        elif max_change < q:
            assert tsv.quality == question_code
        elif all([math.isnan(v) for v in (m, r, q)]):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code
    # ----------------------------------------------- #
    # screen_with_constant_value: work with selection #
    # ----------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    ts2 = ts.select(lambda tsv: tsv.time > time).screen_with_constant_value(
        f"{hours}Hours", m, r, q, above, pct
    )
    tsvs = ts2.tsv
    for i, tsv in enumerate(tsvs):
        vals = values[max(i - hours, 0) : i + 1]
        valid_vals = [v for v in vals if not math.isnan(v) and not math.isinf(v)]
        pct_valid = 100 * len(valid_vals) / len(vals)
        max_change = max(valid_vals) - min(valid_vals)
        if i < hours + 6:  # time is at hour 5
            assert tsv.quality == unscreened_code
        elif pct_valid < pct:
            assert tsv.quality == unscreened_code
        elif math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == unscreened_code
        elif values[i] < above:
            assert tsv.quality == unscreened_code
        elif max_change < m:
            assert tsv.quality == missing_code_screened
            assert math.isnan(tsv.value.magnitude)
        elif max_change < r:
            assert tsv.quality == reject_code
        elif max_change < q:
            assert tsv.quality == question_code
        elif all([math.isnan(v) for v in (m, r, q)]):
            assert tsv.quality == unscreened_code
        else:
            assert tsv.quality == okay_code


def make_test_screen_with_forward_moving_average_data() -> list[list[Any]]:
    data = []
    for window in 3, 5:
        for only_valid in False, True:
            for use_reduced in False, True:
                for diff_limit in 10, 15:
                    for failed_validity in "QRM":
                        data.append(
                            [
                                window,
                                only_valid,
                                use_reduced,
                                diff_limit,
                                failed_validity,
                            ]
                        )
    return data


@pytest.mark.parametrize(
    "window, only_valid, use_reduced, diff_limit, failed_validity",
    make_test_screen_with_forward_moving_average_data(),
)
def test_screen_with_forward_moving_average(
    window: int,
    only_valid: bool,
    use_reduced: bool,
    diff_limit: float,
    failed_validity: str,
) -> None:
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.inf,
        1090,
        1090,
        1120,
        1135,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        1240,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": len(values) * [0],
        },
        index=times,
    )
    unscreened_code = Qual(
        "Unscreened Unknown No_range Original None None None Unprotected".split()
    ).code
    okay_code = Qual(
        "Screened Okay No_range Original None None None Unprotected".split()
    ).code
    protected_code = Qual(
        "Screened Unknown No_range Original None None None Protected".split()
    ).code
    missing_code_unscreened = Qual(
        "Screened Missing No_range Original None None None Unprotected".split()
    ).code
    missing_code_screened = Qual(
        "Screened Missing No_range Modified Automatic Missing Relative_Value Unprotected".split()
    ).code
    question_code = Qual(
        "Screened Questionable No_range Original None None Relative_Value Unprotected".split()
    ).code
    reject_code = Qual(
        "Screened Rejected No_range Original None None Relative_Value Unprotected".split()
    ).code
    # ---------------------------------- #
    # screen_with_forward_moving_average #
    # ---------------------------------- #
    ts2 = ts.forward_moving_average(window, only_valid, use_reduced)
    averaged = ts2.values
    ts3 = ts.screen_with_forward_moving_average(
        window, only_valid, use_reduced, diff_limit, failed_validity
    )
    tsvs = ts3.tsv
    for i, tsv in enumerate(tsvs):
        if math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == missing_code_unscreened
        elif math.isnan(averaged[i]):
            assert tsv.quality == unscreened_code
        elif abs(averaged[i] - values[i]) > diff_limit:
            if failed_validity == "Q":
                assert tsv.quality == question_code
            elif failed_validity == "R":
                assert tsv.quality == reject_code
            else:
                assert tsv.quality == missing_code_screened
                assert math.isnan(tsv.value.magnitude)
        else:
            assert tsv.quality == okay_code
    # -------------------------------------------------------------- #
    # screen_with_forward_moving_average: work with protected values #
    # -------------------------------------------------------------- #
    ts2 = ts.forward_moving_average(window, only_valid, use_reduced)
    averaged = ts2.values
    ts3 = (
        ts.select(lambda tsv: cast(int, tsv.time.hour) % 24 == 1)
        .iset_protected()
        .screen_with_forward_moving_average(
            window,
            only_valid,
            use_reduced,
            diff_limit,
            failed_validity,
        )
    )
    tsvs = ts3.tsv
    for i, tsv in enumerate(tsvs):
        if tsv.quality.protection:
            assert tsv.quality == protected_code
            assert tsv.value.magnitude == values[i] or (
                math.isnan(tsv.value.magnitude) and math.isnan(values[i])
            )
        elif math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == missing_code_unscreened
        elif math.isnan(averaged[i]):
            assert tsv.quality == unscreened_code
        elif abs(averaged[i] - values[i]) > diff_limit:
            if failed_validity == "Q":
                assert tsv.quality == question_code
            elif failed_validity == "R":
                assert tsv.quality == reject_code
            else:
                assert tsv.quality == missing_code_screened
                assert math.isnan(tsv.value.magnitude)
        else:
            assert tsv.quality == okay_code
    # ------------------------------------------------------- #
    # screen_with_forward_moving_average: work with selection #
    # ------------------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    ts2 = ts.forward_moving_average(window, only_valid, use_reduced)
    averaged = ts2.values
    ts3 = ts.select(lambda tsv: tsv.time > time).screen_with_forward_moving_average(
        window, only_valid, use_reduced, diff_limit, failed_validity
    )
    tsvs = ts3.tsv
    for i, tsv in enumerate(tsvs):
        if tsv.time <= time:
            assert tsv.quality == unscreened_code
        elif math.isnan(values[i]) or math.isinf(values[i]):
            assert tsv.quality == missing_code_unscreened
        elif math.isnan(averaged[i]):
            assert tsv.quality == unscreened_code
        elif abs(averaged[i] - values[i]) > diff_limit:
            if failed_validity == "Q":
                assert tsv.quality == question_code
            elif failed_validity == "R":
                assert tsv.quality == reject_code
            else:
                assert tsv.quality == missing_code_screened
                assert math.isnan(tsv.value.magnitude)
        else:
            assert tsv.quality == okay_code


def make_test_estimate_missing_values_data() -> list[list[Any]]:
    data = []
    for accumulation in (False, True):
        for estimate_rejected in (False, True):
            for set_questionable in (False, True):
                data.append([accumulation, estimate_rejected, set_questionable])
    return data


@pytest.mark.parametrize(
    "accumulation, estimate_rejected, set_questionable",
    make_test_estimate_missing_values_data(),
)
def test_estimate_missing_values(
    accumulation: bool, estimate_rejected: bool, set_questionable: bool
) -> None:
    #                  [-] Accumulation      [-] Accumulation      [-] Accumulation      [-] Accumulation      [+] Accumulation      [+] Accumulation      [+] Accumulation      [+] Accumulation
    #                  [-] Estimate Rejected [-] Estimate Rejected [+] Estimate Rejected [+] Estimate Rejected [-] Estimate Rejected [-] Estimate Rejected [+] Estimate Rejected [+] Estimate Rejected
    #    Original      [-] Set Questionable  [+] Set Questionable  [-] Set Questionable  [+] Set Questionable  [-] Set Questionable  [+] Set Questionable  [-] Set Questionable  [+] Set Questionable
    #    ------------- --------------------- --------------------- --------------------- --------------------- --------------------- --------------------- --------------------- ---------------------
    #            0   1              2     3                4     5               6     7               8     9              10    11              12    13             14    15              16    17
    data = """ 
        [[    1000,  3,          1000,    3,            1000,    3,           1000,    3,           1000,    3,           1000,    3,           1000,    3,          1000,    3,           1000,    3],
         [    1015,  3,          1015,    3,            1015,    3,           1015,    3,           1015,    3,           1015,    3,           1015,    3,          1015,    3,           1015,    3],
         [math.nan,  5,   323.3333333, 2435,     323.3333333, 2441,           1030, 2435,           1030, 2441,       math.nan,    5,       math.nan,    5,          1030, 2435,           1030, 2441],
         [math.nan,  5,  -368.3333333, 2435,    -368.3333333, 2441,           1045, 2435,           1045, 2441,       math.nan,    5,       math.nan,    5,          1045, 2435,           1045, 2441],
         [   -1060, 17,         -1060,   17,           -1060,   17,           1060, 2435,           1060, 2441,          -1060,   17,          -1060,   17,          1060, 2435,           1060, 2441],
         [math.nan,  5,  -338.3333333, 2435,    -338.3333333, 2441,           1075, 2435,           1075, 2441,   -338.3333333, 2435,   -338.3333333, 2441,          1075, 2435,           1075, 2441],
         [math.nan,  5,   383.3333333, 2435,     383.3333333, 2441,           1090, 2435,           1090, 2441,    383.3333333, 2435,    383.3333333, 2441,          1090, 2435,           1090, 2441],
         [    1105,  3,          1105,    3,            1105,    3,           1105,    3,           1105,    3,           1105,    3,           1105,    3,          1105,    3,           1105,    3],
         [    1120,  3,          1120,    3,            1120,    3,           1120,    3,           1120,    3,           1120,    3,           1120,    3,          1120,    3,           1120,    3],
         [    1135,  3,          1135,    3,            1135,    3,           1135,    3,           1135,    3,           1135,    3,           1135,    3,          1135,    3,           1135,    3],
         [    1050,  3,          1050,    3,            1050,    3,           1050,    3,           1050,    3,           1050,    3,           1050,    3,          1050,    3,           1050,    3],
         [    1165,  3,          1165,    3,            1165,    3,           1165,    3,           1165,    3,           1165,    3,           1165,    3,          1165,    3,           1165,    3],
         [    1180,  3,          1180,    3,            1180,    3,           1180,    3,           1180,    3,           1180,    3,           1180,    3,          1180,    3,           1180,    3],
         [    1195,  3,          1195,    3,            1195,    3,           1195,    3,           1195,    3,           1195,    3,           1195,    3,          1195,    3,           1195,    3],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [math.nan,  5,      math.nan,    5,        math.nan,    5,       math.nan,    5,       math.nan,    5,           1195, 2435,           1195, 2441,          1195, 2435,           1195, 2441],
         [    1195,  3,          1195,    3,            1195,    3,           1195,    3,           1195,    3,           1195,    3,           1195,    3,          1195,    3,           1195,    3],
         [    1315,  3,          1315,    3,            1315,    3,           1315,    3,           1315,    3,           1315,    3,           1315,    3,          1315,    3,           1315,    3],
         [    1330,  3,          1330,    3,            1330,    3,           1330,    3,           1330,    3,           1330,    3,           1330,    3,          1330,    3,           1330,    3],
         [    1300,  3,          1300,    3,            1300,    3,           1300,    3,           1300,    3,           1300,    3,           1300,    3,          1300,    3,           1300,    3]]
"""
    Qual.set_return_unsigned_codes()
    data_vals = np.transpose(eval(data.strip()))
    columns = {
        # value columns, quality columns are this plus 1
        (False, False, False): 2,
        (False, False, True): 4,
        (False, True, False): 6,
        (False, True, True): 8,
        (True, False, False): 10,
        (True, False, True): 12,
        (True, True, False): 14,
        (True, True, True): 16,
    }
    start_time = HecTime("2024-10-10T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(data_vals[0]))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": data_vals[0],
            "quality": list(map(int, data_vals[1])),
        },
        index=times,
    )
    max_missing_count = 5
    # ----------------------- #
    # estimate_missing_values #
    # ----------------------- #
    ts2 = ts.estimate_missing_values(
        max_missing_count, accumulation, estimate_rejected, set_questionable
    )
    key = (accumulation, estimate_rejected, set_questionable)
    expected_values = data_vals[columns[key]]
    expected_qualities = list(map(int, data_vals[columns[key] + 1]))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        [
            ts2.qualities[i] == expected_qualities[i]
            for i in range(len(expected_qualities))
        ]
    )
    # --------------------------------------------------- #
    # estimate_missing_values: work with protected values #
    # --------------------------------------------------- #
    ts2 = (
        ts.select(lambda tsv: cast(int, tsv.time.hour) % 2 == 1)
        .set_protected()
        .estimate_missing_values(
            max_missing_count,
            accumulation,
            estimate_rejected,
            set_questionable,
        )
    )
    key = (accumulation, estimate_rejected, set_questionable)
    expected_values = copy.deepcopy(data_vals[columns[key]])
    expected_qualities = list(map(int, data_vals[columns[key] + 1]))
    dv0 = data_vals[0][:]
    dv1 = data_vals[1][:]
    for i in range(0, len(dv0), 2):
        expected_values[i] = dv0[i]
        expected_qualities[i] = Qual(int(dv1[i])).set_protection("Protected").unsigned
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        [
            ts2.qualities[i] == expected_qualities[i]
            for i in range(len(expected_qualities))
        ]
    )
    # -------------------------------------------- #
    # estimate_missing_values: work with selection #
    # -------------------------------------------- #
    time = HecTime("2024-10-10T06:00:00")
    time_offset = 6
    ts2 = ts.select(lambda tsv: tsv.time > time).estimate_missing_values(
        max_missing_count,
        accumulation,
        estimate_rejected,
        set_questionable,
    )
    key = (accumulation, estimate_rejected, set_questionable)
    expected_values = []
    expected_qualities = []
    for i in range(len(ts)):
        expected_values.append(
            data_vals[0][i] if i <= time_offset else data_vals[columns[key]][i]
        )
        expected_qualities.append(
            int(data_vals[1][i]) if i <= time_offset else data_vals[columns[key] + 1][i]
        )
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        [
            ts2.qualities[i] == expected_qualities[i]
            for i in range(len(expected_qualities))
        ]
    )


def test_expand_collapse_trim() -> None:
    start_time = HecTime("2024-10-15T01:00:00")
    intvl = Interval.get_cwms("1Day")
    values = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        math.inf,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = intvl.get_datetime_index(
        start_time=start_time, count=len(values), name="time"
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values,
            "quality": 5 * [0] + 6 * [5] + 13 * [0],
        },
        index=times,
    )
    # ------------------------------------------#
    # RTS without protected values or selection #
    # ------------------------------------------#
    expected_length_1 = len(ts)
    expected_times_1 = ts.times[:]
    expected_values_1 = ts.values[:]
    expected_qualities_1 = ts.qualities[:]
    ts2 = ts.collapse()
    expected_length_2 = expected_length_1 - 6
    expected_times = expected_times_1[:5] + expected_times_1[11:]
    expected_values = expected_values_1[:5] + expected_values_1[11:]
    expected_qualities = expected_qualities_1[:5] + expected_qualities_1[11:]
    assert len(ts2) == expected_length_1
    assert len(ts2.times) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    ts2.iexpand("2024-10-13T01:00:00", "2024-11-09T01:00:00")
    expected_length_2 = expected_length_1 + 4
    expected_times = (
        ["2024-10-13 01:00:00", "2024-10-14 01:00:00"]
        + expected_times_1
        + ["2024-11-08 01:00:00", "2024-11-09 01:00:00"]
    )
    expected_values = [math.nan, math.nan] + expected_values_1 + [math.nan, math.nan]
    expected_qualities = [5, 5] + expected_qualities_1 + [5, 5]
    assert len(ts2) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    ts2.itrim()
    assert len(ts2) == expected_length_1
    assert all(ts2.times[i] == expected_times_1[i] for i in range(expected_length_1))
    assert np.allclose(ts2.values, expected_values_1, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities_1[i] for i in range(expected_length_1)
    )
    # ----------------------------------------#
    # RTS with protected values and selection #
    # ----------------------------------------#
    Qual.set_return_unsigned_codes()
    ts2 = ts.select(
        lambda tsv: tsv.time == HecTime("2024-10-20T01:00:00")
    ).iset_protected()
    ts2.iselect(lambda tsv: tsv.time == HecTime("2024-10-25T01:00:00"))
    expected_length_1 = len(ts)
    expected_times_1 = ts2.times[:]
    expected_values_1 = ts2.values[:]
    expected_qualities_1 = ts2.qualities[:]
    ts2 = ts2.icollapse()
    # print(ts2.data)
    expected_length_2 = expected_length_1 - 4
    expected_times = expected_times_1[:6] + expected_times_1[10:]
    expected_values = expected_values_1[:6] + expected_values_1[10:]
    expected_qualities = expected_qualities_1[:6] + expected_qualities_1[10:]
    assert len(ts2) == expected_length_1
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    ts2.iexpand("2024-10-13T01:00:00", "2024-11-09T01:00:00")
    # print(ts2.data)
    expected_length_2 = expected_length_1 + 4
    expected_times = (
        ["2024-10-13 01:00:00", "2024-10-14 01:00:00"]
        + expected_times_1
        + ["2024-11-08 01:00:00", "2024-11-09 01:00:00"]
    )
    expected_values = [math.nan, math.nan] + expected_values_1 + [math.nan, math.nan]
    expected_qualities = [5, 5] + expected_qualities_1 + [5, 5]
    assert len(ts2) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    selected = ts2.selected  # save selection
    ts2.iselect(lambda tsv: tsv.time == HecTime("2024-11-08 01:00:00")).iset_protected()
    cast(pd.DataFrame, ts2.data)["selected"] = selected  # restore selection
    ts2.iselect(lambda tsv: tsv.time == HecTime("2024-10-14 01:00:00"), Combine.OR)
    ts2.itrim()
    # print(ts2.data)
    expected_length_2 = expected_length_1 + 2
    expected_times = (
        ["2024-10-14 01:00:00"] + expected_times_1 + ["2024-11-08 01:00:00"]
    )
    expected_values = [math.nan] + expected_values_1 + [math.nan]
    expected_qualities = [5] + expected_qualities_1 + [2147483653]
    assert len(ts2) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    # ----------------------------------------#
    # LRTS with protected values or selection #
    # ----------------------------------------#
    intvl = cast(
        Interval,
        Interval.get_any_cwms(lambda i: i.name == "~1Day" and i.is_local_regular),
    )
    ts2 = ts.label_as_time_zone("US/Pacific")
    ts2 = ts2.set_interval(intvl)
    expected_length_1 = len(ts2)
    expected_times_1 = ts2.times[:]
    expected_values_1 = ts2.values[:]
    expected_qualities_1 = ts2.qualities[:]
    ts2.icollapse()
    expected_length_2 = expected_length_1 - 6
    expected_times = expected_times_1[:5] + expected_times_1[11:]
    expected_values = expected_values_1[:5] + expected_values_1[11:]
    expected_qualities = expected_qualities_1[:5] + expected_qualities_1[11:]
    assert len(ts2) == expected_length_1
    assert len(ts2.times) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    ts2.iexpand("2024-10-13T01:00:00-07:00", "2024-11-09T01:00:00-08:00")
    # print(ts2.data)
    expected_length_2 = expected_length_1 + 4
    expected_times = (
        ["2024-10-13 01:00:00-07:00", "2024-10-14 01:00:00-07:00"]
        + expected_times_1
        + ["2024-11-08 01:00:00-08:00", "2024-11-09 01:00:00-08:00"]
    )
    expected_values = [math.nan, math.nan] + expected_values_1 + [math.nan, math.nan]
    expected_qualities = [5, 5] + expected_qualities_1 + [5, 5]
    assert len(ts2) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )
    ts2.iselect(
        lambda tsv: tsv.time == HecTime("2024-11-08 01:00:00-08:00")
    ).iset_protected()
    ts2.iselect(
        lambda tsv: tsv.time == HecTime("2024-10-14 01:00:00-07:00"), Combine.OR
    )
    ts2.itrim()
    expected_length_2 = expected_length_1 + 2
    expected_times = (
        ["2024-10-14 01:00:00-07:00"] + expected_times_1 + ["2024-11-08 01:00:00-08:00"]
    )
    expected_values = [math.nan] + expected_values_1 + [math.nan]
    expected_qualities = [5] + expected_qualities_1 + [2147483653]
    assert len(ts2) == expected_length_2
    assert all(ts2.times[i] == expected_times[i] for i in range(expected_length_2))
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all(
        ts2.qualities[i] == expected_qualities[i] for i in range(expected_length_2)
    )


def test_merge() -> None:
    start_time = HecTime("2024-10-15T01:00:00")
    intvl = Interval.get_cwms("1Day")
    values1 = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        math.inf,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    ts1 = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts1._data = pd.DataFrame(
        {
            "value": values1,
            "quality": 5 * [0] + 6 * [5] + 13 * [0],
        },
        index=intvl.get_datetime_index(
            start_time=start_time, count=len(values1), name="time"
        ),
    )
    values2 = [
        2000,
        2015,
        2030,
        2045,
        2060,
        2075,
        math.inf,
        2105,
        -math.inf,
        2135,
        2150,
        2165,
        2180,
        2195,
        2210,
        2225,
        2240,
        2250,
        2270,
        2285,
        math.nan,
        math.nan,
        2330,
        2300,
    ]
    ts2 = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts2._data = pd.DataFrame(
        {
            "value": values2,
            "quality": 20 * [0] + 2 * [5] + 2 * [0],
        },
        index=intvl.get_datetime_index(
            start_time=start_time, count=len(values2), name="time"
        ),
    )
    # ------------------------------------- #
    # same time window, no protected values #
    # ------------------------------------- #
    ts3 = ts1.merge(ts2)
    expected_length = len(ts1)
    expected_values = [
        (
            ts2.values[i]
            if math.isnan(ts1.values[i])
            or math.isinf(ts1.values[i])
            and not math.isnan(ts2.values[i])
            else ts1.values[i]
        )
        for i in range(expected_length)
    ]
    expected_qualities = [
        (
            ts2.qualities[i]
            if math.isnan(ts1.values[i])
            or math.isinf(ts1.values[i])
            and not math.isnan(ts2.values[i])
            else ts1.qualities[i]
        )
        for i in range(expected_length)
    ]
    assert len(ts3) == expected_length
    assert all([ts3.times[i] == ts2.times[i] for i in range(len(ts1))])
    assert np.allclose(ts3.values, expected_values, equal_nan=True)
    assert all(
        ts3.qualities[i] == expected_qualities[i] for i in range(expected_length)
    )
    # ------------------------------ #
    # test merging empty time series #
    # ------------------------------ #
    ts1_copy = ts1.copy()  # will restore later
    ts2_copy = ts2.copy()  # will restore later
    ts1._data = None
    ts3 = ts1.merge(ts2)
    assert len(ts3) == expected_length
    assert all([ts3.times[i] == ts2.times[i] for i in range(expected_length)])
    assert np.allclose(ts3.values, ts2.values, equal_nan=True)
    assert all(ts3.qualities[i] == ts2.qualities[i] for i in range(expected_length))
    ts3 = ts2.merge(ts1)
    assert len(ts3) == expected_length
    assert all([ts3.times[i] == ts2.times[i] for i in range(expected_length)])
    assert np.allclose(ts3.values, ts2.values, equal_nan=True)
    assert all(ts3.qualities[i] == ts2.qualities[i] for i in range(expected_length))
    # ---------------------------------- #
    # same time window, protected values #
    # ---------------------------------- #
    ts1 = ts1_copy
    ts2 = ts2_copy
    ts1.iselect(5).iset_protected()
    ts2.iselect(21).iset_protected()
    ts3 = ts1.merge(ts2)
    expected_values[5] = ts1.values[5]
    expected_qualities[5] = ts1.qualities[5]
    expected_values[21] = ts2.values[21]
    expected_qualities[21] = ts2.qualities[21]
    assert len(ts3) == expected_length
    assert all([ts3.times[i] == ts2.times[i] for i in range(len(ts1))])
    assert np.allclose(ts3.values, expected_values, equal_nan=True)
    assert all(
        ts3.qualities[i] == expected_qualities[i] for i in range(expected_length)
    )
    # ---------------------- #
    # differing time windows #
    # ---------------------- #
    ts1 = ts1_copy
    ts2 = ts2_copy
    shift_offset = 6  # intervals
    ts2 >>= shift_offset
    ts3 = ts1.merge(ts2)
    expected_length += shift_offset
    expected_times = sorted(set(ts1.times) | set(ts2.times))
    expected_values = (
        ts1.values[:shift_offset]
        + [
            (
                ts2.values[i - shift_offset]
                if math.isnan(ts1.values[i])
                or math.isinf(ts1.values[i])
                and not math.isnan(ts2.values[i - shift_offset])
                else ts1.values[i]
            )
            for i in range(shift_offset, len(ts1))
        ]
        + ts2.values[-shift_offset:]
    )
    expected_qualities = (
        ts1.qualities[:shift_offset]
        + [
            (
                ts2.qualities[i - shift_offset]
                if math.isnan(ts1.values[i])
                or math.isinf(ts1.values[i])
                and not math.isnan(ts2.values[i - shift_offset])
                else ts1.qualities[i]
            )
            for i in range(shift_offset, len(ts1))
        ]
        + ts2.qualities[-shift_offset:]
    )
    assert len(ts3) == expected_length
    assert all([ts3.times[i] == expected_times[i] for i in range(len(ts1))])
    assert np.allclose(ts3.values, expected_values, equal_nan=True)
    assert all(
        ts3.qualities[i] == expected_qualities[i] for i in range(expected_length)
    )
    # --------------------- #
    # test mixing intervals #
    # --------------------- #
    intvl = Interval.get_cwms("12Hours")
    ts4 = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts4._data = pd.DataFrame(
        {
            "value": values2,
            "quality": 20 * [0] + 2 * [5] + 2 * [0],
        },
        index=intvl.get_datetime_index(
            start_time=start_time, count=len(values1), name="time"
        ),
    )
    try:
        ts1.merge(ts4)
    except TimeSeriesException as tse:
        assert str(tse).find("is not consistent with interval") != -1


def test_to_irregular() -> None:
    start_time = HecTime("2024-10-15T01:00:00")
    intvl = Interval.get_cwms("1Day")
    values1 = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        math.inf,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values1))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values1,
            "quality": 5 * [0] + 6 * [5] + 13 * [0],
        },
        index=times,
    )
    assert ts.interval.name == "1Day"
    valid_intervals = set(Interval.get_all_cwms_names(lambda i: i.is_any_irregular))
    for intvl_name in Interval.get_all_names():
        try:
            ts.ito_irregular(intvl_name)
            assert (
                intvl_name in valid_intervals
            ), f"{intvl_name} should have raised an exception!"
            # print(ts.name)
        except TimeSeriesException as tse:
            assert (
                intvl_name not in valid_intervals
            ), f"{intvl_name} should not have raised an exception!"
            # print(str(tse))


def test_snap_to_regular() -> None:
    start_time = HecTime("2024-10-15T01:00:00")
    intvl = Interval.get_cwms("1Hour")
    values1 = [
        1000,
        1015,
        1030,
        1045,
        1060,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        math.nan,
        1165,
        1180,
        1195,
        1210,
        1225,
        1240,
        math.inf,
        1270,
        -math.inf,
        1300,
        1315,
        1330,
        1300,
    ]
    times = pd.DatetimeIndex(
        [
            (start_time + i * TimeSpan(intvl.values)).datetime()
            for i in range(len(values1))
        ],
        name="time",
    )
    ts = TimeSeries(f"Loc1.Flow.Inst.{intvl.name}.0.Computed")
    ts._data = pd.DataFrame(
        {
            "value": values1,
            "quality": 5 * [0] + 6 * [5] + 13 * [0],
        },
        index=times,
    )
    # print(ts.data)
    ts2 = ts.snap_to_regular("4Hours", "PT10M")
    # print(ts2.data)
    assert ts2.name == ts.name.replace("1Hour", "4Hours")
    assert len(ts2) == 0
    ts2 = ts.snap_to_regular("4Hours", "PT10M", "PT1H")
    # print(ts2.data)
    expected_time_vals = [
        HecTime("2024-10-15 04:10:00")
        + i * TimeSpan(Interval.get_cwms("4Hours").values)
        for i in range(6)
    ]
    expected_times = [f"{t.date(-13)} {t.time(True)}" for t in expected_time_vals]
    expected_values = [1045.0, math.nan, 1165.0, 1225.0, -math.inf, 1300.0]
    expected_qualities = [0, 5, 0, 0, 0, 0]
    assert all([ts2.times[i] == expected_times[i] for i in range(6)])
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all([ts2.qualities[i] == expected_qualities[i] for i in range(6)])
    ts2 = ts.snap_to_regular("4Hours", "PT10M", "PT0S", "PT1H")
    # print(ts2.data)
    expected_time_vals = [
        HecTime("2024-10-15 00:10:00")
        + i * TimeSpan(Interval.get_cwms("4Hours").values)
        for i in range(6)
    ]
    expected_times = [f"{t.date(-13)} {t.time(True)}" for t in expected_time_vals]
    expected_values = [1000.0, 1060.0, math.nan, 1180.0, 1240.0, 1300.0]
    expected_qualities = [0, 0, 5, 0, 0, 0]
    assert all([ts2.times[i] == expected_times[i] for i in range(6)])
    assert np.allclose(ts2.values, expected_values, equal_nan=True)
    assert all([ts2.qualities[i] == expected_qualities[i] for i in range(6)])
    ts2 = ts.snap_to_regular("4Hours", "PT10M", "PT1H", "PT1H")
    # print(ts2.data)
    expected_time_vals = [
        HecTime("2024-10-15 00:10:00")
        + i * TimeSpan(Interval.get_cwms("4Hours").values)
        for i in range(6)
    ]
    expected_times = [f"{t.date(-13)} {t.time(True)}" for t in expected_time_vals]
    expected_values = [1000.0, 1045.0, math.nan, 1165.0, 1225.0, 1300.0]
    expected_qualities = [0, 0, 5, 0, 0, 0]


def make_test_new_regluar_time_series_data() -> list[list[Any]]:
    data = []
    time_zone = "US/Pacific"
    start_times = [
        HecTime(s).label_as_time_zone(time_zone)
        for s in ("2025-02-15T15:30:00", "2025-10-15T15:30:00")
    ]
    matchers = [
        lambda i: i.minutes == 1440 and i.is_local_regular,
        lambda i: i.name == "1Day",
    ]
    intervals = [
        cast(Interval, intvl)
        for intvl in [Interval.get_any_cwms(matcher) for matcher in matchers]
    ]
    offsets: List[Union[TimeSpan, timedelta, str, int]] = [
        TimeSpan(hours=8),
        timedelta(hours=8),
        "PT8H",
        480,
    ]
    values = (100.0, [1.0, 2.0, 3.0, 4.0, 5.0])
    qualities: tuple[Union[list[Union[Qual, int]], Qual, int], ...] = (
        3,
        Qual(3),
        [0, 3],
        [Qual(0), Qual(3)],
    )
    for start_time in start_times:
        end_specs: tuple[HecTime, int] = (
            HecTime(start_time) + 24 * TimeSpan(Interval.get_cwms("1Day").values),
            24,
        )
        for end in end_specs:
            for intvl in intervals:
                for offset in offsets:
                    for value in values:
                        for quality in qualities:
                            data.append(
                                [start_time, end, intvl, offset, value, quality]
                            )
    if slow_test_coverage < 100:
        data = random_subset(data)
    return data


@pytest.mark.parametrize(
    "start_time, end, intvl, offset, value, quality",
    make_test_new_regluar_time_series_data(),
)
def test_new_regular_time_series(
    start_time: HecTime,
    end: Union[HecTime, int],
    intvl: Interval,
    offset: Union[TimeSpan, timedelta, str, int],
    value: Union[float, list[float]],
    quality: Union[list[Union[Qual, int]], Qual, int],
) -> None:
    name = "Loc1.Flow.Inst.0.0.Computed"
    time_zone = "US/Pacific"
    expected_length = 24
    expected_times = {
        "2025-02-15T15:30:00-08:00": {
            "~1Day": (
                "2025-02-16 08:00:00-08:00",
                "2025-02-17 08:00:00-08:00",
                "2025-02-18 08:00:00-08:00",
                "2025-02-19 08:00:00-08:00",
                "2025-02-20 08:00:00-08:00",
                "2025-02-21 08:00:00-08:00",
                "2025-02-22 08:00:00-08:00",
                "2025-02-23 08:00:00-08:00",
                "2025-02-24 08:00:00-08:00",
                "2025-02-25 08:00:00-08:00",
                "2025-02-26 08:00:00-08:00",
                "2025-02-27 08:00:00-08:00",
                "2025-02-28 08:00:00-08:00",
                "2025-03-01 08:00:00-08:00",
                "2025-03-02 08:00:00-08:00",
                "2025-03-03 08:00:00-08:00",
                "2025-03-04 08:00:00-08:00",
                "2025-03-05 08:00:00-08:00",
                "2025-03-06 08:00:00-08:00",
                "2025-03-07 08:00:00-08:00",
                "2025-03-08 08:00:00-08:00",
                "2025-03-09 08:00:00-07:00",
                "2025-03-10 08:00:00-07:00",
                "2025-03-11 08:00:00-07:00",
            ),
            "1Day": (
                "2025-02-16 08:00:00-08:00",
                "2025-02-17 08:00:00-08:00",
                "2025-02-18 08:00:00-08:00",
                "2025-02-19 08:00:00-08:00",
                "2025-02-20 08:00:00-08:00",
                "2025-02-21 08:00:00-08:00",
                "2025-02-22 08:00:00-08:00",
                "2025-02-23 08:00:00-08:00",
                "2025-02-24 08:00:00-08:00",
                "2025-02-25 08:00:00-08:00",
                "2025-02-26 08:00:00-08:00",
                "2025-02-27 08:00:00-08:00",
                "2025-02-28 08:00:00-08:00",
                "2025-03-01 08:00:00-08:00",
                "2025-03-02 08:00:00-08:00",
                "2025-03-03 08:00:00-08:00",
                "2025-03-04 08:00:00-08:00",
                "2025-03-05 08:00:00-08:00",
                "2025-03-06 08:00:00-08:00",
                "2025-03-07 08:00:00-08:00",
                "2025-03-08 08:00:00-08:00",
                "2025-03-09 09:00:00-07:00",
                "2025-03-10 09:00:00-07:00",
                "2025-03-11 09:00:00-07:00",
            ),
        },
        "2025-10-15T15:30:00-07:00": {
            "~1Day": (
                "2025-10-16 08:00:00-07:00",
                "2025-10-17 08:00:00-07:00",
                "2025-10-18 08:00:00-07:00",
                "2025-10-19 08:00:00-07:00",
                "2025-10-20 08:00:00-07:00",
                "2025-10-21 08:00:00-07:00",
                "2025-10-22 08:00:00-07:00",
                "2025-10-23 08:00:00-07:00",
                "2025-10-24 08:00:00-07:00",
                "2025-10-25 08:00:00-07:00",
                "2025-10-26 08:00:00-07:00",
                "2025-10-27 08:00:00-07:00",
                "2025-10-28 08:00:00-07:00",
                "2025-10-29 08:00:00-07:00",
                "2025-10-30 08:00:00-07:00",
                "2025-10-31 08:00:00-07:00",
                "2025-11-01 08:00:00-07:00",
                "2025-11-02 08:00:00-08:00",
                "2025-11-03 08:00:00-08:00",
                "2025-11-04 08:00:00-08:00",
                "2025-11-05 08:00:00-08:00",
                "2025-11-06 08:00:00-08:00",
                "2025-11-07 08:00:00-08:00",
                "2025-11-08 08:00:00-08:00",
            ),
            "1Day": (
                "2025-10-16 08:00:00-07:00",
                "2025-10-17 08:00:00-07:00",
                "2025-10-18 08:00:00-07:00",
                "2025-10-19 08:00:00-07:00",
                "2025-10-20 08:00:00-07:00",
                "2025-10-21 08:00:00-07:00",
                "2025-10-22 08:00:00-07:00",
                "2025-10-23 08:00:00-07:00",
                "2025-10-24 08:00:00-07:00",
                "2025-10-25 08:00:00-07:00",
                "2025-10-26 08:00:00-07:00",
                "2025-10-27 08:00:00-07:00",
                "2025-10-28 08:00:00-07:00",
                "2025-10-29 08:00:00-07:00",
                "2025-10-30 08:00:00-07:00",
                "2025-10-31 08:00:00-07:00",
                "2025-11-01 08:00:00-07:00",
                "2025-11-02 07:00:00-08:00",
                "2025-11-03 07:00:00-08:00",
                "2025-11-04 07:00:00-08:00",
                "2025-11-05 07:00:00-08:00",
                "2025-11-06 07:00:00-08:00",
                "2025-11-07 07:00:00-08:00",
                "2025-11-08 07:00:00-08:00",
            ),
        },
    }
    ts = TimeSeries.new_regular_time_series(
        name,
        start_time,
        end,
        intvl,
        offset,
        time_zone,
        value,
        quality,
    )
    assert ts.name == name.replace("Inst.0", f"Inst.{intvl.name}")
    assert len(ts) == expected_length
    same = [
        ts.times[i] == expected_times[str(start_time)][intvl.name][i]
        for i in range(expected_length)
    ]
    if not all(same):
        for t1, t2 in list(
            zip(
                expected_times[str(start_time)][intvl.name],
                ts.times,
            )
        ):
            print(f"{t1}\t{t2}\t{t2 == t1}")
    assert all(same)
    if value == 100.0:
        assert ts.values == expected_length * [100.0]
    else:
        assert ts.values == eval(
            "[1.,2.,3.,4.,5.,1.,2.,3.,4.,5.,1.,2.,3.,4.,5.,1.,2.,3.,4.,5.,1.,2.,3.,4.]"
        )
    if isinstance(quality, list):
        assert ts.qualities == eval("[0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3]")
    else:
        assert ts.qualities == expected_length * [3]


def make_test_resample_data() -> list[list[Any]]:
    data = []
    for param_type in [
        "Average",
        "Constant",
        "Instantaneous",
        "Maximum",
        "Minimum",
        "Total",
    ]:
        for param in ("Precip", "Code", "Flow"):
            for op in (
                "count",
                "max",
                "min",
                "prev",
                "interp",
                "integ",
                "volume",
                "average",
                "accum",
            ):
                if op in ("count", "max", "min"):
                    for require_entire_interval in (True, False, None):
                        data.append([param_type, param, op, require_entire_interval])
                else:
                    data.append([param_type, param, op, None])
    if slow_test_coverage < 100:
        data = random_subset(data)
    return data


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_same_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    call_count = 0
    offset = 0
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_1_hour.name}.0.Test",
        "2025-02-01 01:00",
        30,
        intvl_1_hour,
        offset,
        None,
        [100 + i for i in range(30)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Constant": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Instantaneous": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Maximum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Minimum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Total": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            },
            "False": {
                "Average": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Constant": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Instantaneous": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Maximum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Minimum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Total": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            },
            "None": {
                "Average": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Constant": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Instantaneous": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Maximum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Minimum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Total": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            },
        },
        "max": {
            "True": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
            "False": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
            "None": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
        },
        "min": {
            "True": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
            "False": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
            "None": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            },
        },
        "prev": {
            "Average": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Constant": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Instantaneous": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Maximum": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Minimum": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Total": "[math.nan, 100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
        },
        "interp": {
            "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
        },
        "integ": {
            "Average": "[360000., 363600., 367200., 370800., 374400., 378000., 381600., 385200., 388800., 392400., 396000., 399600., 403200., 406800., 410400., 414000., 417600., 421200., 424800., 428400., 432000., 435600., 439200., 442800., 446400., 450000., 453600., 457200., 460800., 464400.]",
            "Constant": "[360000., 363600., 367200., 370800., 374400., 378000., 381600., 385200., 388800., 392400., 396000., 399600., 403200., 406800., 410400., 414000., 417600., 421200., 424800., 428400., 432000., 435600., 439200., 442800., 446400., 450000., 453600., 457200., 460800., 464400.]",
            "Instantaneous": "[360000., 361800., 365400., 369000., 372600., 376200., 379800., 383400., 387000., 390600., 394200., 397800., 401400., 405000., 408600., 412200., 415800., 419400., 423000., 426600., 430200., 433800., 437400., 441000., 444600., 448200., 451800., 455400., 459000., 462600.]",
        },
        "volume": {
            "Average": "[360000., 363600., 367200., 370800., 374400., 378000., 381600., 385200., 388800., 392400., 396000., 399600., 403200., 406800., 410400., 414000., 417600., 421200., 424800., 428400., 432000., 435600., 439200., 442800., 446400., 450000., 453600., 457200., 460800., 464400.]",
            "Constant": "[360000., 363600., 367200., 370800., 374400., 378000., 381600., 385200., 388800., 392400., 396000., 399600., 403200., 406800., 410400., 414000., 417600., 421200., 424800., 428400., 432000., 435600., 439200., 442800., 446400., 450000., 453600., 457200., 460800., 464400.]",
            "Instantaneous": "[360000., 361800., 365400., 369000., 372600., 376200., 379800., 383400., 387000., 390600., 394200., 397800., 401400., 405000., 408600., 412200., 415800., 419400., 423000., 426600., 430200., 433800., 437400., 441000., 444600., 448200., 451800., 455400., 459000., 462600.]",
        },
        "average": {
            "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Instantaneous": "[100., 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5, 110.5, 111.5, 112.5, 113.5, 114.5, 115.5, 116.5, 117.5, 118.5, 119.5, 120.5, 121.5, 122.5, 123.5, 124.5, 125.5, 126.5, 127.5, 128.5]",
            "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Total": "[50., 50.5, 51., 51.5, 52., 52.5, 53., 53.5, 54., 54.5, 55., 55.5, 56., 56.5, 57., 57.5, 58., 58.5, 59., 59.5, 60., 60.5, 61., 61.5, 62., 62.5, 63., 63.5, 64., 64.5]",
        },
        "accum": {
            "Average": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Instantaneous": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
        },
    }
    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_1_hour.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_same_non_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    call_count = 0
    offset = 10
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_1_hour.name}.0.Test",
        "2025-02-01 01:00",
        30,
        intvl_1_hour,
        offset,
        None,
        [100 + i for i in range(30)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
            "False": {
                "Average": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Constant": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Instantaneous": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Maximum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Minimum": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Total": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            },
            "None": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
        },
        "max": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "min": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "prev": {
            "Average": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Constant": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Maximum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Minimum": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
            "Total": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128.]",
        },
        "interp": {
            "Average": "[101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Constant": "[101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Instantaneous": "[100.83333333333333, 101.83333333333333, 102.83333333333333, 103.83333333333333, 104.83333333333333, 105.83333333333333, 106.83333333333333, 107.83333333333333, 108.83333333333333, 109.83333333333333, 110.83333333333333, 111.83333333333333, 112.83333333333333, 113.83333333333333, 114.83333333333333, 115.83333333333333, 116.83333333333333, 117.83333333333333, 118.83333333333333, 119.83333333333333, 120.83333333333333, 121.83333333333333, 122.83333333333333, 123.83333333333333, 124.83333333333333, 125.83333333333333, 126.83333333333333, 127.83333333333333, 128.83333333333334]",
            "Maximum": "[101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Minimum": "[101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124., 125., 126., 127., 128., 129.]",
            "Total": "[84.166667, 85., 85.833333, 86.666667, 87.5, 88.333333, 89.166667, 90., 90.833333, 91.666667, 92.5, 93.333333, 94.166667, 95., 95.833333, 96.666667, 97.5, 98.333333, 99.166667, 100., 100.833333, 101.666667, 102.5, 103.333333, 104.166667, 105., 105.833333, 106.666667, 107.5 ]",
        },
        "integ": {
            "Average": "[363000., 366600., 370200., 373800., 377400., 381000., 384600., 388200., 391800., 395400., 399000., 402600., 406200., 409800., 413400., 417000., 420600., 424200., 427800., 431400., 435000., 438600., 442200., 445800., 449400., 453000., 456600., 460200., 463800.]",
            "Constant": "[363000., 366600., 370200., 373800., 377400., 381000., 384600., 388200., 391800., 395400., 399000., 402600., 406200., 409800., 413400., 417000., 420600., 424200., 427800., 431400., 435000., 438600., 442200., 445800., 449400., 453000., 456600., 460200., 463800.]",
            "Instantaneous": "[301250., 364800., 368400., 372000., 375600., 379200., 382800., 386400., 390000., 393600., 397200., 400800., 404400., 408000., 411600., 415200., 418800., 422400., 426000., 429600., 433200., 436800., 440400., 444000., 447600., 451200., 454800., 458400., 462000.]",
        },
        "volume": {
            "Average": "[363000., 366600., 370200., 373800., 377400., 381000., 384600., 388200., 391800., 395400., 399000., 402600., 406200., 409800., 413400., 417000., 420600., 424200., 427800., 431400., 435000., 438600., 442200., 445800., 449400., 453000., 456600., 460200., 463800.]",
            "Constant": "[363000., 366600., 370200., 373800., 377400., 381000., 384600., 388200., 391800., 395400., 399000., 402600., 406200., 409800., 413400., 417000., 420600., 424200., 427800., 431400., 435000., 438600., 442200., 445800., 449400., 453000., 456600., 460200., 463800.]",
            "Instantaneous": "[301250., 364800., 368400., 372000., 375600., 379200., 382800., 386400., 390000., 393600., 397200., 400800., 404400., 408000., 411600., 415200., 418800., 422400., 426000., 429600., 433200., 436800., 440400., 444000., 447600., 451200., 454800., 458400., 462000.]",
        },
        "average": {
            "Average": "[100.8333333, 101.8333333, 102.8333333, 103.8333333, 104.8333333, 105.8333333, 106.8333333, 107.8333333, 108.8333333, 109.8333333, 110.8333333, 111.8333333, 112.8333333, 113.8333333, 114.8333333, 115.8333333, 116.8333333, 117.8333333, 118.8333333, 119.8333333, 120.8333333, 121.8333333, 122.8333333, 123.8333333, 124.8333333, 125.8333333, 126.8333333, 127.8333333, 128.8333333]",
            "Constant": "[100.8333333, 101.8333333, 102.8333333, 103.8333333, 104.8333333, 105.8333333, 106.8333333, 107.8333333, 108.8333333, 109.8333333, 110.8333333, 111.8333333, 112.8333333, 113.8333333, 114.8333333, 115.8333333, 116.8333333, 117.8333333, 118.8333333, 119.8333333, 120.8333333, 121.8333333, 122.8333333, 123.8333333, 124.8333333, 125.8333333, 126.8333333, 127.8333333, 128.8333333]",
            "Instantaneous": "[100.4166667, 101.3333333, 102.3333333, 103.3333333, 104.3333333, 105.3333333, 106.3333333, 107.3333333, 108.3333333, 109.3333333, 110.3333333, 111.3333333, 112.3333333, 113.3333333, 114.3333333, 115.3333333, 116.3333333, 117.3333333, 118.3333333, 119.3333333, 120.3333333, 121.3333333, 122.3333333, 123.3333333, 124.3333333, 125.3333333, 126.3333333, 127.3333333, 128.3333333]",
            "Maximum": "[100.8333333, 101.8333333, 102.8333333, 103.8333333, 104.8333333, 105.8333333, 106.8333333, 107.8333333, 108.8333333, 109.8333333, 110.8333333, 111.8333333, 112.8333333, 113.8333333, 114.8333333, 115.8333333, 116.8333333, 117.8333333, 118.8333333, 119.8333333, 120.8333333, 121.8333333, 122.8333333, 123.8333333, 124.8333333, 125.8333333, 126.8333333, 127.8333333, 128.8333333]",
            "Minimum": "[100.8333333, 101.8333333, 102.8333333, 103.8333333, 104.8333333, 105.8333333, 106.8333333, 107.8333333, 108.8333333, 109.8333333, 110.8333333, 111.8333333, 112.8333333, 113.8333333, 114.8333333, 115.8333333, 116.8333333, 117.8333333, 118.8333333, 119.8333333, 120.8333333, 121.8333333, 122.8333333, 123.8333333, 124.8333333, 125.8333333, 126.8333333, 127.8333333, 128.8333333]",
            "Total": "[50.347, 50.847, 51.347, 51.847, 52.347, 52.847, 53.347, 53.847, 54.347, 54.847, 55.347, 55.847, 56.347, 56.847, 57.347, 57.847, 58.347, 58.847, 59.347, 59.847, 60.347, 60.847, 61.347, 61.847, 62.347, 62.847, 63.347, 63.847, 64.347]",
        },
        "accum": {
            "Average": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Instantaneous": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Total": "[100.833, 101.833, 102.833, 103.833, 104.833, 105.833, 106.833, 107.833, 108.833, 109.833, 110.833, 111.833, 112.833, 113.833, 114.833, 115.833, 116.833, 117.833, 118.833, 119.833, 120.833, 121.833, 122.833, 123.833, 124.833, 125.833, 126.833, 127.833, 128.833]",
        },
    }

    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_1_hour.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, intvl_1_hour, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op, intvl_1_hour)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_small_to_large_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    intvl_6_hours = Interval.get_cwms("6Hours")
    call_count = 0
    offset = 0
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_1_hour.name}.0.Test",
        "2025-02-01 01:00",
        30,
        intvl_1_hour,
        offset,
        None,
        [100 + i for i in range(30)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[6., 6., 6., 6., 6.]",
                "Constant": "[6., 6., 6., 6., 6.]",
                "Instantaneous": "[6., 6., 6., 6., 6.]",
                "Maximum": "[6., 6., 6., 6., 6.]",
                "Minimum": "[6., 6., 6., 6., 6.]",
                "Total": "[6., 6., 6., 6., 6.]",
            },
            "False": {
                "Average": "[6., 6., 6., 6., 6.]",
                "Constant": "[6., 6., 6., 6., 6.]",
                "Instantaneous": "[6., 6., 6., 6., 6.]",
                "Maximum": "[6., 6., 6., 6., 6.]",
                "Minimum": "[6., 6., 6., 6., 6.]",
                "Total": "[6., 6., 6., 6., 6.]",
            },
            "None": {
                "Average": "[6., 6., 6., 6., 6.]",
                "Constant": "[6., 6., 6., 6., 6.]",
                "Instantaneous": "[6., 6., 6., 6., 6.]",
                "Maximum": "[6., 6., 6., 6., 6.]",
                "Minimum": "[6., 6., 6., 6., 6.]",
                "Total": "[6., 6., 6., 6., 6.]",
            },
        },
        "max": {
            "True": {
                "Average": "[105., 111., 117., 123., 129.]",
                "Constant": "[105., 111., 117., 123., 129.]",
                "Instantaneous": "[105., 111., 117., 123., 129.]",
                "Maximum": "[105., 111., 117., 123., 129.]",
                "Minimum": "[105., 111., 117., 123., 129.]",
                "Total": "[105., 111., 117., 123., 129.]",
            },
            "False": {
                "Average": "[105., 111., 117., 123., 129.]",
                "Constant": "[105., 111., 117., 123., 129.]",
                "Instantaneous": "[105., 111., 117., 123., 129.]",
                "Maximum": "[105., 111., 117., 123., 129.]",
                "Minimum": "[105., 111., 117., 123., 129.]",
                "Total": "[105., 111., 117., 123., 129.]",
            },
            "None": {
                "Average": "[105., 111., 117., 123., 129.]",
                "Constant": "[105., 111., 117., 123., 129.]",
                "Instantaneous": "[105., 111., 117., 123., 129.]",
                "Maximum": "[105., 111., 117., 123., 129.]",
                "Minimum": "[105., 111., 117., 123., 129.]",
                "Total": "[105., 111., 117., 123., 129.]",
            },
        },
        "min": {
            "True": {
                "Average": "[100., 106., 112., 118., 124.]",
                "Constant": "[100., 106., 112., 118., 124.]",
                "Instantaneous": "[100., 106., 112., 118., 124.]",
                "Maximum": "[100., 106., 112., 118., 124.]",
                "Minimum": "[100., 106., 112., 118., 124.]",
                "Total": "[100., 106., 112., 118., 124.]",
            },
            "False": {
                "Average": "[100., 106., 112., 118., 124.]",
                "Constant": "[100., 106., 112., 118., 124.]",
                "Instantaneous": "[100., 106., 112., 118., 124.]",
                "Maximum": "[100., 106., 112., 118., 124.]",
                "Minimum": "[100., 106., 112., 118., 124.]",
                "Total": "[100., 106., 112., 118., 124.]",
            },
            "None": {
                "Average": "[100., 106., 112., 118., 124.]",
                "Constant": "[100., 106., 112., 118., 124.]",
                "Instantaneous": "[100., 106., 112., 118., 124.]",
                "Maximum": "[100., 106., 112., 118., 124.]",
                "Minimum": "[100., 106., 112., 118., 124.]",
                "Total": "[100., 106., 112., 118., 124.]",
            },
        },
        "prev": {
            "Average": "[104., 110., 116., 122., 128.]",
            "Constant": "[104., 110., 116., 122., 128.]",
            "Instantaneous": "[104., 110., 116., 122., 128.]",
            "Maximum": "[104., 110., 116., 122., 128.]",
            "Minimum": "[104., 110., 116., 122., 128.]",
            "Total": "[104., 110., 116., 122., 128.]",
        },
        "interp": {
            "Average": "[105., 111., 117., 123., 129.]",
            "Constant": "[105., 111., 117., 123., 129.]",
            "Instantaneous": "[105., 111., 117., 123., 129.]",
            "Maximum": "[105., 111., 117., 123., 129.]",
            "Minimum": "[105., 111., 117., 123., 129.]",
            "Total": "[105., 111., 117., 123., 129.]",
        },
        "integ": {
            "Average": "[2214000., 2343600., 2473200., 2602800., 2732400.]",
            "Constant": "[2214000., 2343600., 2473200., 2602800., 2732400.]",
            "Instantaneous": "[1845000., 2332800., 2462400., 2592000., 2721600.]",
        },
        "volume": {
            "Average": "[2214000., 2343600., 2473200., 2602800., 2732400.]",
            "Constant": "[2214000., 2343600., 2473200., 2602800., 2732400.]",
            "Instantaneous": "[1845000., 2332800., 2462400., 2592000., 2721600.]",
        },
        "average": {
            "Average": "[102.5, 108.5, 114.5, 120.5, 126.5]",
            "Constant": "[102.5, 108.5, 114.5, 120.5, 126.5]",
            "Instantaneous": "[102.5, 108., 114., 120., 126.]",
            "Maximum": "[102.5, 108.5, 114.5, 120.5, 126.5]",
            "Minimum": "[102.5, 108.5, 114.5, 120.5, 126.5]",
            "Total": "[51.25, 54.25, 57.25, 60.25, 63.25]",
        },
        "accum": {
            "Average": "[math.nan, 6., 6., 6., 6.]",
            "Instantaneous": "[math.nan, 6., 6., 6., 6.]",
            "Total": "[615., 651., 687., 723., 759.]",
        },
    }

    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_6_hours.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, intvl_6_hours, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op, intvl_6_hours)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            # print(f"error     = {message}")
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_large_to_small_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    intvl_6_hours = Interval.get_cwms("6Hours")
    call_count = 0
    offset = 0
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_1_hour.name}.0.Test",
        "2025-02-01 06:00",
        5,
        intvl_6_hours,
        offset,
        None,
        [100 + 6 * i for i in range(5)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
            "False": {
                "Average": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Constant": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Instantaneous": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Maximum": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Minimum": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Total": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
            },
            "None": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
        },
        "max": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Constant": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Maximum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Minimum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Total": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "min": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Constant": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Maximum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Minimum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Total": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan, 124.]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "prev": {
            "Average": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Constant": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Instantaneous": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Maximum": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Minimum": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Total": "[math.nan, 100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
        },
        "interp": {
            "Average": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Constant": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Instantaneous": "[100., 101., 102., 103., 104., 105., 106., 107., 108., 109., 110., 111., 112., 113., 114., 115., 116., 117., 118., 119., 120., 121., 122., 123., 124.]",
            "Maximum": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Minimum": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Total": "[100., 17.6666667, 35.3333333, 53., 70.6666667, 88.3333333, 106., 18.6666667, 37.3333333, 56., 74.6666667, 93.3333333, 112., 19.6666667, 39.3333333, 59.00, 78.6666667, 98.3333333, 118., 20.6666667, 41.3333333, 62., 82.6666667, 103.3333333, 124.]",
        },
        "integ": {
            "Average": "[360000, 381600., 381600., 381600., 381600., 381600., 381600., 403200., 403200., 403200., 403200., 403200., 403200., 424800., 424800., 424800., 424800., 424800., 424800., 446400., 446400., 446400., 446400., 446400., 446400.]",
            "Constant": "[360000, 381600., 381600., 381600., 381600., 381600., 381600., 403200., 403200., 403200., 403200., 403200., 403200., 424800., 424800., 424800., 424800., 424800., 424800., 446400., 446400., 446400., 446400., 446400., 446400.]",
            "Instantaneous": "[math.nan, 361800., 365400., 369000., 372600., 376200., 379800., 383400., 387000., 390600., 394200., 397800., 401400., 405000., 408600., 412200., 415800., 419400., 423000., 426600., 430200., 433800., 437400., 441000., 444600.]",
        },
        "volume": {
            "Average": "[360000., 381600., 381600., 381600., 381600., 381600., 381600., 403200., 403200., 403200., 403200., 403200., 403200., 424800., 424800., 424800., 424800., 424800., 424800., 446400., 446400., 446400., 446400., 446400., 446400.]",
            "Constant": "[360000., 381600., 381600., 381600., 381600., 381600., 381600., 403200., 403200., 403200., 403200., 403200., 403200., 424800., 424800., 424800., 424800., 424800., 424800., 446400., 446400., 446400., 446400., 446400., 446400.]",
            "Instantaneous": "[math.nan, 361800., 365400., 369000., 372600., 376200., 379800., 383400., 387000., 390600., 394200., 397800., 401400., 405000., 408600., 412200., 415800., 419400., 423000., 426600., 430200., 433800., 437400., 441000., 444600.]",
        },
        "average": {
            "Average": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Constant": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Instantaneous": "[math.nan, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5, 110.5, 111.5, 112.5, 113.5, 114.5, 115.5, 116.5, 117.5, 118.5, 119.5, 120.5, 121.5, 122.5, 123.5]",
            "Maximum": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Minimum": "[100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Total": "[91.6666667, 8.8333333, 26.5, 44.1666667, 61.8333333, 79.5, 97.1666667, 9.3333333, 28., 46.6666667, 65.3333333, 84., 102.6666667, 9.8333333, 29.5, 49.1666667, 68.8333333, 88.5, 108.1666667, 10.3333333, 31., 51.6666667, 72.3333333, 93., 113.6666667]",
        },
        "accum": {
            "Average": "[math.nan, 6., 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0.]",
            "Instantaneous": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Total": "[16.6666667, 17.6666667, 17.6666667, 17.6666667, 17.6666667, 17.6666667, 17.6666667, 18.6666667, 18.6666667, 18.6666667, 18.6666667, 18.6666667, 18.6666667, 19.6666667, 19.6666667, 19.6666667, 19.6666667, 19.6666667, 19.6666667, 20.6666667, 20.6666667, 20.6666667, 20.6666667, 20.6666667, 20.6666667]",
        },
    }
    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_1_hour.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, intvl_1_hour, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op, intvl_1_hour)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            # print(f"error     = {message}")
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_small_to_large_non_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    intvl_6_hours = Interval.get_cwms("6Hours")
    call_count = 0
    offset = 10
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_1_hour.name}.0.Test",
        "2025-02-01 01:00",
        30,
        intvl_1_hour,
        offset,
        None,
        [100 + i for i in range(30)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[5., 5., 5., 5., 5.]",
                "Constant": "[5., 5., 5., 5., 5.]",
                "Instantaneous": "[5., 5., 5., 5., 5.]",
                "Maximum": "[5., 5., 5., 5., 5.]",
                "Minimum": "[5., 5., 5., 5., 5.]",
                "Total": "[5., 5., 5., 5., 5.]",
            },
            "False": {
                "Average": "[5., 6., 6., 6., 6.]",
                "Constant": "[5., 6., 6., 6., 6.]",
                "Instantaneous": "[5., 6., 6., 6., 6.]",
                "Maximum": "[5., 6., 6., 6., 6.]",
                "Minimum": "[5., 6., 6., 6., 6.]",
                "Total": "[5., 6., 6., 6., 6.]",
            },
            "None": {
                "Average": "[5., 5., 5., 5., 5.]",
                "Constant": "[5., 5., 5., 5., 5.]",
                "Instantaneous": "[5., 6., 6., 6., 6.]",
                "Maximum": "[5., 5., 5., 5., 5.]",
                "Minimum": "[5., 5., 5., 5., 5.]",
                "Total": "[5., 5., 5., 5., 5.]",
            },
        },
        "max": {
            "True": {
                "Average": "[104., 110., 116., 122., 128.]",
                "Constant": "[104., 110., 116., 122., 128.]",
                "Instantaneous": "[104., 110., 116., 122., 128.]",
                "Maximum": "[104., 110., 116., 122., 128.]",
                "Minimum": "[104., 110., 116., 122., 128.]",
                "Total": "[104., 110., 116., 122., 128.]",
            },
            "False": {
                "Average": "[104., 110., 116., 122., 128.]",
                "Constant": "[104., 110., 116., 122., 128.]",
                "Instantaneous": "[104., 110., 116., 122., 128.]",
                "Maximum": "[104., 110., 116., 122., 128.]",
                "Minimum": "[104., 110., 116., 122., 128.]",
                "Total": "[104., 110., 116., 122., 128.]",
            },
            "None": {
                "Average": "[104., 110., 116., 122., 128.]",
                "Constant": "[104., 110., 116., 122., 128.]",
                "Instantaneous": "[104., 110., 116., 122., 128.]",
                "Maximum": "[104., 110., 116., 122., 128.]",
                "Minimum": "[104., 110., 116., 122., 128.]",
                "Total": "[104., 110., 116., 122., 128.]",
            },
        },
        "min": {
            "True": {
                "Average": "[100., 106., 112., 118., 124.]",
                "Constant": "[100., 106., 112., 118., 124.]",
                "Instantaneous": "[100., 106., 112., 118., 124.]",
                "Maximum": "[100., 106., 112., 118., 124.]",
                "Minimum": "[100., 106., 112., 118., 124.]",
                "Total": "[100., 106., 112., 118., 124.]",
            },
            "False": {
                "Average": "[100., 105., 111., 117., 123.]",
                "Constant": "[100., 105., 111., 117., 123.]",
                "Instantaneous": "[100., 105., 111., 117., 123.]",
                "Maximum": "[100., 105., 111., 117., 123.]",
                "Minimum": "[100., 105., 111., 117., 123.]",
                "Total": "[100., 105., 111., 117., 123.]",
            },
            "None": {
                "Average": "[100., 106., 112., 118., 124.]",
                "Constant": "[100., 106., 112., 118., 124.]",
                "Instantaneous": "[100., 105., 111., 117., 123.]",
                "Maximum": "[100., 106., 112., 118., 124.]",
                "Minimum": "[100., 106., 112., 118., 124.]",
                "Total": "[100., 106., 112., 118., 124.]",
            },
        },
        "prev": {
            "Average": "[104., 110., 116., 122., 128.]",
            "Constant": "[104., 110., 116., 122., 128.]",
            "Instantaneous": "[104., 110., 116., 122., 128.]",
            "Maximum": "[104., 110., 116., 122., 128.]",
            "Minimum": "[104., 110., 116., 122., 128.]",
            "Total": "[104., 110., 116., 122., 128.]",
        },
        "interp": {
            "Average": "[105., 111., 117., 123., 129.]",
            "Constant": "[105., 111., 117., 123., 129.]",
            "Instantaneous": "[104.8333333, 110.8333333, 116.8333333, 122.8333333, 128.8333333]",
            "Maximum": "[105., 111., 117., 123., 129.]",
            "Minimum": "[105., 111., 117., 123., 129.]",
            "Total": "[87.5, 92.5, 97.5, 102.5, 107.5]",
        },
        "integ": {
            "Average": "[2151000., 2340000., 2469600., 2599200., 2728800.]",
            "Constant": "[2151000., 2340000., 2469600., 2599200., 2728800.]",
            "Instantaneous": "[1782050., 2329200., 2458800., 2588400., 2718000.]",
        },
        "volume": {
            "Average": "[2151000., 2340000., 2469600., 2599200., 2728800.]",
            "Constant": "[2151000., 2340000., 2469600., 2599200., 2728800.]",
            "Instantaneous": "[1782050., 2329200., 2458800., 2588400., 2718000.]",
        },
        "average": {
            "Average": "[102.428571, 108.3333333, 114.3333333, 120.3333333, 126.3333333]",
            "Constant": "[102.428571, 108.3333333, 114.3333333, 120.3333333, 126.3333333]",
            "Instantaneous": "[102.4166667, 107.8333333, 113.8333333, 119.8333333, 125.8333333]",
            "Maximum": "[102.428571, 108.3333333, 114.3333333, 120.3333333, 126.3333333]",
            "Minimum": "[102.428571, 108.3333333, 114.3333333, 120.3333333, 126.3333333]",
            "Total": "[49.964, 54.097, 57.097, 60.097, 63.097]",
        },
        "accum": {
            "Average": "[math.nan, 6., 6., 6., 6.]",
            "Instantaneous": "[math.nan, 6., 6., 6., 6.]",
            "Total": "[514.17, 650., 686., 722., 758.]",
        },
    }
    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_6_hours.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, intvl_6_hours, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op, intvl_6_hours)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            # print(f"error     = {message}")
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )


@pytest.mark.parametrize(
    "param_type, param, op, require_entire_interval", make_test_resample_data()
)
def test_resample_large_to_small_non_aligned(
    param_type: str, param: str, op: str, require_entire_interval: Optional[bool]
) -> None:
    intvl_1_hour = Interval.get_cwms("1Hour")
    intvl_6_hours = Interval.get_cwms("6Hours")
    call_count = 0
    offset = 15
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_6_hours.name}.0.Test",
        "2025-02-01 06:00",
        5,
        intvl_6_hours,
        offset,
        None,
        [100 + 6 * i for i in range(5)],
    )
    expected_values = {
        "count": {
            "True": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
            "False": {
                "Average": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Constant": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Maximum": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Minimum": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Total": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
            },
            "None": {
                "Average": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Constant": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Instantaneous": "[1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.]",
                "Maximum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Minimum": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
                "Total": "[0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]",
            },
        },
        "max": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "min": {
            "True": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "False": {
                "Average": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
            "None": {
                "Average": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Constant": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Instantaneous": "[100., math.nan, math.nan, math.nan, math.nan, math.nan, 106., math.nan, math.nan, math.nan, math.nan, math.nan, 112., math.nan, math.nan, math.nan, math.nan, math.nan, 118., math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Maximum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Minimum": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
                "Total": "[math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]",
            },
        },
        "prev": {
            "Average": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Constant": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Instantaneous": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Maximum": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Minimum": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
            "Total": "[100., 100., 100., 100., 100., 100., 106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118.]",
        },
        "interp": {
            "Average": "[106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Constant": "[106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Instantaneous": "[100.75, 101.75, 102.75, 103.75, 104.75, 105.75, 106.75, 107.75, 108.75, 109.75, 110.75, 111.75, 112.75, 113.75, 114.75, 115.75, 116.75, 117.75, 118.75, 119.75, 120.75, 121.75, 122.75, 123.75]",
            "Maximum": "[106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Minimum": "[106., 106., 106., 106., 106., 106., 112., 112., 112., 112., 112., 112., 118., 118., 118., 118., 118., 118., 124., 124., 124., 124., 124., 124.]",
            "Total": "[13.25, 30.9166667, 48.5833333, 66.25, 83.9166667, 101.5833333, 14., 32.6666667, 51.3333333, 70., 88.6666667, 107.3333333, 14.75, 34.4166667, 54.0833333, 73.75, 93.4166667, 113.0833333, 15.5, 36.1666667, 56.8333333, 77.5, 98.1666667, 118.8333333]",
        },
        "integ": {
            "Average": "[376200., 381600., 381600., 381600., 381600., 381600., 397800., 403200., 403200., 403200., 403200., 403200., 419400., 424800., 424800., 424800., 424800., 424800., 441000., 446400., 446400., 446400., 446400., 446400.]",
            "Constant": "[376200., 381600., 381600., 381600., 381600., 381600., 397800., 403200., 403200., 403200., 403200., 403200., 419400., 424800., 424800., 424800., 424800., 424800., 441000., 446400., 446400., 446400., 446400., 446400.]",
            "Instantaneous": "[271012.5, 364500., 368100., 371700., 375300., 378900., 382500., 386100., 389700., 393300., 396900., 400500., 404100., 407700., 411300., 414900., 418500., 422100., 425700., 429300., 432900., 436500., 440100., 443700., ]",
        },
        "volume": {
            "Average": "[376200., 381600., 381600., 381600., 381600., 381600., 397800., 403200., 403200., 403200., 403200., 403200., 419400., 424800., 424800., 424800., 424800., 424800., 441000., 446400., 446400., 446400., 446400., 446400.]",
            "Constant": "[376200., 381600., 381600., 381600., 381600., 381600., 397800., 403200., 403200., 403200., 403200., 403200., 419400., 424800., 424800., 424800., 424800., 424800., 441000., 446400., 446400., 446400., 446400., 446400.]",
            "Instantaneous": "[271012.5, 364500., 368100., 371700., 375300., 378900., 382500., 386100., 389700., 393300., 396900., 400500., 404100., 407700., 411300., 414900., 418500., 422100., 425700., 429300., 432900., 436500., 440100., 443700., ]",
        },
        "average": {
            "Average": "[104.5, 106., 106., 106., 106., 106., 110.5, 112., 112., 112., 112., 112., 116.5, 118., 118., 118., 118., 118., 122.5, 124., 124., 124., 124., 124.]",
            "Constant": "[104.5, 106., 106., 106., 106., 106., 110.5, 112., 112., 112., 112., 112., 116.5, 118., 118., 118., 118., 118., 122.5, 124., 124., 124., 124., 124.]",
            "Instantaneous": "[100.375, 101.25, 102.25, 103.25, 104.25, 105.25, 106.25, 107.25, 108.25, 109.25, 110.25, 111.25, 112.25, 113.25, 114.25, 115.25, 116.25, 117.25, 118.25, 119.25, 120.25, 121.25, 122.25, 123.25]",
            "Maximum": "[104.5, 106., 106., 106., 106., 106., 110.5, 112., 112., 112., 112., 112., 116.5, 118., 118., 118., 118., 118., 122.5, 124., 124., 124., 124., 124.]",
            "Minimum": "[104.5, 106., 106., 106., 106., 106., 110.5, 112., 112., 112., 112., 112., 116.5, 118., 118., 118., 118., 118., 122.5, 124., 124., 124., 124., 124.]",
            "Total": "[29.448, 22.0833333, 39.75, 57.4166667, 75.0833333, 92.75, 31.198, 23.3333333, 42., 60.6666667, 79.3333333, 98., 32.948, 24.5833333, 44.25, 63.9166667, 83.5833333, 103.25, 34.698, 25.8333333, 46.5, 67.1666667, 87.8333333, 108.5]",
        },
        "accum": {
            "Average": "[math.nan, 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0., 6., 0., 0., 0., 0., 0.]",
            "Instantaneous": "[math.nan, 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.]",
            "Total": "[17.4166667, 17.6666667, 17.6666667, 17.6666667, 17.6666667, 17.6666667, 18.4166667, 18.6666667, 18.6666667, 18.6666667, 18.6666667, 18.6666667, 19.4166667, 19.6666667, 19.6666667, 19.6666667, 19.6666667, 19.6666667, 20.4166667, 20.6666667, 20.6666667, 20.6666667, 20.6666667, 20.6666667]",
        },
    }

    parameter_type = ParameterType(param_type, "CWMS")
    ts.iset_parameter_type(parameter_type)
    expected_param_type_name = {
        "count": "Total",
        "max": "Max",
        "min": "Min",
        "prev": parameter_type.name,
        "interp": parameter_type.name,
        "integ": parameter_type.name,
        "volume": parameter_type.name,
        "average": "Ave",
        "accum": parameter_type.name,
    }
    ts.iset_parameter(param)
    expected_param_name = {
        "count": f"Count-{param}",
        "max": param,
        "min": param,
        "prev": param,
        "interp": param,
        "integ": "Volume",  # after integration
        "volume": "Volume",  # after integration
        "average": param,
        "accum": param,
    }
    expected_unit = {
        "count": "unit",
        "max": ts.unit,
        "min": ts.unit,
        "prev": ts.unit,
        "interp": ts.unit,
        "integ": "ft3",  # after integration
        "volume": "ft3",  # after integration
        "average": ts.unit,
        "accum": ts.unit,
    }
    expected_name = f"Loc.{expected_param_name[op]}.{expected_param_type_name[op]}.{intvl_1_hour.name}.0.Test"
    if op in ("count", "max", "min"):
        ts2 = ts.resample(op, intvl_1_hour, entire_interval=require_entire_interval)
        call_count += 1
        assert ts2.name == expected_name
        assert ts2.unit == expected_unit[op]
        assert np.allclose(
            ts2.values,
            eval(
                expected_values[op][str(require_entire_interval)][  # type: ignore
                    param_type
                ]
            ),
            equal_nan=True,
        )
    else:
        try:
            ts2 = ts.resample(op, intvl_1_hour)
            call_count += 1
        except TimeSeriesException as tse:
            message = str(tse)
            if op in ("integ", "volume"):
                assert (
                    message.find("Cannot perform VOLUME") != -1
                    or message.find("Cannot perform INTEGRATE") != -1
                )
            elif op == "accum":
                assert message.find(f"Cannot perform ACCUMULATE") != -1
            else:
                raise
        else:
            assert ts2.name == expected_name
            assert ts2.unit == expected_unit[op]
            assert np.allclose(
                ts2.values,
                eval(expected_values[op][param_type]),  # type: ignore
                equal_nan=True,
            )
    # ------------------------------------- #
    # period constants and shift adjustment #
    # ------------------------------------- #
    offset = 0
    ts = TimeSeries.new_regular_time_series(
        f"Loc.Code.Inst.{intvl_6_hours.name}.0.Test",
        "2025-02-01 06:00",
        5,
        intvl_6_hours,
        offset,
        None,
        [100 + 6 * i for i in range(5)],
    )
    tsvs = [
        TimeSeriesValue("2025-02-01 05:00", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-01 05:45", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-01 06:15", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-01 06:45", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-01 18:45", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-02 03:00", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-02 06:15", UQ("n/a"), 0),
        TimeSeriesValue("2025-02-02 06:45", UQ("n/a"), 0),
    ]
    its = TimeSeries("Loc.Code.Inst.0.0.Test")
    its._data = pd.DataFrame(
        {
            "value": [tsv.value.magnitude for tsv in tsvs],
            "quality": [tsv.quality.code for tsv in tsvs],
        },
        index=pd.DatetimeIndex(
            [cast(datetime, tsv.time.datetime()) for tsv in tsvs], name="time"
        ),
    )

    expected_values = {
        "Period Constants": "[math.nan, math.nan, 100.0, 100.0, 112.0, 118.0, 124.0, 124.0]",
        "Shift Adjustment": "[0.0, 0.0, 100.25, 100.75, 112.75, 121.0, 124.0, 124.0]",
    }
    ts2 = ts.resample("prev", its, before="missing", after="last")
    call_count += 1
    assert np.allclose(
        eval(expected_values["Period Constants"]), ts2.values, equal_nan=True  # type: ignore
    )

    ts2 = ts.resample("interp", its, before=0.0, after="last")
    call_count += 1
    assert np.allclose(
        eval(expected_values["Shift Adjustment"]), ts2.values, equal_nan=True  # type: ignore
    )


test_cyclic_analysis_inputs = [
    [
        "./test/resources/timeseries/CyclicAnalysisData.dss",
        "//TestLoc/Flow//1Month/GMT/",
    ],
    ["./test/resources/timeseries/CyclicAnalysisData.dss", "//TestLoc/Flow//1Day/GMT/"],
    [
        "./test/resources/timeseries/CyclicAnalysisData.dss",
        "//TestLoc/Flow//1Hour/GMT/",
    ],
]


@pytest.mark.parametrize("dss_filename, pathname", test_cyclic_analysis_inputs)
def test_cyclic_analysis(dss_filename: str, pathname: str) -> None:
    DssDataStore.set_message_level(0)
    dss = DssDataStore.open(dss_filename)
    ts = cast(TimeSeries, dss.retrieve(pathname))
    results = ts.cyclic_analysis(method="hecmath")
    for computed in results:
        expected = cast(TimeSeries, dss.retrieve(computed.name))
        if not computed.times == expected.times:
            print(computed.name)
            for t1, t2 in list(zip(expected.times, computed.times)):
                print(f"{t1}\t{t2}\t{t2 == t1}")
        assert computed.times == expected.times
        if computed.parameter.basename == "Date" and computed.interval.name != "1Year":
            # hecmath only has year on these time series
            expected.iselect(Select.ALL)
            expected.imap(lambda v: float(int(v)))
        if not np.allclose(computed.values, expected.values, equal_nan=True):
            print(computed.name)
            for t, v1, v2 in list(
                zip(expected.times, expected.values, computed.values)
            ):
                same = np.isclose(v1, v2, equal_nan=True)
                print(f"{t}\t{v1}\t{v2}\t{same}")
            assert computed.values == expected.values


def run_test_timed(test_name: str) -> None:
    print(f"Running {test_name}")
    ts1 = datetime.now()
    try:
        if test_name == "test_cyclic_analysis":
            for dss_filename, pathname in test_cyclic_analysis_inputs:
                ts_a = datetime.now()
                test_cyclic_analysis(dss_filename, pathname)
                ts_b = datetime.now()
                print(f"\t...{pathname} in {(ts_b - ts_a)}")
        else:
            exec(f"{test_name}()")
    except:
        traceback.print_exc()
    ts2 = datetime.now()
    print(f"...completed in {ts2 - ts1}")


if __name__ == "__main__":
    run_test_timed("test_time_series_value")
    run_test_timed("test_create_time_series_by_name")
    run_test_timed("test_math_ops_scalar")
    run_test_timed("test_math_ops_ts")
    run_test_timed("test_selection_and_filter")
    run_test_timed("test_aggregate_ts")
    run_test_timed("test_aggregate_values")
    run_test_timed("test_min_max")
    run_test_timed("test_accum_diff")
    run_test_timed("test_value_counts")
    run_test_timed("test_unit")
    run_test_timed("test_roundoff")
    run_test_timed("test_smoothing")
    run_test_timed("test_protected")
    run_test_timed("test_screen_with_value_range")
    run_test_timed("test_screen_with_value_change_rate")
    run_test_timed("test_screen_with_value_range_or_change_rate")
    run_test_timed("test_screen_with_duration_magnitude")
    run_test_timed("test_screen_with_constant_value")
    run_test_timed("test_screen_with_forward_moving_average")
    run_test_timed("test_estimate_missing_values")
    run_test_timed("test_expand_collapse_trim")
    run_test_timed("test_merge")
    run_test_timed("test_to_irregular")
    run_test_timed("test_snap_to_regular")
    run_test_timed("test_new_regular_time_series")
    run_test_timed("test_resample")
    run_test_timed("test_cyclic_analysis")
