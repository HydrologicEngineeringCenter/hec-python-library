"""
Module to provide native python compatibility for the `hec.heclib.util.HecTime` java class

**NOTE** Static java fields and methods are now module constants and functions (e.g., java `HecTime.isLeap()` -> python `hectime.isLeap()`)

Jump to [**`class HecTime`**](#HecTime)
"""

from datetime import datetime, timedelta
from functools import total_ordering, wraps
from typing import cast
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union
from zoneinfo import ZoneInfo
from hec.timespan import TimeSpan
from hec.interval import Interval
from fractions import Fraction
import math, re, tzlocal, warnings, zoneinfo

__all__ = [
    "UNDEFINED_TIME",
    "SECOND_GRANULARITY",
    "MINUTE_GRANULARITY",
    "HOUR_GRANULARITY",
    "DAY_GRANULARITY",
    "addCentury",
    "cleanTime",
    "computeNumberIntervals",
    "convertTimeZone",
    "curtim",
    "datcln",
    "datjul",
    "datymd",
    "getime",
    "getTimeInt",
    "getTimeVals",
    "getTimeWindow",
    "hm2m",
    "idaywk",
    "ihm2m",
    "ihm2m_2",
    "incrementTimeVals",
    "inctim",
    "isLeap",
    "isValidGranularity",
    "isValidTime",
    "iymdjl",
    "jliymd",
    "juldat",
    "julianToYearMonthDay",
    "maxDay",
    "m2hm",
    "m2ihm",
    "minutesSinceMidnight",
    "nextMonth",
    "nopers",
    "normalizeDateStyle",
    "normalizeTimeVals",
    "parseDateTimeStr",
    "previousMonth",
    "secondsSinceMidnight",
    "systim",
    "to0000",
    "to2400",
    "yearMonthDayToJulian",
    "ymddat",
    "zofset",
    "HecTimeException",
    "HecTime",
]

# ------------------------------------ #
# Miscellaneous definitions for module #
# ------------------------------------ #
DATE_INTEGER: int = 0
DATE_VALUES: int = 1
MIN_EXTENT: int = 0
MAX_EXTENT: int = 1
# time value index constants
Y: int = 0
M: int = 1
D: int = 2
H: int = 3
N: int = 4
S: int = 5
# other scalar definitions
UNDEFINED_TIME: int = -4294967296
"""The value for a time integer that repsents that the time has either not been set yet
or has been set incorrectly."""
DAYS_IN_400_YEARS = 146097
# ------------------------- #
# Month-related definitions #
# ------------------------- #
MONTHS_BY_ABBREV: dict[str, int] = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
MONTH_NAMES: dict[int, str] = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}
# ------------------------------- #
# Granularity-related definitions #
# ------------------------------- #
# INCREMENT values are for backward compatibility only - they are converted to GRANULARITY values on use
SECOND_INCREMENT: int = 0
MINUTE_INCREMENT: int = 1
HOUR_INCREMENT: int = 2
DAY_INCREMENT: int = 3
SECOND_GRANULARITY: int = 10
"""
Value that specifies that each granule represents one second
- Values are offset from `[1970, 1, 1, 0, 0, 0]`
- Earliest represntable time is `[1901, 12, 13, 20, 45, 52]` (integer value = `-2147483648`)
- Latest represntable time is `[2038, 1, 19, 3, 14, 7]` (integer value = `2147483647`)
"""
MINUTE_GRANULARITY: int = 11
"""
Value that specifies that each granule represents one minute. New HecTime objects default to
this granularity if not otherwise specified.
- Values are offset from `[1899, 12, 31, 0, 0, 0]`
- Earliest represntable time is `[-2184, 12, 6, 21, 52, 0]` (integer value = `-2147483648`)
- Latest represntable time is `[5983, 1, 23, 2, 7, 0]` (integer value = `2147483647`)
"""
HOUR_GRANULARITY: int = 12
"""
Value that specifies that each granule represents one hour
- Values are offset from `[1899, 12, 31, 0, 0, 0]`
- Earliest represntable time is `[-243084, 3, 22, 16, 0, 0]` (integer value = `-2147483648`)
- Latest represntable time is `[246883, 10, 8, 7, 0, 0]` (integer value = `2147483647`)
"""
DAY_GRANULARITY: int = 13
"""
Value that specifies that each granule represents one day
- Values are offset from `[1899, 12, 31, 0, 0, 0]`
- Earliest represntable time is `[-5877711, 6, 22, 0, 0, 0]` (integer value = `-2147483645`)
- Latest represntable time is `[5879610, 7, 10, 0, 0, 0]` (integer value = `2147483647`)
"""

GRANULARITIES: tuple[int, ...] = (
    SECOND_GRANULARITY,
    MINUTE_GRANULARITY,
    HOUR_GRANULARITY,
    DAY_GRANULARITY,
)
SECONDS_IN_GRANULE: dict[int, int] = {
    SECOND_GRANULARITY: 1,
    MINUTE_GRANULARITY: 60,
    HOUR_GRANULARITY: 3600,
    DAY_GRANULARITY: 86400,
}
GRANULES_IN_DAY: dict[int, int] = {
    SECOND_GRANULARITY: 86400,
    MINUTE_GRANULARITY: 1440,
    HOUR_GRANULARITY: 24,
    DAY_GRANULARITY: 1,
}
GRANULES_IN_HOUR: dict[int, int] = {g: GRANULES_IN_DAY[g] // 24 for g in GRANULARITIES}
GRANULES_IN_MINUTE: dict[int, int] = {
    g: GRANULES_IN_DAY[g] // 1440 for g in GRANULARITIES
}
GRANULES_IN_SECOND: dict[int, int] = {
    g: GRANULES_IN_DAY[g] // 86400 for g in GRANULARITIES
}
# GRANULES_IN_MONTH[granularity][days_in_month]
GRANULES_IN_MONTH: dict[int, dict[int, int]] = {
    g: {d: GRANULES_IN_DAY[g] * d for d in (28, 29, 30, 31)} for g in GRANULARITIES
}
# GRANULES_IN_YEAR[granularity][is_leap_year]
GRANULES_IN_YEAR: dict[int, tuple[int, ...]] = {
    g: tuple(d * GRANULES_IN_DAY[g] for d in (365, 366)) for g in GRANULARITIES
}
GRANULES_IN_CYCLE: dict[int, int] = {
    SECOND_GRANULARITY: DAYS_IN_400_YEARS * 86400,
    MINUTE_GRANULARITY: DAYS_IN_400_YEARS * 1440,
    HOUR_GRANULARITY: DAYS_IN_400_YEARS * 24,
    DAY_GRANULARITY: DAYS_IN_400_YEARS,
}
# EXTENTS[granularity][(DATE_INTEGER|DATE_VALUES)][(MIN_EXTENT|MAX_EXT)]
EXTENTS: dict[
    int,
    tuple[
        tuple[int, int],
        tuple[tuple[int, int, int, int, int, int], tuple[int, int, int, int, int, int]],
    ],
] = {
    SECOND_GRANULARITY: (
        (-2147483648, 2147483647),
        ((1901, 12, 13, 20, 45, 52), (2038, 1, 19, 3, 14, 7)),
    ),
    MINUTE_GRANULARITY: (
        (-2147483648, 2147483647),
        ((-2184, 12, 6, 21, 52, 0), (5983, 1, 23, 2, 7, 0)),
    ),
    HOUR_GRANULARITY: (
        (-2147483648, 2147483647),
        ((-243084, 3, 22, 16, 0, 0), (246883, 10, 8, 7, 0, 0)),
    ),
    DAY_GRANULARITY: (
        (-2147483645, 2146789687),
        ((-5877711, 6, 22, 0, 0, 0), (5879610, 7, 10, 0, 0, 0)),
    ),
}
# Time values for various granularities that have a time integer of zero
ZERO_TIMES: dict[int, list[int]] = {
    SECOND_GRANULARITY: [1970, 1, 1, 0, 0, 0],
    MINUTE_GRANULARITY: [1899, 12, 31, 0, 0, 0],
    HOUR_GRANULARITY: [1899, 12, 31, 0, 0, 0],
    DAY_GRANULARITY: [1899, 12, 31, 0, 0, 0],
}
# ---------------------------- #
# Interval-related definitions #
# ---------------------------- #

INTERVALS = [
    Interval.MINUTES["1Minute"],
    Interval.MINUTES["2Minutes"],
    Interval.MINUTES["3Minutes"],
    Interval.MINUTES["4Minutes"],
    Interval.MINUTES["5Minutes"],
    Interval.MINUTES["6Minutes"],
    Interval.MINUTES["10Minutes"],
    Interval.MINUTES["12Minutes"],
    Interval.MINUTES["15Minutes"],
    Interval.MINUTES["20Minutes"],
    Interval.MINUTES["30Minutes"],
    Interval.MINUTES["1Hour"],
    Interval.MINUTES["2Hours"],
    Interval.MINUTES["3Hours"],
    Interval.MINUTES["4Hours"],
    Interval.MINUTES["6Hours"],
    Interval.MINUTES["8Hours"],
    Interval.MINUTES["12Hours"],
    Interval.MINUTES["1Day"],
    Interval.MINUTES["2Days"],
    Interval.MINUTES["3Days"],
    Interval.MINUTES["4Days"],
    Interval.MINUTES["5Days"],
    Interval.MINUTES["6Days"],
    Interval.MINUTES["1Week"],
    Interval.MINUTES["Tri-Month"],
    Interval.MINUTES["Semi-Month"],
    Interval.MINUTES["1Month"],
    Interval.MINUTES["1Year"],
]


# ----------------- #
# warning functions #
# ----------------- #
warnings.filterwarnings("always", category=UserWarning)


def NotImplementedWarning(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        warnings.warn(
            f"This implemenation does not support {func.__name__}(). Please remove it from your code.",
            Warning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


def NoOpWarning(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> Any:
        warnings.warn(
            f"{func.__name__}() does nothing in this implementation. Please remove it from your code.",
            Warning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


def addCentury(y: int) -> int:
    """
    Converts 2-digit years into 4 digit years.

    If the year passed in is not in the range 0..99, the year is returned unchanged

    Args:
        y (int): The year

    Returns:
        int: The year as a 4 digit year
    """
    curyear = datetime.now().year
    maxfuture = 10
    if 0 <= y < 100:
        y += 2000
        if y > curyear + maxfuture:
            y -= 100
    return y


def cleanTime(values: list[int]) -> None:
    """
    Normalizes in integer list of either `[julian, minute]` or `[year, month, day, hour, minute, second]`

    Args:
        values (list[int]): Either `[julian, minute]` or `[year, month, day, hour, minute, second]
    """
    if len(values) == 2:
        if values[1] < 0:
            dayincr, minute = divmod(abs(values[1] - 1440), 1440)
            dayincr = -dayincr
            minute = 1440 - minute
        else:
            dayincr, minute = divmod(values[1], 1440)
        values[0] += dayincr
        values[1] = minute
    elif len(values) == 6:
        normalizeTimeVals(values)


def computeNumberIntervals(
    startTime: int, endTime: int, interval: Union[Interval, int]
) -> int:
    """
    Returns the complete number of intervals between two times

    Args:
        startTime (int): The time to compute the number of intervals from, in julian * 1440 + minutesSinceMidnight
        endTime (int): The time to compute the number of intervals to, in julian * 1440 + minutesSinceMidnight
        interval (Union[Interval, int]): The interval to compute the number for. If an integer, it must the the
        actual or characteristic minutes value of a standard Interval object.

    Raises:
        HecTimeException: if the interval is not one of the standard intervals

    Returns:
        int: The number of complete intervals between the two times
    """
    return nopers(
        interval,
        int(startTime / 1440),
        startTime % 1440,
        int(endTime / 1440),
        endTime % 1440,
    )


def convertTimeZone(
    hecTime: "HecTime",
    fromTimeZone: "ZoneInfo",
    toTimeZone: "ZoneInfo",
    respeectDalightSaving: Optional[bool] = True,
) -> None:
    """
    Converts an HecTime object from one time zone to another, optionally specifyintg that the
    target time zone does not observe Daylight Saving Time (DST). Only for HecTime objects
    convertable to datetime objects (between 01Jan0001, 00:00 and 31Dec9999, 23:59).

    Args:
        hecTime (HecTime): The HecTime object to convert
        fromTimeZone (ZoneInfo): The time zone that the object is currently in
        toTimeZone (ZoneInfo): The target time
        respectDaylighSaving (Optional[bool], optional): Specifies whether the target time zone.
            should observe DST. Defaults to True.
            - If `True`, the target time zone is used as specified
            - If `False` and the specified target time zone observes DST, then a time zone is
            found that has the same UTC offset as the specified target time zone but does not
            observe DST.

    Raises:
        HecTimeException:
            - If the HecTime object has an attached time zone that is not the same as `fromTimeZone`.
            - If `respectDaylightSaving` is `True`, `toTimeZone` observes DST and no equivalent
            time zone could be found that does not observer DST
            - If the HecTime object is not convertable to a datetime object
    """
    hecTime.convertTimeZone(fromTimeZone, toTimeZone, respeectDalightSaving)


def curtim(julian: list[int], minutes: list[int]) -> None:
    """
    Get the current timm as days since 1899 and minutes past midnight and return in parameters.

    Args:
        julian (list[int]): A list of length > 0 whose first value receives the current days since 1899
        minutes (list[int]): A list of length > 0 whose first value receives the current minutes past midnight

    Deprecated:
        Use [**`systim()`**](#systim) instead
    """
    warnings.warn(
        "The curtim() function is deprecated. Please use the systim() function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    systim(julian, minutes, True, None)


def datcln(
    julianIn: int, minutesIn: int, julianOut: list[int], minutesOut: list[int]
) -> None:
    """
    Normalizes a time specified in days since 1899 and minutes past midnight so that 0 <= minutesOut < 1440

    Args:
        julianIn (int): _description_
        minutesIn (int): _description_
        julianOut (list[int]): _description_
        minutesOut (list[int]): _description_
    """
    values = 6 * [0]
    julianToYearMonthDay(julianIn, values)
    values[H], values[N] = divmod(minutesIn, 60)
    normalizeTimeVals(values)
    julianOut[0] = yearMonthDayToJulian(values[Y], values[M], values[D])
    minutesOut[0] = values[H] * 60 + values[N]


def datjul(dateStr: str, julian: list[int]) -> None:
    """
    Parses a date string and sets the the number of days since 1899 in the return variable

    Args:
        dateStr (str): The date string (may contain time portion)
        julian (list[int]): A list of length > 0 that whose first element receives the days since 1988

    Raises:
        HecTimeException: if the date string cannot be successfully parsed
    """
    values = parseDateTimeStr(dateStr)
    julian[0] = yearMonthDayToJulian(values[Y], values[M], values[D], False)


def datymd(dateStr: str, ymd: list[int]) -> int:
    """
    Parses a date string and sets the year, month, and day in the return variable

    Args:
        dateStr (str): The date string to parse (may contain a time portion)
        ymd (list[int]): A list of length > 2 whose first three elements receive the year, month, and day

    Returns:
        int: 0 on success or -1 otherwise
    """
    status = 0
    try:
        values = parseDateTimeStr(dateStr)
        ymd[Y] = values[Y]
        ymd[M] = values[M]
        ymd[D] = values[D]
    except HecTimeException:
        status = -1
    return status


def getime(
    timeWindowString: str,
    startJul: list[int],
    startMin: list[int],
    endJul: list[int],
    endMin: list[int],
    status: list[int],
) -> None:
    """
    Parses or computes the start and end of a time window specified as a string in the general form
    `start_time` `end_time` and return the computed times in the specified parameters.

    Args:
        timeWindowString (str): The time window string. Both start time and end time may be absolute times or relative times.
            The string is not case sensitive, but the start and end times must be separated by a comma or whitespace.
            - If absolute:
                - may contain commas and/or spaces
                - may specify a time portion or not:
            - If relative:
                - may not contain commas or spaces
                - are of the format &lt;*anchor*&gt;&lt;*offset*&gt;... where each offset is of the format [+-]&lt;*count*&gt;&lt;*unit*&gt;
                    Multiple offsets are allowed.
                    - Valid anchors are:
                        - `T` the current time
                        - `D` the start of the current day
                        - `B` or `S` - the start time (allowed only on end time and end must not depend on start time)
                        - `E` - the end time (allowed only on start time and the start time must not depend on end time)<br>
                    - The unit for each offset must be one of:
                        - `Y` - year(s)
                        - `M` - month(s)
                        - `D` - days(s)
                        - `H` - hour(s)
            - Examples:
                - `01Aug2024, 01:00 31Aug2024 2400`
                - `2024-01-01 2024-12-31,24:00`
                - `t-7d, t`
                - `e-1m+1d-2h,d`
                - `01Aug2024, 01:00, s+1m`
        startJul (list[int]): Element[0] receives the days since 1899 for the start time if status[0] == 0
        startMin (list[int]): Element[0] receives the minutes past midnight for the start time if status[0] == 0
        endJul (list[int]): Element[0] receives the days since 1899 for the end time if status[0] == 0
        endMin (list[int]): Element[0] receives the minutes past midnight for the end time if status[0] == 0
        status (list[int]): Element[0] recieves `0` if the time window string was successfully parsed, `-1` otherwise
    """
    startTime = HecTime()
    endTime = HecTime()
    status[0] = getTimeWindow(timeWindowString, startTime, endTime)
    if status[0] == 0:
        startJul[0] = cast(int, startTime.julian())
        startMin[0] = cast(int, startTime.minutesSinceMidnight())
        endJul[0] = cast(int, endTime.julian())
        endMin[0] = cast(int, endTime.minutesSinceMidnight())


def getTimeInt(values: list[int], granularity: int) -> int:
    """
    Return a time integer for specified time values and granularity

    Args:
        values (list[int]): The time values (`[year, month, day, hour, minute, second]`)
        granularity (int): The granularity of the time integer to return

    Raises:
        HecTimeException: if values is less than six items in length
        HecTimeException: if the specified granularity is not valid

    Returns:
        int: The time integer for the specified time values and granularity

    See:
        [`isValidGranularity(...)`](#isValidGranularity)
    """
    # ------------- #
    # sanity checks #
    # ------------- #
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")

    if (
        not cast(tuple[int, ...], EXTENTS[granularity][DATE_VALUES][MIN_EXTENT])
        <= tuple(values)
        <= cast(tuple[int, ...], EXTENTS[granularity][DATE_VALUES][MAX_EXTENT])
    ):
        raise HecTimeException(
            f"Time list {values} is invalid for granularity {granularity}"
            f"\n\tTime list must be in range {EXTENTS[granularity][DATE_VALUES][MIN_EXTENT]} .. {EXTENTS[granularity][DATE_VALUES][MAX_EXTENT]}"
        )
    # ----------- #
    # do the work #
    # ----------- #
    timeInt: int = 0
    currentTimeVals: list[int] = list(ZERO_TIMES[granularity])
    normalizeTimeVals(values)
    # -------------------------------#
    # move to the start of the month #
    # -------------------------------#
    days = currentTimeVals[D] - 1
    timeInt -= days * GRANULES_IN_DAY[granularity]
    currentTimeVals[D] -= days
    # ------#
    # years #
    # ------#
    sign = -1 if values[Y] < currentTimeVals[Y] else 1
    cycles = abs(values[Y] - currentTimeVals[Y]) // 400
    timeInt += cycles * GRANULES_IN_CYCLE[granularity] * sign
    currentTimeVals[Y] += cycles * 400 * sign
    years = abs(values[Y] - currentTimeVals[Y])
    for _ in range(years):
        if sign == 1:
            y = currentTimeVals[Y] if currentTimeVals[M] < 3 else currentTimeVals[Y] + 1
        else:
            y = currentTimeVals[Y] if currentTimeVals[M] > 2 else currentTimeVals[Y] - 1
        timeInt += GRANULES_IN_YEAR[granularity][isLeap(y)] * sign
        currentTimeVals[Y] += sign
    # -------#
    # months #
    # -------#
    sign = -1 if values[M] < currentTimeVals[M] else 1
    months = abs(values[M] - currentTimeVals[M])
    for _ in range(months):
        if sign == 1:
            y, m = (
                (currentTimeVals[Y], currentTimeVals[M])
                if currentTimeVals[D] < 3
                else nextMonth(currentTimeVals[Y], currentTimeVals[M])
            )
        else:
            y, m = (
                (currentTimeVals[Y], currentTimeVals[M])
                if currentTimeVals[D] > 2
                else previousMonth(currentTimeVals[Y], currentTimeVals[M])
            )
        timeInt += GRANULES_IN_MONTH[granularity][maxDay(y, m)] * sign
        currentTimeVals[M] += sign
        normalizeTimeVals(currentTimeVals)
    # -----#
    # days #
    # -----#
    days = values[D] - currentTimeVals[D]
    timeInt += days * GRANULES_IN_DAY[granularity]
    currentTimeVals[D] += days
    # ------#
    # hours #
    # ------#
    hours = values[H] - currentTimeVals[H]
    timeInt += hours * GRANULES_IN_HOUR[granularity]
    currentTimeVals[H] += hours
    # --------#
    # minutes #
    # --------#
    minutes = values[N] - currentTimeVals[N]
    timeInt += minutes * GRANULES_IN_MINUTE[granularity]
    currentTimeVals[N] += minutes
    # ---------#
    # seconds #
    # ---------#
    seconds = values[S] - currentTimeVals[S]
    timeInt += seconds
    currentTimeVals[S] += seconds

    normalizeTimeVals(currentTimeVals)
    # --------------------------------------------------------#
    # handle java implementation bug that discards 0004-12-31 #
    # --------------------------------------------------------#
    if values[:3] < [5, 1, 1]:
        timeInt += GRANULES_IN_DAY[granularity]
    return timeInt


def getTimeVals(timeInt: int, granularity: int) -> list[int]:
    """
    Return time values for a time value and granularity

    **NOTE** This function always returns midnight as `[..., 0, 0, 0]`.
    Use [`to2400(...)`](#to2400) to get midnight as hour 24

    Args:
        timeInt (int): The time integer to return the time values for
        granularity (int): The granularity of the time integer

    Raises:
        HecTimeException: if timeInt is not valid for the specified granularity

    Returns:
        list[int]: The list of time values (`[year, month, day, hour, minute, second]`) represented by the time integer in and granularity
    """
    # ------------- #
    # sanity checks #
    # ------------- #
    if (
        not cast(int, EXTENTS[granularity][DATE_INTEGER][MIN_EXTENT])
        <= timeInt
        <= cast(int, EXTENTS[granularity][DATE_INTEGER][MAX_EXTENT])
    ):
        raise HecTimeException(
            f"Time value {timeInt} is invalid for granularity {granularity}"
        )
    # -------------------------------------- #
    # use incrementTimeVals() to do the work #
    # -------------------------------------- #
    return incrementTimeVals(list(ZERO_TIMES[granularity]), timeInt, granularity)


def getTimeWindow(
    timeWindowString: str, startTime: "HecTime", endTime: "HecTime"
) -> int:
    """
    Parses or computes the start and end of a time window specified as a string in the general form
    `start_time` `end_time` and return the computed times in the specified parameters.

    Args:
        timeWindowString (str): The time window string. Both start time and end time may be absolute times or relative times.
            The string is not case sensitive, but the start and end times must be separated by a comma or whitespace.
            - If absolute:
                - may contain commas and/or spaces
                - may specify a time portion or not:
            - If relative:
                - may not contain commas or spaces
                - are of the format &lt;*anchor*&gt;&lt;*offset*&gt;... where each offset is of the format [+-]&lt;*count*&gt;&lt;*unit*&gt;
                    Multiple offsets are allowed.
                    - Valid anchors are:
                        - `T` the current time
                        - `D` the start of the current day
                        - `B` or `S` - the start time (allowed only on end time and end must not depend on start time)
                        - `E` - the end time (allowed only on start time and the start time must not depend on end time)<br>
                    - The unit for each offset must be one of:
                        - `Y` - year(s)
                        - `M` - month(s)
                        - `D` - days(s)
                        - `H` - hour(s)
            - Examples:
                - `01Aug2024, 01:00 31Aug2024 2400`
                - `2024-01-01 2024-12-31,24:00`
                - `t-7d, t`
                - `e-1m+1d-2h,d`
                - `01Aug2024, 01:00, s+1m`
        startTime (HecTime): Is set to the parsed or computed start time if returned status == 0
        endTime (HecTime): Is set to the parsed or computed end time if returned status == 0

    Returns:
        int: `0` on success or `-1` on failure to parse the string
    """

    def setRelativeTime(
        this_time: HecTime, other_time: HecTime, relative_time_str: str
    ) -> None:
        this_time.set(other_time)
        for m in re.finditer(r"([+-]\d+)([YMDH])", relative_time_str):
            count = int(m.group(1))
            if m.group(2) == "Y":
                this_time.increment(count, Interval.MINUTES["1Year"])
            elif m.group(2) == "M":
                this_time.increment(count, Interval.MINUTES["1Month"])
            elif m.group(2) == "D":
                this_time.increment(count, Interval.MINUTES["1Day"])
            elif m.group(2) == "H":
                this_time.increment(count, Interval.MINUTES["1Hour"])

    status: int = 0
    timevals_start: Optional[list[int]] = None
    timevals_end: Optional[list[int]] = None
    now: datetime = datetime.now()
    parts = re.sub(r"\s+|,", " ", timeWindowString.strip().upper()).split()
    if not 2 <= len(parts) <= 4:
        status = -1
    elif len(parts) == 2:
        start, end = parts
    elif len(parts) == 4:
        start, end = f"{parts[0]} {parts[1]}", f"{parts[2]} {parts[3]}"
    elif re.match("^[TDE]", parts[0]):
        if re.match("^[TDBSE]", parts[1]) or re.match("^[TDBSE]", parts[2]):
            status = -1
        else:
            start, end = parts[0], f"{parts[1]} {parts[2]}"
    elif re.match("^[TDBS]", parts[2]):
        if re.match("^[TDBSE]", parts[1]):
            status = -1
        else:
            start, end = f"{parts[0]} {parts[1]}", parts[2]
    else:
        try:
            timevals_start = parseDateTimeStr(f"{parts[0]} {parts[1]}")
            tiemvals_end = parseDateTimeStr(parts[2])
        except:
            try:
                tiemvals_start = parseDateTimeStr(parts[0])
                timevals_end = parseDateTimeStr(f"{parts[1]} {parts[2]}")
            except:
                status = -1
    if status == 0:
        if timevals_start is not None:
            startTime.values = timevals_start
            endTime.values = cast(list[int], timevals_end)
        else:
            while True:
                start_depends_on_end = False
                t1 = HecTime(startTime)
                t2 = HecTime(endTime)
                if start[0] in "TD":
                    t3 = HecTime(startTime)
                    t3.set(now)
                    if start[0] == "D":
                        t3.values = cast(list[int], t3.values)[:3] + [0, 0, 0]
                    setRelativeTime(t1, t3, start)
                elif start[0] in "E":
                    start_depends_on_end = True
                else:
                    if t1.set(start) != 0:
                        status = -1
                        break
                if end[0] in "TD":
                    t3 = HecTime(endTime)
                    t3.set(now)
                    if end[0] == "D":
                        t3.values = cast(list[int], t3.values)[:3] + [0, 0, 0]
                    setRelativeTime(t2, t3, end)
                elif end[0] in "BS":
                    if start_depends_on_end:
                        status = -1
                        break
                    setRelativeTime(t2, t1, end)
                else:
                    if t2.set(end) != 0:
                        status = -1
                        break
                if start_depends_on_end:
                    setRelativeTime(t1, t2, start)
                break
            if status == 0:
                startTime.set(t1)
                endTime.set(t2)
    return status


def hm2m(hm: Union[str, int]) -> int:
    """
    Converts a time in hhmm format (integer or string) to minutes

    Args:
        hm (int): The time to convert (e.g, '0730', 730)

    Returns:
        int: The equivalent minutes (e.g., 450)
    """
    ihm = int(hm)
    return (ihm // 100) * 60 + (ihm % 100)


def idaywk(date: Union[int, list[int]]) -> int:
    """
    Returns the weekday (1=Sunday -> 7=Saturday) for the specified date.

    **NOTE** This differs from `datetime.weekday()` whch returns 0=Monday -> 6=Sunday.

    Args:
        date (Union[int, list[int]]): The date as:
    - `int` - number of days since 1899
    - `list` - a list of at least 3 integers specifying the year, month and day

    Returns:
        int: The weekday (1=Sunday -> 7=Saturday)
    """
    if isinstance(date, int):
        jul = date
    elif isinstance(date, list):
        jul = yearMonthDayToJulian(date[Y], date[M], date[D])
    return jul % 7 + 1


def ihm2m(hm: str) -> int:
    """
    Converts a string in hhmm format to integer minutes

    Args:
        hm (int): The time to convert (e.g, '0730', 730)

    Deprecated:
        Use [**`hm2m()`**](#hm2m) instead

    Returns:
        int: The equivalent minutes (e.g., 450)
    """
    return hm2m(hm)


def ihm2m_2(hm: str) -> int:
    """
    Converts integers in a string to integer minutes

    Args:
        hm (str): The string to collect integers from. Valid strings are:
            - "0730"
            - "730"
            - "7 30"
            - "0 7 3 0"
            - "7H30M"

    Returns:
        int: The equivalent minutes (e.g., 450)
    """
    digits = [c for c in hm if c.isdigit()]
    return hm2m("".join(digits))


def incrementTimeVals(
    values: list[int], incrementValue: int, granularity: int
) -> list[int]:
    """
    Increment or decrement time values by a specified amount and return the result

    Args:
        values (list[int]): The time values (`[year, month, day, hour, minute, sec]`) to increment/decrement.
        incrementValue (int): The number of granules to increment (>0) or decrement (<0)
        granularity (int): The granule size (SECOND_GRANULE, MINUTE_GRANULE, HOUR_GRANULE, or DAY_GRANULE)

    Raises:
        HecTimeException: if values is less than six items in length

    Returns:
        list[int]: The incremented or decremented values
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")

    newTimeVals: list[int] = values[:]
    if granularity == MINUTE_GRANULARITY:
        newTimeVals[S] = 0
    elif granularity == HOUR_GRANULARITY:
        newTimeVals[N] = newTimeVals[S] = 0
    if granularity == DAY_GRANULARITY:
        newTimeVals[H] = newTimeVals[N] = newTimeVals[S] = 0
    # ------------------ #
    # positive increment #
    # ------------------ #
    if incrementValue > 0:
        # -------------------------------------- #
        # increment the number of 400-year cyles #
        # -------------------------------------- #
        cycles = incrementValue // GRANULES_IN_CYCLE[granularity]
        newTimeVals[Y] += cycles * 400
        incrementValue -= cycles * GRANULES_IN_CYCLE[granularity]
        # ----------------------------------------------- #
        # increment individual years in the current cycle #
        # ----------------------------------------------- #
        while True:
            y = newTimeVals[Y] if newTimeVals[M] < 3 else newTimeVals[Y] + 1
            incr = GRANULES_IN_YEAR[granularity][isLeap(y)]
            if incr > incrementValue:
                break
            newTimeVals[Y] += 1
            incrementValue -= incr
        # ------------------------------------------------------------------------------------- #
        # decrement to the start of the current month to keep from worrying about month lengths #
        # ------------------------------------------------------------------------------------- #
        incr = (
            (newTimeVals[D] - 1) * GRANULES_IN_DAY[granularity]
            - newTimeVals[H] * GRANULES_IN_HOUR[granularity]
            - newTimeVals[N] * GRANULES_IN_MINUTE[granularity]
            - newTimeVals[S]
        )
        if incr > 0:
            newTimeVals[D] = 1
            newTimeVals[H] = newTimeVals[N] = newTimeVals[S] = 0
            incrementValue += incr
        # ---------------- #
        # increment months #
        # ---------------- #
        while True:
            incr = GRANULES_IN_MONTH[granularity][
                maxDay(newTimeVals[Y], newTimeVals[M])
            ]
            if incr > incrementValue:
                break
            newTimeVals[M] += 1
            normalizeTimeVals(newTimeVals)
            incrementValue -= incr
        # -------------- #
        # increment days #
        # -------------- #
        days = incrementValue // GRANULES_IN_DAY[granularity]
        incr = days * GRANULES_IN_DAY[granularity]
        if incr <= incrementValue:
            newTimeVals[D] += days
            incrementValue -= incr
            normalizeTimeVals(newTimeVals)
        # -------------- #
        # increment time #
        # -------------- #
        if granularity <= HOUR_GRANULARITY:
            hours = incrementValue // GRANULES_IN_HOUR[granularity]
            incr = hours * GRANULES_IN_HOUR[granularity]
            if incr <= incrementValue:
                newTimeVals[H] += hours
                incrementValue -= incr
            if granularity <= MINUTE_GRANULARITY:
                minutes = incrementValue // GRANULES_IN_MINUTE[granularity]
                incr = minutes * GRANULES_IN_MINUTE[granularity]
                if incr <= incrementValue:
                    newTimeVals[N] += minutes
                    incrementValue -= incr
                if granularity == SECOND_GRANULARITY:
                    newTimeVals[S] += incrementValue
            normalizeTimeVals(newTimeVals)
    elif incrementValue < 0:
        # ------------------ #
        # negative increment #
        # ------------------ #
        incrementValue = -incrementValue
        # --------------------------------------- #
        # decrement the number of 400-year cycles #
        # --------------------------------------- #
        cycles = incrementValue // GRANULES_IN_CYCLE[granularity]
        newTimeVals[Y] -= cycles * 400
        incrementValue -= cycles * GRANULES_IN_CYCLE[granularity]
        # ----------------------------------------------- #
        # decrement individual years in the current cycle #
        # ----------------------------------------------- #
        while True:
            y = newTimeVals[Y] if newTimeVals[M] > 2 else newTimeVals[Y] - 1
            incr = GRANULES_IN_YEAR[granularity][isLeap(y)]
            if incr > incrementValue:
                break
            newTimeVals[Y] -= 1
            incrementValue -= incr
        # ------------------------------------------------------------------------------------- #
        # decrement to the start of the current month to keep from worrying about month lengths #
        # ------------------------------------------------------------------------------------- #
        incr = (
            (newTimeVals[D] - 1) * GRANULES_IN_DAY[granularity]
            + newTimeVals[H] * GRANULES_IN_HOUR[granularity]
            + newTimeVals[N] * GRANULES_IN_MINUTE[granularity]
            + newTimeVals[S]
        )
        if incr <= incrementValue:
            newTimeVals[D] = 1
            newTimeVals[H] = newTimeVals[N] = newTimeVals[S] = 0
            incrementValue -= incr
        # ---------------- #
        # decrement months #
        # ---------------- #
        while True:
            incr = GRANULES_IN_MONTH[granularity][
                maxDay(*previousMonth(newTimeVals[Y], newTimeVals[M]))
            ]
            if incr > incrementValue:
                break
            newTimeVals[M] -= 1
            normalizeTimeVals(newTimeVals)
            incrementValue -= incr
        # -------------- #
        # decrement days #
        # -------------- #
        days = incrementValue // GRANULES_IN_DAY[granularity]
        incr = days * GRANULES_IN_DAY[granularity]
        if incr <= incrementValue:
            newTimeVals[D] -= days
            incrementValue -= incr
            normalizeTimeVals(newTimeVals)
        # -------------- #
        # decrement time #
        # -------------- #
        if granularity <= HOUR_GRANULARITY:
            hours = incrementValue // GRANULES_IN_HOUR[granularity]
            incr = hours * GRANULES_IN_HOUR[granularity]
            if incr <= incrementValue:
                newTimeVals[H] -= hours
                incrementValue -= incr
            if granularity <= MINUTE_GRANULARITY:
                minutes = incrementValue // GRANULES_IN_MINUTE[granularity]
                incr = minutes * GRANULES_IN_MINUTE[granularity]
                if incr <= incrementValue:
                    newTimeVals[N] -= minutes
                    incrementValue -= incr
                if granularity == SECOND_GRANULARITY:
                    newTimeVals[S] -= incrementValue
            normalizeTimeVals(newTimeVals)
    # ------------------------------------------------------- #
    # handle java implementation bug that discards 0004-12-31 #
    # ------------------------------------------------------- #
    if values[:3] >= [5, 1, 1] and newTimeVals[:3] < [5, 1, 1]:
        newTimeVals[D] -= 1
        normalizeTimeVals(newTimeVals)
    return newTimeVals


def inctim(*args: Any) -> None:
    """
    Increments a number of days since 1899 and minutes past midnight by a specified number of intervals of a specified size

    Args:
    - **6 Parameters:**
        - **interval (Union[TimeSpan, timedelta, int]):** - If integer, it is in minutes
        - **numPeriods (int):** - The number of intervals to increment
        - **startJulian (int):** - The starting number of days since 1899
        - **startMinutes (int):** - The starting minutes past midnight
        - **endJulian (list[int]):** - Element 0 receives the ending days since 1899
        - **endMinutes (list[int]):** - Element 0 receives the ending minutes past midnight
    - **7 Parameters:**
        - **interval (int):** - The interval in minutes or days
        - **unitFlag (int):** - A flag spcifying whether `interval` is in minutes (`0`) or days (`1`)
        - **numPeriods (int):** - The number of intervals to increment
        - **startJulian (int):** - The starting number of days since 1899
        - **startMinutes (int):** - The starting minutes past midnight
        - **endJulian (list[int]):** - Element 0 receives the ending days since 1899
        - **endMinutes (list[int]):** - Element 0 receives the ending minutes past midnight

    Raises:
        HecTimeException: if invalid arguments are passed to the function
    """
    if len(args) == 6:
        interval = args[0]
        numPeriods, startJulian, startMinutes = tuple(map(int, args[1:4]))
        endJulian, endMinutes = args[4:]
        unitFlag = 0
        if isinstance(interval, (TimeSpan, timedelta)):
            minutes = int(interval.total_seconds() / 60)
        elif isinstance(interval, int):
            minutes = interval
        else:
            raise TypeError(
                f"Invalid type for interval parameter: {interval.__class__.__name__}"
            )
    elif len(args) == 7:
        minutes, unitFlag, numPeriods, startJulian, startMinutes = tuple(
            map(int, args[:5])
        )
        endJulian, endMinutes = args[5:]
    else:
        raise HecTimeException(f"Expected 6 or 7 arguments to inctim, got {len(args)}")
    if not isinstance(endJulian, list):
        raise HecTimeException(
            f"Expected endJulian to be of type list, got {endJulian.__class__.__name}"
        )
    if not isinstance(endMinutes, list):
        raise HecTimeException(
            f"Expected endJulian to be of type list, got {endMinutes.__class__.__name}"
        )
    if unitFlag not in (0, 1):
        raise HecTimeException(f"Expected unitFlag to be 0 or 1, got {unitFlag}")
    if unitFlag == 1:
        minutes *= 1440
    values = 6 * [0]
    julianToYearMonthDay(startJulian, values)
    values[H], values[N] = divmod(startMinutes, 1440)
    t = HecTime(values)
    t.increment(numPeriods, minutes)
    endJulian[0] = t.julian()
    endMinutes[0] = t.minutesSinceMidnight()


def isLeap(y: int) -> bool:
    """
    Return whether the specified year is a leap year

    Args:
        y (int): The year

    Returns:
        bool: Whether the year is a leap year
    """
    return (not bool(y % 4) and bool(y % 100)) or (not bool(y % 400))


def isValidGranularity(value: int) -> bool:
    """
    Return whether specified granularity is valid

    Args:
        value (int): The granularity value to test

    Returns:
        bool: Whether the value is one of
        - [`SECOND_GRANULARITY`](#SECOND_GRANULARITY)
        - [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY)
        - [`HOUR_GRANULARITY`](#HOUR_GRANULARITY)
        - [`DAY_GRANULARITY`](#DAY_GRANULARITY)
    """
    return value in GRANULARITIES


def isValidTime(dateTime: Union[int, list[int]], granularity: int) -> bool:
    """
    Return whether a specified time integer or time values are in the valid range for the specified granularity

    Args:
        dateTime (Union[int, list[int]]): The time integer or time values (`[year, month, day, hour, minute, second]`) to check validity for
        granularity (int): The granularity to check validity for

    Returns:
        bool: Whether the time integer or time values are in the valid range for the granularity
    """
    if isinstance(dateTime, int):
        return (
            cast(int, EXTENTS[granularity][DATE_INTEGER][MIN_EXTENT])
            <= dateTime
            <= cast(int, EXTENTS[granularity][DATE_INTEGER][MAX_EXTENT])
        )
    else:
        return (
            cast(tuple[int, ...], EXTENTS[granularity][DATE_VALUES][MIN_EXTENT])
            <= tuple(dateTime)
            <= cast(tuple[int, ...], EXTENTS[granularity][DATE_VALUES][MAX_EXTENT])
        )


def iymdjl(year: int, month: int, day: int) -> int:
    """
    Returns the number of days since 31Dec1899 for a specified year, month, and day

    Args:
        year (int): The year
        month (int): The month
        day (int): The day

    Deprecated:
        Use [**`yearMonthDayToJulian()`**](#yearMonthDayToJulian) instead

    Returns:
        int: The number of days sinc 31Dec1899
    """
    warnings.warn(
        "The iymdjl() function is deprecated. Please use the yearMonthDayToJulian() function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return yearMonthDayToJulian(year, month, day)


def jliymd(*args: Any) -> None:
    """
    Populates year, month, and day arguments with the appropriate values for a specified number of days since 31Dec1899

    Args:
    - **2 args:**
      - **jul (int):** The number of days since 31Dec1899
      - **ymd (list[int]):** A list of length >= 3 that receives the year, month, and day
    - **4 args**
      - **jul (int):** The number of days since 31Dec1899
      - **year (list[int]):** An integer list whose first value received the year
      - **month (list[int]):** An integer list whose first value received the month
      - **day (list[int]):** An integer list whose first value received the day

    Deprecated:
        Use [**`julianToYearMonthDay()`**](#julianToYearMonthDay) instead

    Raises:
        HecTimeException: if invalid arguments are specified
    """
    warnings.warn(
        "The jliymd() function is deprecated. Please use the julianToYearMonthDay() function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return julianToYearMonthDay(*args)


def juldat(julian: int, style: int) -> str:
    """
    Returns the date of the specified number of days since 31Dec1899 in the specified style

    Args:
        julian (int): The number of days since 1899
        style (int): The style to return the date in. See [**`date()`**](#HecTime.date)

    Returns:
        str: The date in the specified style
    """
    values = 6 * [0]
    julianToYearMonthDay(julian, values)
    t = HecTime(values)
    t.midnight_as_2400 = False
    return t.date(style)


def julianToYearMonthDay(*args: Any) -> None:
    """
    Populates year, month, and day arguments with the appropriate values for a specified number of days since 31Dec1899

    Args:
    - **2 args**:
      - **jul (int):** The number of days since 31Dec1899
      - **ymd (list[int]):** A list of length >= 3 that receives the year, month, and day
    - **4 args**
      - **jul (int):** The number of days since 31Dec1899
      - **year (list[int]):** An integer list whose first value received the year
      - **month (list[int]):** An integer list whose first value received the month
      - **day (list[int]):** An integer list whose first value received the day

    Raises:
        HecTimeException: if invalid arguments are specified
    """
    args_okay = (
        len(args) in (2, 4)
        and type(args[0]) == int
        and all(map(lambda p: type(p) == list, args[1:]))
    )
    if args_okay:
        y, m, d = to0000(getTimeVals(args[0], DAY_GRANULARITY))[:3]
        if [y, m, d] < [5, 1, 1]:
            values = [y, m, d + 1, 0, 0, 0]
            # in addition to the missing 31Dec0004, java code has
            # another anomoly at 31Dec0000 as shown below
            #     Jul  Y   M   D
            # -693597, 0, 12, 28
            # -693596, 0, 12, 29
            # -693595, 0, 12, 30
            # -693594, 1,  1,  1
            # -693593, 1,  1,  2
            # -693592, 1,  1,  3
            if [y, m, d] < [1, 1, 1]:
                values[D] -= 1
            normalizeTimeVals(values)
            y, m, d = values[:3]
            if [y, m, d] == [0, 12, 31]:
                y, m, d = 1, 1, 1
        if len(args) == 2:
            if len(args[1]) > 2:
                args[1][:3] = [y, m, d]
            else:
                args_okay = False
        else:
            if all([len(args[i]) > 0 for i in (1, 2, 3)]):
                args[1][0] = y
                args[2][0] = m
                args[3][0] = d
            else:
                args_okay = False
    if not args_okay:
        raise HecTimeException(f"Invalid argments for julianToYearMonthDay(): {args}")


def maxDay(y: int, m: int) -> int:
    """
    Return the last month day for a specified year and month

    Args:
        y (int): The year
        m (int): The month

    Returns:
        int: The last calendar day of the specified month
    """
    return (
        31
        if m in (1, 3, 5, 7, 8, 10, 12)
        else 30 if m in (4, 6, 9, 11) else 29 if isLeap(y) else 28
    )


def m2hm(m: int) -> int:
    """
    Returns the equivalent time integer (hhmm) for a specified minute count

    Args:
        m (int): The minutes to convert (e.g., 450)

    Returns:
        int: The time equivalent in hhmm (e.g, 730)
    """
    return m // 60 % 100 % 24 * 100 + m % 60


def m2ihm(mintues: int, hourMinutes: list[str]) -> int:
    """
    Returns the equivalent time integer (hhmm) for a specified minute count and
    places the string representaion in HHMM format in the specified variable


    Args:
        m (int): The minutes to convert (e.g., 450)
        hourMinutes (list[str]): Element 0 receives string equivalen in HHMM format (e.g., "0730")

    Deprecated:
        Use [**`m2hm()`**](#m2hm) instead

    Returns:
        int: The time equivalent in hhmm (e.g, 730)
    """
    warnings.warn(
        "The m2ihm() function is deprecated. Please use the m2hm() function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    hm = m2hm(mintues)
    hourMinutes[0] = f"{hm:04d}"
    return hm


def minutesSinceMidnight(values: list[int]) -> int:
    """
    Returns the number of minutes past midnight for specified time values

    Args:
        values (list[int]): The time values (`[year, month, day, hour, minute, second]`)

    Raises:
        HecTimeException: If `values` is less than six items in length

    Returns:
        int: The number of minutes past midnight
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")
    return values[H] * 60 + values[N]


def nextMonth(y: int, m: int) -> tuple[int, int]:
    """
    Returns the next year and for a specified year and month.

    Args:
        y (int): The specified year
        m (int): The specified month

    Returns:
        tuple[int, int]: The next year and month
    """
    m += 1
    if m > 12:
        y += 1
        m = 1
    return y, m


def nopers(*args: Any) -> int:
    """
    Returns the complete number of intervals between two times

    Args:
        5-parameter version
          - **interval (Union[Interval, int]):** The interval to compute the number of. If an integer, must be the
            actual or characteristic minutes of a standard Interval object
          - **startJulian (int):** The days since 1899 of the first time
          - **startMinutes (int):** The minutes past midnight of the first time
          - **endJulian (int):** The days since 1899 of the second time
          - **endMinutes (int):** The minutes past midnight of the second time
        6 parameter version
          - **interval (int):** The number of minutes or days in the interval to compute the number of. Must be the
            actual or characteristic number of minutes (or equivalent days) of a standard Interval object
          - **unitFlag (int):** 0 for interval in minutes, 1 for interval in days
          - **startJulian (int):** The days since 1899 of the first time
          - **startMinutes (int):** The minutes past midnight of the first time
          - **endJulian (int):** The days since 1899 of the second time
          - **endMinutes (int):** The minutes past midnight of the second time

    Raises:
        HecTimeException: if the interval is not one of the standard intervals

    Returns:
        int: The number of complete intervals between the two times
    """

    interval: Union[Interval, int]
    minutes: int
    unitFlag: int
    startJulian: int
    startMinutes: int
    endJulian: int
    endMinutes: int
    timeVals1: list[int]
    timeVals2: list[int]
    if len(args) == 5:
        interval, startJulian, startMinutes, endJulian, endMinutes = args
        if isinstance(interval, Interval):
            minutes = interval.minutes
        else:
            minutes = interval
    elif len(args) == 6:
        minutes, unitFlag, startJulian, startMinutes, endJulian, endMinutes = args
        if unitFlag:
            minutes *= 1440
    if not minutes in Interval.MINUTES.values():
        raise HecTimeException(
            f"Interval {minutes} is not a standard interval in minutes"
        )
    timeVals1 = 6 * [0]
    julianToYearMonthDay(startJulian, timeVals1)
    timeVals1[H], timeVals1[N] = divmod(startMinutes, 60)
    timeVals2 = 6 * [0]
    julianToYearMonthDay(endJulian, timeVals2)
    timeVals2[H], timeVals2[N] = divmod(endMinutes, 60)
    return HecTime(timeVals1).computeNumberIntervals(HecTime(timeVals2), minutes)


def normalizeDateStyle(style: int) -> int:
    """
    Returns a valid date style for a specified input style

    Args:
        style (int): The input date style

    Returns:
        int: The valid date style
    """
    style = int(math.fmod(style, 1000))  # don't use % for negatives
    if style in (-113, -112, -111, -102, -101, -13, -12, -11):
        pass
    else:
        if -2 <= style <= 19 or 100 <= style <= 119:
            pass
        elif style < 0:
            style = -11 if style < -10 else -1
        elif style < 100:
            style = 10 + style % 10
        else:
            style = 110 + style % 10
    return style


def normalizeTimeVals(values: list[int]) -> None:
    """
    Normalize a list of time values (`[year, month, day, hour, minute, second]`) in place.

    Adjusts each element of the list to be in the valid range for a date/time value.

    Args:
        values (list[int]): The values to normalize.

    Raises:
        HecTimeException: if values is less that six items in length
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")

    # --------------------------- #
    # do the year and month first #
    # --------------------------- #
    while values[M] < 1:
        values[Y] -= 1
        values[M] += 12
    while values[M] > 12:
        values[Y] += 1
        values[M] -= 12
    # --------------------- #
    # next skip to the time #
    # --------------------- #
    while values[S] < 0:
        values[N] -= 1
        values[S] += 60
    while values[S] > 59:
        values[N] += 1
        values[S] -= 60
    while values[N] < 0:
        values[H] -= 1
        values[N] += 60
    while values[N] > 59:
        values[H] += 1
        values[N] -= 60
    while values[H] < 0:
        values[D] -= 1
        values[H] += 24
    while values[H] > 23:
        values[D] += 1
        values[H] -= 24
    # ------------------------------------------------------------- #
    # finally work on the day, which may affect year an month again #
    # ------------------------------------------------------------- #
    while values[D] < 1:
        y, m = previousMonth(values[Y], values[M])
        values[D] += maxDay(y, m)
        values[Y], values[M] = y, m
    d = maxDay(values[Y], values[M])
    while values[D] > d:
        values[M] += 1
        if values[M] > 12:
            values[Y] += 1
            values[M] -= 12
        values[D] -= d
        d = maxDay(values[Y], values[M])


def parseDateTimeStr(dateTimeStr: str) -> list[int]:
    """
    Parse date/time strings of various formats into time values (`[year, month, day, hour, minute, second]`).

    The string must contain at least year, month, day. Missing seconds, (minutes, seconds), or (hours, minutes, seconds)
    are set to zero.

    For strings that cannot be parsed with this method, use [**`HecTime.strptime()`**](#HecTime.strptime)

    Args:
        dateTimeStr (str): The date/time string

    Raises:
        HecTimeException: if dateTimeStr cannot be parsed into at least year, month, and day

    Returns:
        list[int]: The time values as parsed from the date/time string.

    See Also:
        [**`HecTime.strptime()`**](#HecTime.strptime)
    """

    y: Optional[int] = None
    m: Optional[int] = None
    d: Optional[int] = None
    h: Optional[int] = None
    n: Optional[int] = None
    s: Optional[int] = None

    # --------------------- #
    # handle ISO 8601 first #
    # --------------------- #
    iso8601Pattern = re.compile(
        # Group contents
        #  1 = year
        #  2 = month
        #  3 = day
        #  5 = hour
        #  7 = minute
        #  9 = second
        # 10 = tz string
        # 11 = tz hour
        # 13 = tz minute
        r"(-?\d{4,})-(\d{2})-(\d{2})(T(\d{2})(:(\d{2})(:(\d{2}))?)?)?(Z|([+-]?\d{2})(:(\d{2}))?)?"
    )

    matcher = iso8601Pattern.match(dateTimeStr)
    if matcher and len(matcher.group(0)) == len(dateTimeStr):
        y, m, d, h, n, s = [
            0 if v is None else int(v)
            for v in [matcher.group(i) for i in (1, 2, 3, 5, 7, 9)]
        ]
        # TODO - Handle time zone
        return [y, m, d, h, n, s]

    # ---------------------- #
    # handle generic pattern #
    # ---------------------- #
    separatorPattern = re.compile(r"\W+")
    dmyFieldPattern = re.compile(r"(\d+)([a-z]+)(-?\d+)", re.I)

    strParts: list[str] = []
    first = True
    startsWithNegativeSign = bool(dateTimeStr.startswith("-"))
    startsWithDmy = False
    matcher = dmyFieldPattern.match(dateTimeStr)
    if matcher:
        startsWithDmy = True
        strParts.extend(list(matcher.groups()))
        strParts[1] = str(MONTHS_BY_ABBREV[strParts[1][:3].upper()])
        dateTimeStr = dateTimeStr[matcher.end(0) :].strip()
    for token in separatorPattern.split(dateTimeStr[startsWithNegativeSign:]):
        if not token:
            continue
        if first and not startsWithDmy:
            if startsWithNegativeSign:
                strParts.append(f"-{token}")
            else:
                strParts.append(token)
            first = False
        else:
            strParts.append(token)
    if len(strParts) < 3:
        raise HecTimeException(f"Invalid date/time string: {dateTimeStr}")
    if len(strParts) > 3 and len(strParts[-1]) == 4 and strParts[-1].isdigit():
        sn, ss = strParts[-1][:2], strParts[-1][2:]
        strParts = strParts[:-1] + [sn, ss]
    intParts: list[int] = list(map(int, strParts))
    intParts += (6 - len(intParts)) * [0]
    if startsWithDmy:
        y, m, d = [intParts[i] for i in (2, 1, 0)]
    elif startsWithNegativeSign:
        y, m, d = [intParts[i] for i in (0, 1, 2)]
    else:
        if len(strParts[0]) > 2:
            # yyyy mm dd
            y = intParts[0]
            m = intParts[1]
            d = intParts[2]
        elif len(strParts[2]) > 2:
            # mm dd yyyy
            y = intParts[2]
            m = intParts[0]
            d = intParts[1]
        elif abs(intParts[0]) > 31:
            # yy mm dd
            y = addCentury(intParts[0])
            m = intParts[1]
            d = intParts[2]
        elif abs(intParts[2]) > 31:
            # mm dd yy
            y = addCentury(intParts[2])
            m = intParts[0]
            d = intParts[1]
        else:
            # bias toward dd mm yy
            y = addCentury(intParts[2])
            m = intParts[0]
            d = intParts[1]
            if d > maxDay(y, m):
                # fall back to yy mm dd
                y = addCentury(intParts[0])
                m = intParts[1]
                d = intParts[2]
                if d > maxDay(y, m):
                    raise Exception
    if not (1 <= m <= 12) or not (1 <= d <= maxDay(y, m)):
        raise Exception
    h = int(intParts[3])
    if not 0 <= h <= 24:
        raise Exception
    n = intParts[4]
    if not 0 <= n <= 59:
        raise Exception
    s = intParts[5]
    if not 0 <= s <= 59:
        raise Exception
    return [y, m, d, h, n, s]


def previousMonth(y: int, m: int) -> tuple[int, int]:
    """
    Returns the previous year and for a specified year and month.

    Args:
        y (int): The specified year
        m (int): The specified month

    Returns:
        tuple[int, int]: The previous year and month
    """
    m -= 1
    if m < 1:
        y -= 1
        m = 12
    return y, m


def secondsSinceMidnight(values: list[int]) -> int:
    """
    Returns the number of seconds past midnight for specified time values

    Args:
        values (list[int]): The time values (`[year, month, day, hour, minute, second]`)

    Raises:
        HecTimeException: If `values` is less than six items in length

    Returns:
        int: The number of seconds past midnight
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")
    return values[H] * 3600 + values[N] * 60 + values[S]


def systim(
    julian: list[int],
    time: list[int],
    timeInMinutes: Optional[bool] = False,
    inTimeZone: Optional[str] = None,
) -> None:
    """
    Get the current time as days since 1899 and minutes or seconds past midnight and return in parameters,
    optionally in a specified time zone

    Args:
        julian (list[int]): A list of length > 0 whose first value receives the current days since 1899
        time (list[int]): A list of length > 0 whose first value receives the current minutes or seconds past midnight
        timeInMinutes (Optional[bool]): Specifies whether to return the time in minutes (`True`) or seconds (`False`) past midnight.
            Default is False
        inTimeZone (Optional[str]): If present, specifies the time zone of the current time. The days and time values
            will be converted from this time zone to UTC
    """
    if inTimeZone:
        local_offset = datetime.now().astimezone().utcoffset()
        other_offset = datetime.now().astimezone(ZoneInfo(inTimeZone)).utcoffset()
        if local_offset is None or other_offset is None:
            raise HecTimeException("Error determining UTC offset for time zone")
        local_offset_minutes = int(local_offset.total_seconds() / 60)
        other_offset_minutes = int(other_offset.total_seconds() / 60)
        diff = other_offset_minutes - local_offset_minutes
    else:
        diff = 0
    now = datetime.now() + timedelta(minutes=diff)
    julian[0] = yearMonthDayToJulian(now.year, now.month, now.day)
    if timeInMinutes:
        time[0] = now.hour * 60 + now.minute
    else:
        time[0] = now.hour * 3660 + now.minute * 60 + now.second


def to0000(values: list[int]) -> list[int]:
    """Return a copy of time values (`[year, month, day, hour, minute, second]`) with
    `[..., 24, 0, 0]` changed to `[..., 0, 0, 0]` of the next day

    Args:
        values (list[int]): The values to modify if ending in `[24, 0, 0]`

    Raises:
        HecTimeException: if values less than six items in length

    Returns:
        list[int]: A copy of the time values, modified if necessrary
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")

    newTimeVals: list[int] = values[:]
    if newTimeVals[H] == 24 and newTimeVals[N] == newTimeVals[S] == 0:
        newTimeVals[H] = 0
        newTimeVals[D] += 1
        if newTimeVals[D] > maxDay(newTimeVals[Y], newTimeVals[M]):
            newTimeVals[D] = 1
            newTimeVals[M] += 1
            if newTimeVals[M] > 12:
                newTimeVals[M] = 1
                newTimeVals[Y] += 1
    if newTimeVals[:3] == [4, 12, 31]:
        newTimeVals[D] = 30
    return newTimeVals


def to2400(values: list[int]) -> list[int]:
    """Return a copy of time values (`[year, month, day, hour, minute, second]`) with
    `[..., 0, 0, 0]` changed to `[..., 24, 0, 0]` of the previous day

    Args:
        values (list[int]): The values to modify if ending in `[0, 0, 0]`

    Raises:
        HecTimeException: if values less than six items in length

    Returns:
        list[int]: A copy of the time values, modified if necessrary
    """
    if len(values) < 6:
        raise HecTimeException(f"Invalid time list: {values}")

    newTimeVals: list[int] = values[:]
    if newTimeVals[H] == newTimeVals[N] == newTimeVals[S] == 0:
        newTimeVals[H] = 24
        newTimeVals[D] -= 1
        if newTimeVals[D] < 1:
            newTimeVals[M] -= 1
            if newTimeVals[M] < 1:
                newTimeVals[M] = 12
                newTimeVals[Y] -= 1
            newTimeVals[D] = maxDay(newTimeVals[Y], newTimeVals[M])
    if newTimeVals[:3] == [4, 12, 31]:
        newTimeVals[D] = 30
    return newTimeVals


def yearMonthDayToJulian(
    y: int, m: int, d: int, account_for_offset: bool = True
) -> int:
    """
    Returns the number of days since 31Dec 1899 for a specified year, month, and day

    Args:
        y (int): The year
        m (int): The month
        d (int): The day
        account_for_offset (bool) : (Default = True) Specifies whether to account for the missing date (31Dec0004).
            This should be True unless the function is called from an HecTime method which already
            accounts for it.

    Returns:
        int: The number of days since 31Dec1899
    """
    values = [y, m, d] + [0, 0, 0]
    julian = getTimeInt(values, DAY_GRANULARITY)  # takes care of skipped 31Dec0004
    return julian


def ymddat(ymd: list[int], style: int, err: list[int]) -> str:
    """
    Returns the date in the specified style

    Args:
        ymd (list[int]): The year, month, and day to format
        style (int): The style to use (see [**`HecTime.date()`**](#HecTime.date))
        err (list[int]): Element 0 recieve `0` on success and `-1` otherwise

    Returns:
        str: The date in the specified style, or None if err[0] == -1
    """
    try:
        t = HecTime([ymd[Y], ymd[M], ymd[D], 0, 0, 0])
        t.midnight_as_2400 = False
    except:
        err[0] = -1
        return ""
    err[0] = 0
    return t.date(style)


def zofset(
    julian: list[int],
    minutes: list[int],
    interval: int,
    operation: int,
    offset: list[int],
) -> None:
    """
    Computes the offet into a standard interval and/or adjusts the specified time to be at the computed offset

    **NOTE:** Unlike [`HecTime.adjustToIntervalOffset`](#HecTime.adjustToIntervalOffset), any adjustments made will result
    in the output time being earlier than the input time.

    Args:
        julian (list[int]): On input, element 0 specifies the days since 1899 of the date On output,
            element[0] recieves the adjusted days since 1899 if operation is `1` or `2`
        minutes (list[int]): On input, element 0 specifies the minutes past midnight of the time. On output,
            element[0] recieves the adjusted minutes past midnight if operation is `1` or `2`
        interval (int): The interval used to compute the offset and/or adjust the time
        operation (int):<br>
            - **0:** Compute the offset only (return in `offset[0]`)
            - **1:** Compute the offset (return in `offset[0]`) and adjust the time to the offset
                (return in `julian[0]` and `minutes[0]`)
            - **2:** adjust the time to the offset only (return in `julian[0]` and `minutes[0]`)
        offset (list[int]): On output, element 0 receives the computed offset if operation is `0` or `1`
    """
    t = HecTime()
    t.setJulian(julian[0], minutes[0])
    intvl_offset = cast(int, t.getIntervalOffset(interval))
    if operation in (0, 1):
        offset[0] = intvl_offset
    if operation in (1, 2):
        t.adjustToIntervalOffset(interval, 0)
        julian[0], minutes[0] = divmod(cast(int, t.getMinutes()), 1440)


# -------------- #
# Module classes #
# -------------- #
class HecTimeException(Exception):
    """
    Exception specific to the hectime module
    """

    pass


@total_ordering
class HecTime:
    # Ugliness trying to work around pdoc automatically collapsing "hec.heclib.util.HecTime" and linking it
    # to the HecTime class anchor in the current page.
    """
    Class to facilitate moving Jython scripts that use Java class <code>hec.heclib.util.</code><code>HecTime</code> to Python

    Implementation:
        **Granularity**

        Like Java HecTime, `HecTime` objects can be instaniated with different time granularities, with each granule specifying a
        second, minute, hour, or day. Specifically:
        <pre>
        <table>
        <tr><th>Granularity</th><th>Integer Range</th><th>Each Granule Specifies</th><th>Date Range</th></tr>
        <tr><td>SECOND_GRANULARITY<br>= 10</td><td>-2147483648<br>+2147483647</td><td>Seconds after<br>01Jan1970, 00:00</td><td>+1901-12-13T20:45:52<br>+2030-01-19T03:14:17</td></tr>
        <tr><td>MINUTE_GRANULARITY<br>= 11</td><td>-2147483648<br>+2147483647</td><td>Minutes after<br>31Dec1899, 00:00</td><td>-2184-12-06T21:52<br>+5983-01-23T02:07</td></tr>
        <tr><td>HOUR_GRANULARITY<br>= 12</td><td>-2147483648<br>+2147483647</td><td>Hours after<br>31Dec1899, 00:00</td><td>-243084-03-22T16<br>+246883-10-08T07</td></tr>
        <tr><td>DAY_GRANULARITY<br>= 13</td><td>-2147483645<br>+2146789687</td><td>Days after<br>31Dec1899</td><td>-5877711-06-22<br>+5879610-07-10</td></tr>
        </table>
        </pre>

        The default granularity is MINUTE_GRANULARITY, but this may be overridden when calling [`HecTime()`](#HecTime).

        **Chainable methods**

        Since, unlike Java, Python allows code to ignore the return value from functions and methods, many HecTime methods
        with a `void` return type in Java now return a modified `HecTime` object. This allows the chaining of methods
        together for simplify code. For example:
        <pre>
        t = HecTime()
        t.setCurrent()
        t.adjustToIntervalOffset(intvl, 0)
        t.increment(1, intvl)
        </pre>
        can now be coded as:
        <pre>
        t = HecTime.now().adjustToIntervalOffset(intvl, 0).increment(1, intvl)
        </pre>
        although the previous style is still supported.


        **Compatibility with `datetime`**

        This class is written to be trivially convertable to/from `datetime` objects and updatable via `timedelta` objects.
        Like `datetime` objects, `HecTime` objects are not time zone aware unless given time zone information. For `HecTime`
        objects the `atTimeZone()` method is used for this purpose. Also like `datetime` objects, using the [`astimezone()`](#HecTime.astimezone)
        method causes the object to act as if it had been initialized with the local time zone.

        Initialization from a `datetime` object is acccomplished via `ht = HecTime(dt_obj)`. Retieval of a `datetime`
        object is accomplished via `dt_obj = ht.datetime()`. The [`HecTime.atTimeZone(tz)`](#HecTime.atTimeZone) accomplishes
        the same thing as `datetime.replace(tzinfo=tz)`, and the [`HecTime.astimezone(tz)`](#HecTime.astimezone) accomplishes
        the same thing as `datetime.astimezone(tz)`

        `datetime` methods, properties, and operators supported in `HecTime` objects are:
        - Methods
            - `now()` (static method)
            - `astimezone(timezone)`<sup>*</sup>
            - `strftime(format)`
            - `strptime(dateTimeString, format)`
            - `__str__()` (used in `print()`)
        - Properties
            - `year`
            - `month`
            - `day`
            - `hour`
            - `minute`
            - `second`
            - `tzinfo`
        - Operators
            - `+` and `+=`
            - `-` and `-=`
            - `==` and `!=`
            - `<` and `<=`
            - `>` and >=`

        <sup>*</sup>The `astimezone(timezone)`, method, like all `HecTime` methods that take time zone will accept:
        - `ZoneInfo` object
        - String (timezone name)
        - `HecTime` object (the object's time zone is used)
        - `datetime` object (the object's time zone is used)

        *Note:* Compatibility with `datetime` as well as time zone support is only available on `HecTime` objects that are
        within the `datetime` object range of 01Jan0001, 00:00 through 31Dec9999, 23:59. Also, time zone support is not
        provided for `HecTime` objects of `DAY_GRANULARITY`.

        **Addition, subtraction, and comparison operators**

        Integers, `HecTime` objects, `timedelta` objects, and specially formatted strings can be used on the right side of the
        `+` and `+=` operators. The result is always another `HecTime` object. Allowing `HecTime` objects to be added to each
        other breaks the similarity with `datetime`, but the Java HecTime code suppored it.

        Integers, `HecTime` objects, `datetime` objects, `timedelta` objects, and specially formatted strings and be usd
        on the right side of the `-` operator. The result is a `HecTime` object for intgers, `timedelta` objects and strings.
        it is a `timedelta` object for `HecTime` and `timedelta` objects. Integers, `timedelta` objects and specially foratted
        strings can also be on the right side of the `-=` operator

        Adding and subtracting integers adds or subracts the number of granules in the object so the change may be in seconds,
        minutes, hours, or days, depending on the object's granularity.

        Strings of the format used for the offset portion of relative time strings in [`getTimeWindow()`](#getTimeWindow) can be
        used in addition and subtraction operators. Examples
            - `t - "1y"` would return an `HecTime` object one year prior to the `t` object
            - `t += "3m-2d+1h"` would increment the `t` object forward 3 months, back 2 days and forward 1 hour.

        `HecTime` objects can be compared with each other or with `datetime` objects using the standard operators (`==`, `!=`, `<`, `<=`, `>`, `>=`).
        Either type may be on either side of the operators.

        **Use of properties**

        Many methods are deprecated and will generate deprecation warnings when used. Most have been replaced by direct
        read/write or read-only properties.

        The `value()`, `year()`, `month()`, `day()`, `hour()`, `minute()`, and `second()` methods are still supported but
        are accessed in a more pythonic way as read/write (`value`) or read-only (`year`, `month`, `day`, `hour`, `minute`, `second`)
        properties. There is no clean way to issue deprecation warning if these properties are accessed by their getter functions.
    """

    @staticmethod
    def now(granularity: int = MINUTE_GRANULARITY) -> "HecTime":
        """
        Returns a new `HecTime` object initialized to the current system time and specified or default granularity

        Args:
            granularity (int, optional): The granularity of the new object. Defaults to MINUTE_GRANULARITY.

        Returns:
            HecTime: The newly created object
        """
        t = HecTime(granularity)
        t.setCurrent()
        return t

    def __init__(self, *args: Any):
        """
        Initializes a newly-created `HecTime` object.

        <h6 id="arguments">Arguments:</h6>
        - **`HecTime()`** initializes granularity to [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY) and time to [`UNDEFINED_TIME`](#UNDEFINED_TIME)
        - **`HecTime(granularity: int)`** initializes granularity to `granularity` and time to [`UNDEFINED_TIME`](#UNDEFINED_TIME)
        - **`HecTime(values: Union[list[int],tuple[int,...]])`** initializes granularity to [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY) and time to `values`
        - **`HecTime(otherHecTime: HecTime)`** initializes to the same granularity and time as `otherHecTime`
        - **`HecTime(dt: datetime)`** initializes granularity to [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY) and time to the value of `dt`.
        - **`HecTime(dateTimeStr: str)`** initializes granularity to [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY) and time to the results of [parseDateTimeStr](#parseDateTimeStr)(dateTimeStr)
        - **`HecTime(timeInt: int, granularity: int)`** initializes to `timeInt` and `granularity`
        - **`HecTime(dateStr: str, timeStr: str)`** initializes granularity to [`MINUTE_GRANULARITY`](#MINUTE_GRANULARITY) and time to the results of [parseDateTimeStr](#parseDateTimeStr)(`dateStr`+"&nbsp;"+`timeStr`)
        - **`HecTime(dateStr: str, timeStr: str, granularity: int)`** initializes to the specified granularity and results of [parseDateTimeStr](#parseDateTimeStr)(`dateStr`+"&nbsp;"+`timeStr`)

        Raises:
            HecTimeException: if invalid parameters are specified
        """
        # ----------------------------------------------------------- #
        # NOTE __timevals ALWAYS has midnight as 0000 if not None     #
        # It is converted to midnight as 2400 out output as necessary #
        # ----------------------------------------------------------- #
        self.__value: Optional[int] = UNDEFINED_TIME
        self.__granularity: int = MINUTE_GRANULARITY
        self.__values: Optional[list[int]] = None
        self.__midnight_as_2400: bool = True
        self.__default_date_style = 2
        self.__tz = None

        if len(args) == 0:
            # -------------- #
            # Zero arguments #
            # -------------- #
            pass
        elif len(args) == 1:
            # ------------ #
            # One argument #
            # ------------ #
            if isinstance(args[0], int):
                # initialize from a granularity
                self.granularity = args[0]
            elif isinstance(args[0], (list, tuple)):
                # initialize from a list or tuple of integers
                self.set(args[0])
            elif isinstance(args[0], HecTime):
                # initialize from another HecTime object
                self.set(args[0])
            elif isinstance(args[0], datetime):
                # intiialize from a datetime object
                self.set(args[0])
            elif isinstance(args[0], str):
                # initialize from a datetime string
                self.set(parseDateTimeStr(args[0]))
            else:
                raise HecTimeException(
                    f"Invalid initializer: {args[0].__class__.__name__} {args[0]}"
                )
        elif len(args) == 2:
            # ------------- #
            # Two arguments #
            # ------------- #
            if isinstance(args[0], int) and isinstance(args[1], int):
                value, granularity = args[0], args[1]
                self.granularity = granularity
                self.set(value)
            elif isinstance(args[0], str) and isinstance(args[1], str):
                dateStr, timeStr = args
                self.set(f"{dateStr} {timeStr}")
            else:
                raise HecTimeException(
                    "Invalid initializers: "
                    + ",".join(
                        [f"{args[i].__class__.__name__} {args[i]}" for i in range(2)]
                    )
                )
        elif len(args) == 3:
            # --------------- #
            # Three arguments #
            # --------------- #
            if (
                isinstance(args[0], str)
                and isinstance(args[1], str)
                and isinstance(args[2], int)
            ):
                dateStr, timeStr, granularity = args
                self.granularity = granularity
                self.set(f"{dateStr} {timeStr}")
            else:
                raise HecTimeException(
                    "Invalid initializers: "
                    + ",".join(
                        [f"{args[i].__class__.__name__} {args[i]}" for i in range(3)]
                    )
                )
        else:
            raise HecTimeException(
                "Invalid initializers: "
                + ",".join(
                    [
                        f"{args[i].__class__.__name__} {args[i]}"
                        for i in range(len(args))
                    ]
                )
            )

    def __iadd__(self, other: object) -> "HecTime":
        if self.defined:
            if isinstance(other, int):
                self.value += other
            elif isinstance(other, HecTime):
                if other.defined:
                    self.value += other.value * (
                        SECONDS_IN_GRANULE[other.granularity]
                        // SECONDS_IN_GRANULE[self.granularity]
                    )
            elif isinstance(other, timedelta):
                s = other.total_seconds()
                self.value += int(
                    abs(s)
                    // SECONDS_IN_GRANULE[self.granularity]
                    * (-1 if s < 0 else 1)
                )
            elif isinstance(other, TimeSpan):
                vals = [
                    v1 + v2
                    for v1, v2 in zip(
                        cast(list[int], self.values), cast(list[int], other.values)
                    )
                ]
                self.set(vals)
            elif isinstance(other, str):
                for m in re.finditer(r"([+-]?\d+)([YMDH])", other):
                    count = int(m.group(1))
                    if m.group(2) == "Y":
                        self.increment(count, Interval.MINUTES["1Year"])
                    elif m.group(2) == "M":
                        self.increment(count, Interval.MINUTES["1Month"])
                    elif m.group(2) == "D":
                        self.increment(count, Interval.MINUTES["1Day"])
                    elif m.group(2) == "H":
                        self.increment(count, Interval.MINUTES["1Hour"])
            else:
                raise HecTimeException(
                    f"Cannot add {other.__class__.__name__} to HecTime object"
                )
        return self

    def __isub__(self, other: object) -> "HecTime":
        if self.defined:
            if isinstance(other, int):
                self.value -= other
            elif isinstance(other, HecTime):
                if other.defined:
                    self.value -= other.value * (
                        SECONDS_IN_GRANULE[other.granularity]
                        // SECONDS_IN_GRANULE[self.granularity]
                    )
            elif isinstance(other, timedelta):
                s = other.total_seconds()
                self.value -= int(
                    abs(s)
                    // SECONDS_IN_GRANULE[self.granularity]
                    * (-1 if s < 0 else 1)
                )
            elif isinstance(other, TimeSpan):
                vals = [
                    v1 - v2
                    for v1, v2 in zip(
                        cast(list[int], self.values), cast(list[int], other.values)
                    )
                ]
                self.set(vals)
            elif isinstance(other, str):
                for m in re.finditer(r"([+-]?\d+)([YMDH])", other):
                    count = int(m.group(1))
                    if m.group(2) == "Y":
                        self.increment(-count, Interval.MINUTES["1Year"])
                    elif m.group(2) == "M":
                        self.increment(-count, Interval.MINUTES["1Month"])
                    elif m.group(2) == "D":
                        self.increment(-count, Interval.MINUTES["1Day"])
                    elif m.group(2) == "H":
                        self.increment(-count, Interval.MINUTES["1Hour"])
            else:
                raise HecTimeException(
                    f"Cannot add {other.__class__.__name__} to HecTime object"
                )
        return self

    def __add__(self, other: object) -> "HecTime":
        newTime = HecTime(self)
        if newTime.defined:
            if isinstance(other, int):
                newTime.value += other
            elif isinstance(other, HecTime):
                if other.defined:
                    newTime.value += other.value * (
                        SECONDS_IN_GRANULE[other.granularity]
                        // SECONDS_IN_GRANULE[newTime.granularity]
                    )
            elif isinstance(other, TimeSpan):
                vals = [
                    v1 + v2
                    for v1, v2 in zip(
                        cast(list[int], newTime.values), cast(list[int], other.values)
                    )
                ]
                newTime.set(vals)
            elif isinstance(other, timedelta):
                s = other.total_seconds()
                newTime.value += int(
                    abs(s)
                    // SECONDS_IN_GRANULE[newTime.granularity]
                    * (-1 if s < 0 else 1)
                )
            elif isinstance(other, str):
                for m in re.finditer(r"([+-]?\d+)([YMDH])", other):
                    count = int(m.group(1))
                    if m.group(2) == "Y":
                        newTime.increment(count, Interval.MINUTES["1Year"])
                    elif m.group(2) == "M":
                        newTime.increment(count, Interval.MINUTES["1Month"])
                    elif m.group(2) == "D":
                        newTime.increment(count, Interval.MINUTES["1Day"])
                    elif m.group(2) == "H":
                        newTime.increment(count, Interval.MINUTES["1Hour"])
            else:
                return NotImplemented
            values = cast(list[int], newTime.values)
            if newTime.granularity > SECOND_GRANULARITY:
                values[S] = 0
            if newTime.granularity > MINUTE_GRANULARITY:
                values[N] = 0
            newTime.set(values)
        return newTime

    def __sub__(self, other: object) -> Optional[Union["HecTime", TimeSpan, timedelta]]:
        if not self.defined:
            return None
        return_obj: Union[HecTime, TimeSpan, timedelta]
        if isinstance(other, (int, str, timedelta)):
            return_obj = HecTime(self)
            if not return_obj.defined:
                return None
            if isinstance(other, int):
                return_obj.value -= other
            elif isinstance(other, TimeSpan):
                vals = [v1 - v2 for v1, v2 in zip(self.values, other.values)]
                return_obj.set(vals)
            elif isinstance(other, timedelta):
                s = other.total_seconds()
                return_obj.value -= int(
                    abs(s)
                    // SECONDS_IN_GRANULE[return_obj.granularity]
                    * (-1 if s < 0 else 1)
                )
            elif isinstance(other, str):
                for m in re.finditer(r"([+-]?\d+)([YMDH])", other):
                    count = int(m.group(1))
                    if m.group(2) == "Y":
                        return_obj.increment(-count, Interval.MINUTES["1Year"])
                    elif m.group(2) == "M":
                        return_obj.increment(-count, Interval.MINUTES["1Month"])
                    elif m.group(2) == "D":
                        return_obj.increment(-count, Interval.MINUTES["1Day"])
                    elif m.group(2) == "H":
                        return_obj.increment(-count, Interval.MINUTES["1Hour"])
            return return_obj
        elif isinstance(other, HecTime):
            vals = [
                v1 - v2
                for v1, v2 in zip(
                    cast(list[int], self.values), cast(list[int], other.values)
                )
            ]
            return_obj = TimeSpan(vals)
        elif isinstance(other, datetime):
            return_obj = cast(datetime, self.datetime()) - other
        else:
            return NotImplemented
        return return_obj

    def __rsub__(self, other: datetime) -> timedelta:
        if not self.defined:
            return timedelta(seconds=0)
        return timedelta(seconds=-cast(timedelta, (self - other)).total_seconds())

    def __repr__(self) -> str:
        if self.granularity == SECOND_GRANULARITY:
            granularityStr = "SECOND_GRANULARITY"
        elif self.granularity == MINUTE_GRANULARITY:
            granularityStr = "MINUTE_GRANULARITY"
        elif self.granularity == HOUR_GRANULARITY:
            granularityStr = "HOUR_GRANULARITY"
        else:
            granularityStr = "DAY_GRANULARITY"
        if self.__tz:
            tzStr = f'.atTimeZone("{str(self.__tz)}")'
        else:
            tzStr = ""
        if not self.defined:
            return f"HecTime(UNDEFINED_TIME, {granularityStr}){tzStr}"
        else:
            return f"HecTime({self.values}, {granularityStr}){tzStr}"

    def __str__(self) -> str:
        return self.getISO8601DateTime()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HecTime):
            vals1 = (
                self.astimezone("UTC").values if self.__tz is not None else self.values
            )
            vals2 = (
                other.astimezone("UTC").values
                if other.__tz is not None
                else other.values
            )
            return vals1 == vals2
        elif isinstance(other, datetime):
            if other.tzinfo is not None:
                return self.astimezone(other).datetime() == other
            return self.datetime() == other
        else:
            return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, HecTime):
            if not self.defined:
                return False if not other.defined else True
            return (
                False
                if not other.defined
                else cast(list[int], self.values) < cast(list[int], other.values)
            )
        elif isinstance(other, datetime):
            if not self.defined:
                return True
            if other.tzinfo is not None:
                return cast(datetime, self.astimezone(other).datetime()) < other
            return cast(datetime, self.datetime()) < other
        else:
            return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, HecTime):
            if not self.defined:
                return False
            return (
                True
                if not other.defined
                else cast(list[int], self.values) > cast(list[int], other.values)
            )
        elif isinstance(other, datetime):
            if not self.defined:
                return False
            if other.tzinfo is not None:
                return cast(datetime, self.astimezone(other).datetime()) > other
            return cast(datetime, self.datetime()) > other
        else:
            return NotImplemented

    @property
    def year(self) -> Optional[int]:
        """
        The object's year, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[Y]

    @property
    def month(self) -> Optional[int]:
        """
        The object's month, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[M]

    @property
    def day(self) -> Optional[int]:
        """
        The object's day of month, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[D]

    @property
    def hour(self) -> Optional[int]:
        """
        The object's hour of day, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[H]

    @property
    def minute(self) -> Optional[int]:
        """
        The object's minute of hour, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[N]

    @property
    def second(self) -> Optional[int]:
        """
        The object's second of minute, or None if undefined

        Operations:
            Read Only
        """
        if not self.defined:
            return None
        return cast(list[int], self.values)[S]

    @property
    def tzinfo(self) -> Optional[ZoneInfo]:
        """
        The object's attached time zone

        Operations:
            Read Only
        """
        return self.__tz

    @property
    def granularity(self) -> int:
        """
        The object's current granularity.

        Operations:
            Read/Write

        Returns:
            int: The granularity
        """
        return self.__granularity

    @granularity.setter
    def granularity(self, value: int) -> None:
        values = self.values
        if SECOND_INCREMENT <= value <= DAY_INCREMENT:
            # change INCREMENT to GRANULARITY
            value += 10
        if not isValidGranularity(value):
            raise HecTimeException(f"Invalid time granularity: {value}")
        self.__granularity = value
        if values:
            try:
                self.set(values)
            except:
                self.__value = UNDEFINED_TIME
                self.__values = None
        if self.__granularity == DAY_GRANULARITY:
            self.__tz = None

    @property
    def defined(self) -> bool:
        """
        Whether this object has been defined

        Operations:
            Read Only
        """
        return self.value != UNDEFINED_TIME

    @property
    def value(self) -> int:
        """
        The object's current time integer.


        Operations:
            Read/Write
        """
        if self.__value is None:
            self.__value = getTimeInt(
                cast(list[int], self.__values), self.__granularity
            )
        return self.__value

    @value.setter
    def value(self, value: int) -> None:
        if (
            cast(int, EXTENTS[self.granularity][DATE_INTEGER][MIN_EXTENT])
            <= value
            <= cast(int, EXTENTS[self.granularity][DATE_INTEGER][MAX_EXTENT])
        ):
            self.__value = value
            self.__values = None
        else:
            self.__value = UNDEFINED_TIME
            self.__values = None

    @property
    def values(self) -> Optional[list[int]]:
        """
        The object's current time values (`[year, month, day, hour, minute, second]`).

        This property is None when the [`value`](#value) property is [`UNDEFINED_TIME`](#UNDEFINED_TIME)


        Operations:
            Read/Write
        """
        if self.__values is None:
            if not self.defined:
                return None
            self.__values = getTimeVals(cast(int, self.__value), self.__granularity)
            if self.__values[:3] == [4, 12, 31]:
                self.__values[D] = 30
        return to2400(self.__values) if self.__midnight_as_2400 else self.__values[:]

    @values.setter
    def values(self, values: Union[tuple[int, ...], list[int]]) -> None:
        values = list(values)
        normalizeTimeVals(values)
        if self.granularity > SECOND_GRANULARITY:
            values[S] = 0
        if self.granularity > MINUTE_GRANULARITY:
            values[N] = 0
        if self.granularity > HOUR_GRANULARITY:
            values[H] = 0
        if isValidTime(values, self.granularity):
            self.__values = values
            self.__value = None
            if self.granularity == DAY_GRANULARITY and any(values[3:]):
                self.value += 1
        else:
            self.__value = UNDEFINED_TIME
            self.__values = None

    @property
    def midnight_as_2400(self) -> bool:
        """
        The object's current setting of whether to show midnight as hour 24 (default) or not.


        Operations:
            Read/Write
        """
        return self.__midnight_as_2400

    @midnight_as_2400.setter
    def midnight_as_2400(self, state: bool) -> None:
        self.__midnight_as_2400 = state

    @property
    def default_date_style(self) -> int:
        """
        The object's current default data style.


        Operations:
            Read/Write
        """
        return self.__default_date_style

    @default_date_style.setter
    def default_date_style(self, style: int) -> None:
        self.__default_date_style = style

    @property
    def date_str(self) -> str:
        """
        The object's current date string using the default_date_style


        Operations:
            Read Only
        """
        return self.date()

    @property
    def date_time_str(self) -> str:
        """
        The object's current date and time string using the default_date_style


        Operations:
            Read
        """
        return self.dateAndTime()

    def add(self, time: Union[int, "HecTime"]) -> "HecTime":
        """
        Adds an number of granules or an HecTime to this object

        Args:
            time (Union[int, HecTime]): the to add. If an integer:
        - SECOND_GRANULARITY - adds the specified number of seconds
        - MINUTE_GRANULARITY - adds the specified number of minutes
        - HOUR_GRANULARITY - adds the specified number of hours
        - DAY_GRANULARITY - adds the specified number of days

        Deprecated:
            Use the `+=` operator instead

        Returns:
            HecTime: The modified object
        """
        warnings.warn(
            "The add() method is deprecated. Please use the += operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self += time
        return self

    def addDays(self, days: int) -> "HecTime":
        """
        Adds a number of days to the object

        Args:
            days (int): the number of days to add.

        Returns:
            HecTime: The modified object
        """
        self += timedelta(days=days)
        return self

    def addHours(self, hours: int) -> "HecTime":
        """
        Adds a number of hours to the object

        Args:
            hours (int): the number of hours to add.

        Returns:
            HecTime: The modified object
        """
        self += timedelta(hours=hours)
        return self

    def addMinutes(self, minutes: int) -> "HecTime":
        """
        Adds a number of minutes to the object

        Args:
            minutes (int): the number of minutes to add.

        Returns:
            HecTime: The modified object
        """
        self += timedelta(minutes=minutes)
        return self

    def addSeconds(self, seconds: int) -> "HecTime":
        """
        Adds a number of seconds to the object

        Args:
            seconds (int): the number of seconds to add.

        Returns:
            HecTime: The modified object
        """
        self += timedelta(seconds=seconds)
        return self

    def adjustToIntervalOffset(
        self, interval: Union[Interval, int], offsetMinutes: int
    ) -> "HecTime":
        """
        Adjusts this object to be at the specified offset past the specified interval.

        **NOTE:** Unlike [`zofset`](#zofset) The resulting time may be *at*, *before*, or *after*
        the this object, but will always be in the interval that begins at or before this object.

        To get the begninning of the interval that starts at or before this object, set
        offsetMinutes to 0. To get the beginning of the next interval set offsetMinutes
        be the same as intervalMinutes.

        Args:
            interval (Union[Interval, int]): The interval. If an integer, must be the actual
                or charactersitic minutes of a standard Interval
            offsetMinutes (int): The offset into the interval in minutes (0..interval)

        Returns:
            The adjusted object

        Raises:
            HecTimeException: if offset it out of range for interval
        """
        values = self.values
        if values is not None:
            if isinstance(interval, Interval):
                intervalMinutes = interval.minutes
            else:
                intervalMinutes = interval
            if not 0 <= offsetMinutes <= intervalMinutes:
                raise HecTimeException("Offset must be in range 0..interval")
            # ------------------------------------------ #
            # first back up to the start of the interval #
            # ------------------------------------------ #
            if intervalMinutes == Interval.MINUTES["1Year"]:
                values[M] = 1
                values[D] = 1
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["1Month"]:
                values[D] = 1
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["Semi-Month"]:
                values[D] = 15 if values[D] > 15 else 1
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["Tri-Month"]:
                values[D] = 20 if values[D] > 20 else 10 if values[D] > 10 else 1
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["1Week"]:
                values[D] -= (idaywk(values[:3]) - 1) % 7
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["6Days"]:
                values[D] -= yearMonthDayToJulian(values[Y], values[M], values[D]) % 6
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["5Days"]:
                values[D] -= yearMonthDayToJulian(values[Y], values[M], values[D]) % 5
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["4Days"]:
                values[D] -= yearMonthDayToJulian(values[Y], values[M], values[D]) % 4
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["3Days"]:
                values[D] -= yearMonthDayToJulian(values[Y], values[M], values[D]) % 3
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["2Days"]:
                values[D] -= yearMonthDayToJulian(values[Y], values[M], values[D]) % 2
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["1Day"]:
                values[H] = 0
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["12Hours"]:
                values[H] -= values[H] % 12
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["8Hours"]:
                values[H] -= values[H] % 8
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["6Hours"]:
                values[H] -= values[H] % 6
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["4Hours"]:
                values[H] -= values[H] % 4
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["3Hours"]:
                values[H] -= values[H] % 3
                values[N] = 0
            elif intervalMinutes == Interval.MINUTES["2Hours"]:
                values[H] -= values[H] % 2
                values[N] = 0
            else:
                values[N] -= values[N] % intervalMinutes
            # --------------------- #
            # now add in the offset #
            # --------------------- #
            values[M] += offsetMinutes // Interval.MINUTES["1Month"]
            values[N] += offsetMinutes % Interval.MINUTES["1Month"]
            values[S] = 0
            normalizeTimeVals(values)
            self.values = values
        return self

    def atTimeZone(
        self,
        timeZone: Union["HecTime", datetime, ZoneInfo, str, None],
        onAlreadytSet: int = 1,
    ) -> "HecTime":
        """
        Attaches the specified time zone to this object. Does not change the time

        Args:
            timeZone (Union[ZoneInfo, str]): The time zone to attach or object containing that time zone.
                Use `"local"` to specify the system time zone.
            onAlreadytSet (int, optional): Specifies action to take if a different time zone is already
                attached. Defaults to 1.
                - `0`: Quietly attach the new time zone
                - `1`: (default) Issue a warning about attaching a different time zone
                - `2`: Raises an exception
        Raises:
            HecTimeException: if a different time zone is already attached and `onAlreadySet` == 2

        Returns:
            HecTime: The updated object
        """
        if isinstance(timeZone, HecTime):
            tz = timeZone.__tz
        elif isinstance(timeZone, datetime):
            tz = timeZone.tzinfo
        elif isinstance(timeZone, (ZoneInfo, type(None))):
            tz = timeZone
        else:
            tz = (
                tzlocal.get_localzone()
                if timeZone.lower() == "local"
                else ZoneInfo(timeZone)
            )
        if self.__tz:
            if tz == self.__tz:
                return self
            if tz is not None:
                if onAlreadytSet > 0:
                    message = f"{self} already has a time zone set to {self.__tz} when setting to {tz}"
                    if onAlreadytSet > 1:
                        raise HecTimeException(message)
                    else:
                        warnings.warn(
                            message + ". Use onAlreadySet=0 to prevent this message.",
                            UserWarning,
                        )
        if self.__granularity != DAY_GRANULARITY:
            self.__tz = tz
        return self

    def astimezone(
        self, timeZone: Union["HecTime", datetime, ZoneInfo, str], onTzNotSet: int = 1
    ) -> "HecTime":
        """
        Returns a copy of this object at the spcified time zone

        Args:
            timeZone (Union[HecTime, datetime, ZoneInfo, str]): The target time zone or object containg the target time zone.
                Use `"local"` to specify the system time zone.
            onTzNotSet (int, optional): Specifies behavior if this object has no time zone attached. Defaults to 1.
                - `0`: Quietly behave as if this object had the local time zone attached.
                - `1`: (default) Same as `0`, but issue a warning.
                - `2`: Raise an exception preventing objectes with out time zones attached from using this method.

        Returns:
            HecTime: A copy of this object at the specified time zone
        """
        if isinstance(timeZone, HecTime):
            tz = timeZone.__tz
        elif isinstance(timeZone, datetime):
            tz = timeZone.tzinfo
        elif isinstance(timeZone, ZoneInfo):
            tz = timeZone
        else:
            tz = (
                tzlocal.get_localzone()
                if timeZone.lower() == "local"
                else ZoneInfo(timeZone)
            )

        t = HecTime(self)
        if t.granularity != DAY_GRANULARITY:
            if not self.__tz:
                if onTzNotSet > 0:
                    if onTzNotSet > 1:
                        raise HecTimeException(
                            f"Cannot convert {repr(self)} to time zone {str(tz)}: No time zone attached."
                        )
                    localname = tzlocal.get_localzone_name()
                    warnings.warn(
                        f"Treating {repr(self)}\nas if it had local time zone ({localname}) attached in order to convert "
                        f"to time zone {str(tz)}.\nUse onTzNotSet=0 to prevent this warning."
                    )
            if t.defined:
                t.set(cast(datetime, self.datetime()).astimezone(tz))
            else:
                t.__tz = tz
        return t

    @NoOpWarning
    def cleanTime(self) -> None:
        """Placeholder for API compatibility. Does nothing."""
        pass

    def clone(self) -> object:
        """
        Returns a clone of this object

        Returns:
            object: the clone of this object
        """
        return HecTime(self)

    def compareTimes(self, other: "HecTime") -> int:
        """
        Returns an integer comparison with another HecTime object

        Args:
            other (HecTime): The other HecTime object

        Returns:
            int:
            - -1 if this object < other
            - 0 if this object == other
            - 1 if this object > other
        """
        return -1 if self < other else 1 if self > other else 0

    @NotImplementedWarning
    def compareTo(self, other: object) -> int:
        """Not supported in this implementation"""
        return NotImplemented

    def computeNumberIntervals(
        self, other: "HecTime", interval: Union[int, timedelta, Interval]
    ) -> int:
        """
        Returns the number of complete intervals between this object and another specified HecTime object

        Args:
            other (HecTime): The other time to compute the number of intervals to
            interval (Union[int, timedelta]): The interval size to compute the number of intervals for.
        - `int` - the minutes in a standard interval
        - `timedelta` - If equivalent to a standard interval, the same result as specifying the equivalent integer
            is returned. Otherwise the both HecTime objects are converted to datetime objects and the number of
            intervals is computed as `((other.datetime - self.datetime) / timesdelta')

        Raises:
            HecTimeException: if `interval` is a non-standard integer or if it is a nonstandard timedelta and
                either of this object or `other` is not convertable to a datetime object

        Returns:
            int: The number of complete intervals between this time and the other time.
        """
        if not self.defined or not other.defined:
            return UNDEFINED_TIME
        if isinstance(interval, int):
            minutes = interval
        elif isinstance(interval, timedelta):
            minutes = int(interval.total_seconds() / 60)
            if not minutes in Interval.MINUTES.values():
                return int(
                    (cast(datetime, other.datetime()) - cast(datetime, self.datetime()))
                    / interval
                )
        elif isinstance(interval, Interval):
            minutes = interval.minutes
        else:
            raise TypeError(
                f"Unsupported type for method computeNumberIntervals: {interval.__class__.__name__}"
            )
        if minutes not in Interval.MINUTES.values():
            raise HecTimeException(f"{minutes} minutes is not a standard intvl.")
        jul1 = cast(int, self.julian())
        min1 = cast(int, self.minutesSinceMidnight())
        jul2 = cast(int, other.julian())
        min2 = cast(int, other.minutesSinceMidnight())
        diff = jul2 * 1440 + min2 - jul1 * 1440 - min1
        count = int(diff / minutes)
        temp = HecTime(self).increment(count, minutes)
        if abs(count) > 3:
            while True:
                jul1 = cast(int, temp.julian())
                min1 = cast(int, temp.minutesSinceMidnight())
                diff = jul2 * 1440 + min2 - jul1 * 1440 - min1
                count2 = int(diff / minutes)
                if abs(count2) <= 1:
                    break
                count += count2
                temp = HecTime(self).increment(count, minutes)
        # adjust as necessary
        while temp > other:
            count -= 1
            temp = HecTime(self).increment(count, minutes)
        while temp <= other:
            count += 1
            temp = HecTime(self).increment(count, minutes)
        count -= 1
        if isinstance(interval, int) and interval in (
            Interval.MINUTES["Tri-Month"],
            Interval.MINUTES["Semi-Month"],
            Interval.MINUTES["1Month"],
            Interval.MINUTES["1Year"],
        ):
            # ------------------------------------------------- #
            # additional verification for month-based intervals #
            # ------------------------------------------------- #
            temp.set(self)
            temp.increment(count, interval)
            if temp > other:
                count -= 1
            temp.set(self)
            temp.increment(count + 1, interval)
            if not temp > other:
                count += 1
        return count

    def convertTimeZone(
        self,
        fromTimeZone: Union["ZoneInfo", str],
        toTimeZone: Union["ZoneInfo", str],
        respectDaylighSaving: Optional[bool] = True,
    ) -> "HecTime":
        """
        Converts this object from one time zone to another, optionally specifyintg that the
        target time zone does not observe Daylight Saving Time (DST). Only for HecTime objects
        convertable to datetime objects (between 01Jan0001, 00:00 and 31Dec9999, 23:59).

        **NOTE:** The Java signatures for this method that operate on and return a copy of the HecTime
        object are not supported in this implementation. The `astimezone()` method can be used for that purpose.

        Args:
            fromTimeZone (Union[ZoneInfo, str]): The time zone to convert from
            toTimeZone (Union[ZoneInfo, str]): The target time zone
            respectDaylighSaving (Optional[bool], optional): Specifies whether the target time zone.
                should observe DST. Defaults to True.
                - If `True`, the target time zone is used as specified
                - If `False` and the specified target time zone observes DST, then a time zone is
                found that has the same UTC offset as the specified target time zone but does not
                observe DST.

        Returns:
            HecTime: The modified object

        Raises:
            HecTimeException:
                - If `respectDaylightSaving` is `True`, `toTimeZone` observes DST and no equivalent
                time zone could be found that does not observer DST
                - If this object is not convertable to a datetime object
        """
        fromTz = (
            fromTimeZone
            if isinstance(fromTimeZone, ZoneInfo)
            else ZoneInfo(fromTimeZone)
        )
        if self.tzinfo and self.tzinfo != fromTz:
            raise HecTimeException(
                f"Cannot specify fromTimeZone as {str(fromTz)} when the attached time zone is {str(self.tzinfo)}"
            )
        toTz = toTimeZone if isinstance(toTimeZone, ZoneInfo) else ZoneInfo(toTimeZone)
        targetTz = toTz
        if not respectDaylighSaving:
            t = datetime.now().astimezone(targetTz)
            if t.dst():
                for tz in [
                    tz for tz in zoneinfo.available_timezones() if tz.startswith("Etc")
                ]:
                    t2 = t.astimezone(ZoneInfo(tz))
                    if t2.utcoffset() == t.utcoffset() and not t2.dst():
                        targetTz = ZoneInfo(tz)
                        break
            else:
                raise HecTimeException(
                    f"No time zone found with same offset as {targetTz} that does not observe Daylight Saving Time"
                )
        if self.defined:
            self.set(
                cast(datetime, self.datetime())
                .replace(tzinfo=fromTz)
                .astimezone(targetTz)
            )
        return self

    def date(self, style: Optional[int] = None) -> str:
        """
        Returns the date in the specified style

        <table style='font-family:monospace;'>
        <tr><th colspan="4">Base date styles</th></tr>
        <tr><td><b>0:</b>&nbsp;June&nbsp;2,&nbsp;1985</td><td><b>10:</b>&nbsp;&nbsp;June&nbsp;2,&nbsp;85</td><td><b>100:</b>&nbsp;JUNE&nbsp;2,&nbsp;1985</td><td><b>110:</b>&nbsp;JUNE&nbsp;2,&nbsp;85</td></tr>
        <tr><td><b>1:</b>&nbsp;&nbsp;Jun&nbsp;2,&nbsp;1985</td><td><b>11:</b>&nbsp;&nbsp;&nbsp;Jun&nbsp;2,&nbsp;85</td><td><b>101:</b>&nbsp;&nbsp;JUN&nbsp;2,&nbsp;1985</td><td><b>111:</b>&nbsp;&nbsp;JUN&nbsp;2,&nbsp;85</td></tr>
        <tr><td><b>2:</b>&nbsp;&nbsp;2&nbsp;June&nbsp;1985</td><td><b>12:</b>&nbsp;&nbsp;&nbsp;2&nbsp;June&nbsp;85</td><td><b>102:</b>&nbsp;&nbsp;2&nbsp;JUNE&nbsp;1985</td><td><b>112:</b>&nbsp;&nbsp;&nbsp;2&nbsp;JUN&nbsp;85</td></tr>
        <tr><td><b>3:</b>&nbsp;&nbsp;&nbsp;&nbsp;June&nbsp;1985</td><td><b>13:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;June&nbsp;85</td><td><b>103:</b>&nbsp;&nbsp;&nbsp;&nbsp;JUNE&nbsp;1985</td><td><b>113:</b>&nbsp;&nbsp;&nbsp;&nbsp;JUNE&nbsp;85</td></tr>
        <tr><td><b>4:</b>&nbsp;&nbsp;&nbsp;&nbsp;02Jun1985</td><td><b>14:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;02Jun85</td><td><b>104:</b>&nbsp;&nbsp;&nbsp;&nbsp;02JUN1985</td><td><b>114:</b>&nbsp;&nbsp;&nbsp;&nbsp;02JUN85</td></tr>
        <tr><td><b>5:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2Jun1985</td><td><b>15:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2Jun85</td><td><b>105:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2JUN1985</td><td><b>115:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2JUN85</td></tr>
        <tr><td><b>6:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Jun1985</td><td><b>16:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Jun85</td><td><b>106:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JUN1985</td><td><b>116:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JUN85</td></tr>
        <tr><td><b>7:</b>&nbsp;&nbsp;02&nbsp;Jun&nbsp;1985</td><td><b>17:</b>&nbsp;&nbsp;&nbsp;02&nbsp;Jun&nbsp;85</td><td><b>107:</b>&nbsp;&nbsp;02&nbsp;JUN&nbsp;1985</td><td><b>117:</b>&nbsp;&nbsp;02&nbsp;JUN&nbsp;85</td></tr>
        <tr><td><b>8:</b>&nbsp;&nbsp;&nbsp;2&nbsp;Jun&nbsp;1985</td><td><b>18:</b>&nbsp;&nbsp;&nbsp;&nbsp;2&nbsp;Jun&nbsp;85</td><td><b>108:</b>&nbsp;&nbsp;&nbsp;2&nbsp;JUN&nbsp;1985</td><td><b>118:</b>&nbsp;&nbsp;&nbsp;2&nbsp;JUN&nbsp;85</td></tr>
        <tr><td><b>9:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Jun&nbsp;1985</td><td><b>19:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Jun&nbsp;85</td><td><b>109:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JUN&nbsp;1985</td><td><b>119:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;JUN&nbsp;85</td></tr>
        <tr><th colspan="4">Extended date styles</th></tr>
        <tr><td><b>-1:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6/2/85</td><td><b>-11:</b>&nbsp;&nbsp;&nbsp;&nbsp;06/02/85</td><td><b>-101:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6/2/1985</td><td><b>-111:</b>&nbsp;06/02/1985</td></tr>
        <tr><td><b>-2:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6-2-85</td><td><b>-12:</b>&nbsp;&nbsp;&nbsp;&nbsp;06-02-85</td><td><b>-102:</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6-2-1985</td><td><b>-112:</b>&nbsp;06-02-1985</td></tr>
        <tr><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td><b>-13:</b>&nbsp;&nbsp;1985-06-02</td><td></td><td></td></tr>
        </table>

        **NOTE** that years that overflow four digits will not be truncated if using a style that shows four digits in the table (styles 0..9, 100..109, -113..-101 and -13).
        Other formats will continue to show only the last two digits of the year. In all cases a negative sign will be prepended to the year for negative years (whether two digits or more are shown).
        lib.dateAndTime)

        Args:
            style (Optional[int]): The date style to use. If not specified the [`default_date_style`](#HecTime.default_date_style) property is used

        Returns:
            str: The formatted date
        """

        if not self.defined or style == -1000:
            return ""
        dateStr = ""
        if style is None:
            style = self.__default_date_style
        style = normalizeDateStyle(style)
        y, m, d = cast(list[int], self.values)[:3]
        year: str
        mon: str
        day: str
        if style == -13:
            dateStr = f"{y:0{5 if y < 0 else 4}}-{m:02d}-{d:02d}"
        elif style < 0:
            if style in (-101, -102, -111, -112):
                year = f"{y:0{5 if y < 0 else 4}}"
            else:
                y2 = int(math.fmod(y, 100))
                year = f"{y2:0{3 if y2 < 0 else 2}}"
            if style in (-11, -12, -111, -112):
                mon = f"{m:02d}"
                day = f"{d:02d}"
            else:
                mon = str(m)
                day = str(d)
            if style in (-1, -11, -101, -111):
                dateStr = f"{mon}/{day}/{year}"
            else:
                dateStr = f"{mon}-{day}-{year}"
        else:
            if style % 100 < 10:
                year = f"{y:0{5 if y < 0 else 4}}"
            else:
                y2 = int(math.fmod(y, 100))
                year = f"{y2:0{3 if y2 < 0 else 2}}"
            mon = MONTH_NAMES[m]
            if style % 10 not in (0, 2, 3):
                mon = mon[:3]
            if style >= 100:
                mon = mon.upper()
            if style % 10 in (3, 6, 9):
                day = ""
            elif style % 10 in (4, 7):
                day = f"{d:02d}"
            else:
                day = str(d)
            if style % 10 in (0, 1):
                dateStr = f"{mon} {day}, {year}"
            elif style % 10 in (2, 3, 7, 8, 9):
                dateStr = f"{day} {mon} {year}".strip()
            else:
                dateStr = f"{day}{mon}{year}"

        return dateStr

    def dateAndTime(self, style: Optional[int] = None) -> str:
        """
        Returns a string representing the date and time in the specified style.

        Args:
            style (Optional[int]): The date style to use. If not specified the [`default_date_style`](#HecTime.default_date_style) property is used

        Returns:
            str: The formatted date and time. The date is generated using the style parameter (see [`date`](#HecTime.date)), which is separated from
            the time portion (with colons) (see [`time`](#HecTime.time)) by a comma and space
        """
        dateTimeStr = ""
        if self.defined:
            dateTimeStr += self.date(style)
        if self.__granularity < DAY_GRANULARITY:
            timeStr = self.time()
            if self.__granularity > SECOND_GRANULARITY:
                timeStr = timeStr[:5]
            dateTimeStr += f", {timeStr}" if dateTimeStr else timeStr
        return dateTimeStr

    def datetime(self) -> Optional[datetime]:
        """
        Returns a `datetime` object equivalent to this object.

        Returns:
            datetime: The equivalent `datetime` object or `None` if this object's time is undefined
        """
        if not self.defined:
            return None
        else:
            values = cast(list[int], self.values)
            if not [1, 1, 1, 0, 0, 0] < values < [9999, 12, 31, 23, 59, 50]:
                raise HecTimeException(
                    f"Time values {self.values} are not in datetime range"
                )
            y, m, d, h, n, s = to0000(values)
            if self.__tz:
                dt = datetime(y, m, d, h, n, s, tzinfo=self.__tz)
            else:
                dt = datetime(y, m, d, h, n, s)
            return dt

    def dayOfWeek(self) -> Optional[int]:
        """
        Returns the day of week (1 = Sunday -> 7 = Saturday) for this object.

        **NOTE:** This differs from `datetime.weekday()` whch returns 0=Monday -> 6=Sunday.

        Returns:
            int: The day of week (1 = Sunday -> 7 = Saturday)
        """
        return None if not self.defined else idaywk(cast(int, self.julian()))

    def dayOfWeekName(self) -> Optional[str]:
        return (
            None
            if not self.defined
            else (
                "***ERROR***",
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            )[cast(int, self.dayOfWeek())]
        )

    def dayOfYear(self) -> Optional[int]:
        """
        Returns the day of the year of this object (01Jan = 1)

        Returns:
            Optional[int]: The day of the year
        """
        tv = self.values
        return (
            None
            if tv is None
            else (
                yearMonthDayToJulian(tv[Y], tv[M], tv[D])
                - yearMonthDayToJulian(tv[Y], 1, 1)
                + 1
            )
        )

    def equalTo(self, other: "HecTime") -> bool:
        """
        Returns whether this object is equivalent to another

        Args:
            other (Union[&quot;HecTime&quot;, datetime]): The object to compare to

        Deprrecated:
            Use `==` operator instead

        Returns:
            bool: The result of the comparison
        """
        warnings.warn(
            "The equalTo() method is deprecated. Please use the == operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return other == self

    def getDefaultDateStyle(self) -> int:
        """
        Returns the default date style

        Deprecated:
            Use [**default_date_style**](#HecTime.default_date_style) property instead

        Returns
            int: The default date style
        """
        warnings.warn(
            "The getDefaultDateStyle() method is deprecated. Please use the default_date_style property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.__default_date_style

    def getIntervalOffset(self, interval: int) -> Optional[int]:
        """
        Returns the number of minutes that the current object is after the top of the most recent standard interval

        Args:
            interval (int): The interval to determine the offset into

        Raises:
            HecTimeException: if the interval is not a standard interval

        Returns:
            Optional[int]: The number of minutes into the interval
        """
        tv = self.values
        if tv is None:
            return None
        julian = cast(int, self.julian())
        minutes = cast(int, self.minutesSinceMidnight())
        if interval == Interval.MINUTES["1Minute"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N], 0]
        elif interval == Interval.MINUTES["2Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 2, 0]
        elif interval == Interval.MINUTES["3Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 3, 0]
        elif interval == Interval.MINUTES["4Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 4, 0]
        elif interval == Interval.MINUTES["5Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 5, 0]
        elif interval == Interval.MINUTES["6Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 6, 0]
        elif interval == Interval.MINUTES["10Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 10, 0]
        elif interval == Interval.MINUTES["12Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 12, 0]
        elif interval == Interval.MINUTES["15Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 15, 0]
        elif interval == Interval.MINUTES["20Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 20, 0]
        elif interval == Interval.MINUTES["30Minutes"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], tv[N] - tv[N] % 30, 0]
        elif interval == Interval.MINUTES["1Hour"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H], 0, 0]
        elif interval == Interval.MINUTES["2Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 2, 0, 0]
        elif interval == Interval.MINUTES["3Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 3, 0, 0]
        elif interval == Interval.MINUTES["4Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 4, 0, 0]
        elif interval == Interval.MINUTES["6Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 6, 0, 0]
        elif interval == Interval.MINUTES["8Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 8, 0, 0]
        elif interval == Interval.MINUTES["12Hours"]:
            topOfInterval = [tv[Y], tv[M], tv[D], tv[H] - tv[H] % 12, 0, 0]
        elif interval == Interval.MINUTES["1Day"]:
            topOfInterval = [tv[Y], tv[M], tv[D], 0, 0, 0]
        elif interval == Interval.MINUTES["2Days"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 2, 0, 0, 0]
        elif interval == Interval.MINUTES["3Days"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 3, 0, 0, 0]
        elif interval == Interval.MINUTES["4Days"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 4, 0, 0, 0]
        elif interval == Interval.MINUTES["5Days"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 5, 0, 0, 0]
        elif interval == Interval.MINUTES["6Days"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 6, 0, 0, 0]
        elif interval == Interval.MINUTES["1Week"]:
            topOfInterval = [tv[Y], tv[M], tv[D] - julian % 7, 0, 0, 0]
        elif interval == Interval.MINUTES["Tri-Month"]:
            topOfInterval = [
                tv[Y],
                tv[M],
                1 if tv[D] < 11 else 11 if tv[D] < 21 else 21,
                0,
                0,
                0,
            ]
        elif interval == Interval.MINUTES["Semi-Month"]:
            topOfInterval = [tv[Y], tv[M], 1 if tv[D] < 15 else 16, 0, 0, 0]
        elif interval == Interval.MINUTES["1Month"]:
            topOfInterval = [tv[Y], tv[M], 1, 0, 0, 0]
        elif interval == Interval.MINUTES["1Year"]:
            topOfInterval = [tv[Y], 1, 1, 0, 0, 0]
        else:
            raise HecTimeException(f"Interval {interval} is not a standard interval")
        topJulian = yearMonthDayToJulian(
            topOfInterval[Y], topOfInterval[M], topOfInterval[D]
        )
        topMinutes = topOfInterval[H] * 60 + topOfInterval[N]
        return (julian - topJulian) * 1440 + minutes - topMinutes

    def getISO8601DateTime(self) -> str:
        """
        Returns the time of this object in ISO 8601 format.

        Returns:
            str: The time of this object in ISO 8601 format
        """
        timestr = ""
        if self.defined:
            timestr = self.date(-13)
            tv = cast(list[int], self.values)
            timestr += f"T{tv[H]:02d}:{tv[N]:02d}:{tv[S]:02d}"
            if self.__tz is not None:
                utc_offset = cast(datetime, self.datetime()).utcoffset()
                if utc_offset is None:
                    raise HecTimeException(
                        f"Could not determine UTC offset for time zone {self.__tz}"
                    )
                offsetMinutes = int(utc_offset.total_seconds() / 60)
                timestr += f"{int(offsetMinutes/60):+03d}:{offsetMinutes % 60:02d}"
        return timestr

    def getMinutes(
        self, timeZoneOffset: Optional[Union[int, "ZoneInfo"]] = None
    ) -> Optional[int]:
        """
        Returns the time of this object as (days since 1899) * 1400 + (minutes past midnight), optionally offsetting by a time zone

        Args:
            timeZoneOffset (Optional[Union[int, ZoneInfo]]): if `int`, the number of minutes *behind* UTC (positive for western longitudes)

        Returns:
            int: The time in minutes
        """
        if not self.defined:
            return None
        minutes = cast(int, self.julian()) * 1440 + cast(
            int, self.minutesSinceMidnight()
        )
        if timeZoneOffset:
            offsetMinutes = 0
            if isinstance(timeZoneOffset, int):
                offsetMinutes = -timeZoneOffset
            elif isinstance(timeZoneOffset, ZoneInfo):
                utc_offset = datetime.now(tz=timeZoneOffset).utcoffset()
                if utc_offset is None:
                    raise HecTimeException(
                        f"Could not retrieve UTC offset from time zone {timeZoneOffset}"
                    )
                offsetMinutes = int(utc_offset.total_seconds() / 60)
            else:
                raise HecTimeException(
                    f"Expected int or ZoneInfo for timeZoneOffset, got {timeZoneOffset.__class__.__name__}"
                )
            minutes += offsetMinutes
        return minutes

    def getShowsTimeAsBeginningOfDay(self) -> bool:
        """
        Retrieves whether midnight is shown as hour 0 instead of hour 24 of the previous day

        Deprecated:
            Use [**midnight_as_2400**](#HecTime.midnight_as_2400) property instead

        Returns:
            bool: `True` if midnight is shown as hour 0, `False` if midnight is shown as hour 24
        """
        warnings.warn(
            "The getShowsTimeAsBeginningOfDay() method is deprecated. Please use the midnight_as_2400 property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return not self.midnight_as_2400

    def getTime(self, withColons: Optional[bool] = True) -> str:
        """
        Returns a string representing the time portion

        - withColons = True (default), `[..., 6, 8, 23]` is retuned is `06:08:23`
        - withColons = False, `[..., 6, 8, 23]` is retuned is `0608`
        Args:
            withColons (Optional[bool], optional): Specifies with or without colons. Defaults to `True`.

        Deprecated:
            use [**time**](#HecTime.HecTime.time) method instead

        Returns:
            str: The time portion string with colons (hour, minute, and second), or without colons (hour, minute only))
        """
        warnings.warn(
            "The getTime() method is deprecated. Please use the time() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.time(withColons)

    def getTimeGranularity(self) -> int:
        """
        Returns the granularity of this object

        Deprecated:
            Use [**granularity**](#HecTime.granularity) property instead

        Returns:
            int: The granularity
        """
        warnings.warn(
            "The getTimeGranularity() method is deprecated. Please use the granularity property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.granularity

    def getTimeInMillis(
        self, timeZoneOffset: Optional[Union[int, "ZoneInfo"]] = None
    ) -> Optional[int]:
        """
        Returns the time of this object in milliseconds into of the Unix Epoch (01Jan1970 00:00:00 UTC).

        Note that is the standard time value used in Java as well as 1000.0 times the standard time
        value used in python (e.g., `time.time()` or `datetime.timestamp()`)

        Args:
            timeZoneOffset (Optional[Union[int, ZoneInfo]]): if `int`, the number of minutes *behind* UTC (positive for western longitudes).
                If not specified, the milliseconds returned will be as if this object is in UTC

        Returns:
            Optional[int]: None if this object is not defined., otherwise the milliseconds of the current time from the beginning of the Unix Epoch
        """
        if not self.defined:
            return None
        return (
            cast(int, self.getMinutes(timeZoneOffset))
            - cast(int, HecTime([1970, 1, 1, 0, 0, 0]).getMinutes(timeZoneOffset))
        ) * 60000

    def getXMLDateTime(self) -> str:
        """
        Returns the time of this object in ISO 8601 format.

        Deprecated:
            Use [**getISO8601DateTime**](#HecTime.getISO8601DateTime) instead

        Raises:
            HecTimeException: if timeZoneOffset is specifed but is not an integer or ZoneInfo object,
            or is a ZoneInfo object and no UTC offset could be determined from it

        Returns:
            str: The time of this object in ISO 8601 format
        """
        warnings.warn(
            "The getXMLDateTime() method is deprecated. Please use the getISODateTime() method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.getISO8601DateTime()

    def greaterThan(self, other: "HecTime") -> bool:
        """
        Returns whether this object is greater than (later than) another HecTime object

        Args:
            other (HecTime): The other object to compare to

        Deprecated:
            Use the the `>` operator instead.

        Returns:
            bool: Whether this object is greater than the other
        """
        warnings.warn(
            "The greaterThan() method is deprecated. Please use the > operatorinstead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self > other

    def greaterThanEqualTo(self, other: "HecTime") -> bool:
        """
        Returns whether this object is greater than (later than) or equal to (same time as) another HecTime object

        Args:
            other (HecTime): The other object to compare to

        Deprecated:
            Use the the `>=` operator instead.

        Returns:
            bool: Whether this object is greater than or equal to the other
        """
        warnings.warn(
            "The greaterThan() method is deprecated. Please use the >= operatorinstead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self >= other

    def hourMinutes(self) -> str:
        """
        Returns the time portion in HHMM format or "" if this object is undefined

        Returns:
            str: The time portion in HHMM format or "" if this object is undefined
        """
        if not self.defined:
            return ""
        tv = cast(list[int], self.values)
        return f"{tv[H]:02d}{tv[N]:02d}"

    def hoursMinutesSeconds(
        self, hours: list[int], minutes: list[int], seconds: list[int]
    ) -> None:
        """
        Returns the object's hour, minute, and second in the spefied parameters

        Args:
            hours (list[int]): Element 0 recieves the hour
            minutes (list[int]): Element 0 recieves the minute
            seconds (list[int]): Element 0 receives the second
        """
        if self.defined:
            hours[0], minutes[0], seconds[0] = cast(list[int], self.values)[3:]

    def increment(self, count: int, interval: Union[TimeSpan, int]) -> "HecTime":
        """
        Increments this object by a specified number of intervals.

        For month-based intervals (`"Tri-Month"`, `"Semi-Month"`, `"1Month"`, `"1Year"`), if the date
        of the current object is the last day of a month, the resulting date will be the last day of the month
        or sub-month (days 10 or 20 for `"Tri-Month"` and day 15 for `"Semi-Month"`), as shown:
        <table>
        <tr><th>Start Time</th><th>Count</th><th>Interval</th><th>Result</th></tr>
        <tr><td>28Feb2023, 01:00</td><td>1</td><td><code>"Tri-Month"</code></td><td>10Mar2023, 01:00</td></tr>
        <tr><td>28Feb2023, 01:00</td><td>2</td><td><code>"Tri-Month"</code></td><td>20Mar2023, 01:00</td></tr>
        <tr><td>28Feb2023, 01:00</td><td>3</td><td><code>"Tri-Month"</code></td><td>31Mar2023, 01:00</td></tr>
        <tr><td>28Feb2024, 01:00</td><td>1</td><td><code>"Tri-Month"</code></td><td>08Mar2023, 01:00</td></tr>
        <tr><td>28Feb2024, 01:00</td><td>2</td><td><code>"Tri-Month"</code></td><td>18Mar2023, 01:00</td></tr>
        <tr><td>28Feb2024, 01:00</td><td>3</td><td><code>"Tri-Month"</code></td><td>28Mar2023, 01:00</td></tr>
        </table>

        Note that this method produces results that differ from the Java HecTime.increment() method where
        the Java code produces incorrect results, as in the following examples (all such discrepancies are
        limited to `"Tri-Month"`, `"Semi-Month"`, and `"1Month"`:
        <table>
        <tr><th>Start Time</th><th>Count</th><th>Interval</th><th>Correct Result</th><th>Java HecTime Result</th></tr>
        <tr><td>29Jan2023, 01:00</td><td>1</td><td><code>"1Month"</code></td><td>28Feb2023, 01:00</td><td>01Mar2023, 01:00</td></tr>
        <tr><td>09Feb2024, 01:00</td><td>2</td><td><code>"Tri-Month"</code></td><td>29Feb2024, 01:00</td><td>09Mar2024, 01:00</td></tr>
        <tr><td>28Feb2024, 01:00</td><td>2</td><td><code>"Semi-Month"</code></td><td>28Mar2024, 01:00</td><td>31Mar2024, 01:00</td></tr>
        </table>

        Args:
            count (int): The number of intervals to increment
            interval (Union[TimeSpan, int]): The interval to increment by.

        Returns:
            HecTime: The incremented object
        """
        values = self.values
        if values is not None:
            values = to0000(values)
            if isinstance(interval, int):
                # --------------- #
                # integer minutes #
                # --------------- #
                minutes = interval
            elif isinstance(interval, Interval):
                # ---------------- #
                # Interval object  #
                # ---------------- #
                minutes = interval.minutes
            else:
                # ------------------------------------- #
                # TimeSpan object (likely non-standard) #
                # ------------------------------------- #
                tsvals = cast(list[Union[Fraction, int]], interval.values)
                t = HecTime(self)
                if tsvals[Y]:
                    t.increment(count * cast(int, tsvals[0]), Interval.MINUTES["1Year"])
                if tsvals[M]:
                    if isinstance(tsvals[M], Fraction):
                        if tsvals[M].denominator == 3:
                            t.increment(
                                count * tsvals[M].numerator,
                                Interval.MINUTES["Tri-Month"],
                            )
                        else:
                            # deniminator is restricted to 2..3
                            t.increment(
                                count * tsvals[M].numerator,
                                Interval.MINUTES["Semi-Month"],
                            )
                    else:
                        t.increment(
                            count * cast(int, tsvals[M]), Interval.MINUTES["1Month"]
                        )
                if any(tsvals[D:]):
                    t.increment(
                        count,
                        cast(int, tsvals[D]) * 1440
                        + cast(int, tsvals[H]) * 60
                        + cast(int, tsvals[N]),
                    )
                self.set(t)
                return self
            if minutes == Interval.MINUTES["1Year"]:
                # ------ #
                # 1 year #
                # ------ #
                isLastDay = values[D] == maxDay(values[Y], values[M])
                values[Y] += count
                lastDay = maxDay(values[Y], values[M])
                if isLastDay:
                    values[D] = lastDay
                else:
                    if lastDay < values[D]:
                        values[D] = lastDay
            elif minutes == Interval.MINUTES["1Month"]:
                # ------- #
                # 1 month #
                # ------- #
                isLastDay = values[D] == maxDay(values[Y], values[M])
                d = values[D]
                values[M] += count
                values[D] = 1
                normalizeTimeVals(values)
                lastDay = maxDay(values[Y], values[M])
                if isLastDay:
                    values[D] = lastDay
                else:
                    values[D] = d if d <= lastDay else lastDay
            elif minutes == Interval.MINUTES["Semi-Month"]:
                # --------- #
                # 1/2 month #
                # --------- #
                offset = min(values[D], 30) % 15
                startDay = values[D]
                isLastDay = values[D] == maxDay(values[Y], values[M])
                startBin = 0 if values[D] < 15 else 1
                end = startBin + count
                if count > 0:
                    values[M] += end // 2
                else:
                    values[M] += int((end - 1) / 2)
                values[D] = 1
                normalizeTimeVals(values)
                lastDay = maxDay(values[Y], values[M])
                values[D] = min(
                    15 * (startBin + (end % 2 - startBin) + int(startDay >= 30))
                    + offset,
                    lastDay,
                )
                if isLastDay:
                    values[D] = 15 if values[D] <= 15 else lastDay
            elif minutes == Interval.MINUTES["Tri-Month"]:
                # --------- #
                # 1/3 month #
                # --------- #
                offset = min(values[D], 30) % 10
                startDay = values[D]
                startBin = 0 if values[D] < 10 else 1 if values[D] < 20 else 2
                isLastDay = values[D] == maxDay(values[Y], values[M])
                end = startBin + count
                if count > 0:
                    values[M] += end // 3
                else:
                    values[M] += int((end - 2) / 3)
                values[D] = 1
                normalizeTimeVals(values)
                lastDay = maxDay(values[Y], values[M])
                values[D] = min(
                    10 * (startBin + (end % 3 - startBin) + int(startDay >= 30))
                    + offset,
                    lastDay,
                )
                if isLastDay:
                    values[D] = (
                        10 if values[D] <= 10 else 20 if values[D] <= 20 else lastDay
                    )
            else:
                i = Interval.getAny(lambda i: i.minutes == minutes)
                if i:
                    # ------------------------------ #
                    # standard non-calendar interval #
                    # ------------------------------ #
                    values[N] += count * i.minutes
                else:
                    # ------------------------------------------------------------------------- #
                    # not a standard interval, just increment the time by the number of minutes #
                    # ------------------------------------------------------------------------- #
                    values[N] += count * minutes
            normalizeTimeVals(values)
            self.values = values
        return self

    def incrementSecs(self, count: int, interval: int) -> "HecTime":
        """
        Increments this object by a specified number of intervals, which are specified in seconds

        Args:
            count (int): The number of intervals to increment
            interval (int): The size of the interval in seconds. The behavior depends on whether the interval is < 60:
                - `< 60` - the object is incremented by (count * interval) seconds
                - `>= 60` - The object is incremented by (count * interval // 60) minutes

        Returns:
            HecTime: The incremented object
        """
        if interval >= 60:
            self.increment(count, interval // 60)
        else:
            values = self.values
            if values is not None:
                values[S] += count * interval
                normalizeTimeVals(values)
                self.values = values
        return self

    def isDefined(self) -> bool:
        """
        Returns whether this object has been defined

        Deprecated:
            Use [**`defined`**](#HecTime.defined) property instead

        Returns:
            bool: Whether this object has been defined
        """
        warnings.warn(
            "The isDefined() method is deprecated. Please use the defined property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.defined

    def isoDate(self) -> str:
        """
        Returns the date of the current object as YYMMDD format

        Returns:
            str: The date in YYMMDD format
        """
        if not self.defined:
            return ""
        tv = cast(list[int], self.values)
        return f"{tv[Y% 100]:02d}{tv[M]:02d}{tv[D]:02d})"

    def isoTime(self) -> str:
        """
        Returns the time of the current object as HHMMSS format

        Returns:
            str: The date in HHMMSS format
        """
        if not self.defined:
            return ""
        tv = cast(list[int], self.values)
        return f"{tv[H]:02d}{tv[N]:02d}{tv[S]:02d})"

    def isTimeDefined(self) -> bool:
        """
        Returns whether this object has been defined

        Deprecated:
            Use [**`defined`**](#HecTime.defined) property instead

        Returns:
            bool: Whether this object has been defined
        """
        warnings.warn(
            "The isTimeDefined() method is deprecated. Please use the defined property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.defined

    def julian(self) -> Optional[int]:
        """
        Returns the number of days since 31Dec8199 for this object

        Returns:
            int: The number of days since 31Dec1899
        """
        if not self.defined:
            return None
        values = cast(list[int], self.values)
        jul = yearMonthDayToJulian(values[Y], values[M], values[D])
        return jul

    def lessThan(self, other: "HecTime") -> bool:
        """
        Returns whether this object is less than (earlier than) another HecTime object

        Args:
            other (HecTime): The other HecTime object

        Deprecated:
            Use the `<` operator instead

        Returns:
            bool: Whether this object is less than the other object
        """
        warnings.warn(
            "The lessThan() method is deprecated. Please use the < operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self < other

    def lessThanEqualTo(self, other: "HecTime") -> bool:
        """
        Returns whether this object is less than (earlier than) another or equal to (same time as) HecTime object

        Args:
            other (HecTime): The other HecTime object

        Deprecated:
            Use the `<=` operator instead

        Returns:
            bool: Whether this object is less than or equal to the other object
        """
        warnings.warn(
            "The lessThanEqualTo() method is deprecated. Please use the <= operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self <= other

    def minutesSinceMidnight(self) -> Optional[int]:
        """
        Returns the number of minutes past midnight for this object

        Returns:
            int: the number of minutes past midnight
        """
        if not self.defined:
            return None
        return minutesSinceMidnight(cast(list[int], self.values))

    def NotEqualTo(self, other: "HecTime") -> bool:
        """
        Returns whether this object is not equivalent to another

        Args:
            other (Union[&quot;HecTime&quot;, datetime]): The object to compare to

        Deprrecated:
            Use `!=` operator instead

        Returns:
            bool: The result of the comparison
        """
        warnings.warn(
            "The notEqualTo() method is deprecated. Please use the != operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return other != self

    def secondsSinceMidnight(self) -> int:
        """
        Returns the number of seconds past midnight for this object

        Returns:
            int: the number of seconds past midnight
        """
        if not self.defined:
            return UNDEFINED_TIME
        return secondsSinceMidnight(cast(list[int], self.values))

    def set(self, *args: Any) -> int:
        """
        Set the object to a specified date/time. Valid parameters are:
        - **`set(timeInt: int)`** sets the time to the value of `timeInt` for the current granularity
        - **`set(dateTimeStr: str)`** sets the time to the results of [parseDateTimeStr](#HecTime.parseDateTimeStr)(`dateTimeStr`)
        - **`set(dt: datetime)`** sets the time to the value of `dt`
        - **`set(values: Union[list[int],tuple[int,...]])`** sets the time to `values`
        - **`set(otherHecTime: HecTime)`** sets the time and granularity to be the same as `otherHecTime`
        - **`set(dateStr: str, timeStr: str)`** sets the time to the results of [parseDateTimeStr](#HecTime.parseDateTimeStr)(`dateStr`+"&nbsp;"+`timeStr`)

        Returns:
            int: `0` if date/time is successfully set, otherwise non-zero

        See Also:
            [**`parseDateTimeStr()`**](#parseDateTimeStr)
            <br>[**`HecTime.strptime()`**](#HecTime.strptime)
        """
        if len(args) == 1:
            # ------------ #
            # One argument #
            # ------------ #
            if isinstance(args[0], int):
                # set from a time integer
                if isValidTime(args[0], self.__granularity):
                    self.value = args[0]
                else:
                    self.value = UNDEFINED_TIME
            elif isinstance(args[0], str):
                # set from a datetime string
                try:
                    self.set(parseDateTimeStr(args[0]))
                except:
                    self.value = UNDEFINED_TIME
            elif isinstance(args[0], datetime):
                # set from a datetime object
                dt = args[0]
                self.values = [
                    args[0].year,
                    args[0].month,
                    args[0].day,
                    args[0].hour,
                    args[0].minute,
                    args[0].second,
                ]
                self.__tz = dt.tzinfo
            elif isinstance(args[0], (list, tuple)):
                # initialize from a list or tuple of integers
                self.values = list(args[0])
            elif isinstance(args[0], HecTime):
                # initialize from another HecTime object
                self.__value = args[0].value
                self.__values = args[0].values
                self.__granularity = args[0].granularity
                self.__midnight_as_2400 = args[0].midnight_as_2400
                self.__tz = args[0].__tz
        elif len(args) == 2:
            if isinstance(args[0], str) and isinstance(args[1], str):
                self.set(args[0] + " " + args[1])

        return -1 if not self.defined else 0

    def setCurrent(self) -> "HecTime":
        """
        Sets this object to the current time

        Returns:
            HecTime: The modified object
        """
        self.set(datetime.now())
        return self

    def setDate(self, dateStr: str) -> int:
        """
        Sets the date portion only from a string

        Args:
            dateStr (str): The date string. Any time portion is ignored

        Returns:
            int: `0` on success or `-1` on failure
        """
        try:
            values = parseDateTimeStr(dateStr)[:3] = [0, 0, 0]
            if self.defined:
                values = values[:3] + cast(list[int], self.values)[3:]
            self.values = values
            return 0
        except:
            return -1

    def setDefaultDateStyle(self, style: int) -> None:
        """
        Sets the default date style

        Args:
            style (int): The default date style

        Deprecated:
            Use [**default_date_style**](#HecTime.default_date_style) property instead
        """
        warnings.warn(
            "The setDefaultDateStyle() method is deprecated. Please use the default_date_style property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.__default_date_style = style

    def setJulian(
        self,
        julian: int,
        minutesPastMidnight: Optional[int] = None,
        secondsPastMinute: Optional[int] = None,
    ) -> "HecTime":
        """
        Sets the date portion from the number of days since 1899, and optionally the time portion

        Args:
            julian (int): The number of days since 1899
            minutesPastMidnight (Optional[int], optional): The number of minutes past midnight for the time portion. Defaults to None.
            secondsPastMinute (Optional[int], optional): The number of seconds past the minute for the time portion. Defaults to None.

        Returns:
            HecTime: The modified object
        """
        values = 6 * [0]
        julianToYearMonthDay(julian, values)
        if minutesPastMidnight is not None:
            values[H], values[N] = divmod(minutesPastMidnight, 60)
            if secondsPastMinute is not None:
                values[S] = secondsPastMinute
        self.values = values
        return self

    def setMinutes(
        self, totalMinutes: int, timeZoneOffset: Optional[Union[int, "ZoneInfo"]]
    ) -> "HecTime":
        """
        Set the date and time portions of this object from the number of minutes since 1899

        Args:
            totalMinutes (int): The number of minutes since 1899
            timeZoneOffset (Optional[Union[int, &quot;ZoneInfo&quot;]], optional): The time zone to represent this object in. Defaults to None.
                If `int`, the number of minutes *behind* UTC (positive for western longitudes)

        Returns:
            HecTime: The modified object

        Raises:
            HecTimeException: if `timeZoneOffset` is not an integer or `ZoneInfo` object, or if the UTC offset cannot be
                determed for the `ZoneInfo` object
        """
        julian, minutes = divmod(totalMinutes, 1440)
        if timeZoneOffset:
            offsetMinutes = 0
            if isinstance(timeZoneOffset, int):
                offsetMinutes = -timeZoneOffset
            elif isinstance(timeZoneOffset, ZoneInfo):
                utc_offset = datetime.now(tz=timeZoneOffset).utcoffset()
                if utc_offset is None:
                    raise HecTimeException(
                        f"Could not retrieve UTC offset from time zone {timeZoneOffset}"
                    )
                offsetMinutes = int(utc_offset.total_seconds() / 60)
            else:
                raise HecTimeException(
                    f"Expected int or ZoneInfo for timeZoneOffset, got {timeZoneOffset.__class__.__name__}"
                )
            minutes -= offsetMinutes
        self.setJulian(julian, minutes)
        return self

    def setSeconds(self, totalSeconds: int) -> "HecTime":
        """
        Sets the date and time portions of this object from the number seconds since 1970-01-01T00:00:00Z

        Args:
            totalSeconds (int): The number of seconds since 1970-01-01T00:00:00Z (same as Python timestamps and seconds of Unix Epoch)

        Returns:
            HecTime: The modified object
        """
        z = ZERO_TIMES[SECOND_GRANULARITY]
        self.set(
            datetime(z[Y], z[M], z[D], z[H], z[N], z[S])
            + timedelta(seconds=totalSeconds)
        )
        return self

    def setTime(self, timeStr: str) -> int:
        """
        Set the time portion of this object from a time string with or without the date portion

        Args:
            timeStr (str): the time string

        Returns:
            int: `0` on success or `-1` if the time string cannot be parsed
        """
        if self.defined:
            try:
                parsedVals = parseDateTimeStr(timeStr)
            except:
                try:
                    parsedVals = parseDateTimeStr(f"01Jan2000 {timeStr}")
                except:
                    return -1
            values = cast(list[int], self.values)[:3] + parsedVals[3:]
            self.values = values
            return 0
        else:
            return -1

    def setTimeGranularity(self, granularity: int) -> "HecTime":
        """
        Sets the granularity, keeping the existing time values if possible

        Args:
            granularity (int): The new granularity

        Deprecated:
            Use [**granularity**](#HecTime.granularity) property instead

        Returns:
            HecTime: The modified object
        """
        warnings.warn(
            "The setTimeGranularity() method is deprecated. Please use the granularity property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.granularity = granularity
        return self

    @NotImplementedWarning
    def setTimeGranularityInSeconds(self, granularityInSeconds: int) -> None:
        """Not supported in this implementation"""
        pass

    def setTimeInMillis(
        self, milliseconds: int, timeZoneOffset: Optional[Union[int, "ZoneInfo"]]
    ) -> "HecTime":
        """
        Sets the date and time portions of this object from the number milliseconds since 1970-01-01T00:00:00Z

        Args:
            milliseconds (int): The number of seconds since 1970-01-01T00:00:00Z (same as Java milliseconds and milliseconds of Unix Epoch)
            timeZoneOffset (Optional[Union[int, &quot;ZoneInfo&quot;]], optional): The time zone to represent this object in. Defaults to None.
                If `int`, the number of minutes *behind* UTC (positive for western longitudes)

        Returns:
            HecTime: The modified object
        """
        seconds = milliseconds // 1000
        if timeZoneOffset:
            offsetMinutes = 0
            if isinstance(timeZoneOffset, int):
                offsetMinutes = -timeZoneOffset
            elif isinstance(timeZoneOffset, ZoneInfo):
                utc_offset = datetime.now(tz=timeZoneOffset).utcoffset()
                if utc_offset is None:
                    raise HecTimeException(
                        f"Could not retrieve UTC offset from time zone {timeZoneOffset}"
                    )
                offsetMinutes = int(utc_offset.total_seconds() / 60)
            else:
                raise HecTimeException(
                    f"Expected int or ZoneInfo for timeZoneOffset, got {timeZoneOffset.__class__.__name__}"
                )
            seconds -= offsetMinutes * 60
        self.setSeconds(seconds)
        return self

    def setUndefined(self) -> "HecTime":
        """
        Sets this object to the undefined state.

        Returns:
            HecTime: The modified object
        """
        self.value = UNDEFINED_TIME
        return self

    def setXML(self, dateTimeStr: str) -> int:
        """
        Sets this object from an ISO 8601 date/time string.

        Args:
            dateTimeStr (str): The date/time string

        Deprecated:
            The [**`set()`**](#HecTime(set)) function handles this. Use it instead

        Returns:
            int: `0` on success, `-1` otherwise
        """
        warnings.warn(
            "The setXML() method is deprecated. Please use set() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.set(dateTimeStr)

    def setYearMonthDay(
        self, year: int, month: int, day: int, minutesPastMidnight: Optional[int]
    ) -> "HecTime":
        """
        Sets the date portion from a year, month, and day, and optioally the time portion from minutes past midnight

        Args:
            year (int): The year
            month (int): The month
            day (int): The day
            minutesPastMidnight (Optional[int]): The minutes past midnight

        Returns:
            HecTime: The modified object
        """
        values = [year, month, day, 0, 0, 0]
        if minutesPastMidnight is not None:
            values[H], values[N] = divmod(minutesPastMidnight, 60)
        self.values = values
        return self

    def showTimeAsBeginningOfDay(self, state: bool) -> "HecTime":
        """
        Sets whether to show midnight as hour 0 instead of hour 24 of the previous day

        Args:
            state (bool): Whether to show midnight as hour 0 instead of hour 24 of the previous day

        Deprecated:
            Use [**midnight_as_2400**](#HecTime.midnight_as_2400) property instead

        Returns:
            HecTime: The modified object
        """
        warnings.warn(
            "The showTimeAsBeginningOfDay() method is deprecated. Please use the midnight_as_2400 property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.midnight_as_2400 = not state
        return self

    def strftime(self, format: str) -> str:
        """
        Returns a string representing the date and time in the specified format.

        Args:
            format (str): The format string.
                Format specfics can be found [**here**](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior).

        Returns:
            str: The formatted date and time

        See Also:
            - [`date()`](#Hectime.date)
            - [`dateAndTime()`](#Hectime.dateAndTime)
        """
        return cast(datetime, self.datetime()).strftime(format) if self.defined else ""

    def strptime(self, dateTimeStr: str, format: str) -> "HecTime":
        """
        Sets this object from a string representation and a matching format.

        Args:
            dateTimeStr (str): The string to parse.
            format (str): The format describing the string.
                 Format specfics can be found [**here**](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior).

        Returns:
            HecTime: The object updated from the string representation and formt.

        See Also:
            [**`parseDateTimeStr()`**](#parseDateTimeStr)
            <br>[**`HecTime.set()`**](#HecTime.set)
        """
        self.set(datetime.strptime(dateTimeStr, format))
        return self

    def subtract(self, other: Union[int, "HecTime"]) -> "HecTime":
        """
        Subtracts an integer number of granules or HecTime object from this one

        Args:
            other (Union[int, &quot;HecTime&quot;]): The number of granules or HecTime object to subtract

        Deprecated:
            Use the `-=` operator instead instead

        Returns:
            HecTime: The modified object
        """
        warnings.warn(
            "The subtract() method is deprecated. Please use the -= operator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self -= other
        return self

    def subtractDays(self, days: int) -> "HecTime":
        """
        Subtracts a number of days from the object

        Args:
            days (int): the number of days to subtract.

        Returns:
            HecTime: The modified object
        """
        self -= timedelta(days=days)
        return self

    def subtractHours(self, hours: int) -> "HecTime":
        """
        Subtracts a number of hours fram the object

        Args:
            hours (int): the number of hours to subtract.

        Returns:
            HecTime: The modified object
        """
        self -= timedelta(hours=hours)
        return self

    def subtractMinutes(self, minutes: int) -> "HecTime":
        """
        Subtracts a number of minutes from the object

        Args:
            minutes (int): the number of minutes to subtract.

        Returns:
            HecTime: The modified object
        """
        self -= timedelta(minutes=minutes)
        return self

    def subtractSeconds(self, seconds: int) -> "HecTime":
        """
        Subtracts a number of seconds from the object

        Args:
            seconds (int): the number of seconds to subtract.

        Returns:
            HecTime: The modified object
        """
        self -= timedelta(seconds=seconds)
        return self

    def time(self, withColons: Optional[bool] = True) -> str:
        """
        Returns a string representing the time portion

        - withColons = True (default), `[..., 6, 8, 23]` is retuned is `06:08:23`
        - withColons = False, `[..., 6, 8, 23]` is retuned is `0608`
        Args:
            withColons (Optional[bool], optional): Specifies with or without colons. Defaults to `True`.

        Returns:
            str: The time portion string with colons (hour, minute, and second), or without colons (hour, minute only))
        """
        timeStr = ""
        if self.defined:
            h, n, s = cast(list[int], self.values)[3:]
            if withColons:
                timeStr = f"{h:02d}:{n:02d}:{s:02d}"
            else:
                timeStr = f"{h:02d}{n:02d}"
        return timeStr

    def timeGranularity(self) -> int:
        """
        Returns the granularity of this object

        Deprecated:
            Use [**granularity**](#HecTime.granularity) property instead

        Returns:
            int: The granularity
        """
        warnings.warn(
            "The timeGranularity() method is deprecated. Please use the granularity property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.granularity

    @NotImplementedWarning
    def toString(self, style: Optional[int]) -> str:
        """Not supported in this implementation"""
        return NotImplemented