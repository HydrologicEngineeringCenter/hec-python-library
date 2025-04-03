"""
Provides standard time intervals
"""

import os
import sys
from datetime import timedelta

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Any, Callable, Optional, Union, cast

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
    - <code>getAny<em>Context</em>()</code>
    - <code>getAny<em>Context</em>Name()</code>
    - <code>getAll<em>Context</em>()</code>
    - <code>getAll<em>Context</em>Names()</code>

    Where *Context* is `Cwms`, `Dss`, or `DssBlock`.

    There are similar static methods that retrieve Interval objects or their names from all contexts:
    - <code>getAny()</code>
    - <code>getAnyName()</code>
    - <code>getAll()</code>
    - <code>getAllNames()</code>
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
    <tr><td>Ir-Century</td><td>0</td><td>DSS</td></tr>
    <tr><td>Ir-Day</td><td>0</td><td>DSS</td></tr>
    <tr><td>Ir-Decade</td><td>0</td><td>DSS</td></tr>
    <tr><td>Ir-Month</td><td>0</td><td>DSS</td></tr>
    <tr><td>Ir-Year</td><td>0</td><td>DSS</td></tr>
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

    @staticmethod
    def setDefaultExceptionOnNotFound(state: bool) -> None:
        """
        Sets the default behavior if any of the get... methods do not find an Interval object to return.

        Args:
            state (bool): Whether to raise an exception if no Interval is found (True) or return None (False)
        """
        Interval._default_exception_on_not_found = state

    @staticmethod
    def getDefaultExceptionOnNotFound() -> bool:
        """
        Retrieves the default behavior if any of the get... methods do not find an Interval object to return.

        Returns:
            bool: True if the default behavior is to raise an exception when no Interval is found or False
                if None is returned when no Interval is found
        """
        return Interval._default_exception_on_not_found

    @staticmethod
    def _getAny(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional["Interval"]:
        all = Interval._getAll(intervals, matcher)
        if all:
            return all[0]
        else:
            raise_exc = (
                exceptionOnNotFound
                if exceptionOnNotFound is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                print(exceptionOnNotFound)
                print(Interval._default_exception_on_not_found)
                raise IntervalException("No such Interval")
            else:
                return None

    @staticmethod
    def _getAnyName(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional[str]:
        all = Interval._getAllNames(intervals, matcher)
        if all:
            return all[0]
        else:
            raise_exc = (
                exceptionOnNotFound
                if exceptionOnNotFound is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return None

    @staticmethod
    def _getAll(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list["Interval"]:
        all = [i for i in intervals if matcher(i)] if matcher else intervals[:]
        if all:
            return all
        else:
            raise_exc = (
                exceptionOnNotFound
                if exceptionOnNotFound is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return all

    @staticmethod
    def _getAllNames(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
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
                exceptionOnNotFound
                if exceptionOnNotFound is not None
                else Interval._default_exception_on_not_found
            )
            if raise_exc:
                raise IntervalException("No such Interval")
            else:
                return all

    @staticmethod
    def getCwms(key: Union[str, int]) -> "Interval":
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
            intvl = Interval.getAnyCwms(lambda i: i.name == key.title(), False)
            if intvl is None:
                raise IntervalException(f'No CWMS interval found with name = "{key}"')
        elif isinstance(key, int):
            intvl = Interval.getAnyCwms(lambda i: i.minutes == key, False)
            if intvl is None:
                raise IntervalException(f"No CWMS interval found with minutes = {key}")
        else:
            raise TypeError(f"Expected string or integer, got {key.__class__.__name__}")
        return intvl

    @staticmethod
    def getDss(key: Union[str, int]) -> "Interval":
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
            intvl = Interval.getAnyDss(lambda i: i.name == key.title(), False)
            if intvl is None:
                raise IntervalException(
                    f'No HEC-DSS interval found with name = "{key}"'
                )
        elif isinstance(key, int):
            intvl = Interval.getAnyDss(lambda i: i.minutes == key, False)
            if intvl is None:
                raise IntervalException(
                    f"No HEC-DSS interval found with minutes = {key}"
                )
        else:
            raise TypeError(f"Expected string or integer, got {key.__class__.__name__}")
        return intvl

    @staticmethod
    def getAny(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in any context

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._getAny(intervals, matcher, exceptionOnNotFound)
            if i:
                break
        return i

    @staticmethod
    def getAnyName(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the any context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._getAnyName(intervals, matcher, exceptionOnNotFound)
            if i:
                break
        return i

    @staticmethod
    def getAll(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the any context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in all contexts are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(
            _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES,
            matcher,
            exceptionOnNotFound,
        )

    @staticmethod
    def getAllNames(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the any context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in all contexts are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return list(
            dict.fromkeys(
                Interval._getAllNames(
                    _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES,
                    matcher,
                    exceptionOnNotFound,
                )
            )
        )

    @staticmethod
    def getAnyCwms(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_CWMS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAnyCwmsName(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_CWMS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllCwms(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the CWMS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_CWMS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllCwmsNames(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the CWMS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return list(
            dict.fromkeys(
                Interval._getAllNames(_CWMS_INTERVALS, matcher, exceptionOnNotFound)
            )
        )

    @staticmethod
    def getAnyDss(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_DSS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAnyDssName(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_DSS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllDss(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the DSS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_DSS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllDssNames(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the DSS context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._getAllNames(_DSS_INTERVALS, matcher, exceptionOnNotFound)

    @staticmethod
    def getAnyDssBlock(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_DSS_BLOCK_SIZES, matcher, exceptionOnNotFound)

    @staticmethod
    def getAnyDssBlockName(
        matcher: Callable[["Interval"], bool],
        exceptionOnNotFound: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_DSS_BLOCK_SIZES, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllDssBlock(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list["Interval"]:
        """
        Retuns list of matched `Interval` objects in the DSS block size context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_DSS_BLOCK_SIZES, matcher, exceptionOnNotFound)

    @staticmethod
    def getAllDssBlockNames(
        matcher: Optional[Callable[["Interval"], bool]] = None,
        exceptionOnNotFound: Optional[bool] = None,
    ) -> list[str]:
        """
        Retuns list of names of matched `Interval` objects in the DSS block size context

        Args:
            matcher (Optional[Callable[[Interval], bool]]): A function that returns True or False when passed an `Interval` object parameter. Defaults to None.
                If None, all `Interval` objects in the context are matched.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`
            exceptionOnNotFound (bool): Specifies whether to raise an exception if no Intervals are found. If None, the default
                behavior is used. Optional. Defaults to None. See [setDefaultExceptionOnNotFound](#Interval.setDefaultExceptionOnNotFound) and
                [getDefaultExceptionOnNotFound](#Interval.getDefaultExceptionOnNotFound)

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._getAllNames(_DSS_BLOCK_SIZES, matcher, exceptionOnNotFound)

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
            print(self.values)
            raise IntervalException(
                "Only one of years, months, days, hours, and minutes is allowed to be non-zero"
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
                    Interval.getAnyDss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.getAnyCwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.getAnyDssBlock(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __iadd__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

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
                    Interval.getAnyDss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.getAnyCwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.getAnyDssBlock(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __isub__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

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
                    Interval.getAnyDss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.getAnyCwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.getAnyDssBlock(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            else:
                return NotImplemented
        else:
            return NotImplemented

    def __imul__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Interval object")

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
                    Interval.getAnyDss(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _CWMS_INTERVALS:
                return cast(
                    Interval,
                    Interval.getAnyCwms(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
                    ),
                )
            elif self in _DSS_BLOCK_SIZES:
                return cast(
                    Interval,
                    Interval.getAnyDssBlock(
                        lambda i: i.minutes == minutes and i.is_regular,
                        exceptionOnNotFound=True,
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

    def __repr__(self) -> str:
        try:
            self.total_seconds()
            return f'Interval("{super().__str__()}", "{self._name}")'
        except:
            return f'Interval("{super().__str__()}", "{self._name}", {self.minutes})'

    def __str__(self) -> str:
        return super().__str__()

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

    @property
    def context(self) -> str:
        """
        The context of this object ("Cwms", "Dss", or "DssBlock")

        Operations:
            Read-only
        """
        return self._context

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
    def is_any_regular(self) -> bool:
        """
        Whether this object represents a regular or local regular interval

        Operations:
            Read-only
        """
        return self.is_regular or self.is_local_regular

    @property
    def is_irregular(self) -> bool:
        """
        Whether this object represents a normal irregular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0] and self.name[0] != "~"

    @property
    def is_pseudo_regular(self) -> bool:
        """
        Whether this object represents a pseudo-regular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0] and self.name[0] == "~"

    @property
    def is_any_irregular(self) -> bool:
        """
        Whether this object represents a normal irregular or pseudo-regular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0]


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
    Interval("PT0S", "Ir-Day", "Dss"),
    Interval("PT0S", "Ir-Month", "Dss"),
    Interval("PT0S", "Ir-Year", "Dss"),
    Interval("PT0S", "Ir-Decade", "Dss"),
    Interval("PT0S", "Ir-Century", "Dss"),
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
    Interval("P1M", "1Month", "DssBlock", 43200),
    Interval("P1Y", "1Year", "DssBlock", 525600),
    Interval("P10Y", "1Decade", "DssBlock", 5256000),
    Interval("P100Y", "1Century", "DssBlock", 52560000),
]

for _i in _CWMS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_BLOCK_SIZES:
    Interval.MINUTES[_i.name] = _i.minutes
