"""
Provides time series types and operations
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from hec.location import Location
from hec.parameter import Parameter
from hec.parameter import ElevParameter
from hec.parameter import ParameterType
from hec.interval import Interval
from hec.duration import Duration
from hec.hectime import HecTime
from hec.unit import UnitQuantity
from hec.quality import Quality
import hec.unit
from typing import cast
from typing import Any
from typing import Optional
from typing import Union
from datetime import datetime
from datetime import timedelta
from pint import Unit
import pandas as pd
import traceback

_CWMS = "CWMS"
_DSS = "DSS"


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


class TimeSeries:

    def __init__(self, value: Any):
        self._context: str
        self._watershed: Optional[str] = None
        self._location: Location
        self._parameter: Parameter
        self._parameter_type: Optional[ParameterType] = None
        self._interval: Interval
        self._duration: Optional[Duration] = None
        self._version: Optional[str] = None
        self._data: Optional[pd.DataFrame] = None

        if isinstance(value, str):
            self.name = value

    @property
    def name(self) -> str:
        parts = []
        if self._context == _CWMS:
            parts.append(str(self._location))
            parts.append(self._parameter.name)
            parts.append(cast(ParameterType, self._parameter_type).getCwmsName())
            parts.append(self._interval.name)
            parts.append(cast(Duration, self._duration).name)
            parts.append(cast(str, self._version))
            return ".".join(parts)
        elif self._context == _DSS:
            parts.append("")
            parts.append("")
            parts.append(self._location.name)
            parts.append(self._parameter.name)
            parts.append("")
            parts.append(self._interval.name)
            parts.append(self._version if self._version else "")
            parts.append("")
            return "/".join(parts)
        else:
            raise TimeSeriesException(f"Invalid context: {self._context}")

    @name.setter
    def name(self, value: str) -> None:
        try:
            parts = value.split(".")
            if len(parts) == 6:
                self._context = _CWMS
                self.setLocation(parts[0])
                self.setParameter(parts[1])
                self.setParameterType(parts[2])
                self.setInterval(parts[3])
                self.setDuration(parts[4])
                self.version = parts[5]
            else:
                parts = value.split("/")
                if len(parts) == 8:
                    A, B, C, E, F = 1, 2, 3, 5, 6
                    self._context = _DSS
                    self.watershed = parts[A]
                    self.setLocation(parts[B])
                    self.setParameter(parts[C])
                    self.setInterval(parts[E])
                    self.version = parts[F]
                else:
                    raise TimeSeriesException(
                        "Expected valid CWMS TSID or DSS TS Pathname"
                    )
            if not self._location:
                raise TimeSeriesException("Location must be specified")
            if not self._parameter:
                raise TimeSeriesException("Parameter must be specified")
            if not self._parameter_type and self._context == _CWMS:
                raise TimeSeriesException("Parameter type must be specified")
            if not self._interval:
                raise TimeSeriesException("Interval must be specified")
            if not self._duration and self._context == _CWMS:
                raise TimeSeriesException("Duration must be specified")
            if not self._version and self._context == _CWMS:
                raise TimeSeriesException("Version must be specified")

        except Exception as e:
            raise TimeSeriesException(
                f"Invalid time series name: '{value}':\n{traceback.format_exc()}"
            )

    @property
    def watershed(self) -> Optional[str]:
        return self._watershed

    @watershed.setter
    def watershed(self, value: str) -> None:
        if isinstance(value, str):
            self._watershed = value
        else:
            raise TypeError

    @property
    def location(self) -> Location:
        return self._location

    @property
    def parameter(self) -> Parameter:
        return self._parameter

    @property
    def parameter_type(self) -> Optional[ParameterType]:
        return self._parameter_type

    @property
    def interval(self) -> Interval:
        return self._interval

    @property
    def duration(self) -> Optional[Duration]:
        return self._duration

    @property
    def version(self) -> Optional[str]:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        if isinstance(value, str):
            self._version = value
        else:
            raise TypeError

    @property
    def unit(self) -> str:
        return self._parameter.unit_name

    @property
    def vertical_datum_info(self) -> Optional[ElevParameter._VerticalDatumInfo]:
        if isinstance(self._parameter, ElevParameter):
            return self._parameter.vertical_datum_info
        else:
            return None

    @property
    def vertical_datum_info_xml(self) -> Optional[str]:
        if (
            isinstance(self._parameter, ElevParameter)
            and self._parameter.vertical_datum_info
        ):
            return self._parameter.vertical_datum_info_xml
        else:
            return None

    @property
    def vertical_datum_info_dict(self) -> Optional[dict[str, Any]]:
        if (
            isinstance(self._parameter, ElevParameter)
            and self._parameter.vertical_datum_info
        ):
            return self._parameter.vertical_datum_info_dict
        else:
            return None

    def setLocation(self, value: Union[Location, str]) -> None:
        if isinstance(value, Location):
            self._location = value
        elif isinstance(value, str):
            if self._context == _CWMS:
                try:
                    office, location = value.split("/")
                    self._location = Location(location, office)
                except:
                    self._location = Location(value)
            elif self._context == _DSS:
                self._location = Location(value)
            else:
                raise TimeSeriesException(f"Invalid context: {self._context}")
        else:
            raise TypeError

    def setParameter(self, value: Union[Parameter, str]) -> None:
        if isinstance(value, Parameter):
            self._parameter = value
        elif isinstance(value, str):
            self._parameter = Parameter(value, "EN")
        else:
            raise TypeError

    def setParameterType(self, value: Union[ParameterType, str]) -> None:
        if isinstance(value, ParameterType):
            self._parameter_type = value
        elif isinstance(value, str):
            self._parameter_type = ParameterType(value)
        else:
            raise TypeError

    def setInterval(self, value: Union[Interval, str]) -> None:
        if isinstance(value, Interval):
            self._interval = value
        elif isinstance(value, str):
            self._interval = Interval.getCwms(value)
        else:
            raise TypeError

    def setDuration(self, value: Union[Duration, str]) -> None:
        if isinstance(value, Duration):
            self._duration = value
        elif isinstance(value, str):
            self._duration = Duration.forInterval(value)
        else:
            raise TypeError

    def setUnit(self, value: Union[Unit, str]) -> None:
        if isinstance(value, Unit):
            if self._parameter.unit.dimensionality != Unit.dimensionality:
                raise TimeSeriesException(
                    f"Cannont set unit of {self._parameter.name} time series to {value}"
                )
            self._parameter._unit = value
            self._parameter._unit_name = eval(
                f"f'{{{value}:{UnitQuantity._default_output_format}}}'"
            )
        elif isinstance(value, str):
            self._parameter.to(value, in_place=True)
        if self._data:
            raise TimeSeriesException("Cannot yet change units of data")

    def setVerticalDatumInfo(
        self, value: Union[ElevParameter._VerticalDatumInfo, dict[str, Any], str]
    ) -> None:
        if self._parameter.base_parameter == "Elev":
            if isinstance(value, ElevParameter._VerticalDatumInfo):
                self._parameter = ElevParameter(self._parameter.name, value.to_dict())
            else:
                self._parameter = ElevParameter(self._parameter.name, value)
        else:
            raise TimeSeriesException(
                f"Cannot set vertical datum on {self._parameter.name} time series"
            )
