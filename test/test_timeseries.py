from hec.timeseries import TimeSeriesValue as TSV
from hec.hectime import HecTime
from hec.unit import UnitQuantity as UQ
from hec.quality import Quality as Qual
from datetime import timedelta


def test_time_series_value() -> None:
    # --------------------------------------- #
    # - create TSV without specifying quality #
    # --------------------------------------- #
    tsv = TSV("14Oct2024 10:55", UQ(230, "cfs"))
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
    tsv = TSV("14Oct2024 10:55", UQ(12.3, "ft"), Qual("okay"))
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
