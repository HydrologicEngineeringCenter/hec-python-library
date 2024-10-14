"""
Provides location info
"""

import os
import sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

import warnings
from typing import Any, Optional, cast

warnings.filterwarnings("always", category=UserWarning)


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
        elevation: Optional[float] = None,
        elevation_unit: Optional[str] = None,
        horizontal_datum: Optional[str] = None,
        vertical_datum: Optional[str] = None,
    ):
        """
        Initializes a Location object

        Args:
            name (str): The location name
            office (str, optional): The office that owns the location, if applicable. Defaults to None.
            latitude (float, optional): The latitude of the location. Defaults to None.
            longitude (float, optional): The longitude of the location. Defaults to None.
            elevation (float, optional): The elevation of the location. Defaults to None.
            elevation_unit (str, optional): The unit of elevation of the location. Defaults to None.
            horizontal_datum (str, optional): The horizontal datum of the specified lat/lon. Defaults to None.
            vertical_datum (str, optional): The vertical datum of the specified elevation. Defaults to None.
        """
        self._name: str
        self._office: Optional[str]
        self._latitude: Optional[float]
        self._longitude: Optional[float]
        self._elevation: Optional[float]
        self._elevation_unit: Optional[str]
        self._horizontal_datum: Optional[str]
        self._vertical_datum: Optional[str]

        self.name = name
        self.office = office
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.elevation_unit = elevation_unit
        self.horizontal_datum = horizontal_datum
        self.vertical_datum = vertical_datum

    def __str__(self) -> str:
        if self.office:
            return f"{self.office}/{self.name}"
        else:
            return self.name

    def __repr__(self) -> str:
        s = f"Location(name='{self.name}'"
        if self.office is not None:
            s += f",office='{self.office}'"
        if self.latitude is not None:
            s += f",latitude={self.latitude}"
        if self.longitude is not None:
            s += f",longitude={self.longitude}"
        if self.elevation is not None:
            s += f",elevation={self.elevation}"
        if self.elevation_unit is not None:
            s += f",elevation_unit='{self.elevation_unit}'"
        if self.horizontal_datum is not None:
            s += f",horizontal_datum='{self.horizontal_datum}'"
        if self.vertical_datum is not None:
            s += f",vertical_datum='{self.vertical_datum}'"
        s += ")"
        return s

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
    def basename(self) -> str:
        """
        The name of the location up to any initial '-' character

        Operations:
            Read Only
        """
        return self._name.split("-", 1)[0]

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
    def elevation(self) -> Optional[float]:
        return self._elevation

    @elevation.setter
    def elevation(self, value: Optional[float]) -> None:
        """
        The elevation of the location

        Operations:
            Read/Write
        """
        self._elevation = None if value is None else float(value)

    @property
    def elevation_unit(self) -> Optional[str]:
        return self._elevation_unit

    @elevation_unit.setter
    def elevation_unit(self, value: Optional[str]) -> None:
        """
        The unit of the location's elevation

        Operations:
            Read/Write
        """
        self._elevation_unit = None if value is None else str(value)

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
    def vertical_datum(self) -> Optional[str]:
        """
        The vertical datum of the location's elevation

        Operations:
            Read/Write
        """
        return self._vertcal_datum

    @vertical_datum.setter
    def vertical_datum(self, value: Optional[str]) -> None:
        self._vertcal_datum = None if value is None else str(value)
