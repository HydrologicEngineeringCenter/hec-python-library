"""
Provides time series types and operations
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

import hec.hectime
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
from copy import deepcopy
import pandas as pd
import cwms.types

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
    """
    Holds time series and provides time series operations
    """

    slice_stop_exclusive: bool = True

    @classmethod
    def setSliceStopExclusive(cls, state: bool = True) -> None:
        cls.slice_stop_exclusive = state

    @classmethod
    def setSliceStopInclusive(cls, state: bool = True) -> None:
        cls.slice_stop_exclusive = not state

    def __init__(self, init_from: Any):
        """
        Initializes a new TimeSeries object

        Args:
            init_from (Any): The object to initialize from.
                * **str**: A CWMS time series identifier or HEC-DSS time series pathname.
                    * If CWMS
                        * The following components are set from the identifier:
                            * location (may be in the format &lt;*office*&gt;/&lt;*location*&gt; to set office)
                            * parameter
                            * parameter type
                            * interval
                            * duration
                            * version
                        * The following components are not set:
                            * watershed
                    * If HEC-DSS
                        * The following components are set from the pathname:
                            * A => watershed
                            * B => location
                            * C => parameter
                            * E => interval
                            * F => version
                        * The following compents are not set:
                            * parameter type
                            * duration
                    * The parameter unit is set to the default English unit
                    * No vertical datum information is set for elevation parameter
                * **dict**: A CWMS time series as returned from CDA using cwms.get_timeseries
        """
        self._slice_stop_exclusive = TimeSeries.slice_stop_exclusive
        self._context: str
        self._watershed: Optional[str] = None
        self._location: Location
        self._parameter: Parameter
        self._parameter_type: Optional[ParameterType] = None
        self._interval: Interval
        self._duration: Optional[Duration] = None
        self._version: Optional[str] = None
        self._data: Optional[pd.DataFrame] = None

        if isinstance(init_from, str):
            self.name = init_from
        elif isinstance(init_from, cwms.types.Data):
            self._context = _CWMS
            props = init_from.json
            df = init_from.df
            self.name = props["name"]
            self.location.office = props["office-id"]
            if self.parameter.base_parameter == "Elev":
                self.setParameter(
                    ElevParameter(self.parameter.name, props["vertical-datum-info"])
                )
                self.location.elevation = self.parameter.elevation.magnitude
                self.location.elevation_unit = self.parameter.elevation.specified_unit
                self.location.vertical_datum = self.parameter.native_datum
            else:
                self.setParameter(Parameter(self.parameter.name, props["units"]))
            if df is not None and len(df):
                self._data = init_from.df.copy(deep=True)
                self._data.columns = ["time", "value", "quality"]
                self._data.set_index("time", inplace=True)
        else:
            raise TypeError(type(init_from))

    def __repr__(self) -> str:
        return f"<TimeSeries({self.name}) unit={self.parameter._unit_name} {len(self)} values>"

    def __str__(self) -> str:
        return f"{self.name} {len(self)} vlaues in {self.parameter.unit_name}"

    def __len__(self) -> int:
        return 0 if self._data is None else len(self._data)

    def __getitem__(self, key) -> "TimeSeries":
        other = self.clone(include_data=False)
        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            if isinstance(start, int) or isinstance(stop, int):
                times = self.times
                if isinstance(start, int):
                    start = str(times[start])
                if isinstance(stop, int):
                    stop = str(times[stop])
            if stop is not None:
                if self._slice_stop_exclusive:
                    if isinstance(stop, (datetime, HecTime)):
                        stop = stop - timedelta(seconds=1)
                    else:
                        t = HecTime(hec.hectime.SECOND_GRANULARITY)
                        t.set(stop)
                        stop = str(t - timedelta(seconds=1))
            print(f"start = {start}")
            print(f"stop  = {stop}")
            print(f"step  = {step}")
            other._data = self._data.loc[start:stop:step]
        elif isinstance(key, int):
            keystr = str(self.times[key])
            other._data = self._data.loc[keystr]
        elif isinstance(key, (datetime, HecTime)):
            other._data = self._data.loc[str(HecTime(key)).replace("T", " ")]
        else:
            other._data = self._data.loc[key]
        return other

    def _indexVal(self, offset: int) -> str:
        return str(self.times[offset])

    @property
    def slice_stop_exclusive(self) -> bool:
        """
        Whether the `stop` portion of `[start:stop]` slicing is exclusive for this object.
        * If `True`, the slicing TimeSeries objects follows Python rules, where `stop`
            specifies the lowest index not included.
        * If `False`, the slicing of TimeSeries objects follows pandas.DataFrame rules,
            where `stop` specifies the highest index included.

        The default value is determined by the class state, which defaults to `True`, but
        can be set by calling [setSliceStartExclusive()](#TimeSeries.setSliceStartExclusive) or
        [setSliceStartInclusive()](#TimeSeries.setSliceStartInclusive) before creating a
        TimeSeires object

        Operations:
            Read/Write
        """
        return self._slice_stop_exclusive

    @slice_stop_exclusive.setter
    def slice_stop_exclusive(self, state: bool) -> None:
        self._slice_stop_exclusive = state

    @property
    def name(self) -> str:
        """
        The CWMS time series identifier or HEC-DSS pathname

        Operations:
            Read/Write
        """
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
                        "Expected valid CWMS time series identifier or HEC-DSS time series pathname"
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
        """
        The watershed (DSS A pathname part)

        Operations:
            Read Only
        """
        return self._watershed

    @watershed.setter
    def watershed(self, value: str) -> None:
        self._watershed = value

    @property
    def location(self) -> Location:
        """
        The location object (used in HEC-DSS B pathname part)

        Operations:
            Read Only
        """
        return self._location

    @property
    def parameter(self) -> Parameter:
        """
        The parameter object (used in HEC-DSS C pathname part)

        Operations:
            Read Only
        """
        return self._parameter

    @property
    def parameter_type(self) -> Optional[ParameterType]:
        """
        The parameter type object

        Operations:
            Read Only
        """
        return self._parameter_type

    @property
    def interval(self) -> Interval:
        """
        The interval object (used in HEC-DSS E pathname part)

        Operations:
            Read Only
        """
        return self._interval

    @property
    def duration(self) -> Optional[Duration]:
        """
        The duration object

        Operations:
            Read Only
        """
        return self._duration

    @property
    def version(self) -> Optional[str]:
        """
        The version (HEC-DSS F pathname part)

        Operations:
            Read/Write
        """
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        self._version = value

    @property
    def unit(self) -> str:
        """
        The parameter unit object

        Operations:
            Read Only
        """
        return self._parameter.unit_name

    @property
    def vertical_datum_info(self) -> Optional[ElevParameter._VerticalDatumInfo]:
        """
        The vertical datum info object or None if not set

        Operations:
            Read Only
        """
        if isinstance(self._parameter, ElevParameter):
            return self._parameter.vertical_datum_info
        else:
            return None

    @property
    def vertical_datum_info_xml(self) -> Optional[str]:
        """
        The vertical datum info as an XML string or None if not set

        Operations:
            Read Only
        """
        if (
            isinstance(self._parameter, ElevParameter)
            and self._parameter.vertical_datum_info
        ):
            return self._parameter.vertical_datum_info_xml
        else:
            return None

    @property
    def vertical_datum_info_dict(self) -> Optional[dict[str, Any]]:
        """
        The vertical datum info as a dictionary or None if not set

        Operations:
            Read Only
        """
        if (
            isinstance(self._parameter, ElevParameter)
            and self._parameter.vertical_datum_info
        ):
            return self._parameter.vertical_datum_info_dict
        else:
            return None

    @property
    def data(self) -> Optional[pd.DataFrame]:
        """
        The data (times, values, qualities) as a DataFrame or None if not set

        Operations:
            Read Only
        """
        return self._data

    @property
    def times(self) -> list[Any]:
        """
        The times as a DataFrame or None if not set

        Operations:
            Read Only
        """
        def f(item) :
            ht = HecTime()
            ht.set(item)
            ht.midnight_as_2400 = False
            return str(ht).replace("T", " ")

        return (
            [] if self._data is None else list(map(f, self._data.index.tolist()))
        )

    @property
    def values(self) -> list[float]:
        """
        The values as a DataFrame or None if not set

        Operations:
            Read Only
        """
        return [] if self._data is None else self._data["value"].tolist()

    @property
    def qualities(self) -> list[int]:
        """
        The qualities as a DataFrame or None if not set

        Operations:
            Read Only
        """
        return [] if self._data is None else self._data["quality"].tolist()

    def setLocation(self, value: Union[Location, str]) -> None:
        """
        Sets the location for the time series

        Args:
            value (Union[Location, str]):
                * Location: The Location object to use
                * str: The location name (may be in the format &lt;*office*&gt;/&lt;*location*&gt; to set office)
        """
        if isinstance(value, Location):
            self._location = value
        else:
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

    def setParameter(self, value: Union[Parameter, str]) -> None:
        """
        Sets the parameter for the time series

        Args:
            value (Union[Parameter, str]):
                * Parameter: The Parameter object to use
                * str: The parameter name - the unit will be set to the default English unit
        """
        if isinstance(value, Parameter):
            self._parameter = value
        else:
            self._parameter = Parameter(value, "EN")

    def setParameterType(self, value: Union[ParameterType, str]) -> None:
        """
        Sets the parameter type for the time series

        Args:
            value (Union[ParameterType, str]):
                * ParameterType: The ParameterType object to use
                * str: The parameter type name
        """
        if isinstance(value, ParameterType):
            self._parameter_type = value
        else:
            self._parameter_type = ParameterType(value)

    def setInterval(self, value: Union[Interval, str, int]) -> None:
        """
        Sets the interval for the time series

        Args:
            value (Union[Interval, str]):
                * Interval: The Interval object to use
                * str: The interval name
                * int: The (actual or characteristic) number of minutes for the interval
        """
        if isinstance(value, Interval):
            self._interval = value
        else:
            self._interval = Interval.getCwms(value)

    def setDuration(self, value: Union[Duration, str, int]) -> None:
        """
        Sets the Duration for the time series

        Args:
            value (Union[Duration, str]):
                * Interval: The Duration object to use
                * str: The duration name
                * int: The (actual or characteristic) number of minutes for the duration
        """
        if isinstance(value, Duration):
            self._duration = value
        else:
            self._duration = Duration.forInterval(value)

    def setUnit(self, value: Union[Unit, str]) -> None:
        """
        Sets the parameter unit for the time series

        Args:
            value (Union[Unit, str]):
                * ParameterType: The Unit object to use
                * str: The unit name
        """
        if isinstance(value, Unit):
            if self._parameter.unit.dimensionality != Unit.dimensionality:
                raise TimeSeriesException(
                    f"Cannont set unit of {self._parameter.name} time series to {value}"
                )
            self._parameter._unit = value
            self._parameter._unit_name = eval(
                f"f'{{{value}:{UnitQuantity._default_output_format}}}'"
            )
        else:
            self._parameter.to(value, in_place=True)
        if self._data:
            raise TimeSeriesException("Cannot yet change units of data")

    def setVerticalDatumInfo(self, value: Union[str, dict[str, Any]]) -> None:
        """
        Sets the vertical datum info for the time series

        Args:
            value (Union[str, dict[str, Any]]):
                * str: the vertical datum info as an XML string
                * dict: the vertical datum info as a dictionary

        Raises:
            TimeSeriesException: If the base parameter is not "Elev"
        """
        if self._parameter.base_parameter == "Elev":
            self._parameter = ElevParameter(self._parameter.name, value)
        else:
            raise TimeSeriesException(
                f"Cannot set vertical datum on {self._parameter.name} time series"
            )

    def clone(self, include_data: bool = True) -> "TimeSeries":
        """
        Creates a copy of this object, with or without data

        Args:
            include_data (bool, optional): Specifies whether to include the data in the copy. Defaults to True.

        Returns:
            TimeSeries: The copy of this object
        """
        other = TimeSeries(self.name)
        other._location = deepcopy(self._location)
        other._parameter = deepcopy(self._parameter)
        other._parameter_type = deepcopy(self._parameter_type)
        other._interval = deepcopy(self._interval)
        other._duration = deepcopy(self._duration)
        other._version = self._version
        if include_data:
            other._data = self._data.copy(deep=True)
        return other

    def setValue(self, time: Union[HecTime, datetime, str, int], value: float) -> None:
        key: str
        if isinstance(time, HecTime):
            key = str(time).replace("T", " ")
        elif isinstance(time, datetime):
            key = str(HecTime(time)).replace("T", " ")
        elif isinstance(time, str):
            key = time
        elif isinstance(time, int):
            key = self._indexVal(time)
        else:
            raise TypeError(
                f"Expected HecTime, datetime, str, or int - got {type(time)}"
            )
        self._data.loc[key, "value"] = value

    def setQuality(
        self, time: Union[HecTime, datetime, str, int], quality: Union[Quality, int]
    ) -> None:
        key: str
        if isinstance(time, HecTime):
            key = str(time).replace("T", " ")
        elif isinstance(time, datetime):
            key = str(HecTime(time)).replace("T", " ")
        elif isinstance(time, str):
            key = time
        elif isinstance(time, int):
            key = self._indexVal(time)
        else:
            raise TypeError(
                f"Expected HecTime, datetime, str, or int - got {type(time)}"
            )
        self._data.loc[key, "quality"] = Quality(quality).code

    def setValueQuality(
        self,
        time: Union[HecTime, datetime, str, int],
        value: float,
        quality: Union[Quality, int],
    ) -> None:
        key: str
        if isinstance(time, HecTime):
            key = str(time).replace("T", " ")
        elif isinstance(time, datetime):
            key = str(HecTime(time)).replace("T", " ")
        elif isinstance(time, str):
            key = time
        elif isinstance(time, int):
            key = self._indexVal(time)
        else:
            raise TypeError(
                f"Expected HecTime, datetime, str, or int - got {type(time)}"
            )
        self._data.loc[key, "value"] = value
        self._data.loc[key, "quality"] = Quality(quality).code
