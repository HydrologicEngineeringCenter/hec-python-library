"""
Provides standard time intervals
"""

from datetime import datetime, timedelta
from fractions import Fraction
from typing import Any, Callable, List, Optional, Union, cast
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import hec
from hec.timespan import TimeSpan, TimeSpanException

_new_local_regular_names = False


class IntervalException(TimeSpanException):
    """
    Exception specific to Interval operations
    """

    pass


class Interval(TimeSpan):
    """
    Class to hold information about time series recurrence intervals.

    Intervals are a restriction of the TimeSpan base class that also hold extra information.
    - **Restriction:** At most one of `years`, `months`, `days`, `hours`, and `minutes` can be non-zero, and `seconds` must be zero.
    - **Extension:**
        - Each interval has a name that may be context specific.
        - Each also has a specified number of minutes:
            - For non-calendar-based intervals, the minutes are the actual number of minutes in the interval
            - For calendar-based intervals, the minutes are a characteristic number based on standard calendar items:<pre>
                - Tri-Month:  minutes =  10 * 1440       =    14400
                - Semi-Month: minutes =  15 * 1440       =    21600
                - 1 Month:    minutes =  30 * 1440       =    43200
                - 1 Year:     minutes = 365 * 1440       =   525600
                - 1 Decade:   minutes = 365 * 1440 * 10  =  5256000
                - 1 Century:  minutes = 365 * 1440 * 100 = 52560000</pre>

    Intervals should not need to be created by the user, as intervals for the following three contexts are
    created during initialization of the interval module:
    - **CWMS Context:** Contains Intervals used with CWMS
    - **DSS Context:** Contains Intervals used with HEC-DSS files
    - **DSS Block Size Context:** Contains Intervals for the record block sizes in HEC-DSS files

    Each context has its own set of four static methods that retrieve Interval objects or their names:
    - <code>get_any<em>Context</em>()</code>
    - <code>get_any<em>Context</em>_name()</code>
    - <code>get_all<em>Context</em>()</code>
    - <code>get_all<em>Context</em>_names()</code>

    Where *Context* is `Cwms`, `Dss`, or `DssBlock`.

    There are similar static methods that retrieve Interval objects or their names from all contexts:
    - <code>get_any()</code>
    - <code>get_any_name()</code>
    - <code>get_all()</code>
    - <code>get_all_names()</code>
    """

    MINUTES: dict[str, int] = {}
    """
    Dictionary that holds interval minutes, accessed by interval name. Includes all contexts.
    <details>
    <summary>Click to show contents.</summary>
    <pre><table>
    <tr><th>Name</th><th>Minutes</th><th>Context(s)</th></tr>
    <tr><td>0</td><td>0</td><td>CWMS</td></tr>
    <tr><td>Irr</td><td>0</td><td>CWMS</td></tr>
    <tr><td>IR-Century</td><td>0</td><td>DSS</td></tr>
    <tr><td>IR-Day</td><td>0</td><td>DSS</td></tr>
    <tr><td>IR-Decade</td><td>0</td><td>DSS</td></tr>
    <tr><td>IR-Month</td><td>0</td><td>DSS</td></tr>
    <tr><td>IR-Year</td><td>0</td><td>DSS</td></tr>
    <tr><td>1Minute</td><td>1</td><td>CWMS, DSS</td></tr>
    <tr><td>2Minute</td><td>2</td><td>DSS</td></tr>
    <tr><td>2Minutes</td><td>2</td><td>CWMS</td></tr>
    <tr><td>3Minute</td><td>3</td><td>DSS</td></tr>
    <tr><td>3Minutes</td><td>3</td><td>CWMS</td></tr>
    <tr><td>4Minute</td><td>4</td><td>DSS</td></tr>
    <tr><td>4Minutes</td><td>4</td><td>CWMS</td></tr>
    <tr><td>5Minute</td><td>5</td><td>DSS</td></tr>
    <tr><td>5Minutes</td><td>5</td><td>CWMS</td></tr>
    <tr><td>6Minute</td><td>6</td><td>DSS</td></tr>
    <tr><td>6Minutes</td><td>6</td><td>CWMS</td></tr>
    <tr><td>10Minute</td><td>10</td><td>DSS</td></tr>
    <tr><td>10Minutes</td><td>10</td><td>CWMS</td></tr>
    <tr><td>12Minute</td><td>12</td><td>DSS</td></tr>
    <tr><td>12Minutes</td><td>12</td><td>CWMS</td></tr>
    <tr><td>15Minute</td><td>15</td><td>DSS</td></tr>
    <tr><td>15Minutes</td><td>15</td><td>CWMS</td></tr>
    <tr><td>20Minute</td><td>20</td><td>DSS</td></tr>
    <tr><td>20Minutes</td><td>20</td><td>CWMS</td></tr>
    <tr><td>30Minute</td><td>30</td><td>DSS</td></tr>
    <tr><td>30Minutes</td><td>30</td><td>CWMS</td></tr>
    <tr><td>1Hour</td><td>60</td><td>CWMS, DSS</td></tr>
    <tr><td>2Hour</td><td>120</td><td>DSS</td></tr>
    <tr><td>2Hours</td><td>120</td><td>CWMS</td></tr>
    <tr><td>3Hour</td><td>180</td><td>DSS</td></tr>
    <tr><td>3Hours</td><td>180</td><td>CWMS</td></tr>
    <tr><td>4Hour</td><td>240</td><td>DSS</td></tr>
    <tr><td>4Hours</td><td>240</td><td>CWMS</td></tr>
    <tr><td>6Hour</td><td>360</td><td>DSS</td></tr>
    <tr><td>6Hours</td><td>360</td><td>CWMS</td></tr>
    <tr><td>8Hour</td><td>480</td><td>DSS</td></tr>
    <tr><td>8Hours</td><td>480</td><td>CWMS</td></tr>
    <tr><td>12Hour</td><td>720</td><td>DSS</td></tr>
    <tr><td>12Hours</td><td>720</td><td>CWMS</td></tr>
    <tr><td>1Day</td><td>1440</td><td>CWMS, DSS</td></tr>
    <tr><td>2Day</td><td>2880</td><td>DSS</td></tr>
    <tr><td>2Days</td><td>2880</td><td>CWMS</td></tr>
    <tr><td>3Day</td><td>4320</td><td>DSS</td></tr>
    <tr><td>3Days</td><td>4320</td><td>CWMS</td></tr>
    <tr><td>4Day</td><td>5760</td><td>DSS</td></tr>
    <tr><td>4Days</td><td>5760</td><td>CWMS</td></tr>
    <tr><td>5Day</td><td>7200</td><td>DSS</td></tr>
    <tr><td>5Days</td><td>7200</td><td>CWMS</td></tr>
    <tr><td>6Day</td><td>8640</td><td>DSS</td></tr>
    <tr><td>6Days</td><td>8640</td><td>CWMS</td></tr>
    <tr><td>1Week</td><td>10080</td><td>CWMS, DSS</td></tr>
    <tr><td>Tri-Month</td><td>14400</td><td>DSS</td></tr>
    <tr><td>Semi-Month</td><td>21600</td><td>DSS</td></tr>
    <tr><td>1Month</td><td>43200</td><td>CWMS, DSS, DSS BLOCK SIZE</td></tr>
    <tr><td>1Year</td><td>525600</td><td>CWMS, DSS, DSS BLOCK SIZE</td></tr>
    <tr><td>1Decade</td><td>5256000</td><td>DSS BLOCK SIZE</td></tr>
    <tr><td>1Century</td><td>52560000</td><td>DSS BLOCK SIZE</td></tr>
    </table></pre>
    </details>
    """

    _default_exception_on_not_found: bool = False

    def __init__(
        self, timespan: str, name: str, context: str, minutes: Optional[int] = None
    ):
        """Initializer used by module"""
        super().__init__(timespan)
        self._name = name
        self._context = context
        if minutes is None:
            self._intvl_minutes = self.total_seconds() // 60
        else:
            self._intvl_minutes = minutes
        if self._seconds != 0:
            raise IntervalException("Seconds is not allowed to be non-zero")
        count = sum([1 for item in cast(list[int], self.values) if item])
        if count > 1:
            raise IntervalException(
                f"Only one of years, months, days, hours, and minutes is allowed to be non-zero: got {self.values}"
            )

    def __add__(self, other: object) -> "Interval":
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a pseudo-regular Interval object"
            )
        if isinstance(other, (TimeSpan, timedelta)):
            minutes = (self.total_seconds() + other.total_seconds()) // 60
            if self in _DSS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_dss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_cwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.get_any_dss_block(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Interval):
            return [self.context, self.name, self.minutes] == [
                other.context,
                other.name,
                other.minutes,
            ]
        return False

    def __iadd__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

    def __imul__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

    def __isub__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

    def __mul__(self, other: object) -> "Interval":
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local-regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an pseudo-regular Interval object"
            )
        if isinstance(other, (int, float)):
            minutes = int((self.total_seconds() * other) // 60)
            if self in _DSS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_dss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_cwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.get_any_dss_block(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __radd__(self, other: timedelta) -> Union[TimeSpan, timedelta]:
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local-regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a pseudo-regular Interval object"
            )
        if isinstance(other, TimeSpan):
            return TimeSpan(seconds=other.total_seconds() + self.total_seconds())
        elif isinstance(other, timedelta):
            return timedelta(seconds=other.total_seconds() + self.total_seconds())
        else:
            return NotImplemented

    def __repr__(self) -> str:
        try:
            self.total_seconds()
            return f'Interval("{super().__str__()}", "{self._name}")'
        except:
            return f'Interval("{super().__str__()}", "{self._name}", {self.minutes})'

    def __rmul__(self, other: object) -> "TimeSpan":
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local-regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a pseudo-regular Interval object"
            )
        if isinstance(other, (int, float)):
            minutes = int((self.total_seconds() * other) // 60)
            if self in _DSS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_dss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_cwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.get_any_dss_block(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __rsub__(self, other: object) -> Union[TimeSpan, timedelta]:
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local-regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a pseudo-regular Interval object"
            )
        if isinstance(other, TimeSpan):
            return TimeSpan(seconds=other.total_seconds() - self.total_seconds())
        elif isinstance(other, timedelta):
            return timedelta(seconds=other.total_seconds() - self.total_seconds())
        return NotImplemented

    def __sub__(self, other: object) -> "Interval":
        if self.is_local_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a local-regular Interval object"
            )
        if self.is_irregular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with an irregular Interval object"
            )
        if self.is_pseudo_regular:
            raise NotImplementedError(
                "Cannot perform mathematical operations with a pseudo-regular Interval object"
            )
        if isinstance(other, (TimeSpan, timedelta)):
            minutes = (self.total_seconds() - other.total_seconds()) // 60
            if self in _DSS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_dss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.get_any_cwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.get_any_dss_block(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exception_on_not_found=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __str__(self) -> str:
        return super().__str__()

    @staticmethod
    def _get_all(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list["Interval"]:
        all = [i for i in intervals if matcher(i)] if matcher else intervals[:]
        if all:
            return all
        else:
            raise_exc = (
                exception_on_not_found
                if exception_on_not_found is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return all

    @staticmethod
    def _get_all_names(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list[str]:
        all = (
            [i.name for i in intervals if matcher(i)]
            if matcher
            else [i.name for i in intervals]
        )
        if all:
            return all
        else:
            raise_exc = (
                exception_on_not_found
                if exception_on_not_found is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return all

    @staticmethod
    def _get_any(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional["Interval"]:
        all = Interval._get_all(intervals, matcher)
        if all:
            return all[0]
        else:
            raise_exc = (
                exception_on_not_found
                if exception_on_not_found is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                print(exception_on_not_found)
                print(Interval._default_exception_on_not_found)
                raise IntervalException("No such Interval")
            else:
                return None

    @staticmethod
    def _get_any_name(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional[str]:
        all = Interval._get_all_names(intervals, matcher)
        if all:
            return all[0]
        else:
            raise_exc = (
                exception_on_not_found
                if exception_on_not_found is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return None

    @property
    def context(self) -> str:
        """
        The context of this object ("Cwms", "Dss", or "DssBlock")

        Operations:
            Read-only
        """
        return self._context

    @staticmethod
    def get_all(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the any context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in all contexts are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._get_all(
            _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES,
            matcher,
            exception_on_not_found,
        )

    @staticmethod
    def get_all_cwms(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the CWMS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._get_all(_CWMS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_all_cwms_names(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the CWMS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return list(
            dict.fromkeys(
                Interval._get_all_names(
                    _CWMS_INTERVALS, matcher, exception_on_not_found
                )
            )
        )

    @staticmethod
    def get_all_dss(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the DSS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._get_all(_DSS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_all_dss_block_names(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the DSS block size context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._get_all_names(
            _DSS_BLOCK_SIZES, matcher, exception_on_not_found
        )

    @staticmethod
    def get_all_dss_blocks(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the DSS block size context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._get_all(_DSS_BLOCK_SIZES, matcher, exception_on_not_found)

    @staticmethod
    def get_all_dss_names(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the DSS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._get_all_names(_DSS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_all_names(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exception_on_not_found: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the any context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in all contexts are matched.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return list(
            dict.fromkeys(
                Interval._get_all_names(
                    _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES,
                    matcher,
                    exception_on_not_found,
                )
            )
        )

    @staticmethod
    def get_any(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in any context

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._get_any(intervals, matcher, exception_on_not_found)
            if i:
                break
        return i

    @staticmethod
    def get_any_cwms(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_no_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._get_any(_CWMS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_any_cwms_name(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._get_any_name(_CWMS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_any_dss(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._get_any(_DSS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_any_dss_block(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._get_any(_DSS_BLOCK_SIZES, matcher, exception_on_not_found)

    @staticmethod
    def get_any_dss_block_name(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._get_any_name(_DSS_BLOCK_SIZES, matcher, exception_on_not_found)

    @staticmethod
    def get_any_dss_name(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_exception_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._get_any_name(_DSS_INTERVALS, matcher, exception_on_not_found)

    @staticmethod
    def get_any_name(
        matcher: Callable[["Interval"], bool],
        exception_on_not_found: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the any context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.is_irregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exception_on_not_found (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [set_default_excpetion_on_not_found](#Interval.set_default_exception_on_not_found) and
                [get_default_exception_on_not_found](#Interval.get_default_exception_on_not_found)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._get_any_name(intervals, matcher, exception_on_not_found)
            if i:
                break
        return i

    @staticmethod
    def get_cwms(key: Union[str, int]) -> "Interval":
        """
        Returns a CWMS interval with the specified name or minutes

        Args:
            key (Union[str, int]): The name or (actual or characteristic) minutes of the interval to retrieve.

        Raises:
            IntervalException: if no CWMS interval exists with the specified key
            TypeError: If the key is not a string or integer

        Returns:
            Interval: The CWMS interval
        """
        intvl: Optional[Interval] = None
        if isinstance(key, str):
            intvl = Interval.get_any_cwms(lambda i: i.name == key.title(), False)
            if intvl is None:
                raise IntervalException(f'No CWMS interval found with name = "{key}"')
        elif isinstance(key, int):
            intvl = Interval.get_any_cwms(lambda i: i.minutes == key, False)
            if intvl is None:
                raise IntervalException(f"No CWMS interval found with minutes = {key}")
        else:
            raise TypeError(f"Expected string or integer, got {key.__class__.__name__}")
        return intvl

    def get_datetime_index(
        self,
        start_time: Any,
        end_time: Optional[Any] = None,
        count: Optional[int] = None,
        offset: Optional[Any] = None,
        time_zone: Optional[Any] = None,
        name: Optional[str] = None,
    ) -> pd.DatetimeIndex:
        """
        Generates a pandas DatetimeIndex from this interval.

        Args:
            start_time (Any): A time in the first interval. If `offset` is None, this will be the first time, otherwise the first time will be the top of the interval
                containing this time plus the specified `offset`. If the time includes no time zone, it will be assumed to be in `time_zone`, if specified, if any.
                Must be an [`HecTime`](hectime.html#HecTime) object or an object suitable for the [`HecTime` constructor](hectime.html#HecTime.__init__)
            end_time (Optional[Any]): The generated series will end on or before this time, if specified. If the time includes no time zone, it will be assumed to be in `time_zone`, if specified.
                If specified, must be an [`HecTime`](hectime.html#HecTime) object or an object suitable for the [`HecTime` constructor](hectime.html#HecTime.__init__). Either `end_time` or
                `count`, but not both, must be specified. Defaults to None.
            count (Optional[int]): The number of times in the index. Either `end_time` or `count`, but not both, must be specified. Defaults to None.
            offset (Optional[Any]): The offset of each time into the interval. If None, the offset is determined from `start_time`. If specified, must be an
                [`TimeSpan`](timespan.html#TimeSpan) object or an object suitable for the [`TimeSpan` constructor](timespan.html#TimeSpan.__init__). Defaults to None.
            time_zone (Optional[Any]): The time zone of the generated times. Must be specified if the interval is a local-regular interval. Defaults to None.
            name (Optional[str]): The name of the index. If the generated index is to be used in a [`TimeSeries`](timeseries.html#TimeSeries) object, specify the name as "name". Defaults to None.

        Raises:
            IntervalException: If invalid parameters are specified

        Returns:
            pd.DatetimeIndex: The generated index.

        Notes:
            There is a somewhat subtle interplay between `start_time` and `offset`. If `offset` is None or not specified, the index is generated as follows:
                <ul>
                <li>The offset used is the offset of <code>start_time</code> into the Interval object being used</li>
                <li>The offset handles end-of-month dates and leap years by adjusting the actual offset at each time to keep dates as aligned as possible</li>
                </ul>
            Otherwise the offset is used literally.<br>
            See the following examples:
        <table style="font-size: 14px;">
        <pre>
        <tr><th colspan="5">Index on 1Month interval<br>Values in <span style="color: red;">red</span> exceed the end of the month</th><tr>
        <tr><th>start_time</th><th colspan="2">"2025&#8209;01&#8209;31 08:00:00"</th><th colspan="2">"2025&#8209;01&#8209;01 00:00:00"</th></tr>
        <tr><th>offset</th><th>None</th><th colspan="2">TimeSpan("P30DT8H")</th><th>timedelta(<br>&nbsp;&nbsp;days=30,<br>&nbsp;&nbsp;hours=8,<br>)</th></tr>
        <tr><th rowspan="13">index</th>
        <tr><td>2025&#8209;01&#8209;31&nbsp;08:00:00</td><td>2025&#8209;01&#8209;31&nbsp;08:00:00</td><td>2025&#8209;01&#8209;31&nbsp;08:00:00</td><td>2025&#8209;01&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;02&#8209;28&nbsp;08:00:00</td><td style="color: red;">2025&#8209;03&#8209;03&nbsp;08:00:00</td><td style="color: red;">2025&#8209;03&#8209;03&nbsp;08:00:00</td><td style="color: red;">2025&#8209;03&#8209;03&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;03&#8209;31&nbsp;08:00:00</td><td>2025&#8209;03&#8209;31&nbsp;08:00:00</td><td>2025&#8209;03&#8209;31&nbsp;08:00:00</td><td>2025&#8209;03&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;04&#8209;30&nbsp;08:00:00</td><td style="color: red;">2025&#8209;05&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;05&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;05&#8209;01&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;05&#8209;31&nbsp;08:00:00</td><td>2025&#8209;05&#8209;31&nbsp;08:00:00</td><td>2025&#8209;05&#8209;31&nbsp;08:00:00</td><td>2025&#8209;05&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;06&#8209;30&nbsp;08:00:00</td><td style="color: red;">2025&#8209;07&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;07&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;07&#8209;01&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;07&#8209;31&nbsp;08:00:00</td><td>2025&#8209;07&#8209;31&nbsp;08:00:00</td><td>2025&#8209;07&#8209;31&nbsp;08:00:00</td><td>2025&#8209;07&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;08&#8209;31&nbsp;08:00:00</td><td>2025&#8209;08&#8209;31&nbsp;08:00:00</td><td>2025&#8209;08&#8209;31&nbsp;08:00:00</td><td>2025&#8209;08&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;09&#8209;30&nbsp;08:00:00</td><td style="color: red;">2025&#8209;10&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;10&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;10&#8209;01&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;10&#8209;31&nbsp;08:00:00</td><td>2025&#8209;10&#8209;31&nbsp;08:00:00</td><td>2025&#8209;10&#8209;31&nbsp;08:00:00</td><td>2025&#8209;10&#8209;31&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;11&#8209;30&nbsp;08:00:00</td><td style="color: red;">2025&#8209;12&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;12&#8209;01&nbsp;08:00:00</td><td style="color: red;">2025&#8209;12&#8209;01&nbsp;08:00:00</td></tr>
        <tr><td>2025&#8209;12&#8209;31&nbsp;08:00:00</td><td>2025&#8209;12&#8209;31&nbsp;08:00:00</td><td>2025&#8209;12&#8209;31&nbsp;08:00:00</td><td>2025&#8209;12&#8209;31&nbsp;08:00:00</td></tr>
        </pre>
        </table>
        <table style="font-size: 14px;">
        <pre>
        <tr><th colspan="5">Index on 1Year interval<br>Values in <span style="color: red;">red</span> don't match the starting day-of-month</th><tr>
        <tr><th>start_time</th><th colspan="2">"2025&#8209;05&#8209;11 00:00:00"</th><th colspan="2">"2025&#8209;01&#8209;01 00:00:00"</th></tr>
        <tr><th>offset</th><th>None</th><th colspan="2">TimeSpan("P1M10D")</th><th>timedelta(<br>&nbsp;&nbsp;days=130,<br>)</th></tr>
        <tr><th rowspan="13">index</th>
        <tr><td>2025&#8209;05&#8209;11&nbsp;00:00:00</td><td>2025&#8209;05&#8209;11&nbsp;00:00:00</td><td>2025&#8209;05&#8209;11&nbsp;00:00:00</td><td>2025&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2026&#8209;05&#8209;11&nbsp;00:00:00</td><td>2026&#8209;05&#8209;11&nbsp;00:00:00</td><td>2026&#8209;05&#8209;11&nbsp;00:00:00</td><td>2026&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2027&#8209;05&#8209;11&nbsp;00:00:00</td><td>2027&#8209;05&#8209;11&nbsp;00:00:00</td><td>2027&#8209;05&#8209;11&nbsp;00:00:00</td><td>2027&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2028&#8209;05&#8209;11&nbsp;00:00:00</td><td>2028&#8209;05&#8209;11&nbsp;00:00:00</td><td>2028&#8209;05&#8209;11&nbsp;00:00:00</td><td style="color: red;">2028&#8209;05&#8209;10&nbsp;00:00:00</td></tr>
        <tr><td>2029&#8209;05&#8209;11&nbsp;00:00:00</td><td>2029&#8209;05&#8209;11&nbsp;00:00:00</td><td>2029&#8209;05&#8209;11&nbsp;00:00:00</td><td>2029&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2030&#8209;05&#8209;11&nbsp;00:00:00</td><td>2030&#8209;05&#8209;11&nbsp;00:00:00</td><td>2030&#8209;05&#8209;11&nbsp;00:00:00</td><td>2030&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2031&#8209;05&#8209;11&nbsp;00:00:00</td><td>2031&#8209;05&#8209;11&nbsp;00:00:00</td><td>2031&#8209;05&#8209;11&nbsp;00:00:00</td><td>2031&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2032&#8209;05&#8209;11&nbsp;00:00:00</td><td>2032&#8209;05&#8209;11&nbsp;00:00:00</td><td>2032&#8209;05&#8209;11&nbsp;00:00:00</td><td style="color: red;">2032&#8209;05&#8209;10&nbsp;00:00:00</td></tr>
        <tr><td>2033&#8209;05&#8209;11&nbsp;00:00:00</td><td>2033&#8209;05&#8209;11&nbsp;00:00:00</td><td>2033&#8209;05&#8209;11&nbsp;00:00:00</td><td>2033&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2034&#8209;05&#8209;11&nbsp;00:00:00</td><td>2034&#8209;05&#8209;11&nbsp;00:00:00</td><td>2034&#8209;05&#8209;11&nbsp;00:00:00</td><td>2034&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2035&#8209;05&#8209;11&nbsp;00:00:00</td><td>2035&#8209;05&#8209;11&nbsp;00:00:00</td><td>2035&#8209;05&#8209;11&nbsp;00:00:00</td><td>2035&#8209;05&#8209;11&nbsp;00:00:00</td></tr>
        <tr><td>2036&#8209;05&#8209;11&nbsp;00:00:00</td><td>2036&#8209;05&#8209;11&nbsp;00:00:00</td><td>2036&#8209;05&#8209;11&nbsp;00:00:00</td><td style="color: red;">2036&#8209;05&#8209;10&nbsp;00:00:00</td></tr>
        </pre>
        </table>
        """
        if not self.is_any_regular:
            raise IntervalException(
                f"Cannot create a datetime index from irregular interval {self.name}"
            )
        if not any([end_time, count]):
            raise IntervalException("One of 'end_time' or 'count' must be specified")
        if all([end_time, count]):
            raise IntervalException(
                "Only one of 'end_time' or 'count' may be specified"
            )
        l_start_time = hec.hectime.HecTime(start_time).label_as_time_zone(
            "UTC" if self.is_local_regular else time_zone, on_already_set=0
        )
        if not l_start_time.defined:
            raise IntervalException(
                "Cannot get a datetime index: start_time is undefined."
            )
        l_start_time.midnight_as_2400 = False
        l_interval_begin = hec.hectime.HecTime(l_start_time).adjust_to_interval_offset(
            self, 0
        )
        l_interval_offset = cast(TimeSpan, l_start_time - l_interval_begin)
        l_end_time = (
            None
            if end_time is None
            else hec.hectime.HecTime(end_time).label_as_time_zone(
                "UTC" if self.is_local_regular else time_zone, on_already_set=0
            )
        )
        if l_end_time:
            if not l_end_time.defined:
                raise IntervalException(
                    "Cannot get a datetime index: end_time is specified but undefined."
                )
            l_end_time.midnight_as_2400 = False
        if time_zone is None and self.is_local_regular:
            raise IntervalException(
                f"Cannot create a local-regular time series: no time zone specified."
            )
        l_offset = None if offset is None else TimeSpan(offset)
        l_first_time = l_start_time if l_offset is None else l_interval_begin + l_offset
        if l_first_time < l_start_time:
            l_interval_begin = l_interval_begin.increment(1, self)
            l_first_time = l_interval_begin + l_offset
        if (
            self.is_local_regular
            and self.minutes > Interval.MINUTES["1Month"]
            and offset
            and time_zone
        ):
            # -------------------------------- #
            # adjust for crossing DST boundary #
            # -------------------------------- #
            l_start_time_tz = l_start_time.label_as_time_zone(
                time_zone, on_already_set=0
            )
            l_interval_begin_tz = cast(
                hec.hectime.HecTime, l_start_time_tz.clone()
            ).adjust_to_interval_offset(self, 0)
            l_first_time_tz = l_interval_begin_tz + l_offset
            if l_first_time_tz < l_start_time_tz:
                l_interval_begin_tz.increment(1, self)
                l_first_time_tz = l_interval_begin_tz + l_offset
            l_first_time = l_first_time_tz.label_as_time_zone("UTC", on_already_set=0)
        try:
            l_freq = _DATETIME_INDEX_FREQ[str(TimeSpan(self.values))]
        except KeyError:
            l_freq = None
        if l_freq:
            if time_zone and not self.is_local_regular:
                l_first_time = l_first_time.convert_to_time_zone("UTC")
                if l_end_time:
                    l_end_time = l_end_time.convert_to_time_zone("UTC")
            l_indx = pd.date_range( # type: ignore
                start=l_first_time.datetime(),
                end=None if l_end_time is None else l_end_time.datetime(),
                periods=count,
                freq=l_freq,
                name=name,
            )
            if l_end_time:
                l_indx = l_indx[(l_indx <= l_end_time.datetime())]  # type: ignore[operator]
            if time_zone and not self.is_local_regular:
                l_indx = l_indx.tz_convert(
                    ZoneInfo(time_zone) if isinstance(time_zone, str) else time_zone
                )
        else:
            # ------------------------------------------------------------------------ #
            # calendar intervals don't have a single frequency for pandas date_range() #
            # ------------------------------------------------------------------------ #
            if l_end_time:
                l_start_minutes = cast(int, l_start_time.julian()) * 1440 + cast(
                    int, l_start_time.minutes_since_midnight()
                )
                l_end_minutes = cast(int, l_end_time.julian()) * 1440 + cast(
                    int, l_end_time.minutes_since_midnight()
                )
                l_count = int((l_end_minutes - l_start_minutes) / self.minutes * 1.1)
            else:
                l_count = cast(int, count)
            if self.minutes == Interval.MINUTES["1Month"]:
                if l_offset is None:
                    if cast(int, l_first_time.day) >= 28:
                        l_target_day = l_start_time.day
                        if time_zone and not self.is_local_regular:
                            l_first_time = l_first_time.convert_to_time_zone("UTC")
                            if l_end_time:
                                l_end_time = l_end_time.convert_to_time_zone("UTC")
                        l_indx = pd.date_range( # type: ignore
                            start=l_first_time.datetime(),
                            periods=l_count,
                            freq="1ME",
                            unit="s",
                            name=name,
                        )
                        if time_zone and not self.is_local_regular:
                            l_indx = l_indx.tz_convert(
                                ZoneInfo(time_zone)
                                if isinstance(time_zone, str)
                                else time_zone
                            )
                        l_timestamps = [
                            (
                                dt.replace(day=l_target_day)
                                if dt.day > cast(int, l_target_day)
                                else dt
                            )
                            for dt in l_indx
                        ]
                        l_indx = pd.DatetimeIndex(data=l_timestamps, name=name)
                        if l_end_time:
                            l_indx = l_indx[(l_indx <= l_end_time.datetime())]  # type: ignore[operator]
                    else:
                        if time_zone and not self.is_local_regular:
                            l_interval_begin = l_interval_begin.convert_to_time_zone(
                                "UTC"
                            )
                            if l_end_time:
                                l_end_time = l_end_time.convert_to_time_zone("UTC")
                        l_indx = pd.date_range( # type: ignore
                            start=l_interval_begin.datetime(),
                            periods=l_count,
                            freq="1MS",
                            unit="s",
                            name=name,
                        )
                        if time_zone and not self.is_local_regular:
                            l_indx = l_indx.tz_convert(
                                ZoneInfo(time_zone)
                                if isinstance(time_zone, str)
                                else time_zone
                            )
                        v = cast(list[int], l_interval_offset.values)
                        if v[0]:
                            l_indx += pd.DateOffset(years=v[0])  # type: ignore[operator]
                        if v[1]:
                            l_indx += pd.DateOffset(months=v[1])  # type: ignore[operator]
                        if v[2]:
                            l_indx += pd.DateOffset(days=v[2])  # type: ignore[operator]
                        if v[3]:
                            l_indx += pd.DateOffset(hours=v[3])  # type: ignore[operator]
                        if v[4]:
                            l_indx += pd.DateOffset(minutes=v[4])  # type: ignore[operator]
                        if l_end_time:
                            l_indx = l_indx[(l_indx <= l_end_time.datetime())]  # type: ignore[operator]
                else:
                    if time_zone and l_offset is not None:
                        l_interval_begin = l_interval_begin.convert_to_time_zone("UTC")
                        if l_end_time:
                            l_end_time = l_end_time.convert_to_time_zone("UTC")
                    l_indx = pd.date_range( # type: ignore
                        start=l_interval_begin.datetime(),
                        periods=l_count,
                        freq="1MS",
                        unit="s",
                        name=name,
                    )
                    v = cast(list[int], l_offset.values)
                    if v[0]:
                        l_indx += pd.DateOffset(years=v[0])  # type: ignore[operator]
                    if v[1]:
                        l_indx += pd.DateOffset(months=v[1])  # type: ignore[operator]
                    if v[2]:
                        l_indx += pd.DateOffset(days=v[2])  # type: ignore[operator]
                    if v[3]:
                        l_indx += pd.DateOffset(hours=v[3])  # type: ignore[operator]
                    if v[4]:
                        l_indx += pd.DateOffset(minutes=v[4])  # type: ignore[operator]
                    if l_end_time:
                        l_indx = l_indx[(l_indx <= l_end_time.datetime())]  # type: ignore[operator]
                    if time_zone and l_offset is not None:
                        if self.is_local_regular:
                            l_indx = l_indx.tz_localize(None).tz_localize(
                                ZoneInfo(time_zone)
                                if isinstance(time_zone, str)
                                else time_zone
                            )
                        else:
                            l_indx = l_indx.tz_convert(
                                ZoneInfo(time_zone)
                                if isinstance(time_zone, str)
                                else time_zone
                            )
            else:
                if offset is None:
                    l_first_time = l_start_time
                else:
                    l_interval_begin = cast(
                        hec.hectime.HecTime, l_start_time.clone()
                    ).adjust_to_interval_offset(self, 0)
                    l_first_time = l_interval_begin + offset
                    if l_first_time < l_start_time:
                        l_interval_begin.increment(1, self)
                        l_first_time = l_interval_begin + offset
                if time_zone:
                    if self.is_local_regular:
                        l_first_time = l_first_time.label_as_time_zone(
                            "UTC", on_already_set=0
                        )
                        if l_end_time is not None:
                            l_end_time = l_end_time.label_as_time_zone(
                                "UTC", on_already_set=0
                            )
                    else:
                        l_first_time = l_first_time.convert_to_time_zone("UTC")
                        if l_end_time is not None:
                            l_end_time = l_end_time.convert_to_time_zone("UTC")
                l_hectimes = [
                    l_first_time.copy().increment(i, self) for i in range(l_count)
                ]
                if l_end_time is not None:
                    while l_hectimes[-1] > l_end_time:
                        l_hectimes.pop()
                if time_zone:
                    if self.is_local_regular:
                        l_hectimes = [
                            ht.label_as_time_zone(time_zone, on_already_set=0)
                            for ht in l_hectimes
                        ]
                    else:
                        l_hectimes = [
                            ht.convert_to_time_zone(time_zone) for ht in l_hectimes
                        ]
                l_datetimes = [cast(datetime, ht.datetime()) for ht in l_hectimes]
                l_indx = pd.DatetimeIndex(data=l_datetimes, name=name)
        if self.is_local_regular:
            ambiguous_flags = np.zeros(len(l_indx), dtype=bool)
            l_indx = l_indx.tz_localize(None).tz_localize(
                ZoneInfo(time_zone) if isinstance(time_zone, str) else time_zone,
                ambiguous=ambiguous_flags,
            )
        return l_indx # type: ignore

    @staticmethod
    def get_default_exception_on_not_found() -> bool:
        """
        Retrieves the default behavior if any of the get... methods do not find an Interval object to return.

        Returns:
            bool: True if the default behavior is to raise an exception when no Interval is found or False
                if `None` is returned when no Interval is found
        """
        return Interval._default_exception_on_not_found

    @staticmethod
    def get_dss(key: Union[str, int]) -> "Interval":
        """
        Returns an HEC-DSS interval with the specified name or minutes

        Args:
            key (Union[str, int]): The name or (actual or characteristic) minutes of the interval to retrieve.

        Raises:
            IntervalException: if no Dss interval exists with the specified key
            TypeError: If the key is not a string or integer

        Returns:
            Interval: The Dss interval
        """
        intvl: Optional[Interval] = None
        if isinstance(key, str):
            if key.upper().startswith("IR-"):
                intvl = Interval.get_any_dss(
                    lambda i: i.name == f"IR-{key[3:].title()}", False
                )
            else:
                intvl = Interval.get_any_dss(lambda i: i.name == key.title(), False)
            if intvl is None:
                raise IntervalException(
                    f'No HEC-DSS interval found with name = "{key}"'
                )
        elif isinstance(key, int):
            intvl = Interval.get_any_dss(lambda i: i.minutes == key, False)
            if intvl is None:
                raise IntervalException(
                    f"No HEC-DSS interval found with minutes = {key}"
                )
        else:
            raise TypeError(f"Expected string or integer, got {key.__class__.__name__}")
        return intvl

    @staticmethod
    def get_dss_block_for_interval(interval: Union[str, int, "Interval"]) -> "Interval":
        """
        Returns the HEC-DSS block size for a specified interval.

        Args:
            interval (Union[str, int, &quot;Interval&quot;]): The interval to return the block size for. May be an Interval object,
                or its name or (actual or characteristic) minutes.

        Returns:
            Interval: An interval object representing the HEC-DSS block size
        """
        if isinstance(interval, (str, int)):
            _interval = Interval.get_dss(interval)
        elif isinstance(interval, Interval):
            _interval = interval
        else:
            raise ValueError(
                f"Expected str, int, or Interval for interval, got {interval.__class__.__name__}"
            )
        block_size_name = _DSS_BLOCK_SIZE_FOR_INTERVAL[_interval.name]
        assert block_size_name, f"Couldn't determine HEC-DSS block size for {_interval}"
        block_size = Interval.get_any_dss_block(lambda i: i.name == block_size_name)
        assert (
            block_size
        ), f"Couldn't instantiate block size interval '{block_size_name}'"
        return block_size

    @property
    def is_any_irregular(self) -> bool:
        """
        Whether this object represents a normal irregular or pseudo-regular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0]

    @property
    def is_any_regular(self) -> bool:
        """
        Whether this object represents a regular or local regular interval

        Operations:
            Read-only
        """
        return self.is_regular or self.is_local_regular

    @property
    def is_local_regular(self) -> bool:
        """
        Whether this object represents a local regular interval

        Operations:
            Read-only
        """
        if _new_local_regular_names:
            return self.values != [0, 0, 0, 0, 0, 0] and self.name.endswith("Local")
        else:
            return self.values != [0, 0, 0, 0, 0, 0] and self.name[0] == "~"

    @property
    def is_pseudo_regular(self) -> bool:
        """
        Whether this object represents a pseudo-regular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0] and self.name[0] == "~"

    @property
    def is_regular(self) -> bool:
        """
        Whether this object represents a normal regular interval

        Operations:
            Read-only
        """
        if _new_local_regular_names:
            return self.values != [0, 0, 0, 0, 0, 0] and not self.name.endswith("Local")
        else:
            return self.values != [0, 0, 0, 0, 0, 0] and self.name[0] != "~"

    @property
    def is_irregular(self) -> bool:
        """
        Whether this object represents a normal irregular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0] and self.name[0] != "~"

    @property
    def minutes(self) -> int:
        """
        The minutes (actual or characteristic) of this object

        Operations:
            Read-only
        """
        return self._intvl_minutes

    @property
    def name(self) -> str:
        """
        The name of this object

        Operations:
            Read-only
        """
        return self._name

    @staticmethod
    def set_default_exception_on_not_found(state: bool) -> None:
        """
        Sets the default behavior if any of the get... methods do not find an Interval object to return.

        Args:
            state (bool): Whether to raise an exception if no Interval is found (True) or return None (False)
        """
        Interval._default_exception_on_not_found = state


_CWMS_INTERVALS = [
    Interval("PT0S", "0", "Cwms"),
    Interval("PT0S", "Irr", "Cwms"),
    Interval("PT0S", "~1Minute", "Cwms"),
    Interval("PT0S", "~2Minutes", "Cwms"),
    Interval("PT0S", "~3Minutes", "Cwms"),
    Interval("PT0S", "~4Minutes", "Cwms"),
    Interval("PT0S", "~5Minutes", "Cwms"),
    Interval("PT0S", "~6Minutes", "Cwms"),
    Interval("PT0S", "~10Minutes", "Cwms"),
    Interval("PT0S", "~12Minutes", "Cwms"),
    Interval("PT0S", "~15Minutes", "Cwms"),
    Interval("PT0S", "~20Minutes", "Cwms"),
    Interval("PT0S", "~30Minutes", "Cwms"),
    Interval("PT0S", "~1Hour", "Cwms"),
    Interval("PT0S", "~2Hours", "Cwms"),
    Interval("PT0S", "~3Hours", "Cwms"),
    Interval("PT0S", "~4Hours", "Cwms"),
    Interval("PT0S", "~6Hours", "Cwms"),
    Interval("PT0S", "~8Hours", "Cwms"),
    Interval("PT0S", "~12Hours", "Cwms"),
    Interval("PT0S", "~1Day", "Cwms"),
    Interval("PT0S", "~2Days", "Cwms"),
    Interval("PT0S", "~3Days", "Cwms"),
    Interval("PT0S", "~4Days", "Cwms"),
    Interval("PT0S", "~5Days", "Cwms"),
    Interval("PT0S", "~6Days", "Cwms"),
    Interval("PT0S", "~1Week", "Cwms"),
    Interval("PT0S", "~1Month", "Cwms"),
    Interval("PT0S", "~1Year", "Cwms"),
    Interval("PT1M", "1Minute", "Cwms"),
    Interval("PT2M", "2Minutes", "Cwms"),
    Interval("PT3M", "3Minutes", "Cwms"),
    Interval("PT4M", "4Minutes", "Cwms"),
    Interval("PT5M", "5Minutes", "Cwms"),
    Interval("PT6M", "6Minutes", "Cwms"),
    Interval("PT10M", "10Minutes", "Cwms"),
    Interval("PT12M", "12Minutes", "Cwms"),
    Interval("PT15M", "15Minutes", "Cwms"),
    Interval("PT20M", "20Minutes", "Cwms"),
    Interval("PT30M", "30Minutes", "Cwms"),
    Interval("PT1H", "1Hour", "Cwms"),
    Interval("PT2H", "2Hours", "Cwms"),
    Interval("PT3H", "3Hours", "Cwms"),
    Interval("PT4H", "4Hours", "Cwms"),
    Interval("PT6H", "6Hours", "Cwms"),
    Interval("PT8H", "8Hours", "Cwms"),
    Interval("PT12H", "12Hours", "Cwms"),
    Interval("P1D", "1Day", "Cwms"),
    Interval("P2D", "2Days", "Cwms"),
    Interval("P3D", "3Days", "Cwms"),
    Interval("P4D", "4Days", "Cwms"),
    Interval("P5D", "5Days", "Cwms"),
    Interval("P6D", "6Days", "Cwms"),
    Interval("P7D", "1Week", "Cwms"),
    Interval("P1M", "1Month", "Cwms", 43200),
    Interval("P1Y", "1Year", "Cwms", 525600),
    Interval(
        "PT1M", "1MinuteLocal" if _new_local_regular_names else "~1Minute", "Cwms"
    ),
    Interval(
        "PT2M", "2MinutesLocal" if _new_local_regular_names else "~2Minutes", "Cwms"
    ),
    Interval(
        "PT3M", "3MinutesLocal" if _new_local_regular_names else "~3Minutes", "Cwms"
    ),
    Interval(
        "PT4M", "4MinutesLocal" if _new_local_regular_names else "~4Minutes", "Cwms"
    ),
    Interval(
        "PT5M", "5MinutesLocal" if _new_local_regular_names else "~5Minutes", "Cwms"
    ),
    Interval(
        "PT6M", "6MinutesLocal" if _new_local_regular_names else "~6Minutes", "Cwms"
    ),
    Interval(
        "PT10M", "10MinutesLocal" if _new_local_regular_names else "~10Minutes", "Cwms"
    ),
    Interval(
        "PT12M", "12MinutesLocal" if _new_local_regular_names else "~12Minutes", "Cwms"
    ),
    Interval(
        "PT15M", "15MinutesLocal" if _new_local_regular_names else "~15Minutes", "Cwms"
    ),
    Interval(
        "PT20M", "20MinutesLocal" if _new_local_regular_names else "~20Minutes", "Cwms"
    ),
    Interval(
        "PT30M", "30MinutesLocal" if _new_local_regular_names else "~30Minutes", "Cwms"
    ),
    Interval("PT1H", "1HourLocal" if _new_local_regular_names else "~1Hour", "Cwms"),
    Interval("PT2H", "2HoursLocal" if _new_local_regular_names else "~2Hours", "Cwms"),
    Interval("PT3H", "3HoursLocal" if _new_local_regular_names else "~3Hours", "Cwms"),
    Interval("PT4H", "4HoursLocal" if _new_local_regular_names else "~4Hours", "Cwms"),
    Interval("PT6H", "6HoursLocal" if _new_local_regular_names else "~6Hours", "Cwms"),
    Interval("PT8H", "8HoursLocal" if _new_local_regular_names else "~8Hours", "Cwms"),
    Interval(
        "PT12H", "12HoursLocal" if _new_local_regular_names else "~12Hours", "Cwms"
    ),
    Interval("P1D", "1DayLocal" if _new_local_regular_names else "~1Day", "Cwms"),
    Interval("P2D", "2DaysLocal" if _new_local_regular_names else "~2Days", "Cwms"),
    Interval("P3D", "3DaysLocal" if _new_local_regular_names else "~3Days", "Cwms"),
    Interval("P4D", "4DaysLocal" if _new_local_regular_names else "~4Days", "Cwms"),
    Interval("P5D", "5DaysLocal" if _new_local_regular_names else "~5Days", "Cwms"),
    Interval("P6D", "6DaysLocal" if _new_local_regular_names else "~6Days", "Cwms"),
    Interval("P7D", "1WeekLocal" if _new_local_regular_names else "~1Week", "Cwms"),
    Interval(
        "P1M", "1MonthLocal" if _new_local_regular_names else "~1Month", "Cwms", 43200
    ),
    Interval(
        "P1Y", "1YearLocal" if _new_local_regular_names else "~1Year", "Cwms", 525600
    ),
]

_DSS_INTERVALS = [
    Interval("PT0S", "IR-Day", "Dss"),
    Interval("PT0S", "IR-Month", "Dss"),
    Interval("PT0S", "IR-Year", "Dss"),
    Interval("PT0S", "IR-Decade", "Dss"),
    Interval("PT0S", "IR-Century", "Dss"),
    # Interval("PT0S", "~1Second", "Dss"),
    # Interval("PT0S", "~2Second", "Dss"),
    # Interval("PT0S", "~3Second", "Dss"),
    # Interval("PT0S", "~4Second", "Dss"),
    # Interval("PT0S", "~5Second", "Dss"),
    # Interval("PT0S", "~6Second", "Dss"),
    # Interval("PT0S", "~10Second", "Dss"),
    # Interval("PT0S", "~15Second", "Dss"),
    # Interval("PT0S", "~20Second", "Dss"),
    # Interval("PT0S", "~30Second", "Dss"),
    Interval("PT0S", "~1Minute", "Dss"),
    Interval("PT0S", "~2Minute", "Dss"),
    Interval("PT0S", "~3Minute", "Dss"),
    Interval("PT0S", "~4Minute", "Dss"),
    Interval("PT0S", "~5Minute", "Dss"),
    Interval("PT0S", "~6Minute", "Dss"),
    Interval("PT0S", "~10Minute", "Dss"),
    Interval("PT0S", "~12Minute", "Dss"),
    Interval("PT0S", "~15Minute", "Dss"),
    Interval("PT0S", "~20Minute", "Dss"),
    Interval("PT0S", "~30Minute", "Dss"),
    Interval("PT0S", "~1Hour", "Dss"),
    Interval("PT0S", "~2Hour", "Dss"),
    Interval("PT0S", "~3Hour", "Dss"),
    Interval("PT0S", "~4Hour", "Dss"),
    Interval("PT0S", "~6Hour", "Dss"),
    Interval("PT0S", "~8Hour", "Dss"),
    Interval("PT0S", "~12Hour", "Dss"),
    Interval("PT0S", "~1Day", "Dss"),
    Interval("PT0S", "~2Day", "Dss"),
    Interval("PT0S", "~3Day", "Dss"),
    Interval("PT0S", "~4Day", "Dss"),
    Interval("PT0S", "~5Day", "Dss"),
    Interval("PT0S", "~6Day", "Dss"),
    Interval("PT0S", "~1Week", "Dss"),
    Interval("PT0S", "~1Month", "Dss"),
    Interval("PT0S", "~1Year", "Dss"),
    # Interval("PT1S", "1Second", "Dss"),
    # Interval("PT2S", "2Second", "Dss"),
    # Interval("PT3S", "3Second", "Dss"),
    # Interval("PT4S", "4Second", "Dss"),
    # Interval("PT5S", "5Second", "Dss"),
    # Interval("PT6S", "6Second", "Dss"),
    # Interval("PT10S", "10Second", "Dss"),
    # Interval("PT15S", "15Second", "Dss"),
    # Interval("PT20S", "20Second", "Dss"),
    # Interval("PT30S", "30Second", "Dss"),
    Interval("PT1M", "1Minute", "Dss"),
    Interval("PT2M", "2Minute", "Dss"),
    Interval("PT3M", "3Minute", "Dss"),
    Interval("PT4M", "4Minute", "Dss"),
    Interval("PT5M", "5Minute", "Dss"),
    Interval("PT6M", "6Minute", "Dss"),
    Interval("PT10M", "10Minute", "Dss"),
    Interval("PT12M", "12Minute", "Dss"),
    Interval("PT15M", "15Minute", "Dss"),
    Interval("PT20M", "20Minute", "Dss"),
    Interval("PT30M", "30Minute", "Dss"),
    Interval("PT1H", "1Hour", "Dss"),
    Interval("PT2H", "2Hour", "Dss"),
    Interval("PT3H", "3Hour", "Dss"),
    Interval("PT4H", "4Hour", "Dss"),
    Interval("PT6H", "6Hour", "Dss"),
    Interval("PT8H", "8Hour", "Dss"),
    Interval("PT12H", "12Hour", "Dss"),
    Interval("P1D", "1Day", "Dss"),
    Interval("P2D", "2Day", "Dss"),
    Interval("P3D", "3Day", "Dss"),
    Interval("P4D", "4Day", "Dss"),
    Interval("P5D", "5Day", "Dss"),
    Interval("P6D", "6Day", "Dss"),
    Interval("P7D", "1Week", "Dss"),
    Interval("P1/3M", "Tri-Month", "Dss", 14400),
    Interval("P1/2M", "Semi-Month", "Dss", 21600),
    Interval("P1M", "1Month", "Dss", 43200),
    Interval("P1Y", "1Year", "Dss", 525600),
]
_DSS_BLOCK_SIZES = [
    Interval("P1D", "1Day", "DssBlock"),
    Interval("P1M", "1Month", "DssBlock", 43200),
    Interval("P1Y", "1Year", "DssBlock", 525600),
    Interval("P10Y", "1Decade", "DssBlock", 5256000),
    Interval("P100Y", "1Century", "DssBlock", 52560000),
]
_DSS_BLOCK_SIZE_FOR_INTERVAL = {
    "IR-Day": "1Day",
    "IR-Month": "1Month",
    "IR-Year": "1Year",
    "IR-Decade": "1Decade",
    "IR-Century": "1Century",
    "~1Second": "1Day",
    "~2Second": "1Day",
    "~3Second": "1Day",
    "~4Second": "1Day",
    "~5Second": "1Day",
    "~6Second": "1Day",
    "~10Second": "1Day",
    "~15Second": "1Day",
    "~20Second": "1Day",
    "~30Second": "1Day",
    "~1Minute": "1Day",
    "~2Minute": "1Day",
    "~3Minute": "1Day",
    "~4Minute": "1Day",
    "~5Minute": "1Day",
    "~6Minute": "1Day",
    "~10Minute": "1Day",
    "~12Minute": "1Day",
    "~15Minute": "1Day",
    "~20Minute": "1Day",
    "~30Minute": "1Month",
    "~1Hour": "1Month",
    "~2Hour": "1Month",
    "~3Hour": "1Month",
    "~4Hour": "1Month",
    "~6Hour": "1Year",
    "~8Hour": "1Year",
    "~12Hour": "1Year",
    "~1Day": "1Year",
    "~2Day": "1Year",
    "~3Day": "1Year",
    "~4Day": "1Year",
    "~5Day": "1Year",
    "~6Day": "1Year",
    "~1Week": "1Decade",
    "~1Month": "1Century",
    "~1Year": "1Century",
    "1Second": "1Day",
    "2Second": "1Day",
    "3Second": "1Day",
    "4Second": "1Day",
    "5Second": "1Day",
    "6Second": "1Day",
    "10Second": "1Day",
    "15Second": "1Day",
    "20Second": "1Day",
    "30Second": "1Day",
    "1Minute": "1Day",
    "2Minute": "1Day",
    "3Minute": "1Day",
    "4Minute": "1Day",
    "5Minute": "1Day",
    "6Minute": "1Day",
    "10Minute": "1Day",
    "12Minute": "1Day",
    "15Minute": "1Month",
    "20Minute": "",
    "30Minute": "",
    "1Hour": "1Month",
    "2Hour": "1Month",
    "3Hour": "1Month",
    "4Hour": "1Month",
    "6Hour": "1Month",
    "8Hour": "1Month",
    "12Hour": "1Month",
    "1Day": "1Year",
    "2Day": "1Year",
    "3Day": "1Year",
    "4Day": "1Year",
    "5Day": "1Year",
    "6Day": "1Year",
    "1Week": "1Decade",
    "Tri-Month": "1Decade",
    "Semi-Month": "1Decade",
    "1Month": "1Decade",
    "1Year": "1Century",
}
_DATETIME_INDEX_FREQ = {
    "PT1M": "min",
    "PT2M": "2min",
    "PT3M": "3min",
    "PT4M": "4min",
    "PT5M": "5min",
    "PT6M": "6min",
    "PT10M": "10min",
    "PT12M": "12min",
    "PT15M": "15min",
    "PT20M": "20min",
    "PT30M": "30min",
    "PT1H": "h",
    "PT2H": "2h",
    "PT3H": "3h",
    "PT4H": "4h",
    "PT6H": "6h",
    "PT8H": "8h",
    "PT12H": "12h",
    "P1D": "D",
    "P2D": "2D",
    "P3D": "3D",
    "P4D": "4D",
    "P5D": "5D",
    "P6D": "6D",
    "P7D": "7D",  # "W" is anchored to Sunday
}

for _i in _CWMS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_BLOCK_SIZES:
    Interval.MINUTES[_i.name] = _i.minutes
