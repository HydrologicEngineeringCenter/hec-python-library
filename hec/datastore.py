from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from hec.hectime import HecTime

try:
    import cwms  # type: ignore

    cwms_imported = True
except ImportError:
    cwms_imported = False


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
        self._unit_system: str = "EN"

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
            # --------------- #
            # name (required) #
            # --------------- #
            if "name" in kwargs:
                argval = kwargs["name"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'name', got {argval.__class__.__name__}"
                    )
                self._name = argval
            else:
                raise DataStoreException("No name specified for data store.")
            # ----------------- #
            # office (optional) #
            # ----------------- #
            if "office" in kwargs:
                argval = kwargs["office"]
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                self._name = argval
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
                self._name = argval
            # --------------------- #
            # start_time (optional) #
            # --------------------- #
            if "start_time" in kwargs:
                self._time_window = (
                    HecTime(kwargs["start_time"]),
                    self._time_window[1],
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
                    self._unit_sytem = "SI"
                else:
                    raise ValueError(
                        f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{argval}'"
                    )
                self._name = argval

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}"
            + self._name
            + (f" ({self._description})" if self._description else "")
            + ">"
        )

    def __str__(self) -> str:
        return self._name + (f" ({self._description})" if self._description else "")

    @abstractmethod
    def catalog(
        self, pattern: Optional[str], regex: Optional[str], data_type: Optional[str]
    ) -> List[str]:
        pass

    @abstractmethod
    def close(self) -> None:
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
        self._read_only = _read_only

    @abstractmethod
    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]]) -> Any:
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
    def units(self) -> str:
        return self._unit_system

    @units.setter
    def units(self, _units: str) -> None:
        if _units.lower().startswith("en"):
            self._unit_system = "EN"
        elif _units.lower() in ("si", "metric"):
            self._unit_sytem = "SI"
        else:
            raise ValueError(
                f"Expected 'EN', 'English', 'SI', or 'metric' for units, got '{_units}'"
            )


class DssDataStore(DataStore):
    def __init__(self, **kwargs: Dict[str, Any]):
        super().__init__()
        self._init(**kwargs)

    def catalog(
        self, pattern: Optional[str], regex: Optional[str], data_type: Optional[str]
    ) -> List[str]:
        # TODO: catalog file
        return []

    def close(self) -> None:
        # TODO: close DSS file
        self._is_open = False

    def open(self) -> bool:
        # TODO: check open DSS file
        self._is_open = True
        return self._is_open

    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]]) -> Any:
        # TODO: retrieve data set
        pass

    def store(self, obj: object, opts: Optional[Dict[str, Any]] = None) -> None:
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        # TODO: store data set


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

    def catalog(
        self, pattern: Optional[str], regex: Optional[str], data_type: Optional[str]
    ) -> List[str]:
        # TODO: perform catalog catalog
        return []

    def close(self) -> None:
        self._is_open = False

    def open(self) -> bool:
        cwms.api.init_session(self._api_root, self._api_key)
        self._is_open = True
        return self._is_open

    def retrieve(self, identifier: str, opts: Optional[Dict[str, Any]]) -> Any:
        # TODO: retrieve data set
        pass

    def store(self, obj: object, opts: Optional[Dict[str, Any]] = None) -> None:
        if self._read_only:
            raise DataStoreException(
                f"Cannot store to {self._name}, data store is set to read-only"
            )
        # TODO: store data set
