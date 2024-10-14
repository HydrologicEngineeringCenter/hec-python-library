"""
Provides standard time durations
"""

import os
import sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from datetime import timedelta
from typing import Union, cast

from hec.interval import Interval
from hec.timespan import TimeSpan, TimeSpanException


class DurationException(TimeSpanException):
    """
    Exception specific to Duration operations
    """

    pass


class Duration(TimeSpan):
    """
    Class to hold information about the durations represented by time series values.

    Durations are a restriction of the TimeSpan base class that also hold extra information.
    - **Restriction:** At most one of `years`, `months`, `days`, `hours`, and `minutes` can be non-zero, and `seconds` must be zero.
    - **Extension:**
        - Each duration has a name
        - Each duration is a Beginning of Period (BOP) or End of Period (EOP) duration. Normally values
            represent the state at the end of duration (e.g, the elevation or flow at the end of an hour or day).
            EOP Duration objects are returned unless otherwise specified.

    Durations should not need to be created by the user, as durations for all CWMS intervals are created
    during module initialization.
    """

    @staticmethod
    def forInterval(
        interval: Union[Interval, str, int], bop: bool = False
    ) -> "Duration":
        """
        Returns a Duration object for a specified interval

        Args:
            interval (Union[Interval, str, int]): A standard CWMS Interval object, or the name or
                (actual or characteristic) minutes of a standard CWMS interval
            bop (bool, optional): Specifies whether to return a Beginning of Period Duration object.
                Defaults to False.

        Raises:
            TypeError: If the first argument is not an Interval, string, or integer
            DurationException: If the first argument a non-standard name or minutes or
                no such Duration object exists

        Returns:
            Duration: The Duration object matching the specified interval and bop setting.
        """
        if isinstance(interval, str):
            intvl = Interval.getAnyCwms(lambda i: i.name == interval)
        elif isinstance(interval, int):
            intvl = Interval.getAnyCwms(lambda i: i.minutes == interval)
        elif isinstance(interval, Interval):
            intvl = interval
        else:
            raise TypeError(
                f"Expected Interval, str, or int, got {interval.__class__.__name__}"
            )
        if not intvl:
            raise DurationException(
                f"Cannot create Duration from invalid Interval: {interval}"
            )
        if intvl.minutes == 0:
            key = str(intvl)
        else:
            key = str(intvl) + (":BOP" if bop else ":EOP")
        try:
            return _DURATIONS[key]
        except KeyError:
            raise DurationException(f"No such duration: {intvl}, bop={bop}")

    def __init__(self, interval: Union[Interval, str], bop: bool = False):
        """Initializer used by module"""
        if isinstance(interval, str):
            intvl = Interval.getAny(lambda i: i.name == interval)
            if intvl is None:
                raise DurationException(f"Cannot find Interval with name '{interval}'")
        else:
            intvl = interval
        super().__init__(str(intvl))
        self._interval = intvl
        self._bop = bop

    def __add__(self, other: object) -> "Duration":
        if isinstance(other, (TimeSpan, timedelta)):
            minutes = (self.total_seconds() + other.total_seconds()) // 60
            return Duration.forInterval(
                cast(
                    Interval,
                    Interval.getAny(
                        lambda i: i.minutes == minutes and i.is_regular, True
                    ),
                ),
                self.isBop,
            )
        else:
            return NotImplemented

    def __iadd__(self, other: object) -> "Interval":
        raise NotImplementedError("Cannot modify an existing Duration object")

    def __radd__(self, other: timedelta) -> Union[TimeSpan, timedelta]:
        if isinstance(other, TimeSpan):
            return TimeSpan(seconds=other.total_seconds() + self.total_seconds())
        elif isinstance(other, timedelta):
            return timedelta(seconds=other.total_seconds() + self.total_seconds())
        else:
            return NotImplemented

    def __sub__(self, other: object) -> "Duration":
        if isinstance(other, (TimeSpan, timedelta)):
            minutes = (self.total_seconds() - other.total_seconds()) // 60
            return Duration.forInterval(
                cast(
                    Interval,
                    Interval.getAny(
                        lambda i: i.minutes == minutes and i.is_regular, True
                    ),
                ),
                self.isBop,
            )
        else:
            return NotImplemented

    def __isub__(self, other: object) -> "Duration":
        raise NotImplementedError("Cannot modify an existing Duration object")

    def __rsub__(self, other: object) -> Union[TimeSpan, timedelta]:
        if isinstance(other, TimeSpan):
            return TimeSpan(seconds=other.total_seconds() - self.total_seconds())
        elif isinstance(other, timedelta):
            return timedelta(seconds=other.total_seconds() - self.total_seconds())
        return NotImplemented

    def __mul__(self, other: object) -> "Duration":
        if isinstance(other, (int, float)):
            minutes = int((self.total_seconds() * other) // 60)
            return Duration.forInterval(
                cast(
                    Interval,
                    Interval.getAny(
                        lambda i: i.minutes == minutes and i.is_regular, True
                    ),
                ),
                self.isBop,
            )
        else:
            return NotImplemented

    def __imul__(self, other: object) -> "Duration":
        raise NotImplementedError("Cannot modify an existing Duration object")

    def __rmul__(self, other: object) -> "TimeSpan":
        if isinstance(other, (int, float)):
            minutes = int((self.total_seconds() * other) // 60)
            return Duration.forInterval(
                cast(
                    Interval,
                    Interval.getAny(
                        lambda i: i.minutes == minutes and i.is_regular, True
                    ),
                ),
                self.isBop,
            )
        else:
            return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Duration):
            return self.name == other.name
        return False

    def __repr__(self) -> str:
        if self.minutes == 0:
            return f"Duration({repr(self._interval)})"
        else:
            return f"Duration({repr(self._interval)}, bop={self._bop})"

    def __str__(self) -> str:
        if self.minutes == 0:
            return super().__str__()
        else:
            return super().__str__() + (":BOP" if self._bop else ":EOP")

    @property
    def minutes(self) -> int:
        """
        The minutes (actual or characteristic) of this object

        Operations:
            Read-only
        """
        return self._interval.minutes

    @property
    def name(self) -> str:
        """
        The name of this object

        Operations:
            Read-only
        """
        return self._interval.name + ("BOP" if self.minutes > 0 and self._bop else "")

    @property
    def isBop(self) -> bool:
        """
        Whether this object is a Beginning of Period Duration

        Operations:
            Read-only
        """
        if self.minutes == 0:
            return True
        return self._bop

    @property
    def isEop(self) -> bool:
        """
        Whether this object is an End of Period Duration

        Operations:
            Read-only
        """
        if self.minutes == 0:
            return True
        return not self._bop


_DURATIONS = {}
for _d in [
    Duration(intvl, bop)
    for intvl in Interval.getAllCwms(
        lambda i: i.name != "Irr" and not i.name.startswith("~")
    )
    for bop in (False, True)
]:
    _DURATIONS[str(_d)] = _d
