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
from zoneinfo import ZoneInfo
from pint import Unit
from copy import deepcopy
import pandas as pd
import cwms.types  # type: ignore
import warnings
import tzlocal

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
    Holds time series and provides time series operations.

    ### Structure
    TimeSeries objects contain the following properties
    * `watershed` (Optional): A string that holds the the DSS A pathname part. Unused in CWMS contexts.
    * `location` (Required): A [Location](./location.html#Location) object. Its `name` property is used
        for the CWMS location identifier or DSS B pathname part.
    * `parameter` (Required): A [Parameter](./parameter.html#Parameter) object. May be an [ElevParameter](./parameter.html#ElevParameter)
        if the base parameter is "Elev", but only if there is vertical datum info. Its `name` property is
        used for the CWMS parameter identifier or DSS C pathname part.
    * `parameter_type` (Optional): A [ParameterType](./parameter.html#ParameterType) object. Its `name`
        property is used for the CWMS parameter type identifier or DSS data type
    * `interval` (Required): An [Interval](./interval.html#Interval) object. Its `name` property is used
        for the CWMS interval identier or DSS E pathname poart
    * `duration` (Optional): A [Duration](./duration.html#Durationg) object. Its `name` property is used
        for the CWMS duration identifier. Unused in DSS contexts.
    * `version` (Optional): A string that holds the CWMS version identifier or DSS F pathname part.
    * `data` (Optiona): A pandas.DataFrame object containing the time series data. The DataFrame has a DateTime index,
        a float column named "value" and a integer column named "quality"

    ### Other properties
    * `name`: The name used to initalize the object. Will be a valid CWMS time series identifier or DSS time series pathname.
    * `unit`: The unit of the parameter. Also available as the `unit_name` property of the `parameter` proerty.
    * `time_zone`: The time zone of the data or None if not set
    * `vertical_datum_info_xml`: The vertical datum info as an XML string
    * `vertical_datum_info_dict`: The vertical datum info as a dictionary
    * `times`: The times of the data values as a list of strings
    * `values`: The data values as a list of floats
    * `qualities`: The quality codes of the data values as a list of integers
    * `slice_stop_exclusive`: Controls slicing behavior

    ### Indexing and slicing
    In addition to operations available on the `data` DataFrame, TimeSeries objects may also be indexed by
    individual indexes or slices.

    The result of an index or slice operation is a copy TimeSeries object with the data as indicated in
    the index or slice.

    Indexes (single, as well as start and stop values for slices) may be one of:
    * HecTime object
    * datetime object
    * String - must be in the format yyyy&#8209;mm&#8209;dd&nbsp;hh:mm:ss([+|&#8209;]hh:mm). The time zone portion is required
        if the data times have the time zone specified
    * Integer (index into the list of data times using normal python indexing)

    Slice steps are supported and must be a positive integer value (times must always increase)

    By default, slicing follows python behavior where the stop value is exclusive (not included in the returned data).
    To use DataFrame behavior where the stop value is inclusive (returned in the data):
    * call `TimeSeries.setSliceStopInclusive()` before creating any TimeSeries objects
    * set the `slice_stop_exclusive` property to False on existing TimeSeries objects.

    Note that slicing of the `data` object will always use DataFrame behavior.
    """

    _default_slice_stop_exclusive: bool = True

    @staticmethod
    def formatTimeForIndex(item: Union[HecTime, datetime, str]) -> str:
        ht = HecTime()
        ht.set(item)
        ht.midnight_as_2400 = False
        return str(ht).replace("T", " ")

    @classmethod
    def setSliceStopExclusive(cls, state: bool = True) -> None:
        """
        Set the default slicing behavior of new TimeSeries objects

        Args:
            state (bool, optional): Defaults to True.
                * `True`: python behavior (stop value is excluded)
                * `False`: DataFrame behavior (stop value is included)
        """
        cls._default_slice_stop_exclusive = state

    @classmethod
    def setSliceStopInclusive(cls, state: bool = True) -> None:
        """
        Set the default slicing behavior of new TimeSeries objects

        Args:
            state (bool, optional): Defaults to True.
                * `True`: DataFrame behavior (stop value is included)
                * `False`: python behavior (stop value is excluded)
        """
        cls._default_slice_stop_exclusive = not state

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
                * **cwms.types.Data**: A CWMS time series as returned from CDA using `cwms.get_timeseries()`
        """
        self._slice_stop_exclusive = TimeSeries._default_slice_stop_exclusive
        self._context: str
        self._watershed: Optional[str] = None
        self._location: Location
        self._parameter: Parameter
        self._parameter_type: Optional[ParameterType] = None
        self._interval: Interval
        self._duration: Optional[Duration] = None
        self._version: Optional[str] = None
        self._timezone: Optional[str] = None
        self._data: Optional[pd.DataFrame] = None

        if isinstance(init_from, str):
            self.name = init_from
        elif isinstance(init_from, cwms.types.Data):
            self._context = _CWMS
            props = init_from.json
            df = init_from.df
            self.name = props["name"]
            self.location.office = props["office-id"]
            # props["time-zone"] is time zone of request time window, actual times are in epoch milliseconds
            self._timezone = "UTC"
            if self.parameter.base_parameter == "Elev":
                elevParam = ElevParameter(
                    self.parameter.name, props["vertical-datum-info"]
                )
                if elevParam.elevation:
                    self.location.elevation = elevParam.elevation.magnitude
                    self.location.elevation_unit = elevParam.elevation.specified_unit
                self.location.vertical_datum = elevParam.native_datum
                self.setParameter(elevParam)
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

    def __getitem__(self, key: Any) -> "TimeSeries":
        if self._data is None:
            raise TimeSeriesException(
                "Cannot index or slice into a TimeSeries object with no data"
            )
        other = self.clone(include_data=False)
        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            if start:
                try:
                    start = self.indexOf(start)
                except IndexError as ie:
                    if ie.args and ie.args[0] == "list index out of range":
                        stop = None
                    else:
                        raise
            if stop:
                try:
                    stop = self.indexOf(stop)
                    if self._slice_stop_exclusive:
                        t = HecTime(hec.hectime.SECOND_GRANULARITY)
                        t.set(stop)
                        stop = str(t - timedelta(seconds=1)).replace("T", " ")
                except IndexError as ie:
                    if ie.args and ie.args[0] == "list index out of range":
                        stop = None
                    else:
                        raise
            other._data = self._data.loc[start:stop:step]
        else:
            other._data = cast(pd.DataFrame, self._data.loc[self.indexOf(key)])
        return other

    def indexOf(self, item_to_index: Union[HecTime, datetime, int, str]) -> str:
        """
        Retrieves the data index of a specified object

        Args:
            item_to_index (Union[HecTime, datetime, int, str]): The object to retrieve the index of.
                * **HecTime**: an HecTime object
                * **datetime**:  a datetime object
                * **int**: a normal python index
                * **str**: a date-time string

        Raises:
            TypeError: If `item_to_index` is not one of the expected types
            IndexError:
                * **int**: If the integer is out of range of the number of times
                * **Others**: If no index item matches the input object

        Returns:
            str: The actual index item that for the specified object
        """
        times = self.times
        idx = None
        try:
            if isinstance(item_to_index, HecTime):
                ht = HecTime(item_to_index)
                ht.midnight_as_2400 = False
                key = str(ht).replace("T", " ")
                idx = times.index(key)
            elif isinstance(item_to_index, datetime):
                ht = HecTime(item_to_index)
                ht.midnight_as_2400 = False
                key = str(ht).replace("T", " ")
                idx = times.index(key)
            elif isinstance(item_to_index, str):
                idx = times.index(item_to_index)
            elif isinstance(item_to_index, int):
                idx = item_to_index
            else:
                raise TypeError(
                    f"Expected HecTime, datetime, str, or int. Got {type(item_to_index)}"
                )
        except TypeError:
            raise
        except:
            raise IndexError(f"{item_to_index} is not in times")
        return str(times[idx])

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
        TimeSeries object

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
                f"Invalid time series name: '{value}':\n{type(e)}: {' '.join(e.args)}"
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
    def time_zone(self) -> Optional[str]:
        """
        The time zone of the data

        Operations:
            Read Only
        """
        return self._timezone

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
        The data as a DataFrame or None if not set. Note this exposes the interal DataFrame object to
        allow direct modification. For uses that should not modify this TimeSeries object, the DataFrame
        should be copied using its `copy()` method prior to modification (e.g., `df = ts.data.copy()`)

        Operations:
            Read Only
        """
        return self._data

    @property
    def times(self) -> list[str]:
        """
        The times as a list of strings (empty if there is no data). Items are formatted as yyyy&#8209;mm&#8209;dd&nbsp;hh:mm:ss([+|&#8209;]hh:mm)

        Operations:
            Read Only
        """

        return (
            []
            if self._data is None
            else list(map(TimeSeries.formatTimeForIndex, self._data.index.tolist()))
        )

    @property
    def values(self) -> list[float]:
        """
        The values as a list of floats (empty if there is no data)

        Operations:
            Read Only
        """
        return [] if self._data is None else self._data["value"].tolist()

    @property
    def qualities(self) -> list[int]:
        """
        The qualities as a list of integers (empty if there is no data)

        Operations:
            Read Only
        """
        return [] if self._data is None else self._data["quality"].tolist()

    def setLocation(self, value: Union[Location, str]) -> "TimeSeries":
        """
        Sets the location for the time series

        Args:
            value (Union[Location, str]):
                * Location: The Location object to use
                * str: The location name (may be in the format &lt;*office*&gt;/&lt;*location*&gt; to set office)

        Returns:
            TimeSeries: The modified object
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
        return self

    def setParameter(self, value: Union[Parameter, str]) -> "TimeSeries":
        """
        Sets the parameter for the time series

        Args:
            value (Union[Parameter, str]):
                * Parameter: The Parameter object to use
                * str: The parameter name - the unit will be set to the default English unit

        Returns:
            TimeSeries: The modified object
        """
        if isinstance(value, Parameter):
            self._parameter = value
        else:
            self._parameter = Parameter(value, "EN")
        return self

    def setParameterType(self, value: Union[ParameterType, str]) -> "TimeSeries":
        """
        Sets the parameter type for the time series

        Args:
            value (Union[ParameterType, str]):
                * ParameterType: The ParameterType object to use
                * str: The parameter type name

        Returns:
            TimeSeries: The modified object
        """
        if isinstance(value, ParameterType):
            self._parameter_type = value
        else:
            self._parameter_type = ParameterType(value)
        return self

    def setInterval(self, value: Union[Interval, str, int]) -> "TimeSeries":
        """
        Sets the interval for the time series

        Args:
            value (Union[Interval, str]):
                * Interval: The Interval object to use
                * str: The interval name
                * int: The (actual or characteristic) number of minutes for the interval

        Returns:
            TimeSeries: The modified object
        """
        if isinstance(value, Interval):
            self._interval = value
        else:
            if self._context == _CWMS:
                self._interval = Interval.getCwms(value)
            else:
                self._interval = Interval.getDss(value)
        return self

    def setDuration(self, value: Union[Duration, str, int]) -> "TimeSeries":
        """
        Sets the Duration for the time series

        Args:
            value (Union[Duration, str]):
                * Interval: The Duration object to use
                * str: The duration name
                * int: The (actual or characteristic) number of minutes for the duration

        Returns:
            TimeSeries: The modified object
        """
        if isinstance(value, Duration):
            self._duration = value
        else:
            self._duration = Duration.forInterval(value)
        return self

    def setUnit(self, value: Union[Unit, str]) -> "TimeSeries":
        """
        Sets the parameter unit for the time series

        Args:
            value (Union[Unit, str]):
                * ParameterType: The Unit object to use
                * str: The unit name

        Returns:
            TimeSeries: The modified object
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
        return self

    def setVerticalDatumInfo(self, value: Union[str, dict[str, Any]]) -> "TimeSeries":
        """
        Sets the vertical datum info for the time series

        Args:
            value (Union[str, dict[str, Any]]):
                * str: the vertical datum info as an XML string
                * dict: the vertical datum info as a dictionary

        Raises:
            TimeSeriesException: If the base parameter is not "Elev"

        Returns:
            TimeSeries: The modified object
        """
        if self._parameter.base_parameter == "Elev":
            self._parameter = ElevParameter(self._parameter.name, value)
        else:
            raise TimeSeriesException(
                f"Cannot set vertical datum on {self._parameter.name} time series"
            )
        return self

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
        other._timezone = self._timezone
        if include_data and self._data is not None:
            other._data = self._data.copy()
        return other

    def setValue(
        self, time: Union[HecTime, datetime, str, int, slice], value: float
    ) -> "TimeSeries":
        """
        Set the value at one or more indexes

        Args:
            time (Union[HecTime, datetime, str, int, slice]): The index or indexes if a slice
            value (float): The value to set

        Returns:
            TimeSeries: The modified object
        """
        if self._data is None:
            raise TimeSeriesException("Invalid call to setValue(): object has no data")
        if isinstance(time, slice):
            start = self.indexOf(time.start)
            stop = self.indexOf(time.stop)
            self._data.loc[slice(start, stop, time.step), "value"] = value
        else:
            self._data.loc[self.indexOf(time), "value"] = value
        return self

    def setQuality(
        self,
        time: Union[HecTime, datetime, str, int, slice],
        quality: Union[Quality, int],
    ) -> "TimeSeries":
        """
        Set the quality at one or more indexes

        Args:
            time (Union[HecTime, datetime, str, int, slice]): The index or indexes if a slice
            quality (Union[Quality, int]): The quality to set

        Raises:
            TimeSeiresException: If the object has no data

        Returns:
            TimeSeries: The modified object
        """
        if self._data is None:
            raise TimeSeriesException(
                "Invalid call to setQuality(): object has no data"
            )
        if isinstance(time, slice):
            start = self.indexOf(time.start)
            stop = self.indexOf(time.stop)
            self._data.loc[slice(start, stop, time.step), "quality"] = Quality(
                quality
            ).code
        else:
            self._data.loc[self.indexOf(time), "quality"] = Quality(quality).code
        return self

    def setValueQuality(
        self,
        time: Union[HecTime, datetime, str, int, slice],
        value: float,
        quality: Union[Quality, int],
    ) -> "TimeSeries":
        """
        Set the value and quality at one or more indexes

        Args:
            time (Union[HecTime, datetime, str, int, slice]): The index or indexes if a slice
            value (float): The value to set
            quality (Union[Quality, int]): The quality to set

        Raises:
            TimeSeiresException: If the object has no data

        Returns:
            TimeSeries: The modified object
        """
        if self._data is None:
            raise TimeSeriesException(
                "Invalid call to setValueQuality(): object has no data"
            )
        if isinstance(time, slice):
            start = self.indexOf(time.start)
            stop = self.indexOf(time.stop)
            self._data.loc[slice(start, stop, time.step), "value"] = value
            self._data.loc[slice(start, stop, time.step), "quality"] = Quality(
                quality
            ).code
        else:
            key = self.indexOf(time)
            self._data.loc[key, "value"] = value
            self._data.loc[key, "quality"] = Quality(quality).code
        return self

    def atTimeZone(
        self,
        timeZone: Optional[Union["HecTime", datetime, ZoneInfo, str]],
        onAlreadytSet: int = 1,
    ) -> "TimeSeries":
        """
        Attaches the specified time zone to this object. Does not change the actual times

        Args:
            timeZone (Optional[Union["HecTime", datetime, ZoneInfo, str]]): The time zone to attach or
                object containing that time zone.
                * Use `"local"` to specify the system time zone.
                * Use `None` to remove time zone information
            onAlreadytSet (int): Specifies action to take if a different time zone is already
                attached. Defaults to 1.
                - `0`: Quietly attach the new time zone
                - `1`: (default) Issue a warning about attaching a different time zone
                - `2`: Raises an exception
        Raises:
            TimeSeriesException: if a different time zone is already attached and `onAlreadySet` == 2

        Returns:
            TimeSeries: The modified object
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
        if self._timezone:
            if tz == ZoneInfo(self._timezone):
                return self
            if tz is None:
                if self._data is not None:
                    self._data = self._data.tz_localize(None)
                self._timezone = None
            else:
                if onAlreadytSet > 0:
                    message = f"{repr(self)} already has a time zone set to {self._timezone} when setting to {tz}"
                    if onAlreadytSet > 1:
                        raise TimeSeriesException(message)
                    else:
                        warnings.warn(
                            message + ". Use onAlreadySet=0 to prevent this message.",
                            UserWarning,
                        )
                if self._data is not None:
                    self._data = self._data.tz_localize(None)
                    self._data = self._data.tz_localize(str(tz))
                self._timezone = str(timeZone)
        else:
            if tz:
                if self._data is not None:
                    self._data = self._data.tz_localize(str(tz))
                self._timezone = str(tz)
        return self

    def asTimeZone(
        self, timeZone: Union["HecTime", datetime, ZoneInfo, str], onTzNotSet: int = 1
    ) -> "TimeSeries":
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
            TimeSeries: A copy of this object at the specified time zone
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
        if self._data is not None:
            if self._timezone:
                self._data = self._data.tz_convert(str(tz))
            else:
                self._data = self._data.tz_localize(str(tz))
        self._timezone = str(tz)
        return self
