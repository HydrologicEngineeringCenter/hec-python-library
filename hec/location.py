"""
Provides location info
"""

import re
import warnings
from enum import Enum
from io import StringIO
from typing import Any, Optional, Union, cast

import numpy as np

import hec
from hec.parameter import (
    _NAVD88,
    _NGVD29,
    _OTHER_DATUM,
    _all_datums_pattern,
    _navd88_pattern,
    _ngvd29_pattern,
)
from hec.unit import UnitQuantity

warnings.filterwarnings("always", category=UserWarning)

_loc_pat = re.compile("^[^.-]{1,24}(-[^.]{1,32})?$")


def _is_cwms_location(id: str) -> bool:
    return bool(_loc_pat.match(id))


class KIND(Enum):
    SITE = 1
    STREAM = 2
    BASIN = 3
    PROJECT = 4
    EMBANKMENT = 5
    OUTLET = 6
    TURBINE = 7
    LOCK = 8
    STREAM_LOCATION = 9
    GATE = 10
    OVERFLOW = 11
    STREAM_GAGE = 12
    STREAM_REACH = 13
    PUMP = 14
    WEATHER_GAGE = 15
    ENTITY = 16


class LocationException(Exception):
    """
    Exception specific to Location operations
    """

    pass


class Location:
    """
    Holds information about locations
    """

    def __init__(
        self,
        name: str,
        office: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        horizontal_datum: Optional[str] = None,
        elevation: Optional[float] = None,
        elevation_unit: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        time_zone: Optional[str] = None,
        kind: Optional[str] = None,
        vertical_datum_info: Optional[Union[str, dict[str, Any]]] = None,
    ):
        """
        Initializes a Location object

        Args:
            name (str): The location name
            office (Optional[str]): The office that owns the location, if applicable. Defaults to None.
            latitude (Optional[float]): The latitude of the location. Defaults to None.
            longitude (Optional[float]): The longitude of the location. Defaults to None.
            horizontal_datum (Optional[str]): The horizontal datum of the specified lat/lon. Defaults to None.
            elevation (Optional[float]): The elevation of the location. Defaults to None.
            elevation_unit (Optional[str]): The unit of elevation of the location. Defaults to None.
            vertical_datum (Optional[str]): The native vertical datum of the specified elevation. Defaults to None.
            vertical_datum_info (Optional[Union[str, dict[str,Any]]]): The vertical datum info for the location. Overrides `elevation`, `elevation_unit`, and `vertical_datum` parameters, if also specified. Defaults to None.
        """
        self._name: str = name
        self._office: Optional[str] = office
        self._latitude: Optional[float] = latitude
        self._longitude: Optional[float] = longitude
        self._horizontal_datum: Optional[str] = horizontal_datum
        self._elevation: Optional[UnitQuantity] = None
        self._vertical_datum: Optional[str] = None
        self._time_zone: Optional[str] = None
        self._kind: Optional[KIND] = None
        self._vertical_datum_info: Optional[
            hec.parameter.ElevParameter._VerticalDatumInfo
        ] = None
        if elevation and elevation_unit:
            self._elevation = UnitQuantity(elevation, elevation_unit)
        if vertical_datum is not None:
            if _all_datums_pattern.match(vertical_datum):
                if _navd88_pattern.match(vertical_datum):
                    self._vertical_datum = _NAVD88
                elif _ngvd29_pattern.match(vertical_datum):
                    self._vertical_datum = _NGVD29
                else:
                    self._vertical_datum = _OTHER_DATUM
            else:
                self._vertical_datum = vertical_datum
        if time_zone is not None:
            try:
                self._time_zone = str(
                    hec.hectime.HecTime.now()
                    .convert_to_time_zone(time_zone, on_tz_not_set=0)
                    .tzinfo
                )
            except:
                raise LocationException(f"Invalid time zone: {time_zone}")
        if kind is None or kind.strip() == "":
            self._kind = None
        else:
            if kind.upper() in KIND.__members__:
                self._kind = KIND[kind.upper()]
            else:
                raise LocationException(
                    f"Invalid kind: {kind.upper()}, must be one of {','.join(KIND.__members__)}"
                )
        if vertical_datum_info is not None:
            self._vertical_datum_info = hec.parameter.ElevParameter._VerticalDatumInfo(
                vertical_datum_info
            )
        vdi = self._vertical_datum_info
        if vdi:
            if vdi.elevation and self._elevation:
                if not np.isclose(
                    self._elevation.to(vdi.elevation.unit).magnitude,
                    vdi.elevation.magnitude,
                ):
                    warnings.warn(
                        f"Vertical datum info elevation of {vdi.elevation} overrides parameters of {elevation} and {elevation_unit}",
                        UserWarning,
                    )
            if (
                vdi.native_datum
                and vertical_datum
                and vdi.native_datum != vertical_datum
            ):
                warnings.warn(
                    f"Vertical datum info native datum of {vdi.native_datum} overrides parameter of {vertical_datum}",
                    UserWarning,
                )

    def __repr__(self) -> str:
        s = f"Location(name='{self.name}'"
        if self.office is not None:
            s += f",office='{self.office}'"
        if self.latitude is not None:
            s += f",latitude={self.latitude}"
        if self.longitude is not None:
            s += f",longitude={self.longitude}"
        if self.horizontal_datum is not None:
            s += f",horizontal_datum='{self.horizontal_datum}'"
        if not self.vertical_datum_info and self.elevation is not None:
            s += f",elevation={float(self.elevation.magnitude)}"  # prevent truncating .0 in output
            s += f",elevation_unit='{self.elevation.specified_unit}'"
            if self.vertical_datum is not None:
                s += f",vertical_datum='{self.vertical_datum}'"
        if self._time_zone is not None:
            s += f",time_zone='{self._time_zone}'"
        if self._kind is not None:
            s += f",kind='{self._kind.name}'"
        if self.vertical_datum_info is not None:
            s += f",vertical_datum_info='{self.vertical_datum_json}'"
        s += ")"
        return s

    def __str__(self) -> str:
        if self.office:
            return f"{self.office}/{self.name}"
        else:
            return self.name

    @property
    def basename(self) -> str:
        """
        The name of the location up to any initial '-' character

        Operations:
            Read Only
        """
        return self._name.split("-", 1)[0]

    @property
    def elevation(self) -> Optional[UnitQuantity]:
        """
        The elevation of the location

        Operations:
            Read/Write
        """
        if self._vertical_datum_info:
            return self._vertical_datum_info.elevation
        if self._elevation:
            return self._elevation
        else:
            return None

    @elevation.setter
    def elevation(self, value: Optional[UnitQuantity]) -> None:
        if self._vertical_datum_info is not None:
            raise LocationException(
                "Cannot directly set the elevation of a location with vertical datum information"
            )
        self._elevation = None if value is None else value

    @property
    def horizontal_datum(self) -> Optional[str]:
        """
        The horizontal datum of the location's latitude/longitude

        Operations:
            Read/Write
        """
        return self._horizontal_datum

    @horizontal_datum.setter
    def horizontal_datum(self, value: Optional[str]) -> None:
        self._horizontal_datum = None if value is None else str(value)

    @property
    def kind(self) -> Optional[str]:
        """
        The kind of the location

        Operations:
            Read/Write
        """
        return None if self._kind is None else self._kind.name

    @kind.setter
    def kind(self, value: Optional[str]) -> None:
        if value is None or value.strip() == "":
            self._kind = None
        else:
            if value.upper() in KIND.__members__:
                self._kind = KIND[value.upper()]
            else:
                raise LocationException(
                    f"Invalid kind: {value.upper()}, must be one of {','.join(KIND.__members__)}"
                )

    @property
    def latitude(self) -> Optional[float]:
        """
        The latitude of the location

        Operations:
            Read/Write
        """
        return self._latitude

    @latitude.setter
    def latitude(self, value: Optional[float]) -> None:
        if value is None:
            self._latitude = None
        else:
            v = float(value)
            if not -90 <= v <= 90:
                raise LocationException(f"Latitude of {v} is invalid")
            self._latitude = v

    @property
    def longitude(self) -> Optional[float]:
        """
        The longitude of the location

        Operations:
            Read/Write
        """
        return self._longitude

    @longitude.setter
    def longitude(self, value: Optional[float]) -> None:
        if value is None:
            self._longitude = None
        else:
            v = float(value)
            if not -180 <= v <= 180:
                raise LocationException(f"Longitude of {v} is invalid")
            self._longitude = v

    @property
    def name(self) -> str:
        """
        The full name of the location

        Operations:
            Read/Write
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        v = str(value)
        for c in "./\\,;'\"`":
            if c in v:
                warnings.warn(
                    f'Location name "{v}" contains the character "{c}" and may not be usable in all contexts',
                    UserWarning,
                )
        for c in value:
            if not c.isascii():
                warnings.warn(
                    f'Location name "{v}" contains the character "{c}" ({ord(c)}, 0x{ord(c):x})'
                    + " and may not be usable in all contexts",
                    UserWarning,
                )
        self._name = v

    @property
    def office(self) -> Optional[str]:
        """
        The office that owns the location

        Operations:
            Read/Write
        """
        return self._office

    @office.setter
    def office(self, value: Optional[str]) -> None:
        if value is None:
            self._office = None
        else:
            v = str(value)
            for c in v:
                if not c.isascii():
                    warnings.warn(
                        f'Location office "{v}" contains the character "{c}" ({ord(c)}, 0x{ord(c):x})'
                        + " and may not be usable in all contexts",
                        UserWarning,
                    )
            self._office = v

    @property
    def subname(self) -> Optional[str]:
        """
        The name of the location after any initial '-' character

        Operations:
            Read Only
        """
        parts = self._name.split("-", 1)
        return None if len(parts) == 1 else parts[1]

    @property
    def time_zone(self) -> Optional[str]:
        """
        The time zone of the location

        Operations:
            Read/Write
        """
        return self._time_zone

    @time_zone.setter
    def time_zone(self, value: Optional[str]) -> None:
        if value is None:
            self._time_zone = None
        else:
            try:
                self._time_zone = str(
                    hec.hectime.HecTime.now()
                    .convert_to_time_zone(value, on_tz_not_set=0)
                    .tzinfo
                )
            except:
                raise LocationException(f"Invalid time zone: {value}")

    @property
    def vertical_datum(self) -> Optional[str]:
        """
        The native vertical datum of the location's elevation

        Operations:
            Read/Write
        """
        return (
            self._vertical_datum
            if self._vertical_datum_info is None
            else self._vertical_datum_info.native_datum
        )

    @vertical_datum.setter
    def vertical_datum(self, value: Optional[str]) -> None:
        if self._vertical_datum_info:
            raise LocationException(
                "Cannot directly set native vertical datum on a location with vertical datum information"
            )
        if value is None:
            self._vertical_datum = None
        elif _all_datums_pattern.match(value):
            if _navd88_pattern.match(value):
                self._vertical_datum = _NAVD88
            elif _ngvd29_pattern.match(value):
                self._vertical_datum = _NGVD29
            else:
                self._vertical_datum = _OTHER_DATUM
        else:
            self._vertical_datum = value

    @property
    def vertical_datum_info(
        self,
    ) -> Optional[hec.parameter.ElevParameter._VerticalDatumInfo]:
        """
        The vertical datum information for the location.
            * The getter returns a _VerticalDatumInfo object.
            * The setter accepts _VerticalDatumInfo objects


        Operations:
            Read/Write
        """
        return self._vertical_datum_info

    @vertical_datum_info.setter
    def vertical_datum_info(self, value: Optional[Any]) -> None:
        if value is None:
            self._vertical_datum_info = None
        elif isinstance(value, hec.parameter.ElevParameter._VerticalDatumInfo):
            self._vertical_datum_info = value.clone()
        elif isinstance(value, dict):
            s = re.sub(r"\b(True|False)\b", lambda m: m.group(0).lower(), str(value))
            self._vertical_datum_info = hec.parameter.ElevParameter._VerticalDatumInfo(
                s
            )
        elif isinstance(value, str):
            self._vertical_datum_info = hec.parameter.ElevParameter._VerticalDatumInfo(
                value
            )
        else:
            raise TypeError(
                f"Expected str or ElevParameter._VerticalDatumInfo, got {value.__class__.__name__}"
            )

    @property
    def vertical_datum_json(self) -> Optional[str]:
        vdi = self._vertical_datum_info
        if vdi:
            buf = StringIO()
            buf.write(f'{{"office":"{self.office}","location":"{self.name}",')
            if vdi.elevation:
                buf.write(
                    f'"elevation":{vdi.elevation.magnitude},"unit":"{vdi.elevation.specified_unit}",'
                )
            else:
                buf.write(f'"elevation":null,"unit":"null",')
            buf.write(f'"native-datum":"{vdi.native_datum}",')
            if vdi.navd88_offset or vdi.ngvd29_offset:
                buf.write('"offsets":[')
                if vdi.navd88_offset:
                    buf.write(
                        f'{{"to-datum":"{_NAVD88}","value":{vdi.navd88_offset.magnitude},"estimate":"{"true" if vdi.navd88_offset_is_estimate else "false"}"}}'
                    )
                if vdi.ngvd29_offset:
                    if vdi.navd88_offset:
                        buf.write(",")
                    buf.write(
                        f'{{"to-datum":"{_NGVD29}","value":{vdi.ngvd29_offset.magnitude},"estimate":{"true" if vdi.ngvd29_offset_is_estimate else "false"}}}'
                    )
                buf.write("]")
            buf.write("}")
            json = buf.getvalue()
            buf.close()
            return json
        else:
            return None

    @property
    def vertical_datum_xml(self) -> Optional[str]:
        vdi = self._vertical_datum_info
        if vdi:
            lines = str(self._vertical_datum_info).split("\n")
            buf = StringIO()
            buf.write(f'<vertical-datum-info office="{self.office}" ')
            if vdi.elevation:
                buf.write(f'unit="{vdi.elevation.specified_unit}">\n')
            else:
                buf.write('"unit=""\n')
            buf.write(f"  <location>{self.name}</location>\n")
            buf.write("\n".join(lines[1:]))
            xml = buf.getvalue()
            buf.close()
            return xml
        else:
            return None
