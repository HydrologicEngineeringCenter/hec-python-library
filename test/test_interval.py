"""Module for testing hec.interval module
"""

from hec.interval import Interval, IntervalException


def test_get_all() -> None:
    assert Interval.getAllCwmsNames() == [
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
    assert Interval.getAllCwmsNames(lambda i: i.is_irregular) == [
        "0",
        "Irr",
    ]
    assert Interval.getAllCwmsNames(lambda i: i.minutes == 720) == [
        "12Hours",
        "~12Hours",
    ]
    assert Interval.getAllDssNames() == [
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
    assert Interval.getAllDssNames(lambda i: i.is_irregular) == [
        "Ir-Day",
        "Ir-Month",
        "Ir-Year",
        "Ir-Decade",
        "Ir-Century",
    ]
    assert Interval.getAllDssNames(lambda i: i.minutes == 720) == [
        "12Hour",
    ]
    assert Interval.getAllDssBlockNames() == [
        "1Month",
        "1Year",
        "1Decade",
        "1Century",
    ]
    assert Interval.getAllDssBlockNames(lambda i: i.is_irregular) == []


def test_get_any() -> None:
    assert Interval.getAnyCwmsName(lambda i: i.minutes == 720) == "12Hours"
    assert Interval.getAnyDssName(lambda i: i.minutes == 720) == "12Hour"
    i = Interval.getAnyCwms(lambda i: i.name == "12Hours")
    assert i is not None
    assert i.minutes == 720
    assert i.name == "12Hours"
    i = Interval.getAnyDss(lambda i: i.name == "12Hour")
    assert i is not None
    assert i.minutes == 720
    assert i.name == "12Hour"
    assert Interval.getAnyDss(lambda i: i.name == "12Hours") is None


def test_getCwms() -> None:
    intvl = Interval.getCwms("1Month")
    assert intvl.name == "1Month"
    assert intvl.minutes == 43200
    intvl = Interval.getCwms(720)
    assert intvl.name == "12Hours"
    assert intvl.minutes == 720
    exception_raised = False
    try:
        intvl = Interval.getCwms("12Hour")
    except Exception as e:
        exception_raised = True
        assert isinstance(e, IntervalException)
    assert exception_raised
    exception_raised = False
    try:
        intvl = Interval.getCwms(intvl)  # type: ignore
    except Exception as e:
        exception_raised = True
        assert isinstance(e, TypeError)
    assert exception_raised


def test_getDss() -> None:
    intvl = Interval.getDss("1Month")
    assert intvl.name == "1Month"
    assert intvl.minutes == 43200
    intvl = Interval.getDss(720)
    assert intvl.name == "12Hour"
    assert intvl.minutes == 720
    exception_raised = False
    try:
        intvl = Interval.getDss("12Hours")
    except Exception as e:
        exception_raised = True
        assert isinstance(e, IntervalException)
    assert exception_raised
    exception_raised = False
    try:
        intvl = Interval.getDss(intvl)  # type: ignore
    except Exception as e:
        exception_raised = True
        assert isinstance(e, TypeError)
    assert exception_raised
