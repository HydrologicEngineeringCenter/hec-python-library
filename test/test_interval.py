"""Module for testing hec.interval module
"""

import datetime
import pytest
import sys
import zoneinfo

from test.shared import dataset_from_file, random_subset, scriptdir, slow_test_coverage
from typing import Any, List, Optional, Union, cast

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
    ):
    sys.stderr.write(f"{interval.name},{start_time},{end_time},{count},{offset},{time_zone}\n")
    l_ts1 = datetime.datetime.now()
    l_start_time = cast(HecTime, start_time.clone()).label_as_time_zone("UTC" if interval.is_local_regular else time_zone)
    l_start_time.midnight_as_2400 = False
    l_interval = Interval.get_any(lambda i: i.minutes == interval.minutes and i. is_regular) if interval.is_local_regular else interval
    if end_time is not None:
        l_end_time = cast(HecTime, end_time.clone()).label_as_time_zone("UTC" if interval.is_local_regular else time_zone)
        l_end_time.midnight_as_2400 = False
        l_start_minutes = l_start_time.julian() * 1440 + l_start_time.minutes_since_midnight()
        l_end_minutes = l_end_time.julian() * 1440 + l_end_time.minutes_since_midnight()
        l_count = int((l_end_minutes - l_start_minutes) / l_interval.minutes * 1.1)
    else:
        l_count = count
    if offset is None:
        if time_zone:
            l_start_time.label_as_time_zone("UTC", on_already_set=0)
            l_hectimes = [cast(HecTime, l_start_time.clone()).increment(i, l_interval).label_as_time_zone(time_zone, on_already_set=0) for i in range(l_count)]
        else:
            l_hectimes = [cast(HecTime, l_start_time.clone()).increment(i, l_interval) for i in range(l_count)]
    else:
        l_interval_begin = cast(HecTime, l_start_time.clone()).adjust_to_interval_offset(l_interval, 0)
        l_first_time = l_interval_begin + offset
        if l_first_time < l_start_time:
            l_interval_begin.increment(1, l_interval)
        if time_zone:
            l_hectimes = [cast(HecTime, l_interval_begin.clone()).increment(i, l_interval).increment(1, offset) for i in range(l_count)]
        else:
            l_hectimes = [cast(HecTime, l_interval_begin.clone()).increment(i, l_interval).increment(1, offset) for i in range(l_count)]
    if interval.is_local_regular:
        l_hectimes = [ht.label_as_time_zone(time_zone, on_already_set=0) for ht in l_hectimes]
    if end_time is not None:
        l_end_time.label_as_time_zone(time_zone, on_already_set=0)
        while l_hectimes[-1] > l_end_time:
            l_hectimes.pop()
    l_datetimes = [ht.datetime() for ht in l_hectimes]
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
        for l_start_time in (HecTime('2025-01-01T01:01:00'), HecTime('2025-01-31T08:00:00')):
            l_count = 20 if l_interval.minutes < 3650 * 1440 else 2
            l_end_time = cast(HecTime, l_start_time.clone()).increment(l_count, l_interval)
            for l_offset in (None, 0, datetime.timedelta(minutes=l_interval.minutes / 2)):
                for l_time_zone in (None, 'UTC', 'US/Pacific'):
                    if l_time_zone is None and l_interval.is_local_regular:
                        continue
                    l_datetimes = generate_one_expected_data(l_interval, l_start_time, None, l_count, l_offset, l_time_zone)
                    print(f"{l_interval.name}/{l_start_time}/None/{l_count}/{repr(l_offset)}/{l_time_zone}\t{'|'.join(map(repr, l_datetimes))}")
                    l_datetimes = generate_one_expected_data(l_interval, l_start_time, l_end_time, None, l_offset, l_time_zone)
                    print(f"{l_interval.name}/{l_start_time}/{l_end_time}/None/{repr(l_offset)}/{l_time_zone}\t{'|'.join(map(repr, l_datetimes))}")

@pytest.mark.slow
@pytest.mark.parametrize(
    "key, times_str", dataset_from_file("resources/interval/datetime_index-data.tsv", slow=True)
)
def test_get_datetime_index(key: str, times_str: str) -> None:
    keyparts = key.split("/", 5)
    intvl = Interval.get_any(lambda i: i.name == keyparts[0] and i.is_any_regular)
    start_time = HecTime(keyparts[1])
    end_time: Optional[HecTime] = None
    count: Optional[int] = None
    offset: Union[int, datetime.timedelta]
    if keyparts[2] == "None":
        count = int(keyparts[3])
    else:
        end_time = HecTime(keyparts[2])
    offset = eval(keyparts[4])
    time_zone = keyparts[5]
    if time_zone == "None":
        time_zone = None
    expected = list(map(eval, times_str.split("|")))
    
    indx = intvl.get_datetime_index(
        start_time, end_time, count, offset, time_zone
    )
    actual = indx.to_list()
    okay = expected == actual
    if not okay:
        print("*** ERROR ***")
        print(f"intvl={intvl.name}")
        print(f"start_time={start_time}")
        print(f"end_time={end_time}")
        print(f"count={count}")
        print(f"offset={repr(offset)}")
        print(f"time_zone={time_zone}")
        print(f"len(expected)={len(expected)}")
        print(f"len(actual)={len(actual)}")
        for v1, v2 in list(zip(expected, actual)):
            print(f"{v1}{chr(9)}{v2}{chr(9)}{v2 == v1}")
    assert okay


if __name__ == "__main__":
    # generate_one_expected_data(Interval.get_any_cwms(lambda i: i.minutes == 1 and i.is_local_regular),HecTime("2025-01-01T01:01:00"),HecTime("2025-01-01T01:21:00"),None,0,"US/Pacific")
    # generate_datetime_index_expected_data()
    # data = "1Year/2025-01-01T01:01:00/2045-01-01T01:01:00/None/None/None-datetime.datetime(2025, 1, 1, 1, 1)|datetime.datetime(2026, 1, 1, 1, 1)|datetime.datetime(2027, 1, 1, 1, 1)|datetime.datetime(2028, 1, 1, 1, 1)|datetime.datetime(2029, 1, 1, 1, 1)|datetime.datetime(2030, 1, 1, 1, 1)|datetime.datetime(2031, 1, 1, 1, 1)|datetime.datetime(2032, 1, 1, 1, 1)|datetime.datetime(2033, 1, 1, 1, 1)|datetime.datetime(2034, 1, 1, 1, 1)|datetime.datetime(2035, 1, 1, 1, 1)|datetime.datetime(2036, 1, 1, 1, 1)|datetime.datetime(2037, 1, 1, 1, 1)|datetime.datetime(2038, 1, 1, 1, 1)|datetime.datetime(2039, 1, 1, 1, 1)|datetime.datetime(2040, 1, 1, 1, 1)|datetime.datetime(2041, 1, 1, 1, 1)|datetime.datetime(2042, 1, 1, 1, 1)|datetime.datetime(2043, 1, 1, 1, 1)|datetime.datetime(2044, 1, 1, 1, 1)|datetime.datetime(2045, 1, 1, 1, 1)"
    # key, times_str = data.replace("-datetime", "\tdatetime").split("\t")
    # test_get_datetime_index(key, times_str)

    intvl = Interval.get_cwms("1Year")
    indx = intvl.get_datetime_index(
        start_time=HecTime("2025-01-01 00:00:00"),
        count=12,
        offset=datetime.timedelta(days=130),
        time_zone=None,
    )
    for datetime in indx: print(datetime)
