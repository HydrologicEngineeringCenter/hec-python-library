"""
Provides standard time durations
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Union
from hec.timespan import TimeSpan
from hec.timespan import TimeSpanException
from hec.interval import Interval


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

    def __init__(self, interval: Interval, bop: bool = False):
        """Initializer used by module"""
        super().__init__(str(interval))
        self._interval = interval
        self._bop = bop

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
    for intvl in Interval.getAllCwms(lambda i: i.name != "Irr")
    for bop in (False, True)
]:
    _DURATIONS[str(_d)] = _d
