"""
Provides time series types and operations
"""

import bisect
import math
import statistics as stat
import types
import warnings
from copy import deepcopy
from datetime import datetime, timedelta
from functools import total_ordering
from itertools import cycle, islice
from typing import Any, Callable, Dict, List, Optional, Union, cast
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import tzlocal
from pint import Unit

import hec.hectime
import hec.parameter
import hec.unit
from hec.const import CWMS, DSS, Combine, Select, SelectionState
from hec.duration import Duration
from hec.hectime import HecTime
from hec.interval import Interval
from hec.location import Location
from hec.parameter import ElevParameter, Parameter, ParameterType
from hec.quality import Quality
from hec.timespan import TimeSpan
from hec.unit import UnitQuantity

# from pytz.exceptions import AmbiguousTimeError


try:
    import cwms.cwms_types  # type: ignore

    cwms_imported = True
except ImportError:
    cwms_imported = False

_RESAMPLE_OP_ACCUMULATE = "ACCUMULATE"
_RESAMPLE_OP_AVERAGE = "AVERAGE"
_RESAMPLE_OP_COUNT = "COUNT"
_RESAMPLE_OP_INTEGRATE = "INTEGRATE"
_RESAMPLE_OP_INTERPOLATE = "INTERPOLATE"
_RESAMPLE_OP_MAXIMUM = "MAXINUM"
_RESAMPLE_OP_MINIMUM = "MININUM"
_RESAMPLE_OP_PREVIOUS = "PREVIOUS"
_RESAMPLE_OP_VOLUME = "VOLUME"

_RESAMPLE_FIRST = "FIRST"
_RESAMPLE_LAST = "LAST"
_RESAMPLE_MISSING = "MISSING"

_resample_operations = {
    #   Name:                    is_discreet
    _RESAMPLE_OP_ACCUMULATE: False,
    _RESAMPLE_OP_AVERAGE: False,
    _RESAMPLE_OP_COUNT: True,
    _RESAMPLE_OP_INTEGRATE: False,
    _RESAMPLE_OP_INTERPOLATE: False,
    _RESAMPLE_OP_MAXIMUM: True,
    _RESAMPLE_OP_MINIMUM: True,
    _RESAMPLE_OP_PREVIOUS: True,
    _RESAMPLE_OP_VOLUME: False,
}

_resample_before = (_RESAMPLE_FIRST, _RESAMPLE_MISSING)

_resample_after = (_RESAMPLE_LAST, _RESAMPLE_MISSING)

pd.set_option("future.no_silent_downcasting", True)


def _is_cwms_tsid(id: str) -> bool:
    parts = id.split(".")
    if len(parts) != 6:
        return False
    if len(parts[0]) > 57 or len(parts[0].split("-")[0]) > 24:
        return False
    if len(parts[1]) > 49 or len(parts[1].split("-")[0]) > 16:
        return False
    if len(parts[2]) > 16:
        return False
    if len(parts[3]) > 16:
        return False
    if len(parts[4]) > 16:
        return False
    if len(parts[5]) > 32:
        return False
    if parts[1].split("-")[0].upper() not in map(
        str.upper, Parameter.base_parameters("CWMS")
    ):
        return False
    if parts[2].upper() not in map(
        str.upper, ParameterType.parameter_type_names("CWMS")
    ):
        return False
    if parts[3].upper() not in map(str.upper, Interval.get_all_cwms_names()):
        return False
    if parts[4].upper() not in set(
        [Duration.for_interval(i).name.upper() for i in Interval.get_all_cwms_names()]
    ):
        return False
    return True


def _is_dss_ts_pathname(id: str) -> bool:
    A, B, C, D, E, F = 1, 2, 3, 4, 5, 6
    parts = id.split("/")
    if len(parts) != 8:
        return False
    if not parts[E].upper() in map(str.upper, Interval.get_all_dss_names()):
        return False
    if parts[D]:
        time_parts = parts[D].split("-")
        try:
            [HecTime(time_part) for time_part in time_parts]
        except:
            return False
    return True


class TimeSeriesException(Exception):
    """
    Exception specific to time series operations
    """

    pass


@total_ordering
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
        self._time = time.copy() if isinstance(time, HecTime) else HecTime(time)
        self._value = value if isinstance(value, UnitQuantity) else UnitQuantity(value)
        self._quality = Quality(quality)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TimeSeriesValue):
            return self.time == other.time
        else:
            return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, TimeSeriesValue):
            return self.time > other.time
        elif isinstance(other, HecTime):
            return self.time > other
        elif isinstance(other, (datetime, str)):
            return self.time > HecTime(other)
        else:
            return NotImplemented

    def __lt__(self, other: "TimeSeriesValue") -> bool:
        if isinstance(other, TimeSeriesValue):
            return self.time < other.time
        elif isinstance(other, HecTime):
            return self.time < other
        elif isinstance(other, (datetime, str)):
            return self.time < HecTime(other)
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return f"TimeSeriesValue({repr(self._time)}, {repr(self._value)}, {repr(self._quality)})"

    def __str__(self) -> str:
        return f"({str(self._time)}, {str(self.value)}, {str(self._quality)})"

    def equals(self, other: object, degree: int = 4) -> bool:
        """
        Returns whether two TimeSeriesValue objects are equal to the specified strictness.
        If the strictness indicates comparing the value fields, the comparison can use either of the following for value equality:
        * normal: equivalent values are considered equal even if they have different units. (e.g., 12 in == 1 ft)
        * strict: values must have same magnitude and units to be considered equal

        Args:
            other (object): The other TimeSeriesValue object to compare to
            degree (int): Specifies how strict to make the comparison. Valid values are:
                * `1`: Compares only time fields (same as == operator).
                * `2`: Compares only time and value fields with normal value equality.
                * `3`: Compares only time and value fields with strict value equality.
                * `4`: Compares time, value, and quality fields with normal value equality.
                * `5`: Compares time, value, and quality fields with stict value equality.
                <br>Defaults to `4`

        Returns:
            bool: Whether the time, value, and quality of two TimeSeriesValue objects are equal to the specified strictness.
        """
        if isinstance(other, TimeSeriesValue):
            if degree == 1:
                return self.time == other.time
            elif degree == 2:
                return self.time == other.time and self.value == other.value
            elif degree == 3:
                return (
                    self.time == other.time
                    and self.value.magnitude == other.value.magnitude
                    and self.value.unit == other.value.unit
                )
            elif degree == 4:
                return (
                    self.time == other.time
                    and self.value == other.value
                    and self.quality == other.quality
                )
            elif degree == 5:
                return (
                    self.time == other.time
                    and self.value.magnitude == other.value.magnitude
                    and self.value.unit == other.value.unit
                    and self.quality == other.quality
                )
            else:
                raise TimeSeriesException(
                    f"Expected strictness parameter to be 1-5, got {degree}"
                )
        else:
            raise TimeSeriesException(
                f"Expected parameter other to be TimeSeriesValue, got {type(other)}"
            )

    @property
    def is_valid(self) -> bool:
        """
        Whether this object is valid. TimeSeriesValues are valid unless any of the following are True:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read-Write
        """
        try:
            if math.isnan(self._value.magnitude) or math.isinf(self._value.magnitude):
                return False
            if self._quality.validity_id in ("MISSING", "REJECTED"):
                return False
            return True
        except:
            return False

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
    * call `TimeSeries.set_slice_stop_inclusive()` before creating any TimeSeries objects
    * set the `slice_stop_exclusive` property to False on existing TimeSeries objects.

    Note that slicing of the `data` object will always use DataFrame behavior.

    ### In-Place Methods

    All methods that return a time series have an optional parameter named `in_place` that defaults to `False`:
    * Leaving unspecified or specifying `False` will cause the method to return a new time series, leaving the time series
      on which the method is called unchanged and available for future use.
    * Specifying `True` will modify the time series on which the method is called and return the modified time series. The
      return value may of course be ignored if desired.

    Each of these method also has a "in-place" method without the `in_place` parameter and which simply calls the original
    method with `in_place=True`. The methods are named the same as the original methods prepended with the letter 'i' (e.g.,
    `select()` --> `iselect()`, `set_parameter()` --> `iset_parameter()`)
    """

    _default_slice_stop_exclusive: bool = True

    def __init__(
        self,
        name: str,
        times: Optional[
            Union[list[Union[HecTime, datetime, str]], pd.DatetimeIndex]
        ] = None,
        values: Optional[Union[list[float], float]] = None,
        qualities: Optional[Union[list[Union[Quality, int]], Quality, int]] = None,
        time_zone: Optional[str] = None,
    ):
        """
        Initializes a new TimeSeries object. To generate a new regular interval time series using start time, end time, interval, and offset
        see also [`new_regular_time_series()`](#TimeSeries.new_regular_time_series)

        Args:
            name (str):  The time series name. Must be either a CWMS time series identifier or HEC-DSS time series pathname.
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
                    * The following components are set by default:
                        * parameter type:
                            * INST_CUM if C includes "Precip" (case insensitive)
                            * INST_VAL otherwise
                    * The following compents are not set:
                        * duration
                * The parameter unit is set to the default English unit
                * No vertical datum information is set for elevation parameter

            times (Optional[Union[list[Union[HecTime, datetime, str]], pd.DatetimeIndex]]): The times for the time series. If specified, all times must have the same time zone or no time zone.
                If not specified, `values`, `qualities`, and `time_zone` my not be specified. Defaults to None.
            values (Optional[Union[list[float], float]]): A value or a list of values to assign to the specified times. If a single value or a list of values shorter than the list of times, the
                specified value(s) is/are repeated until each time has an assigned value. Must be specified if `times is specified`. Defaults to None.
            qualities (Optional[Union[list[Union[Quality, int]], Quality, int]]): A quality code or object or a list of quality codes or objects  to assign to the specified times. If a single quality
                or a list of qualities shorter than the list of times, the specified quality(ies) is/are repeated until each time has an assigned quality. If not specified and `times` is specified, each
                time will be assigned a quality code of zeor.Defaults to None.
            time_zone (Optional[str]): The time zone of the time series. If specified, must be a valid time zone name or "local". Interaction with the time zone of the `times` argument is as follows.
                Defaults to None.
                <table>
                <tr><th><code>times</code> has time zone</th><th><code>time_zone</code> specified</th><th>Time series time zone</th></tr>
                <tr><td>False</td><td>False</td><td>local time zone</td></tr>
                <tr><td>False</td><td>True</td><td>as specified in <code>time_zone</code></td></tr>
                <tr><td>True</td><td>False</td><td>as specified in <code>times</code></td></tr>
                <tr><td>True</td><td>True</td><td>as specified in <code>time_zone</code><br><code>times</code> are converted to <code>time_zone</code></td></tr>
                </table>
        """
        self._slice_stop_exclusive = TimeSeries._default_slice_stop_exclusive
        self._context: Optional[str] = None
        self._watershed: Optional[str] = None
        self._location: Location
        self._parameter: Parameter
        self._parameter_type: Optional[ParameterType] = None
        self._interval: Interval
        self._duration: Optional[Duration] = None
        self._version: Optional[str] = None
        self._version_time: Optional[HecTime] = None
        self._timezone: Optional[str] = None
        self._data: Optional[pd.DataFrame] = None
        self._midnight_as_2400: bool = False
        self._selection_state: SelectionState = SelectionState.TRANSIENT
        self._expanded = False
        self._skip_validation = False

        self.name = name.strip()
        if times is None:
            if not all([arg is None for arg in (values, qualities, time_zone)]):
                raise TimeSeriesException(
                    "None of values, qualities, or time_zone may be specified when times is not specified"
                )
            return
        # ------------ #
        # handle times #
        # ------------ #
        if isinstance(times, pd.DatetimeIndex):
            l_indx = times.copy()
            l_indx.name = "time"
        else:
            try:
                l_hectimes = list(map(hec.hectime.HecTime, times))
            except:
                raise TimeSeriesException("Cannot convert times to HecTime objects")
            tzname = str(l_hectimes[0].tzinfo)
            if not all(
                [str(l_hectimes[i].tzinfo) == tzname for i in range(1, len(l_hectimes))]
            ):
                raise TimeSeriesException(
                    "Times do not all have the same (or no) time zone"
                )
            l_indx = pd.DatetimeIndex(
                data=[ht.datetime() for ht in l_hectimes], name="time"
            )
        # ------------- #
        # handle values #
        # ------------- #
        if values is None:
            l_values = len(l_indx) * [np.nan]
        elif isinstance(values, float):
            l_values = len(l_indx) * [values]
        elif isinstance(values, (tuple, list)):
            try:
                floats = [float(v) for v in values]
            except:
                raise TimeSeriesException("Not all values are convertible to float")
            l_values = list(islice(cycle(floats), len(l_indx)))
        else:
            raise TimeSeriesException(
                f"Expected float or sequence of floats for values, got {values.__class__.__name__}"
            )
        # ---------------- #
        # handle qualities #
        # ---------------- #
        if qualities is None:
            l_qualities = len(l_indx) * [0]
        elif isinstance(qualities, (Quality, int)):
            l_qualities = len(l_indx) * [
                q.code if isinstance(q, Quality) else q for q in [qualities]
            ]
        elif isinstance(qualities, (tuple, list)):
            if not all([isinstance(q, (Quality, int)) for q in qualities]):
                raise TimeSeriesException(
                    "Not all qualities are integers or Quality objects"
                )
            ints = [q.code if isinstance(q, Quality) else q for q in qualities]
            l_qualities = list(islice(cycle(ints), len(l_indx)))
        else:
            raise TimeSeriesException(
                f"Expected Quality object, int or sequence of Quality objects or ints for qualities, got {values.__class__.__name__}"
            )
        # ---------------- #
        # handle time zone #
        # ---------------- #
        l_times_tz = None if l_indx.tz is None else str(l_indx.tz)
        if time_zone is None:
            if l_times_tz is None:
                self._timezone = tzlocal.get_localzone_name()
            else:
                self._timezone = str(l_indx.tz)
        else:
            self._timezone = time_zone
            if l_times_tz:
                l_indx.tz_convert(ZoneInfo(time_zone))
            else:
                l_indx.tz_localize(ZoneInfo(time_zone))
        # -------------------------- #
        # finally, set the DataFrame #
        # -------------------------- #
        self._data = pd.DataFrame(
            {
                "value": l_values,
                "quality": l_qualities,
            },
            index=l_indx,
        )

    def __add__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ------------- #
        # ADD to a copy #
        # ------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------ #
            # add a unitless scalar to time series #
            # ------------------------------------ #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] += amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] += amount
            return other
        elif isinstance(amount, UnitQuantity):
            # --------------------------------------- #
            # add a scalar with a unit to time series #
            # --------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__add__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------#
            # add another time series to time series #
            # ---------------------------------------#
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] + other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __floordiv__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # --------------------- #
        # INTEGER DIVIDE a copy #
        # --------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------- #
            # divide time series by unitless scalar #
            # ------------------------------------- #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] //= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] //= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # -------------------------------------- #
            # divide time series by scalar with unit #
            # -------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            other = self.__floordiv__(amount.to(to_unit).magnitude)
            other.iset_parameter(new_parameter)
            return other
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------- #
            # divide time series by another time series #
            # ----------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] // other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            other.iset_parameter(new_parameter)
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __getitem__(self, key: Any) -> "TimeSeries":
        if self._data is None:
            raise TimeSeriesException(
                "Cannot index or slice into a TimeSeries object with no data"
            )
        other = self.copy(include_data=False)
        if isinstance(key, slice):
            start, stop, step = key.start, key.stop, key.step
            if start:
                try:
                    start = self.index_of(start, "next")
                except IndexError as ie:
                    if ie.args and ie.args[0] == "list index out of range":
                        stop = None
                    else:
                        raise
            if stop:
                try:
                    stop = self.index_of(stop, "stop")
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
            other._data = cast(pd.DataFrame, self._data.loc[self.index_of(key)])
        return other

    def __iadd__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ------------ #
        # ADD in-place #
        # ------------ #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------ #
            # add a unitless scalar to time series #
            # ------------------------------------ #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] += amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] += amount
            return self
        elif isinstance(amount, UnitQuantity):
            # --------------------------------------- #
            # add a scalar with a unit to time series #
            # --------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__iadd__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------#
            # add another time series to time series #
            # ---------------------------------------#
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] + self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __ifloordiv__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ----------------------- #
        # INTEGER DIVIDE in-place #
        # ----------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------- #
            # divide time series by unitless scalar #
            # ------------------------------------- #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] //= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] //= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # -------------------------------------- #
            # divide time series by scalar with unit #
            # -------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            self.__ifloordiv__(amount.to(to_unit).magnitude)
            self.iset_parameter(new_parameter)
            return self
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------- #
            # divide time series by another time series #
            # ----------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] // self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            self.iset_parameter(new_parameter)
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __ilshift__(self, amount: Union[TimeSpan, timedelta, int]) -> "TimeSeries":
        # ------------------------------ #
        # SHIFT EARLIER in time in-place #
        # ------------------------------ #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (TimeSpan)):
            offset = amount
        elif isinstance(amount, timedelta):
            offset = TimeSpan(amount)
        elif isinstance(amount, int):
            if self._interval.is_irregular:
                raise TimeSeriesException(
                    "Cannot shift an irregular interval time series by an integer value"
                )
            offset = amount * self._interval
        times = list(map(HecTime, self.times))
        times2 = []
        for i in range(len(times)):
            times[i].midnight_as_2400 = False
            times[i] -= offset
            times2.append(times[i].datetime())
        self._data.index = pd.DatetimeIndex(times2)
        self._data.index.name = "time"
        return self

    def __imod__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # --------------- #
        # MODULO in-place #
        # --------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # -------------------------------------- #
            # mod time series with a unitless scalar #
            # -------------------------------------- #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] %= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] %= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # --------------------------------------- #
            # mod time series with a scalar with unit #
            # --------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__imod__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------- #
            # mod time series with another time series #
            # ---------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] % self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __imul__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ----------------- #
        # MULTIPLY in-place #
        # ----------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # --------------------------------------- #
            # multiply time series by unitless scalar #
            # --------------------------------------- #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] *= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] *= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # ---------------------------------------- #
            # multiply time series by scalar with unit #
            # ---------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq * UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq * UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((dstq / srcq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to multiply '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            self.__imul__(amount.to(to_unit).magnitude)
            self.iset_parameter(new_parameter)
            return self
        elif isinstance(amount, TimeSeries):
            # ------------------------------------------- #
            # multiply time series by another time series #
            # ------------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq * UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq * UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((dstq / srcq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to multiply '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] * self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            self.iset_parameter(new_parameter)
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __ipow__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ------------------------- #
        # RAISE to a power in-place #
        # ------------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------ #
            # raise time series by unitless scalar #
            # ------------------------------------ #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] **= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] **= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # ------------------------------------- #
            # raise time series by scalar with unit #
            # ONLY dimensionless units are allowed  #
            # ------------------------------------- #
            self.__ipow__(amount.to("n/a").magnitude)
            return self
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------- #
            # raise time series by another time series #
            # ONLY dimensionless units are allowed     #
            # ---------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            that = cast(pd.DataFrame, amount.to("n/a")._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] ** self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __irshift__(self, amount: Union[TimeSpan, timedelta, int]) -> "TimeSeries":
        # ---------------------------- #
        # SHIFT LATER in time in-place #
        # ---------------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (TimeSpan)):
            offset = amount
        elif isinstance(amount, timedelta):
            offset = TimeSpan(amount)
        elif isinstance(amount, int):
            if self._interval.is_irregular:
                raise TimeSeriesException(
                    "Cannot shift an irregular interval time series by an integer value"
                )
            offset = amount * self._interval
        times = list(map(HecTime, self.times))
        times2 = []
        for i in range(len(times)):
            times[i].midnight_as_2400 = False
            times[i] += offset
            times2.append(times[i].datetime())
        self._data.index = pd.DatetimeIndex(times2)
        self._data.index.name = "time"
        return self

    def __isub__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ----------------- #
        # SUBTRACT in-place #
        # ----------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------------- #
            # subtract a unitless scalar from time series #
            # ------------------------------------------- #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] -= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] -= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # ---------------------------------------------- #
            # subtract a scalar with a unit from time series #
            # ---------------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__isub__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------------#
            # subtract another time series from time series #
            # ----------------------------------------------#
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] - self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __itruediv__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # --------------- #
        # DIVIDE in-place #
        # --------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------- #
            # divide time series by unitless scalar #
            # ------------------------------------- #
            data = self._data
            if self.has_selection:
                data.loc[data["selected"], ["value"]] /= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
            else:
                data["value"] /= amount
            return self
        elif isinstance(amount, UnitQuantity):
            # -------------------------------------- #
            # divide time series by scalar with unit #
            # -------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            self.__itruediv__(amount.to(to_unit).magnitude)
            self.iset_parameter(new_parameter)
            return self
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------- #
            # divide time series by another time series #
            # ----------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            self._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            self._data["value"] = self._data["value_1"] / self._data["value_2"]
            self._data["quality"] = 0
            self._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            self.iset_parameter(new_parameter)
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return self
        else:
            return NotImplemented

    def __len__(self) -> int:
        if self._data is None or self._data.empty:
            return 0
        if self._expanded:
            shape = self._data.shape
            return 1 if len(shape) == 1 else shape[0]
        else:
            copy = self.copy()
            copy.iexpand()
            shape = cast(pd.DataFrame, copy._data).shape
            return 1 if len(shape) == 1 else shape[0]

    def __lshift__(self, amount: Union[TimeSpan, timedelta, int]) -> "TimeSeries":
        # ---------------------------- #
        # SHIFT a copy EARLIER in time #
        # ---------------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        other: TimeSeries = self.copy()
        if isinstance(amount, (TimeSpan)):
            offset = amount
        elif isinstance(amount, timedelta):
            offset = TimeSpan(amount)
        elif isinstance(amount, int):
            if self._interval.is_irregular:
                raise TimeSeriesException(
                    "Cannot shift an irregular interval time series by an integer value"
                )
            offset = amount * self._interval
        times = list(map(HecTime, self.times))
        times2 = []
        for i in range(len(times)):
            times[i].midnight_as_2400 = False
            times[i] -= offset
            times2.append(times[i].datetime())
        cast(pd.DataFrame, other._data).index = pd.DatetimeIndex(times2)
        cast(pd.DataFrame, other._data).index.name = "time"
        return other

    def __mod__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ---------------- #
        # MODULO of a copy #
        # ---------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # -------------------------------------- #
            # mod time series with a unitless scalar #
            # -------------------------------------- #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] %= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] %= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # --------------------------------------- #
            # mod time series with a scalar with unit #
            # --------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__mod__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------- #
            # mod time series with another time series #
            # ---------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] % other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __mul__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # --------------- #
        # MULTIPLY a copy #
        # --------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # --------------------------------------- #
            # multiply time series by unitless scalar #
            # --------------------------------------- #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] *= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] *= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # ---------------------------------------- #
            # multiply time series by scalar with unit #
            # ---------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq * UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq * UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((dstq / srcq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to multiply '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            other = self.__mul__(amount.to(to_unit).magnitude)
            other.iset_parameter(new_parameter)
            return other
        elif isinstance(amount, TimeSeries):
            # ------------------------------------------- #
            # multiply time series by another time series #
            # ------------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq * UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq * UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((dstq / srcq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to multiply '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] * other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            other.iset_parameter(new_parameter)
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __neg__(self) -> "TimeSeries":
        # ------------- #
        # NEGATE a copy #
        # ------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        other = self.copy()
        data = cast(pd.DataFrame, other._data)
        if other.has_selection:
            data.loc[data["selected"], ["value"]] *= -1
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if other is not self:
                    other.iselect(Select.ALL)
        else:
            data["value"] *= -1
        return other

    def __pow__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ----------------------- #
        # RAISE a copy to a power #
        # ----------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------ #
            # raise time series by unitless scalar #
            # ------------------------------------ #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] **= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] **= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # ------------------------------------- #
            # raise time series by scalar with unit #
            # ONLY dimensionless units are allowed  #
            # ------------------------------------- #
            other = self.__pow__(amount.to("n/a").magnitude)
            return other
        elif isinstance(amount, TimeSeries):
            # ---------------------------------------- #
            # raise time series by another time series #
            # ONLY dimensionless units are allowed     #
            # ---------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            that = cast(pd.DataFrame, amount.to("n/a")._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] ** other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __repr__(self) -> str:
        if self._version_time:
            return f"<TimeSeries('{self.name}'): {len(self)} values, version_time={self._version_time}, unit={self.parameter._unit_name}>"
        else:
            return f"<TimeSeries('{self.name}'): {len(self)} values, unit={self.parameter._unit_name}>"

    def __rshift__(self, amount: Union[TimeSpan, timedelta, int]) -> "TimeSeries":
        # -------------------------- #
        # SHIFT a copy LATER in time #
        # -------------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        other: TimeSeries = self.copy()
        if isinstance(amount, (TimeSpan)):
            offset = amount
        elif isinstance(amount, timedelta):
            offset = TimeSpan(amount)
        elif isinstance(amount, int):
            if self._interval.is_irregular:
                raise TimeSeriesException(
                    "Cannot shift an irregular interval time series by an integer value"
                )
            offset = amount * self._interval
        times = list(map(HecTime, self.times))
        times2 = []
        for i in range(len(times)):
            times[i].midnight_as_2400 = False
            times[i] += offset
            times2.append(times[i].datetime())
        cast(pd.DataFrame, other._data).index = pd.DatetimeIndex(times2)
        cast(pd.DataFrame, other._data).index.name = "time"
        return other

    def __str__(self) -> str:
        if self._version_time:
            return f"{self.name} @{self._version_time} {len(self)} values in {self.parameter.unit_name}"
        else:
            return f"{self.name} {len(self)} values in {self.parameter.unit_name}"

    def __sub__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # -------------------- #
        # SUBTRACT from a copy #
        # -------------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------------- #
            # subtract a unitless scalar from time series #
            # ------------------------------------------- #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] -= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] -= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # ---------------------------------------------- #
            # subtract a scalar with a unit from time series #
            # ---------------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
            else:
                to_unit = self.unit
            return self.__sub__(amount.to(to_unit).magnitude)
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------------#
            # subtract another time series from time series #
            # ----------------------------------------------#
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            this = self._data
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                that = cast(pd.DataFrame, amount.to("n/a")._data)
            else:
                that = cast(pd.DataFrame, amount.to(self.unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] - other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def __truediv__(
        self, amount: Union["TimeSeries", UnitQuantity, float, int]
    ) -> "TimeSeries":
        # ------------- #
        # DIVIDE a copy #
        # ------------- #
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if isinstance(amount, (float, int)):
            # ------------------------------------- #
            # divide time series by unitless scalar #
            # ------------------------------------- #
            other = self.copy()
            data = cast(pd.DataFrame, other._data)
            if other.has_selection:
                data.loc[data["selected"], ["value"]] /= amount
                if self.selection_state == SelectionState.TRANSIENT:
                    self.iselect(Select.ALL)
                    if other is not self:
                        other.iselect(Select.ALL)
            else:
                data["value"] /= amount
            return other
        elif isinstance(amount, UnitQuantity):
            # -------------------------------------- #
            # divide time series by scalar with unit #
            # -------------------------------------- #
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, self.unit)
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, end_unit)
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            other = self.__truediv__(amount.to(to_unit).magnitude)
            other.iset_parameter(new_parameter)
            return other
        elif isinstance(amount, TimeSeries):
            # ----------------------------------------- #
            # divide time series by another time series #
            # ----------------------------------------- #
            if amount._data is None:
                raise TimeSeriesException(
                    "Operation is invalid with empty time series."
                )
            if UnitQuantity(1, amount.unit).unit.dimensionless:
                to_unit = "n/a"
                new_parameter = self.parameter
            else:
                try:
                    srcq = UnitQuantity(1, str(UnitQuantity(1, self.unit).unit))
                    try:
                        end_unit = hec.unit.get_unit_name(
                            (srcq / UnitQuantity(1, amount.unit)).unit
                        )
                    except:
                        end_unit = hec.unit.get_unit_name(
                            hec.unit.get_compatible_units(
                                (srcq / UnitQuantity(1, amount.unit)).unit
                            )[0]
                        )
                    dstq = UnitQuantity(1, str(UnitQuantity(1, end_unit).unit))
                    to_unit = hec.unit.get_unit_name((srcq / dstq).unit)
                    new_param_name = hec.parameter.get_compatible_parameters(end_unit)[
                        0
                    ]
                    new_parameter = Parameter(new_param_name, end_unit)
                except:
                    raise TimeSeriesException(
                        f"\n==> Cannot automtically determine conversion to divide '{self.unit}' by '{amount.unit}'."
                        "\n==> Use the '.to()' method to convert one of the operands to a unit compatible with the other."
                    ) from None
            this = self._data
            that = cast(pd.DataFrame, amount.to(to_unit)._data)
            other = self.copy(include_data=False)
            other._data = pd.merge(
                this[this["selected"]] if "selected" in this.columns else this,
                that[that["selected"]] if "selected" in that.columns else that,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )
            other._data["value"] = other._data["value_1"] / other._data["value_2"]
            other._data["quality"] = 0
            other._data.drop(
                columns=["value_1", "value_2", "quality_1", "quality_2"], inplace=True
            )
            other.iset_parameter(new_parameter)
            # ------------------------------ #
            # reset any transient selections #
            # ------------------------------ #
            for ts in self, other, amount:
                if ts.selection_state == SelectionState.TRANSIENT:
                    ts.iselect(Select.ALL)
            return other
        else:
            return NotImplemented

    def _convert_to_context(self, ctx: str) -> None:
        if ctx not in (CWMS, DSS):
            raise TimeSeriesException(f"Invalid context: {ctx}")
        if self.parameter_type is None:
            raise TimeSeriesException(
                "Cannot change context of time series with unknown parameter type"
            )
        if self._context is None:
            self._context = ctx
        elif self._context == ctx:
            pass
        elif ctx == CWMS:
            # ----------- #
            # dss to cwms #
            # ----------- #
            self._skip_validation = True
            self._context = ctx
            if self._watershed is not None:
                self._watershed = self._watershed.title()
            self._location.name = self._location.name.title().replace(" ", "_")
            bn = self.parameter.basename
            sn = self.parameter.subname
            bpnu = bn.upper()
            for bp in Parameter.base_parameters("CWMS"):
                if bp.upper() == bpnu:
                    bn = bp
                    break
            pn = bn
            if sn:
                sn = sn.title().replace(" ", "_")
                pn += f"-{sn}"
            self.iset_parameter(Parameter(pn, self.parameter.unit_name))
            intvl = Interval.get_any_cwms(
                lambda i: i.is_regular == self.is_regular
                and i.minutes == self.interval.minutes
            )
            if intvl is None:
                raise TimeSeriesException(
                    f"Could not find CWMS equivalent of DSS interval {self._interval}"
                )
            self.iset_interval(intvl)
            if self.parameter_type.get_cwms_name() == "Inst":
                self.iset_duration(0)
            else:
                self.iset_duration(Duration.for_interval(self.interval))
            if self._version:
                self._version = self._version.title().replace(" ", "_")
            else:
                self._version = "None"
            self._skip_validation = False
            self._validate()
        elif ctx == DSS:
            # ----------- #
            # cwms to dss #
            # ----------- #
            self._skip_validation = True
            self._context = ctx
            if self.is_irregular:
                number_values = (
                    0
                    if not self.data
                    else 1 if len(self.data.shape) == 1 else self.data.shape[0]
                )
                seconds_per_year = timedelta(days=365).total_seconds()
                time_range = cast(
                    TimeSpan, (HecTime(self.times[-1]) - HecTime(self.times[0]))
                ).total_seconds()
                values_per_year = number_values / time_range * seconds_per_year
                if values_per_year > 1000:
                    intvl = Interval.get_any_dss(lambda i: i.name == "IR-Decade")
                elif values_per_year > 100:
                    intvl = Interval.get_any_dss(lambda i: i.name == "IR-Year")
                elif values_per_year > 100.0 / 12:
                    intvl = Interval.get_any_dss(lambda i: i.name == "IR-Month")
                else:
                    intvl = Interval.get_any_dss(lambda i: i.name == "IR-Day")
            else:
                if self.interval.is_local_regular or self.interval.is_pseudo_regular:
                    intvl = Interval.get_dss(self.interval.name)
                else:
                    intvl = Interval.get_any_dss(
                        lambda i: i.is_regular == True
                        and i.minutes == self.interval.minutes
                    )
            if intvl is None:
                raise TimeSeriesException(
                    f"Could not find DSS equivalent of CWMS interval {self._interval}"
                )
            self.iset_interval(intvl)
            if self.version == "None":
                self._version = None
            self._skip_validation = False
            self._validate()

    def _diff(self, time_based: bool, in_place: bool = False) -> "TimeSeries":
        target = self if in_place else self.copy()
        if target._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if target.has_selection:
            target._data.loc[~target._data["selected"], "value"] = np.nan
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if target is not self:
                    target.iselect(Select.ALL)
        base_param_name = self.parameter.basename
        if time_based:
            if base_param_name not in Parameter.differentiable_base_parameters():
                raise TimeSeriesException(
                    f"Cannot compute derivative on a time series with parameter of {base_param_name}, "
                    f"base parameter must be one of {Parameter.differentiable_base_parameters()}"
                )
            unit_system = "EN" if target.is_english else "SI"
            normal_unit = hec.unit.get_unit_name(
                Parameter(base_param_name, unit_system).unit
            )
            info = Parameter.differentiation_info(base_param_name)
            factor = info[unit_system]
            target.to(normal_unit)
            target._data["time-diffs"] = (
                target._data.index.to_series().diff().dt.total_seconds()
            )
            target._data["diffs"] = (
                target._data["value"].diff() / target._data["time-diffs"] * factor
            )
            target._data.drop(columns=["time-diffs"])
            subname = self.parameter.subname
            new_paramname = info["base_parameter"]
            if subname:
                new_paramname += "-" + subname
            new_parameter = Parameter(new_paramname, unit_system)
            target.iset_parameter(new_parameter)
        else:
            if self.parameter.basename not in Parameter.accumulatable_base_parameters():
                raise TimeSeriesException(
                    f"Cannot compute differences on a time series with parameter of {base_param_name}, "
                    f"base parameter must be one of {Parameter.accumulatable_base_parameters()}"
                )
            if cast(ParameterType, self.parameter_type).get_raw_name() in (
                "Constant",
                "Minimum",
                "Maximum",
            ):
                raise TimeSeriesException(
                    f"Cannot compute differences on a {cast(ParameterType, self.parameter_type).name} time series."
                )
            target._data["diffs"] = target._data["value"].diff()
        target._data["value"] = target._data["diffs"]
        target._data.drop(columns=["diffs"])
        target._data = target._data.drop(target._data.index[0])
        return target

    def _moving_average(
        self,
        operation: str,
        window: int,
        only_valid: bool,
        use_reduced: bool,
        in_place: bool = False,
    ) -> "TimeSeries":
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        op = operation.upper()
        centered = op in ["CENTERED", "OLYMPIC"]
        olympic = op == "OLYMPIC"
        if window < 2:
            raise TimeSeriesException("Window size for averaging must be > 1")
        if centered and window % 2 == 0:
            raise TimeSeriesException(
                f"Window must be an odd number for {'Olympic' if olympic else 'Centered'} moving average"
            )
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        df = cast(pd.DataFrame, target._data)
        # --------------------------- #
        # first perform the averaging #
        # --------------------------- #
        if olympic:
            # -------------------------------------------- #
            # we have to roll our own function for Olympic #
            # -------------------------------------------- #
            def olympic_average(vals: np.ndarray) -> Any:  # type: ignore
                vals = vals[~np.isnan(vals)]
                if len(vals) <= 2:
                    return np.nan
                return np.mean(np.sort(vals)[1:-1])

            df["averaged"] = (
                df["value"]
                .rolling(window=window, min_periods=1, center=True)
                .apply(olympic_average, raw=True)
            )
        else:
            # --------------------------------------------------- #
            # for Forward and Centered we can use built-in mean() #
            # --------------------------------------------------- #
            df["averaged"] = (
                df["value"]
                .rolling(window=window, min_periods=1, center=centered)
                .mean()
            )
        # ---------------------------------------------------------------------------------- #
        # next change any values that don't match only_valid and use_reduced criteria to NaN #
        # ---------------------------------------------------------------------------------- #
        if only_valid:
            invalid_indices = TimeSeries._invalid_indices(df)
            bad: set[np.datetime64] = set()
            if centered:
                for idx in invalid_indices:
                    pos = cast(int, df.index.get_loc(idx))
                    bad.update(df.index[pos - window // 2 : pos - window // 2 + window])
            else:
                for idx in invalid_indices:
                    pos = cast(int, df.index.get_loc(idx))
                    bad.update(df.index[pos : pos + window])
            bad_indices = sorted(bad)
            df.loc[bad_indices, "averaged"] = np.nan
        if centered:
            if not use_reduced:
                df.loc[df.index[: window // 2], "averaged"] = np.nan
                df.loc[df.index[-(window // 2) :], "averaged"] = np.nan
        else:
            if use_reduced:
                df.loc[df.index[0], "averaged"] = np.nan
            else:
                df.loc[df.index[: window - 1], "averaged"] = np.nan
        # -------------------------------- #
        # finally clean up and set quality #
        # -------------------------------- #
        df["value"] = df["averaged"]
        df.drop(columns=["averaged"], inplace=True)
        df.loc[TimeSeries._valid_indices(df), "quality"] = 0
        df.loc[TimeSeries._invalid_indices(df), "quality"] = 5
        return target

    @staticmethod
    def _invalid_indices(df: pd.DataFrame) -> list[np.datetime64]:
        return cast(
            list[np.datetime64],
            df.index[
                (df["value"].isna())
                | (np.isinf(df["value"]))
                | (df["quality"] == 5)
                | ((df["quality"].astype("int64") & 0b1_0000) != 0)
            ],
        )

    @staticmethod
    def _protected_indices(df: pd.DataFrame) -> list[np.datetime64]:
        return cast(
            list[np.datetime64],
            df[
                (
                    df["quality"].astype("int64")
                    & 0b1000_0000_0000_0000_0000_0000_0000_0000
                )
                != 0
            ].index,
        )

    def _resample_continuous(
        self,
        operation: str,
        old_tsvs: List[TimeSeriesValue],
        new_tsvs: List[TimeSeriesValue],
        is_regular: bool,
        bounds: List[Any],
        max_missing_percent: float,
    ) -> None:
        new_parameter = None
        new_unit = self.unit
        if operation in (_RESAMPLE_OP_INTEGRATE, _RESAMPLE_OP_VOLUME):
            if operation == _RESAMPLE_OP_VOLUME:
                if self.parameter.basename != "Flow":
                    raise TimeSeriesException(
                        f"Cannot perform VOLUME resample operation on time series of {self.parameter}"
                    )
                if (
                    self.parameter.unit.dimensionality
                    != Parameter("Flow").unit.dimensionality
                ):
                    raise TimeSeriesException(
                        f"Cannot perform VOLUME resample operation on time series with unit of {self.unit}"
                    )
            else:
                if self.parameter.basename not in hec.parameter._integration_parameters:
                    raise TimeSeriesException(
                        f"Cannot perform INTEGRATE resample operation on time series of {self.parameter}\n"
                        f"Base parameter must be one of {Parameter.integrable_base_parameters()}"
                    )
                if self.parameter.unit.dimensionality not in [
                    Parameter(p).unit.dimensionality
                    for p in hec.parameter._integration_parameters
                ]:
                    raise TimeSeriesException(
                        f"Cannot perform INTEGRATE resample operation on time series with unit of {self.unit}\n"
                        f"Unit dimensionality must be one of {sorted(set([str(Parameter(p).unit.dimensionality) for p in Parameter.integrable_base_parameters()]))}"
                    )
            if cast(ParameterType, self.parameter_type).get_raw_name() not in [
                "Average",
                "Constant",
                "Instantaneous",
            ]:
                raise TimeSeriesException(
                    f"Cannot perform INTEGRATE or VOLUME resample operation time series with parameter type {cast(ParameterType, self.parameter_type).name}"
                )
            this_unit = self.parameter.unit
            time_unit = hec.unit.get_pint_unit("s")
            new_unit = this_unit * time_unit
            new_parameter = self.get_integration_parameter()
        elif operation == _RESAMPLE_OP_ACCUMULATE:
            if cast(ParameterType, self.parameter_type).get_raw_name() in (
                "Constant",
                "Minimum",
                "Maximum",
            ):
                raise TimeSeriesException(
                    f"Cannot perform ACCUMULATE resample operation on {cast(ParameterType, self.parameter_type).name} time series."
                )
            if self.parameter.basename not in Parameter.accumulatable_base_parameters():
                raise TimeSeriesException(
                    f"Cannot perform ACCUMULATE resample operation on time series of {self.parameter}\n"
                    f"Base parameter must be one of {Parameter.accumulatable_base_parameters()}"
                )
            if self.parameter.unit.dimensionality in [
                Parameter(p).unit.dimensionality
                for p in hec.parameter._integration_parameters
            ]:
                raise TimeSeriesException(
                    f"Cannot perform ACCUMULATE resample operation on time series with unit of {self.unit}\n"
                    f"Unit dimensionality must be not be one of {sorted(set([str(Parameter(p).unit.dimensionality) for p in hec.parameter._integration_parameters]))}"
                )
        is_inst = (
            cast(ParameterType, self.parameter_type).get_raw_name() == "Instantaneous"
        )
        is_total = cast(ParameterType, self.parameter_type).get_raw_name() == "Total"
        is_accum = (
            cast(ParameterType, self.parameter_type).name == "INST-CUM"
            if self.context == DSS
            else is_inst and self.parameter.base_parameter == "Precip"
        )
        prev_lo: Optional[int] = None
        prev_hi: int
        len_old = len(old_tsvs)
        lo: int
        hi: int
        interpolated: TimeSeriesValue
        prev_interpolated: Optional[TimeSeriesValue] = None
        last_valid = 0.0
        first_boundary = True
        for i, boundary in [(i, b) for (i, b) in enumerate(bounds) if b is not None]:
            missing_seconds = 0.0
            t1, t2 = (0, 1) if i == 0 else (i - 1, i)
            new_interval_seconds = (
                cast(datetime, new_tsvs[t2].time.datetime())
                - cast(datetime, new_tsvs[t1].time.datetime())
            ).total_seconds()
            max_missing_seconds = new_interval_seconds * max_missing_percent / 100.0
            new_val = math.nan
            if not first_boundary:
                prev_lo, prev_hi = lo, hi
                prev_interpolated = interpolated
            first_boundary = False
            lo, hi = boundary
            if lo == hi:
                t1, t2 = (lo, lo + 1) if lo < len_old - 1 else (hi - 1, hi)
            else:
                t1, t2 = (lo, hi)
            old_interval_seconds = (
                cast(datetime, old_tsvs[t2].time.datetime())
                - cast(datetime, old_tsvs[t1].time.datetime())
            ).total_seconds()
            # ---------------------------------------------- #
            # interpolate the value at the new interval time #
            # ---------------------------------------------- #
            interpolated = TimeSeriesValue(new_tsvs[i].time, new_tsvs[i].value, 0)
            for interpolation_iteration in [1]:
                # ---------------------------------------------------- #
                # expand the interpolation window to valid value times #
                # ---------------------------------------------------- #
                while lo >= 0 and not old_tsvs[lo].is_valid:
                    lo1, lo2 = (0, 1) if lo == 0 else (lo - 1, lo)
                    lo = -1
                    missing_seconds += (
                        cast(datetime, old_tsvs[lo2].time.datetime())
                        - cast(datetime, old_tsvs[lo1].time.datetime())
                    ).total_seconds()
                if lo < 0:
                    # ------------------------------- #
                    # can't interpolate this interval #
                    # ------------------------------- #
                    break
                while hi < len_old and not old_tsvs[hi].is_valid:
                    hi1, hi2 = (hi - 1, hi) if hi == len_old - 1 else (hi, hi + 1)
                    hi += 1
                    missing_seconds += (
                        cast(datetime, old_tsvs[hi2].time.datetime())
                        - cast(datetime, old_tsvs[hi1].time.datetime())
                    ).total_seconds()
                if hi == len_old:
                    # ------------------------------- #
                    # can't interpolate this interval #
                    # ------------------------------- #
                    break
                # -------------------------------------------------------------------------- #
                # can't interpolate this interval if expansion is wider than missing percent #
                # -------------------------------------------------------------------------- #
                if missing_seconds > max_missing_seconds:
                    break
                # ---------------------------------------------- #
                # can't interpolate decreasing cumulative values #
                # ---------------------------------------------- #
                if (
                    is_accum
                    and old_tsvs[hi].value.magnitude < old_tsvs[lo].value.magnitude
                ):
                    break
                # ------------------------ #
                # perform the intepolation #
                # ------------------------ #
                if lo == hi or (not is_inst and not is_total):
                    interpolated.value = old_tsvs[hi].value
                else:
                    fraction = float(
                        (
                            cast(datetime, new_tsvs[i].time.datetime())
                            - cast(datetime, old_tsvs[lo].time.datetime())
                        ).total_seconds()
                    ) / float(
                        (
                            cast(datetime, old_tsvs[hi].time.datetime())
                            - cast(datetime, old_tsvs[lo].time.datetime())
                        ).total_seconds()
                    )
                    if (
                        is_total
                        and old_tsvs[lo].time <= new_tsvs[i].time < old_tsvs[hi].time
                    ):
                        interpolated.value = old_tsvs[hi].value * fraction
                    else:
                        interpolated.value = old_tsvs[lo].value + fraction * (
                            old_tsvs[hi].value.magnitude - old_tsvs[lo].value.magnitude
                        )
            if operation == _RESAMPLE_OP_INTERPOLATE:
                new_tsvs[i].value = interpolated.value
            elif operation == _RESAMPLE_OP_ACCUMULATE and not is_total:
                if prev_interpolated is not None:
                    val = interpolated.value - prev_interpolated.value
                    if val >= 0 or not is_accum:
                        new_tsvs[i].value = val
            else:
                # ---------------------------------- #
                # gather the contributing components #
                # ---------------------------------- #
                intvl_tsvs: list[TimeSeriesValue] = []
                partial_first_component = False

                if i == 0:
                    prev_new_time = new_tsvs[0].time - (
                        new_tsvs[1].time - new_tsvs[0].time
                    )
                    prev_interpolated = TimeSeriesValue(
                        cast(HecTime, prev_new_time).clone(),
                        UnitQuantity(math.nan, self.unit),
                        0,
                    )
                    prev_hi = 0
                if cast(TimeSeriesValue, prev_interpolated).time < old_tsvs[hi].time:
                    intvl_tsvs.append(cast(TimeSeriesValue, prev_interpolated))
                    if i == 0:
                        if operation == _RESAMPLE_OP_ACCUMULATE and is_total:
                            prev_new_time = cast(HecTime, intvl_tsvs[0].time.clone())
                            td = timedelta(seconds=old_interval_seconds)
                            while prev_new_time + td < old_tsvs[0].time:
                                prev_new_time = prev_new_time + td
                            if prev_new_time > intvl_tsvs[0].time:
                                intvl_tsvs.append(
                                    TimeSeriesValue(
                                        prev_new_time.clone(),
                                        UnitQuantity(math.nan, self.unit),
                                        0,
                                    )
                                )
                        elif (
                            old_tsvs[0].time - timedelta(seconds=old_interval_seconds)
                            > cast(TimeSeriesValue, prev_interpolated).time
                        ):
                            intvl_tsvs.append(
                                TimeSeriesValue(
                                    old_tsvs[0].time
                                    - timedelta(seconds=old_interval_seconds),
                                    UnitQuantity(math.nan, self.unit),
                                    0,
                                )
                            )
                        intvl_tsvs.sort()
                        if is_total and is_regular:
                            first_fraction = True
                            for j in range(len(intvl_tsvs)):
                                if math.isnan(
                                    intvl_tsvs[j].value.magnitude
                                ) and intvl_tsvs[j].time > old_tsvs[0].time - timedelta(
                                    seconds=old_interval_seconds
                                ):
                                    fraction = (
                                        1.0
                                        - (
                                            cast(datetime, old_tsvs[0].time.datetime())
                                            - cast(
                                                datetime, intvl_tsvs[j].time.datetime()
                                            )
                                        ).total_seconds()
                                        / (
                                            cast(datetime, old_tsvs[1].time.datetime())
                                            - cast(
                                                datetime, old_tsvs[0].time.datetime()
                                            )
                                        ).total_seconds()
                                    )
                                    if first_fraction:
                                        first_fraction = False
                                        if 0.0 <= fraction <= 1.0:
                                            partial_first_component = True
                                    intvl_tsvs[j].value = old_tsvs[0].value * fraction
                    if (
                        cast(
                            HecTime,
                            (
                                old_tsvs[prev_lo].time
                                if prev_lo is not None
                                else old_tsvs[lo].time
                                - timedelta(seconds=old_interval_seconds)
                            ),
                        )
                        < cast(TimeSeriesValue, prev_interpolated).time
                    ):
                        partial_first_component = True
                for j in range(prev_hi, hi + 1):
                    if (
                        cast(TimeSeriesValue, prev_interpolated).time
                        < old_tsvs[j].time
                        < interpolated.time
                    ):
                        intvl_tsvs.append(old_tsvs[j])
                if interpolated.time > intvl_tsvs[-1].time:
                    intvl_tsvs.append(interpolated)
                if (
                    partial_first_component
                    and is_total
                    and (
                        math.isfinite(intvl_tsvs[0].value.magnitude)
                        and intvl_tsvs[1].value.magnitude
                        < intvl_tsvs[0].value.magnitude
                    )
                ):
                    # ---------------------------------------------------------------------------------- #
                    # Zero out the first value to prevent averaging of the first two values in this case #
                    # ---------------------------------------------------------------------------------- #
                    intvl_tsvs[0].value = UnitQuantity(0.0, self.unit)
                # --------------------------- #
                # compute the resampled value #
                # --------------------------- #
                values: List[float] = []
                value_seconds: List[float] = []
                invalid: List[bool] = []
                if partial_first_component and not math.isnan(
                    intvl_tsvs[0].value.magnitude
                ):
                    values.append(intvl_tsvs[0].value.magnitude)
                    value_seconds.append(0)
                    invalid.append(False)
                for j in range(1, len(intvl_tsvs)):
                    seconds = (
                        cast(datetime, intvl_tsvs[j].time.datetime())
                        - cast(datetime, intvl_tsvs[j - 1].time.datetime())
                    ).total_seconds()
                    is_invalid = False
                    if operation == _RESAMPLE_OP_ACCUMULATE:
                        if is_inst:
                            if not (
                                intvl_tsvs[j - 1].is_valid and intvl_tsvs[j].is_valid
                            ):
                                missing_seconds += seconds
                                is_invalid = True
                            value = (
                                intvl_tsvs[j - 1].value.magnitude
                                + intvl_tsvs[j].value.magnitude
                            ) / 2
                        else:
                            if not intvl_tsvs[j].is_valid:
                                missing_seconds += seconds
                                is_invalid = True
                            if new_interval_seconds < old_interval_seconds:
                                value = old_tsvs[hi].value.magnitude
                            else:
                                value = intvl_tsvs[j].value.magnitude
                    elif operation == _RESAMPLE_OP_AVERAGE:
                        if is_inst:
                            if not (
                                intvl_tsvs[j - 1].is_valid and intvl_tsvs[j].is_valid
                            ):
                                missing_seconds += seconds
                                is_invalid = True
                            value = (
                                intvl_tsvs[j - 1].value.magnitude
                                + intvl_tsvs[j].value.magnitude
                            ) / 2
                        elif is_total:
                            if j == 1 and (
                                partial_first_component
                                or (
                                    new_interval_seconds > old_interval_seconds
                                    and (
                                        cast(datetime, intvl_tsvs[1].time.datetime())
                                        - cast(datetime, intvl_tsvs[0].time.datetime())
                                    ).total_seconds()
                                    < old_interval_seconds
                                )
                            ):
                                values.append(intvl_tsvs[0].value.magnitude)
                                value_seconds.append(0)
                                invalid.append(not intvl_tsvs[0].is_valid)
                                value = intvl_tsvs[1].value.magnitude
                                if not intvl_tsvs[1].is_valid:
                                    missing_seconds += seconds
                                    is_invalid = True
                            else:
                                if not intvl_tsvs[j].is_valid:
                                    missing_seconds += seconds
                                    is_invalid = True
                                value = intvl_tsvs[j].value.magnitude
                        else:
                            if not intvl_tsvs[j].is_valid:
                                missing_seconds += seconds
                                is_invalid = True
                            value = intvl_tsvs[j].value.magnitude
                    elif operation in (_RESAMPLE_OP_INTEGRATE, _RESAMPLE_OP_VOLUME):
                        if is_inst:
                            if not (
                                intvl_tsvs[j - 1].is_valid and intvl_tsvs[j].is_valid
                            ):
                                missing_seconds += seconds
                                is_invalid = True
                            value = (
                                intvl_tsvs[j - 1].value.magnitude
                                + intvl_tsvs[j].value.magnitude
                            ) / 2
                        elif is_total:
                            if j == 1 and partial_first_component:
                                values.append(intvl_tsvs[0].value.magnitude)
                                value_seconds.append(0)
                                invalid.append(not intvl_tsvs[0].is_valid)
                                value = intvl_tsvs[1].value.magnitude
                                if not intvl_tsvs[1].is_valid:
                                    missing_seconds += seconds
                                    is_invalid = True
                            else:
                                if not intvl_tsvs[j].is_valid:
                                    missing_seconds += seconds
                                    is_invalid = True
                                value = intvl_tsvs[j].value.magnitude / 2
                        else:
                            if not intvl_tsvs[j].is_valid:
                                missing_seconds += seconds
                                is_invalid = True
                            value = intvl_tsvs[j].value.magnitude
                    values.append(value)
                    value_seconds.append(seconds)
                    invalid.append(is_invalid)
                if operation == _RESAMPLE_OP_ACCUMULATE:
                    if (
                        lo == hi
                        and len(values) < 2
                        and seconds == old_interval_seconds == new_interval_seconds
                    ):
                        if is_inst and hi > 0:
                            new_val = (
                                old_tsvs[hi - 1].value.magnitude
                                + old_tsvs[hi].value.magnitude
                            ) / 2
                        else:
                            new_val = old_tsvs[hi].value.magnitude
                    else:
                        if missing_seconds > max_missing_seconds:
                            continue
                        if is_total:
                            # ----------------- #
                            # add up components #
                            # ----------------- #
                            if len(intvl_tsvs) == 2:
                                # ------------ #
                                # 1 components #
                                # ------------ #
                                if not intvl_tsvs[1].is_valid:
                                    new_val = math.nan
                                elif not intvl_tsvs[0].is_valid:
                                    new_val = intvl_tsvs[1].value.magnitude / (
                                        old_interval_seconds / new_interval_seconds
                                    )
                                else:
                                    for j in range(len_old):
                                        if old_tsvs[j].time >= intvl_tsvs[1].time:
                                            new_val = (old_tsvs[j].value.magnitude) / (
                                                old_interval_seconds
                                                / new_interval_seconds
                                            )
                                            break
                                    else:
                                        new_val = (intvl_tsvs[1].value.magnitude) / (
                                            old_interval_seconds / new_interval_seconds
                                        )
                            elif len(intvl_tsvs) == 3:
                                # ------------ #
                                # 2 components #
                                # ------------ #
                                new_val = math.nan
                                if partial_first_component:
                                    if (
                                        intvl_tsvs[0].is_valid
                                        and intvl_tsvs[1].is_valid
                                    ):
                                        new_val = (
                                            intvl_tsvs[1].value.magnitude
                                            - intvl_tsvs[0].value.magnitude
                                        )
                                        if intvl_tsvs[2].is_valid:
                                            new_val += intvl_tsvs[2].value.magnitude
                                    else:
                                        new_val = intvl_tsvs[2].value.magnitude
                                else:
                                    new_val = intvl_tsvs[2].value.magnitude
                            else:
                                # ---------------------- #
                                # more than 2 components #
                                # ---------------------- #
                                if partial_first_component:
                                    if invalid[0] or invalid[1]:
                                        new_val = 0
                                    else:
                                        new_val = values[1] - values[0]
                                    new_val += sum(
                                        [
                                            values[j]
                                            for j in range(2, len(values))
                                            if not invalid[j]
                                        ]
                                    )
                                else:
                                    new_val = sum(
                                        [
                                            values[j]
                                            for j in range(len(values))
                                            if not invalid[j]
                                        ]
                                    )
                        else:
                            # --------------------------------- #
                            # diff between end and start values #
                            # --------------------------------- #
                            new_val = (
                                intvl_tsvs[-1].value.magnitude
                                - intvl_tsvs[0].value.magnitude
                            )
                            if is_accum and new_val < 0.0:
                                new_val = math.nan
                elif operation == _RESAMPLE_OP_AVERAGE:
                    if (
                        lo == hi
                        and len(values) < 2
                        and seconds == old_interval_seconds == new_interval_seconds
                    ):
                        # ------------------------------------------------------------ #
                        # single value in interval that represents the exact interval #
                        # ------------------------------------------------------------ #
                        if is_inst and hi > 0:
                            new_val = (
                                old_tsvs[hi - 1].value.magnitude
                                + old_tsvs[hi].value.magnitude
                            ) / 2
                        elif is_total:
                            new_val = old_tsvs[hi].value.magnitude / 2
                        else:
                            new_val = old_tsvs[hi].value.magnitude
                    else:
                        if missing_seconds > max_missing_seconds:
                            continue
                        if is_total:
                            new_val = 0.0
                            for j in range(len(values)):
                                if invalid[j]:
                                    continue
                                if (values[j] < last_valid) or (
                                    value_seconds[j] == old_interval_seconds
                                ):
                                    new_val += values[j] / 2 * value_seconds[j]
                                else:
                                    if j == 0:
                                        last_valid = values[j]
                                        continue
                                    new_val += (
                                        (values[j - 1] + values[j])
                                        / 2
                                        * value_seconds[j]
                                    )
                                last_valid = values[j]
                            new_val /= sum(
                                [
                                    value_seconds[j]
                                    for j in range(len(value_seconds))
                                    if not invalid[j]
                                ]
                            )
                        else:
                            # ------------------------------- #
                            # data type isn't Total (PER-CUM) #
                            # ------------------------------- #
                            new_val = sum(
                                [
                                    values[j] * value_seconds[j]
                                    for j in range(len(values))
                                    if not invalid[j]
                                ]
                            ) / sum(
                                [
                                    value_seconds[j]
                                    for j in range(len(value_seconds))
                                    if not invalid[j]
                                ]
                            )
                elif operation in (_RESAMPLE_OP_INTEGRATE, _RESAMPLE_OP_VOLUME):
                    if (
                        lo == hi
                        and len(values) < 2
                        and seconds == old_interval_seconds == new_interval_seconds
                    ):
                        if is_inst and hi > 0:
                            new_val = (
                                (
                                    old_tsvs[hi - 1].value.magnitude
                                    + old_tsvs[hi].value.magnitude
                                )
                                / 2
                                * new_interval_seconds
                            )
                        else:
                            new_val = (
                                old_tsvs[hi].value.magnitude * new_interval_seconds
                            )
                    else:
                        if missing_seconds > max_missing_seconds:
                            continue
                        new_val = sum(
                            [
                                values[j] * value_seconds[j]
                                for j in range(len(values))
                                if not invalid[j]
                            ]
                        )
                new_tsvs[i].value = UnitQuantity(new_val, new_unit)
                if new_parameter:
                    new_tsvs[i].value.ito(new_parameter.unit)

    def _resample_discreet(
        self,
        operation: str,
        old_tsvs: List[TimeSeriesValue],
        new_tsvs: List[TimeSeriesValue],
        bounds: List[Any],
        entire_interval: Optional[bool] = None,
    ) -> None:
        is_inst = (
            cast(ParameterType, self.parameter_type).get_raw_name() == "Instantaneous"
        )
        require_entire_interval = (
            entire_interval
            if entire_interval is not None
            else not is_inst and operation != _RESAMPLE_OP_PREVIOUS
        )
        prev_lo = None
        prev_hi = None
        for i, boundary in [(i, b) for (i, b) in enumerate(bounds) if b is not None]:
            lo, hi = boundary
            # -------------------------------------------------------- #
            # get a list of valid indices that end in the new interval #
            # -------------------------------------------------------- #
            if prev_hi is None:
                indices = [
                    j for j in range(hi + 1 if lo == hi else hi) if old_tsvs[j].is_valid
                ]
            else:
                if operation == _RESAMPLE_OP_PREVIOUS and hi == prev_hi:
                    prev_hi -= 1
                elif prev_hi == prev_lo and operation != _RESAMPLE_OP_PREVIOUS:
                    prev_hi += 1
                indices = [
                    j
                    for j in range(prev_hi, hi + 1 if lo == hi else hi)
                    if old_tsvs[j].is_valid
                ]
            if require_entire_interval and operation != _RESAMPLE_OP_PREVIOUS:
                # ---------------------------------------------------------- #
                # reduce the indices to those that start in the new interval #
                # ---------------------------------------------------------- #
                new_interval_start = (
                    new_tsvs[i - 1].time
                    if i > 0
                    else (
                        new_tsvs[0].time - (new_tsvs[1].time - new_tsvs[0].time)
                        if len(new_tsvs) > 1
                        else None
                    )
                )
                if not new_interval_start:
                    indices = []
                else:
                    for k in range(len(indices)):
                        old_interval_start = (
                            old_tsvs[indices[k] - 1].time
                            if indices[k] > 0
                            else (
                                old_tsvs[0].time - (old_tsvs[1].time - old_tsvs[0].time)
                                if len(old_tsvs) > 1
                                else None
                            )
                        )
                        if (
                            old_interval_start is not None
                            and old_interval_start >= new_interval_start
                        ):
                            indices = indices[k:]
                            break
                    else:
                        indices = []
            if operation == _RESAMPLE_OP_COUNT:
                # ----------- #
                # count valid #
                # ----------- #
                new_val = float(len(indices))
            elif operation in (_RESAMPLE_OP_MAXIMUM, _RESAMPLE_OP_MINIMUM):
                # ------------------ #
                # maximum or minimum #
                # ------------------ #
                vals = [old_tsvs[j].value.magnitude for j in indices]
                func = max if operation == _RESAMPLE_OP_MAXIMUM else min
                new_val = func(vals) if vals else math.nan
            elif operation == _RESAMPLE_OP_PREVIOUS:
                # -------- #
                # previous #
                # -------- #
                if hi == lo:
                    new_val = (
                        old_tsvs[indices[-1] - 1].value.magnitude
                        if indices and indices[-1] != 0
                        else math.nan
                    )
                else:
                    new_val = (
                        old_tsvs[indices[-1]].value.magnitude if indices else math.nan
                    )
            else:
                raise TimeSeriesException(
                    f"Unexpected discreet resample operation: {operation}"
                )
            new_tsvs[i].value = UnitQuantity(new_val, self.unit)
            prev_lo = lo
            prev_hi = hi

    @staticmethod
    def _round_off(v: float, precision: int, tens_place: int) -> float:
        if np.isnan(v) or np.isinf(v):
            return v
        exponent = 0
        factor = 1.0
        v2 = abs(v)
        while v2 > 10.0:
            exponent += 1
            factor /= 10.0
            v2 /= 10.0
        while v2 < 1.0:
            exponent -= 1
            factor *= 10.0
            v2 *= 10.0
        precision = min(exponent + 1 - tens_place, precision)
        if precision >= 0:
            factor_precision = 10 ** (precision - 1)
            v3 = np.rint(factor_precision * v2) / factor_precision / factor
            if v < 0.0:
                v3 = -v3
        else:
            v3 = 0.0
        return round(float(v3), 10)

    @staticmethod
    def _screen_with_constant_value(
        times: list[HecTime],
        values: list[float],
        qualities: Optional[list[int]],
        duration: Duration,
        missing_limit: float,
        reject_limit: float,
        question_limit: float,
        min_threshold: float,
        percent_valid_required: float,
    ) -> list[int]:
        total_count = len(times)
        if total_count < 2:
            raise TimeSeriesException("Operation requires a time series of length > 1")
        if qualities is None:
            qualities_in = total_count * [0]
        else:
            qualities_in = qualities
        if len(values) != total_count:
            raise TimeSeriesException(
                f"Lists of times and values must be of same length, got {total_count} and {len(values)}"
            )
        if len(qualities_in) != total_count:
            raise TimeSeriesException(
                f"Lists of times and qualities must be of same length, got {total_count} and {len(qualities_in)}"
            )
        if (
            not math.isnan(percent_valid_required)
            and not 0 <= percent_valid_required <= 100
        ):
            raise TimeSeriesException(
                f"percent_valid_required must be in range 0..100, got {percent_valid_required}"
            )
        # ----------------- #
        # set the variables #
        # ----------------- #
        qualities_out = total_count * [0]
        test_missing = not math.isnan(missing_limit)
        test_reject = not math.isnan(reject_limit)
        test_question = not math.isnan(question_limit)
        if test_missing:
            if test_reject and missing_limit >= reject_limit:
                raise TimeSeriesException(
                    "Missing limit must be less than Reject limit"
                )
            if test_question and missing_limit >= question_limit:
                raise TimeSeriesException(
                    "Missing limit must be less than Question limit"
                )
        if test_reject:
            if test_question and reject_limit >= question_limit:
                raise TimeSeriesException(
                    "Reject limit must be less than Question limit"
                )
        quality_text = {
            "okay": "Screened Okay No_Range Original None None None Unprotected",
            "missing": "Screened Missing No_Range Modified Automatic Missing Duration_Value Unprotected",
            "question": "Screened Questionable No_Range Original None None Duration_Value Unprotected",
            "reject": "Screened Rejected No_Range Original None None Duration_Value Unprotected",
        }
        okay_code = Quality(quality_text["okay"].split()).code
        missing_code = Quality(quality_text["missing"].split()).code
        question_code = Quality(quality_text["question"].split()).code
        reject_code = Quality(quality_text["reject"].split()).code
        # ---------------- #
        # do the screening #
        # ---------------- #
        for last in range(1, total_count):
            # --------------------------- #
            # don't screen invalid values #
            # --------------------------- #
            if (
                math.isnan(values[last])
                or math.isinf(values[last])
                or Quality(qualities_in[last]).score == 0
            ):
                continue
            if (
                values[last] < min_threshold
            ):  # always False if min_threshold is math.nan:
                continue
            # ---------------------------------------------------------------------------------------------- #
            # get the times that contribute to the accumulation at this time step for the specified duration #
            # ---------------------------------------------------------------------------------------------- #
            for first in range(last + 1)[::-1]:
                minutes = (
                    cast(TimeSpan, (times[last] - times[first])).total_seconds() / 60
                )
                if minutes >= duration.minutes:
                    break
            if minutes < duration.minutes:
                continue
            span = range(first, last + 1)
            # ---------------------------------- #
            # verify we have enough valid values #
            # ---------------------------------- #
            valid = [
                values[i]
                for i in span
                if not math.isnan(values[i])
                and not math.isinf(values[i])
                and Quality(qualities_in[i]).score > 0
            ]
            if (
                100.0 * len(valid) / len(span) < percent_valid_required
            ):  # will always be False with math.nan
                continue
            # ---------------------------------- #
            # get the max change in the duration #
            # ---------------------------------- #
            max_change = max(valid) - min(valid)
            # ------------------------- #
            # set the retuned qualities #
            # ------------------------- #
            if test_missing and max_change < missing_limit:
                qualities_out[last] = missing_code
            elif test_reject and max_change < reject_limit:
                qualities_out[last] = reject_code
            elif test_question and max_change < question_limit:
                qualities_out[last] = question_code
            elif test_missing or test_reject or test_question:
                qualities_out[last] = okay_code

        return qualities_out

    @staticmethod
    def _screen_with_duration_magnitude(
        times: list[HecTime],
        values: list[float],
        qualities: Optional[list[int]],
        duration: Duration,
        min_missing_limit: float,
        min_reject_limit: float,
        min_question_limit: float,
        max_question_limit: float,
        max_reject_limit: float,
        max_missing_limit: float,
        percent_valid_required: float,
    ) -> list[int]:
        total_count = len(times)
        if total_count < 2:
            raise TimeSeriesException("Operation requires a time series of length > 1")
        if qualities is None:
            qualities_in = total_count * [0]
        else:
            qualities_in = qualities
        if len(values) != total_count:
            raise TimeSeriesException(
                f"Lists of times and values must be of same length, got {total_count} and {len(values)}"
            )
        if len(qualities_in) != total_count:
            raise TimeSeriesException(
                f"Lists of times and qualities must be of same length, got {total_count} and {len(qualities_in)}"
            )
        if (
            not math.isnan(percent_valid_required)
            and not 0 <= percent_valid_required <= 100
        ):
            raise TimeSeriesException(
                f"percent_valid_required must be in range 0..100, got {percent_valid_required}"
            )
        if duration.is_bop:
            raise TimeSeriesException(
                "Method is currently suitable for End-of-Period durations only"
            )
        # ----------------- #
        # set the variables #
        # ----------------- #
        qualities_out = total_count * [0]
        test_min_missing = not math.isnan(min_missing_limit)
        test_min_reject = not math.isnan(min_reject_limit)
        test_min_question = not math.isnan(min_question_limit)
        test_max_question = not math.isnan(max_question_limit)
        test_max_reject = not math.isnan(max_reject_limit)
        test_max_missing = not math.isnan(max_missing_limit)
        quality_text = {
            "okay": "Screened Okay No_Range Original None None None Unprotected",
            "missing": "Screened Missing No_Range Modified Automatic Missing Duration_Value Unprotected",
            "question": "Screened Questionable No_Range Original None None Duration_Value Unprotected",
            "reject": "Screened Rejected No_Range Original None None Duration_Value Unprotected",
        }
        okay_code = Quality(quality_text["okay"].split()).code
        missing_code = Quality(quality_text["missing"].split()).code
        question_code = Quality(quality_text["question"].split()).code
        reject_code = Quality(quality_text["reject"].split()).code
        base_time = times[0] - (
            times[1] - times[0]
        )  # assume the first interval is equal to the second

        # ---------------- #
        # do the screening #
        # ---------------- #
        for last in range(total_count):
            # --------------------------- #
            # don't screen invalid values #
            # --------------------------- #
            if (
                math.isnan(values[last])
                or math.isinf(values[last])
                or Quality(qualities_in[last]).score == 0
            ):
                continue
            # ---------------------------------------------------------------------------------------------- #
            # get the times that contribute to the accumulation at this time step for the specified duration #
            # ---------------------------------------------------------------------------------------------- #
            if last == 0:
                # ------------------------------------------------ #
                # assume the first interval is equal to the second #
                # ------------------------------------------------ #
                first = 0
                minutes = cast(TimeSpan, (times[last] - base_time)).total_seconds() / 60
            else:
                for first in range(last + 1)[::-1]:
                    first_time = base_time if first == 0 else times[first - 1]
                    minutes = (
                        cast(TimeSpan, (times[last] - first_time)).total_seconds() / 60
                    )
                    if minutes >= duration.minutes:
                        break
            if minutes < duration.minutes:
                continue
            span = range(first, last + 1)
            if first == last:
                # ------------------ #
                # single valid value #
                # ------------------ #
                total = values[last]
            else:
                # ----------------------------------------------- #
                # verify we have enough valid contributing values #
                # ----------------------------------------------- #
                valid = [
                    i
                    for i in span
                    if not math.isnan(values[i])
                    and not math.isinf(values[i])
                    and Quality(qualities_in[i]).score > 0
                ]
                if (
                    100.0 * len(valid) / len(span) < percent_valid_required
                ):  # will always be False with math.nan
                    continue
                # -------------------------------------------------- #
                # enumerate the contributions so we can adjust later #
                # -------------------------------------------------- #
                contrib = [
                    (values[i], 0)[
                        bool(
                            math.isnan(values[i])
                            or math.isinf(values[i])
                            or Quality(qualities_in[i]).score == 0
                        )
                    ]
                    for i in span
                ]
                total = sum(contrib)
            extra_minutes = minutes % duration.minutes
            # ----------------------------------------------------------- #
            # adjust for accumulations that exceed the specified duration #
            # ----------------------------------------------------------- #
            if extra_minutes:
                # ----------------------------------------------------------- #
                # take all of the extra out of the first value's contribution #
                # ----------------------------------------------------------- #
                first_time = base_time if first == 0 else times[first - 1]
                first_interval = (
                    cast(TimeSpan, (times[first] - first_time)).total_seconds() / 60
                )
                total -= contrib[0] * float(extra_minutes) / first_interval
            # ------------------------- #
            # set the retuned qualities #
            # ------------------------- #
            if (test_min_missing and total < min_missing_limit) or (
                test_max_missing and total > max_missing_limit
            ):
                qualities_out[last] = missing_code
            elif (test_min_reject and total < min_reject_limit) or (
                test_max_reject and total > max_reject_limit
            ):
                qualities_out[last] = reject_code
            elif (test_min_question and total < min_question_limit) or (
                test_max_question and total > max_question_limit
            ):
                qualities_out[last] = question_code
            elif (
                test_min_missing
                or test_max_missing
                or test_min_reject
                or test_max_reject
                or test_min_question
                or test_max_question
            ):
                qualities_out[last] = okay_code

        return qualities_out

    def _tsv(self, row: pd.DataFrame) -> Any:
        # --------------------------------------------- #
        # create a TimeSeriesValue from a DataFrame row #
        # --------------------------------------------- #
        return cast(
            Any,
            TimeSeriesValue(
                row.name,
                UnitQuantity(row.value, self.unit),
                cast(Union[Quality, int], int(row.quality)),
            ),
        )

    @staticmethod
    def _unProtected_indices(df: pd.DataFrame) -> list[np.datetime64]:
        return cast(
            list[np.datetime64],
            df[
                (
                    df["quality"].astype("int64")
                    & 0b1000_0000_0000_0000_0000_0000_0000_0000
                )
                == 0
            ].index,
        )

    @staticmethod
    def _valid_indices(df: pd.DataFrame) -> list[np.datetime64]:
        return cast(
            list[np.datetime64],
            df.index[
                ~(
                    (df["value"].isna())
                    | (np.isinf(df["value"]))
                    | (df["quality"] == 5)
                    | ((df["quality"].astype("int64") & 0b1_0000) != 0)
                )
            ],
        )

    def _validate(self) -> None:
        # ------------------------------- #
        # validate times against interval #
        # ------------------------------- #
        if self._skip_validation:
            return
        if self.is_any_regular and self._data is not None and not self._data.empty:
            if self._timezone:
                my_datetimes = (
                    self._data.copy()
                    .tz_localize(None)
                    .tz_localize(
                        self._timezone,
                        ambiguous=np.zeros(len(self._data.index), dtype=bool),
                    )
                    .index.to_list()
                )
            else:
                my_datetimes = self._data.index.to_list()
            interval_times = self.interval.get_datetime_index(
                start_time=my_datetimes[0],
                count=len(my_datetimes),
                time_zone=self.time_zone,
            ).to_list()
            for dt in my_datetimes:
                if not dt in interval_times:
                    raise (
                        TimeSeriesException(
                            f"Time {dt} is not consistent with interval {self.interval.name} beginning at {my_datetimes[0]}"
                        )
                    )

    def accum(self, in_place: bool = False) -> "TimeSeries":
        """
        Returns a time series whose values are the accumulation of values in this time series.

        Missing values are ignored; the accumulation at those times is the same as for the
        previous time.

        If a selection is present, all non-selected items are set to missing before the
        accumulation is computed. They remain missing in the retuned time series.

        **Restrictions**
        * May be performed only on time series with accumulatable base parameters. Use [Parameter.accumulatable_base_parameters()](parameter.html#Parameter.accumulatable_base_parameters) to
            list the accumulatable base parameters.
        * May be performed only on Instantaneous, Average, or Total time series (CWMS: Inst, Ave, Total, DSS: INST-VAL, INST-CUM, PER-CUM)

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            in_place (bool, optional): If True, this object is modified and retured, otherwise
                a copy of this object is modified and returned.. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data or one of the restrictions listed above is violated.

        Returns:
            TimeSeries: The accumulation time series
        """
        if self.parameter.basename not in Parameter.accumulatable_base_parameters():
            raise TimeSeriesException(
                f"Cannot accumulate a time series with parameter of {self.parameter.name}, "
                f"base parameter must be one of {Parameter.accumulatable_base_parameters()}"
            )
        if cast(ParameterType, self.parameter_type).get_raw_name() in (
            "Constant",
            "Minimum",
            "Maximum",
        ):
            raise TimeSeriesException(
                f"Cannot perform accumulate a {cast(ParameterType, self.parameter_type).name} time series."
            )
        target = self if in_place else self.copy()
        if target._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if target.has_selection:
            target._data.loc[~target._data["selected"], "value"] = np.nan
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if target is not self:
                    target.iselect(Select.ALL)
        target._data["accum"] = target._data["value"].cumsum().ffill()
        target._data["value"] = target._data["accum"]
        target._data.drop(columns=["accum"])
        return target

    def aggregate(
        self,
        func: Union[list[Union[Callable[[Any], Any], str]], Callable[[Any], Any], str],
    ) -> Any:
        """
        Perform an aggregation of the values in a time series time series.

        Args:
            func (Union[list[Union[Callable[[Any], Any], str]],Callable[[Any], Any], str]): The aggregation function(s).
            May be one of:
                <ul>
                <li><b>list[Union[Callable[[Any], Any], str]]</b>: A list comprised of items from the following two options
                (note that there is overlap between the python builtin functions and the pandas functions)
                <li><b>Callable[[Any], Any]</b>: Must take an iterable of floats and return a float timeseries<br>
                    May be a function defined in the code (including lambda funtions) or a standard python aggregation function:
                    <ul>
                    <li><code>all</code></li>
                    <li><code>any</code></li>
                    <li><code>len</code></li>
                    <li><code>max</code></li>
                    <li><code>min</code></li>
                    <li><code>sum</code></li>
                    <li><code>math.prod</code></li>
                    <li><code>statistics.fmean</code></li>
                    <li><code>statistics.geometric_mean</code></li>
                    <li><code>statistics.harmonic_mean</code></li>
                    <li><code>statistics.mean</code></li>
                    <li><code>statistics.median</code></li>
                    <li><code>statistics.median_grouped</code></li>
                    <li><code>statistics.median_high</code></li>
                    <li><code>statistics.median_low</code></li>
                    <li><code>statistics.mode</code></li>
                    <li><code>statistics.multimode</code></li>
                    <li><code>statistics.pstdev</code></li>
                    <li><code>statistics.pvariance</code></li>
                    <li><code>statistics.quantiles</code></li>
                    <li><code>statistics.stdev</code></li>
                    <li><code>statistics.variance</code></li>
                    </ul>
                </li>
                <li><b>str</b>: Must be the name of a pandas aggregation function:
                    <ul>
                    <li><code>"all"</code></li>
                    <li><code>"any"</code></li>
                    <li><code>"count"</code></li>
                    <li><code>"describe"</code></li>
                    <li><code>"first"</code></li>
                    <li><code>"last"</code></li>
                    <li><code>"max"</code></li>
                    <li><code>"mean"</code></li>
                    <li><code>"median"</code></li>
                    <li><code>"min"</code></li>
                    <li><code>"nunique"</code></li>
                    <li><code>"prod"</code></li>
                    <li><code>"sem"</code></li>
                    <li><code>"size"</code></li>
                    <li><code>"skew"</code></li>
                    <li><code>"std"</code></li>
                    <li><code>"sum"</code></li>
                    <li><code>"var"</code></li>
                    </ul>
                </li>
                </ul>

        Raises:
            TimeSeriesException: If the time series has no data, or if there are less than two items
            to aggregate over.

        Returns:
            The result of the aggregation function(s)
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if len(selected) < 2:
                raise TimeSeriesException(
                    "Cannot perform aggregation with fewer than 2 items selected"
                )
            return selected["value"].agg(func)
        else:
            if len(self._data) < 2:
                raise TimeSeriesException(
                    "Cannot perform aggregation with fewer than 2 items"
                )
            if func in (stat.stdev, stat.pstdev):
                # ------------------------------------------------------------------#
                # why don't these functions just return NaN if the encounter a NaN? #
                # ------------------------------------------------------------------#
                return (
                    cast(Callable[[Any], Any], func)(self.values)
                    if all([np.isfinite(v) for v in self.values])
                    else np.nan
                )
            else:
                return self._data["value"].agg(func)

    @staticmethod
    def aggregate_ts(
        func: Union[list[Union[Callable[[Any], Any], str]], Callable[[Any], Any], str],
        timeseries: list["TimeSeries"],
    ) -> "TimeSeries":
        """
        Generate a time series that is an aggregation of multiple time series.

        Note that some usages (marked with <sup>1</sup>, <sup>2</sup>, <sup>3</sup>, or <sup>4</sup>) generate non-standard TimeSeries results.
        In these cases the `.data` property of the TimeSeries should be used directly instead of using the `.values` property or using the
        TimeSeries in further operations.

        Args:
            func (Union[list[Union[Callable[[Any], Any], str]], Callable[[Any], Any], str]): The aggregation function(s).
            May be one of:
                <ul>
                <li><b>list[Union[Callable[[Any], Any], str]]</b><sup>1</sup>: A list comprised of items from the following two options
                (note that there is overlap between the python builtin functions and the pandas functions)
                <li><b>Callable[[Any], Any]</b>: Must take an iterable of floats and return a single value<br>
                    May be a function defined in the code (including lambda funtions) or a standard python aggregation function:
                    <ul>
                    <li><code>all</code><sup>2</sup></li>
                    <li><code>any</code><sup>2</sup></li>
                    <li><code>len</code></li>
                    <li><code>max</code></li>
                    <li><code>min</code></li>
                    <li><code>sum</code></li>
                    <li><code>math.prod</code></li>
                    <li><code>statistics.fmean</code></li>
                    <li><code>statistics.geometric_mean</code></li>
                    <li><code>statistics.harmonic_mean</code></li>
                    <li><code>statistics.mean</code></li>
                    <li><code>statistics.median</code></li>
                    <li><code>statistics.median_grouped</code></li>
                    <li><code>statistics.median_high</code></li>
                    <li><code>statistics.median_low</code></li>
                    <li><code>statistics.mode</code></li>
                    <li><code>statistics.multimode</code><sup>3</sup></li>
                    <li><code>statistics.pstdev</code></li>
                    <li><code>statistics.pvariance</code></li>
                    <li><code>statistics.quantiles</code><sup>3</sup></li>
                    <li><code>statistics.stdev</code></li>
                    <li><code>statistics.variance</code></li>
                    </ul>
                </li>
                <li><b>str</b>: Must be the name of a pandas aggregation function:
                    <ul>
                    <li><code>"all"</code><sup>2</sup></li>
                    <li><code>"any"</code><sup>2</sup></li>
                    <li><code>"count"</code></li>
                    <li><code>"describe"</code><sup>1</sup></li>
                    <li><code>"first"</code></li>
                    <li><code>"last"</code></li>
                    <li><code>"max"</code></li>
                    <li><code>"mean"</code></li>
                    <li><code>"median"</code></li>
                    <li><code>"min"</code></li>
                    <li><code>"nunique"</code></li>
                    <li><code>"prod"</code></li>
                    <li><code>"sem"</code></li>
                    <li><code>"size"</code><sup>4</sup></li>
                    <li><code>"skew"</code></li>
                    <li><code>"std"</code></li>
                    <li><code>"sum"</code></li>
                    <li><code>"var"</code></li>
                    </ul>
                </li>
                </ul>
            timeseries (list[TimeSeries]): The time series for the function to aggregate over

        <sup>1</sup>The `.data` property is a DataFrame with named columns.<br>
        <sup>2</sup>The "Values" column of the `.data` property contains bool values float values<br>
        <sup>3</sup>The "Values" column of the `.data` property contains lists of values instead of float values.<br>
        <sup>4</sup>The `.data` property is a DataFrame with one unnamed column.<br>

        Raises:
            TimeSeriesException: If less than two of the time series have data, or if the time series have
                no common times.

        Returns:
            TimeSeries: The time series that is the result of the aggregation function. The times series name will be
            modified from the first time series specified in the following way:
            * The parameter will be "Code"
            * the version will be "Aggregate"
        """
        try:
            # ----------------------------------- #
            # filter out time series without data #
            # ----------------------------------- #
            with_data = [ts for ts in timeseries if ts.data is not None]
            if len(with_data) < 2:
                raise TimeSeriesException(
                    "More that one time series with data is required"
                )
            # ------------------------------------------------------------------------------------------------- #
            # generate an index common to all time series and create a list of DataFrames with only those times #
            # ------------------------------------------------------------------------------------------------- #
            common_index = cast(pd.DataFrame, with_data[0].data).index
            for ts in with_data[1:]:
                common_index = common_index.intersection(
                    cast(pd.DataFrame, ts.data).index
                )
                if len(common_index) == 0:
                    raise TimeSeriesException("Time series do not include common times")
            common_index.name = "time"
            dfs = [cast(pd.DataFrame, ts.data).loc[common_index] for ts in with_data]
            # ---------------------------------------- #
            # generate and return a result time series #
            # ---------------------------------------- #
            ts = timeseries[0].copy(include_data=False)
            ts.ito("Code").version = "Aggregate"
            if func in (stat.stdev, stat.pstdev):
                # ------------------------------------------------------------------#
                # why don't these functions just return NaN if the encounter a NaN? #
                # ------------------------------------------------------------------#
                def func2(*args: Any) -> float:
                    v = (
                        cast(Callable[[Any], Any], func)(*args)
                        if all([np.isfinite(x) for x in args[0].to_list()])
                        else np.nan
                    )
                    return v

                ts._data = pd.concat(dfs)[["value"]].groupby(level=0).agg(func2)
            else:
                ts._data = pd.concat(dfs)[["value"]].groupby(level=0).agg(func)
            ts._data.set_index(common_index)
            ts._data["quality"] = 0
            return ts
        finally:
            for i in range(len(timeseries)):
                if timeseries[i].selection_state == SelectionState.TRANSIENT:
                    timeseries[i].select(Select.ALL)

    @property
    def can_determine_unit_system(self) -> bool:
        """
        Returns whether the unit of this time series is recognized as an English unit, or a Metric unit, but not both

        Operations:
            Read Only
        """
        return self.is_english != self.is_metric

    def centered_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Computes and returns a time series that is the centered moving average of this time series.

        A centered moving average sets the value at each time to be the average of the values at that
        time and a number of previous and following consecutive times.

        Args:
            window (int): The number of values to average over. The result at each time will be
                the average of the values at ((window-1)/2) previous times, the value at the current
                time, and the values at ((window-1)/2) following times. The span between times is not
                accounted for so discretion should be used if the time series is irregular. Must be an odd number.
            only_valid (bool): Specifies whether to only average over windows where every value is
                valid. If False, the average at any given time may be computed using fewer values
                that specified in the window parameter.
            use_reduced (bool): Specifies whether to allow averages using less than window number
                of values will be computed at the beginning and end of the times series. If False, the
                values at the first and last ((window-1)/2) times will be set to missing.
            in_place (bool, optional): If True, this time series is modified and returned.
                Otherwise this time series is not modified. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data or if the window is invalid.

        Returns:
            TimeSeries: The averaged time series
        """
        return self._moving_average(
            "CENTERED", window, only_valid, use_reduced, in_place
        )

    def copy(self, include_data: bool = True) -> "TimeSeries":
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
        other._version_time = (
            None if self._version_time is None else self._version_time.copy()
        )
        other._timezone = self._timezone
        if include_data and self._data is not None:
            other._data = self._data.copy()
            other._expanded = self._expanded
        return other

    def collapse(self, in_place: bool = False) -> "TimeSeries":
        """
        Collapses a regular time series (either this one or a copy of this one), removing all missing values unless they are
        either protected or marked as part of the current selection.

        Irregular time series (including pseudo-regular time series) are not affected.

        Does not alter any selection, even if selection state is `SelectionState.TRANSIENT`. Selected items remain
        selected after collapse even though their location in the data may change.

        Args:
            in_place (bool, optional): Specifies whether to collapse this time series (True) or a copy of this time series (False).
            Defaults to False.

        Returns:
            TimeSeries: The collapsed time series
        """
        # --------------------------------------- #
        # short circuit for irregular time series #
        # --------------------------------------- #
        if self.is_any_irregular:
            return self if in_place else self.copy()
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        df = cast(pd.DataFrame, target._data)  # does not recognize selection
        # --------------- #
        # set the results #
        # --------------- #
        if self.has_selection:
            condition = (
                ~df["value"].isna()
                | ((df["quality"] & (1 << 31)) != 0)
                | df["selected"]
            )
        else:
            condition = ~df["value"].isna() | ((df["quality"] & (1 << 31)) != 0)
        target._data = df[condition]
        target._expanded = False
        return target

    @property
    def context(self) -> Optional[str]:
        """
        The context of the time series. Valid contexts are "CWMS" and "DSS"

        Operations:
            Read/Write
        """
        return self._context

    @context.setter
    def context(self, ctx: str) -> None:
        self._convert_to_context(ctx)

    def convert_to_time_zone(
        self,
        time_zone: Union["HecTime", datetime, ZoneInfo, str],
        on_tz_not_set: int = 1,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Converts a time series (either this one or a copy of it) to the spcified time zone and returns it

        Args:
            time_zone (Union[HecTime, datetime, ZoneInfo, str]): The target time zone or object containg the target time zone.
                Use `"local"` to specify the system time zone.
            on_tz_not_set (int, optional): Specifies behavior if this object has no time zone attached. Defaults to 1.
                - `0`: Quietly behave as if this object had the local time zone attached.
                - `1`: (default) Same as `0`, but issue a warning.
                - `2`: Raise an exception preventing objectes with out time zones attached from using this method.
            in_place (bool): Specifies whether to convert this time series (True) or a copy of it (False). Defaults to False

        Returns:
            TimeSeries: The converted time series
        """
        tz = HecTime._get_zone_info_obj(time_zone)
        target = self if in_place else self.copy()
        if target._data is not None:
            if not target._timezone:
                localzone_name = tzlocal.get_localzone_name()
                if on_tz_not_set > 0:
                    message = f"{repr(target)} has no time zone when setting to {tz}, assuming local time zone of {localzone_name}"
                    if on_tz_not_set > 1:
                        raise TimeSeriesException(message)
                    else:
                        warnings.warn(
                            message + ". Use on_tz_not_set=0 to prevent this message.",
                            UserWarning,
                        )
                target._data = target._data.tz_localize(
                    localzone_name,
                    ambiguous=np.zeros(len(target._data.index), dtype=bool),
                    nonexistent="NaT",
                )
            target._data = target._data.tz_convert(tz)
            if target._version_time is not None:
                if target._version_time.tzinfo is None:
                    target._version_time = target._version_time.label_as_time_zone(tz)
                else:
                    target._version_time = target._version_time.convert_to_time_zone(tz)
        target._timezone = str(tz)
        return target

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

    def diff(self, in_place: bool = False) -> "TimeSeries":
        """
        Returns a time series whose values are the differences of successive values in this time series.

        A missing value at a specific time in the source time series will cause the value at that
        and the next time in the result time sereies to be missing.

        If a selection is present, all non-selected items are set to missing before the
        accumulation is computed. They remain missing in the retuned time series.

        **Restrictions**
        * May be performed only on time series with accumulatable base parameters. Use [Parameter.accumulatable_base_parameters()](parameter.html#Parameter.accumulatable_base_parameters) to
            list the accumulatable base parameters.
        * May be performed only on Instantaneous, Average, or Total time series (CWMS: Inst, Ave, Total, DSS: INST-VAL, INST-CUM, PER-CUM)

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            in_place (bool, optional): If True, this object is modified and retured, otherwise
                a copy of this object is modified and returned.. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data.

        Returns:
            TimeSeries: The time series of differences
        """
        return self._diff(time_based=False, in_place=in_place)

    @property
    def duration(self) -> Optional[Duration]:
        """
        The duration object

        Operations:
            Read Only
        """
        return self._duration

    def estimate_missing_values(
        self,
        max_missing_count: int,
        accumulation: bool = False,
        estimate_rejected: bool = True,
        set_questioned: bool = True,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Estimates missing values in a time series using specified criteria, and returns the estimated time series (either this time series or a copy of it).
        Values are estimated using linear interpolation between the bounding valid values

        Args:
            max_missing_count (int): The maximum number of consecutive missing values that will be replaced with estimates.
                Groups of consecutive missing values larger than this number remain missing (except see `accumulation`).
            accumulation (bool, optional): Specifies whether the time series is an accumulation (e.g., cumulative precipitaion).
                The estimation behavior for accumulation time series differs in that
                * If the bounding valid values for a group of consecutive missing values decrease with increasing time, no estimations are performed
                * If the bounding valid values for a group of consecutive missing values are equal, the all missing values in the group are replaced
                    with the same value, without regard to `max_missing_count`
                Defaults to False.
            estimate_rejected (bool, optional): Specifies whether to treat values in the time series with Rejected quality as missing. Defaults to True.
            set_questioned (bool, optional): Specifies whether to set the quality for estimated values to Questionable. If False, quality is set to Okay. Defaults to True.
            in_place (bool, optional): Specfies whether to modify and return this time series (True) or a copy of this time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If there are no values in the time series

        Returns:
            TimeSeries: The estimated time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        quality_code = [
            Quality(
                "Screened Okay No_Range Modified Automatic Lin_Interp None Unprotected".split()
            ).code,
            Quality(
                "Screened Questionable No_Range Modified Automatic Lin_Interp None Unprotected".split()
            ).code,
        ][int(set_questioned)]
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        df_protected = df.loc[
            (df["quality"] & 0b1000_0000_0000_0000_0000_0000_0000_0000) != 0
        ].copy()
        # ----------------- #
        # do the estimation #
        # ----------------- #
        if estimate_rejected:
            mask = (df["quality"] & 0b1_1111) == 0b1_0001
            df.loc[mask, "value"] = np.nan
        original = df["value"].copy()
        if accumulation:

            def conditional_interpolation(
                df: pd.DataFrame, max_nan: int
            ) -> pd.DataFrame:
                values = df["value"]
                is_nan = values.isna()
                groups = (
                    is_nan != is_nan.shift()
                ).cumsum()  # Identify groups of consecutive NaN/Non-NaN
                # Iterate through groups
                for group_id, group in df.groupby(groups):
                    if not group["value"].isna().any():
                        continue  # Skip non-NaN groups
                    # Find indices for the current NaN group
                    nan_indices = group.index
                    prev_pos = cast(int, df.index.get_loc(nan_indices[0])) - 1
                    next_pos = cast(int, df.index.get_loc(nan_indices[-1])) + 1
                    # Check bounds
                    if prev_pos < 0 or next_pos >= len(values):
                        continue  # Skip interpolation if out of bounds
                    # Get values before and after the NaNs
                    prev_index = df.index[prev_pos]
                    next_index = df.index[next_pos]
                    prev_value = values[prev_index]
                    next_value = values[next_index]
                    # Apply conditions
                    if next_value < prev_value:
                        continue  # Skip interpolation if the next value is less than the previous
                    if prev_value == next_value:
                        df.loc[nan_indices, "value"] = (
                            prev_value  # Fill with the same value
                        )
                        continue
                    # Check if NaN count exceeds the limit
                    if len(nan_indices) > max_nan:
                        continue
                    # Perform interpolation
                    df.loc[nan_indices, "value"] = values.interpolate().loc[nan_indices]
                return df

            df = conditional_interpolation(df, max_missing_count)
        else:

            def interp(series: pd.Series, max_nan: int) -> pd.Series:  # type: ignore
                # get a mask of NaN locations
                is_nan = series.isna()
                # identify groups of consecutive values
                groups = (is_nan != is_nan.shift()).cumsum()
                # count the number of NaNs in each group
                nan_counts = is_nan.groupby(groups).transform("sum")
                # replace NaNs we don't want interpolated
                mask = ~((nan_counts > max_nan) & is_nan)
                nan_indicies = mask.where(~mask).dropna().index
                series[nan_indicies] = 0
                # interpolate the remaining NaNs and restore the un-interpolated NaNs
                series = series.interpolate()
                series[nan_indicies] = np.nan
                return series

            df.loc[:, "value"] = interp(df["value"].copy(), max_missing_count)
        modified = (original.isna()) & (df["value"].notna())
        df.loc[modified, "quality"] = quality_code
        # --------------- #
        # set the results #
        # --------------- #
        for idx in df_protected.index:
            df.loc[idx, "value"] = df_protected.loc[idx, "value"]
            df.loc[idx, "quality"] = df_protected.loc[idx, "quality"]
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def expand(
        self,
        start_time: Optional[Union[str, datetime, HecTime]] = None,
        end_time: Optional[Union[str, datetime, HecTime]] = None,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Expands a regular time series (either this one or a copy of this one) so that there are no gaps in time
        (fills gaps with missing values) and returns the expanded time series. If `start_time` and/or `end_time`
        are specified, the times between the start_time and the first time and between the last time and the end_time
        are considered as gaps to be filled.

        Irregular time series (including pseudo-regular time series) are not affected.

        Does not alter any selection, even if selection state is `SelectionState.TRANSIENT`. Selected items remain
        selected after expansion even though their location in the data may change.

        Args:
            start_time (Optional[Union[str, datetime, HecTime]]): The beginning of the timespan before the first time
                to fill with missing values. Does not need to fall on the time series interval. If not at least one full
                interval prior to the first time, no missing values will be inserted before the first time. Defaults to None.
            end_time (Optional[Union[str, datetime, HecTime]]): The end of the timespan after the last time to fill
                with missing values. Does not need to fall on the time series interval. If not at least one full interval after
                the last time, no missing values will be inserted after the last time. Defaults to None.
            in_place (bool, optional): Specifies whether to expand this time series (True) or a copy of this time series (False).
            Defaults to False.

        Returns:
            TimeSeries: The expanded time series
        """
        target = self if in_place else self.copy()
        if self.is_any_regular and not target._expanded:
            if target._data is None or target._data.empty:
                if start_time and end_time:
                    index = target.interval.get_datetime_index(
                        start_time, end_time, None, None, self.time_zone, "times"
                    )
                    self._data = pd.DataFrame(
                        {"value": len(index) * [math.nan], "quality": len(index * [5])},
                        index=index,
                    )
            else:
                start = None if start_time is None else HecTime(start_time).datetime()
                end = None if end_time is None else HecTime(end_time).datetime()
                if self._data is not None and not self._data.empty:
                    my_datetimes = self._data.index.to_list()
                    first, last = my_datetimes[0], my_datetimes[-1]
                else:
                    first, last = None, None
                if start is None and first is None:
                    raise TimeSeriesException(
                        "Cannot expand an empty time series without a valid start time"
                    )
                if end is None and last is None:
                    raise TimeSeriesException(
                        "Cannot expand an empty time series without a valid end time"
                    )
                _start_time = (
                    start
                    if first is None
                    else first if start is None else min(start, first)
                )
                _end_time = (
                    end if last is None else last if end is None else max(end, last)
                )
                offset = HecTime(_start_time) - HecTime(
                    _start_time
                ).adjust_to_interval_offset(self.interval, 0)
                interval_times = self.interval.get_datetime_index(
                    start_time=_start_time,
                    end_time=_end_time,
                    time_zone=self.time_zone,
                    offset=offset,
                )
                target._data = target._data.reindex(interval_times)
                target._data.fillna({"quality": 5}, inplace=True)
                target._data["quality"] = target._data["quality"].astype("int64")
                if "selected" in target._data.columns:
                    target._data.fillna({"selected": False}, inplace=True)
            target._expanded = True
        return target

    def filter(self, unselected: bool = False, in_place: bool = False) -> "TimeSeries":
        """
        Filters a time series (either this one or a copy of this one) and returns the results. The returned time series
        will contain only the selected or unselected items in the original time series.

        Args:
            unselected (bool, optional): Specifies including only selected itmes (False) or only unselected items (True). Defaults to False.
            in_place (bool, optional): Specifies whether to modifiy this time series (True) or a copy of it (False). Defaults to False.

        Returns:
            TimeSeries: The filtered time series
        """
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        if target.has_selection:
            if unselected:
                df = data.loc[data["selected"] == False]
            else:
                df = data.loc[data["selected"]]
        else:
            if unselected:
                df = pd.DataFrame(columns=df.columns)
            else:
                df = data
        target._data = df
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def ifilter(self, unselected: bool = False) -> "TimeSeries":
        """
        Convenience method for executing [fileter(...)](#TimeSeries.filter) with `in_place=True`.
        """
        return self.filter(unselected, in_place=True)

    @property
    def first_valid_time(self) -> Optional[np.datetime64]:
        """
        The time of the first valid value in the time series. Values are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return None
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        valid_indices = TimeSeries._valid_indices(df)
        return (
            None
            if len(valid_indices) == 0
            else cast(np.datetime64, df.loc[valid_indices[0]].name)
        )

    @property
    def first_valid_value(self) -> Optional[float]:
        """
        The first valid value in the time series. Values are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return None
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        valid_indices = TimeSeries._valid_indices(df)
        return (
            None
            if len(valid_indices) == 0
            else float(df.loc[valid_indices[0]]["value"])
        )

    def format_time_for_index(self, item: Union[HecTime, datetime, str]) -> str:
        """
        Formats a time item for indexing into the times of this object. The formatting depends on
        the setting of this object's [`mindnight_as_2400`](#TimeSeries.midnight_as_2400) property

        Args:
            item (Union[HecTime, datetime, str]): The time item to format.

        Returns:
            str: The formatted string with the midnight setting of this object
        """
        ht = HecTime()
        ht.set(item)
        ht.midnight_as_2400 = self.midnight_as_2400
        return str(ht).replace("T", " ")

    def forward_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Computes and returns a time series that is the forward moving average of this time series.

        A forward moving average sets the value at each time to be the average of the values at that
        time and a number of previous consecutive times.

        Args:
            window (int): The number of values to average over. The result at each time will be
                the average of the values at (window-1) previous times and the value at the current
                time. The span between times is not accounted for so discretion should be used if
                the time series is irregular.
            only_valid (bool): Specifies whether to only average over windows where every value is
                valid. If False, the average at any given time may be computed using fewer values
                that specified in the window parameter.
            use_reduced (bool): Specifies whether to allow averages using less than window number
                of values will be computed at the beginning of the times series. If False, the
                values at the first (window-1) times will be set to missing.
            in_place (bool, optional): If True, this time series is modified and returned.
                Otherwise this time series is not modified. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data or if the window is invalid.

        Returns:
            TimeSeries: The averaged time series
        """
        return self._moving_average(
            "FORWARD", window, only_valid, use_reduced, in_place
        )

    def get_differentiation_parameter(self) -> Parameter:
        """
        Returns a new Parameter object appropriate for differentiating this time series with respect to time.

        The new parameter will preserve any sub-parameter of this time series as well as the unit system of this time sereis.

        Raises:
            TimeSeriesException: If time series is not integrable (see [Parameter.differentiable_base_parameters](parameter.html#Parameter.differentiable_base_parameters))

        Returns:
            Parameter: The new parameter object
        """
        if self.parameter.basename not in Parameter.differentiable_base_parameters():
            raise TimeSeriesException(
                f"Base parameter {self.parameter.basename} is not differentiable"
            )
        sub_param = self.parameter.subname
        new_parameter_name: str = cast(
            str, hec.parameter._differentiation_parameters[self.parameter.basename]
        )
        if sub_param:
            new_parameter_name += f"-{sub_param}"
        unit_system = UnitQuantity(self.parameter.unit_name).get_unit_systems()[0]
        new_parameter = Parameter(
            new_parameter_name,
            unit_system,
        )
        return new_parameter

    def get_integration_parameter(self) -> Parameter:
        """
        Returns a new Parameter object appropriate for integrating this time series over time.

        The new parameter will preserve any sub-parameter of this time series as well as the unit system of this time sereis.

        Raises:
            TimeSeriesException: If time series is not integrable (see [Parameter.integrable_base_parameters](parameter.html#Parameter.integrable_base_parameters))

        Returns:
            Parameter: The new parameter object
        """
        if self.parameter.basename not in Parameter.integrable_base_parameters():
            raise TimeSeriesException(
                f"Base parameter {self.parameter.basename} is not integrable"
            )
        sub_param = self.parameter.subname
        new_parameter_name = hec.parameter._integration_parameters[
            self.parameter.basename
        ]
        if sub_param:
            new_parameter_name += f"-{sub_param}"
        unit_system = "EN" if self.is_english else "SI"
        new_parameter = Parameter(
            new_parameter_name,
            unit_system,
        )
        return new_parameter

    def has_same_times(self, other: "TimeSeries") -> bool:
        """
        Returns whether another time series has the same times as this time series.

        Args:
            other (TimeSeries): The other time series

        Returns:
            bool: Whether another time series has the same times as this time series.
        """
        return other.times == self.times

    @property
    def has_selection(self) -> bool:
        """
        Whether the object has a current selection specified

        Operations:
            Read Only
        """
        return self._data is not None and "selected" in self._data.columns

    def iaccum(self) -> "TimeSeries":
        """
        Convenience method for executing [accum(...)](#TimeSeries.accum) with `in_place=True`.
        """
        return self.accum(True)

    def icentered_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Convenience method for executing [centered_moving_average(...)](#TimeSeries.centered_moving_average) with `in_place=True`.
        """
        return self.centered_moving_average(
            window, only_valid, use_reduced, in_place=True
        )

    def icollapse(self) -> "TimeSeries":
        """
        Convenience method for executing [collapse(...)](#TimeSeries.collapse) with `in_place=True`.
        """
        return self.collapse(in_place=True)

    def iconvert_to_time_zone(
        self,
        time_zone: Union["HecTime", datetime, ZoneInfo, str],
        on_tz_not_set: int = 1,
    ) -> "TimeSeries":
        """
        Convenience method for executing [convert_to_time_zone(...)](#TimeSeries.convert_to_time_zone) with `in_place=True`.
        """
        return self.convert_to_time_zone(time_zone, on_tz_not_set, in_place=True)

    def idiff(self, in_place: bool = False) -> "TimeSeries":
        """
        Convenience method for executing [diff(...)](#TimeSeries.diff) with `in_place=True`.
        """
        return self.diff(True)

    def iestimate_missing_values(
        self,
        max_missing_count: int,
        accumulation: bool = False,
        estimate_rejected: bool = True,
        set_questioned: bool = True,
    ) -> "TimeSeries":
        """
        Convenience method for executing [estimate_missing_values(...)](#TimeSeries.estimate_missing_values) with `in_place=True`.
        """
        return self.estimate_missing_values(
            max_missing_count,
            accumulation,
            estimate_rejected,
            set_questioned,
            in_place=True,
        )

    def iexpand(
        self,
        start_time: Optional[Union[str, datetime, HecTime]] = None,
        end_time: Optional[Union[str, datetime, HecTime]] = None,
    ) -> "TimeSeries":
        """
        Convenience method for executing [expand(...)](#TimeSeries.expand) with `in_place=True`.
        """
        return self.expand(start_time, end_time, in_place=True)

    def iforward_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Convenience method for executing [forward_moving_average(...)](#TimeSeries.forward_moving_average) with `in_place=True`.
        """
        return self.forward_moving_average(
            window, only_valid, use_reduced, in_place=True
        )

    def imap(self, func: Callable[[float], float]) -> "TimeSeries":
        """
        Convenience method for executing [map(...)](#TimeSeries.map) with `in_place=True`.
        """
        return self.map(func, in_place=True)

    def ilabel_as_time_zone(
        self,
        time_zone: Optional[Union["HecTime", datetime, ZoneInfo, str]],
        on_already_set: int = 1,
    ) -> "TimeSeries":
        """
        Convenience method for executing [label_as_time_zone(...)](#TimeSeries.label_as_time_zone) with `in_place=True`.
        """
        return self.label_as_time_zone(time_zone, on_already_set, True)

    def imerge(self, other: Union["TimeSeries", List["TimeSeries"]]) -> "TimeSeries":
        """
        Convenience method for executing [merge(...)](#TimeSeries.merge) with `in_place=True`.
        """
        return self.merge(other, in_place=True)

    def index_of(
        self,
        item_to_index: Union[HecTime, datetime, int, str],
        not_found: Optional[str] = None,
    ) -> str:
        """
        Retrieves the data index of a specified object

        Args:
            item_to_index (Union[HecTime, datetime, int, str]): The object to retrieve the index of.
                * **HecTime**: an HecTime object
                * **datetime**:  a datetime object
                * **int**: a normal python index
                * **str**: a date-time string
            not_found (Optional[str]): Specifies the behavior if `item_to_index` is not in the index:
                * 'next': return the higher of the bounding indices of the item
                * 'previous': return the lower of the bounding indices of the item
                * 'stop': used for the stop index of slices - return the lower of the bounding indices plus one (unless beyond end)
                * None (default): raise an IndexError

        Raises:
            TimeSeriesException: If the time series has no values, or if `not_found` is specifed and is not "next" "previous", or "stop"
            TypeError: If `item_to_index` is not one of the expected types
            IndexError:
                * **int**: If the integer is out of range of the number of times
                * **Others**: If no index item matches the input object

        Returns:
            str: The actual index item that for the specified object
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if not_found and not_found not in ("next", "previous", "stop"):
            raise TimeSeriesException(
                'Parameter not_found must be None, "next", "previous", or "stop"'
            )
        times = self.times
        idx = None
        try:
            if isinstance(item_to_index, (HecTime, datetime, str)):
                ht = HecTime(item_to_index)
                ht.midnight_as_2400 = False
                key = str(ht).replace("T", " ")
                if not_found is None:
                    idx = times.index(key)
                else:
                    try:
                        idx = times.index(key)
                    except:
                        if not_found == "next":
                            for i in range(len(times)):
                                if times[i] > key:
                                    idx = i
                                    break
                            else:
                                raise
                        elif not_found == "previous":
                            for i in range(len(times))[::-1]:
                                if times[i] < key:
                                    idx = i
                                    break
                            else:
                                raise
                        elif not_found == "stop":
                            for i in range(len(times))[::-1]:
                                if times[i] < key:
                                    idx = i
                                    if idx < len(times) - 1:
                                        idx += 1
                                    break
                            else:
                                raise
            elif isinstance(item_to_index, int):
                idx = item_to_index
                if idx < 0 and not_found == "next":
                    idx = 0
                if idx >= len(times) and not_found == "previous":
                    idx = len(times) - 1
            else:
                raise TypeError(
                    f"Expected HecTime, datetime, str, or int. Got {type(item_to_index)}"
                )
        except TypeError:
            raise
        except:
            if not_found == "next":
                raise IndexError(
                    f"{item_to_index} is not in times and no next time was found"
                )
            if not_found == "previous":
                raise IndexError(
                    f"{item_to_index} is not in times and no previous time was found"
                )
            raise IndexError(f"{item_to_index} is not in times")
        assert idx is not None
        return times[idx]

    @property
    def interval(self) -> Interval:
        """
        The interval object (used in HEC-DSS E pathname part)

        Operations:
            Read Only
        """
        return self._interval

    def iolympic_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Convenience method for executing [olympic_moving_average(...)](#TimeSeries.olympic_moving_average) with `in_place=True`.
        """
        return self.olympic_moving_average(
            window, only_valid, use_reduced, in_place=True
        )

    def iresample(
        self,
        operation: str,
        interval: Optional[Union["TimeSeries", TimeSpan, timedelta]] = None,
        offset: Optional[Union[int, TimeSpan, timedelta]] = None,
        start_time: Optional[Union[HecTime, datetime, str]] = None,
        end_time: Optional[Union[HecTime, datetime, str]] = None,
        max_missing_percent: float = 25.0,
        entire_interval: Optional[bool] = None,
        before: Union[str, float] = 0.0,
        after: Union[str, float] = _RESAMPLE_LAST,
    ) -> "TimeSeries":
        """
        Convenience method for executing [resample(...)](#TimeSeries.resample) with `in_place=True`.
        """
        return self.resample(
            operation,
            interval,
            offset,
            start_time,
            end_time,
            max_missing_percent,
            entire_interval,
            before,
            after,
            in_place=True,
        )

    def iround_off(self, precision: int, tens_place: int) -> "TimeSeries":
        """
        Convenience method for executing [round_off(...)](#TimeSeries.round_off) with `in_place=True`.
        """
        return self.map(lambda v: TimeSeries._round_off(v, precision, tens_place), True)

    @property
    def is_any_irregular(self) -> bool:
        """
        Specifies whether the time series is a normal irregular or pseudo-regular time series

        Operations:
            Read Only
        """
        return self.interval.is_any_irregular

    @property
    def is_any_regular(self) -> bool:
        """
        Specifies whether the time series is a normal regular or local regular time series

        Operations:
            Read Only
        """
        return self.interval.is_any_regular

    @staticmethod
    def is_cwms_ts_id(identifier: str) -> bool:
        """
        Returns whether the specified identifier is a valid CWMS time series identifier

        Args:
            identifier (str): The identifier

        Returns:
            bool: Whether the identifier is a valid CWMS time series identifier
        """
        return _is_cwms_tsid(identifier)

    @staticmethod
    def is_dss_ts_pathname(identifier: str) -> bool:
        """
        Returns whether the specified identifier is a valid HEC-DSS time series pathname

        Args:
            identifier (str): The identifier

        Returns:
            bool: Whether the identifier is a valid HEC-DSS time series pathname
        """
        return _is_dss_ts_pathname(identifier)

    @property
    def is_english(self) -> bool:
        """
        Returns whether the unit of this time series is recognized as an English unit

        Operations:
            Read Only
        """
        return self.unit in hec.unit.unit_names_by_unit_system["EN"]

    @property
    def is_irregular(self) -> bool:
        """
        Specifies whether the time series is a normal irregular time series

        Operations:
            Read Only
        """
        return self.interval.is_irregular

    @property
    def is_local_regular(self) -> bool:
        """
        Specifies whether the time series is a local regular time series

        Operations:
            Read Only
        """
        return self.interval.is_local_regular

    @property
    def is_metric(self) -> bool:
        """
        Returns whether the unit of this time series is recognized as an Metric unit

        Operations:
            Read Only
        """
        return self.unit in hec.unit.unit_names_by_unit_system["SI"]

    @property
    def is_pseudo_regular(self) -> bool:
        """
        Specifies whether the time series is a normal irregular or pseudo-regular time series

        Operations:
            Read Only
        """
        return self.interval.is_pseudo_regular

    @property
    def is_regular(self) -> bool:
        """
        Specifies whether the time series is a normal regular time series

        Operations:
            Read Only
        """
        return self.interval.is_regular

    def is_valid(self, index: Union[int, str, datetime, HecTime]) -> bool:
        """
        Returns whether the index is in the time series and the value at the index is valid

        Args:
            index (Union[int, str, datetime, HecTime]): The index to test.

        Returns:
            bool: False if any of the following are true, otherwise True:
            * The time series does not contain the index
            * The quality is MISSING
            * The quality is REJECTED
            * The value is NaN
            * The value is Infinite
        """
        if not isinstance(index, (int, str, datetime, HecTime)):
            raise TypeError(
                f"Expected int, str, datetime, or HecTime, got {type(index)}"
            )
        try:
            df = self[index].data
            if df is None:
                return False
            if math.isnan(df.value) or math.isinf(df.value):
                return False
            if df.quality & 0b0_0101 or df.quality & 0b1_0001:
                return False
            return True
        except:
            return False

    def iscreen_with_constant_value(
        self,
        duration: Union[Duration, str],
        missing_limit: float = math.nan,
        reject_limit: float = math.nan,
        question_limit: float = math.nan,
        min_threshold: float = math.nan,
        percent_valid_required: float = math.nan,
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_constant_value(...)](#TimeSeries.screen_with_constant_value) with `in_place=True`.
        """
        return self.screen_with_constant_value(
            duration,
            missing_limit,
            reject_limit,
            question_limit,
            min_threshold,
            percent_valid_required,
            False,
        )

    def iscreen_with_duration_magnitude(
        self,
        duration: Union[Duration, str],
        min_missing_limit: float,
        min_reject_limit: float,
        min_question_limit: float,
        max_question_limit: float,
        max_reject_limit: float,
        max_missing_limit: float,
        percent_valid_required: float = 0.0,
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_duration_magnitude(...)](#TimeSeries.screen_with_duration_magnitude) with `in_place=True`.
        """
        return self.screen_with_duration_magnitude(
            duration,
            min_missing_limit,
            min_reject_limit,
            min_question_limit,
            max_question_limit,
            max_reject_limit,
            max_missing_limit,
            percent_valid_required,
            False,
        )

    def iscreen_with_forward_moving_average(
        self,
        window: int,
        only_valid: bool,
        use_reduced: bool,
        diff_limit: float,
        invalid_validity: str = "M",
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_forward_moving_average(...)](#TimeSeries.screen_with_forward_moving_average) with `in_place=True`.
        """
        return self.screen_with_forward_moving_average(
            window,
            only_valid,
            use_reduced,
            diff_limit,
            invalid_validity,
            False,
        )

    def iscreen_with_value_change_rate(
        self,
        min_reject_limit: float = math.nan,
        min_question_limit: float = math.nan,
        max_question_limit: float = math.nan,
        max_reject_limit: float = math.nan,
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_value_change_rate(...)](#TimeSeries.screen_with_value_change_rate) with `in_place=True`.
        """
        return self.screen_with_value_change_rate(
            min_reject_limit, min_question_limit, max_reject_limit, max_question_limit
        )

    def iscreen_with_value_range(
        self,
        min_reject_limit: float = math.nan,
        min_question_limit: float = math.nan,
        max_question_limit: float = math.nan,
        max_reject_limit: float = math.nan,
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_value_range(...)](#TimeSeries.screen_with_value_range) with `in_place=True`.
        """
        return self.screen_with_value_range(
            min_reject_limit, min_question_limit, max_question_limit, max_reject_limit
        )

    def iscreen_with_value_range_or_change(
        self,
        min_limit: float = math.nan,
        max_limit: float = math.nan,
        change_limit: float = math.nan,
        replace_invalid_value: bool = True,
        invalid_value_replacement: float = math.nan,
        invalid_validity: str = "M",
    ) -> "TimeSeries":
        """
        Convenience method for executing [screen_with_value_range_or_change(...)](#TimeSeries.screen_with_value_range_or_change) with `in_place=True`.
        """
        return self.screen_with_value_range_or_change(
            min_limit,
            max_limit,
            change_limit,
            replace_invalid_value,
            invalid_value_replacement,
            invalid_validity,
        )

    def iselect(
        self,
        selection: Union[Select, int, slice, Callable[[TimeSeriesValue], bool]],
        combination: Combine = Combine.REPLACE,
    ) -> "TimeSeries":
        """
        Convenience method for executing [select(...)](#TimeSeries.select) with `in_place=True`.
        """
        return self.select(selection, combination, in_place=True)

    def iselect_valid(self) -> "TimeSeries":
        """
        Convenience method for executing [select_valid(...)](#TimeSeries.select_valid) with `in_place=True`.
        """
        self.select_valid(in_place=True)
        return self

    def iset_duration(self, value: Union[Duration, str, int]) -> "TimeSeries":
        """
        Convenience method for executing [set_duration(...)](#TimeSeries.set_duration) with `in_place=True`.
        """
        return self.set_duration(value, in_place=True)

    def iset_interval(self, value: Union[Interval, str, int]) -> "TimeSeries":
        """
        Convenience method for executing [set_interval(...)](#TimeSeries.set_interval) with `in_place=True`.
        """
        return self.set_interval(value, in_place=True)

    def iset_location(self, value: Union[Location, str]) -> "TimeSeries":
        """
        Convenience method for executing [set_location(...)](#TimeSeries.set_location) with `in_place=True`.
        """
        return self.set_location(value, in_place=True)

    def iset_parameter(self, value: Union[Parameter, str]) -> "TimeSeries":
        """
        Convenience method for executing [set_parameter(...)](#TimeSeries.set_parameter) with `in_place=True`.
        """
        return self.set_parameter(value, in_place=True)

    def iset_parameter_type(self, value: Union[ParameterType, str]) -> "TimeSeries":
        """
        Convenience method for executing [set_parameter_type(...)](#TimeSeries.set_parameter_type) with `in_place=True`.
        """
        return self.set_parameter_type(value, in_place=True)

    def iset_protected(self) -> "TimeSeries":
        """
        Convenience method for executing [set_protected(...)](#TimeSeries.set_protected) with `in_place=True`.
        """
        return self.set_protected(in_place=True)

    def iset_quality(self, quality: Union[Quality, int]) -> "TimeSeries":
        """
        Convenience method for executing [set_quality(...)](#TimeSeries.set_quality) with `in_place=True`.
        """
        return self.set_quality(quality, True)

    def iset_unit(self, value: Union[Unit, str]) -> "TimeSeries":
        """
        Convenience method for executing [set_unit(...)](#TimeSeries.set_unit) with `in_place=True`.
        """
        return self.set_unit(value, in_place=True)

    def iset_unprotected(self) -> "TimeSeries":
        """
        Convenience method for executing [set_unprotected(...)](#TimeSeries.set_unprotected) with `in_place=True`.
        """
        return self.set_unprotected(in_place=True)

    def iset_value(self, value: float) -> "TimeSeries":
        """
        Convenience method for executing [set_value(...)](#TimeSeries.set_value) with `in_place=True`.
        """
        return self.set_value(value, True)

    def iset_value_quality(
        self, value: float, quality: Union[Quality, int]
    ) -> "TimeSeries":
        """
        Convenience method for executing [set_value_quality(...)](#TimeSeries.set_value_quality) with `in_place=True`.
        """
        return self.set_value_quality(value, quality, True)

    def iset_vertical_datum_info(
        self, value: Union[str, dict[str, Any]]
    ) -> "TimeSeries":
        """
        Convenience method for executing [set_vertical_datum_info(...)](#TimeSeries.set_vertical_datum_info) with `in_place=True`.
        """
        return self.set_vertical_datum_info(value, in_place=True)

    def isnap_to_regular(
        self,
        interval: Union[Interval, str],
        offset: Optional[Union[TimeSpan, timedelta, str]] = None,
        backward: Optional[Union[TimeSpan, timedelta, str]] = None,
        forward: Optional[Union[TimeSpan, timedelta, str]] = None,
    ) -> "TimeSeries":
        """
        Convenience method for executing [snap_to_regular(...)](#TimeSeries.snap_to_regular) with `in_place=True`.
        """
        return self.snap_to_regular(interval, offset, backward, forward, in_place=True)

    def itime_derivative(self, in_place: bool = False) -> "TimeSeries":
        """
        Convenience method for executing [time_derivative(...)](#TimeSeries.time_derivative) with `in_place=True`.
        """
        return self.time_derivative(True)

    def ito(self, unit_parameter_or_datum: Union[str, Unit, Parameter]) -> "TimeSeries":
        """
        Convenience method for executing [to(...)](#TimeSeries.to) with `in_place=True`.
        """
        return self.to(unit_parameter_or_datum, True)

    def ito_irregular(self, interval: Union[Interval, str]) -> "TimeSeries":
        """
        Convenience method for executing [to_irregular(...)](#TimeSeries.to_irregular) with `in_place=True`.
        """
        return self.to_irregular(interval, in_place=True)

    def itrim(self) -> "TimeSeries":
        """
        Convenience method for executing [trim(...)](#TimeSeries.trim) with `in_place=True`.
        """
        return self.trim(in_place=True)

    def kurtosis(self) -> float:
        """
        Computes the kurtosis coefficient of the values in the time series

        Raises:
            TimeSeriesException: If the time series has no data or fewer than 2 items selected.

        Returns:
            float: The kurtosis coefficient
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if len(selected) < 2:
                raise TimeSeriesException(
                    "Cannot perform aggregation with fewer than 2 items selected"
                )
            return cast(float, selected["value"].kurtosis())
        else:
            if len(self._data) < 2:
                raise TimeSeriesException(
                    "Cannot perform aggregation with fewer than 2 items"
                )
            return cast(float, self._data["value"].kurtosis())

    def label_as_time_zone(
        self,
        time_zone: Optional[Union["HecTime", datetime, ZoneInfo, str]],
        on_already_set: int = 1,
        in_place: bool = True,
    ) -> "TimeSeries":
        """
        Attaches the specified time zone to this object or a copy of this object and returns it. Does not change the actual times

        Args:
            time_zone (Optional[Union["HecTime", datetime, ZoneInfo, str]]): The time zone to attach or
                object containing that time zone.
                * Use `"local"` to specify the system time zone.
                * Use `None` to remove time zone information
            on_already_set (int): Specifies action to take if a different time zone is already
                attached. Defaults to 1.
                - `0`: Quietly attach the new time zone
                - `1`: (default) Issue a warning about attaching a different time zone
                - `2`: Raises an exception
            in_place (bool): Specifies whether to attach the time zone to this time series (True) or a copy of it (False). Defaults to False
        Raises:
            TimeSeriesException: if a different time zone is already attached and `on_already_set` == 2

        Returns:
            TimeSeries: The modified object
        """
        tz = HecTime._get_zone_info_obj(time_zone)
        target = self if in_place else self.copy()
        if target._timezone:
            if tz and tz.key == target._timezone:
                return target
            if tz is None:
                if target._data is not None:
                    target._data = target._data.tz_localize(None)
                target._timezone = None
            else:
                if on_already_set > 0:
                    message = f"{repr(target)} already has a time zone set to {target._timezone} when setting to {tz}"
                    if on_already_set > 1:
                        raise TimeSeriesException(message)
                    else:
                        warnings.warn(
                            message + ". Use on_already_set=0 to prevent this message.",
                            UserWarning,
                        )
                if target._data is not None:
                    target._data = target._data.tz_localize(None)
                    target._data = target._data.tz_localize(
                        tz,
                        ambiguous=np.zeros(len(target._data.index), dtype=bool),
                        nonexistent="NaT",
                    )
                target._timezone = str(time_zone)
        else:
            if tz:
                if target._data is not None:
                    target._data = target._data.tz_localize(None)
                    target._data = target._data.tz_localize(
                        tz,
                        ambiguous=np.zeros(len(target._data.index), dtype=bool),
                        nonexistent="NaT",
                    )
                target._timezone = str(tz)
        return target

    @property
    def last_valid_time(self) -> Optional[np.datetime64]:
        """
        The time of the last valid value in the time series. Values are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return None
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        valid_indices = TimeSeries._valid_indices(df)
        return (
            None
            if len(valid_indices) == 0
            else cast(np.datetime64, df.loc[valid_indices[-1]].name)
        )

    @property
    def last_valid_value(self) -> Optional[float]:
        """
        The last valid value in the time series. Values are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return None
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        valid_indices = TimeSeries._valid_indices(df)
        return (
            None
            if len(valid_indices) == 0
            else float(df.loc[valid_indices[-1]]["value"])
        )

    @property
    def location(self) -> Location:
        """
        The location object (used in HEC-DSS B pathname part)

        Operations:
            Read Only
        """
        return self._location

    def map(
        self, func: Callable[[float], float], in_place: bool = False
    ) -> "TimeSeries":
        """
        Applies a function of one variable to the values of this object and returns the modified object

        Args:
            func (Callable): The function of one variable to apply to the values
            in_place (bool, optional): Specifies whether to operate on this object (True)
                or a copy of this object (False). Defaults to False.

        Returns:
            TimeSeries: Either this object (modified) or a modified copy of this object.
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        target = self if in_place else self.copy()
        cast(pd.DataFrame, target._data)["value"] = cast(pd.DataFrame, target._data)[
            "value"
        ].map(func)
        return target

    def max_value(self) -> float:
        """
        Returns the maximum value in the time series.

        Raises:
            TimeSeriesException: If the time series has no data

        Returns:
            float: The maximum value in the time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
            if len(selected) == 0:
                raise TimeSeriesException("Operation is invalid with empty selection.")
            return float(selected["value"].max())
        else:
            return float(self._data["value"].max())

    def max_value_time(self) -> HecTime:
        """
        Returns the time of maximum value in the time series.

        Raises:
            TimeSeriesException: If the time series has no data

        Returns:
            float: The time of maximum value in the time series. If the maximum value
                occurs more than once, the earliest time is returned.
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
            if len(selected) == 0:
                raise TimeSeriesException("Operation is invalid with empty selection.")
            return HecTime(selected["value"].idxmax())
        else:
            return HecTime(self._data["value"].idxmax())

    def merge(
        self, other: Union["TimeSeries", List["TimeSeries"]], in_place: bool = False
    ) -> "TimeSeries":
        """
        Merges one or more time series into either this time series or a copy of it, and returns the merged time series.

        When the same time exists while merging, the following precedence is followed:
        * other protected value (incoming protected trumps existing protected)
        * this protected value
        * this unprotected value if it is not NaN or infinite
        * other unprotected value if it is not NaN or infinte

        Args:
            other (Union[&quot;TimeSeries&quot;, List[&quot;TimeSeries&quot;]]): The other times series (one or a list) to merge.
                If a list, each other time series is merged in sequence, with earlier results acting as this time series for later merges
            in_place (bool, optional): Specifies whether to merge into this time series (True) or a copy of it (False). Defaults to False.

        Raises:
            TimeSeriesException: If this time series is a regular time series and the merged times are not all on the interval

        Returns:
            TimeSeries: The merged time series
        """
        # ---------------- #
        # set up variables #
        # ---------------- #
        others = other if isinstance(other, list) else [other]
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(
            pd.DataFrame, target._data
        )  # doesn't affect selection, can't overwrite protected rows
        # ----------------- #
        # perform the merge #
        # ----------------- #
        all_times = set() if data is None or data.empty else set(data.index.to_list())
        for ts in others:
            if data is None:
                if ts._data is None:
                    continue
                data = ts._data.copy()
            elif ts._data is None:
                continue
            else:
                data2 = ts._data
                # Align data2 with data by reindexing
                #
                # Moved to using sets becuase data.index.union(data2.index) didn't always work
                all_times |= set(data2.index.to_list())
                aligned_data2 = data2.reindex(pd.Index(sorted(all_times), name="time"))
                aligned_data2["quality"] = (
                    pd.to_numeric(aligned_data2["quality"], errors="coerce")
                    .fillna(5)
                    .astype("Int64")  # set to missing quality
                )
                # Create overwrite_mask
                overwrite_mask = (
                    (data["value"].isna() | np.isinf(data["value"]))  # NaN or infinite
                    & ~(
                        (data["quality"].astype(int) & (1 << 31)) != 0
                    )  # Bit 31 not set in data
                ) | (
                    (
                        (aligned_data2["quality"].astype(int) & (1 << 31)) != 0
                    )  # Bit 31 set in data2
                )
                # Update rows in data where overwrite_mask is True
                updated_data = data.copy()
                updated_data.loc[overwrite_mask] = aligned_data2.loc[overwrite_mask]
                # Add rows from data2 not in data
                data = pd.concat(
                    [
                        df
                        for df in (
                            updated_data,
                            aligned_data2[~aligned_data2.index.isin(data.index)],
                        )
                        if not df.empty
                    ]
                )
            target._data = data
        target._validate()
        return target

    @property
    def midnight_as_2400(self) -> bool:
        """
        The object's current setting of whether to show midnight as hour 24 (default) or not.

        Operations:
            Read/Write
        """
        return self._midnight_as_2400

    @midnight_as_2400.setter
    def midnight_as_2400(self, state: bool) -> None:
        self._midnight_as_2400 = state

    def min_value(self) -> float:
        """
        Returns the minimum value in the time series.

        Raises:
            TimeSeriesException: If the time series has no data

        Returns:
            float: The minimum value in the time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
            if len(selected) == 0:
                raise TimeSeriesException("Operation is invalid with empty selection.")
            return float(selected["value"].min())
        else:
            return float(self._data["value"].min())

    def min_value_time(self) -> HecTime:
        """
        Returns the time of minimum value in the time series.

        Raises:
            TimeSeriesException: If the time series has no data

        Returns:
            float: The time of minimum value in the time series. If the minimum value
                occurs more than once, the earliest time is returned.
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
            if len(selected) == 0:
                raise TimeSeriesException("Operation is invalid with empty selection.")
            return HecTime(selected["value"].idxmin())
        else:
            return HecTime(self._data["value"].idxmin())

    @property
    def name(self) -> str:
        """
        The CWMS time series identifier or HEC-DSS pathname

        Operations:
            Read/Write
        """
        parts = []
        if self._context == CWMS:
            parts.append(str(self._location.name))
            parts.append(self._parameter.name)
            parts.append(cast(ParameterType, self._parameter_type).get_cwms_name())
            parts.append(self._interval.name)
            parts.append(cast(Duration, self._duration).name)
            parts.append(cast(str, self._version))
            return ".".join(parts)
        elif self._context == DSS:
            parts.append("")
            parts.append(self.watershed if self.watershed else "")
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
            if _is_cwms_tsid(value):
                parts = value.split(".")
                self._context = CWMS
                self.iset_location(parts[0])
                self.iset_parameter(parts[1])
                self.iset_parameter_type(parts[2])
                self.iset_interval(parts[3])
                self.iset_duration(parts[4])
                self.version = parts[5]
            elif _is_dss_ts_pathname(value):
                parts = value.split("/")
                A, B, C, E, F = 1, 2, 3, 5, 6
                self._context = DSS
                self.watershed = parts[A]
                self.iset_location(parts[B])
                self.iset_parameter(parts[C])
                self.iset_parameter_type(
                    "INST-CUM" if "PRECIP" in parts[C].upper() else "INST-VAL"
                )
                self.iset_interval(parts[E])
                self.version = parts[F]

            else:
                raise TimeSeriesException(
                    "Expected valid CWMS time series identifier or HEC-DSS time series pathname"
                )
            if not self._location:
                raise TimeSeriesException("Location must be specified")
            if not self._parameter:
                raise TimeSeriesException("Parameter must be specified")
            if not self._parameter_type and self._context == CWMS:
                raise TimeSeriesException("Parameter type must be specified")
            if self._interval is None:
                raise TimeSeriesException("Interval must be specified")
            if self._duration is None and self._context == CWMS:
                raise TimeSeriesException("Duration must be specified")
            if not self._version and self._context == CWMS:
                raise TimeSeriesException("Version must be specified")

        except Exception as e:
            raise TimeSeriesException(
                f"Invalid time series name: '{value}':\n{type(e)}: {' '.join(e.args)}"
            )

    @staticmethod
    def new_regular_time_series(
        name: str,
        start: Union[HecTime, datetime, str],
        end: Union[HecTime, datetime, str, int],
        interval: Union[Interval, timedelta, str],
        offset: Optional[Union[TimeSpan, timedelta, str, int]] = None,
        time_zone: Optional[str] = None,
        values: Optional[Union[List[float], float]] = None,
        qualities: Optional[Union[list[Union[Quality, int]], Quality, int]] = None,
    ) -> "TimeSeries":
        """
        Generates and returns a new regular (possibly local regular) interval time series with the
        specified times, values, and qualities.

        Args:
            name (str): The name of the time series. The interval portion will be overwritten by the `interval` if they don't agree
            start (Union[HecTime, datetime, str]): The specified start time. The actual start time may be later than this, depending on `interval` and `offset`
            end (Union[HecTime, datetime, str, int]): Either the specified end time or, if int, the number of intervals in the time series.
                The actual end time may be earlier than the specified end time, depending on `interval` and `offset`
            interval (Union[Interval, timedelta, str]): The interval of the time series. Will overwrite the interval portion of `name`. If it
                is a local regular interval and `start` includes a time zone, then the time series will be a local regular time series
            offset (Optional[Union[TimeSpan, timedelta, str, int]]): The interval offset. If int, then number of minutes. If none, then the
                offset is determined from `start` (it's offset into the specified interval). Defaults to None.
            time_zone (Optional[str]): The time zone. Must be specified if `interval` is a local-regular interval.
            values (Optional[Union[List[float], float]]): The value(s) to populate the time series with. If float, it specifies all values.
                If list, the list is repeated as many whole and/or partial time as necessary to fill the time series. Defaults to None, which causes all values to be NaN.
            qualities (Optional[Union[list[Union[Quality, int]], Quality, int]]): The qualities to fill the time series with. If Quality or int,
                it specifies all qualities. If list, the list is repeated as many whole and/or partial times to fill the time sries Defaults to None, which causes all qualities to be zero.

        Raises:
            TimeSeriesException: If an irregular interval is specified. To generate new irregular interval time series, use [`TimeSeries(name, times, values, quality, time_zone)`](#TimeSeries.__init__)

        Returns:
            TimeSeries: The generated regular (possible local regular) interval time series
        """
        # ---------------------------------------- #
        # handle name, start, interval, and offset #
        # ---------------------------------------- #
        ts = TimeSeries(name)
        start_time = HecTime(start)
        start_time.midnight_as_2400 = False
        if isinstance(interval, Interval):
            intvl = interval
        elif isinstance(interval, timedelta):
            matcher = (
                lambda i: i.minutes == int(interval.total_seconds() // 60)
                and i.is_regular
            )
            if ts._context == DSS:
                intvl = cast(Interval, Interval.get_any_dss(matcher, True))
            else:
                intvl = cast(Interval, Interval.get_any_cwms(matcher, True))
        elif isinstance(interval, str):
            matcher = lambda i: i.name == interval and i.is_regular
            if ts._context == DSS:
                intvl = cast(Interval, Interval.get_any_dss(matcher, True))
            else:
                intvl = cast(Interval, Interval.get_any_cwms(matcher, True))
        else:
            raise TypeError(
                f"Expected interval parameter to be Interval or timedelta, got {type(interval)}"
            )
        if not intvl.is_any_regular:
            raise TimeSeriesException(
                f"Cannot generate a regular time series with the specified interval {intvl}"
            )
        ts.iset_interval(intvl)
        specified_start_time: HecTime = start_time.copy()
        interval_offset: TimeSpan
        if offset is None:
            interval_offset = cast(
                TimeSpan,
                specified_start_time
                - specified_start_time.adjust_to_interval_offset(intvl, 0),
            )
        else:
            if isinstance(offset, int):
                interval_offset = TimeSpan(minutes=offset)
            elif isinstance(offset, TimeSpan):
                interval_offset = offset
            else:
                interval_offset = TimeSpan(offset)
        start_time.adjust_to_interval_offset(intvl, 0)
        start_time += interval_offset
        if start_time < specified_start_time:
            start_time += intvl
        # ---------- #
        # handle end #
        # ---------- #
        if isinstance(end, (HecTime, datetime, str)):
            # -------- #
            # end time #
            # -------- #
            times = intvl.get_datetime_index(
                start_time=start_time, end_time=end, time_zone=time_zone, name="time"
            )
        elif isinstance(end, int):
            # ------------------- #
            # number of intervals #
            # ------------------- #
            times = intvl.get_datetime_index(
                start_time=start_time, count=end, time_zone=time_zone, name="time"
            )
        return TimeSeries(ts.name, times, values, qualities)

    @property
    def number_invalid_values(self) -> int:
        """
        The number of invalid values in the time series. Values are invalid if any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        return int(
            df[
                (df["value"].isna())
                | (np.isinf(df["value"]))
                | (df["quality"] == 5)
                | ((df["quality"].astype("int64") & 0b1_0000) != 0)
            ].shape[0]
        )

    @property
    def number_missing_values(self) -> int:
        """
        The number of invalid values in the time series. Values are missing if either of the following are true:
        * The quality is MISSING
        * The value is NaN

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        return df[(df["value"].isna()) | (df["quality"] == 5)].shape[0]

    @property
    def number_questioned_values(self) -> int:
        """
        The number of values in the time series that have quality of QUESTIONABLE:

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        return df[((df["quality"].astype("int64") & 0b1000) != 0)].shape[0]

    @property
    def number_rejected_values(self) -> int:
        """
        The number of values in the time series that have quality of REJECTED:

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        return df[((df["quality"].astype("int64") & 0b1_0000) != 0)].shape[0]

    @property
    def number_valid_values(self) -> int:
        """
        The number of valid values in the time series. Values are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
        return int(
            df[
                ~(
                    (df["value"].isna())
                    | (np.isinf(df["value"]))
                    | (df["quality"] == 5)
                    | ((df["quality"].astype("int64") & 0b1_0000) != 0)
                )
            ].shape[0]
        )

    @property
    def number_values(self) -> int:
        """
        The number of values in the time series. Same as len(ts).

        Operations:
            Read Only
        """
        if len(self) == 0:
            return 0
        data = cast(pd.DataFrame, self._data)
        df = data[data["selected"]] if self.has_selection else data
        return df.shape[0]

    def olympic_moving_average(
        self, window: int, only_valid: bool, use_reduced: bool, in_place: bool = False
    ) -> "TimeSeries":
        """
        Computes and returns a time series that is the olympic moving average of this time series.

        An olympic moving average sets the value at each time to be the average of the values at that
        time and a number of previous and following consecutive times, disregarding the minimum
        and maximum values in the range to average over.

        Args:
            window (int): The number of values to average over. The result at each time will be
                the average of the values at ((window-1)/2) previous times, the value at the current
                time, and the values at ((window-1)/2) following times, not using the minimum and
                maximum values in the window. The span between times is not accounted for so discretion
                should be used if the time series is irregular. Must be an odd number.
            only_valid (bool): Specifies whether to only average over windows where every value is
                valid. If False, the average at any given time may be computed using fewer values
                that specified in the window parameter.
            use_reduced (bool): Specifies whether to allow averages using less than window number
                of values will be computed at the beginning and end of the times series. If False, the
                values at the first and last ((window-1)/2) times will be set to missing.
            in_place (bool, optional): If True, this time series is modified and returned.
                Otherwise this time series is not modified. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data or if the window is invalid.

        Returns:
            TimeSeries: The averaged time series
        """
        return self._moving_average(
            "OLYMPIC", window, only_valid, use_reduced, in_place
        )

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

    def percentile(self, pct: float) -> float:
        """
        Computes the specified percentile of the values in the time series

        Args:
            pct (float): The desired percentile in the range of 1..100

        Raises:
            TimeSeriesException: If the time series has no data or fewer than 2 items selected.

        Returns:
            float: The value for the specified percentile
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.has_selection:
            selected = self._data[self._data["selected"]]
            if len(selected) < 2:
                raise TimeSeriesException(
                    "Cannot perform operation with fewer than 2 items selected"
                )
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
            return selected["value"].quantile(pct / 100.0)
        else:
            if len(self._data) < 2:
                raise TimeSeriesException(
                    "Cannot perform operation with fewer than 2 items"
                )
            return self._data["value"].quantile(pct / 100.0)

    @staticmethod
    def percentile_ts(pct: float, timeseries: list["TimeSeries"]) -> "TimeSeries":
        """
        Computes the specified percentile of the values in the time series

        Args:
            pct (Union[tuple[float, ...], list[float], float]): The desired percentile in the range of 1..100
                or a list or tuple of such percentiles.

        Raises:
            TimeSeriesException: If the time series has no data or fewer than 2 items selected.

        Returns:
            TimeSeries: The time series of percentiles for each time. The times series name will be
            modified from the first time series specified in the following way:
            * The parameter will be "Code-Percentile"
            * the version will be "<pct>-percentile" with <pct> replaced by the pct parameter with any decimal
                point replaced with an underscore (_) character
        """
        try:
            # ----------------------------------- #
            # filter out time series without data #
            # ----------------------------------- #
            with_data = [ts for ts in timeseries if ts.data is not None]
            if len(with_data) < 2:
                raise TimeSeriesException(
                    "More that one time series with data is required"
                )
            # ------------------------------------------------------------------------------------------------- #
            # generate an index common to all time series and create a list of DataFrames with only those times #
            # ------------------------------------------------------------------------------------------------- #
            common_index = cast(pd.DataFrame, with_data[0].data).index
            for ts in with_data[1:]:
                common_index = common_index.intersection(
                    cast(pd.DataFrame, ts.data).index
                )
                if len(common_index) == 0:
                    raise TimeSeriesException("Time series do not include common times")
            common_index.name = "time"
            # ---------------------------------------- #
            # generate and return a result time series #
            # ---------------------------------------- #
            ts = timeseries[0].copy(include_data=False)
            ts.ito("Code-Percentile").version = (
                f"{str(pct).replace('.', '_')}-percentile"
            )
            ts._data = pd.DataFrame(
                {
                    "value": pd.concat(
                        [
                            (
                                cast(pd.DataFrame, ts._data).loc[
                                    cast(pd.DataFrame, ts._data)["selected"], ["value"]
                                ]
                                if ts.has_selection
                                else cast(pd.DataFrame, ts._data)["value"]
                            )
                            for ts in timeseries
                        ],
                        axis=1,
                    ).apply(lambda row: np.percentile(row.dropna(), pct), axis=1),
                    "quality": 0,
                },
                index=common_index,
            )
            return ts
        finally:
            for i in range(len(timeseries)):
                if timeseries[i].selection_state == SelectionState.TRANSIENT:
                    timeseries[i].select(Select.ALL)

    @property
    def qualities(self) -> list[int]:
        """
        The qualities as a list of integers (empty if there is no data)

        Operations:
            Read Only
        """
        return (
            []
            if self._data is None or cast(pd.DataFrame, self.data).empty
            else (
                [tsv.quality.signed for tsv in self.tsv]
                if Quality._return_signed_codes
                else [tsv.quality.unsigned for tsv in self.tsv]
            )
        )

    def resample(
        self,
        operation: str,
        interval: Optional[Union["TimeSeries", TimeSpan, timedelta]] = None,
        offset: Optional[Union[int, TimeSpan, timedelta]] = None,
        start_time: Optional[Union[HecTime, datetime, str]] = None,
        end_time: Optional[Union[HecTime, datetime, str]] = None,
        max_missing_percent: float = 25.0,
        entire_interval: Optional[bool] = None,
        before: Union[str, float] = 0.0,
        after: Union[str, float] = _RESAMPLE_LAST,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Resamples a time series using a specified operation onto an interval or time pattern and returns the result, which may be a new time series or this time series modified.

        For this method document:
        * **old**: pertains to the time series this method is called on
        * **new**: pertains to the result time series
        * **point**: a time/value combination in a time series
        * **interval**: the time between one point (exclusive) and the next (inclusive), regardless of whether it corresponds to an actual [`Interval`](interval.html#Interval)
        * **interval time**: the ending time of the interval

        **Operation Types**

        The resample operations are divided in to discreet and continuous operations:
        * **Discreet**:
            * `Count`: The number of valid old points in each new interval
            * `Maximum`: The maximum value of valid old points in each new interval
            * `Minimum`: The minimum value of valid old points in each new interval
            * `Previous`: The value of the latest valid old point prior to each new interval time
        * **Continuous**:
            * `Interpolate`: Find the value at each new interval time (see callouts in plots below)
            * `Integrate`: Integrate the time series for each new interval(see shaded area in plots below)
            * `Average`: The integration of the time series for each new interval divided by the sum of the times used for integration for that interval.
              Note that this generates the *average value in the interval* which can be greater than the *average value over the interval* (integration divided by new interval span)
              if one or more old points in the new interval are missing or invalid.
            * `Accumulate`: The accumulation over each new interval (see computations below each plot below). Note that this differs from the [`accum`](#TimeSeries.accum) method which accumulates
              successive values in a time series.
            * `Volume`: A special case of `Integrate` that requires the old time series to have the base parameter of "Flow'; the new base parameter is "Volume"

        For discreet operations (except `Previous`) the `entire_interval` argument specifies whether to require that each entire old interval falls within the new interval
        (True) or to allow all old points whose interval time is in the new interval (False).

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        **Parameter Type Effects**

        Interpolation, which is performed for all continous operations, and accumulation are dependent on the [`parameter_type`](#TimeSeries.parameter_type) of the time series. Each plot below
        is for a 1-Hour regular time series with the following points:
        |Time|Value|
        |----|-----|
        |01Feb2025 01:10|1.0|
        |01Feb2025 02:10|2.0|
        |01Feb2025 03:10|3.0|
        |01Feb2025 04:10|4.0|
        |01Feb2025 05:10|3.0|
        |01Feb2025 06:10|2.0|
        The callouts show the interpolated values at 01:00 (except for Intantaneous), 02:00, 03:00, 04:00, 05:00, and 06:00. The shaded portion show the area used for integration,
        which is performed not only for the `Integrate` operation, but `Average` and `Volume` operations as well. Below each plot the accumulation from 02:00 to 04:00 is computed.

        * **Instantaneous Types** (CWMS: Inst, DSS: INST-VAL, INST-CUM): ![Intantaneous interpolataion and integration](images/Interpolate_Integrate_Instantaneous.png)
        <br>*For instantaeous accumulation (e.g., CWMS: Precip.Inst, DSS INST-CUM), any point with a value lower than the previous point is considered to be invalid, so 05:00 and and 06:00 would be invalid values.*
        <br>`Accumulation (02:00-04:00) = 3.8333 - 1.8333 = 2.0`.
        * **Period Constant Types** (CWMS: Ave, Const, Min, Max, DSS: PER-AVER, PER-MIN, PER-MAX): ![Period value interpolataion and integration](images/Interpolate_Integrate_Average.png)
        <br>`Accumulation (02:00-04:00) = 4.0000 - 2.0000 = 2.0`.
        * **Period Total Types** (CWMS: Total, DSS: PER-CUM): ![Total interpolataion and integration](images/Interpolate_Integrate_Total.png)
        <br>`Accumulation (02:00-04:00) = 2.0000 - 1.6667 + 3.0 + 3.3333 = 6.6667`.

        **Parameters, Units, and Parameter Types**

        The new time series may have different parameter, unit, and/or parameter than the old time series:
        * `Count`:
            * **Parameter**: will be "Count-&lt;old_parameter&gt;"
            * **Unit**: will be "unit"
            * **Parameter Type**: will be Total (CWMS: Total, DSS: PER-CUM)
        * `Maximum`
            * **Parameter Type**: will be Maximum (CWMS: Max, DSS: PER-MAX)
        * `Minimum`
            * **Parameter Type**: will be Minimum (CWMS: Min, DSS: PER-MIN)
        * `Integrate`:
            * **Parameter**: will be the integration parameter returned by [get_integration_parameter()](#TimeSeries.get_integration_parameter)
            * **Unit**: will be the unit of the parameter returned by [get_integration_parameter()](#TimeSeries.get_integration_parameter), which preserves the unit system of the old time series
        * `Average`
            * **Parameter Type**: will be Average (CWMS: Ave, DSS: PER-AVER)
        * `Volume`:
            * **Parameter**: will be "Volume"
            * **Unit**: will be "ft3" or "m3" depending on the unit system of the old time series

        <a name="restrictions"></a>
        **Restrictions**

        Not all continuous resample operations can be performed on all time series.
        * `Integrate`:
            * May be performed only on time series with integrable base parameters. Use [Parameter.integrable_base_parameters()](parameter.html#Parameter.integrable_base_parameters) to
              list the integrable base parameters.
            * May be performed only on Instantaneous, Average, or constant time series (CWMS: Inst, Ave, Const, DSS: INST-VAL, INST-CUM, PER-AVER)
        * `Accumulate`:
            * May be performed only on time series with accumulatable base parameters. Use [Parameter.accumulatable_base_parameters()](parameter.html#Parameter.accumulatable_base_parameters) to
              list the accumulatable base parameters.
            * May be performed only on Instantaneous, Average, or Total time series (CWMS: Inst, Ave, Total, DSS: INST-VAL, INST-CUM, PER-CUM)
        * `Volume`:
            * May be performed only on Instantaneous, Average, or Constant time series (CWMS: Inst, Ave, Const, DSS: INST-VAL, INST-CUM, PER-AVER) with base parameter of "Flow"

        Args:
            operation (str): The resample operation to perform. Must be one of `Count`, `Maximum`, `Minimum`, `Previous`, `Interpolate`, `Integrate`, `Average`, `Accumulate`, or `Volume` or a unique
                beginning portion (case insensitive). 'c' is interpeted as `Count`, but 'INT' is ambiguous between `Interpolate` and `Integrate`.
            interval (Optional[Union[&quot;TimeSeries&quot;, TimeSpan, timedelta]]): The interval or time pattern to resample onto. If None, the old interval is used. Otherwise the following
                can be used:
                * [`Interval`](interval.html#Interval): resample onto a standard regular or local-regular interval
                * [`TimeSpan`](timespan.html#TimeSpan) or `timedelta`: resample onto non-standard regular interval
                * [`TimeSeries`](#TimeSeries): resample onto an irregular time interval
                Defaults to None.
            offset (Optional[Union[int, TimeSpan, timedelta]]): Offset into `interval` for each new time. If specified as an int, the value is in minutes. None is the
                same as specifying `0`, `TimeSpan("PT0S")`, or `timedelta(seconds=0)`. Defaults to None
            start_time (Optional[Union[HecTime, datetime, str]]): Start time of the new time series. None specifies the same start time as the old time sereies. Defaults to None.
            end_time (Optional[Union[HecTime, datetime, str]]): End time of the new time series. None specifies the same end time as the old time sereies. Defaults to None.
            max_missing_percent (float, optional): The maximum amount of time in each new interval that can be invalid or missing and still perform the resample operation for that interval.
                If the old time series is regular interval, this is approximately equivalent to the max percent of points that can be invalid or missing. If more than this amount of time
                is invalid or missing in any new interval, the value for that interval will be set to missing. Defaults to 25.0.
            entire_interval (Optional[bool]): *Used only for discreet resample operations (except `Previous`)*. Specifies whether to require each old interval to begin and end in the new
                interval in order to be considered (True) or to allow all old intervals that end in the new interval (False). If None, each old interval is required toe begin and end in the new interval
                for all data types except Instantaneous (CWMS: Inst, DSS: INST-VAL, INST-CUM). Defaults to None.
            before (Union[str, float], optional): *Used only for time patterns*. Specfies the value for new points (points in the time pattern) that are prior to the beginning of the old time series.
                * **float**: The floating point value to set the new points to.
                * **str**: May be one of
                    * "FIRST": sets the new values to the first value in the old time series
                    * "MISSING": sets the new values to missing
                Defaults to 0.0.
            after (Union[str, float], optional): *Used only for time patterns*. Specfies the value for new points (points in the time pattern) that are after to the end of the old time series.
                * **float**: The floating point value to set the new points to.
                * **str**: May be one of
                    * "LAST": sets the new values to the last value in the old time series
                    * "MISSING": sets the new values to missing
                Defaults to "LAST".
            in_place (bool, optional): Specifies whether to resample onto this time series (True) or onto a new time series (False). Defaults to False.

        Raises:
            TimeSeriesException:<br>
                * on time series with no data
                * on time series with no parameter type
                * on invalid `operation` parameter (matches zero or more than one)
                * on invalid `before` paremeter
                * on invalid `after` parameter
                * on empty pattern time series
                * on attempt perform invalid continuous resample operation (see [Restrictions](#restrictions)) above
            TypeError:<br>
                * on unexpected `interval` type parameter

        Returns:
            TimeSeries: The resampled time series, whether this one or a new one.
        """
        # ------------- #
        # sanity checks #
        # ------------- #
        if self._data is None or self._data.empty:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        if self.parameter_type is None:
            raise TimeSeriesException(
                "Cannot resample a time series without a known parameter type."
            )
        matched_operations = [
            o for o in _resample_operations if o.startswith(operation.upper())
        ]
        if not matched_operations:
            raise TimeSeriesException(
                f"'{operation}' does not match any valid resample operation"
            )
        if len(matched_operations) > 1:
            raise Exception(
                f"'{operation}' matches multiple operations: {', '.join(matched_operations)}"
            )
        resample_operation = matched_operations[0]
        if isinstance(before, str):
            matched_value = [
                o for o in _resample_before if o.startswith(before.upper())
            ]
            if not matched_value:
                raise TimeSeriesException(
                    f"'{before}' doesn't match any valid before option"
                )
            if matched_value[0] == _RESAMPLE_FIRST:
                before_value = -math.inf
            elif matched_value[0] == _RESAMPLE_MISSING:
                before_value = math.inf
            else:
                raise TimeSeriesException(
                    f"'{matched_value}' is unexpected before option"
                )
        else:
            before_value = before
        if isinstance(after, str):
            matched_value = [o for o in _resample_after if o.startswith(after.upper())]
            if not matched_value:
                raise TimeSeriesException(
                    f"'{after}' doesn't match any valid after option"
                )
            if matched_value[0] == _RESAMPLE_LAST:
                after_value = -math.inf
            elif matched_value[0] == _RESAMPLE_MISSING:
                after_value = math.inf
            else:
                raise TimeSeriesException(
                    f"'{matched_value}' is unexpected after option"
                )
        else:
            after_value = after
        # ---------------------------------------- #
        # Generate time series values at new times #
        # ---------------------------------------- #
        time_window = {
            "start": HecTime(start_time if start_time else self.times[0]),
            "end": HecTime(end_time if end_time else self.times[-1]),
        }
        new_tsvs: List[TimeSeriesValue]
        interval_offset = (
            TimeSpan()
            if not offset
            else (
                TimeSpan(0, 0, 0, 0, offset)
                if isinstance(offset, int)
                else TimeSpan(offset)
            )
        )
        if interval is None or isinstance(interval, TimeSeries):
            # --------------------------------- #
            # use pattern time series for times #
            # --------------------------------- #
            timeseries = interval
            if timeseries is None:
                # ------------------------------------- #
                # use same interval as this time series #
                # ------------------------------------- #
                timeseries = self
            if timeseries._data is None or timeseries._data.empty:
                raise TimeSeriesException(
                    "Operation is invalid with empty pattern time series."
                )
            new_tsvs = [
                TimeSeriesValue(
                    HecTime(t) + interval_offset,
                    UnitQuantity(math.nan, timeseries.unit),
                    0,
                )
                for t in timeseries.times
            ]
            if timeseries.has_selection:
                new_tsvs = [
                    new_tsvs[i]
                    for i in list(
                        np.flatnonzero(cast(pd.DataFrame, timeseries.data)["selected"])
                    )
                ]
                if timeseries.selection_state == SelectionState.TRANSIENT:
                    timeseries.iselect(Select.ALL)
        elif isinstance(interval, Interval):
            # ---------------------- #
            # use Interval for times #
            # ---------------------- #
            start_time = cast(HecTime, time_window["start"].clone())
            if interval.is_any_regular:
                start_time -= TimeSpan(
                    minutes=cast(int, start_time.get_interval_offset(interval))
                    - interval_offset.total_seconds() // 60
                )
                if start_time < time_window["start"]:
                    start_time += interval
            new_tsvs = []
            t = start_time
            while t <= time_window["end"]:
                new_tsvs.append(
                    TimeSeriesValue(t, UnitQuantity(math.nan, self.unit), 0)
                )
                t += interval
        elif isinstance(interval, (TimeSpan, timedelta)):
            # ---------------------- #
            # use TimeSpan for times #
            # ---------------------- #
            timespan = (
                TimeSpan(interval) if isinstance(interval, timedelta) else interval
            )
            new_tsvs = []
            t = time_window["start"] + interval_offset
            while t <= time_window["end"]:
                new_tsvs.append(
                    TimeSeriesValue(t, UnitQuantity(math.nan, self.unit), 0)
                )
                t += timespan
        else:
            raise TypeError(
                f"Expected Optional[Union[TimeSeries, TimeSpan, timedelta]] for interval parameter, got {type(interval)}"
            )
        # ------------------------------------------------------------ #
        # generate time series values at (possibly selected) old times #
        # ------------------------------------------------------------ #
        old_tsvs = self.tsv
        if self.has_selection:
            old_tsvs = [
                old_tsvs[i]
                for i in list(np.flatnonzero(cast(pd.DataFrame, self.data)["selected"]))
            ]
        # ----------------------------------------------------------- #
        # get the bounding indices of the old times for each new time #
        # ----------------------------------------------------------- #
        bounds: List[Any] = len(new_tsvs) * [None]
        for i in range(len(new_tsvs)):
            prev = bisect.bisect_right(old_tsvs, new_tsvs[i])
            if prev == 0:
                # ------------------------------------------------------------------------- #
                # old time is before first new time  - set value and leave bounds[i] = None #
                # ------------------------------------------------------------------------- #
                if math.isfinite(before_value) or math.isnan(before_value):
                    new_tsvs[i].value = UnitQuantity(before_value, self.unit)
                elif before_value == -math.inf:
                    # RESAMPLE_FIRST
                    new_tsvs[i].value = old_tsvs[0].value
                else:
                    # RESAMPLE_MISSING
                    new_tsvs[i].value = UnitQuantity(math.nan, self.unit)
            elif prev == len(old_tsvs):
                prev -= 1
                if old_tsvs[prev].time == new_tsvs[i].time:
                    # --------------------------------- #
                    # old time is exactly last new time #
                    # --------------------------------- #
                    bounds[i] = (prev, prev)
                else:
                    # ----------------------------------------------------------------------------------------- #
                    # old time is after last new time - set remaining values and leave bounds for values = None #
                    # ----------------------------------------------------------------------------------------- #
                    for j in range(i, len(new_tsvs)):
                        if math.isfinite(after_value) or math.isnan(after_value):
                            new_tsvs[j].value = UnitQuantity(after_value, self.unit)
                        elif after_value == -math.inf:
                            # _RESAMPLE_LAST
                            new_tsvs[j].value = old_tsvs[-1].value
                        else:
                            # _RESAMPLE_MISSING
                            new_tsvs[j].value = UnitQuantity(math.nan, self.unit)
                    break
            else:
                # ----------------------------------------------------------------------------- #
                # old time is in range of new times - set the bounds to fill in the value later #
                # ----------------------------------------------------------------------------- #
                prev -= 1
                if old_tsvs[prev].time == new_tsvs[i].time:
                    bounds[i] = (prev, prev)
                else:
                    bounds[i] = (prev, prev + 1)
        # ------------------------------ #
        # perform the resample operation #
        # ------------------------------ #
        target = self if in_place else self.copy()
        is_discreet = _resample_operations[resample_operation]
        if is_discreet:
            self._resample_discreet(
                resample_operation, old_tsvs, new_tsvs, bounds, entire_interval
            )
        else:
            is_regular = isinstance(interval, Interval) and interval.is_any_regular
            self._resample_continuous(
                resample_operation,
                old_tsvs,
                new_tsvs,
                is_regular,
                bounds,
                max_missing_percent,
            )
        target._data = None
        # ------------------------------------------------ #
        # update parameter and unit info for the operation #
        # ------------------------------------------------ #
        if resample_operation == _RESAMPLE_OP_AVERAGE:
            target.iset_parameter_type(ParameterType("Average", target.context))
        elif resample_operation == _RESAMPLE_OP_COUNT:
            target.iset_parameter(f"Count-{target.parameter.name}")
            target.iset_parameter_type(ParameterType("Total", target.context))
        elif resample_operation == _RESAMPLE_OP_MAXIMUM:
            target.iset_parameter_type(ParameterType("Maximum", target.context))
        elif resample_operation == _RESAMPLE_OP_MINIMUM:
            target.iset_parameter_type(ParameterType("Minimum", target.context))
        elif resample_operation in (_RESAMPLE_OP_INTEGRATE, _RESAMPLE_OP_VOLUME):
            new_parameter = self.get_integration_parameter()
            target.iset_parameter(new_parameter)
        # ---------------------------- #
        # update interval information  #
        # ---------------------------- #
        if interval is None:
            target.iset_interval(self.interval)
        elif isinstance(interval, TimeSeries):
            target.iset_interval(interval.interval)
        elif isinstance(interval, Interval):
            target.iset_interval(interval)
        else:
            if target.context == DSS:
                times_per_year = len(new_tsvs) / (
                    (
                        cast(datetime, new_tsvs[-1].time.datetime())
                        - cast(datetime, new_tsvs[0].time.datetime())
                    ).total_seconds()
                    / 86400.0
                    / 365.0
                )
                if times_per_year < 10:
                    target.iset_interval(Interval.get_dss("Ir-Decade"))
                elif times_per_year < 1000:
                    target.iset_interval(Interval.get_dss("Ir-Year"))
                elif times_per_year < 10000:
                    target.iset_interval(Interval.get_dss("Ir-Month"))
                else:
                    target.iset_interval(Interval.get_dss("Ir-Day"))
            else:
                target.iset_interval(Interval.get_cwms("0"))
        # ---------------------- #
        # rebuild the data frame #
        # ---------------------- #
        target._data = pd.DataFrame(
            {
                "value": [tsv.value.magnitude for tsv in new_tsvs],
                "quality": [tsv.quality.code for tsv in new_tsvs],
            },
            index=pd.Index([tsv.time.datetime() for tsv in new_tsvs], name="time"),
        )
        # -------------------------------- #
        # return the resampled time series #
        # -------------------------------- #
        target._validate()
        return target

    def round_off(
        self, precision: int, tens_place: int, in_place: bool = False
    ) -> "TimeSeries":
        """
        Return a time series whose values are rounded according to the parameters.

        <table>
        <tr><th>value</th><th>precision</th><th>tens_place></th><th>result</th></tr>
        <tr><td>123456.789</td><td>5</td><td>0</td><td>123460.0</td></tr>
        <tr><td>123456.789</td><td>7</td><td>-1</td><td>123456.8</td></tr>
        <tr><td>123456.789</td><td>7</td><td>0</td><td>123457.0</td></tr>
        <tr><td>123456.789</td><td>7</td><td>1</td><td>123460.0</td></tr>
        </table>

        Args:
            precision (int): The maximum number of significant digits to use.
            tens_place (int): The lowest power of 10 to have a non-zero value.
            in_place (bool, optional): Modify and return this object if True, otherwise modify
                and return a copy of this object. Defaults to False.

        Returns:
            TimeSeries: The modified object
        """
        return self.map(
            lambda v: TimeSeries._round_off(v, precision, tens_place), in_place
        )

    def screen_with_constant_value(
        self,
        duration: Union[Duration, str],
        missing_limit: float = math.nan,
        reject_limit: float = math.nan,
        question_limit: float = math.nan,
        min_threshold: float = math.nan,
        percent_valid_required: float = math.nan,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - setting values and/or quality codes
        where the value changes over a specified duration are below specified limits.

        Args:
            duration (Union[Duration, str]): The duration over which to screen the value changes. May be a
                [`Duration`](duration.html#Duration) object or the name of a valid duration (e.g., '6Hours', '1Day', ...).
            missing_limit (float, optional): The mininum value change over the duration that is not flagged as missing. Values flagged as missing also have the value modified to math.nan. Defaults to math.nan (test not performed).
            reject_limit (float, optional): The mininum non-missing value change over the duration that is not flagged as rejected. Defaults to math.nan (test not performed).
            question_limit (float, optional): The mininum non-rejected, non-missing value change over the duration that is not flagged as questionable. Defaults to math.nan (test not performed).
            min_threshold (float, optional): Values less than this will not be screened. Defaults to math.nan (test not performed)
            percent_valid_required (float, optional): The minimum percent (0..100) of valid values in the duration that will allow the value to be screened. Defaults to math.nan (test not performed).
                Defaults to math.nan. Values are invalid if any of the following are true:
                * The quality is MISSING
                * The quality is REJECTED
                * The value is NaN
                * The value is Infinite
            in_place (bool, optional): Specifies whether to modify this time series (True) or a copy of it. Defaults to False.

        Raises:
            TimeSeriesException: If any of the following are true:
                * The time series has fewer than two values to be screened.
                * If `percent_valid_required` is not in the range 0..100
                * If the non-NaN limits are not in the following increasing-value order:
                    * `missing_limit`
                    * `reject_limit`
                    * `question_limit`

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        if isinstance(duration, str):
            dur = Duration(duration)
        else:
            dur = duration
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        df_protected = df.loc[
            (df["quality"] & 0b1000_0000_0000_0000_0000_0000_0000_0000) != 0
        ].copy()
        # ---------------- #
        # do the screening #
        # ---------------- #
        quality_codes = TimeSeries._screen_with_constant_value(
            list(map(HecTime, map(self.format_time_for_index, df.index.tolist()))),
            df["value"].tolist(),
            df["quality"].tolist(),
            dur,
            missing_limit,
            reject_limit,
            question_limit,
            min_threshold,
            percent_valid_required,
        )
        df.loc[:, "quality"] = df["quality"] & 0b0_0001 | np.array(quality_codes)
        df.loc[(df["quality"] & 0b0_0101 == 0b0_0101), "value"] = np.nan
        df.update(df_protected)
        # -------------------------------------------------- #
        # can't use .update(df) because it doesn't copy NaNs #
        # -------------------------------------------------- #
        for idx in df_protected.index:
            df.loc[idx, "value"] = df_protected.loc[idx, "value"]
            df.loc[idx, "quality"] = df_protected.loc[idx, "quality"]
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def screen_with_duration_magnitude(
        self,
        duration: Union[Duration, str],
        min_missing_limit: float = math.nan,
        min_reject_limit: float = math.nan,
        min_question_limit: float = math.nan,
        max_question_limit: float = math.nan,
        max_reject_limit: float = math.nan,
        max_missing_limit: float = math.nan,
        percent_valid_required: float = 0.0,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - setting values and/or quality codes
        where the accumulated values over a specified duration are outside the specified range.

        Args:
            duration (Union[Duration, str]): The duration over which to screen the accumulated values. May be a
                [`Duration`](duration.html#Duration) object or the name of a valid duration (e.g., '6Hours', '1Day', ...). Accumulations for durations that are not even multiples
                of regular time series intervals may be used. Irregular time series may also be screened. The end of the duration is always positioned at the time (assumed to be EOP) of
                the accumulation to be screened. If the beginning of the duration does not align with a data time in the time series, a fraction of the first interval's accumulation is used.
                Only EOP durations may be used.
            min_missing_limit (float, optional): The minimum accumulation over the duration that is not flagged as missing. Values flagged as missing also have the value modified to math.nan. Defaults to `math.nan` (test disabled).
            min_reject_limit (float, optional): The minimum non-missing accumulation over the duration that is not flagged as rejected. Defaults to `math.nan` (test disabled).
            min_question_limit (float, optional): The minimum non-rejected, non-missing accumulation over the duration that is not flagged as questioned. Defaults to `math.nan` (test disabled).
            max_question_limit (float, optional): The maximum non-rejected, non-missing accumulation over the duration that is not flagged as questioned. Defaults to `math.nan` (test disabled).
            max_reject_limit (float, optional): The maximum non-missing accumulation over the duration that is not flagged as rejected. Defaults to `math.nan` (test disabled).
            max_missing_limit (float, optional): The maximum accumulation over the duration that is not flagged as missing. Values flagged as missing also have the value modified to math.nan. Defaults to `math.nan` (test disabled).
            percent_valid_required (float, optional): The minimum percent (0..100) of valid values in the accumulation that will allow the value to be screened. Defaults to 0.
                Values are invalid if any of the following are true:
                * The quality is MISSING
                * The quality is REJECTED
                * The value is NaN
                * The value is Infinite
            in_place (bool, optional): Specifies whether to modify this time series (True) or a copy of it. Defaults to False.

        Raises:
            TimeSeriesException: If any of the following are true:
                * The time series has fewer than two values to be screened.
                * If `percent_valid_required` is not in the range 0..100
                * If the non-NaN limits are not in the following increasing-value order:
                    * `min_missing_limit`
                    * `min_reject_limit`
                    * `min_question_limit`
                    * `max_question_limit`
                    * `max_reject_limit`
                    * `max_missing_limit`

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        if isinstance(duration, str):
            dur = Duration(duration)
        else:
            dur = duration
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        df_protected = df.loc[
            (df["quality"] & 0b1000_0000_0000_0000_0000_0000_0000_0000) != 0
        ].copy()
        # ---------------- #
        # do the screening #
        # ---------------- #
        quality_codes = TimeSeries._screen_with_duration_magnitude(
            list(map(HecTime, map(self.format_time_for_index, df.index.tolist()))),
            df["value"].tolist(),
            df["quality"].tolist(),
            dur,
            min_missing_limit,
            min_reject_limit,
            min_question_limit,
            max_question_limit,
            max_reject_limit,
            max_missing_limit,
            percent_valid_required,
        )
        df.loc[:, "quality"] = df["quality"] & 0b0_0001 | np.array(quality_codes)
        df.loc[(df["quality"] & 0b0_0101 == 0b0_0101), "value"] = np.nan
        df.update(df_protected)
        # -------------------------------------------------- #
        # can't use .update(df) because it doesn't copy NaNs #
        # -------------------------------------------------- #
        for idx in df_protected.index:
            df.loc[idx, "value"] = df_protected.loc[idx, "value"]
            df.loc[idx, "quality"] = df_protected.loc[idx, "quality"]
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def screen_with_forward_moving_average(
        self,
        window: int,
        only_valid: bool,
        use_reduced: bool,
        diff_limit: float,
        failed_validity: str = "M",
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - setting values and/or quality codes where the value differ from
        those of a forward moving averge of the time series by a specified amount.

        Args:
            window (int): The number of values to average over. See [`forward_moving_average()`](#TimeSeries.forward_moving_average) for more info.
            only_valid (bool): Specifies whether to only average over windows where every value is
                valid. See [`forward_moving_average()`](#TimeSeries.forward_moving_average) for more info.
            use_reduced (bool): Specifies whether to allow averages using less than window number
                of values will be computed at the beginning of the times series. See [`forward_moving_average()`](#TimeSeries.forward_moving_average) for more info.
            diff_limit (float): The maximum difference between a value and the value at the same time in the forward moving average
                that will not be flagged as questionable, rejected, or missing. See [`forward_moving_average()`](#TimeSeries.forward_moving_average) for more info.
            failed_validity (str, optional): Specifies the validity portion of the quality code for failed values
                Must be one of "M" (Missing), "R" (Rejected) or "Q" (Questionable). Values flagged as missing also have the value modified to math.nan.
                Defaults to "M".
            in_place (bool, optional): Specifies whether to modify this time series (True) or a copy of it. Defaults to False.

        Raises:
            TimeSeriesException: If any of the following are true:
                * The time series has no data
                * The window is invalid
                * `failed_validity` is not one of "M", "R", or "Q"

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        if failed_validity.upper() not in "MQR":
            raise TimeSeriesException("Failed validity must be 'M', 'Q', or 'R'")
        validity_component = {"M": "Missing", "Q": "Questionable", "R": "Rejected"}[
            failed_validity.upper()
        ]
        quality_text = {
            "invalid-missing": "Screened Missing No_Range Original None None None Unprotected",
            "screened-okay": "Screened Okay No_Range Original None None None Unprotected",
            "screened-missing": f"Screened {validity_component} No_Range Modified Automatic Missing Relative_Value Unprotected",
            "screened-other": f"Screened {validity_component} No_Range Original None None Relative_Value Unprotected",
        }
        invalid_missing_code = Quality(quality_text["invalid-missing"].split()).code
        screened_okay_code = Quality(quality_text["screened-okay"].split()).code
        screened_missing_code = Quality(quality_text["screened-missing"].split()).code
        screened_other_code = Quality(quality_text["screened-other"].split()).code
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        df_protected = df.loc[
            (df["quality"] & 0b1000_0000_0000_0000_0000_0000_0000_0000) != 0
        ].copy()
        # ---------------- #
        # do the screening #
        # ---------------- #
        missing_indices = df.index[
            pd.isna(df["value"]) | np.isinf(df["value"])
        ].tolist()
        df.loc[missing_indices, "value"] = np.nan
        df.loc[missing_indices, "quality"] = invalid_missing_code
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]
        df_average = cast(
            pd.DataFrame,
            target.forward_moving_average(window, only_valid, use_reduced).data,
        )
        for idx in set(df.index) - set(missing_indices):
            current_quality_code = df.loc[idx, "quality"]
            if np.isnan(df_average.loc[idx, "value"]):
                continue
            if abs(df_average.loc[idx, "value"] - df.loc[idx, "value"]) > diff_limit:
                if failed_validity.upper() == "M":
                    df.loc[idx, "quality"] = (
                        current_quality_code & 0b0_0001 | screened_missing_code
                    )
                    df.loc[idx, "value"] = np.nan
                else:
                    df.loc[idx, "quality"] = (
                        current_quality_code & 0b0_0001 | screened_other_code
                    )
            elif current_quality_code & 1 == 0:
                df.loc[idx, "quality"] = screened_okay_code
        # --------------- #
        # set the results #
        # --------------- #
        for idx in df_protected.index:
            df.loc[idx, "value"] = df_protected.loc[idx, "value"]
            df.loc[idx, "quality"] = df_protected.loc[idx, "quality"]
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def screen_with_value_change_rate(
        self,
        min_reject_limit: float = math.nan,
        min_question_limit: float = math.nan,
        max_question_limit: float = math.nan,
        max_reject_limit: float = math.nan,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - settting the quality codes to
        "Okay", "Missing", "Questionable" or "Rejected" based on specified criteria about the rate of change.

        Args:
            min_reject_limit (float, optional): The minimum change per minute from one value to the next (increasing or decreasing) that is not flagged as rejected. Defaults to `math.nan` (test disabled).
            min_question_limit (float, optional): The minimum non-rejected change per minute  from one value to the next (increasing or decreasing) that is not flagged as questioned. Defaults to `math.nan` (test disabled).
            max_question_limit (float, optional): The maximum non-rejected change per minute  from one value to the next (increasing or decreasing) that is not flagged as questioned. Defaults to `math.nan` (test disabled).
            max_reject_limit (float, optional): The maximum change per minute  from one value to the next (increasing or decreasing) that is not flagged as rejected. Defaults to `-ath.nan` (test disabled).
            in_place (bool, optional): Specifies whether to modify and return this time series (True) or a copy of this
                time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If this time series has no data, or if:
                * `min_reject_limit` (if not `math.nan`) is not less than `min_question_limit` (if not `math.nan`) or `max_reject_limit` (if not `math.nan`)
                * `min_question_limit` (if not `math.nan`) is not less than `max_question_limit` (if not `math.nan`) or `max_reject_limit` (if not `math.nan`)
                * `max_question_limit` (if not `math.nan`) is not less thatn `max_reject_limit` (if not `math.nan`)

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        test_min_reject = not math.isnan(min_reject_limit)
        test_min_question = not math.isnan(min_question_limit)
        test_max_question = not math.isnan(max_question_limit)
        test_max_reject = not math.isnan(max_reject_limit)
        if test_min_reject:
            if test_min_question and min_reject_limit >= min_question_limit:
                raise TimeSeriesException(
                    "min_reject_limit must be less than min_question_limit"
                )
            if test_max_reject and max_reject_limit <= min_reject_limit:
                raise TimeSeriesException(
                    "min_reject_limit must be less than max_reject_limit"
                )
        elif test_min_question:
            if test_max_question and min_question_limit >= max_question_limit:
                raise TimeSeriesException(
                    "min_question_limit must be less than max_question_limit"
                )
            if test_max_reject and min_question_limit >= max_reject_limit:
                raise TimeSeriesException(
                    "min_question_limit must be less than max_reject_limit"
                )
        elif test_max_question and test_max_reject:
            if max_question_limit >= max_reject_limit:
                raise TimeSeriesException(
                    "max_question_limit must be less than max_reject_limit"
                )
        quality_text = {
            "okay": "Screened Okay No_Range Original None None None Unprotected",
            "missing": "Screened Missing No_Range Original None None None Unprotected",
            "question": "Screened Questionable No_Range Original None None Rate_of_Change Unprotected",
            "reject": "Screened Rejected No_Range Original None None Rate_of_Change Unprotected",
        }
        okay_code = Quality(quality_text["okay"].split()).code
        missing_code = Quality(quality_text["missing"].split()).code
        question_code = Quality(quality_text["question"].split()).code
        reject_code = Quality(quality_text["reject"].split()).code
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        data["value_diff"] = data["value"].diff()
        data["minutes_diff"] = data.index.to_series().diff().dt.total_seconds() / 60
        data["rate_of_change"] = data["value_diff"] / data["minutes_diff"]
        df = data.loc[data["selected"]] if self.has_selection else data
        # ---------------- #
        # do the screening #
        # ---------------- #
        protected_indices = set(TimeSeries._protected_indices(df))
        unscreened_indices = set([df.index[0]])
        missing_indices = (
            set(df[df["rate_of_change"].isna()].index) - unscreened_indices
        )
        question_indices = set()
        reject_indices = set()
        if test_min_reject:
            reject_indices |= set(
                df[
                    (df["rate_of_change"] < min_reject_limit)
                    & (~df.index.isin(protected_indices))
                ].index
            )
        if test_max_reject:
            reject_indices |= set(
                df[
                    (df["rate_of_change"] > max_reject_limit)
                    & (~df.index.isin(protected_indices))
                ].index
            )
        if test_min_question:
            question_indices |= set(
                df[
                    (df["rate_of_change"] < min_question_limit)
                    & (~df.index.isin(protected_indices))
                    & (~df.index.isin(reject_indices))
                ].index
            )
        if test_max_question:
            question_indices |= set(
                df[
                    (df["rate_of_change"] > max_question_limit)
                    & (~df.index.isin(protected_indices))
                    & (~df.index.isin(reject_indices))
                ].index
            )
        okay_indices = df.index.difference(
            list(
                protected_indices
                | missing_indices
                | unscreened_indices
                | question_indices
                | reject_indices
            )
        )
        df.loc[
            df["rate_of_change"].isna()
            & ~df.index.isin(protected_indices)
            & ~df.index.isin(unscreened_indices),
            "quality",
        ] = (df["quality"] & ~missing_code) | missing_code
        df.loc[
            df.index.isin(okay_indices) & ~df.index.isin(protected_indices), "quality"
        ] = okay_code
        df.loc[
            df.index.isin(missing_indices) & ~df.index.isin(protected_indices),
            "quality",
        ] |= missing_code
        df.loc[
            df.index.isin(question_indices) & ~df.index.isin(protected_indices),
            "quality",
        ] |= question_code
        df.loc[
            df.index.isin(reject_indices) & ~df.index.isin(protected_indices), "quality"
        ] |= reject_code
        data.loc[df.index, "value"] = df["value"]
        data.loc[df.index, "quality"] = df["quality"]
        return target

    def screen_with_value_range(
        self,
        min_reject_limit: float = math.nan,
        min_question_limit: float = math.nan,
        max_question_limit: float = math.nan,
        max_reject_limit: float = math.nan,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - settting the quality codes to
        "Okay", "Missing", "Questionable" or "Rejected" based on specified criteria about the value magnitudes.

        Args:
            min_reject_limit (float, optional): The minimum value that is not flagged as rejected. Defaults to `-math.nan` (test disabled).
            min_question_limit (float, optional): The minium non-rejected value that is flagged as questionable. Defaults to `-math.nan` (test disabled).
            max_question_limit (float, optional): The maxium non-rejected value that is flagged as questionable. Defaults to `-math.nan` (test disabled).
            max_reject_limit (float, optional): The minimum value that is not flagged as rejected. Defaults to `-math.nan` (test disabled).
            in_place (bool, optional): Specifies whether to modify and return this time series (True) or a copy of this
                time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If this time series has no data, or if:
                * `min_reject_limit` (if not `math.nan`) is not less than `min_question_limit` (if not `math.nan`) or `max_reject_limit` (if not `math.nan`)
                * `min_question_limit` (if not `math.nan`) is not less than `max_question_limit` (if not `math.nan`) or `max_reject_limit` (if not `math.nan`)
                * `max_question_limit` (if not `math.nan`) is not less than `max_reject_limit` (if not `math.nan`)

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        test_min_reject = not math.isnan(min_reject_limit)
        test_min_question = not math.isnan(min_question_limit)
        test_max_question = not math.isnan(max_question_limit)
        test_max_reject = not math.isnan(max_reject_limit)
        if test_min_reject:
            if test_min_question and min_reject_limit >= min_question_limit:
                raise TimeSeriesException(
                    "min_reject_limit must be less than min_question_limit"
                )
            if test_max_reject and max_reject_limit <= min_reject_limit:
                raise TimeSeriesException(
                    "min_reject_limit must be less than max_reject_limit"
                )
        elif test_min_question:
            if test_max_question and min_question_limit >= max_question_limit:
                raise TimeSeriesException(
                    "min_question_limit must be less than max_question_limit"
                )
            if test_max_reject and min_question_limit >= max_reject_limit:
                raise TimeSeriesException(
                    "min_question_limit must be less than max_reject_limit"
                )
        elif test_max_question and test_max_reject:
            if max_question_limit >= max_reject_limit:
                raise TimeSeriesException(
                    "max_question_limit must be less than max_reject_limit"
                )
        quality_text = {
            "okay": "Screened Okay No_Range Original None None None Unprotected",
            "missing": "Screened Missing No_Range Original None None None Unprotected",
            "question": "Screened Questionable No_Range Original None None Absolute_Value Unprotected",
            "reject": "Screened Rejected No_Range Original None None Absolute_Value Unprotected",
        }
        okay_code = Quality(quality_text["okay"].split()).code
        missing_code = Quality(quality_text["missing"].split()).code
        question_code = Quality(quality_text["question"].split()).code
        reject_code = Quality(quality_text["reject"].split()).code
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        # ---------------- #
        # do the screening #
        # ---------------- #
        protected_indices = set(TimeSeries._protected_indices(df))
        missing_indices = set(df[df["value"].isna()].index)
        question_indices = set()
        reject_indices = set()
        if test_min_reject:
            reject_indices |= set(
                df[
                    (df["value"] < min_reject_limit)
                    & (~df.index.isin(protected_indices))
                ].index
            )
        if test_max_reject:
            reject_indices |= set(
                df[
                    (df["value"] > max_reject_limit)
                    & (~df.index.isin(protected_indices))
                ].index
            )
        if test_min_question:
            question_indices |= set(
                df[
                    (df["value"] < min_question_limit)
                    & (~df.index.isin(protected_indices))
                    & (~df.index.isin(reject_indices))
                ].index
            )
        if test_max_question:
            question_indices |= set(
                df[
                    (df["value"] > max_question_limit)
                    & (~df.index.isin(protected_indices))
                    & (~df.index.isin(reject_indices))
                ].index
            )
        okay_indices = df.index.difference(
            list(
                protected_indices | reject_indices | question_indices | missing_indices
            )
        )
        df.loc[
            df.index.isin(okay_indices) & ~df.index.isin(protected_indices), "quality"
        ] = okay_code
        df.loc[
            df.index.isin(missing_indices) & ~df.index.isin(protected_indices),
            "quality",
        ] |= missing_code
        df.loc[
            df.index.isin(question_indices) & ~df.index.isin(protected_indices),
            "quality",
        ] |= question_code
        df.loc[
            df.index.isin(reject_indices) & ~df.index.isin(protected_indices), "quality"
        ] |= reject_code
        data.loc[df.index, "value"] = df["value"]
        data.loc[df.index, "quality"] = df["quality"]
        return target

    def screen_with_value_range_or_change(
        self,
        min_limit: float = math.nan,
        max_limit: float = math.nan,
        change_limit: float = math.nan,
        replace_invalid_value: bool = True,
        invalid_value_replacement: float = math.nan,
        invalid_validity: str = "M",
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Screens a time series - either this one or a copy of this one - setting values and/or quality codes
        where the values are outside the specified range or differ more than the specified change.

        Args:
            min_limit (float): The minimum valid value. Values below this value will have their values and/or quality codes changed.
                Defaults to `math.nan` (test disabled).
            max_limit (float): The maximum valid value. Values above this value will have their values and/or quality codes changed.
                Defaults to `math.nan` (test disabled).
            change_limit (float): The maxium valid change from one value to the next. Values whose change (either increasing or decreasing)
                is greater that is will have their values and/or quality codes changed. Defaults to `math.nan` (test disabled).
            replace_invalid_value (bool, optional): Replace screened-out values with the specified value. Defaults to True.
            invalid_value_replacement (float, optional): The value to replace screen-out values with if `replace_invalid_value=True`.
                 Defaults to `math.nan` (missing value).
            invalid_validity (str, optional): Specifies the validity component of the quality code for screened-out values.
                May be "M" (Missing), "Q" (Questionable), or "R" (Rejected). Values flagged as missing also have the value modified to math.nan.
                Defaults to "M".
            in_place (bool, optional): Specifies whether to modify and return this time series (True) or a copy of this
                time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data or f `invalid_validity` (if specified) is not 'M', 'Q', or 'R'.

        Returns:
            TimeSeries: The screened time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ---------------- #
        # set up variables #
        # ---------------- #
        test_min = not math.isnan(min_limit)
        test_max = not math.isnan(max_limit)
        test_change = not math.isnan(change_limit)
        repl_validity = invalid_validity.upper()
        if repl_validity not in "MQR":
            raise TimeSeriesException("Invalid validity must be 'M', 'Q', or 'R'")
        validity_component = {"M": "Missing", "Q": "Questionable", "R": "Rejected"}[
            repl_validity
        ]
        quality_text = {
            "okay": "Screened Okay No_Range Original None None None Unprotected",
            "abs_val": f"Screened {validity_component} No_Range Modified Automatic Missing Absolute_Value Unprotected",
            "rate_of_change": f"Screened {validity_component} No_Range Modified Automatic Missing Rate_of_Change Unprotected",
        }
        okay_code = Quality(quality_text["okay"].split()).code
        missing_code = Quality("Missing").code
        abs_value_code = Quality(quality_text["abs_val"].split()).code
        rate_of_change_code = Quality(quality_text["rate_of_change"].split()).code
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        # ---------------- #
        # do the screening #
        # ---------------- #
        protected_indices = set(TimeSeries._protected_indices(df))
        missing_indices = set(df[df["value"].isna()].index)
        min_indices = set()
        max_indices = set()
        change_indices = set()
        if test_min:
            min_indices |= set(
                df[
                    (df["value"] < min_limit) & (~df.index.isin(protected_indices))
                ].index
            )
        if test_max:
            max_indices = set(
                df[
                    (df["value"] > max_limit) & (~df.index.isin(protected_indices))
                ].index
            )
        if test_change:
            change_indices = set(
                df[
                    (abs(df["value"] - df["value"].shift(1)) > change_limit)
                    & (~df.index.isin(protected_indices))
                ].index
            )
        okay_indices = df.index.difference(
            list(
                protected_indices
                | min_indices
                | max_indices
                | change_indices
                | missing_indices
            )
        )
        df.loc[df["value"].isna(), "quality"] = (
            df["quality"] & ~missing_code
        ) | missing_code
        df.loc[
            df.index.isin(okay_indices) & ~df.index.isin(protected_indices), "quality"
        ] = okay_code
        df.loc[
            df.index.isin(min_indices) & ~df.index.isin(protected_indices), "quality"
        ] |= abs_value_code
        df.loc[
            df.index.isin(max_indices) & ~df.index.isin(protected_indices), "quality"
        ] |= abs_value_code
        df.loc[
            df.index.isin(change_indices) & ~df.index.isin(protected_indices), "quality"
        ] |= rate_of_change_code
        if replace_invalid_value:
            df.loc[
                df.index.isin(min_indices) & ~df.index.isin(protected_indices), "value"
            ] = invalid_value_replacement
            df.loc[
                df.index.isin(max_indices) & ~df.index.isin(protected_indices), "value"
            ] = invalid_value_replacement
            df.loc[
                df.index.isin(change_indices) & ~df.index.isin(protected_indices),
                "value",
            ] = invalid_value_replacement
            if math.isnan(invalid_value_replacement):
                # -------------------------------------------------- #
                # make sure quality indicates missing for NaN values #
                # -------------------------------------------------- #
                df.loc[
                    df.index.isin(min_indices) & ~df.index.isin(protected_indices),
                    "quality",
                ] = (df["quality"] & ~missing_code) | missing_code
                df.loc[
                    df.index.isin(max_indices) & ~df.index.isin(protected_indices),
                    "quality",
                ] = (df["quality"] & ~missing_code) | missing_code
                df.loc[
                    df.index.isin(change_indices) & ~df.index.isin(protected_indices),
                    "quality",
                ] = (df["quality"] & ~missing_code) | missing_code
        # -------------------------------------------------- #
        # can't use .update(df) because it doesn't copy NaNs #
        # -------------------------------------------------- #
        for idx in df.index:
            data.loc[idx, "value"] = df.loc[idx, "value"]
            data.loc[idx, "quality"] = df.loc[idx, "quality"]

        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def select(
        self,
        selection: Union[Select, int, slice, Callable[[TimeSeriesValue], bool]],
        combination: Combine = Combine.REPLACE,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Marks individual items in this object - or a copy of this object - as selected for pariticpation the next operation,
        either directly or by combining each item's current selected state with the result of a function.
        On creation the selection is cleared (i.e., every item is selected)

        This object's selection_state property determines the selection of this object after the next operation:
        * `SelectionState.TRANSIENT`: (default) The selection will be cleared after the next operation.
        * `SelectionState.DURABLE`: The selection will remain until explicitly changed by a call to iselect()

        Args:
            selection (Union[Select, int, slice, Callable[[TimeSeriesValue], bool]]): One of the following:
                * `Select.NONE`: Marks all items as unselected. Any `combination` is ignored.
                * `Select.ALL`: Marks all items as selected. Any `combination` is ignored.
                * `Select.INVERT`: Inverts the current selected state of each item. Any `combination` is ignored.
                * integer: An integer offset from the beginning of the time series
                * `HecTime` object: single item matching specified time
                * datetime object: single item matching specified time
                * string convertible to HecTime object: : single item matching specified time
                * slice: One or more items.
                    * The start parameter (if specified) and stop parameter may be:
                        * integers - offsets from the first value in the time series
                        * `HecTime` objects
                        * datetime objects
                        * strings convertible to HecTime objects
                    * The step parameter must be an integer, if specified
                * function: A function that takes a single `TimeSeriesValue` parameter and returns a bool result.
                    An item is marked as selected if and only if the result of the function is True for the item (when combined with the current state if necessary).
            combination (Combine, optional): Specifies how to combine the function result with an item's current selected state.
                Used when `selection` is not one of eh `Select` values. Defaults to Combine.REPLACE.
                * `Combine.REPLACE`: Current selected state of each item is ignored and is replaced by the result of the function.
                * `Combine.AND`: Current selected state of each item is ANDed with the result of the function to generate new selected state.
                * `Combine.OR`: Current selected state of each items is ORed with the result of the function to generate new selected state.
                * `Combine.XOR`: Current selected state of each item is XORed with the result of the function to generate new selected state.
            in_place (bool, optional): Specifies whether to mark itmes in this object (True) or a copy of this object (False). Defaults to False.

        Raises:
            TimeSeriesException: If this object has no data
            ValueError: If an invalid selection or combination is specified.

        Returns:
            TimeSeries: The marked object
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        if isinstance(selection, Select):
            # ---------------- #
            # direct selection #
            # ---------------- #
            if selection == Select.NONE:
                data.assign(selected=False)
            elif selection == Select.ALL:
                if "selected" in data.columns:
                    data = data.drop(columns=["selected"])
            elif selection == Select.INVERT:
                if "selected" in data.columns:
                    data.loc[:, "selected"] = data.loc[:, "selected"] != True
                else:
                    data.assign(selected=False)
            elif selection == Combine.NOOP:
                pass
            else:
                raise ValueError(f"Invalid selection: {selection}")
        elif isinstance(selection, int):
            # --------------------- #
            # selection via integer #
            # --------------------- #
            func = (
                lambda tsv: target.format_time_for_index(tsv.time)
                in target.__getitem__(slice(selection, selection + 1)).times
            )
            return target.iselect(func, combination)
        elif isinstance(selection, HecTime):
            # --------------------- #
            # selection via HecTime #
            # --------------------- #
            func = lambda tsv: target.format_time_for_index(
                tsv.time
            ) == target.format_time_for_index(selection)
            return target.iselect(func, combination)
        elif isinstance(selection, (str, datetime)):
            # -------------------------------- #
            # selection via string or datetime #
            # -------------------------------- #
            func = lambda tsv: target.format_time_for_index(
                tsv.time
            ) == target.format_time_for_index(HecTime(selection))
            return target.iselect(func, combination)
        elif isinstance(selection, slice):
            # ------------------- #
            # selection via slice #
            # ------------------- #
            func = (
                lambda tsv: target.format_time_for_index(tsv.time)
                in target.__getitem__(selection).times
            )
            return target.iselect(func, combination)
        elif type(selection) == types.FunctionType:
            # ---------------------- #
            # selection via function #
            # ---------------------- #
            func = selection
            if combination == Combine.REPLACE:
                data.loc[:, "selected"] = data.apply(
                    lambda row: func(self._tsv(row)),
                    axis=1,
                )
            elif combination == Combine.AND:
                if "selected" in cast(pd.DataFrame, target._data).columns:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: row["selected"] and func(self._tsv(row)),
                        axis=1,
                    )
                else:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: func(self._tsv(row)),
                        axis=1,
                    )
            elif combination == Combine.OR:
                if "selected" in cast(pd.DataFrame, target._data).columns:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: row["selected"] or func(self._tsv(row)),
                        axis=1,
                    )
                else:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: func(self._tsv(row)),
                        axis=1,
                    )
            elif combination == Combine.XOR:
                if "selected" in cast(pd.DataFrame, target._data).columns:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: (row["selected"] or func(self._tsv(row)))
                        and not (row["selected"] and func(self._tsv(row))),
                        axis=1,
                    )
                else:
                    data.loc[:, "selected"] = data.apply(
                        lambda row: not func(self._tsv(row)),
                        axis=1,
                    )
            else:
                raise ValueError(f"Invalid combination: {combination}")
        else:
            raise TypeError(
                f"Invalid type for 'selection' parameter: {type(selection)}"
            )
        target._data = data
        return target

    def select_valid(self, in_place: bool = False) -> "TimeSeries":
        """
        Marks individual items in this object - or a copy of this object - as selected for pariticpation the next operation based on whether
        the items are valid. Items are valid unless any of the following are true:
        * The quality is MISSING
        * The quality is REJECTED
        * The value is NaN
        * The value is Infinite

        This selection replaces any other selection - if it is to be combined with other selection criteria
        it must be performed before the other criteria


        This object's selection_state property indicates/determines whether the selection is cleared af the next operation (via
        an automatic ts.select(Select.NONE)) or maintained until explicitly modified.

        Args:
            in_place (bool, optional): Specifies whether to mark itmes in this object (True) or a copy of this object (False). Defaults to False.

        Raises:
            TimeSeriesException: If this object has no data

        Returns:
            TimeSeries: The marked object
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        data.loc[:, "selected"] = data.index.isin(TimeSeries._valid_indices(data))
        return target

    @property
    def selected(self) -> list[bool]:
        """
        The current selection (empty if all items are selected)

        Operations:
            Read Only
        """
        return (
            []
            if self._data is None or "selected" not in self._data.columns
            else self._data["selected"].tolist()
        )

    @property
    def selection_state(self) -> SelectionState:
        """
        The persistence state of selections in this object.

        The default selection_state of [SelectionState.TRANSIENT](./const.html#SelectionState)

        Operations:
            Read/Write
        """
        return self._selection_state

    @selection_state.setter
    def selection_state(self, period: SelectionState) -> None:
        self._selection_state = period

    def set_duration(
        self, value: Union[Duration, str, int], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the Duration for this time series, or a copy of it, and returns the modified time series

        Args:
            value (Union[Duration, str]):
                * Interval: The Duration object to use
                * str: The duration name
                * int: The (actual or characteristic) number of minutes for the duration
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if isinstance(value, Duration):
            target._duration = value
        else:
            target._duration = Duration.for_interval(value)
        return target

    def set_interval(
        self, value: Union[Interval, str, int], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the interval for this time series, or a copy of it, and returns the modified time series

        Args:
            value (Union[Interval, str]):
                * Interval: The Interval object to use
                * str: The interval name
                * int: The (actual or characteristic) number of minutes for the interval
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if isinstance(value, Interval):
            target._interval = value
        else:
            if target._context == CWMS:
                target._interval = Interval.get_cwms(value)
            else:
                target._interval = Interval.get_dss(value)
        target._validate()
        return target

    def set_location(
        self, value: Union[Location, str], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the location for this time series or a copy of it and returns the modified time series

        Args:
            value (Union[Location, str]):
                * Location: The Location object to use
                * str: The location name (may be in the format &lt;*office*&gt;/&lt;*location*&gt; to set office)
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if isinstance(value, Location):
            target._location = value
        else:
            if target._context == CWMS:
                try:
                    office, location = value.split("/")
                    target._location = Location(location, office)
                except:
                    target._location = Location(value)
            elif target._context == DSS:
                target._location = Location(value)
            else:
                raise TimeSeriesException(f"Invalid context: {target._context}")
        return target

    def set_parameter(
        self, value: Union[Parameter, str], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the parameter for this time series or a copy of it, and returns the modified time series

        Args:
            value (Union[Parameter, str]):
                * Parameter: The Parameter object to use
                * str: The parameter name - the unit will be set to the default English unit
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if isinstance(value, Parameter):
            target._parameter = value
        else:
            target._parameter = Parameter(value, "EN")
        return target

    def set_parameter_type(
        self, value: Union[ParameterType, str], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the parameter type for this time series, or a copy of it, and returns the modified time series

        Args:
            value (Union[ParameterType, str]):
                * ParameterType: The ParameterType object to use
                * str: The parameter type name
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified object
        """
        target = self if in_place else self.copy()
        if isinstance(value, ParameterType):
            target._parameter_type = value
        else:
            target._parameter_type = ParameterType(value)
        return target

    def set_protected(self, in_place: bool = False) -> "TimeSeries":
        """
        Sets the quality protection bit of selected items of this time series - or a copy of it - and
        returns the modified time series.

        Args:
            in_place (bool, optional): Specifies whether to modify and return this time series (True)
                or a copy of this time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data.

        Returns:
            TimeSeries: The modidified time series
        """
        if self._data is None:
            raise TimeSeriesException("Operation is invalid with empty time series.")
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if target.has_selection else data
        # -------------------------------------------- #
        # set the protection bit of selected qualities #
        # -------------------------------------------- #
        df.loc[:, "quality"] |= 0b1000_0000_0000_0000_0000_0000_0000_0001
        data.loc[df.index, "quality"] = df["quality"]
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def set_unprotected(self, in_place: bool = False) -> "TimeSeries":
        """
        Un-sets the quality protection bit of selected items of this time series - or a copy of it - and
        returns the modified time series.

        Args:
            in_place (bool, optional): Specifies whether to modify and return this time series (True)
                or a copy of this time series (False). Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data.

        Returns:
            TimeSeries: The modidified time series
        """
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        df = data.loc[data["selected"]] if self.has_selection else data
        df.loc[:, "quality"] = df["quality"] & 0b0111_1111_1111_1111_1111_1111_1111_1111
        cast(pd.DataFrame, target._data).update(df)
        if self.selection_state == SelectionState.TRANSIENT:
            self.iselect(Select.ALL)
            if target is not self:
                target.iselect(Select.ALL)
        return target

    def set_quality(
        self, quality: Union[Quality, int], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the quality of selected items of this object or a copy of this object

        Args:
            quality: Union[Quality, int]: The quality to set for selected items
            in_place (bool): Specifies whether to set the values in this object
                (True) or a copy of this object (False)

        Returns:
            TimeSeries: The modified object
        """
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        if target.has_selection:
            data.loc[data["selected"], ["quality"]] = Quality(quality).code
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if target is not self:
                    target.iselect(Select.ALL)
        else:
            data["quality"] = Quality(quality).code
        return target

    @classmethod
    def set_slice_stop_exclusive(cls, state: bool = True) -> None:
        """
        Set the default slicing behavior of new TimeSeries objects

        Args:
            state (bool, optional): Defaults to True.
                * `True`: python behavior (stop value is excluded)
                * `False`: DataFrame behavior (stop value is included)
        """
        cls._default_slice_stop_exclusive = state

    @classmethod
    def set_slice_stop_inclusive(cls, state: bool = True) -> None:
        """
        Set the default slicing behavior of new TimeSeries objects

        Args:
            state (bool, optional): Defaults to True.
                * `True`: DataFrame behavior (stop value is included)
                * `False`: python behavior (stop value is excluded)
        """
        cls._default_slice_stop_exclusive = not state

    def set_unit(self, value: Union[Unit, str], in_place: bool = False) -> "TimeSeries":
        """
        Sets the parameter unit for this time series, or a copy of it, and returns the modified time series.

        **NOTE**: This does *not* modify any data values. Use the [ito()](#TimeSeries.ito) method
        to modify data, which also sets the unit.

        Args:
            value (Union[Unit, str]):
                <ul>
                <li>Unit: The Unit object or name to use</li>
                <li>str: The unit name</li>
                </ul>
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if isinstance(value, Unit):
            if target._parameter.unit.dimensionality != Unit.dimensionality:
                raise TimeSeriesException(
                    f"Cannont set unit of {target._parameter.name} time series to {value}"
                )
            target._parameter._unit = value
            target._parameter._unit_name = eval(
                f"f'{{{value}:{UnitQuantity._default_output_format}}}'"
            )
        else:
            target._parameter.to(value, in_place=True)
        return target

    def set_value(self, value: float, in_place: bool = False) -> "TimeSeries":
        """
        Sets the value of selected items of this object or a copy of this object

        Args:
            value (float): The value to set for selected items
            in_place (bool): Specifies whether to set the values in this object
                (True) or a copy of this object (False)

        Returns:
            TimeSeries: The modified object
        """
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        if target.has_selection:
            data.loc[data["selected"], ["value"]] = value
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if target is not self:
                    target.iselect(Select.ALL)
        else:
            data["value"] = value
        return target

    def set_value_quality(
        self, value: float, quality: Union[Quality, int], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the value and quality of selected items of this object or a copy of this object

        Args:
            value (float): The value to set for selected items
            quality: Union[Quality, int]: The quality to set for selected items
            in_place (bool): Specifies whether to set the values in this object
                (True) or a copy of this object (False)

        Returns:
            TimeSeries: The modified object
        """
        target = self if in_place else self.copy()
        data = cast(pd.DataFrame, target._data)
        if target.has_selection:
            data.loc[data["selected"], ["value"]] = value
            data.loc[data["selected"], ["quality"]] = Quality(quality).code
            if self.selection_state == SelectionState.TRANSIENT:
                self.iselect(Select.ALL)
                if target is not self:
                    target.iselect(Select.ALL)
        else:
            data["value"] = value
            data["quality"] = Quality(quality).code
        return target

    def set_vertical_datum_info(
        self, value: Union[str, dict[str, Any]], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets the vertical datum info for this time series, or a copy  of it, and returns the modified time series

        Args:
            value (Union[str, dict[str, Any]]):
                <ul>
                <li>str: the vertical datum info as an XML string
                <li>dict: the vertical datum info as a dictionary</li>
                </ul>
            in_place (bool): Specifies whether to modify and return this time series (True) or a copy of this
                time series. Defaults to False.

        Raises:
            TimeSeriesException: If the base parameter is not "Elev"

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        if target._parameter.base_parameter == "Elev":
            target._parameter = ElevParameter(target._parameter.name, value)
        else:
            raise TimeSeriesException(
                f"Cannot set vertical datum on {target._parameter.name} time series"
            )
        return target

    @property
    def slice_stop_exclusive(self) -> bool:
        """
        Whether the `stop` portion of `[start:stop]` slicing is exclusive for this object.
        * If `True`, the slicing TimeSeries objects follows Python rules, where `stop`
            specifies the lowest index not included.
        * If `False`, the slicing of TimeSeries objects follows pandas.DataFrame rules,
            where `stop` specifies the highest index included.

        The default value is determined by the class state, which defaults to `True`, but
        can be set by calling [set_slice_stop_exclusive()](#TimeSeries.set_slice_stop_exclusive) or
        [set_slice_stop_inclusive()](#TimeSeries.set_slice_stop_inclusive) before creating a
        TimeSeries object

        Operations:
            Read/Write
        """
        return self._slice_stop_exclusive

    @slice_stop_exclusive.setter
    def slice_stop_exclusive(self, state: bool) -> None:
        self._slice_stop_exclusive = state

    def snap_to_regular(
        self,
        interval: Union[Interval, str],
        offset: Optional[Union[TimeSpan, timedelta, str]] = None,
        backward: Optional[Union[TimeSpan, timedelta, str]] = None,
        forward: Optional[Union[TimeSpan, timedelta, str]] = None,
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Modifies and returns a time series (either this one or a copy of this one) by snapping values to a specified regular interval
        (with an optional interval offset) and setting the interval to the one specified.
        * Only values within the `forward` and `backward` time spans around the new interval/offset will be included in the modified time series
        * If multiple values in the source time series are within the `forward` and `backward` time spans:
            * If some values are protected and others unprotected, the protected value closest to the snapping time is used.
            * If all or none of the values are protected:
                * If some values are valid and others invalid the valid value closest to the snapping time is used.
                * If all or none of the values are valid, the value closest to the snapping time is used.

        This method does not respect selections. To snap based on a selection, first use the [`filter()`](#TimeSeries.filter) or
        [`ifilter()`](#TimeSeries.ifilter) method to genrate a time series from the selected values.

        The resulting time series is always a regular time series, but if the time series has an attached time zone and `interval` is an
        [`Interval`](./interval.html#Interval) object with the [`is_local_regular`](./interval.html#Interval.is_local_regular) property of True, then the resulting time series will be a Local Regular Time Series (LRTS).

        The resulting time series will be a collapsed time series, with no values at times for which no values in the original time series
        were within the `forward` and `backward` time spans. The [`expand()`](#TimeSeries.expand) method may be used to expand the collapsed time series.

        Args:
            interval (Union[Interval, str]): The new interval
            offset (Optional[Union[TimeSpan, timedelta, str]]): The offset into the interval to snap the vlues to. Defaults to None.
            backward (Optional[Union[TimeSpan, timedelta, str]]): The time span prior to the interval/offset to accept values from.
                Defaults to None.
            forward (Optional[Union[TimeSpan, timedelta, str]]): The time span after the interval/offset to accept values from.
                Defaults to None.
            in_place (bool, optional): Specifies whether to modify this time series (True) or a copy of it (False). Defaults to False.

        Raises:
            TimeSeriesException: If the specified interval is not a valid regular interval for the context of the time series. E.g., an
                irregular interval or a DSS-only regluar interval is specified for a CWMS time series

        Returns:
            TimeSeries: The modified time series
        """
        # ----------------- #
        # handle parameters #
        # ----------------- #
        target = self if in_place else self.copy()
        intvl: Optional[Interval] = None
        ofst: Optional[TimeSpan] = None
        back: Optional[TimeSpan] = None
        ahead: Optional[TimeSpan] = None
        if isinstance(interval, str):
            if self._context == DSS:
                if interval not in Interval.get_all_dss_names(
                    lambda i: i.is_any_regular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval}' is not a valid DSS regular interval"
                    )
                intvl = Interval.get_any_dss(lambda i: i.name == interval)
            elif self._context == CWMS:
                if interval not in Interval.get_all_cwms_names(
                    lambda i: i.is_any_regular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval}' is not a valid CWMS regular interval"
                    )
                intvl = Interval.get_any_cwms(lambda i: i.name == interval)
        elif isinstance(interval, Interval):
            if self._context == DSS:
                if interval.name not in Interval.get_all_dss_names(
                    lambda i: i.is_any_regular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval.name}' is not a valid DSS regular interval"
                    )
                intvl = interval
            elif self._context == CWMS:
                if interval.name not in Interval.get_all_cwms_names(
                    lambda i: i.is_any_regular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval.name}' is not a valid CWMS regular interval"
                    )
                intvl = interval
        else:
            raise TypeError(
                f"Expected interval parameter to be Interval or str, got '{type(interval)}'"
            )
        assert intvl is not None, f"Unable to retrieve Interval with name '{interval}'"
        if offset is None:
            ofst = TimeSpan("PT0S")
        else:
            if isinstance(offset, TimeSpan):
                ofst = offset
            elif isinstance(offset, (timedelta, str)):
                ofst = TimeSpan(offset)
            else:
                raise TypeError(
                    f"Expected offset parameter to be TimeSpan, timedelta, or str, got '{type(offset)}'"
                )
            assert ofst is not None
        if backward is None:
            back = TimeSpan("PT0S")
        else:
            if isinstance(backward, TimeSpan):
                back = backward
            elif isinstance(backward, (timedelta, str)):
                back = TimeSpan(backward)
            else:
                raise TypeError(
                    f"Expected backward parameter to be TimeSpan, timedelta, or str, got '{type(backward)}'"
                )
            assert back is not None
        if forward is None:
            ahead = TimeSpan("PT0S")
        else:
            if isinstance(forward, TimeSpan):
                ahead = forward
            elif isinstance(forward, (timedelta, str)):
                ahead = TimeSpan(forward)
            else:
                raise TypeError(
                    f"Expected forward parameter to be TimeSpan, timedelta, or str, got '{type(forward)}'"
                )
            assert ahead is not None
        # --------------- #
        # do the snapping #
        # --------------- #
        tsvs = target.tsv
        tsvs_by_time: Dict[HecTime, TimeSeriesValue] = {}
        for tsv in tsvs:
            prev_time = (
                cast(
                    HecTime,
                    tsv.time - cast(int, tsv.time.get_interval_offset(intvl.minutes)),
                )
                + ofst.total_seconds() // 60
            )
            prev_offset = TimeSpan(
                minutes=(
                    cast(HecTime, (tsv.time - ofst)).get_interval_offset(intvl.minutes)
                )
            )
            next_time = prev_time + intvl if prev_time < tsv.time else prev_time
            if prev_time <= tsv.time and prev_time + ahead >= tsv.time:
                if prev_time not in tsvs_by_time:
                    tsvs_by_time[prev_time] = tsv
                else:
                    this_offset = prev_offset
                    this_valid = tsv.is_valid
                    this_protected = tsv.quality.protection
                    other_time = tsvs_by_time[prev_time].time
                    other_valid = tsvs_by_time[prev_time].is_valid
                    other_protected = tsvs_by_time[prev_time].quality.protection
                    if other_time < prev_time:
                        other_offset = prev_time - other_time
                    else:
                        other_offset = other_time - prev_time
                    if this_protected and not other_protected:
                        tsvs_by_time[prev_time] = tsv
                    elif this_valid and not other_valid:
                        tsvs_by_time[prev_time] = tsv
                    elif this_offset < other_offset:
                        tsvs_by_time[prev_time] = tsv
            if next_time - back <= tsv.time:
                if next_time not in tsvs_by_time:
                    tsvs_by_time[next_time] = tsv
                else:
                    this_offset = cast(TimeSpan, next_time - tsv.time)
                    this_valid = tsv.is_valid
                    this_protected = tsv.quality.protection
                    other_time = tsvs_by_time[next_time].time
                    other_valid = tsvs_by_time[next_time].is_valid
                    other_offset = cast(TimeSpan, next_time - other_time)
                    other_protected = tsvs_by_time[next_time].quality.protection
                    if this_protected and not other_protected:
                        tsvs_by_time[next_time] = tsv
                    elif this_valid and not other_valid:
                        tsvs_by_time[next_time] = tsv
                    elif this_offset < other_offset:
                        tsvs_by_time[next_time] = tsv
        for t in tsvs_by_time:
            tsvs_by_time[t].time = t
        new_tsvs = [tsvs_by_time[t] for t in sorted(tsvs_by_time)]
        # --------------- #
        # set the results #
        # --------------- #
        target._interval = intvl
        target._data = pd.DataFrame(
            {
                "value": [tsv.value.magnitude for tsv in new_tsvs],
                "quality": [tsv.quality.code for tsv in new_tsvs],
            },
            index=pd.Index([tsv.time.datetime() for tsv in new_tsvs], name="time"),
        )
        target._validate()
        return target

    def time_derivative(self, in_place: bool = False) -> "TimeSeries":
        """
        Returns a time series whose values are the differences of successive values in this time series divided
        by the number of minutes between the times of the values.

        A missing value at a specific time in the source time series will cause the value at that
        and the next time in the result time sereies to be missing.

        If a selection is present, all non-selected items are set to missing before the
        accumulation is computed. They remain missing in the retuned time series.

        **Restrictions**
            * May be performed only on time series with differentiable base parameters. Use [Parameter.differentiable_base_parameters()](parameter.html#Parameter.differentiable_base_parameters) to
              list the accumulatable base parameters.

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            in_place (bool, optional): If True, this object is modified and retured, otherwise
                a copy of this object is modified and returned.. Defaults to False.

        Raises:
            TimeSeriesException: If the time series has no data.

        Returns:
            TimeSeries: The time series of time-based differences
        """
        return self._diff(time_based=True, in_place=in_place)

    @property
    def time_zone(self) -> Optional[str]:
        """
        The time zone of the data

        Operations:
            Read Only
        """
        return self._timezone

    @property
    def times(self) -> list[str]:
        """
        The times as a list of strings (empty if there is no data). Items are formatted as yyyy&#8209;mm&#8209;dd&nbsp;hh:mm:ss([+|&#8209;]hh:mm)

        Operations:
            Read Only
        """
        if self._data is None:
            return []
        if len(self._data.shape) == 1:
            timestr = self._data.name.strftime("%Y-%m-%d %H:%M:%S%z")
            if timestr[-5] in "-+":
                timestr = f"{timestr[:-2]}:{timestr[-2:]}"
            return timestr
        return list(map(self.format_time_for_index, self._data.index.tolist()))

    def to(
        self,
        unit_parameter_or_datum: Union[str, Unit, Parameter],
        in_place: bool = False,
    ) -> "TimeSeries":
        """
        Converts this object - or a copy of this object - to another unit, parameter, or vertical datum

        Args:
            unit_parameter_or_datum (Union[str, Unit, Parameter]): The unit, parameter or vertical datum to convert to
            in_place (bool, optional): Whether to convert this object (True) or a copy of this object (False).
                Defaults to False.

        Raises:
            TimeSeriesException: If setting the vertical datum on a non Elev parameter or an Elev parameter
                without vertical datum information

        Returns:
            TimeSeries: The converted object
        """
        target = self if in_place else self.copy()
        if isinstance(
            unit_parameter_or_datum, str
        ) and hec.parameter._all_datums_pattern.match(unit_parameter_or_datum):
            # ----------------- #
            # to vertical datum #
            # ----------------- #
            if isinstance(target.parameter, ElevParameter):
                offset = target.parameter.get_offset_to(unit_parameter_or_datum)
                if offset:
                    offset.ito(self.unit)
                    target.parameter.ito(unit_parameter_or_datum)
                    if target._data is not None:
                        target._data["value"] += offset.magnitude
            elif target.parameter.base_parameter == "Elev":
                raise TimeSeriesException(
                    f"Cannot set vertical datum on {self.parameter.name} time series that has no vetical datum information"
                )
            else:
                raise TimeSeriesException(
                    f"Cannot set vertical datum on {self.parameter.name} time series"
                )
            return target
        param: Optional[Parameter] = None
        from_unit = target.unit
        to_unit: Union[Unit, str]
        if isinstance(unit_parameter_or_datum, Parameter):
            param = unit_parameter_or_datum
        elif isinstance(unit_parameter_or_datum, str):
            try:
                param = Parameter(unit_parameter_or_datum)
            except:
                pass
        if param is not None:
            # ------------ #
            # to parameter #
            # ------------ #
            to_unit = param.unit_name
            target.iset_parameter(param)
        else:
            to_unit = cast(Union[Unit, str], unit_parameter_or_datum)
            target.iset_unit(to_unit)
        # ------- #
        # to unit #
        # ------- #
        if target._data is not None:
            conv_1 = hec.unit.convert_units(1, from_unit, to_unit)
            conv_10 = hec.unit.convert_units(10, from_unit, to_unit)
            if conv_10 == 10 * conv_1:
                # --------------- #
                # constant factor #
                # --------------- #
                target._data["value"] *= conv_1
            elif (conv_10 - 10) == (conv_1 - 1):
                # --------------- #
                # constant offset #
                # --------------- #
                target._data["value"] += conv_1 - 1
            else:
                # --------------------------------- #
                # need to apply conversion per item #
                # --------------------------------- #
                target._data.loc[:, "value"] = target._data.apply(
                    lambda v: hec.unit.convert_units(v, from_unit, to_unit)
                )
        return target

    def to_irregular(
        self, interval: Union[Interval, str], in_place: bool = False
    ) -> "TimeSeries":
        """
        Sets a time series (either this one or a copy of this one) to a specified irregular interval, and returns
        the modified time series. The times of the data values are not changed.

        Args:
            interval (Union[Interval, str]): The irregular interval to set the time series to.
            in_place (bool, optional): Specifies whether to modify this time series (True) or a copy of it (False).
                Defaults to False.

        Raises:
            TimeSeriesException: If the specified interval is not a valid irregular interval for the
                context of the time series (e.g., a regular interval or a DSS-only irregular interval
                for a CWMS time series)

        Returns:
            TimeSeries: The modified time series
        """
        target = self if in_place else self.copy()
        intvl: Optional[Interval] = None
        if isinstance(interval, str):
            if self._context == DSS:
                if interval not in Interval.get_all_dss_names(
                    lambda i: i.is_any_irregular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval}' is not a valid DSS irregular interval"
                    )
                intvl = Interval.get_any_dss(lambda i: i.name == interval)
            elif self._context == CWMS:
                if interval not in Interval.get_all_cwms_names(
                    lambda i: i.is_any_irregular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval}' is not a valid CWMS irregular interval"
                    )
                intvl = Interval.get_any_cwms(lambda i: i.name == interval)
        elif isinstance(interval, Interval):
            if self._context == DSS:
                if interval.name not in Interval.get_all_dss_names(
                    lambda i: i.is_any_irregular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval.name}' is not a valid DSS irregular interval"
                    )
                intvl = interval
            elif self._context == CWMS:
                if interval.name not in Interval.get_all_cwms_names(
                    lambda i: i.is_any_irregular
                ):
                    raise TimeSeriesException(
                        f"Interval '{interval.name}' is not a valid CWMS irregular interval"
                    )
                intvl = interval
        else:
            raise TypeError(f"Expected Interval or str, got '{type(interval)}'")
        assert intvl is not None, f"Unable to retrieve Interval with name '{interval}'"
        target.set_interval(intvl)
        return target

    def trim(self, in_place: bool = False) -> "TimeSeries":
        """
        Trims a regular time series (either this one or a copy of this one), removing all missing values from the beginning and
        end of the time series unless they are either protected or marked as part of the current selection.

        Irregular time series (including pseudo-regular time series) are not affected.

        Does not alter any selection, even if selection state is `SelectionState.TRANSIENT`. Selected items remain
        selected after trim even though their location in the data may change.

        Args:
            in_place (bool, optional): Specifies whether to trim this time series (True) or a copy of this time series (False).
            Defaults to False.

        Returns:
            TimeSeries: The trimmed time series
        """
        # --------------------------------------- #
        # short circuit for irregular time series #
        # --------------------------------------- #
        if self.is_any_irregular:
            return self if in_place else self.copy()
        # ------------------------------ #
        # get the DataFrame to work with #
        # ------------------------------ #
        target = self if in_place else self.copy()
        df = cast(pd.DataFrame, target._data)  # does not recognize selection
        # --------------- #
        # set the results #
        # --------------- #
        if self.has_selection:
            condition = (
                ~df["value"].isna()
                | ((df["quality"] & (1 << 31)) != 0)
                | df["selected"]
            )
        else:
            condition = ~df["value"].isna() | (
                (df["quality"].astype("int64") & (1 << 31)) != 0
            )
        first_valid = condition.idxmax()  # First index where condition is True
        last_valid = condition[::-1].idxmax()  # Last index where condition is True
        target._data = df.loc[first_valid:last_valid]  # type: ignore
        return target

    @property
    def tsv(self) -> list[TimeSeriesValue]:
        """
        The times, values, and qualities as a list of TimeSeriesValue objects (empty if there is no data)

        Operations:
            Read Only
        """
        if self._data is None:
            return []
        if len(self._data.shape) == 1:
            return [
                TimeSeriesValue(
                    self._data.name,
                    UnitQuantity(self._data.value, self.unit),
                    self._data.quality,
                )
            ]

        def func(tsv: TimeSeriesValue) -> Any:
            return tsv

        return cast(
            list[TimeSeriesValue],
            (
                pd.DataFrame(self._data)
                .apply(
                    lambda row: func(self._tsv(row)),
                    axis=1,
                )
                .tolist()
            ),
        )

    @property
    def unit(self) -> str:
        """
        The parameter unit object

        Operations:
            Read Only
        """
        return self._parameter.unit_name

    @property
    def values(self) -> list[float]:
        """
        The values as a list of floats (empty if there is no data)

        Operations:
            Read Only
        """
        return [] if self._data is None else self._data["value"].tolist()

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
    def version_time(self) -> Optional[HecTime]:
        """
        The version date/time

        Operations:
            Read/Write
        """
        return self._version_time

    @version_time.setter
    def version_time(self, version_time: Union[HecTime, datetime, str]) -> None:
        self._version_time = HecTime(version_time)

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
