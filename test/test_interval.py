"""Module for testing hec.interval module
"""

from hec import Interval, IntervalException


def test_get_all() -> None:
    assert Interval.get_all_cwms_names() == [
        "0",
        "Irr",
        "~1Minute",
        "~2Minutes",
        "~3Minutes",
        "~4Minutes",
        "~5Minutes",
        "~6Minutes",
        "~10Minutes",
        "~12Minutes",
        "~15Minutes",
        "~20Minutes",
        "~30Minutes",
        "~1Hour",
        "~2Hours",
        "~3Hours",
        "~4Hours",
        "~6Hours",
        "~8Hours",
        "~12Hours",
        "~1Day",
        "~2Days",
        "~3Days",
        "~4Days",
        "~5Days",
        "~6Days",
        "~1Week",
        "~1Month",
        "~1Year",
        "1Minute",
        "2Minutes",
        "3Minutes",
        "4Minutes",
        "5Minutes",
        "6Minutes",
        "10Minutes",
        "12Minutes",
        "15Minutes",
        "20Minutes",
        "30Minutes",
        "1Hour",
        "2Hours",
        "3Hours",
        "4Hours",
        "6Hours",
        "8Hours",
        "12Hours",
        "1Day",
        "2Days",
        "3Days",
        "4Days",
        "5Days",
        "6Days",
        "1Week",
        "1Month",
        "1Year",
    ]
    assert Interval.get_all_cwms_names(lambda i: i.is_irregular) == [
        "0",
        "Irr",
    ]
    assert Interval.get_all_cwms_names(lambda i: i.minutes == 720) == [
        "12Hours",
        "~12Hours",
    ]
    assert Interval.get_all_dss_names() == [
        "Ir-Day",
        "Ir-Month",
        "Ir-Year",
        "Ir-Decade",
        "Ir-Century",
        "~1Minute",
        "~2Minute",
        "~3Minute",
        "~4Minute",
        "~5Minute",
        "~6Minute",
        "~10Minute",
        "~12Minute",
        "~15Minute",
        "~20Minute",
        "~30Minute",
        "~1Hour",
        "~2Hour",
        "~3Hour",
        "~4Hour",
        "~6Hour",
        "~8Hour",
        "~12Hour",
        "~1Day",
        "~2Day",
        "~3Day",
        "~4Day",
        "~5Day",
        "~6Day",
        "~1Week",
        "~1Month",
        "~1Year",
        "1Minute",
        "2Minute",
        "3Minute",
        "4Minute",
        "5Minute",
        "6Minute",
        "10Minute",
        "12Minute",
        "15Minute",
        "20Minute",
        "30Minute",
        "1Hour",
        "2Hour",
        "3Hour",
        "4Hour",
        "6Hour",
        "8Hour",
        "12Hour",
        "1Day",
        "2Day",
        "3Day",
        "4Day",
        "5Day",
        "6Day",
        "1Week",
        "Tri-Month",
        "Semi-Month",
        "1Month",
        "1Year",
    ]
    assert Interval.get_all_dss_names(lambda i: i.is_irregular) == [
        "Ir-Day",
        "Ir-Month",
        "Ir-Year",
        "Ir-Decade",
        "Ir-Century",
    ]
    assert Interval.get_all_dss_names(lambda i: i.minutes == 720) == [
        "12Hour",
    ]
    assert Interval.get_all_dss_block_names() == [
        "1Month",
        "1Year",
        "1Decade",
        "1Century",
    ]
    assert Interval.get_all_dss_block_names(lambda i: i.is_irregular) == []


def test_get_any() -> None:
    assert Interval.get_any_cwms_name(lambda i: i.minutes == 720) == "12Hours"
    assert Interval.get_any_dss_name(lambda i: i.minutes == 720) == "12Hour"
    i = Interval.get_any_cwms(lambda i: i.name == "12Hours")
    assert i is not None
    assert i.minutes == 720
    assert i.name == "12Hours"
    i = Interval.get_any_dss(lambda i: i.name == "12Hour")
    assert i is not None
    assert i.minutes == 720
    assert i.name == "12Hour"
    assert Interval.get_any_dss(lambda i: i.name == "12Hours") is None


def test_get_cwms() -> None:
    intvl = Interval.get_cwms("1Month")
    assert intvl.name == "1Month"
    assert intvl.minutes == 43200
    intvl = Interval.get_cwms(720)
    assert intvl.name == "12Hours"
    assert intvl.minutes == 720
    exception_raised = False
    try:
        intvl = Interval.get_cwms("12Hour")
    except Exception as e:
        exception_raised = True
        assert isinstance(e, IntervalException)
    assert exception_raised
    exception_raised = False
    try:
        intvl = Interval.get_cwms(intvl)  # type: ignore
    except Exception as e:
        exception_raised = True
        assert isinstance(e, TypeError)
    assert exception_raised


def get_get_dss() -> None:
    intvl = Interval.get_dss("1Month")
    assert intvl.name == "1Month"
    assert intvl.minutes == 43200
    intvl = Interval.get_dss(720)
    assert intvl.name == "12Hour"
    assert intvl.minutes == 720
    exception_raised = False
    try:
        intvl = Interval.get_dss("12Hours")
    except Exception as e:
        exception_raised = True
        assert isinstance(e, IntervalException)
    assert exception_raised
    exception_raised = False
    try:
        intvl = Interval.get_dss(intvl)  # type: ignore
    except Exception as e:
        exception_raised = True
        assert isinstance(e, TypeError)
    assert exception_raised
