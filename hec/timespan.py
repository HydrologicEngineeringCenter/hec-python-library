"""
Provides basic time span functionality.
Like timedelta, but with calendar capabilities and without sub-second resolution.
"""

import re
from datetime import timedelta
from fractions import Fraction
from functools import total_ordering
from typing import Any, Optional, Union, cast

import hec
import hec.shared

__all__ = ["TimeSpanException", "TimeSpan"]
Y, M, D, H, N, S = 0, 1, 2, 3, 4, 5

# regex modified for fractional months from https://rgxdb.com/r/MD2234J
#
#     1   negative ('-' == negative, empty == positive)
#     2   years
#     3   months (modified to allow fractional months)
#     4   days/weeks
#     5   W or D (W == weeks, D == days)
#     6   hours
#     7   minutes
#     8   seconds
timespan_pattern = re.compile(
    r"^(-?)P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+(?:/\d+)?)M)?(?:(\d+)([DW]))?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$"
)


class TimeSpanException(Exception):
    """
    Exception specific to TimeSpan operations
    """

    pass


@total_ordering
class TimeSpan:
    """
    Class to provide generic timespan capabilities that includes both calendar-based and non-calendar-based
    functionality. Internal fields are:
    - years
    - months
    - days
    - hours
    - minutes
    - seconds

    **Comparison/Contrast with `timedelta`**
    <pre>
    <table>
    <tr><th>timedelta</th><th>TimeSpan</th></tr>
    <tr><td><b>Does not </b> support calendar-based
    operations</td><td><b>Does</b> support calendar-based operations</td></tr>
    <tr><td><b>Does</b> have sub-second resolution</td><td><b>Does not</b> have sub-second resolution</td></tr>
    <tr><td>Can <b>always</b> be combined/compared
    with other timedelta objects</td><td>
    <ul>
    <li>Can <b>always</b> be combined with other TimeSpan
    objects</li>
    <li>Can be combined with timedelta objects <b>if</b> <em>years</em>
    and <em>months</em> are both zero</li>
    <li>Can be compared with other TimeSpan objects <b>if</b> <em>days</em>
    values don't conflict with <em>years</em> or <em>months</em> values</li>
    <li>Can be compared with timedelta objects <b>if</b> <em>years</em>
    and <em>months</em> are both zero</li>
    </ul>
    </td></tr>
    </table>
    </pre>

    **Fractional Months**

    Since HEC-DSS supports intervals of 1/3 and 1/2 month, the month portion of a `TimeSpan` object may be an integer
    or a `Fraction` object from the fractions package. Rules for using fractions are:
    - Fractions can be used for the month portion only
    - `n/2` and `n/3` are the only fractions allowed
    - Fractions can be specified as:
        - mathimatical expression (`1/3`)
        - Fraction object (`Fraction(1,3)`)
        - string (`"1/3"`)

    **Uninitialized Objects**

    Objects constructed without any initializer (e.g., `ts = TimeSpan()`) are initialized to be instantaneous (all values are zero).

    <a id="string_representation"></a>
    **String Representation**

    The `repr` function returns: <pre>TimeSpan([<em>years</em>, <em>months</em>, <em>days</em>, <em>hours</em>, <em>minutes</em>, <em>seconds</em>])</pre>
    The `str` function returns one or two ISO 8601 duration strings or *pseudo-*duration strings if the months value is a fraction.
    - If the object has both calendar- and non-calendar-based (non-zero) values, and the signs of those portions are different,
        the result will be one duration string for the calendar portion and one for the non-calendar portion, separated by a comma.
    - Otherwise the result will be a single duration string.
    <pre>
    PT0S
    P1Y2M3DT4H5M
    -P1Y2M3DT4H5M
    P1Y2M,-P3DT4H5M
    -P1Y2M,P3DT4H5M
    P3Y1/3M
    -P2/3M
    </pre>
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialiazes the object at construction.

        <h6 id="arguments">Arguments:</h6>
        - **Default**
            - **`TimeSpan()`** Initializes to default value of instantaneous (all values equal zero)
        - **Positional**
            - **`TimeSpan(`*`timedelta`*`)`**
            - **`TimeSpan(`*`string`*`)`** where *string* is:
                - an integer as a string
                - one or two ISO 8601 strings or *pseudo-*duration strings as discussed under
                [**String Representation**](#string_representation)
            - **`TimeSpan(`*`list`*`)`** where *list* contains 1..6 values interpreted as years,
                months, days, hours, minutes, and seconds. Values must be convertable via the
                `int()` function except for the second value, which may also be convertable via the `Fraction()` constructor.
            - **`TimeSpan(`*`tuple`*`)`** where *tuple* contains 1..6 values interpreted as years,
                months, days, hours, minutes, and seconds. Values must be convertable via the
                `int()` function except for the second value, which may also be convertable via the `Fraction()` constructor.
            - **`TimeSpan(`*`years`*`[,`*`months`*`[,`*`days`*`[,`*`hours`*`[,`*`minutes`*`[,`*`seconds`*`]]]]])`**
                All values must be convertable via the `int()` function except for *months*,  which may
                also be convertable via the `Fraction()` constructor.

        - **Keyword**:<br>
            - **`TimeSpan([years=`*`years`*`,] [months=`*`months`*`,] [days=`*`days`*`,] [hours=`*`hours`*`,] [minutes=`*`minutes`*`,] [seconds=`*`seconds`*`])`**
                All values must be convertable via the `int()` function except for *months*,  which may
                also be convertable via the `Fraction()` constructor.


        Raises:
            TimeSpanException: if invalid initializers are specified
        """
        # ---------------------- #
        # default initialization #
        # ---------------------- #
        self._years: Optional[int] = None
        self._months: Optional[Union[int, Fraction]] = None
        self._days: Optional[int] = None
        self._hours: Optional[int] = None
        self._minutes: Optional[int] = None
        self._seconds: Optional[int] = None
        self.set(*args, **kwargs)

    def __add__(self, other: object) -> "TimeSpan":
        if isinstance(other, TimeSpan):
            values = []
            values.append(self.values)
            values.append(other.values)
            return TimeSpan(list(map(sum, zip(*values))))
        elif isinstance(other, timedelta):
            vals = cast(list[Union[int, Fraction]], self.values)
            vals[S] += int(other.total_seconds())
            return TimeSpan(vals)
        else:
            return NotImplemented

    def __bool__(self) -> bool:
        return False if self.values is None else any(self.values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TimeSpan):
            return self.values == other.values
        elif isinstance(other, timedelta):
            return self.total_seconds() == int(other.total_seconds())
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, TimeSpan):
            v1 = cast(list[Union[int, Fraction]], self.values)
            v2 = cast(list[Union[int, Fraction]], other.values)
            if (
                cast(int, v1[Y])
                and (abs(cast(int, v2[D]))) > 365
                or cast(int, v2[Y])
                and abs(cast(int, v1[D])) > 365
                or isinstance(v1[M], int)
                and abs(cast(int, v2[D])) > 28
                or isinstance(v1[M], Fraction)
                and abs(cast(int, v2[D])) > 30 / v1[M].denominator
                or isinstance(v2[M], int)
                and abs(cast(int, v1[D])) > 28
                or isinstance(v2[M], Fraction)
                and abs(cast(int, v1[D])) > 30 / v2[M].denominator
            ):
                raise TimeSpanException(
                    "Cannot compare items due to calenar and non-calendar conflicts"
                )
            if v1[Y] > v2[Y]:
                return True
            if v1[Y] < v2[Y]:
                return False
            if v1[M] > v2[M]:
                return True
            if v1[M] < v2[M]:
                return False
            if v1[D] > v2[D]:
                return True
            if v1[D] < v2[D]:
                return False
            if v1[H] > v2[H]:
                return True
            if v1[H] < v2[H]:
                return False
            if v1[N] > v2[N]:
                return True
            if v1[N] < v2[N]:
                return False
            if v1[S] > v2[S]:
                return True
            if v1[S] < v2[S]:
                return False
            return False
        elif isinstance(other, timedelta):
            return self.total_seconds() > other.total_seconds()
        else:
            return NotImplemented

    def __iadd__(self, other: object) -> "TimeSpan":
        if isinstance(other, TimeSpan):
            values = []
            values.append(self.values)
            values.append(other.values)
            self.values = list(map(sum, zip(*values)))
            return self
        elif isinstance(other, timedelta):
            vals = cast(list[Union[int, Fraction]], self.values)
            vals[S] += int(other.total_seconds())
            self.values = vals
            return self
        else:
            return NotImplemented

    def __imul__(self, other: object) -> "TimeSpan":
        if isinstance(other, int):
            vals = list(
                map(lambda v: v * other, cast(list[Union[int, Fraction]], self.values))
            )
            self.values = vals
            return self
        else:
            return NotImplemented

    def __isub__(self, other: object) -> "TimeSpan":
        if isinstance(other, TimeSpan):
            values = []
            values.append(self.values)
            values.append(
                list(map(lambda x: -x, cast(list[Union[int, Fraction]], other.values)))
            )
            self.values = list(map(sum, zip(*values)))
            return self
        elif isinstance(other, timedelta):
            vals = cast(list[Union[int, Fraction]], self.values)
            vals[S] -= int(other.total_seconds())
            self.values = vals
            return self
        else:
            return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, TimeSpan):
            v1 = cast(list[Union[int, Fraction]], self.values)
            v2 = cast(list[Union[int, Fraction]], other.values)
            if (
                cast(int, v1[Y])
                and (abs(cast(int, v2[D]))) > 365
                or cast(int, v2[Y])
                and abs(cast(int, v1[D])) > 365
                or isinstance(v1[M], int)
                and abs(cast(int, v2[D])) > 28
                or isinstance(v1[M], Fraction)
                and abs(cast(int, v2[D])) > 30 / v1[M].denominator
                or isinstance(v2[M], int)
                and abs(cast(int, v1[D])) > 28
                or isinstance(v2[M], Fraction)
                and abs(cast(int, v1[D])) > 30 / v2[M].denominator
            ):
                raise TimeSpanException(
                    "Cannot compare items due to calenar and non-calendar conflicts"
                )
            if v1[Y] < v2[Y]:
                return True
            if v1[Y] > v2[Y]:
                return False
            if v1[M] < v2[M]:
                return True
            if v1[M] > v2[M]:
                return False
            if v1[D] < v2[D]:
                return True
            if v1[D] > v2[D]:
                return False
            if v1[H] < v2[H]:
                return True
            if v1[H] > v2[H]:
                return False
            if v1[N] < v2[N]:
                return True
            if v1[N] > v2[N]:
                return False
            if v1[S] < v2[S]:
                return True
            if v1[S] > v2[S]:
                return False
            return False
        elif isinstance(other, timedelta):
            return self.total_seconds() < other.total_seconds()
        else:
            return NotImplemented

    def __mul__(self, other: object) -> "TimeSpan":
        if isinstance(other, int):
            values = list(
                map(lambda v: v * other, cast(list[Union[int, Fraction]], self.values))
            )
            return TimeSpan(values)
        else:
            return NotImplemented

    def __radd__(self, other: timedelta) -> Union["TimeSpan", timedelta]:
        return timedelta(seconds=other.total_seconds() + self.total_seconds())

    def __repr__(self) -> str:
        return (
            f"TimeSpan([{self._years}, {str(self._months)}, {self._days}, "
            f"{self._hours}, {self._minutes}, {self._seconds}])"
        )

    def __rmul__(self, other: object) -> "TimeSpan":
        if isinstance(other, int):
            values = list(
                map(lambda v: v * other, cast(list[Union[int, Fraction]], self.values))
            )
            return TimeSpan(values)
        else:
            return NotImplemented

    def __rsub__(self, other: Any) -> Any:
        if isinstance(other, timedelta):
            return timedelta(seconds=other.total_seconds() - self.total_seconds())
        return NotImplemented

    def __str__(self) -> str:
        if self.values is None:
            return "Undefined TimeSpan"
        if not any(self.values):
            return "PT0S"
        sign1 = sign2 = False
        temp = TimeSpan(self.values)
        temp._normalize()
        v = cast(list[int], temp.values)
        if v[Y] < 0:
            sign1 = True
            v[Y] += 1
            v[M] -= 12
        if v[D] < 0:
            sign2 = True
            v[D] += 1
            v[H] -= 23
            v[N] -= 59
            if v[S]:
                v[S] -= 60
        if sign1 == sign2:
            string = (
                "-P"
                if sign1
                else "P"
                + (f"{abs(v[Y])}Y" if v[Y] else "")
                + (f"{abs(v[M])}M" if v[M] else "")
                + (f"{abs(v[D])}D" if v[D] else "")
                + ("T" if any(v[H:]) else "")
                + (f"{abs(v[H])}H" if v[H] else "")
                + (f"{abs(v[N])}M" if v[N] else "")
                + (f"{abs(v[S])}S" if v[S] else "")
            )
        else:
            string = (
                ("" if not any(v[Y:D]) else "-P" if sign1 else "P")
                + (f"{abs(v[Y])}Y" if v[Y] else "")
                + (f"{abs(v[M])}M" if v[M] else "")
                + ("," if any(v[Y:D]) and any(v[D:]) else "")
                + ("" if not any(v[D:]) else "-P" if sign2 else "P")
                + (f"{abs(v[D])}D" if v[D] else "")
                + ("T" if any(v[H:]) else "")
                + (f"{abs(v[H])}H" if v[H] else "")
                + (f"{abs(v[N])}M" if v[N] else "")
                + (f"{abs(v[S])}S" if v[S] else "")
            )
        return string

    def __sub__(self, other: object) -> "TimeSpan":
        if isinstance(other, TimeSpan):
            values = []
            values.append(self.values)
            values.append(
                list(map(lambda x: -x, cast(list[Union[int, Fraction]], other.values)))
            )
            return TimeSpan(list(map(sum, zip(*values))))
        elif isinstance(other, timedelta):
            vals = cast(list[Union[int, Fraction]], self.values)
            vals[S] -= int(other.total_seconds())
            return TimeSpan(vals)
        else:
            return NotImplemented

    def _normalize(self) -> None:

        self._years = self._years if self._years is not None else 0
        self._months = self._months if self._months is not None else 0
        self._days = self._days if self._days is not None else 0
        self._hours = self._hours if self._hours is not None else 0
        self._minutes = self._minutes if self._minutes is not None else 0
        self._seconds = self._seconds if self._seconds is not None else 0

        v: list[Union[int, Fraction]] = [
            self._years,
            self._months,
            self._days,
            self._hours,
            self._minutes,
            self._seconds,
        ]
        if any(v[D:]):
            while v[S] > 59:
                v[N] += 1
                v[S] -= 60
            while v[S] < 0:
                v[N] -= 1
                v[S] += 60
            while v[N] > 59:
                v[H] += 1
                v[N] -= 60
            while v[N] < 0:
                v[H] -= 1
                v[N] += 60
            while v[H] > 23:
                v[D] += 1
                v[H] -= 24
            while v[H] < 0:
                v[D] -= 1
                v[H] += 24
        if any(v[:D]):
            while v[M] > 12:
                v[Y] += 1
                v[M] -= 12
            while v[M] < 0:
                v[Y] -= 1
                v[M] += 12

        self._years = cast(int, v[Y])
        self._months = v[M]
        self._days = cast(int, v[D])
        self._hours = cast(int, v[H])
        self._minutes = cast(int, v[N])
        self._seconds = cast(int, v[S])

    @staticmethod
    def _parse_possible_fraction(item: Any) -> Union[int, Fraction]:
        parsed: Union[int, Fraction]
        if isinstance(item, (int, Fraction)):
            parsed = item
        elif isinstance(item, str):
            if item.isdigit():
                parsed = int(item)
            elif item.find("/") != -1:
                parsed = Fraction(item)
            else:
                raise TimeSpanException(
                    f'Expected "{item}" to be an integer, float, string, or fraction. got {item.__class__.__name__}'
                )
        elif isinstance(item, float):
            f = Fraction(item).limit_denominator()
            if f.denominator == 1:
                parsed = f.numerator
            elif f.denominator <= 16:
                parsed = f
            else:
                raise TimeSpanException(
                    f'Floating point "{item}" is not representable as a fraction with a denominator <= 16'
                )
        else:
            raise TimeSpanException(
                f'Expected "{item}" to be an integer, float, string, or fraction. got {item.__class__.__name__}'
            )
        return parsed

    def set(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialiazes or re-initializes the object.

        <h6 id="arguments">Arguments:</h6>
        - **Positional**
            - **`set(`*`timedelta`*`)`**
            - **`set(`*`string`*`)`** where *string* is:
                - an integer as a string
                - one or two ISO 8601 strings or *pseudo-*duration strings as discussed under
                [**String Representation**](#string_representation)
            - **`set(`*`list`*`)`** where *list* contains 1..6 values interpreted as years,
                months, days, hours, minutes, and seconds. Values must be convertable via the
                `int()` function except for the second value, which may also be convertable via the `Fraction()` constructor.
            - **`set(`*`tuple`*`)`** where *tuple* contains 1..6 values interpreted as years,
                months, days, hours, minutes, and seconds. Values must be convertable via the
                `int()` function except for the second value, which may also be convertable via the `Fraction()` constructor.
            - **`set(`*`years`*`[,`*`months`*`[,`*`days`*`[,`*`hours`*`[,`*`minutes`*`[,`*`seconds`*`]]]]])`**
                All values must be convertable via the `int()` function except for *months*,  which may
                also be convertable via the `Fraction()` constructor.

        - **Keyword**:<br>
            - **`set([years=`*`years`*`], [months=`*`months`*`], [days=`*`days`*`], [hours=`*`hours`*`], [minutes=`*`minutes`*`], [seconds=`*`seconds`*`])`**
                All values must be convertable via the `int()` function except for *months*,  which may
                also be convertable via the `Fraction()` constructor.


        Raises:
            TimeSpanException: if invalid initializers are specified
        """
        # ----------------------- #
        # process positional args #
        # ----------------------- #
        parse = TimeSpan._parse_possible_fraction
        if len(args) == 0:
            if len(kwargs) == 0:
                self.set([0, 0, 0, 0, 0, 0])
        elif len(args) == 1:
            if isinstance(args[0], TimeSpan):
                self.set(args[0].values)
            elif isinstance(args[0], timedelta):
                self._seconds = int(args[0].total_seconds())
            elif isinstance(args[0], int):
                self.set([int(args[0]), 0, 0, 0, 0, 0])
            elif isinstance(args[0], str):
                if args[0].isdigit():
                    self.set([int(args[0]), 0, 0, 0, 0, 0])
                else:
                    parts = args[0].split(",", 1)
                    vals: list[list[Union[int, Fraction]]] = []
                    for i in range(len(parts)):
                        vals.append([])
                        m = timespan_pattern.match(parts[i])
                        if m:
                            vals[i].append(int(m.group(2)) if m.group(2) else 0)
                            vals[i].append(parse(m.group(3)) if m.group(3) else 0)
                            vals[i].append(int(m.group(4)) if m.group(4) else 0)
                            vals[i][2] *= 7 if m.group(5) == "W" else 1
                            vals[i].append(int(m.group(6)) if m.group(6) else 0)
                            vals[i].append(int(m.group(7)) if m.group(7) else 0)
                            vals[i].append(
                                int(float(m.group(8))) if m.group(8) else 0
                            )  # truncate seconds
                            if m.group(1) == "-":
                                vals[i] = list(map(lambda x: -x, vals[i]))
                        else:
                            raise TimeSpanException(
                                "Expected positional argument 1 (string) to be in ISO 8601 Duration format.\n"
                                f'Got "{args[0]}" instead.'
                            )
                    self.set(list(map(sum, zip(*vals))))
            elif isinstance(args[0], (list, tuple)):
                self._years = int(args[0][0]) if len(args[0]) > 0 else 0
                self._months = parse(args[0][1]) if len(args[0]) > 1 else 0
                self._days = int(args[0][2]) if len(args[0]) > 2 else 0
                self._hours = int(args[0][3]) if len(args[0]) > 3 else 0
                self._minutes = int(args[0][4]) if len(args[0]) > 4 else 0
                self._seconds = int(args[0][5]) if len(args[0]) > 5 else 0
            else:
                raise TimeSpanException(
                    f"Positional argument 1 is of unexpected type: {args[0].__class__.__name__}"
                )
        elif len(args) > 6:
            raise TimeSpanException(
                f"Expected 0..6 positional arguments, got {len(args)}"
            )
        if len(args) > 5:
            self._seconds = int(args[5])
        if len(args) > 4:
            self._minutes = int(args[4])
        if len(args) > 3:
            self._hours = int(args[3])
        if len(args) > 2:
            self._days = int(args[2])
        if len(args) > 1:
            self._months = parse(args[1])
        if len(args) > 0:
            if self._years is None and isinstance(args[0], (int, float, str)):
                self._years = int(args[0])
        # -------------------- #
        # process keyword args #
        # -------------------- #
        for key in kwargs:
            if key == "years":
                if self._years is not None:
                    raise TimeSpanException(
                        "Cannot specify years in both positional and keyword parameters"
                    )
                self._years = int(kwargs[key])
            if key == "months":
                if self._months is not None:
                    raise TimeSpanException(
                        "Cannot specify months in both positional and keyword parameters"
                    )
                self._months = int(kwargs[key])
            if key == "days":
                if self._days is not None:
                    raise TimeSpanException(
                        "Cannot specify days in both positional and keyword parameters"
                    )
                self._days = int(kwargs[key])
            if key == "hours":
                if self._hours is not None:
                    raise TimeSpanException(
                        "Cannot specify hour in both positional and keyword parameters"
                    )
                self._hours = int(kwargs[key])
            if key == "minutes":
                if self._minutes is not None:
                    raise TimeSpanException(
                        "Cannot specify years in both positional and keyword parameters"
                    )
                self._minutes = int(kwargs[key])
            if key == "seconds":
                if self._seconds is not None:
                    raise TimeSpanException(
                        "Cannot specify seconds in both positional and keyword parameters"
                    )
                self._seconds = int(kwargs[key])
        self._normalize()

    def timedelta(self) -> timedelta:
        """
        Returns an equivalent `timedelta` object

        Raises:
            TimeSpanException: if the object contains any calendar-based values

        Returns:
            timedelta: The equivalent `timedelta` object
        """
        v = cast(list[Union[int, Fraction]], self.values)
        if v[Y] or v[M]:
            raise TimeSpanException(
                "Object with calendar-based values is not convertable to timedelta"
            )
        return timedelta(seconds=self.total_seconds())

    def total_seconds(self) -> int:
        """
        Returns the total number of seconds represented by this object

        Raises:
            TimeSpanException: if the object contains any calendar-based values

        Returns:
            int: The total number of seconds
        """
        v = cast(list[Union[int, Fraction]], self.values)
        if v[Y] or v[M]:
            raise TimeSpanException(
                "Object with calendar-based values cannot compute total seconds"
            )
        return (
            cast(int, v[D]) * 86400
            + cast(int, v[H]) * 3600
            + cast(int, v[N]) * 60
            + cast(int, v[S])
        )

    @property
    def values(self) -> Optional[list[Union[int, Fraction]]]:
        """
        A list of years, months, days, hours, minutes, and seconds in this time span.
        On read, all values will be normalized:
        - years and days are unconstrained in magnitude
        - integer months will be in the range of ±0..12
        - fractional months normalized
        - hours will be in the range of ±0..23
        - minutes and seconds will be in the range ±0..59
        - calendar-based values (years, months) will have the same sign if not zero
        - non-calendar-based values (days, hours, minutes, seconds) will have the same sign if not zero
        - calendar- and non-calendar-based values may have different signs

        Operations:
            Read/Write
        """
        if not all(
            map(
                lambda x: x is not None,
                [
                    self._years,
                    self._months,
                    self._days,
                    self._hours,
                    self._minutes,
                    self._seconds,
                ],
            )
        ):
            return None
        return [
            cast(int, self._years),
            cast(Union[int, Fraction], self._months),
            cast(int, self._days),
            cast(int, self._hours),
            cast(int, self._minutes),
            cast(int, self._seconds),
        ]

    @values.setter
    def values(self, values: list[Union[int, Fraction]]) -> None:
        original_values = self.values
        try:
            self.set(values)
            error = False
        except:
            error = True
        finally:
            if error:
                self.set(original_values)
