"""Module for testing hec.interval module
"""

import datetime
import sys
import zoneinfo
from test.shared import dataset_from_file, random_subset, scriptdir, slow_test_coverage
from typing import Any, List, Optional, Union, cast

import pytest

from hec import HecTime, Interval, IntervalException, TimeSpan


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
        "IR-Day",
        "IR-Month",
        "IR-Year",
        "IR-Decade",
        "IR-Century",
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
        "IR-Day",
        "IR-Month",
        "IR-Year",
        "IR-Decade",
        "IR-Century",
    ]
    assert Interval.get_all_dss_names(lambda i: i.minutes == 720) == [
        "12Hour",
    ]
    assert Interval.get_all_dss_block_names() == [
        "1Day",
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


def test_get_dss() -> None:
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


def generate_one_expected_data(
    interval: Interval,
    start_time: HecTime,
    end_time: Optional[HecTime],
    count: Optional[int],
    offset: Optional[Any],
    time_zone: Optional[str],
) -> list[datetime.datetime]:
    sys.stderr.write(
        f"{interval.name},{start_time},{end_time},{count},{offset},{time_zone}\n"
    )
    l_ts1 = datetime.datetime.now()
    l_start_time = cast(HecTime, start_time.clone()).label_as_time_zone(time_zone)
    l_start_time.midnight_as_2400 = False
    l_interval = (
        Interval.get_any(lambda i: i.minutes == interval.minutes and i.is_regular)
        if not interval.is_local_regular
        else interval
    )
    assert l_interval is not None
    if end_time is not None:
        l_end_time = cast(HecTime, end_time.clone()).label_as_time_zone(time_zone)
        l_end_time.midnight_as_2400 = False
        l_start_minutes = cast(int, l_start_time.julian()) * 1440 + cast(
            int, l_start_time.minutes_since_midnight()
        )
        l_end_minutes = cast(int, l_end_time.julian()) * 1440 + cast(
            int, l_end_time.minutes_since_midnight()
        )
        l_count = int((l_end_minutes - l_start_minutes) / l_interval.minutes * 1.1)
    else:
        l_count = cast(int, count)
        l_end_time = None
    if offset is None:
        l_first_time = l_start_time
    else:
        l_interval_begin = cast(
            HecTime, l_start_time.clone()
        ).adjust_to_interval_offset(l_interval, 0)
        l_first_time = l_interval_begin + offset
        if l_first_time < l_start_time:
            l_interval_begin.increment(1, l_interval)
            l_first_time = l_interval_begin + offset
    if time_zone:
        if l_interval.is_local_regular:
            l_first_time = l_first_time.label_as_time_zone("UTC", on_already_set=0)
            if l_end_time is not None:
                l_end_time = l_end_time.label_as_time_zone("UTC", on_already_set=0)
        else:
            l_first_time = l_first_time.convert_to_time_zone("UTC")
            if l_end_time is not None:
                l_end_time = l_end_time.convert_to_time_zone("UTC")
    l_hectimes = [
        cast(HecTime, l_first_time.clone()).increment(i, l_interval)
        for i in range(l_count)
    ]
    if l_end_time is not None:
        while l_hectimes[-1] > l_end_time:
            l_hectimes.pop()
    if time_zone:
        if l_interval.is_local_regular:
            l_hectimes = [
                ht.label_as_time_zone(time_zone, on_already_set=0) for ht in l_hectimes
            ]
        else:
            l_hectimes = [ht.convert_to_time_zone(time_zone) for ht in l_hectimes]
    l_datetimes = [cast(datetime.datetime, ht.datetime()) for ht in l_hectimes]
    l_ts2 = datetime.datetime.now()
    sys.stderr.write(f"{l_ts2 - l_ts1}\n")
    return l_datetimes


def generate_datetime_index_expected_data() -> None:
    """
    Redirect stdout to data file. stderr will show progress and any errors
    """
    l_intervals_used = set()
    for l_interval in Interval.get_all(lambda i: i.is_any_regular):
        l_info = (l_interval.minutes, l_interval.is_local_regular)
        if l_info in l_intervals_used:
            continue
        l_intervals_used.add(l_info)
        for l_start_time in (
            HecTime("2025-01-01T01:01:00"),
            HecTime("2025-01-31T08:00:00"),
        ):
            l_count = 20 if l_interval.minutes < 3650 * 1440 else 2
            l_end_time = cast(HecTime, l_start_time.clone()).increment(
                l_count, l_interval
            )
            for l_offset in (
                None,
                0,
                datetime.timedelta(minutes=l_interval.minutes / 2),
            ):
                for l_time_zone in (None, "UTC", "US/Pacific"):
                    if l_time_zone is None and l_interval.is_local_regular:
                        continue
                    l_datetimes = generate_one_expected_data(
                        l_interval, l_start_time, None, l_count, l_offset, l_time_zone
                    )
                    print(
                        f"{l_interval.name}/{l_start_time}/None/{l_count}/{repr(l_offset)}/{l_time_zone}\t{'|'.join(map(repr, l_datetimes))}"
                    )
                    l_datetimes = generate_one_expected_data(
                        l_interval,
                        l_start_time,
                        l_end_time,
                        None,
                        l_offset,
                        l_time_zone,
                    )
                    print(
                        f"{l_interval.name}/{l_start_time}/{l_end_time}/None/{repr(l_offset)}/{l_time_zone}\t{'|'.join(map(repr, l_datetimes))}"
                    )


@pytest.mark.slow
@pytest.mark.parametrize(
    "key, times_str",
    dataset_from_file("resources/interval/datetime_index-data.tsv", slow=True),
)
def test_get_datetime_index(key: str, times_str: str) -> None:
    l_keyparts = key.split("/", 5)
    l_intvl = Interval.get_any(lambda i: i.name == l_keyparts[0] and i.is_any_regular)
    assert l_intvl is not None
    l_start_time = HecTime(l_keyparts[1])
    l_end_time: Optional[HecTime] = None
    l_count: Optional[int] = None
    l_offset: Union[int, datetime.timedelta]
    if l_keyparts[2] == "None":
        l_count = int(l_keyparts[3])
    else:
        l_end_time = HecTime(l_keyparts[2])
    l_offset = eval(l_keyparts[4])
    l_time_zone: Optional[str] = l_keyparts[5]
    if l_time_zone == "None":
        l_time_zone = None
    l_expected = list(map(eval, times_str.split("|")))

    l_indx = l_intvl.get_datetime_index(
        l_start_time, l_end_time, l_count, l_offset, l_time_zone
    )
    l_actual = l_indx.to_list()
    l_okay = l_expected == l_actual
    if not l_okay:
        print("*** ERROR ***")
        print(f"intvl={l_intvl.name}")
        print(f"start_time={l_start_time}")
        print(f"end_time={l_end_time}")
        print(f"count={l_count}")
        print(f"offset={repr(l_offset)}")
        print(f"time_zone={l_time_zone}")
        print(f"len(expected)={len(l_expected)}")
        print(f"len(actual)={len(l_actual)}")
        for v1, v2 in list(zip(l_expected, l_actual)):
            print(f"{v1}{chr(9)}{v2}{chr(9)}{v2 == v1}")
    assert l_okay


if __name__ == "__main__":
    pass
    # t = HecTime("2025-01-31T00:00:00").label_as_time_zone("UTC")
    # i = Interval.get_any_cwms(lambda i: i.name == "~1Month" and i.is_local_regular)
    # t.increment(1, i)
    # l_datetimes = generate_one_expected_data(Interval.get_any_cwms(lambda i: i.name == "~1Month" and i.is_local_regular),HecTime("2025-01-31T00:00:00"),None,20,None,"UTC")
    # for dt in l_datetimes: print(dt)
    # generate_datetime_index_expected_data()
    data = "~1Year/2025-01-01T01:01:00/None/20/datetime.timedelta(days=182, seconds=43200)/US/Pacific-datetime.datetime(2025, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2026, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2027, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2028, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2029, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2030, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2031, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2032, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2033, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2034, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2035, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2036, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2037, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2038, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2039, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2040, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2041, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2042, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2043, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))|datetime.datetime(2044, 7, 2, 13, 0, tzinfo=zoneinfo.ZoneInfo(key='US/Pacific'))"
    key, times_str = data.replace("-datetime", "\tdatetime").split("\t")
    test_get_datetime_index(key, times_str)
