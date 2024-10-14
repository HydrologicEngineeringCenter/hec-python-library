"""
Provides time series types and operations
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Any
from typing import Union
from datetime import datetime
from hec.location import Location
from hec.parameter import Parameter
from hec.parameter import ElevParameter
from hec.parameter import ParameterType
from hec.interval import Interval
from hec.duration import Duration
from hec.hectime import HecTime
from hec.unit import UnitQuantity
from hec.quality import Quality


class TimeSeriesException(Exception):
    """
    Exception specific to time series operations
    """

    pass


class TimeSeriesValue:
    """
    Holds a single time series value
    """

    def __init__(
        self,
        time: Any,
        value: Any,
        quality: Union[Quality, int] = 0,
    ):
        """
        Initializes a TimeSeriesValue object

        Args:
            time (Any): The time. Must be an HecTime object or [convertible to an HecTime object](./hectime.html#HecTime.__init__)
            value (Any): The value. Must be a UnitQuantity object or [convertible to a UnitQuantity](./unit.html#UnitQuantity.__init__) object
            quality (Union[Quality, int], optional): The quality code. Must be a Quality object or a valid quality integer. Defaults to 0.
        """
        self._time = time if isinstance(time, HecTime) else HecTime(time)
        self._value = value if isinstance(value, UnitQuantity) else UnitQuantity(value)
        self._quality = quality if isinstance(quality, Quality) else Quality(quality)

    @property
    def time(self) -> HecTime:
        """
        The time

        Operations:
            Read-Write
        """
        return self._time

    @time.setter
    def time(self, time: Any) -> None:
        self._time = time if isinstance(time, HecTime) else HecTime(time)

    @property
    def value(self) -> UnitQuantity:
        """
        The value

        Operations:
            Read-Write
        """
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value if isinstance(value, UnitQuantity) else UnitQuantity(value)

    @property
    def quality(self) -> Quality:
        """
        The Quality

        Operations:
            Read-Write
        """
        return self._quality

    @quality.setter
    def quality(self, quality: Union[Quality, int]) -> None:
        self._quality = quality if isinstance(quality, Quality) else Quality(quality)

    def __repr__(self) -> str:
        return f"TimeSeriesValue({repr(self._time)}, {repr(self._value)}, {repr(self._quality)})"

    def __str__(self) -> str:
        return f"({str(self._time)}, {str(self.value)}, {str(self._quality)})"
