"""Module for testing hec.hectime module"""

import os
import time
from datetime import datetime, timedelta
from test.shared import dataset_from_file, random_subset, scriptdir, slow_test_coverage
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest
import tzlocal

from hec import HecTime, Interval, TimeSpan, hectime

Y, M, D, H, N, S = range(6)

# ----------------------------------------------------- #
# set up a dictionary of HecTime objects by granularity #
# ----------------------------------------------------- #
hectimes: dict[int, HecTime] = {g: HecTime(g) for g in hectime.GRANULARITIES}

# --------------------------------------------------- #
# set the file names for the time data by granularity #
# --------------------------------------------------- #
time_data_filenames: dict[int, str] = {
    hectime.SECOND_GRANULARITY: os.path.join(
        scriptdir, "resources/hectime/second_granularity.txt"
    ),
    hectime.MINUTE_GRANULARITY: os.path.join(
        scriptdir, "resources/hectime/minute_granularity.txt"
    ),
    hectime.HOUR_GRANULARITY: os.path.join(
        scriptdir, "resources/hectime/hour_granularity.txt"
    ),
    hectime.DAY_GRANULARITY: os.path.join(
        scriptdir, "resources/hectime/day_granularity.txt"
    ),
}


# ------------------------ #
# test hectime.add_century #
# ------------------------ #
@pytest.mark.parametrize(
    "_y, _expected", dataset_from_file("resources/hectime/add_century.txt")
)
def test_add_century(_y: str, _expected: str) -> None:
    y, expected = tuple(map(int, (_y, _expected)))
    if y >= 100:
        # legitimate non-2-digit years, behavior differs from Java HecTime.addCentury
        assert hectime.add_century(y) == y
    else:
        # same behavior as Java HecTime.addCentury
        assert hectime.add_century(y) == expected


# ----------------------- #
# test hectime.clean_time #
# ----------------------- #
@pytest.mark.parametrize(
    "_time, _expected", dataset_from_file("resources/hectime/clean_times.txt")
)
def test_clean_time(_time: str, _expected: str) -> None:
    time: list[int] = eval(_time)
    expected: list[int] = eval(_expected)
    hectime.clean_time(time)
    assert time == expected


# ------------------------------------------------ #
# test hectime.compute_number_intervals            #
#                                                  #
# runs 43500 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
INTERVALS = [
    Interval.get_any(lambda i: i.minutes == m)
    for m in sorted(set([m for m in Interval.MINUTES.values() if m > 0]))
]
if slow_test_coverage < 100:
    INTERVALS = random_subset(INTERVALS)


@pytest.mark.slow
@pytest.mark.parametrize(
    "time1, time2", dataset_from_file("resources/hectime/interval_count.txt", slow=True)
)
def test_compute_number_intervals(time1: str, time2: str) -> None:
    t1 = HecTime(time1)
    t2 = HecTime(time2)
    for interval in INTERVALS:
        assert interval is not None
        count = t1.compute_number_intervals(t2, interval)
        t3 = HecTime(t1)
        t3.increment(count, interval)
        assert t3 <= t2
        t3.increment(1, interval)
        assert t3 >= t2


# --------------------------------------------------------- #
# test hectime.convert_time_zone, HecTime.convert_time_zone #
# --------------------------------------------------------- #
@pytest.mark.parametrize(
    "time1, from_tz, to_tz, time2",
    dataset_from_file("resources/hectime/convert_timezone.txt"),
)
def test_convert_time_zone(time1: str, from_tz: str, to_tz: str, time2: str) -> None:
    t = HecTime(time1)
    hectime.convert_time_zone(t, ZoneInfo(from_tz), ZoneInfo(to_tz))
    assert t.date_and_time(-13) == time2
    t = HecTime(time1)
    t.convert_time_zone(ZoneInfo(from_tz), ZoneInfo(to_tz))
    assert t.date_and_time(-13) == time2


# ------------------------------------ #
# test hectime.curtime, hectime.systim #
# ------------------------------------ #
def test_curtim() -> None:
    julian, minute = [0], [0]
    julian2, timeval = [0], [0]
    now = datetime.now()
    timevals = 6 * [0]
    while now.second == 59:
        time.sleep(0.25)
        now = datetime.now()
    hectime.curtim(julian, minute)
    hectime.julian_to_year_month_day(julian[0], timevals)
    timevals[H], timevals[N] = divmod(minute[0], 60)
    assert timevals[:5] == [now.year, now.month, now.day, now.hour, now.minute]
    hectime.systim(julian2, timeval)
    assert julian2[0] == julian[0]
    assert abs(timeval[0] // 60 - minute[0]) < 60
    hectime.systim(julian2, timeval, True)
    assert [julian2[0], timeval[0]] == [julian[0], minute[0]]
    hectime.systim(julian2, timeval, True, "UTC")
    diff1 = (julian2[0] * 1440 + timeval[0]) - (julian[0] * 1440 + minute[0])
    diff2 = (
        -(
            cast(timedelta, now.replace(tzinfo=tzlocal.get_localzone()).utcoffset())
        ).total_seconds()
        // 60
    )
    assert diff1 == diff2


# ------------------------------------------------ #
# test hectime.datcln, hectime.normalize_time_vals #
# ------------------------------------------------ #
@pytest.mark.parametrize(
    "_time, _expected", dataset_from_file("resources/hectime/clean_times.txt")
)
def test_datcln(_time: str, _expected: str) -> None:
    time: list[int] = eval(_time)
    expected: list[int] = eval(_expected)
    if len(time) == 2:
        julian_clean = [0]
        minute_clean = [0]
        hectime.datcln(time[0], time[1], julian_clean, minute_clean)
        assert julian_clean[0] == expected[0]
        assert minute_clean[0] == expected[1]
    elif len(time) == 6:
        hectime.normalize_time_vals(time)
        assert time == expected


# --------------------------------------------------------------------------- #
# test hectime.datjul, hectime.datymd, hectime.iymdjl, hectime.jliymd,        #
# hectime.juldat, hectime.ymddat                                              #
# exercises hectime.parse_date_time_str, hectime.juilan_to_year_month_day,    #
# hectime.year_month_day_to_julian                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "datestr, _jul, _y, _m, _d", dataset_from_file("resources/hectime/dat_jul_ymd.txt")
)
def test_dat_jul_ymd(datestr: str, _jul: str, _y: str, _m: str, _d: str) -> None:
    jul, y, m, d = list(map(int, (_jul, _y, _m, _d)))
    julian = [0]
    hectime.datjul(datestr, julian)
    assert julian[0] == jul
    ymd = 6 * [0]
    hectime.datymd(datestr, ymd)
    assert ymd[:3] == [y, m, d]
    assert hectime.iymdjl(y, m, d) == jul
    ymd = 6 * [0]
    hectime.jliymd(jul, ymd)
    assert ymd[:3] == [y, m, d]
    assert hectime.juldat(jul, 4) == datestr
    err = [0]
    assert hectime.ymddat(ymd, 4, err) == datestr


# ----------------------------------------------- #
# test hectime.getime and hectime.get_time_window #
# ----------------------------------------------- #
@pytest.mark.parametrize(
    "tw_str, start_time, end_time, _juls, _mins, _jule, _mine",
    dataset_from_file("resources/hectime/time_window.txt"),
)
def test_get_time_window__getime(
    tw_str: str,
    start_time: str,
    end_time: str,
    _juls: str,
    _mins: str,
    _jule: str,
    _mine: str,
) -> None:
    t_start: HecTime = HecTime()
    t_end: HecTime = HecTime()
    juls, mins, jule, mine = list(map(int, (_juls, _mins, _jule, _mine)))
    jul_start = [0]
    min_start = [0]
    jul_end = [0]
    min_end = [0]
    status = [0]
    hectime.get_time_window(tw_str, t_start, t_end)
    assert t_start.date_and_time(-13) == start_time
    assert t_end.date_and_time(-13) == end_time
    hectime.getime(tw_str, jul_start, min_start, jul_end, min_end, status)
    assert status[0] == 0
    assert jul_start[0] == juls
    assert min_start[0] == mins
    assert jul_end[0] == jule
    assert min_end[0] == mine


# -------------------------------------------------------------------------------------- #
# test hectime.m2hm, hectime.ihm2m, hectime.ihm2m_2, hectime.min2ihm, and hectime.min2hm #
# -------------------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "_minutes, timestr", dataset_from_file("resources/hectime/hour_minute.txt")
)
def test_m_hm(_minutes: str, timestr: str) -> None:
    minutes = int(_minutes)
    timestr2 = [""]
    assert hectime.m2hm(minutes) == int(timestr)
    assert hectime.m2ihm(minutes, timestr2) == int(timestr)
    assert timestr2[0] == timestr
    assert hectime.hm2m(timestr) == minutes
    assert hectime.hm2m(int(timestr)) == minutes
    assert hectime.ihm2m(timestr) == minutes
    assert hectime.ihm2m_2("~".join(list(timestr))) == minutes


# ------------------------------------------------------------------ #
# test hectime.idaywk, HecTime.day_of_week, HecTime.day_of_week_name #
# ------------------------------------------------------------------ #
@pytest.mark.parametrize(
    "datestr, _jul, _weekday, dayname",
    dataset_from_file("resources/hectime/weekday.txt"),
)
def test_weekday(datestr: str, _jul: str, _weekday: str, dayname: str) -> None:
    jul, weekday = list(map(int, (_jul, _weekday)))
    assert hectime.idaywk(jul) == weekday
    t = HecTime(datestr)
    t.midnight_as_2400 = False
    assert hectime.idaywk(cast(list[int], t.values)) == weekday
    assert t.day_of_week() == weekday
    assert t.day_of_week_name() == dayname


# ------------------------------------------------ #
# test HecTime.increment, hectime.inctim           #
# exercises hectime.increment_time_vals            #
#                                                  #
# runs 63510 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
@pytest.mark.slow
@pytest.mark.parametrize(
    "start_time, _interval, _count, end_time",
    dataset_from_file("resources/hectime/increment.txt", slow=True),
)
def test_increment(start_time: str, _interval: str, _count: str, end_time: str) -> None:
    interval = int(_interval)
    count = int(_count)
    t = HecTime(start_time)
    t2 = HecTime(t)
    t2.increment(count, interval)
    assert t2.date_and_time(-13) == end_time
    intvl = Interval.get_any(lambda i: i.minutes == interval)
    assert intvl is not None
    t2 = HecTime(t)
    t2.increment(count, intvl)
    assert t2.date_and_time(-13) == end_time
    ts = TimeSpan(str(intvl)) + timedelta(minutes=10)
    t3 = HecTime(t)
    t3.increment(count, ts)
    t4 = HecTime(end_time)
    t4 += count * timedelta(minutes=10)
    assert t3 == t4
    start_jul = t.julian()
    start_min = t.minutes_since_midnight()
    end_jul = [0]
    end_min = [0]
    hectime.inctim(interval, count, start_jul, start_min, end_jul, end_min)
    assert end_jul[0] == t2.julian()
    assert end_min[0] == t2.minutes_since_midnight()
    if intvl.minutes <= Interval.MINUTES["1Week"]:
        # --------------------------------- #
        # can't use calendar info in inctim #
        # --------------------------------- #
        intvl = Interval.get_any(lambda i: i.minutes == interval)
        assert intvl is not None
        end_jul = [0]
        end_min = [0]
        hectime.inctim(intvl, count, start_jul, start_min, end_jul, end_min)
        assert end_jul[0] == t2.julian()
        assert end_min[0] == t2.minutes_since_midnight()
        ts = TimeSpan(str(intvl)) + timedelta(minutes=10)
        end_jul = [0]
        end_min = [0]
        hectime.inctim(ts, count, start_jul, start_min, end_jul, end_min)
        assert end_jul[0] == t4.julian()
        assert end_min[0] == t4.minutes_since_midnight()


# ------------------------------------------------------ #
# test HecTime.adjust_to_interval_offset, hectime.zofset #
# ------------------------------------------------------ #
@pytest.mark.parametrize(
    "time1, _interval, _offset, time2",
    dataset_from_file("resources/hectime/adjust_to_interval_offset.txt"),
)
def test_interval_offset(time1: str, _interval: str, _offset: str, time2: str) -> None:
    interval = int(_interval)
    month_based = interval > 10080
    offset = int(_offset)
    jul0, min0 = [0], [0]
    jul1, min1 = [0], [0]
    jul2, min2 = [0], [0]
    ofst = [0]
    t = HecTime()
    t.midnight_as_2400 = False
    t.set(time1)
    jul0[0] = jul1[0] = cast(int, t.julian())
    min0[0] = min1[0] = cast(int, t.minutes_since_midnight())
    computed_offset = t.get_interval_offset(interval)
    t.adjust_to_interval_offset(interval, offset)
    assert t.date_and_time(-13) == time2
    jul2[0] = cast(int, t.julian())
    min2[0] = cast(int, t.minutes_since_midnight())
    ofst[0] = -1
    hectime.zofset(jul1, min1, interval, 0, ofst)
    assert jul1 == jul0
    assert min1 == min0
    if not month_based:
        assert ofst[0] == computed_offset
    ofst[0] = -1
    hectime.zofset(jul1, min1, interval, 1, ofst)
    if not month_based:
        assert (jul2[0] * 1440 + min2[0]) - (jul1[0] * 1440 + min1[0]) == offset
        assert ofst[0] == computed_offset
    jul1[0] = jul0[0]
    min1[0] = min0[0]
    ofst[0] = -1
    hectime.zofset(jul1, min1, interval, 2, ofst)
    if not month_based:
        assert (jul2[0] * 1440 + min2[0]) - (jul1[0] * 1440 + min1[0]) == offset
    assert ofst[0] == -1


# -------------------------------- #
# test HecTime.get_interval_offset #
# -------------------------------- #
@pytest.mark.parametrize(
    "timestr, _interval, _expected_offset",
    dataset_from_file("resources/hectime/interval_offset.txt"),
)
def test_get_interval_offset(
    timestr: str, _interval: str, _expected_offset: int
) -> None:
    interval = int(_interval)
    expected_offset = int(_expected_offset)
    t = HecTime(timestr)
    assert t.get_interval_offset(interval) == expected_offset


# ----------------------------------------------------------------------------------------- #
# read the files and build the data sets for initializing from time integer and time values #
# ----------------------------------------------------------------------------------------- #
int_test_data: list[tuple[HecTime, int, list[int]]] = []
list_test_data: list[tuple[HecTime, list[int], int]] = []
for granularity in hectime.GRANULARITIES:
    ht = HecTime(granularity)
    ht.midnight_as_2400 = False
    with open(time_data_filenames[granularity]) as f:
        lines = f.read().strip().split("\n")
    for line in lines:
        parts = line.split("\t")
        time_int = int(parts[0])
        time_vals = eval(parts[1])
        int_test_data.append((ht, time_int, time_vals))
        list_test_data.append((ht, time_vals, time_int))
    if slow_test_coverage < 100:
        int_test_data = random_subset(int_test_data)
        list_test_data = random_subset(list_test_data)


# ------------------------------------------------ #
# test initializing from time integer              #
# runs 40004 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
@pytest.mark.slow
@pytest.mark.parametrize("ht, timeint, expected_time_vals", int_test_data)
def test_initialize_hectime_from_integer(
    ht: HecTime, timeint: int, expected_time_vals: list[int]
) -> None:
    assert ht.set(timeint) == 0
    assert ht.values == expected_time_vals


# ------------------------------------------------ #
# test initializing from time values list          #
# runs 40004 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
@pytest.mark.slow
@pytest.mark.parametrize("ht, timevals, expected_time_int", list_test_data)
def test_initialize_hectime_from_list(
    ht: HecTime, timevals: list[int], expected_time_int: int
) -> None:
    assert ht.set(timevals) == 0
    assert ht.value == expected_time_int


# ------------------------------- #
# test initializing from a string #
# ------------------------------- #
@pytest.mark.parametrize(
    "_string, _time_vals_2400, _time_vals_0000",
    dataset_from_file("resources/hectime/string_date_times.txt"),
)
def test_initialize_hectime_from_string(
    _string: str, _time_vals_2400: str, _time_vals_0000: str
) -> None:
    string = _string.strip("'\"")
    time_vals_0000 = [int(item) for item in eval(_time_vals_0000)]
    t = HecTime(hectime.SECOND_GRANULARITY)
    t.midnight_as_2400 = False
    assert t.set(string) == 0
    assert t.values == time_vals_0000


# ---------------------- #
# test midnight settings #
# ---------------------- #
@pytest.mark.parametrize(
    "_string, _time_vals_2400, _time_vals_0000",
    dataset_from_file("resources/hectime/string_date_times.txt"),
)
def test_midnight_settings(
    _string: str, _time_vals_2400: str, _time_vals_0000: str
) -> None:
    time_vals_0000 = [int(item) for item in eval(_time_vals_0000)]
    time_vals_2400 = [int(item) for item in eval(_time_vals_2400)]
    t = HecTime(hectime.SECOND_GRANULARITY)
    t.midnight_as_2400 = True
    assert t.set(time_vals_0000) == 0
    assert t.values == time_vals_2400
    t.midnight_as_2400 = False
    assert t.values == time_vals_0000


# ------------------------- #
# test date and time styles #
# ------------------------- #
@pytest.mark.parametrize(
    "_style, _granularity, _expected",
    dataset_from_file("resources/hectime/date_time_styles.txt"),
)
def test_date_time_style(_style: str, _granularity: str, _expected: str) -> None:
    style = int(_style)
    granularity = int(_granularity)
    expected = _expected.strip("\"'")
    ht = HecTime(int(granularity))
    ht.midnight_as_2400 = False
    assert ht.set([2024, 1, 2, 3, 4, 5]) == 0
    assert ht.date_and_time(int(style)) == expected


# ---------------------------------------------------------- #
# test setting from datetime and retrieving datetime objects #
# ---------------------------------------------------------- #
def test_to_from_datetime() -> None:
    dt = datetime(2024, 8, 15, 10, 53, 12)
    ht = HecTime(dt)
    assert ht.datetime() == dt.replace(second=0)
    ht = HecTime(hectime.SECOND_GRANULARITY)
    ht.set(dt)
    assert ht.datetime() == dt
    ht = ht.label_as_time_zone("UTC")
    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    assert ht.convert_to_time_zone("US/Central").datetime() == dt.astimezone(
        ZoneInfo("US/Central")
    )
    assert ht.astimezone("UTC") == dt.astimezone(ZoneInfo("US/Central")).astimezone(
        ZoneInfo("UTC")
    )
    dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("US/Central"))
    ht.set(dt)
    assert ht.datetime() == dt
    assert ht.astimezone("UTC") == dt.astimezone(ZoneInfo("UTC"))


# ------------------------------------------ #
# test addition, subtraction, and comparison #
# ------------------------------------------ #
def test_add_subtract_compare() -> None:
    # -------- #
    # addition #
    # -------- #
    ht = HecTime("15Aug2024", "10:53", hectime.MINUTE_GRANULARITY)
    assert (ht + 1).values == [2024, 8, 15, 10, 54, 0]
    assert (ht + timedelta(seconds=59)).values == [2024, 8, 15, 10, 53, 0]
    assert (ht + timedelta(seconds=61)).values == [2024, 8, 15, 10, 54, 0]
    assert (ht + timedelta(hours=1)).values == [2024, 8, 15, 11, 53, 0]
    assert (ht + timedelta(days=1)).values == [2024, 8, 16, 10, 53, 0]
    assert (ht + TimeSpan(seconds=59)).values == [2024, 8, 15, 10, 53, 0]
    assert (ht + TimeSpan(seconds=61)).values == [2024, 8, 15, 10, 54, 0]
    assert (ht + TimeSpan(hours=1)).values == [2024, 8, 15, 11, 53, 0]
    assert (ht + TimeSpan(days=1)).values == [2024, 8, 16, 10, 53, 0]
    assert (ht + TimeSpan([10, 10, 10, 10, 10, 10])).values == [2035, 6, 25, 21, 3, 0]
    assert (ht + HecTime(1, hectime.SECOND_GRANULARITY)).values == [
        2024,
        8,
        15,
        10,
        53,
        0,
    ]
    assert (ht + HecTime(1, hectime.MINUTE_GRANULARITY)).values == [
        2024,
        8,
        15,
        10,
        54,
        0,
    ]
    assert (ht + HecTime(1, hectime.HOUR_GRANULARITY)).values == [
        2024,
        8,
        15,
        11,
        53,
        0,
    ]
    assert (ht + HecTime(1, hectime.DAY_GRANULARITY)).values == [
        2024,
        8,
        16,
        10,
        53,
        0,
    ]
    exc = False
    try:
        ht + datetime(1, 1, 1, 1, 1, 1)
    except Exception as e:
        exc = True
    assert exc
    # ----------- #
    # subtraction #
    # ----------- #
    assert cast(HecTime, (ht - 1)).values == [2024, 8, 15, 10, 52, 0]
    assert cast(HecTime, (ht - timedelta(seconds=59))).values == [
        2024,
        8,
        15,
        10,
        53,
        0,
    ]
    assert cast(HecTime, (ht - timedelta(seconds=61))).values == [
        2024,
        8,
        15,
        10,
        52,
        0,
    ]
    assert cast(HecTime, (ht - timedelta(hours=1))).values == [2024, 8, 15, 9, 53, 0]
    assert cast(HecTime, (ht - timedelta(days=1))).values == [2024, 8, 14, 10, 53, 0]
    assert ht - datetime(2024, 8, 15, 10, 53, 0) == timedelta(seconds=0)
    assert ht - datetime(2024, 8, 15, 10, 52, 0) == timedelta(minutes=1)
    assert ht - datetime(2024, 8, 15, 9, 53, 0) == timedelta(hours=1)
    assert ht - datetime(2024, 8, 14, 10, 53, 0) == timedelta(days=1)
    assert ht - datetime(2024, 7, 15, 10, 53, 0) == timedelta(days=31)
    assert ht - datetime(2023, 8, 15, 10, 53, 0) == timedelta(days=366)
    assert ht - HecTime([2024, 8, 15, 10, 53, 0]) == TimeSpan()
    assert ht - HecTime([2024, 8, 15, 10, 52, 0]) == TimeSpan([0, 0, 0, 0, 1, 0])
    assert ht - HecTime([2024, 8, 15, 9, 53, 0]) == TimeSpan([0, 0, 0, 1, 0, 0])
    assert ht - HecTime([2024, 8, 14, 10, 53, 0]) == TimeSpan([0, 0, 1, 0, 0, 0])
    assert ht - HecTime([2024, 7, 15, 10, 53, 0]) == TimeSpan([0, 1, 0, 0, 0, 0])
    assert ht - HecTime([2023, 8, 15, 10, 53, 0]) == TimeSpan([1, 0, 0, 0, 0, 0])
    # ----------------------- #
    # right-hand substraction #
    # ----------------------- #
    assert datetime(2024, 8, 15, 10, 53, 0) - ht == timedelta(seconds=0)
    assert datetime(2024, 8, 15, 10, 54, 0) - ht == timedelta(minutes=1)
    assert datetime(2024, 8, 15, 11, 53, 0) - ht == timedelta(hours=1)
    assert datetime(2024, 8, 16, 10, 53, 0) - ht == timedelta(days=1)
    assert datetime(2024, 9, 15, 10, 53, 0) - ht == timedelta(days=31)
    assert datetime(2025, 8, 15, 10, 53, 0) - ht == timedelta(days=365)
    # ------------------#
    # in-place addition #
    # ------------------#
    ht += 1
    assert ht.values == [2024, 8, 15, 10, 54, 0]
    ht += timedelta(seconds=59)
    assert ht.values == [2024, 8, 15, 10, 54, 0]
    ht += timedelta(seconds=61)
    assert ht.values == [2024, 8, 15, 10, 55, 0]
    ht += timedelta(hours=1)
    assert ht.values == [2024, 8, 15, 11, 55, 0]
    ht += timedelta(days=1)
    assert ht.values == [2024, 8, 16, 11, 55, 0]
    ht += HecTime(1, hectime.SECOND_GRANULARITY)
    assert ht.values == [2024, 8, 16, 11, 55, 0]
    ht += HecTime(1, hectime.MINUTE_GRANULARITY)
    assert ht.values == [2024, 8, 16, 11, 56, 0]
    ht += HecTime(1, hectime.HOUR_GRANULARITY)
    assert ht.values == [2024, 8, 16, 12, 56, 0]
    ht += HecTime(1, hectime.DAY_GRANULARITY)
    assert ht.values == [2024, 8, 17, 12, 56, 0]
    ht.add_minutes(1)
    assert ht.values == [2024, 8, 17, 12, 57, 0]
    ht.add_hours(1)
    assert ht.values == [2024, 8, 17, 13, 57, 0]
    ht.add_days(1)
    assert ht.values == [2024, 8, 18, 13, 57, 0]
    ht += TimeSpan(days=1)
    assert ht.values == [2024, 8, 19, 13, 57, 0]
    ht += TimeSpan([10, 10, 10, 10, 10, 0])
    assert ht.values == [2035, 6, 30, 0, 7, 0]
    # ---------------------#
    # in-place subtraction #
    # ---------------------#
    ht -= TimeSpan([10, 10, 10, 10, 10, 0])
    assert ht.values == [2024, 8, 19, 13, 57, 0]
    ht -= TimeSpan(days=1)
    assert ht.values == [2024, 8, 18, 13, 57, 0]
    ht.subtract_days(1)
    assert ht.values == [2024, 8, 17, 13, 57, 0]
    ht.subtract_hours(1)
    assert ht.values == [2024, 8, 17, 12, 57, 0]
    ht.subtract_minutes(1)
    assert ht.values == [2024, 8, 17, 12, 56, 0]
    ht -= 1
    assert ht.values == [2024, 8, 17, 12, 55, 0]
    ht -= timedelta(seconds=59)
    assert ht.values == [2024, 8, 17, 12, 55, 0]
    ht -= timedelta(seconds=61)
    assert ht.values == [2024, 8, 17, 12, 54, 0]
    ht -= timedelta(hours=1)
    assert ht.values == [2024, 8, 17, 11, 54, 0]
    ht -= timedelta(days=1)
    assert ht.values == [2024, 8, 16, 11, 54, 0]
    ht -= HecTime(1, hectime.SECOND_GRANULARITY)
    assert ht.values == [2024, 8, 16, 11, 54, 0]
    ht -= HecTime(1, hectime.MINUTE_GRANULARITY)
    assert ht.values == [2024, 8, 16, 11, 53, 0]
    ht -= HecTime(1, hectime.HOUR_GRANULARITY)
    assert ht.values == [2024, 8, 16, 10, 53, 0]
    ht -= HecTime(1, hectime.DAY_GRANULARITY)
    assert ht.values == [2024, 8, 15, 10, 53, 0]
    # ------------------------- #
    # operations with time zone #
    # ------------------------- #
    times = {
        "Spring": {
            "start": "2025-03-09T01:00:00-08:00",
            "next": "2025-03-10T02:00:00-07:00",
            "next_local": "2025-03-10T01:00:00-07:00",
        },
        "Fall": {
            "start": "2025-11-02T01:30:00-07:00",
            "next": "2025-11-03T00:30:00-08:00",
            "next_local": "2025-11-03T01:30:00-08:00",
        },
    }
    table = str.maketrans("-T:", "   ")
    for season in ("Spring", "Fall"):
        # addition across DST boundary
        ht = HecTime(times[season]["start"][:19]).label_as_time_zone("US/Pacific")
        assert str(ht) == times[season]["start"]
        assert ht.values == list(map(int, str(ht)[:19].translate(table).split()))
        ht2 = ht + 1440
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - 1440
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht + TimeSpan(days=1)
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - TimeSpan(days=1)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht + timedelta(days=1)
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - timedelta(days=1)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht + "1D"
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - "1D"
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht + Interval.get_cwms("1Day")
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - Interval.get_cwms("1Day")
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht + Interval.get_any_cwms(
            lambda i: i.minutes == 1440 and i.is_local_regular
        )
        assert str(ht2) == times[season]["next_local"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2 - Interval.get_any_cwms(
            lambda i: i.minutes == 1440 and i.is_local_regular
        )
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        # in-place addition across DST boundary
        ht2 = ht.copy()
        ht2 += 1440
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= 1440
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2 += TimeSpan(days=1)
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= TimeSpan(days=1)
        assert str(ht3) == times[season]["start"]
        assert isinstance(ht3, HecTime)
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2 += timedelta(days=1)
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= timedelta(days=1)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2 += "1D"
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= "1D"
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2 += Interval.get_cwms("1Day")
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= Interval.get_cwms("1Day")
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2 += Interval.get_any_cwms(lambda i: i.minutes == 1440 and i.is_local_regular)
        assert str(ht2) == times[season]["next_local"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3 -= Interval.get_any_cwms(lambda i: i.minutes == 1440 and i.is_local_regular)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        # increment addition across DST boundary
        ht2 = ht.copy()
        ht2.increment(1, 1440)
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3.increment(-1, 1440)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2.increment(1, TimeSpan(days=1))
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3.increment(-1, TimeSpan(days=1))
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2.increment(1, timedelta(days=1))
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3.increment(-1, timedelta(days=1))
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        ht2.increment(1, Interval.get_cwms("1Day"))
        assert str(ht2) == times[season]["next"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3.increment(-1, Interval.get_cwms("1Day"))
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))

        ht2 = ht.copy()
        intvl = Interval.get_any_cwms(
            lambda i: i.minutes == 1440 and i.is_local_regular
        )
        assert isinstance(intvl, Interval)
        ht2.increment(1, intvl)
        print(f"{season}\t{ht2}\t{intvl}")
        assert str(ht2) == times[season]["next_local"]
        assert ht2.values == list(map(int, str(ht2)[:19].translate(table).split()))
        ht3 = ht2.copy()
        ht3.increment(-1, intvl)
        assert isinstance(ht3, HecTime)
        assert str(ht3) == times[season]["start"]
        assert ht3.values == list(map(int, str(ht3)[:19].translate(table).split()))


# -------------------------- #
# test string representation #
# -------------------------- #
def test_string_representation() -> None:
    assert str(HecTime()) == ""
    assert (
        str(HecTime("15Aug2024", "10:53:29", hectime.SECOND_GRANULARITY))
        == "2024-08-15T10:53:29"
    )
    assert (
        str(HecTime("15Aug2024", "10:53:29", hectime.MINUTE_GRANULARITY))
        == "2024-08-15T10:53:00"
    )
    assert (
        str(HecTime("15Aug2024", "10:53:29", hectime.HOUR_GRANULARITY))
        == "2024-08-15T10:00:00"
    )
    assert (
        str(HecTime("15Aug2024", "10:53:29", hectime.DAY_GRANULARITY))
        == "2024-08-14T24:00:00"
    )
    assert (
        str(HecTime("15Aug2024", "00:00:00", hectime.DAY_GRANULARITY))
        == "2024-08-14T24:00:00"
    )
    ht = HecTime(hectime.DAY_GRANULARITY)
    ht.midnight_as_2400 = False
    ht.set("15Aug2024", "00:00:00")
    assert str(ht) == "2024-08-15T00:00:00"
    ht.set("15Aug2024", "10:53:29")
    assert str(ht) == "2024-08-15T00:00:00"
    ht.set("15Aug2024", "24:00:00")
    assert str(ht) == "2024-08-16T00:00:00"


if __name__ == "__main__":
    test_to_from_datetime()
