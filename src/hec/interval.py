"""
Provides standard time intervals
"""

import os
import sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Callable, Optional, Union, cast

from hec.timespan import TimeSpan, TimeSpanException


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

    @staticmethod
    def _getAny(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
    ) -> Optional["Interval"]:
        all = Interval._getAll(intervals, matcher)
        return all[0] if all else None

    @staticmethod
    def _getAnyName(
        intervals: list["Interval"],
        matcher: Callable[["Interval"], bool],
    ) -> Optional[str]:
        all = Interval._getAllNames(intervals, matcher)
        return all[0] if all else None

    @staticmethod
    def _getAll(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
    ) -> list["Interval"]:
        return [i for i in intervals if matcher(i)] if matcher else intervals[:]

    @staticmethod
    def _getAllNames(
        intervals: list["Interval"],
        matcher: Optional[Callable[["Interval"], bool]] = None,
    ) -> list[str]:
        return (
            [i.name for i in intervals if matcher(i)]
            if matcher
            else [i.name for i in intervals]
        )

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
            intvl = Interval.getAnyCwms(lambda i: i.name == key.title())
            if intvl is None:
                raise IntervalException(f'No CWMS interval found with name = "{key}"')
        elif isinstance(key, int):
            intvl = Interval.getAnyCwms(lambda i: i.minutes == key)
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
            intvl = Interval.getAnyDss(lambda i: i.name == key.title())
            if intvl is None:
                raise IntervalException(
                    f'No HEC-DSS interval found with name = "{key}"'
                )
        elif isinstance(key, int):
            intvl = Interval.getAnyDss(lambda i: i.minutes == key)
            if intvl is None:
                raise IntervalException(
                    f"No HEC-DSS interval found with minutes = {key}"
                )
        else:
            raise TypeError(f"Expected string or integer, got {key.__class__.__name__}")
        return intvl

    @staticmethod
    def getAny(matcher: Callable[["Interval"], bool]) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in any context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._getAny(intervals, matcher)
            if i:
                break
        return i

    @staticmethod
    def getAnyName(matcher: Callable[["Interval"], bool]) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the any context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        for intervals in (_CWMS_INTERVALS, _DSS_INTERVALS, _DSS_BLOCK_SIZES):
            i = Interval._getAnyName(intervals, matcher)
            if i:
                break
        return i

    @staticmethod
    def getAll(
        matcher: Optional[Callable[["Interval"], bool]] = None
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
            _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES, matcher
        )

    @staticmethod
    def getAllNames(
        matcher: Optional[Callable[["Interval"], bool]] = None
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
        return Interval._getAllNames(
            _CWMS_INTERVALS + _DSS_INTERVALS + _DSS_BLOCK_SIZES, matcher
        )

    @staticmethod
    def getAnyCwms(matcher: Callable[["Interval"], bool]) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_CWMS_INTERVALS, matcher)

    @staticmethod
    def getAnyCwmsName(matcher: Callable[["Interval"], bool]) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the CWMS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_CWMS_INTERVALS, matcher)

    @staticmethod
    def getAllCwms(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_CWMS_INTERVALS, matcher)

    @staticmethod
    def getAllCwmsNames(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._getAllNames(_CWMS_INTERVALS, matcher)

    @staticmethod
    def getAnyDss(matcher: Callable[["Interval"], bool]) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_DSS_INTERVALS, matcher)

    @staticmethod
    def getAnyDssName(matcher: Callable[["Interval"], bool]) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_DSS_INTERVALS, matcher)

    @staticmethod
    def getAllDss(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_DSS_INTERVALS, matcher)

    @staticmethod
    def getAllDssNames(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._getAllNames(_DSS_INTERVALS, matcher)

    @staticmethod
    def getAnyDssBlock(matcher: Callable[["Interval"], bool]) -> Optional["Interval"]:
        """
        Retuns a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[Interval]: A matched `Interval` object or None
        """
        return Interval._getAny(_DSS_BLOCK_SIZES, matcher)

    @staticmethod
    def getAnyDssBlockName(matcher: Callable[["Interval"], bool]) -> Optional[str]:
        """
        Retuns the name of a matched `Interval` object in the DSS block size context, or None if there is no such object

        Args:
            matcher (Callable[[Interval], bool]): A function that returns True or False when passed an `Interval` object parameter.<br>
                Examples:
                - `lambda i : i.isIrregular`
                - `lambda i : i.minutes < 60`
                - `lambda i : i.name.find("Week") != -1`

        Returns:
            Optional[str]: The name of a matched `Interval` object or None
        """
        return Interval._getAnyName(_DSS_BLOCK_SIZES, matcher)

    @staticmethod
    def getAllDssBlock(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[Interval]: A list of matched `Interval` objects (may be empty)
        """
        return Interval._getAll(_DSS_BLOCK_SIZES, matcher)

    @staticmethod
    def getAllDssBlockNames(
        matcher: Optional[Callable[["Interval"], bool]] = None
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

        Returns:
            List[str]: A list of names of matched `Interval` objects (may be empty)
        """
        return Interval._getAllNames(_DSS_BLOCK_SIZES, matcher)

    def __init__(self, timespan: str, name: str, minutes: Optional[int] = None):
        """Initializer used by module"""
        super().__init__(timespan)
        self._name = name
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
    def isRegular(self) -> bool:
        """
        Whether this object represents a regular interval

        Operations:
            Read-only
        """
        return self.values != [0, 0, 0, 0, 0, 0]

    @property
    def isIrregular(self) -> bool:
        """
        Whether this object represents an irregular interval

        Operations:
            Read-only
        """
        return self.values == [0, 0, 0, 0, 0, 0]


_CWMS_INTERVALS = [
    Interval("PT0S", "0"),
    Interval("PT0S", "Irr"),
    Interval("PT1M", "1Minute"),
    Interval("PT2M", "2Minutes"),
    Interval("PT3M", "3Minutes"),
    Interval("PT4M", "4Minutes"),
    Interval("PT5M", "5Minutes"),
    Interval("PT6M", "6Minutes"),
    Interval("PT10M", "10Minutes"),
    Interval("PT12M", "12Minutes"),
    Interval("PT15M", "15Minutes"),
    Interval("PT20M", "20Minutes"),
    Interval("PT30M", "30Minutes"),
    Interval("PT1H", "1Hour"),
    Interval("PT2H", "2Hours"),
    Interval("PT3H", "3Hours"),
    Interval("PT4H", "4Hours"),
    Interval("PT6H", "6Hours"),
    Interval("PT8H", "8Hours"),
    Interval("PT12H", "12Hours"),
    Interval("P1D", "1Day"),
    Interval("P2D", "2Days"),
    Interval("P3D", "3Days"),
    Interval("P4D", "4Days"),
    Interval("P5D", "5Days"),
    Interval("P6D", "6Days"),
    Interval("P7D", "1Week"),
    Interval("P1M", "1Month", 43200),
    Interval("P1Y", "1Year", 525600),
]
_DSS_INTERVALS = [
    Interval("PT0S", "Ir-Day"),
    Interval("PT0S", "Ir-Month"),
    Interval("PT0S", "Ir-Year"),
    Interval("PT0S", "Ir-Decade"),
    Interval("PT0S", "Ir-Century"),
    Interval("PT1M", "1Minute"),
    Interval("PT2M", "2Minute"),
    Interval("PT3M", "3Minute"),
    Interval("PT4M", "4Minute"),
    Interval("PT5M", "5Minute"),
    Interval("PT6M", "6Minute"),
    Interval("PT10M", "10Minute"),
    Interval("PT12M", "12Minute"),
    Interval("PT15M", "15Minute"),
    Interval("PT20M", "20Minute"),
    Interval("PT30M", "30Minute"),
    Interval("PT1H", "1Hour"),
    Interval("PT2H", "2Hour"),
    Interval("PT3H", "3Hour"),
    Interval("PT4H", "4Hour"),
    Interval("PT6H", "6Hour"),
    Interval("PT8H", "8Hour"),
    Interval("PT12H", "12Hour"),
    Interval("P1D", "1Day"),
    Interval("P2D", "2Day"),
    Interval("P3D", "3Day"),
    Interval("P4D", "4Day"),
    Interval("P5D", "5Day"),
    Interval("P6D", "6Day"),
    Interval("P7D", "1Week"),
    Interval("P1/3M", "Tri-Month", 14400),
    Interval("P1/2M", "Semi-Month", 21600),
    Interval("P1M", "1Month", 43200),
    Interval("P1Y", "1Year", 525600),
]
_DSS_BLOCK_SIZES = [
    Interval("P1M", "1Month", 43200),
    Interval("P1Y", "1Year", 525600),
    Interval("P10Y", "1Decade", 5256000),
    Interval("P100Y", "1Century", 52560000),
]

for _i in _CWMS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_INTERVALS:
    Interval.MINUTES[_i.name] = _i.minutes
for _i in _DSS_BLOCK_SIZES:
    Interval.MINUTES[_i.name] = _i.minutes
