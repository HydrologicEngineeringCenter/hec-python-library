from abc import ABC, abstractmethod
from enum import Enum
from typing import cast, Any, Dict, List, Optional, Tuple
import re
from hec.hectime import HecTime
from hec import parameter
from hec.parameter import ElevParameter, Parameter
from hec.timeseries import TimeSeries
import pandas as pd
import tzlocal

try:
    import cwms  # type: ignore

    cwms_imported = True
except ImportError:
    cwms_imported = False


def pattern_to_regex(pattern: str) -> str:
    chars = ["^"]
    for c in pattern:
        if c == "*":
            chars.extend(".*")
        elif c == "?":
            chars.append(".")
        elif c in ".()+|^$@%{}=!<>&\\":
            chars.append("\\")
            chars.append(c)
        else:
            chars.append(c)
    chars.append("$")
    return "".join(chars)


class CwmsDataTypes(Enum):
    TIMESERIES = 1


class DssDataTypes(Enum):
    TIMESERIES = 1


class DataStoreException(Exception):
    pass


class DataStore(ABC):
    def __init__(self) -> None:
        self._description: Optional[str] = None
        self._init_data: Dict[str, Any]
        self._is_open: bool = False
        self._name: str
        self._office: Optional[str] = None
        self._read_only: bool = True
        self._time_window: Tuple[Optional[HecTime], Optional[HecTime]] = (None, None)
        self._time_zone: str = tzlocal.get_localzone_name()
        self._trim: bool = True
        self._unit_system: str = "EN"
        self._vertical_datum: Optional[str] = None

    def _init(self, **kwargs: Dict[str, Any]) -> None:
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
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'name', got {argval.__class__.__name__}"
                    )
                self._name = argval
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
            # ------------------- #
            # readonly (optional) #
            # ------------------- #
            if "read_only" in kwargs:
                argval = kwargs["read_only"]
                if isinstance(argval, bool):
                    self._read_only = argval
                elif isinstance(argval, str):
                    if argval.lower() not in ("true", "false"):
                        raise ValueError(
                            f"Expected 'True' or 'False' for 'read_only', got '{argval}'"
                        )
                    self._read_only = eval(argval.title())
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
            # --------------- #
            # trim (optional) #
            # --------------- #
            if "trim" in kwargs:
                argval = kwargs["trim"]
                if isinstance(argval, bool):
                    self._trim = argval
                elif isinstance(argval, str):
                    if argval.lower() not in ("true", "false"):
                        raise ValueError(
                            f"Expected 'True' or 'False' for 'trim', got '{argval}'"
                        )
                    self._trim = eval(argval.title())
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
                        self._vertical_datum = parameter._OTHER_DATUM

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='"
            + self._name
            + (f"', description='{self._description}')" if self._description else "')")
        )

    def __str__(self) -> str:
        return self._name + (f" ({self._description})" if self._description else "")

    @abstractmethod
    def catalog(
        self,
        data_type: Optional[str] = None,
        pattern: Optional[str] = None,
        regex: Optional[str] = None,
        case_sensitive: Optional[bool] = False,
        limit: Optional[int] = None,
        office: Optional[str] = None,
    ) -> List[str]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def delete(self, identifier: str, opts: Optional[Dict[str, Any]]) -> None:
        pass

    @property
    def end_time(self) -> Optional[HecTime]:
        return self._time_window[1]

    @end_time.setter
    def end_time(self, _end_time: Optional[HecTime]) -> None:
        self._time_window = (self._time_window[0], _end_time)

    @property
    def name(self) -> str:
        return self._name

    @property
    def office(self) -> Optional[str]:
        return self._office

    @office.setter
    def office(self, _office: str) -> None:
        self._office = _office

    @abstractmethod
    def open(self) -> bool:
        pass

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def is_read_only(self) -> bool:
        return self._read_only

    @is_read_only.setter
    def is_read_only(self, _read_only: bool) -> None:
        self._read_only = bool(_read_only)

    @abstractmethod
    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]] = None) -> Any:
        pass

    @property
    def start_time(self) -> Optional[HecTime]:
        return self._time_window[0]

    @start_time.setter
    def start_time(self, _start_time: Optional[HecTime]) -> None:
        self._time_window = (_start_time, self._time_window[1])

    @abstractmethod
    def store(self, obj: object, opts: Optional[Dict[str, Any]]) -> None:
        pass

    @property
    def time_window(self) -> Tuple[Optional[HecTime], Optional[HecTime]]:
        return self._time_window

    @time_window.setter
    def time_window(
        self, _time_window: Tuple[Optional[HecTime], Optional[HecTime]]
    ) -> None:
        self._time_window = _time_window

    @property
    def trim(self) -> bool:
        return self._trim

    @trim.setter
    def trim(self, _trim: bool) -> None:
        self._trim = bool(_trim)

    @property
    def units(self) -> str:
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


class DssDataStore(DataStore):
    def __init__(self, **kwargs: Dict[str, Any]):
        super().__init__()
        if "name" not in kwargs:
            raise DataStoreException("No name specified for data store.")
        self._init(**kwargs)

    def catalog(
        self,
        data_type: Optional[str] = None,
        pattern: Optional[str] = None,
        regex: Optional[str] = None,
        case_sensitive: Optional[bool] = False,
        limit: Optional[int] = None,
        office: Optional[str] = None,
    ) -> List[str]:
        # TODO: catalog file
        raise NotImplementedError("catalog method is not yet implemented")

    def close(self) -> None:
        # TODO: close DSS file
        self._is_open = False

    def delete(self, identifier: str, opts: Optional[Dict[str, Any]]) -> None:
        # TODO: delete data or data set
        raise NotImplementedError("delete method is not yet implemented")

    def open(self) -> bool:
        # TODO: check open DSS file
        self._is_open = True
        return self._is_open

    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]] = None) -> Any:
        # TODO: retrieve data set
        raise NotImplementedError("retrieve method is not yet implemented")

    def store(self, obj: object, opts: Optional[Dict[str, Any]] = None) -> None:
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        raise NotImplementedError("store method is not yet implemented")


class CwmsDataStore(DataStore):
    _api_root: Optional[str] = None
    _api_key: Optional[str] = None

    def __init__(self, **kwargs: Dict[str, Any]):
        super().__init__()
        self._init(**kwargs)
        if kwargs:
            argval: Any
            # ------------------- #
            # api_root (optional) #
            # ------------------- #
            if "api_root" in kwargs:
                argval = kwargs["api_root"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'api_root', got {argval.__class__.__name__}"
                    )
                self._api_root = argval
                self._name = argval
            # ------------------ #
            # api_key (optional) #
            # ------------------ #
            if "api_key" in kwargs:
                argval = kwargs["api_key"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'api_key', got {argval.__class__.__name__}"
                    )
                self._api_key = argval
        cwms.api.init_session(api_root=self._api_root, api_key=self._api_key)
        self._name = cwms.api.return_base_url()

    def catalog(
        self,
        data_type: Optional[str] = None,
        pattern: Optional[str] = None,
        regex: Optional[str] = None,
        case_sensitive: Optional[bool] = False,
        limit: Optional[int] = None,
        office: Optional[str] = None,
    ) -> List[str]:
        if not data_type:
            raise DataStoreException(
                f"Parameter data_type must be specified and must be one of {list(CwmsDataTypes.__members__)}"
            )
        if data_type.upper() not in CwmsDataTypes.__members__:
            raise DataStoreException(
                f"Invalid data type: '{data_type}', must be one of {list(CwmsDataTypes.__members__)}"
            )
        if not office and not self._office:
            raise DataStoreException(
                f"Office parameter must be specified since data store '{self}' has no default office"
            )
        _regex = regex if regex else pattern_to_regex(pattern) if pattern else None
        catalog_type = CwmsDataTypes[data_type.upper()]
        catalog_items: List[str]
        if catalog_type == CwmsDataTypes.TIMESERIES:
            data = cwms.get_timeseries_catalog(
                office_id=office if office else self._office,
                unit_system=self._unit_system,
                page_size=limit if limit else 5000,
                like=_regex,
            )
            catalog_items = data.df["name"].tolist()
            if not limit:
                while "next-page" in data.json and data.json["next-page"]:
                    data = cwms.get_timeseries_catalog(
                        office_id=office if office else self._office,
                        page=data.json["next-page"],
                        unit_system=self._unit_system,
                        page_size=5000,
                        like=_regex,
                    )
                    catalog_items.extend(data.df["name"].tolist())
        else:
            raise DataStoreException(f"Unexpected error with data type {data_type}")
        if catalog_items and _regex and case_sensitive:
            # API uses case insensitive matching
            pat = re.compile(_regex)
            catalog_items = list(filter(lambda s: pat.match(s), catalog_items))
        return catalog_items

    def close(self) -> None:
        self._is_open = False

    def delete(self, identifier: str, opts: Optional[Dict[str, Any]]) -> None:
        # TODO: retrieve data set
        raise NotImplementedError("delete method is not yet implemented")

    def open(self) -> bool:
        cwms.api.init_session(self._api_root, self._api_key)
        self._is_open = True
        return self._is_open

    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]] = None) -> Any:
        office = self._office
        time_window = self._time_window
        trim = self._trim
        unit_system = self._unit_system
        version_time = None
        vertical_datum = self._vertical_datum
        if opts:
            # -------- #
            # end_time #
            # -------- #
            if "end_time" in opts:
                time_window = (
                    time_window[0],
                    HecTime(opts["end_time"]),
                )
            # ------ #
            # office #
            # ------ #
            if "office" in opts:
                argval = opts["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                office = argval
            # ---------- #
            # start_time #
            # ---------- #
            if "start_time" in opts:
                time_window = (
                    HecTime(opts["start_time"]),
                    time_window[1],
                )
            # ---- #
            # trim #
            # ---- #
            if "trim" in opts:
                argval = opts["trim"]
                if isinstance(argval, bool):
                    trim = argval
                elif isinstance(argval, str):
                    if argval.lower() not in ("true", "false"):
                        raise ValueError(
                            f"Expected 'True' or 'False' for 'trim', got '{argval}'"
                        )
                    trim = eval(argval.title())
                else:
                    raise TypeError(
                        f"Expected bool or str for 'trim', got {argval.__class__.__name__}"
                    )
            # ----- #
            # units #
            # ----- #
            if "units" in opts:
                argval = opts["units"]
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
            if "version_time" in opts:
                version_time = HecTime(opts["version_time"])
            # -------------- #
            # vertical_datum #
            # -------------- #
            if "vertical_datum" in opts:
                argval = opts["vertical_datum"]
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
                        vertical_datum = parameter._OTHER_DATUM

        if time_window[0]:
            if not time_window[0].tzinfo:
                time_window[0].label_as_time_zone(self._time_zone)
        else:
            raise DataStoreException(
                f"Start time must be specified in opts parameter since data store '{self}' has no default start time"
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
        timeseries = TimeSeries(props["name"])
        timeseries.location.office = props["office-id"]
        timeseries._timezone = "UTC"
        if timeseries.parameter.base_parameter == "Elev":
            elev_param = ElevParameter(
                timeseries.parameter.name, props["vertical-datum-info"]
            )
            if elev_param.elevation:
                timeseries.location.elevation = elev_param.elevation.magnitude
                timeseries.location.elevation_unit = elev_param.elevation.specified_unit
            timeseries.location.vertical_datum = elev_param.native_datum
            timeseries.iset_parameter(elev_param)
        else:
            timeseries.iset_parameter(
                Parameter(timeseries.parameter.name, props["units"])
            )
        if df is not None and len(df):
            timeseries._data = data.df.copy(deep=True)
            cast(pd.DataFrame, timeseries._data).columns = pd.Index(
                ["time", "value", "quality"]
            )
            cast(pd.DataFrame, timeseries._data).set_index("time", inplace=True)
            timeseries._validate()
        timeseries.expand()
        timeseries.iconvert_to_time_zone(self._time_zone)
        return timeseries

    def store(self, obj: object, opts: Optional[Dict[str, Any]] = None) -> None:
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        # TODO: store data set
        raise NotImplementedError("store method is not yet implemented")
