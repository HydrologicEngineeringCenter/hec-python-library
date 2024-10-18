"""Module for testing hec.hectime module
"""

import os
import time
from datetime import datetime, timedelta
from test.shared import dataset_from_file, random_subset, scriptdir, slow_test_coverage
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest
import tzlocal

from hec import hectime
from hec.hectime import HecTime
from hec.interval import Interval
from hec.timespan import TimeSpan

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


# ----------------------- #
# test hectime.addCentury #
# ----------------------- #
@pytest.mark.parametrize(
    "_y, _expected", dataset_from_file("resources/hectime/add_century.txt")
)
def test_addCentury(_y: str, _expected: str) -> None:
    y, expected = tuple(map(int, (_y, _expected)))
    if y >= 100:
        # legitimate non-2-digit years, behavior differs from Java HecTime.addCentury
        assert hectime.addCentury(y) == y
    else:
        # same behavior as Java HecTime.addCentury
        assert hectime.addCentury(y) == expected


# ---------------------- #
# test hectime.cleanTime #
# ---------------------- #
@pytest.mark.parametrize(
    "_time, _expected", dataset_from_file("resources/hectime/clean_times.txt")
)
def test_cleanTime(_time: str, _expected: str) -> None:
    time: list[int] = eval(_time)
    expected: list[int] = eval(_expected)
    hectime.cleanTime(time)
    assert time == expected


# ------------------------------------------------ #
# test hectime.computeNumberIntervals              #
#                                                  #
# runs 43500 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
INTERVALS = [
    Interval.getAny(lambda i: i.minutes == m)
    for m in sorted(set([m for m in Interval.MINUTES.values() if m > 0]))
]
if slow_test_coverage < 100:
    INTERVALS = random_subset(INTERVALS)


@pytest.mark.slow
@pytest.mark.parametrize(
    "time1, time2", dataset_from_file("resources/hectime/interval_count.txt", slow=True)
)
def test_computeNumberIntervals(time1: str, time2: str) -> None:
    t1 = HecTime(time1)
    t2 = HecTime(time2)
    for interval in INTERVALS:
        assert interval is not None
        count = t1.computeNumberIntervals(t2, interval)
        t3 = HecTime(t1)
        t3.increment(count, interval)
        assert t3 <= t2
        t3.increment(1, interval)
        assert t3 >= t2


# ----------------------------------------------------- #
# test hectime.convertTimeZone, HecTime.convertTimeZone #
# ----------------------------------------------------- #
@pytest.mark.parametrize(
    "time1, fromTz, toTz, time2",
    dataset_from_file("resources/hectime/convert_timezone.txt"),
)
def test_convertTimeZone(time1: str, fromTz: str, toTz: str, time2: str) -> None:
    t = HecTime(time1)
    hectime.convertTimeZone(t, ZoneInfo(fromTz), ZoneInfo(toTz))
    assert t.dateAndTime(-13) == time2
    t = HecTime(time1)
    t.convertTimeZone(ZoneInfo(fromTz), ZoneInfo(toTz))
    assert t.dateAndTime(-13) == time2


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
    hectime.julianToYearMonthDay(julian[0], timevals)
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


# ---------------------------------------------- #
# test hectime.datcln, hectime.normalizeTimeVals #
# ---------------------------------------------- #
@pytest.mark.parametrize(
    "_time, _expected", dataset_from_file("resources/hectime/clean_times.txt")
)
def test_datcln(_time: str, _expected: str) -> None:
    time: list[int] = eval(_time)
    expected: list[int] = eval(_expected)
    if len(time) == 2:
        julianClean = [0]
        minuteClean = [0]
        hectime.datcln(time[0], time[1], julianClean, minuteClean)
        assert julianClean[0] == expected[0]
        assert minuteClean[0] == expected[1]
    elif len(time) == 6:
        hectime.normalizeTimeVals(time)
        assert time == expected


# --------------------------------------------------------------------------- #
# test hectime.datjul, hectime.datymd, hectime.iymdjl, hectime.jliymd,        #
# hectime.juldat, hectime.ymddat                                              #
# exercises hectime.parseDateTimeString, hectime.julianToYearMonthDay,        #
# hectime.yearMonthDayToJulian                                                #
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


# --------------------------------------------- #
# test hectime.getime and hectime.getTimeWindow #
# --------------------------------------------- #
@pytest.mark.parametrize(
    "twStr, startTime, endTime, _juls, _mins, _jule, _mine",
    dataset_from_file("resources/hectime/time_window.txt"),
)
def test_getTimeWindow_getime(
    twStr: str,
    startTime: str,
    endTime: str,
    _juls: str,
    _mins: str,
    _jule: str,
    _mine: str,
) -> None:
    tStart: HecTime = HecTime()
    tEnd: HecTime = HecTime()
    juls, mins, jule, mine = list(map(int, (_juls, _mins, _jule, _mine)))
    julStart = [0]
    minStart = [0]
    julEnd = [0]
    minEnd = [0]
    status = [0]
    hectime.getTimeWindow(twStr, tStart, tEnd)
    assert tStart.dateAndTime(-13) == startTime
    assert tEnd.dateAndTime(-13) == endTime
    hectime.getime(twStr, julStart, minStart, julEnd, minEnd, status)
    assert status[0] == 0
    assert julStart[0] == juls
    assert minStart[0] == mins
    assert julEnd[0] == jule
    assert minEnd[0] == mine


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


# ------------------------------------------------------------- #
# test hectime.idaywk, HecTime.dayOfWeek, HecTime.dayOfWeekName #
# ------------------------------------------------------------- #
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
    assert t.dayOfWeek() == weekday
    assert t.dayOfWeekName() == dayname


# ------------------------------------------------ #
# test HecTime.increment, hectime.inctim           #
# exercises hectime.incrementTimeVals              #
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
    assert t2.dateAndTime(-13) == end_time
    intvl = Interval.getAny(lambda i: i.minutes == interval)
    assert intvl is not None
    t2 = HecTime(t)
    t2.increment(count, intvl)
    assert t2.dateAndTime(-13) == end_time
    ts = TimeSpan(str(intvl)) + timedelta(minutes=10)
    t3 = HecTime(t)
    t3.increment(count, ts)
    t4 = HecTime(end_time)
    t4 += count * timedelta(minutes=10)
    assert t3 == t4
    startJul = t.julian()
    startMin = t.minutesSinceMidnight()
    endJul = [0]
    endMin = [0]
    hectime.inctim(interval, count, startJul, startMin, endJul, endMin)
    assert endJul[0] == t2.julian()
    assert endMin[0] == t2.minutesSinceMidnight()
    if intvl.minutes <= Interval.MINUTES["1Week"]:
        # --------------------------------- #
        # can't use calendar info in inctim #
        # --------------------------------- #
        intvl = Interval.getAny(lambda i: i.minutes == interval)
        assert intvl is not None
        endJul = [0]
        endMin = [0]
        hectime.inctim(intvl, count, startJul, startMin, endJul, endMin)
        assert endJul[0] == t2.julian()
        assert endMin[0] == t2.minutesSinceMidnight()
        ts = TimeSpan(str(intvl)) + timedelta(minutes=10)
        endJul = [0]
        endMin = [0]
        hectime.inctim(ts, count, startJul, startMin, endJul, endMin)
        assert endJul[0] == t4.julian()
        assert endMin[0] == t4.minutesSinceMidnight()


# --------------------------------------------------- #
# test HecTime.adjustToIntervalOffset, hectime.zofset #
# --------------------------------------------------- #
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
    min0[0] = min1[0] = cast(int, t.minutesSinceMidnight())
    computed_offset = t.getIntervalOffset(interval)
    t.adjustToIntervalOffset(interval, offset)
    assert t.dateAndTime(-13) == time2
    jul2[0] = cast(int, t.julian())
    min2[0] = cast(int, t.minutesSinceMidnight())
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


# ------------------------------ #
# test HecTime.getIntervalOffset #
# ------------------------------ #
@pytest.mark.parametrize(
    "timestr, _interval, _expected_offset",
    dataset_from_file("resources/hectime/interval_offset.txt"),
)
def test_getIntervalOffset(timestr: str, _interval: str, _expected_offset: int) -> None:
    interval = int(_interval)
    expected_offset = int(_expected_offset)
    t = HecTime(timestr)
    assert t.getIntervalOffset(interval) == expected_offset


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
        timeInt = int(parts[0])
        timeVals = eval(parts[1])
        int_test_data.append((ht, timeInt, timeVals))
        list_test_data.append((ht, timeVals, timeInt))
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
@pytest.mark.parametrize("ht, timeint, expectedTimeVals", int_test_data)
def test_initialize_HecTime_from_integer(
    ht: HecTime, timeint: int, expectedTimeVals: list[int]
) -> None:
    assert ht.set(timeint) == 0
    assert ht.values == expectedTimeVals


# ------------------------------------------------ #
# test initializing from time values list          #
# runs 40004 tests, skip with pytest -m "not slow" #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
@pytest.mark.slow
@pytest.mark.parametrize("ht, timevals, expectedTimeInt", list_test_data)
def test_initialize_HecTime_from_list(
    ht: HecTime, timevals: list[int], expectedTimeInt: int
) -> None:
    assert ht.set(timevals) == 0
    assert ht.value == expectedTimeInt


# ------------------------------- #
# test initializing from a string #
# ------------------------------- #
@pytest.mark.parametrize(
    "_string, _timeVals2400, _timeVals0000",
    dataset_from_file("resources/hectime/string_date_times.txt"),
)
def test_initialize_HecTime_from_string(
    _string: str, _timeVals2400: str, _timeVals0000: str
) -> None:
    string = _string.strip("'\"")
    timeVals0000 = [int(item) for item in eval(_timeVals0000)]
    t = HecTime(hectime.SECOND_GRANULARITY)
    t.midnight_as_2400 = False
    assert t.set(string) == 0
    assert t.values == timeVals0000


# ---------------------- #
# test midnight settings #
# ---------------------- #
@pytest.mark.parametrize(
    "_string, _timeVals2400, _timeVals0000",
    dataset_from_file("resources/hectime/string_date_times.txt"),
)
def test_midnight_settings(
    _string: str, _timeVals2400: str, _timeVals0000: str
) -> None:
    timeVals0000 = [int(item) for item in eval(_timeVals0000)]
    timeVals2400 = [int(item) for item in eval(_timeVals2400)]
    t = HecTime(hectime.SECOND_GRANULARITY)
    t.midnight_as_2400 = True
    assert t.set(timeVals0000) == 0
    assert t.values == timeVals2400
    t.midnight_as_2400 = False
    assert t.values == timeVals0000


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
    assert ht.dateAndTime(int(style)) == expected


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
    assert ht.atTimeZone("UTC").datetime() == dt.replace(tzinfo=ZoneInfo("UTC"))
    assert ht.atTimeZone("US/Central").datetime() == dt.replace(
        tzinfo=ZoneInfo("US/Central")
    )
    assert ht.astimezone("UTC") == dt.replace(tzinfo=ZoneInfo("US/Central")).astimezone(
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
    ht.addMinutes(1)
    assert ht.values == [2024, 8, 17, 12, 57, 0]
    ht.addHours(1)
    assert ht.values == [2024, 8, 17, 13, 57, 0]
    ht.addDays(1)
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
    ht.subtractDays(1)
    assert ht.values == [2024, 8, 17, 13, 57, 0]
    ht.subtractHours(1)
    assert ht.values == [2024, 8, 17, 12, 57, 0]
    ht.subtractMinutes(1)
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


# -----------------#
# test comparisons #
# -----------------#
ht0 = HecTime()
assert ht0 == HecTime()
assert ht0 == HecTime(hectime.SECOND_GRANULARITY)
ht1 = HecTime("15Aug2024", "10:53", hectime.SECOND_GRANULARITY)
assert ht0 != ht1
assert ht0 < ht1
assert ht0 <= ht1
ht2 = HecTime("15Aug2024", "10:53", hectime.MINUTE_GRANULARITY)
assert ht1 == ht2
assert ht1 <= ht2
assert ht1 >= ht2
ht2 = HecTime("15Aug2024", "10:54", hectime.MINUTE_GRANULARITY)
assert ht1 != ht2
assert ht1 < ht2
assert ht1 <= ht2
assert ht2 > ht1
assert ht2 >= ht1
dt1 = datetime(2024, 8, 15, 10, 53)
assert ht0 != dt1
assert ht0 < dt1
assert ht0 <= dt1
assert dt1 == ht1
assert dt1 <= ht1
assert dt1 >= ht1
assert dt1 <= ht2
ht1.atTimeZone("local")
assert ht1 != dt1
dt2 = dt1.replace(tzinfo=tzlocal.get_localzone())
assert ht1 == dt2
assert ht1 == dt2.astimezone(ZoneInfo("UTC"))
assert ht1.astimezone("UTC") == dt2
assert ht1.astimezone("UTC") == ht1
