from hec.timeseries import TimeSeries
from hec.timeseries import TimeSeriesValue
from hec.hectime import HecTime
from hec.unit import UnitQuantity as UQ
from hec.quality import Quality as Qual
from hec.duration import Duration
from datetime import timedelta
from typing import cast


def test_time_series_value() -> None:
    # --------------------------------------- #
    # - create TSV without specifying quality #
    # --------------------------------------- #
    tsv = TimeSeriesValue("14Oct2024 10:55", UQ(230, "cfs"))
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 10, 55, 0], MINUTE_GRANULARITY), UnitQuantity(230, 'cfs'), Quality(0))"
    )
    assert str(tsv) == "(2024-10-14T10:55:00, 230 cfs, u)"
    assert tsv.time == HecTime("2024-10-14T10:55:00")
    assert tsv.value == UQ(230, "cfs")
    # --------------------------------- #
    # create TSV with quality specified #
    # --------------------------------- #
    assert (
        tsv.quality.text
        == "Unprotected Unscreened Unknown No_Range Original None None None"
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
        tsv.quality.text == "Unprotected Screened Okay No_Range Original None None None"
    )
    # -------------------------------------- #
    # modify TSV (modify value without unit) #
    # -------------------------------------- #
    tsv.time += timedelta(minutes=65)
    tsv.value += 0.7
    tsv.quality = Qual("missing").setProtection(1)
    assert (
        repr(tsv)
        == "TimeSeriesValue(HecTime([2024, 10, 14, 12, 0, 0], MINUTE_GRANULARITY), UnitQuantity(13.0, 'ft'), Quality(-2147483643))"
    )
    assert str(tsv) == "(2024-10-14T12:00:00, 13.0 ft, M)"
    assert tsv.time == HecTime("2024-10-14T12:00:00")
    assert tsv.value == UQ(13, "ft")
    assert (
        tsv.quality.text
        == "Protected Screened Missing No_Range Original None None None"
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
        == "Protected Screened Missing No_Range Original None None None"
    )


def test_create_time_series_by_name() -> None:
    ts = TimeSeries("SWT/Keystone.Elev-Pool.Inst.1Hour.0.Raw-Goes")
    assert ts.name == "SWT/Keystone.Elev-Pool.Inst.1Hour.0.Raw-Goes"
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
