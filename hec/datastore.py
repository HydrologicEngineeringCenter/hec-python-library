"""
Provides classes for cataloging, storing, retrieving, and deleting data using various types of data stores.

Comprises the classes:
* [CwmsDataStore](#CwmsDataStore): Accesses CWMS databases via CDA
* [DssDataStore](#DssDataStore): Accesses HEC-DSS files
"""

import importlib.metadata
import math
import os
import re
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import tzlocal
from hecdss.record_type import RecordType  # type: ignore
from typing_extensions import Literal

from hec import location, parameter, timeseries, unit
from hec.const import CWMS, DSS, UNDEFINED
from hec.duration import Duration
from hec.hectime import HecTime, get_time_window
from hec.interval import Interval
from hec.location import Location
from hec.parameter import ElevParameter, Parameter, ParameterType
from hec.timeseries import TimeSeries
from hec.unit import UnitQuantity

__all__ = [
    "DataStoreException",
    "CwmsDataStore",
    "DssDataStore",
    "AbstractDataStore",
]

_required_cwms_version = ">= '0.6.0'"
_required_dss_version = "> '0.1.21'"

try:
    import cwms  # type: ignore

    cwms_version = importlib.metadata.version("cwms-python")
    cwms_imported = eval(f"'{cwms_version}' {_required_cwms_version}")
except ImportError:
    cwms_imported = False
try:
    from hecdss import HecDss  # type: ignore
    from hecdss import DssPath, IrregularTimeSeries, RegularTimeSeries

    dss_version = importlib.metadata.version("hecdss")
    dss_imported = eval(f"'{dss_version}' {_required_dss_version}")
except ImportError:
    dss_imported = False

A, B, D, D, E, F = 1, 2, 3, 4, 5, 6

warnings.filterwarnings("always", category=UserWarning)


def _pattern_to_regex(pattern: Optional[str]) -> Optional[str]:
    """
    Build regex from extended glob pattern

    Args:
        pattern (Optional[str]): the extended glob pattern
            * ^: beginning of string anchor (added if not specified)
            * $: end of string anchor (added if not specified)
            * ?: any single character (use ?{0,1} for zero or one character)
            * [abc]: character class, matches any character in class (can include ranges like [_a-z0-9])
            * [!abc]: negated character class, matches any character NOT in class (can include ranges like [!_a-z0-9])
            * {n}: number of occurrences of previous character or class (e.g., [abc]{3}) (can specifiy closed or open ranges {m,n}, {m,}, {,n})
            * (|): alteration (e.g. ([abc]|g|z))
    Returns:
        str: The generated regex
    """
    if pattern is None:
        return None
    chars = ["^"]
    for c in pattern:
        if c == "*":
            if chars[-1] in ")]":
                chars.append("*")
            else:
                chars.extend(".*")
        elif c == "?":
            chars.append(".")
        elif c == "^":
            if chars == ["^"]:
                pass
            else:
                chars.extend(["\\", c])
        elif c == "!":
            chars.append("^" if chars[-1] == "[" else "\\!")
        elif c in ".+@%$=<>&\\":
            chars.extend(["\\", c])
        else:
            chars.append(c)
    if chars[-2:] == ["\\", "$"]:
        chars = chars[:-2] + ["$"]
    else:
        chars.append("$")
    return "".join(chars)


class _CwmsDataType(Enum):
    LOCATION = 1
    TIMESERIES = 2


class _DssDataType(Enum):
    ARRAY = 1
    GRID = 2
    LOCATION = 3
    PAIRED_DATA = 4
    TEXT = 5
    TIMESERIES = 6
    TIMESERIES_PROFILE = 7
    TIN = 8


class StoreRule(Enum):
    DELETE_INSERT = 1
    DO_NOT_REPLACE = 2
    REPLACE_ALL = 3
    REPLACE_MISSING_VALUES_ONLY = 4
    REPLACE_WITH_NON_MISSING = 5


class DeleteAction(Enum):
    DELETE_ALL = 1
    DELETE_DATA = 2
    DELETE_KEY = 3


_valid_catalog_fields = {
    CWMS: {
        _CwmsDataType.LOCATION.name: [
            "identifier",
            "office",
            "name",
            "nearest-city",
            "public-name",
            "long-name",
            "kind",
            "time-zone",
            "latitude",
            "longitude",
            "published-latitude",
            "published-longitude",
            "horizontal-datum",
            "elevation",
            "unit",
            "vertical-datum",
            "nation",
            "state",
            "county",
            "bounding-office",
            "map-label",
            "active",
            "aliases",
            "description",
            "type",
        ],
        _CwmsDataType.TIMESERIES.name: [
            "identifier",
            "office",
            "name",
            "time-zone",
            "interval",
            "offset",
            "earliest-time",
            "latest-time",
            "last-update",
        ],
    },
    DSS: {
        _DssDataType.TIMESERIES.name: [
            "identifier",
            "name",
            "earliest-time",
            "latest-time",
        ],
    },
}


class DataStoreException(Exception):
    """
    Base class for all data store exceptions
    """

    pass


class AbstractDataStore(ABC):
    """
    Abstract base class for data store classes
    """

    def __init__(self) -> None:
        self._description: Optional[str] = None
        self._init_data: Dict[str, Any]
        self._is_open: bool = False
        self._name: str
        self._office: Optional[str] = None
        self._read_only: bool = True
        self._store_rule: StoreRule = StoreRule.REPLACE_ALL
        self._time_window: Tuple[Optional[HecTime], Optional[HecTime]] = (None, None)
        self._time_zone: str = tzlocal.get_localzone_name()
        self._trim: bool = True
        self._unit_system: str = "EN"
        self._vertical_datum: Optional[str] = None

    def __enter__(self) -> "AbstractDataStore":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> Literal[False]:
        self.close()
        return False

    def _init(self, **kwargs: Any) -> None:
        if kwargs:
            argval: Any
            self._init_data = kwargs.copy()
            # ---------------------- #
            # description (optional) #
            # ---------------------- #
            if "description" in kwargs:
                argval = kwargs["description"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'description', got {argval.__class__.__name__}"
                    )
                self._description = argval
            # ------------------- #
            # end_time (optional) #
            # ------------------- #
            if "end_time" in kwargs:
                self._time_window = (self._time_window[0], HecTime(kwargs["end_time"]))
            # ---------------------------------------------------- #
            # name (required)  - requirement deferred to sub-class #
            # ---------------------------------------------------- #
            if "name" in kwargs:
                argval = kwargs["name"]
                if not isinstance(argval, (type(None), str)):
                    raise TypeError(
                        f"Expected str for 'name', got {argval.__class__.__name__}"
                    )
                self._name = cast(str, argval)
            # ----------------- #
            # office (optional) #
            # ----------------- #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                self._office = argval
            # -------------------- #
            # read_only (optional) #
            # -------------------- #
            if "read_only" in kwargs:
                argval = kwargs["read_only"]
                if isinstance(argval, bool):
                    self._read_only = argval
                else:
                    raise TypeError(
                        f"Expected bool or str for 'read_only', got {argval.__class__.__name__}"
                    )
            # --------------------- #
            # start_time (optional) #
            # --------------------- #
            if "start_time" in kwargs:
                self._time_window = (
                    HecTime(kwargs["start_time"]),
                    self._time_window[1],
                )
            # --------------------- #
            # store rule (optional) #
            # --------------------- #
            if "store_rule" in kwargs:
                argval = kwargs["store_rule"]
                if isinstance(argval, StoreRule):
                    self._store_rule = argval
                elif isinstance(argval, str):
                    if argval.upper() in list(StoreRule.__members__):
                        self._store_rule = StoreRule[argval.upper()]
                    else:
                        raise ValueError(
                            f"Invalid store rule {argval}, must be one of {list(StoreRule.__members__)}"
                        )
                else:
                    raise TypeError(
                        f"Expected StoreRule or str for store_rule, got {argval.__class__.__name__}"
                    )
            # -------------------- #
            # time_zone (optional) #
            # -------------------- #
            if "time_zone" in kwargs:
                time_zone = kwargs["time_zone"]
                if not isinstance(time_zone, (ZoneInfo, timezone, str)):
                    raise TypeError(
                        f"Expected HecTime, datetime, ZoneInfo, timezone, or str, got {time_zone.__class__.__name__}"
                    )
                try:
                    t = HecTime.now().convert_to_time_zone(time_zone, on_tz_not_set=0)
                except:
                    raise DataStoreException(f"Invalid time zone: {time_zone}")
                self._time_zone = str(time_zone)
            # --------------- #
            # trim (optional) #
            # --------------- #
            if "trim" in kwargs:
                argval = kwargs["trim"]
                if isinstance(argval, bool):
                    self._trim = argval
                else:
                    raise TypeError(
                        f"Expected bool or str for 'trim', got {argval.__class__.__name__}"
                    )
            # ---------------- #
            # units (optional) #
            # ---------------- #
            if "units" in kwargs:
                argval = kwargs["units"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'units', got {argval.__class__.__name__}"
                    )
                if argval.lower().startswith("en"):
                    self._unit_system = "EN"
                elif argval.lower() in ("si", "metric"):
                    self._unit_system = "SI"
                else:
                    raise ValueError(
                        f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{argval}'"
                    )
            # ------------------------- #
            # vertical_datum (optional) #
            # ------------------------- #
            if "vertical_datum" in kwargs:
                argval = kwargs["vertical_datum"]
                if argval is None:
                    self._vertical_datum = None
                else:
                    if not isinstance(argval, str):
                        raise TypeError(
                            f"Expected str for 'vertical_datum', got {argval.__class__.__name__}"
                        )
                    if not parameter._all_datums_pattern.match(argval):
                        raise ValueError(
                            f"Invalid vertical datum: {argval}. Must be one of {parameter._NGVD29}, {parameter._NAVD88} or {parameter._OTHER_DATUM}"
                        )
                    if parameter._ngvd29_pattern.match(argval):
                        self._vertical_datum = parameter._NGVD29
                    elif parameter._navd88_pattern.match(argval):
                        self._vertical_datum = parameter._NAVD88
                    else:
                        self._vertical_datum = None

    def __del__(self) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='"
            + self._name
            + (f"', description='{self._description}')" if self._description else "')")
        )

    def __str__(self) -> str:
        return self._name + (f" ({self._description})" if self._description else "")

    def _assert_open(self) -> None:
        if not self._is_open:
            raise DataStoreException(
                f"{type(self).__name__}({self.name}) is not open for access"
            )

    @abstractmethod
    def catalog(
        self,
        data_type: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Explicitly closes the data store, preventing further access.

        The data store is implicitly closed upon deletion or exiting a context manager ('with' block)
        """
        pass

    @abstractmethod
    def delete(self, identifier: str, **kwargs: Any) -> None:
        pass

    @property
    def end_time(self) -> Optional[HecTime]:
        """
        The end time of the data store's time window (if any)

        Operations:
            Read/Write
        """
        return self._time_window[1]

    @end_time.setter
    def end_time(self, _end_time: Optional[Any]) -> None:
        self._time_window = (
            self._time_window[0],
            (
                _end_time
                if _end_time is None
                else HecTime(_end_time).label_as_time_zone(self._time_zone)
            ),
        )

    @abstractmethod
    def get_extents(self, identifier: str, **kwargs: Any) -> List[HecTime]:
        pass

    @property
    def native_data_store(self) -> Any:
        pass

    @property
    def name(self) -> str:
        """
        The name of the data store as provided in the constructor or `open()` method

        Operations:
            Read Only
        """
        return self._name

    @property
    def office(self) -> Optional[str]:
        """
        The office associated with the data store, if any

        Operations:
            Read/Write
        """
        return self._office

    @office.setter
    def office(self, _office: str) -> None:
        self._office = _office

    @staticmethod
    @abstractmethod
    def open(name: Optional[str] = None, **kwargs: Any) -> "AbstractDataStore":
        pass

    @property
    def is_open(self) -> bool:
        """
        Whether this data store is open for cataloging and reading.

        A data store is open from its construction or call to `open()` until a call to `close()` or deletiion

        Operations:
            Read Only
        """
        return self._is_open

    @property
    def is_read_only(self) -> bool:
        """
        Whether this data store is open for storing and deleting. Meaningless if `is_open` is False

        Operations:
            Read/Write
        """
        return self._read_only

    @is_read_only.setter
    def is_read_only(self, _read_only: bool) -> None:
        self._read_only = bool(_read_only)

    @abstractmethod
    def retrieve(self, identifier: str, **kwargs: Any) -> Any:
        pass

    @property
    def start_time(self) -> Optional[HecTime]:
        """
        The start time of the data store's time window (if any)

        Operations:
            Read/Write
        """
        return self._time_window[0]

    @start_time.setter
    def start_time(self, _start_time: Optional[Any]) -> None:
        self._time_window = (
            (
                _start_time
                if _start_time is None
                else HecTime(_start_time).label_as_time_zone(self._time_zone)
            ),
            self._time_window[1],
        )

    @abstractmethod
    def store(self, obj: object, **kwargs: Any) -> None:
        pass

    @property
    def time_window(self) -> Tuple[Optional[HecTime], Optional[HecTime]]:
        """
        The data store's time window (if any)
        * **Getting**: same as (ds.start_time, ds.end_time)
        * **Setting**: same as ds.start_time, ds.end_time = tw

        Operations:
            Read/Write
        """
        return self._time_window

    @time_window.setter
    def time_window(
        self, _time_window: Union[str, Tuple[Optional[HecTime], Optional[HecTime]]]
    ) -> None:
        if isinstance(_time_window, str):
            start_time = HecTime()
            end_time = HecTime()
            if 0 == get_time_window(_time_window, start_time, end_time):
                self._time_window = (start_time, end_time)
            else:
                raise DataStoreException(
                    f"Invalid time window string: '{_time_window}'"
                )
        elif isinstance(_time_window, tuple):
            self._time_window = (
                (
                    _time_window[0]
                    if _time_window[0] is None
                    else HecTime(_time_window[0])
                ),
                (
                    _time_window[1]
                    if _time_window[1] is None
                    else HecTime(_time_window[1])
                ),
            )
            for i in (0, 1):
                t = cast(HecTime, self._time_window[i])
                if t:
                    if t.tzinfo is None:
                        t.label_as_time_zone(self._time_zone)
                    elif str(t.tzinfo) != self._time_zone:
                        t.convert_to_time_zone(self._time_zone)

    @property
    def time_zone(self) -> str:
        """
        The time zone associated with the data store

        Operations:
            Read/Write
        """
        return self._time_zone

    @time_zone.setter
    def time_zone(self, _time_zone: str) -> None:
        try:
            HecTime.now().convert_to_time_zone(_time_zone, on_tz_not_set=0)
        except:
            raise DataStoreException(f"Invalid time zone: {_time_zone}")
        self._time_zone = _time_zone
        self._time_window = (
            (
                self._time_window[0]
                if self._time_window[0] is None
                else HecTime(self._time_window[0]).label_as_time_zone(
                    self._time_zone, on_already_set=0
                )
            ),
            (
                self._time_window[1]
                if self._time_window[1] is None
                else HecTime(self._time_window[1]).label_as_time_zone(
                    self._time_zone, on_already_set=0
                )
            ),
        )

    @property
    def trim(self) -> bool:
        """
        Whether the datastore will trim missing values from the edges of retrieved regular time series

        Operations:
            Read/Write
        """
        return self._trim

    @trim.setter
    def trim(self, _trim: bool) -> None:
        self._trim = bool(_trim)

    @property
    def units(self) -> str:
        """
        The unit system ('EN' or 'SI') associated with the data store

        Operations:
            Read/Write
        """
        return self._unit_system

    @units.setter
    def units(self, _units: str) -> None:
        if _units.lower().startswith("en"):
            self._unit_system = "EN"
        elif _units.lower() in ("si", "metric"):
            self._unit_system = "SI"
        else:
            raise ValueError(
                f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{_units}'"
            )

    @property
    def vertical_datum(self) -> Optional[str]:
        """
        The vertical datum ('NGVD29', 'NAVD88', 'OTHER') associated with the data store

        Returns:
            Optional[str]: _description_
        """
        return self._vertical_datum

    @vertical_datum.setter
    def vertical_datum(self, _vertical_datum: str) -> None:
        if not parameter._all_datums_pattern.match(_vertical_datum):
            raise ValueError(
                f"Invalid vertical datum: {_vertical_datum}. Must be one of {parameter._NGVD29}, {parameter._NAVD88} or {parameter._OTHER_DATUM}"
            )
        if parameter._ngvd29_pattern.match(_vertical_datum):
            self._vertical_datum = parameter._NGVD29
        elif parameter._navd88_pattern.match(_vertical_datum):
            self._vertical_datum = parameter._NAVD88
        else:
            self._vertical_datum = parameter._OTHER_DATUM


class DssDataStore(AbstractDataStore):
    # Docstring is in __init__.py to allow pdoc to use dynamic docstring
    _DEFAULT_MESSAGE_LEVEL: int = 4

    def __init__(self, **kwargs: Any):
        """
        Creates and returns a new DssDataStore object.

        Equivalent of calling [`DssDataStore.open(name, **kwargs)`](#DssDataStore.open)

        Args:
            description (Optional[str], must be passed by name): The description assocaited with the data store. Defaults to None
            end_time (Optional[Any], must be passed by name): Specifies the end time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            name (str, must be passed by name): The name of the HEC-DSS file to open.
            read_only (Optional[bool], must be passed by name): Specifies whether to open the data store in read-only mode. Defaults to True
            start_time (Optional[Any], must be passed by name): Specifies the start time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            store_rule (Optional[str], must be passed by name): Must be one of the following (case insensitive). Defaults to 'REPLACE_ALL'.
                * 'DELETE_INSERT'
                * 'DO_NOT_REPLACE'
                * 'REPLACE_ALL'
                * 'REPLACE_MISSING_VALUES_ONLY'
                * 'REPLACE_WITH_NON_MISSING'
            trim (Optional[bool], must be passed by name): Specifies the data store's default setting to trim missing values from the beginning and end of any regular time series data set retrieved.
                Defaults to True.
        """
        super().__init__()
        if not dss_imported:
            raise DataStoreException(
                f"Cannot create a DssDataStore object: please install the hec-dss-python module or upgrade to {_required_dss_version}"
            )
        if "name" not in kwargs:
            raise DataStoreException("No name specified for data store.")
        self._init(**kwargs)
        self._name = os.path.abspath(self._name)
        try:
            self._hecdss = HecDss(self._name)
        except:
            raise
        self._is_open = True

    def catalog(
        self,
        data_type: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Retrieves pathnames that match specified conditions

        Args:
            data_type (Optional[str]): The type of data to retrieve pathnames for. Defaults to None, which specifies all data types.
                If specified, must be one of (case insensitive):
                * 'ARRAY'
                * 'GRID'
                * 'LOCATION'
                * 'PAIRED_DATA'
                * 'TEXT'
                * 'TIMESERIES'
                * 'TIMESERIES_PROFILE'
                * 'TIN'
            pattern (Optional[str], must be passed by name): Wildcard pattern (using `*` and `?`) to use for matching pathnames. `regex` takes precedence if both are specified. Defaults to None.
            regex (Optional[str], must be passed by name): Regular expression to use for matching pathnames. Takes precedence over `pattern` if both are specified. Defaults to None.
            case_sensitive (Optional[bool], must be passed by name): Specifies whether `pattern` or `regex` matching is case-sensitive.
            condensed (Optional[bool], must be passed by name): Specifies whether to return a condensed catalog (D-part = time range for time series). Defaults to True

        Raises:
            DataStoreException: if the data store is not open or an invalid `data_type` is specified

        Returns:
            List[str]: The pathnames that match the specified parameters
        """
        self._assert_open()
        case_sensitive: Optional[bool] = False
        condensed: Optional[bool] = True
        _regex: Optional[str] = None
        if kwargs:
            # ------- #
            # pattern #
            # ------- #
            if "pattern" in kwargs:
                argval = kwargs["pattern"]
                if isinstance(argval, str):
                    _regex = _pattern_to_regex(argval)
                else:
                    raise TypeError(
                        f"Expected str for 'pattern', got {argval.__class__.__name__}"
                    )
            # ------------------------------------- #
            # regex (takes precedence over pattern) #
            # ------------------------------------- #
            if "regex" in kwargs:
                argval = kwargs["regex"]
                if isinstance(argval, str):
                    _regex = argval
                else:
                    raise TypeError(
                        f"Expected str for 'regex', got {argval.__class__.__name__}"
                    )
            # -------------- #
            # case_sensitive #
            # -------------- #
            if "case_sensitive" in kwargs:
                argval = kwargs["case_sensitive"]
                if isinstance(argval, bool):
                    case_sensitive = argval
                else:
                    raise TypeError(
                        f"Expected str or bool for 'case_sensitive', got {argval.__class__.__name__}"
                    )
            # --------- #
            # condensed #
            # --------- #
            if "condensed" in kwargs:
                argval = kwargs["condensed"]
                if isinstance(argval, bool):
                    condensed = argval
                else:
                    raise TypeError(
                        f"Expected str or bool for 'condensed', got {argval.__class__.__name__}"
                    )
        _data_type: Optional[_DssDataType] = None
        if data_type:
            if data_type.upper() not in _DssDataType.__members__:
                raise DataStoreException(
                    f"Invalid data type: '{data_type}', must be one of {list(_DssDataType.__members__)}"
                )
            _data_type = _DssDataType[data_type.upper()]
        if condensed:
            pathnames = list(map(str, self._hecdss.get_catalog()))
        else:
            pathnames = self._hecdss._native.hec_dss_catalog()[0]
        if _regex:
            pat = re.compile(_regex, 0 if case_sensitive else re.I)
            pathnames = [p for p in pathnames if pat.match(p)]
        func = None
        if _data_type == _DssDataType.TIMESERIES:
            func = lambda p: self._hecdss.get_record_type(p) in (
                RecordType.RegularTimeSeries,
                RecordType.IrregularTimeSeries,
            )
        elif _data_type == _DssDataType.PAIRED_DATA:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.PairedData
        elif _data_type == _DssDataType.GRID:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.Grid
        elif _data_type == _DssDataType.TEXT:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.Text
        elif _data_type == _DssDataType.ARRAY:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.Array
        elif _data_type == _DssDataType.TIN:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.Tin
        elif _data_type == _DssDataType.LOCATION:
            func = lambda p: self._hecdss.get_record_type(p) == RecordType.LocationInfo
        if func:
            pathnames = list(filter(func, pathnames))
        return pathnames

    def close(self) -> None:
        self._hecdss.close()
        self._is_open = False

    def delete(self, identifier: str, **kwargs: Any) -> None:
        """
        Deletes a data set from the data store.

        Currently only time series data may be deleted. To delete all data for a time series, specifiy `start_time=None` and `end_time=None`

        Args:
            identifier (str): The name of the data set to delete:
                * **TIMESERIES**: A pathname in the dataset. The D part (block start date) is ignored.
            end_time (Optional[Any], must be passed by name): Specifies the end of the time window to delete data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the end of the data store's time window. If None or not specified and the data store's time window doesn't have an end time, all data on or after the start time will be deleted.
            start_time (Optional[Any], must be passed by name): Specifies the start of the time window to delete data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the start of the data store's time window. If None or not specified and the data store's time window doesn't have a start time, all data up to and on the end time will be deleted.
        """
        self._assert_open()
        if TimeSeries.is_dss_ts_pathname(identifier):
            # ------------------------------------------------------------- #
            # the underlying library doesn't allow for deleting records, so #
            # as a proxy we simply set the values to missing and store over #
            # the existing records                                          #
            # ------------------------------------------------------------- #
            time_window = self._time_window
            # ------------------------------------------------------- #
            # override default time window with specified time window #
            # ------------------------------------------------------- #
            if kwargs:
                # -------- #
                # end_time #
                # -------- #
                if "end_time" in kwargs:
                    time_window = (
                        time_window[0],
                        (
                            None
                            if kwargs["end_time"] is None
                            else HecTime(kwargs["end_time"])
                        ),
                    )
                # ---------- #
                # start_time #
                # ---------- #
                if "start_time" in kwargs:
                    time_window = (
                        (
                            None
                            if kwargs["start_time"] is None
                            else HecTime(kwargs["start_time"])
                        ),
                        time_window[1],
                    )
            parts = identifier.split("/")
            parts[D] = "*"
            interval = Interval.get_any_dss(
                lambda i: i.name.upper() == parts[E].upper()
            )
            assert interval is not None, f"Creating Interval from {parts[E]}"
            dss_block_size = Interval.get_dss_block_for_interval(interval)
            assert dss_block_size is not None, f"Getting HEC-DSS block for {interval}"
            pathnames = self.catalog(
                "timeseries", pattern="/".join(parts), condensed=False
            )
            start_time: HecTime
            end_time: HecTime
            for pathname in pathnames:
                block_start = HecTime(pathname.split("/")[D])
                end_time = block_start + dss_block_size
                if interval.is_regular:
                    start_time = block_start + interval
                else:
                    start_time = block_start + 1
                if time_window[0] and end_time < time_window[0]:
                    continue
                elif time_window[1] and start_time > time_window[1]:
                    break
                ts = cast(
                    TimeSeries,
                    self.retrieve(
                        identifier=identifier, start_time=start_time, end_time=end_time
                    ),
                )
                if time_window[0] and time_window[0] > start_time:
                    start_time = time_window[0]
                if time_window[1] and time_window[1] < end_time:
                    end_time = time_window[1]
                df: Optional[pd.DataFrame] = ts.data
                if df is None or df.empty:
                    continue
                start = max(start_time.datetime(), df.index.min())
                end = min(end_time.datetime(), df.index.max())
                df.loc[
                    (df.index >= start) & (df.index <= end),
                    "value",
                ] = math.nan
                df.loc[
                    (df.index >= start) & (df.index <= end),
                    "quality",
                ] = 5
                if interval.is_irregular:
                    df = df[(df.index <= start) | (df.index >= end)]
                ts._data = df
                self.store(ts)
        else:
            raise ValueError(f"Don't know record type of '{identifier}'")

    def get_extents(self, identifier: str, **kwargs: Any) -> List[HecTime]:
        """
        Retrieves the data extents for the specified identifier

        Args:
            identifier (str): The identifier to retrieve the extents for

        Returns:
            List[HecTime]: The earliest time and latest time for the identifier
        """
        if TimeSeries.is_dss_ts_pathname(identifier):
            datetimes = self._hecdss._get_date_time_range(identifier, True)
            times = list(map(HecTime, datetimes))
            return times
        else:
            raise ValueError(
                "The get_extents() method is available only for time series data"
            )

    @property
    def is_open(self) -> bool:
        return not self._hecdss._closed if self._hecdss else False

    @property
    def native_data_store(self) -> Any:
        """
        The underlying HecDss object from the imported library used by this data store

        Operations:
            Read-Only
        """
        return self._hecdss

    @staticmethod
    def open(name: Optional[str] = None, **kwargs: Any) -> "DssDataStore":
        """
        Creates and returns a new DssDataStore object.

        Equivalent of calling [`DssDataStore(**kwargs)`](#DssDataStore) with `name` in `kwargs`

        Args:
            name (str): The name of the HEC-DSS file to open.
            description (Optional[str], must be passed by name): The description assocaited with the data store. Defaults to None
            end_time (Optional[Any], must be passed by name): Specifies the end time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            read_only (Optional[bool], must be passed by name): Specifies whether to open the data store in read-only mode. Defaults to True
            start_time (Optional[Any], must be passed by name): Specifies the start time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            store_rule (Optional[str], must be passed by name): Must be one of the following (case insensitive). Defaults to 'REPLACE_ALL'.
                * 'DELETE_INSERT'
                * 'DO_NOT_REPLACE'
                * 'REPLACE_ALL'
                * 'REPLACE_MISSING_VALUES_ONLY'
                * 'REPLACE_WITH_NON_MISSING'
            trim (Optional[bool], must be passed by name): Specifies the data store's default setting to trim missing values from the beginning and end of any regular time series data set retrieved.
                Defaults to True.
        """
        kwargs2 = kwargs.copy()
        kwargs2["name"] = name
        ds = DssDataStore(**kwargs2)
        return ds

    def retrieve(self, identifier: str, **kwargs: Any) -> Any:
        """
        Retrieves a data set from the data store.

        Currently only time series data may be retrieved. To retrieve all data for a time series, specifiy `start_time=None` and `end_time=None`

        Args:
            identifier (str): The name of the data set to retrieve:
                * **TIMESERIES**: A pathname in the dataset. The D part (block start date) is ignored.
            end_time (Optional[Any], must be passed by name): Specifies the end of the time window to retrieve data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the end of the data store's time window. If None or not specified and the data store's time window doesn't have an end time, all data on or after the start time will be retrieved.
            start_time (Optional[Any], must be passed by name): Specifies the start of the time window to retrieve data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the start of the data store's time window. If None or not specified and the data store's time window doesn't have a start time, all data up to and on the end time will be retrieved.
            trim (Optional[bool], must be passed by name): Specifies whether to trim missing values from the beginning and end of any regular time series data set retrieved.
                Defaults to the data store's trim setting.
        """
        self._assert_open()
        trim = self._trim
        time_window = self._time_window
        if kwargs:
            # -------- #
            # end_time #
            # -------- #
            if "end_time" in kwargs:
                time_window = (
                    time_window[0],
                    None if kwargs["end_time"] is None else HecTime(kwargs["end_time"]),
                )
            # ---------- #
            # start_time #
            # ---------- #
            if "start_time" in kwargs:
                time_window = (
                    (
                        None
                        if kwargs["start_time"] is None
                        else HecTime(kwargs["start_time"])
                    ),
                    time_window[1],
                )
            # ---- #
            # trim #
            # ---- #
            if "trim" in kwargs:
                argval = kwargs["trim"]
                if isinstance(argval, bool):
                    trim = argval
                else:
                    raise TypeError(
                        f"Expected bool or str for trim parameter, got {type(argval).__name__}"
                    )
        obj = self._hecdss.get(
            pathname=identifier,
            startdatetime=(
                time_window[0] if time_window[0] is None else time_window[0].datetime()
            ),
            enddatetime=(
                time_window[1] if time_window[1] is None else time_window[1].datetime()
            ),
            trim=trim,
        )
        if isinstance(obj, (RegularTimeSeries, IrregularTimeSeries)):
            mask = np.isclose(obj.values, UNDEFINED)
            if obj.quality:
                obj.quality[mask] = 5
            obj.values[mask] = np.nan
            ts = TimeSeries(obj.id)
            ts.iset_parameter_type(obj.data_type)
            ts.iset_unit(obj.units)
            df = pd.DataFrame(
                {
                    "value": list(obj.values),
                    "quality": obj.quality if obj.quality else len(obj.times) * [0],
                },
                index=pd.Index(obj.times, name="time"),
            )
            df.loc[df["value"].isna(), "quality"] = 5
            if isinstance(obj, IrregularTimeSeries):
                df = df[(~df["value"].isna())]
            ts._data = df
            return ts
        else:
            raise TypeError(f"Retrieving {type(obj).__name__} objects is not supported")

    @staticmethod
    def set_message_level(level: int = _DEFAULT_MESSAGE_LEVEL) -> None:
        """
        Sets the HEC-DSS message level for all `DssDataStore` objects

        Args:
            level (int, optional): Defaults to 4
                * **0**: No output
                * **1**: Critcal output only
                * **2**: Terse (includes file open and close)
                * **4**: General (includes read and write)
                * **5**: User Diagnostic
                * **11**: Internal Diagnostic
                * **13**: Internal Debug
        """
        HecDss.set_global_debug_level(level)

    def store(self, obj: object, **kwargs: Any) -> None:
        """
        Stores a data set to the data store.

        Currently only time series data may be stored.

        Args:
            obj (object): The data set to store
        """
        self._assert_open()
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        elif isinstance(obj, TimeSeries):
            if obj.data is None or obj.data.empty:
                raise DataStoreException(f"Cannot store empty time series {obj.name}")
            if obj.parameter_type is None:
                raise DataStoreException(
                    f"Cannot store time series {obj.name} with unknown parameter type"
                )
            if obj.context == "CWMS":
                obj = obj.clone()
                obj.context = "DSS"
            if obj.interval.is_regular:
                ts = RegularTimeSeries()
            else:
                ts = IrregularTimeSeries()
            ts.id = obj.name
            data = cast(pd.DataFrame, obj.data)
            ts.times = pd.to_datetime(data.index).tz_localize(None).tolist()
            ts.values = data["value"].fillna(UNDEFINED).tolist()
            ts.quality = data["quality"].tolist()
            ts.units = obj.unit
            ts.data_type = cast(ParameterType, obj.parameter_type).get_dss_name()
            ts.interval = obj.interval.minutes * 60
            ts.start_date = obj.times[0]
            ts.julian_base_date = HecTime(obj.times[0]).julian()
            self._hecdss.put(ts)
        else:
            raise TypeError(f"Storing {type(obj).__name__} objects is not supported")


class CwmsDataStore(AbstractDataStore):
    # Docstring is in __init__.py to allow pdoc to use dynamic docstring

    _api_root: Optional[str] = None
    _api_key: Optional[str] = None

    def __init__(self, **kwargs: Any):
        """
        Creates and returns a new CwmsDataStore object.

        Equivalent of calling [`CwmsDataStore.open(name, **kwargs)`](#CwmsDataStore.open)

        Args:
            api_key (Optional[str], must be passed by name): The API key for this data store. Must be specified to write to or delete from this data store. Defaults to None. If None:
                * The value of environment variable "cda_api_key" is used, if it exists.
            description (Optional[str], must be passed by name): The description assocaited with the data store. Defaults to None
            end_time (Optional[Any], must be passed by name): Specifies the end time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            name (Optional[str], must be passed by name): The API root (base URL). Defaults to None. If None:
                * The value of environment variable "cda_api_root" is used, if it exists.
                * If the environment variable "cda_api_root" is not set, the default, the default value used in `cwms.api.init_session(api_root=None)` is used.
            office (Optional[str], must be passed by name): The default CWMS office for the data store. If None or not specified, each access method will have to have an office specified.
            read_only (Optional[bool], must be passed by name): Specifies whether to open the data store in read-only mode. Defaults to True
            start_time (Optional[Any], must be passed by name): Specifies the start time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            store_rule (Optional[str], must be passed by name): Specifies the default behavior to use when storing data. If specified, it must be one of the following (case insensitive). Defaults to 'REPLACE_ALL'.
                * 'DELETE_INSERT' - delete all existing data in the incoming time window, then store the incoming data
                * 'DO_NOT_REPLACE' - store only non-existing data
                * 'REPLACE_ALL' - store existing and non-existing data
                * 'REPLACE_MISSING_VALUES_ONLY' - store incoming data only where existing data is missing
                * 'REPLACE_WITH_NON_MISSING' - store only non-missing incoming data
            time_zone (Optional[str], must be passed by name): The default time zone for the data store. Defaults to the local time zone.
            trim (Optional[bool], must be passed by name): Specifies the data store's default setting to trim missing values from the beginning and end of any regular time series data set retrieved.
                Defaults to True.
            units: (Optional[str], must be passed by name): "EN" or "SI", specifying English or metric unit system as the default unit system for the data store. Defaults to "EN"
            vertical_datum: (Optional[str], must be passed by name): "NGVD29", "NAVD88", or "NATIVE", specifying the data store's default vertical datum for retrieving elevation data. Defaults to "NATIVE"
        """
        super().__init__()
        self._init(**kwargs)
        if not cwms_imported:
            raise DataStoreException(
                f"Cannot create a CwmsDataStore object: please install the cwms-python module or upgrade to {_required_cwms_version}"
            )
        if kwargs:
            argval: Any
            # ------------------ #
            # api_key (optional) #
            # ------------------ #
            if "api_key" in kwargs:
                argval = kwargs["api_key"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'api_key', got {argval.__class__.__name__}"
                    )
                self._api_key = f"apikey {argval}"
        self._api_root = self._name
        if not self._api_root:
            envval = os.getenv("cda_api_root")
            if envval:
                self._api_root = envval
        if not self._api_key:
            envval = os.getenv("cda_api_key")
            if envval:
                self._api_key = f"apikey {envval}"
        if self._api_root and not self._api_root.endswith("/"):
            self._api_root += "/"
        cwms.api.init_session(api_root=self._api_root, api_key=self._api_key)
        self._name = cwms.api.return_base_url()
        if not self._office:
            self._office = os.getenv("cda_api_office")
        self._cwms = cwms
        self._is_open = True

    def _delete_location(self, identifier: str, **kwargs: Any) -> None:
        office: Optional[str] = self._office
        cascade: bool = False
        self._assert_open()
        if kwargs:
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ------------- #
            # delete_action #
            # ------------- #
            if "delete_action" in kwargs:
                argval = kwargs["delete_action"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'delete_action', got {argval.__class__.__name__}"
                    )
                if argval.upper() not in DeleteAction.__members__:
                    raise ValueError(
                        f"Invalid delete action: {argval}, must be {DeleteAction.DELETE_KEY.name} or {DeleteAction.DELETE_ALL.name}"
                    )
                action = DeleteAction[argval.upper()]
                if action == DeleteAction.DELETE_DATA:
                    raise ValueError(
                        f"Invalid delete action: {argval}, must be {DeleteAction.DELETE_KEY.name} or {DeleteAction.DELETE_ALL.name}"
                    )
                cascade = action == DeleteAction.DELETE_ALL
        if not office:
            raise DataStoreException(
                f"No office specified and CwmsDataStore {self} has no default office"
            )
        cwms.delete_location(
            location_id=identifier, office_id=office, cascade_delete=cascade
        )

    def _delete_time_series(self, identifier: str, **kwargs: Any) -> None:
        office: Optional[str] = self._office
        time_window: Tuple[Optional[HecTime], Optional[HecTime]] = (None, None)
        version_time: Optional[HecTime] = None
        delete_action: Optional[DeleteAction] = None
        self._assert_open()
        if kwargs:
            # ------------- #
            # delete_action #
            # ------------- #
            if "delete_action" in kwargs:
                argval = kwargs["delete_action"]
                if isinstance(argval, DeleteAction):
                    delete_action = argval
                elif isinstance(argval, str):
                    if argval.upper() in list(DeleteAction.__members__):
                        delete_action = DeleteAction[argval.upper()]
                    else:
                        raise ValueError(
                            f"Invalid delete action {argval}, must be one of {list(DeleteAction.__members__)}"
                        )
                else:
                    raise TypeError(
                        f"Expected DeleteAction or str for delete_action, got {argval.__class__.__name__}"
                    )
            # -------- #
            # end_time #
            # -------- #
            if "end_time" in kwargs:
                time_window = (
                    time_window[0],
                    HecTime(kwargs["end_time"]),
                )
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ---------- #
            # start_time #
            # ---------- #
            if "start_time" in kwargs:
                time_window = (
                    HecTime(kwargs["start_time"]),
                    time_window[1],
                )
            # ------------ #
            # version_time #
            # ------------ #
            if "version_time" in kwargs:
                version_time = HecTime(kwargs["version_time"])
        if not office:
            raise DataStoreException(
                f"No office specified and CwmsDataStore {self} has no default office"
            )
        if delete_action:
            # -------------------------------------------- #
            # ignore time window and use the delete action #
            # -------------------------------------------- #
            cwms.delete_timeseries_identifier(
                ts_id=identifier, office_id=office, delete_method=delete_action.name
            )
        else:
            # ---------------------------------------- #
            # use the time window and delete some data #
            # ---------------------------------------- #
            if not (time_window[0] and time_window[1]):
                raise DataStoreException(
                    f"Start_time and/or end_time is not specifed and CwmsDataStore {self} doens't have a complete default time window"
                )
            if time_window[0].tzinfo is None:
                time_window[0].label_as_time_zone(self._time_zone)
            if time_window[1].tzinfo is None:
                time_window[1].label_as_time_zone(self._time_zone)
            if version_time is not None and version_time.tzinfo is None:
                version_time.label_as_time_zone(self._time_zone)
            cwms.delete_timeseries(
                ts_id=identifier,
                office_id=office,
                begin=time_window[0].datetime(),
                end=time_window[1].datetime(),
                version_date=None if version_time is None else version_time.datetime(),
            )

    def _retrieve_location(self, identifier: str, **kwargs: Any) -> Location:
        office = self._office
        unit_system = self._unit_system
        vertical_datum = self._vertical_datum
        if kwargs:
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ----- #
            # units #
            # ----- #
            if "units" in kwargs:
                argval = kwargs["units"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'units', got {argval.__class__.__name__}"
                    )
                if argval.lower().startswith("en"):
                    unit_system = "EN"
                elif argval.lower() in ("si", "metric"):
                    unit_system = "SI"
                else:
                    raise ValueError(
                        f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{argval}'"
                    )
            # -------------- #
            # vertical_datum #
            # -------------- #
            if "vertical_datum" in kwargs:
                argval = kwargs["vertical_datum"]
                if argval is None:
                    self._vertical_datum = None
                else:
                    if not isinstance(argval, str):
                        raise TypeError(
                            f"Expected str for 'vertical_datum', got {argval.__class__.__name__}"
                        )
                    if not parameter._all_datums_pattern.match(argval):
                        raise ValueError(
                            f"Invalid vertical datum: {argval}. Must be one of {parameter._NGVD29}, {parameter._NAVD88} or {parameter._OTHER_DATUM}"
                        )
                    if parameter._ngvd29_pattern.match(argval):
                        vertical_datum = parameter._NGVD29
                    elif parameter._navd88_pattern.match(argval):
                        vertical_datum = parameter._NAVD88
                    else:
                        vertical_datum = None
        catalog = self.catalog(
            "location",
            pattern=identifier,
            office=office,
            units=unit_system,
            vertical_datum=vertical_datum,
            fields="name,office,latitude,longitude,horizontal-datum,elevation,unit,vertical-datum,time-zone,kind",
        )
        if len(catalog) == 0:
            raise DataStoreException(f"Location not found: {identifier}")
        if len(catalog) > 1:
            raise DataStoreException(
                f"Identifier {identifier} matched more than one location"
            )
        fields = catalog[0].split("\t")
        vdi = self.get_vertical_datum_info(identifier)
        if vdi:
            loc = Location(
                name=fields[0],
                office=fields[1],
                latitude=None if not fields[2] else float(fields[2]),
                longitude=None if not fields[3] else float(fields[3]),
                horizontal_datum=fields[4],
                time_zone=fields[8],
                kind=fields[9],
                vertical_datum_info=vdi,
            )
        else:
            loc = Location(
                name=fields[0],
                office=fields[1],
                latitude=None if not fields[2] else float(fields[2]),
                longitude=None if not fields[3] else float(fields[3]),
                horizontal_datum=fields[4],
                elevation=None if not fields[5] else float(fields[5]),
                elevation_unit=fields[6],
                vertical_datum=fields[7],
                time_zone=fields[8],
                kind=fields[9],
            )
        if vertical_datum and loc.vertical_datum_info:
            loc.vertical_datum_info.ito(vertical_datum)
        return loc

    def _retrieve_time_series(self, identifier: str, **kwargs: Any) -> TimeSeries:
        office = self._office
        time_window = self._time_window
        trim = self._trim
        unit_system = self._unit_system
        version_time = None
        vertical_datum = self._vertical_datum
        if kwargs:
            # -------- #
            # end_time #
            # -------- #
            if "end_time" in kwargs:
                time_window = (
                    time_window[0],
                    HecTime(kwargs["end_time"]),
                )
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ---------- #
            # start_time #
            # ---------- #
            if "start_time" in kwargs:
                time_window = (
                    HecTime(kwargs["start_time"]),
                    time_window[1],
                )
            # ---- #
            # trim #
            # ---- #
            if "trim" in kwargs:
                argval = kwargs["trim"]
                if isinstance(argval, bool):
                    trim = argval
                else:
                    raise TypeError(
                        f"Expected bool or str for 'trim', got {argval.__class__.__name__}"
                    )
            # ----- #
            # units #
            # ----- #
            if "units" in kwargs:
                argval = kwargs["units"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'units', got {argval.__class__.__name__}"
                    )
                if argval.lower().startswith("en"):
                    unit_system = "EN"
                elif argval.lower() in ("si", "metric"):
                    unit_system = "SI"
                else:
                    raise ValueError(
                        f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{argval}'"
                    )
            # ------------ #
            # version_time #
            # ------------ #
            if "version_time" in kwargs:
                version_time = HecTime(kwargs["version_time"]).datetime()
            # -------------- #
            # vertical_datum #
            # -------------- #
            if "vertical_datum" in kwargs:
                argval = kwargs["vertical_datum"]
                if argval is None:
                    self._vertical_datum = None
                else:
                    if not isinstance(argval, str):
                        raise TypeError(
                            f"Expected str for 'vertical_datum', got {argval.__class__.__name__}"
                        )
                    if not parameter._all_datums_pattern.match(argval):
                        raise ValueError(
                            f"Invalid vertical datum: {argval}. Must be one of {parameter._NGVD29}, {parameter._NAVD88} or {parameter._OTHER_DATUM}"
                        )
                    if parameter._ngvd29_pattern.match(argval):
                        vertical_datum = parameter._NGVD29
                    elif parameter._navd88_pattern.match(argval):
                        vertical_datum = parameter._NAVD88
                    else:
                        vertical_datum = None

        if time_window[0]:
            if not time_window[0].tzinfo:
                time_window[0].label_as_time_zone(self._time_zone)
        else:
            raise DataStoreException(
                f"Start time must be specified in kwargs parameter since data store '{self}' has no default start time"
            )
        if time_window[1] and not time_window[1].tzinfo:
            time_window[1].label_as_time_zone(self._time_zone)
        data = cwms.get_timeseries(
            ts_id=identifier,
            office_id=office,
            unit=unit_system,
            datum=vertical_datum,
            begin=time_window[0].datetime() if time_window[0] else None,
            end=time_window[1].datetime() if time_window[1] else None,
            version_date=version_time,
            trim=trim,
        )
        self._context = "CWMS"
        props = data.json
        df = data.df
        name = props["name"]
        timeseries = TimeSeries(name)
        timeseries.location.office = props["office-id"]
        timeseries._timezone = "UTC"
        if version_time is not None:
            timeseries.version_time = HecTime(version_time)
        if (
            timeseries.parameter.base_parameter == "Elev"
            and "vertical-datum-info" in props
        ):
            elev_param = ElevParameter(
                timeseries.parameter.name, props["vertical-datum-info"]
            )
            if elev_param.elevation:
                timeseries.location.elevation = elev_param.elevation
            timeseries.location.vertical_datum = elev_param.native_datum
            timeseries.iset_parameter(elev_param)
        else:
            timeseries.iset_parameter(
                Parameter(timeseries.parameter.name, props["units"])
            )
        if df is not None and len(df):
            timeseries._data = data.df.rename(
                columns={"date-time": "time", "quality-code": "quality"}
            ).set_index("time")
            timeseries._validate()
        timeseries.expand()
        timeseries.iconvert_to_time_zone(self._time_zone)
        return timeseries

    def _store_location(self, obj: object, **kwargs: Any) -> None:
        self._assert_open()
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        if not isinstance(obj, Location):
            raise TypeError(f"Expected Location or str, got {obj.__class__.__name__}")
        required_fields = {
            "office-id",
            "name",
            "horizontal-datum",
            "timezone-name",
            "latitude",
            "location-kind",
            "longitude",
        }
        str_args = {
            "office": "office_id",
            "name": "name",
            "public_name": "public_name",
            "long_name": "long_name",
            "description": "description",
            "time_zone": "timezone_name",
            "type": "location_type",
            "kind": "location_kind",
            "nation": "nation",
            "state": "state_initial",
            "county": "county_name",
            "nearest_city": "nearest_city",
            "horizontal_datum": "horizontal_datum",
            "vertical_datum": "vertical_datum",
            "map_label": "map_label",
            "bounding_office": "bounding_office_id",
            "elevation_unit": "elevation_units",
        }
        float_args = {
            "latitude": "latitude",
            "longitude": "longitude",
            "published_longitude": "published_longitude",
            "published_latitude": "published_latitude",
            "elevation": "elevation",
        }
        bool_args = {
            "active": "active",
        }
        # ------------ #
        # set defaults #
        # ------------ #
        active: Optional[bool] = True
        bounding_office_id: Optional[str] = self.office
        county_name: Optional[str] = None
        description: Optional[str] = None
        elevation = obj.elevation.magnitude if obj.elevation else None
        elevation_units = obj.elevation.specified_unit if obj.elevation else None
        horizontal_datum = obj.horizontal_datum
        latitude = obj.latitude if obj.longitude else 0.0
        location_kind = obj.kind if obj.kind else "SITE"
        location_type: Optional[str] = None
        long_name: Optional[str] = None
        longitude = obj.longitude if obj.latitude else 0.0
        map_label: Optional[str] = None
        name = obj.name
        nation: Optional[str] = "US"
        nearest_city: Optional[str] = None
        office_id = obj.office if obj.office else self.office
        public_name: Optional[str] = None
        published_latitude: Optional[float] = 0.0
        published_longitude: Optional[float] = 0.0
        state_initial: Optional[str] = None
        timezone_name = obj.time_zone if obj.time_zone else self.time_zone
        vertical_datum = (
            obj.vertical_datum if obj.vertical_datum else self.vertical_datum
        )
        if kwargs:
            # --------------------------------- #
            # override defaults from parameters #
            # --------------------------------- #
            for argname in str_args:
                if argname in kwargs:
                    argval = kwargs[argname]
                    if isinstance(argval, str):
                        exec(f"{str_args[argname]} = {argval}")
                        if isinstance(obj, Location):
                            new_val = eval(str_args[argname])
                            if (
                                argname == "office"
                                and obj.office
                                and new_val != obj.office
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.office}",
                                    UserWarning,
                                )
                            if argname == "name" and obj.name and new_val != obj.name:
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.name}",
                                    UserWarning,
                                )
                            elif (
                                argname == "horizontal_datum"
                                and obj.horizontal_datum
                                and new_val != obj.horizontal_datum
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.horizontal_datum}",
                                    UserWarning,
                                )
                            elif (
                                argname == "elevation_unit"
                                and obj.elevation
                                and obj.elevation.specified_unit
                                and new_val != obj.elevation.specified_unit
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.elevation.specified_unit}",
                                    UserWarning,
                                )
                            elif (
                                argname == "vertical_datum"
                                and obj.vertical_datum
                                and new_val != obj.vertical_datum
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.vertical_datum}",
                                    UserWarning,
                                )
                            elif (
                                argname == "time_zone"
                                and obj.time_zone
                                and new_val != obj.time_zone
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.time_zone}",
                                    UserWarning,
                                )
                            elif argname == "kind" and obj.kind and new_val != obj.kind:
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.kind}",
                                    UserWarning,
                                )
                    else:
                        raise TypeError(
                            f"Expected str for {argname}, got {argval.__class__.__name__}"
                        )
            for argname in float_args:
                if argname in kwargs:
                    argval = kwargs[argname]
                    if isinstance(argval, (int, float)):
                        exec(f"{str_args[argname]} = {argval}")
                        if isinstance(obj, Location):
                            new_val = eval(str_args[argname])
                            if (
                                argname == "latitude"
                                and obj.latitude
                                and new_val != obj.latitude
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.latitude}",
                                    UserWarning,
                                )
                            elif (
                                argname == "longitude"
                                and obj.longitude
                                and new_val != obj.longitude
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.longitude}",
                                    UserWarning,
                                )
                            elif (
                                argname == "elevation"
                                and obj.elevation
                                and new_val != obj.elevation
                            ):
                                warnings.warn(
                                    f"{argname} value of {argval} overrides location object value of {obj.elevation}",
                                    UserWarning,
                                )
                    else:
                        raise DataStoreException(
                            f"Expected float for {argname}, got {argval.__class__.__name__} instead"
                        )
            for argname in bool_args:
                if argname in kwargs:
                    argval = kwargs[argname]
                    if isinstance(argval, bool):
                        exec(f"{str_args[argname]} = {argval}")
                    else:
                        raise TypeError(
                            f"Expected bool for {argname}, got {argval.__class__.__name__}"
                        )
        # -------------------------------- #
        # build dictionary for cwms-python #
        # -------------------------------- #
        data = {}
        for item in str_args.values():
            data[item.replace("_", "-")] = eval(item)
        for item in float_args.values():
            data[item.replace("_", "-")] = eval(item)
        for item in bool_args.values():
            data[item.replace("_", "-")] = eval(item)
        for item in required_fields:
            if not item in data or data[item] is None:
                raise DataStoreException(
                    f"Required item '{item.replace('-', '_')}' is not specified"
                )
        # ------------------ #
        # store the location #
        # ------------------ #
        cwms.store_location(data)
        if isinstance(obj, Location) and obj._vertical_datum_info is not None:
            # -------------------------------------------------------------- #
            # store the vertical datum via a temporary elevation time series #
            # -------------------------------------------------------------- #
            if not obj.office:
                obj.office = office_id
            now = HecTime.now().convert_to_time_zone("UTC", on_tz_not_set=0)
            epoch_seconds = int(cast(datetime, now.datetime()).timestamp())
            ts_id = f"{obj.name}.Elev.Inst.0.0.Test-{epoch_seconds}"
            ts = TimeSeries(ts_id)
            ts.iset_location(obj)
            ts._data = pd.DataFrame(
                {
                    "value": [100.0],
                    "quality": [0],
                },
                index=pd.Index([now.datetime()], name="time"),
            )
            # ----------------------------------- #
            # 1. store the elevation time seires  #
            # 2. delete the elevation time series #
            # ----------------------------------- #
            try:
                self.store(
                    ts,
                    office=ts.location.office,
                    vertical_datum_info=obj.vertical_datum_json,
                )
            except Exception as e:
                warnings.warn(
                    f"Unable to store vertical datum info for location {obj}",
                    UserWarning,
                )
            else:
                try:
                    self.delete(
                        ts.name,
                        office=ts.location.office,
                        delete_action=DeleteAction.DELETE_ALL,
                    )
                except:
                    warnings.warn(
                        f"Unable to delete temporary time series {ts.location.office}/{ts.name}",
                        UserWarning,
                    )

    def _store_time_series(self, obj: object, **kwargs: Any) -> None:
        self._assert_open()
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        if isinstance(obj, TimeSeries):
            if obj.data is None:
                raise DataStoreException(f"Cannot store empty time series {obj.name}")
            df = obj.data.reset_index().rename(
                columns={"time": "date-time", "quality": "quality-code"}
            )
            name = obj.name
            if name.startswith(f"{self.office}/"):
                name = name.split("/", 1)[1]
            json = cwms.timeseries_df_to_json(
                df,
                name,
                obj.unit,
                self.office,
                None if obj._version_time is None else obj._version_time.datetime(),
            )
            as_lrts = obj.interval.is_local_regular
            override_protection = False
            store_rule = self._store_rule
            vertical_datum_info = None
            if kwargs:
                # ------- #
                # as_lrts #
                # ------- #
                if "as_lrts" in kwargs:
                    argval = kwargs["as_lrts"]
                    if isinstance(argval, bool):
                        as_lrts = argval
                    elif argval is None:
                        pass
                    else:
                        raise TypeError(
                            f"Expected bool or str for 'as_lrts', got {argval.__class__.__name__}"
                        )
                # ------------------- #
                # override_protection #
                # ------------------- #
                if "override_protection" in kwargs:
                    argval = kwargs["override_protection"]
                    if isinstance(argval, bool):
                        override_protection = argval
                    elif argval is None:
                        pass
                    else:
                        raise TypeError(
                            f"Expected bool or str for 'override_protection', got {argval.__class__.__name__}"
                        )
                # ---------- #
                # store rule #
                # ---------- #
                if "store_rule" in kwargs:
                    argval = kwargs["store_rule"]
                    if isinstance(argval, StoreRule):
                        store_rule = argval
                    elif isinstance(argval, str):
                        if argval.upper() in list(StoreRule.__members__):
                            store_rule = StoreRule[argval.upper()]
                        else:
                            raise ValueError(
                                f"Invalid store rule {argval}, must be one of {list(StoreRule.__members__)}"
                            )
                    elif argval is None:
                        pass
                    else:
                        raise TypeError(
                            f"Expected StoreRule or str for store_rule, got {argval.__class__.__name__}"
                        )
                # ------------------- #
                # vertical_datum_info #
                # ------------------- #
                if "vertical_datum_info" in kwargs:
                    argval = kwargs["vertical_datum_info"]
                    if isinstance(argval, str):
                        vertical_datum_info = argval
                    elif argval is None:
                        pass
                    else:
                        raise TypeError(
                            f"Expected bool or str for 'vertical_datum_info', got {argval.__class__.__name__}"
                        )
            if vertical_datum_info:
                json["vertical-datum-info"] = eval(vertical_datum_info)
            cwms.store_timeseries(
                data=json,
                create_as_ltrs=as_lrts,
                store_rule=store_rule.name,
                override_protection=override_protection,
            )
        else:
            raise TypeError(f"Expected TimeSeries, got {obj.__class__.__name__}")

    def catalog(
        self,
        data_type: Optional[str] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        Retrieves CWMS identifiers for the specified data type, optionally with extents for specific data types.

        Currently only time series objects may be cataloged.

        Args:
            data_type (str): Must be one of the following (case insensitive):
                * **'TIMESERIES'**: specifies cataloging CWMS time series objects in the data store
                * **'LOCATION'**: specfies catalog CWMS locations in the data store
            pattern (Optional[str], must be passed by name): An extended wildcard pattern to use for matching identifiers. `regex` takes precedence if both are specified. Defaults to None.
                <table>
                <pre>
                <tr><th colspan="2">Pattern Examples</th></tr>
                <tr><th>pattern</th><th>matches</th></tr>
                <tr><td><code>abc</code></td><td>the literal string "abc"</td></tr>
                <tr><td><code>ab{2,3}c{2}</code></td><td>1 "a" followed by 2 or 3 "b" followed by 2 "c"</td></tr>
                <tr><td><code>a*b?c</code></td><td>1 "a" followed by zero or more characters followed by "b" followed by 1 character followed by 1 "c"</td></tr>
                <tr><td><code>[abc]</code></td><td>1 "a" or "b" or "c"</td></tr>
                <tr><td><code>^[abc]$</code></td><td>beginning of string followed by 1 "a" or "b" or "c" followed by end of string</td></tr>
                <tr><td><code>[!abc]</code></td><td>1 character other than "a" or "b" or "c"</td></tr>
                <tr><td><code>[_a-z0-9]*</code></td><td>zero or more of characters "_" or "a" through "z" or "0" through "9"</td></tr>
                <tr><td><code style="white-space: nowrap;">[!a-z0-9]{1,5}</code></td><td>1..5 characters other than "a" through "z" or "0" through "9"</td></tr>
                <tr><td><code>(abc|def)</code></td><td>either "abc" or "def"</td></tr>
                </pre>
                </table>
            regex (Optional[str], must be passed by name): Regular expression to use for matching identifiers. Takes precedence over `pattern` if both are specified. Defaults to None.
            bounding_office (Optional[str]), must be passed by name): Specifies cataloging only identifiers that are physically located within the boundaries of the specified office.
                Can be a wildcard pattern. Matching is affected by `case_sensitive`.
            case_sensitive (Optional[bool], must be passed by name): Specifies whether and pattern or regular expression matching is case-sensitive.
            category (Optional[str], must be passed by name, LOCATION only): Specifies cataloging only locations in a location group belonging to the specified catgory(ies). Can be a wildcard pattern.
                Matching is affected by `case_sensitive`. Note that specifying `category` or `group`, or including "aliases" in `fields` will slow down the catalog operation.
            fields (Optional[str]), must be passed by name): A comma-separated list of fields to include in the catalog. Valid fields for `data_type` are listed below.
                The catalog will include the fields in the order specified. Defaults to `identifier`.
                * **`TIMESERIES`**:
                    * `identifier`: The time series identifier
                    * `office`: The CWMS office for the time series
                    * `name`: Same as `identifier`
                    * `time-zone`: The time zone of the location of the time seroies
                    * `interval`: The interval of the time series
                    * `offset`:  The offset into each interval of regular time series (in minutes), or <N/A> if interval is irregular
                    * `earliest-time`: The earliest time in the database for this time series, or <None> if no data
                    * `latest-time`: The latest time in the database for this time seires of <None> if no data
                    * `last-update`: The most recent time this time series has been updated, or <None> of no data
                * **`LOCATION`**:
                    * `identifier`: The location identifier
                    * `office`: The CWMS office for the location
                    * `name`: Same as `identifier`
                    * `nearest-city`: The name of the city or town closest to the location
                    * `public-name`: The public name of the location
                    * `long-name`: The long name of the location
                    * `kind`: The kind of location - constrained to:
                        * SITE
                        * EMBANKMENT
                        * OVERFLOW
                        * TURBINE
                        * STREAM
                        * PROJECT
                        * STREAMGAGE
                        * BASIN
                        * OUTLET
                        * LOCK
                        * GATE
                    * `time-zone`: The time zone of the location
                    * `latitude`: The latitude of the location
                    * `longitude`: The latitude of the location
                    * `published-latitude`: The published latitude of the location
                    * `published-longitude`: The published longitude of the location
                    * `horizontal-datum`: The horizontal datum associated with the latitude and longitude
                    * `elevation`: The elevation of the location
                    * `unit`: The unit of the elevation
                    * `vertical-datum`: The vertical datum of the elevation
                    * `nation`: The nation containing the location
                    * `state`: The state/province containing the location
                    * `county`: The county containing the location
                    * `bounding-office`: The CWMS office whose boundary includes the location
                    * `map-label`: The map label of the location
                    * `active`: Whether the location is active
                    * `aliases`: The aliases associated with the location. Note that including this slows down the catalog operation. The aliases are specified as the string
                        representation of a dictionary (i.e., an actual dictionary can be obtained by passing this field to `eval()`). The dictionary keys are the location
                        categories and groups for each alias, and the values are the aliases. The keys are of the form {category}-{group} (e.g., "Angency Aliases-NWS Handbook 5 ID")
                    * `description`: The description of the location
                    * `type`: The unconstrained type of the location (cf `kind`)
            group (Optional[str], must be passed by name, LOCATION only): Specifies cataloging only locations in the specivied location group(s). Can be a wildcard pattern.
                Matching is affected by `case_sensitive`. Note that specifying `category` or `group`, or including "aliases" in `fields` will slow down the catalog operation.
            header (Optional[bool], must be passed by name): Specifies whether to include a header line in the catalog that identifies the fields
            kind (Optional[str], must be passed by name, LOCATION only): Specifies cataloging only locations of the specified location kind. Can be a wildcard pattern.
                Matching is affected by `case_sensitive`.
            limit (Optional[int], must be passed by name): The maximum number of identifiers to return. If None, no limit is imposed. Defaults to None.
            office (Optional[str], must be passed by name): The CWMS office to generate the catalog for. Defaults to None, which uses the data store's default office.
            units (Optional[str], must be passed by name): The unit system ("EN" or "SI") to return the elevation values in. Defaults to None.
            vertical_datum (Optional[str], must be passed by name): The vertical datum ("NGVD29", "NAVD88", or "LOCAL") to return the elevation values in. Defaults to None (Native datum).

        Raises:
            DataStoreException: if the data store is not open or an invalid `data_type` is specified

        Returns:
            List[str]: The CWMS identifiers that match the specified parameters, up to the specified limit, if any
        """
        self._assert_open()
        bounding_office: Optional[str] = None
        case_sensitive: Optional[bool] = False
        category: Optional[str] = None
        fields: List[str] = ["identifier"]
        fieldstr: Optional[str] = None
        group: Optional[str] = None
        header: bool = False
        kind: Optional[str] = None
        limit: Optional[int] = None
        office: Optional[str] = None
        units: Optional[str] = None
        vertical_datum: Optional[str] = None
        _regex: Optional[str] = None
        if not data_type:
            raise DataStoreException(
                f"Parameter data_type must be specified and must be one of {list(_CwmsDataType.__members__)}"
            )
        if data_type.upper() not in _CwmsDataType.__members__:
            raise DataStoreException(
                f"Invalid data type: '{data_type}', must be one of {list(_CwmsDataType.__members__)}"
            )
        if kwargs:
            # --------------- #
            # bounding_office #
            # --------------- #
            if "bounding_office" in kwargs:
                argval = kwargs["bounding_office"]
                if isinstance(argval, str):
                    bounding_office = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'bounding_office', got {argval.__class__.__name__}"
                    )
            # -------------- #
            # case_sensitive #
            # -------------- #
            if "case_sensitive" in kwargs:
                argval = kwargs["case_sensitive"]
                if isinstance(argval, bool):
                    case_sensitive = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str or bool for 'case_sensitive', got {argval.__class__.__name__}"
                    )
            # ------------------------- #
            # category (locations only) #
            # ------------------------- #
            if "category" in kwargs:
                argval = kwargs["category"]
                if isinstance(argval, str):
                    category = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'category', got {argval.__class__.__name__}"
                    )
            # ------ #
            # fields #
            # ------ #
            if "fields" in kwargs:
                argval = kwargs["fields"]
                if isinstance(argval, str):
                    fieldstr = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'fields', got {argval.__class__.__name__}"
                    )
            # --------------------- #
            # group (location only) #
            # --------------------- #
            if "group" in kwargs:
                argval = kwargs["group"]
                if isinstance(argval, str):
                    group = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'group', got {argval.__class__.__name__}"
                    )
            # ------ #
            # header #
            # ------ #
            if "header" in kwargs:
                argval = kwargs["header"]
                if isinstance(argval, bool):
                    header = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str or bool for 'case_sensitive', got {argval.__class__.__name__}"
                    )
            # --------------------- #
            # kind (locations only) #
            # --------------------- #
            if "kind" in kwargs:
                argval = kwargs["kind"]
                if isinstance(argval, str):
                    kind = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'kind', got {argval.__class__.__name__}"
                    )
            # ----- #
            # limit #
            # ----- #
            if "limit" in kwargs:
                argval = kwargs["limit"]
                if isinstance(argval, int):
                    limit = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected int for 'limit', got {argval.__class__.__name__}"
                    )
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if isinstance(argval, str):
                    office = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
            # ------- #
            # pattern #
            # ------- #
            if "pattern" in kwargs:
                argval = kwargs["pattern"]
                if isinstance(argval, str):
                    _regex = _pattern_to_regex(argval)
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'pattern', got {argval.__class__.__name__}"
                    )
            # ------------------------------------- #
            # regex (takes precedence over pattern) #
            # ------------------------------------- #
            if "regex" in kwargs:
                argval = kwargs["regex"]
                if isinstance(argval, str):
                    _regex = argval
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'regex', got {argval.__class__.__name__}"
                    )
            # ----- #
            # units #
            # ----- #
            if "units" in kwargs:
                argval = kwargs["units"]
                if isinstance(argval, str):
                    if argval.upper() not in ["EN", "SI"]:
                        raise DataStoreException(
                            f"Invalid units, expected EN or SI, got {argval}"
                        )
                    units = argval.upper()
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'units', got {argval.__class__.__name__}"
                    )
            # -------------- #
            # vertical_datum #
            # -------------- #
            if "vertical_datum" in kwargs:
                argval = kwargs["vertical_datum"]
                if isinstance(argval, str):
                    if not parameter._all_datums_pattern.match(argval):
                        raise DataStoreException(
                            f"Invalid vertical_datum, expected {parameter._NGVD29}, {parameter._NGVD29}, or {parameter._OTHER_DATUM}"
                        )
                    if parameter._ngvd29_pattern.match(argval):
                        vertical_datum = parameter._NGVD29
                    elif parameter._navd88_pattern.match(argval):
                        vertical_datum = parameter._NAVD88
                    else:
                        vertical_datum = parameter._OTHER_DATUM
                elif argval is None:
                    pass
                else:
                    raise TypeError(
                        f"Expected str for 'vertical_datum', got {argval.__class__.__name__}"
                    )
        if not office and not self._office:
            raise DataStoreException(
                f"Office parameter must be specified since data store '{self}' has no default office"
            )
        header_str = None
        if not _regex:
            _regex = "^.+$"
        catalog_type = _CwmsDataType[data_type.upper()]
        valid_fields = _valid_catalog_fields[CWMS][catalog_type.name]
        catalog_items: List[str] = []
        if catalog_type == _CwmsDataType.TIMESERIES:
            fieldstr = None if not fieldstr else fieldstr.lower().strip()
            name_field = None
            if fieldstr:
                fields = re.split(r"\s*,\s*", fieldstr)
                invalid_fields = [f for f in fields if f not in valid_fields]
                if invalid_fields:
                    raise DataStoreException(
                        f"Invalid field(s) specified: [{', '.join(invalid_fields)}], must be one of [{', '.join(valid_fields)}]"
                    )
            if header:
                header_str = f"#{chr(9).join(fields)}"
            for i in range(len(fields)):
                if fields[i] == "identifier":
                    fields[i] = "name"
                elif fields[i] == "offset":
                    fields[i] = "interval-offset"
            try:
                name_field = fields.index("name")
            except:
                pass
            extent_fields = ["earliest-time", "latest-time", "last-update"]
            include_extents = any([item in fields for item in extent_fields])
            extents = []
            data = cwms.get_timeseries_catalog(
                office_id=office if office else self._office,
                unit_system=units if units else self._unit_system,
                page_size=limit if limit else 5000,
                like=_regex,
                timeseries_category_like=category,
                timeseries_group_like=group,
                bounding_office_like=bounding_office,
                include_extents=include_extents,
            )
            non_extent_fields = [f for f in fields if f not in extent_fields]
            if not data.df.empty:
                field_items = {}
                for field in non_extent_fields:
                    if field == "interval-offset":
                        field_items[field] = [
                            s.replace("-2147483648", "<N/A>")
                            for s in list(map(str, data.df[field].to_list()))
                        ]
                    else:
                        field_items[field] = list(map(str, data.df[field].to_list()))
                if include_extents:
                    extents.extend(
                        list(
                            map(lambda i: eval(str(i))[0], data.df["extents"].to_list())
                        )
                    )
                else:
                    catalog_items.extend(
                        list(
                            map("\t".join, list(zip(*(field_items[f] for f in fields))))
                        )
                    )
                if not limit:
                    while "next-page" in data.json and data.json["next-page"]:
                        data = cwms.get_timeseries_catalog(
                            office_id=office if office else self._office,
                            page=data.json["next-page"],
                            unit_system=self._unit_system,
                            page_size=5000,
                            like=_regex,
                            timeseries_group_like=None,
                        )
                        if not data.df.empty:
                            field_items = {}
                            for field in non_extent_fields:
                                if field == "interval-offset":
                                    field_items[field].extend(
                                        [
                                            s.replace("-2147483648", "<N/A>")
                                            for s in list(
                                                map(str, data.df[field].to_list())
                                            )
                                        ]
                                    )
                                else:
                                    field_items[field].extend(
                                        list(map(str, data.df[field].to_list()))
                                    )
                            if include_extents:
                                extents.extend(
                                    list(
                                        map(
                                            lambda i: eval(str(i))[0],
                                            data.df["extents"].to_list(),
                                        )
                                    )
                                )
                            else:
                                catalog_items.extend(
                                    list(
                                        map(
                                            "\t".join,
                                            list(
                                                zip(*(field_items[f] for f in fields))
                                            ),
                                        )
                                    )
                                )
                if include_extents:
                    field_items["earliest-time"] = list(
                        map(
                            lambda i: (
                                "<None>"
                                if "earliest-time" not in i
                                else i["earliest-time"]
                            ),
                            extents,
                        )
                    )
                    field_items["latest-time"] = list(
                        map(
                            lambda i: (
                                "<None>" if "latest-time" not in i else i["latest-time"]
                            ),
                            extents,
                        )
                    )
                    field_items["last-update"] = list(
                        map(
                            lambda i: (
                                "<None>" if "last-update" not in i else i["last-update"]
                            ),
                            extents,
                        )
                    )
                    transposed_catalog = [field_items[f] for f in fields]
                    catalog = [row for row in list(zip(*transposed_catalog))]
                    catalog_items = ["\t".join(row) for row in catalog]
                if (
                    catalog_items
                    and _regex
                    and case_sensitive
                    and name_field is not None
                ):
                    # API uses case insensitive matching
                    pat = re.compile(_regex)
                    catalog_items = list(
                        filter(
                            lambda s: bool(pat.match(s.split(r"\t")[name_field])),  # type: ignore
                            catalog_items,
                        )
                    )
        elif catalog_type == _CwmsDataType.LOCATION:
            fieldstr = None if not fieldstr else fieldstr.lower().strip()
            name_field = None
            if fieldstr:
                fields = re.split(r"\s*,\s*", fieldstr)
                invalid_fields = [f for f in fields if f not in valid_fields]
                if invalid_fields:
                    raise DataStoreException(
                        f"Invalid field(s) specified: [{', '.join(invalid_fields)}], must be one of [{', '.join(valid_fields)}]"
                    )
            if header:
                header_str = f"#{chr(9).join(fields)}"
            for i in range(len(fields)):
                if fields[i] == "identifier":
                    fields[i] = "name"
            try:
                name_field = fields.index("name")
            except:
                pass
            if category or group or "aliases" in fields:
                # -------------------- #
                # use catalog endpoint #
                # -------------------- #
                # must filter category and group after-the-fact (CDA problem)
                specified_fields = fields[:]
                if category or group and not "aliases" in fields:
                    fields.append("aliases")
                data = cwms.get_locations_catalog(
                    office_id=office if office else self._office,
                    unit_system=self.units,
                    page_size=limit if limit else 5000,
                    like=_regex,
                    # location_category_like=_pattern_to_regex(category), -- doesn't work
                    # location_group_like=_pattern_to_regex(group),       -- doesn't work
                    bounding_office_like=_pattern_to_regex(bounding_office),
                    location_kind_like=_pattern_to_regex(kind),
                )
                if not data.df.empty:
                    field_items = {}
                    for field in fields:
                        field_items[field] = list(map(str, data.df[field].to_list()))
                    catalog_items.extend(
                        list(
                            map("\t".join, list(zip(*(field_items[f] for f in fields))))
                        )
                    )
                if not limit:
                    while "next-page" in data.json and data.json["next-page"]:
                        data = cwms.get_locations_catalog(
                            office_id=office if office else self._office,
                            unit_system=self.units,
                            page_size=limit if limit else 5000,
                            like=_regex,
                            # location_category_like=_pattern_to_regex(category), -- doesn't work
                            # location_group_like=_pattern_to_regex(group),       -- doesn't work
                            bounding_office_like=_pattern_to_regex(bounding_office),
                            location_kind_like=_pattern_to_regex(kind),
                        )
                        if not data.df.empty:
                            field_items = {}
                            for field in fields:
                                field_items[field] = [
                                    "<None>" if not item or item == "nan" else item
                                    for item in map(str, data.df[field].to_list())
                                ]
                            catalog_items.extend(
                                list(
                                    map(
                                        "\t".join,
                                        list(zip(*(field_items[f] for f in fields))),
                                    )
                                )
                            )
                # ---------------------------------------------------------- #
                # filter category and group and re-format aliases for output #
                # ---------------------------------------------------------- #
                try:
                    alias_field = fields.index("aliases")
                except:
                    pass
                else:
                    cat_pat = None if not category else re.compile(_pattern_to_regex(category), 0 if case_sensitive else re.I)  # type: ignore
                    grp_pat = None if not group else re.compile(_pattern_to_regex(group), 0 if case_sensitive else re.I)  # type: ignore
                    matched = len(catalog_items) * [category is None and group is None]
                    include_aliases = "aliases" in specified_fields
                    for i in range(len(catalog_items)):
                        parts = catalog_items[i].split("\t")
                        old = eval(parts[alias_field])
                        new = {}
                        for d in old:
                            cat_grp = d["name"]
                            if cat_pat or grp_pat:
                                cat, grp = cat_grp.split("-", 1)
                                if (cat_pat is None or cat_pat.match(cat)) and (
                                    grp_pat is None or grp_pat.match(grp)
                                ):
                                    matched[i] = True
                            new[cat_grp] = d["value"]
                        parts[alias_field] = str(new)
                        catalog_items[i] = "\t".join(
                            parts if include_aliases else parts[:-1]
                        )  # alias field is always last if not in specified fiels
                    if not all(matched):
                        catalog_items = [
                            catalog_items[i]
                            for i in range(len(catalog_items))
                            if matched[i]
                        ]
                if "elevation" in fields and (vertical_datum or self.vertical_datum):
                    pass
            else:
                # ---------------------- #
                # use locations endpoint #
                # ---------------------- #
                # must filter kind and bounding office after-the-fact (not supported in this endpoint)
                specified_fields = fields[:]
                if bounding_office and not "bounding-office" in fields:
                    fields.append("bounding-office")
                if kind and not "kind" in fields:
                    fields.append("kind")
                data = cwms.get_locations(
                    office_id=office if office else self.office,
                    location_ids=_regex,
                    units=units if units else self.units,
                    datum=vertical_datum if vertical_datum else self.vertical_datum,
                )
                if not data.df.empty:
                    # change column names to match catalog endpoint
                    df = data.df.rename(
                        columns={
                            "bounding-office-id": "bounding-office",
                            "county-name": "county",
                            "elevation-units": "unit",
                            "location-kind": "kind",
                            "location-type": "type",
                            "office-id": "office",
                            "state-initial": "state",
                            "timezone-name": "time-zone",
                        }
                    )
                    field_items = {}
                    for field in fields:
                        items = list(map(str, df[field].to_list()))
                        field_items[field] = [
                            "<None>" if not item or item in ("nan", "NULL") else item
                            for item in items
                        ]
                    # each location gets returned twice (https://github.com/HydrologicEngineeringCenter/cwms-python/issues/143)
                    # so use a set() to filter duplicates
                    catalog_items.extend(
                        sorted(
                            set(
                                map(
                                    "\t".join,
                                    list(zip(*(field_items[f] for f in fields))),
                                )
                            )
                        )
                    )
                    # filter kind and bounding office
                    if bounding_office:
                        pat = re.compile(
                            cast(str, _pattern_to_regex(bounding_office)),
                            0 if case_sensitive else re.I,
                        )
                        idx = fields.index("bounding-office")
                        catalog_items = list(
                            filter(
                                lambda s: pat.match(s.split(r"\t")[idx]), catalog_items
                            )
                        )
                        if not "bounding-office" in specified_fields:
                            fields.pop(idx)
                            for i in range(len(catalog_items)):
                                items = catalog_items[i].split("\t")
                                items.pop(idx)
                                catalog_items[i] = "\t".join(items)
                    if kind:
                        pat = re.compile(
                            cast(str, _pattern_to_regex(kind)),
                            0 if case_sensitive else re.I,
                        )
                        idx = fields.index("kind")
                        catalog_items = list(
                            filter(
                                lambda s: pat.match(s.split("\t")[idx]), catalog_items
                            )
                        )
                        if not "kind" in specified_fields:
                            fields.pop(idx)
                            for i in range(len(catalog_items)):
                                items = catalog_items[i].split("\t")
                                items.pop(idx)
                                catalog_items[i] = "\t".join(items)

            if catalog_items and _regex and case_sensitive and name_field is not None:
                # API uses case insensitive matching
                pat = re.compile(_regex)
                catalog_items = list(
                    filter(
                        lambda s: pat.match(s.split(r"\t")[name_field]), catalog_items
                    )
                )
        else:
            raise DataStoreException(f"Unexpected error with data type {data_type}")
        if header_str:
            catalog_items.insert(0, header_str)
        return catalog_items

    def close(self) -> None:
        cwms.SESSION.close()
        self._is_open = False

    def delete(self, identifier: str, **kwargs: Any) -> None:
        """
        Deletes a data set from the data store.

        Currently only time series data may be deleted.

        Args:
            identifier (str): The name of the data set to delete. Must be a valid one of the following:
                * **time series identifier**: start and end times specify the time window of time series values to delete, inclusive
            delete_action (Optional[str], must be passed by name): Defaults to None. If specified, any time window is ignored and it must be one of (case insensitive):
                * 'DELETE_ALL': delete all data and the identifier for the object
                * 'DELETE_DATA': delete all data for the identifier but does not delete the identifier
                * 'DELETE_KEY': delete only the object identifier - will fail if any data is associated with the identifier
            end_time (Optional[Any], must be passed by name): Specifies the end of the time window to delete data. Ignored if `delete_action` is specified. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the end of the data store's time window.
            office (Optional[str], must be passed by name): The CWMS office to delete data for. Defaults to None, which uses the data store's default office.
            start_time (Optional[Any], must be passed by name): Specifies the start of the time window to delete data. Ignored if `delete_action` is specified. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the start of the data store's time window.
            version_time (Optional[Any], must be passed by name): Specifies the version date/time of the data to delete (time series types only). Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                Defaults to the None, meaning non-versioned data.
        """
        if timeseries._is_cwms_tsid(identifier):
            self._delete_time_series(identifier, **kwargs)
        elif location._is_cwms_location(identifier):
            self._delete_location(identifier, **kwargs)
        else:
            raise ValueError(
                f"Identifier {identifier} is not a recognized CWMS identifier"
            )

    def get_extents(self, identifier: str, **kwargs: Any) -> List[HecTime]:
        """
        Retrieves the data extents for the specified identifier

        Args:
            identifier (str): The identifier to retrieve the extents for

        Returns:
            List[HecTime]: The earliest time, latest time, and latest update time
        """
        office = self._office
        if kwargs:
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
        if not office and not self._office:
            raise DataStoreException(
                f"Office parameter must be specified since data store '{self}' has no default office"
            )
        if TimeSeries.is_cwms_ts_id(identifier):
            item_list = self.catalog(
                "timeseries",
                pattern=identifier,
                fields="identifier,earliest-time,latest-time,last-update",
            )
            if len(item_list) == 0:
                raise DataStoreException(
                    f"Identifier '{identifier}' did not match any time series identifiers"
                )
            if len(item_list) > 1:
                raise DataStoreException(
                    f"Identifier '{identifier}' matched {len(item_list)} time series identifiers"
                )
            return list(map(HecTime, item_list[0].split("\t")[1:]))
        else:
            raise ValueError(
                "The get_extents() method is available only for time series data"
            )

    def get_vertical_datum_info(self, identifier: str, **kwargs: Any) -> Optional[str]:
        """
        Retrieves the vertical datum information for a CWMS location

        Args:
            identifier (str): The location identifier
            office (Optional[str]): The CWMS office for the location. Defaults to the data store's default office.
            format (Optional[str]): The output format for the information. Must be one of 'JSON' or 'XML' (case insensitive). Defaults to 'JSON'

        Returns:
            Optional[str]: The vertical datum information in the specified format
        """
        self._assert_open()
        office = self._office
        output_format = "JSON"
        if kwargs:
            # ------ #
            # office #
            # ------ #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ------ #
            # format #
            # ------ #
            if "format" in kwargs:
                argval = kwargs["format"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'format', got {argval.__class__.__name__}"
                    )
                output_format = argval.upper()
                if output_format not in ("JSON", "XML"):
                    raise DataStoreException(
                        f"Invalid format specified: '{argval}', must be one of 'JSON', or 'XML'"
                    )
        office = office if office else self.office
        if not office:
            raise DataStoreException(
                f"Office parameter must be specified since data store '{self}' has no default office"
            )
        if location._is_cwms_location(identifier):
            loc_id = identifier
        else:
            raise ValueError("Identifier must be a valid CWMS location identifier")
        vdi = None
        # -------------------------------------------------------- #
        # find an elevation time series to retrieve one value from #
        # -------------------------------------------------------- #
        catalog = self.catalog(
            "timeseries", pattern=f"{loc_id}.Elev.*", fields="identifier,latest-time"
        )
        latest_time: Optional[str] = None
        for tsid, latest_time in list(map(lambda s: s.split("\t"), catalog)):
            if latest_time:
                break
        if latest_time:
            # ---------------------------------------------------- #
            # retrieve the time series and the vertical datum info #
            # ---------------------------------------------------- #
            ts = self.retrieve(
                tsid, start_time=latest_time, end_time=latest_time, office=office
            )
            vdi = ts.vertical_datum_info_xml
        else:
            # ------------------------------------------------- #
            # no available elevation time series, so create one #
            # ------------------------------------------------- #
            catalog = self.catalog("location", pattern=loc_id, office=office)
            if not catalog:
                raise DataStoreException(
                    f"{office}/{loc_id} is not a valid CWMS location"
                )
            now = HecTime.now().convert_to_time_zone("UTC", on_tz_not_set=0)
            epoch_seconds = int(cast(datetime, now.datetime()).timestamp())
            ts_id = f"{loc_id}.Elev.Inst.0.0.Test-{epoch_seconds}"
            ts = TimeSeries(ts_id)
            ts.location.office = office
            ts._data = pd.DataFrame(
                {
                    "value": [100.0],
                    "quality": [0],
                },
                index=pd.Index([now.datetime()], name="time"),
            )
            # ------------------------------------------------------ #
            # 1. store the elevation time seires                     #
            # 2. retrieve it and extract the the vertical datum info #
            # 3. delete the elevation time series                    #
            # ------------------------------------------------------ #
            restore_read_only = self.is_read_only
            if restore_read_only:
                self.is_read_only = False
            try:
                self.store(ts, office=office)
                catalog = self.catalog("timeseries", pattern=ts.name, office=office)
                try:
                    ts2 = cast(
                        TimeSeries,
                        self.retrieve(
                            ts.name, office=office, start_time=now, end_time=now
                        ),
                    )
                    vdi = ts2.vertical_datum_info_xml
                finally:
                    self.delete(
                        ts.name, office=office, delete_action=DeleteAction.DELETE_ALL
                    )
            except Exception as e:
                # ------------------------- #
                # may not have write access #
                # ------------------------- #
                pass
            finally:
                if restore_read_only:
                    self.is_read_only = True
        # -------------------------------------------------------------------------------- #
        # return the vertical datum info, issuing a warning if unable to retrieve anything #
        # -------------------------------------------------------------------------------- #
        if vdi:
            ts.location.vertical_datum_info = vdi
            if output_format == "JSON":
                vdi = ts.location.vertical_datum_json
            else:
                vdi = ts.location.vertical_datum_xml
        else:
            warnings.warn(
                f"{self}: Unable to retrieve vertical datum information for location {loc_id}"
            )
        return vdi

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def native_data_store(self) -> Any:
        """
        The cwms module imported by this data store

        Operations:
            Read-Only
        """
        return cwms

    @staticmethod
    def open(name: Optional[str] = None, **kwargs: Any) -> "CwmsDataStore":
        """
        Creates and returns a new CwmsDataStore object.

        Equivalent of calling [`CwmsDataStore(**kwargs)`](#CwmsDataStore) with `name` in `kwargs`

        Args:
            name (Optional[str]): The API root (base URL). Defaults to None. If None:
                * The value of environment variable "cda_api_root" is used, if it exists.
                * If the environment variable "cda_api_root" is not set, the default, the default value used in `cwms.api.init_session()` is used.
            api_key (Optional[str], must be passed by name): The API key for this data store. Must be specified to write to or delete from this data store. Defaults to None. If None:
                * The value of environment variable "cda_api_key" is used, if it exists.
            description (Optional[str], must be passed by name): The description assocaited with the data store. Defaults to None
            end_time (Optional[Any], must be passed by name): Specifies the end time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            office (Optional[str], must be passed by name): The default CWMS office for the data store. If None or not specified, each access method will have to have an office specified.
            read_only (Optional[bool], must be passed by name): Specifies whether to open the data store in read-only mode. Defaults to True
            start_time (Optional[Any], must be passed by name): Specifies the start time of the data store's time window. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor. Defaults to None
            store_rule (Optional[str], must be passed by name): Specifies the default behavior to use when storing data. If specified, it must be one of the following (case insensitive). Defaults to 'REPLACE_ALL'.
                * 'DELETE_INSERT' - delete all existing data in the incoming time window, then store the incoming data
                * 'DO_NOT_REPLACE' - store only non-existing data
                * 'REPLACE_ALL' - store existing and non-existing data
                * 'REPLACE_MISSING_VALUES_ONLY' - store incoming data only where existing data is missing
                * 'REPLACE_WITH_NON_MISSING' - store only non-missing incoming data
            time_zone (Optional[str], must be passed by name): The default time zone for the data store. Defaults to the local time zone.
            trim (Optional[bool], must be passed by name): Specifies the data store's default setting to trim missing values from the beginning and end of any regular time series data set retrieved.
                Defaults to True.
            units (Optional[str], must be passed by name): "EN" or "SI", specifying English or metric unit system as the default unit system for the data store. Defaults to "EN"
            vertical_datum (Optional[str], must be passed by name): "NGVD29", "NAVD88", or "NATIVE", specifying the data store's default vertical datum for retrieving elevation data. Defaults to "NATIVE"
        """
        kwargs2 = {} if not kwargs else kwargs.copy()
        kwargs2["name"] = name
        ds = CwmsDataStore(**kwargs2)
        return ds

    def retrieve(self, identifier: str, **kwargs: Any) -> Any:
        """
        Retrieves a data set from the data store.

        Currently only locations and time series may be retrieved. To retrieve all data for a time series, specifiy `start_time=None` and `end_time=None`

        Args:
            office (Optional[str], must be passed by name): The CWMS office to retrieve data for. Defaults to None, which uses the data store's default office.
            identifier (str): The name of the data set to retrieve:
            Location Arguments:<br>
                * <b>units (Optional[str], must be passed by name):</b> "EN" or "SI", specifying to retrieve data in English or metric units. Defaults to None, which uses the default unit system for the data store
                * <b>vertical_datum (Optional[str], must be passed by name):</b> "NGVD29", "NAVD88", or "NATIVE", specifying the vertical datum to retrieve elevation data for. Defaults to None, which uses the data store's default vertical datum
            TimeSeries Arguments:<br>
                * <b>start_time (Optional[Any], must be passed by name):</b> Specifies the start of the time window to retrieve data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                    Defaults to the start of the data store's time window. If None or not specified and the data store's time window doesn't have a start time, the current time minus 24 hours is used
                * <b>end_time (Optional[Any], must be passed by name):</b> Specifies the end of the time window to retrieve data. Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                    Defaults to the end of the data store's time window. If None or not specified and the data store's time window doesn't have an end time, the current time is used
                * <b>trim (Optional[bool], must be passed by name):</b> Specifies whether to trim missing values from the beginning and end of any regular time series data set retrieved.
                    Defaults to the data store's trim setting.
                * <b>units (Optional[str], must be passed by name):</b> "EN" or "SI", specifying to retrieve data in English or metric units. Defaults to None, which uses the default unit system for the data store
                * <b>version_time (Optional[Any], must be passed by name):</b> Specifies the version date/time of the data to retrieve (time series types only). Must be an [`HecTime`](hectime.html#HecTime) object or a valid input to the `HecTime` constructor.
                    Defaults to the None, which uses the data store's default vertical datum.
                * <b>vertical_datum (Optional[str], must be passed by name):</b> "NGVD29", "NAVD88", or "NATIVE", specifying the vertical datum to retrieve elevation data for. Defaults to None, which uses the data store's default vertical datum

        Returns:
            Any: The [`Location`](location.html#Location) or [`TimeSeries`](timeseries.html#TimeSeries) object
        """
        self._assert_open()
        if timeseries._is_cwms_tsid(identifier):
            return self._retrieve_time_series(identifier, **kwargs)
        if location._is_cwms_location(identifier):
            return self._retrieve_location(identifier, **kwargs)
        raise ValueError(f"Identifier {identifier} is not a recognized CWMS identifier")

    def store(self, obj: object, **kwargs: Any) -> None:
        """
        Stores a data set to the data store.

        Currently only locations and time series data may be stored.

        Args:
            obj (object): The data set to store.
                * For locations, must be a Location object or the name of the location
            Location Arguments:<br>
                * <b>name (Optional[str], must be passed by name):</b> The location's name, Defaults to the Location object's name
                * <b>office (Optional[str], must be passed by name):</b> The location's office. Defaults to the Location object's office
                * <b>kind (str, must be passed by name):</b> The location's kind. Must be on of:
                    * SITE
                    * EMBANKMENT
                    * OVERFLOW
                    * TURBINE
                    * STREAM
                    * PROJECT
                    * STREAMGAGE
                    * BASIN
                    * OUTLET
                    * LOCK
                    * GATE
                * <b>active (Optional[bool], must be passed by name):</b> Whether the location is active in the datbase. Defaults to True
                * <b>latitude (Optional[float], must be passed by name):</b> The location's latitude. Defaults to the Location object's latitude.
                * <b>longitude (Optional[float], must be passed by name):</b> The location's longitude. Defaults to the Location object's longitude
                * <b>horizontal_datum (Optional[str], must be passed by name):</b> The location's horizontal datum
                * <b>elevation (Optional[float], must be passed by name):</b> The location's elevation. Defaults to the Location object's elevation
                * <b>elevation_unit (Optional[str], must be passed by name):</b> The unit of the location's elevation. Defaults to the Location object's elevation unit
                * <b>vertical_datum (Optional[str], must be passed by name):</b> The location's vertical datum. Defaults to the location's vertical datum
                * <b>nation (Optional[str], must be passed by name):</b> The location's nation. Defaults to "US"
                * <b>state (Optional[str], must be passed by name):</b> The location's state. Defaults to None
                * <b>county (Optional[str], must be passed by name):</b> The locations's county. Defaults to None
                * <b>bounding_office (Optional[str], must be passed by name):</b> The CWMS office whose boundar includes the location. Defaults to None
                * <b>nearest_city (Optional[str], must be passed by name):</b> The city nearest the location. Defaults to None
                * <b>time_zone (Optional[str], must be passed by name):</b> The location's time zone. Defaults to the location's time zone
                * <b>public_name (Optional[str], must be passed by name):</b> The location's public name. Defaults to None
                * <b>long_name (Optional[str], must be passed by name):</b> The location's long name. Defaults to None
                * <b>description (Optional[str], must be passed by name):</b> The location's description. Defaults to None
                * <b>map_label (Optional[str], must be passed by name):</b> The location's map label. Defaults to None
                * <b>published_latitude (Optional[float], must be passed by name):</b> The published latitude of the location. Defaults to None
                * <b>published_longitude (Optional[float], must be passed by name):</b> The published longitude of the location. Defaults to None
                * <b>type (Optional[str], must be passed by name):</b> An unconstrained type for the location. Defaults to None
                <br>&nbsp;
                <div>The following items are required to be specified either in the Location object or arguments:
                    <ul>
                    <li>name</li>
                    <li>office</li>
                    <li>kind</li>
                    <li>latitude</li>
                    <li>longitude</li>
                    <li>horizontal_datum</li>
                    <li>time_zone</li>
                    </ul>
                </div>
                <p>
            TimeSeries Arguments:<br>
                * <b>as_lrts (Optional[bool], must be passed by name):</b> Specifies whether to store the time series as LRTS is its interval starts with "~". Defaults to whether the time series is a local regular time series
                * <b>override_protecteion (Optional[bool], must be passed by name):</b> Specifies whether to store non-protected values over existing protected values. (Protected values always overwrite existing values and non-protected existing values are alway overwritten) Defaults to False
                * <b>store_rule (Optional[str], must be passed by name):</b> Specifies the default behavior to use when storing data. If specified, it must be one of the following (case insensitive). Defaults to 'REPLACE_ALL'.
                    * <b>'DELETE_INSERT'</b> - delete all existing data in the incoming time window, then store the incoming data
                    * <b>'DO_NOT_REPLACE'</b> - store only non-existing data
                    * <b>'REPLACE_ALL'</b> - store existing and non-existing data
                    * <b>'REPLACE_MISSING_VALUES_ONLY'</b> - store incoming data only where existing data is missing
                    * <b>'REPLACE_WITH_NON_MISSING'</b> - store only non-missing incoming data
        """
        if isinstance(obj, TimeSeries):
            self._store_time_series(obj, **kwargs)
        elif isinstance(obj, Location):
            self._store_location(obj, **kwargs)
        else:
            raise TypeError(f"Expected TimeSeries, got {obj.__class__.__name__}")


if __name__ == "__main__":
    for pattern in [
        "abc",
        "ab{2,3}c{2}",
        "a*b?c",
        "[abc]",
        "^[abc]$",
        "[!abc]",
        "[_a-z0-9]",
        "[!a-z0-9]",
        "(abc|def)",
        "(OUTLET|TURBINE)",
    ]:
        print(f"{pattern} => {_pattern_to_regex(pattern)}")
