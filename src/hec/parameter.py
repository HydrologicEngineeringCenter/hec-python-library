"""
Provides parameer info
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Optional
from typing import Union
from hec import unit
from hec.unit import UnitQuantity
from pint import Unit
import xml.etree.ElementTree as ET
import re

_ngvd29_pattern = re.compile("^ngvd.?29$", re.I)
_navd88_pattern = re.compile("^navd.?88$", re.I)
_other_datum_pattern = re.compile("^(local|other))$", re.I)
_all_datums_pattern = re.compile("^(ngvd.?29|navd.?88|local|other))$", re.I)

_parameter_info = {}
with open(os.path.join(os.path.dirname(__file__), "resources", "parameters.txt")) as f:
    for line in [
        line for line in f.read().strip().split("\n") if not line.startswith("#")
    ]:
        parts = line.split("\t")
        _parameter_info[parts[0]] = {
            "name": parts[1],
            "description": parts[2],
            "default_en_unit": parts[3],
            "default_si_unit": parts[4],
        }
_base_parameters = {}
for base_parameter in _parameter_info:
    _base_parameters[base_parameter.upper()] = base_parameter


class ParameterException(Exception):
    """
    Exception specific to Parameter operations
    """

    pass


class Parameter:
    """
    Holds info (name and unit) for a parameter
    """

    def __init__(self, name: str, unit_or_system: Optional[str] = None):
        """
        Initializer

        Args:
            name (str): The full parmeter name
            unit_or_system (Optional[str]):<br>
                * If `EN` or `None`, the default English unit for the base parameter will be assigned
                * if `SI`,  the default Système International unit for the base parameter will be assigned
                * Otherwise the specified unit will be assigned

        Raises:
            ParameterException: If the parameter name does not contain a valid base parameter name,
                or if the specified unit is not valid for the parameter
            KeyError: If the specified unit is not a valid unit name, alias or Pint unit definition
        """
        self._name: str
        self._base_parameter: str
        self._unit: str
        basename = name.split("-", 1)[0]
        if basename in _parameter_info:
            self._base_parameter = basename
            self._name = name
        else:
            basename = basename.upper()
            if basename in _base_parameters:
                self._base_parameter = _base_parameters[basename]
                self._name = name
            else:
                raise ParameterException(
                    f"{name} does not contain a recognized base parameter"
                )
        if unit_or_system:
            self.set_unit_or_system(unit_or_system)
        else:
            self._unit = _parameter_info[self._base_parameter]["default_en_unit"]

    def __repr__(self) -> str:
        return f"Parameter('{self._name}', '{self._unit}')"

    def __str__(self) -> str:
        return f"{self._name} ({self._unit})"

    @property
    def name(self) -> str:
        """
        The full name of the parameter as specified

        Operations:
            Read Only
        """
        return self._name

    @property
    def basename(self) -> str:
        """
        The name of the parameter as specified up to any initial '-' character

        Operations:
            Read Only
        """
        return self._name.split("-", 1)[0]

    @property
    def subname(self) -> Optional[str]:
        """
        The name of the parameter as specified after any initial '-' character

        Operations:
            Read Only
        """
        parts = self._name.split("-", 1)
        return None if len(parts) == 1 else parts[1]

    @property
    def base_parameter(self) -> str:
        """
        The actual base parameter used. Will be same as `basename` unless the
        parameter was created using a parameter alias

        Operations:
            Read Only
        """
        return self._base_parameter

    @property
    def unit(self) -> str:
        """
        The unit assigned to the parameter

        Operations:
            Read Only
        """
        return self._unit

    def set_unit_or_system(self, unit_or_system: str) -> None:
        """
        Assigns a unit to this parameter

        Args:
            unit_or_system (str):<br>
                * If `EN`, the default English unit for the base parameter will be assigned
                * if `SI`,  the default Système International unit for the base parameter will be assigned
                * Otherwise the specified unit will be assigned

        Raises:
            ParameterException: If the specified unit is not valid for the parameter
        """
        if unit_or_system.upper() == "EN":
            self._unit = _parameter_info[self._base_parameter]["default_en_unit"]
        elif unit_or_system.upper() == "SI":
            self._unit = _parameter_info[self._base_parameter]["default_si_unit"]
        else:
            unit_name = unit.get_unit_name(unit_or_system)
            if not unit_name in unit.get_compatible_units(
                _parameter_info[self._base_parameter]["default_en_unit"]
            ):
                raise ParameterException(
                    f"{unit_or_system} is not a vaild unit for base parameter {self._base_parameter}"
                )
            self._unit = unit_name


class ElevParameter(Parameter):

    class VerticalDatumException(ParameterException):
        pass

    class VerticalDatumInfo:
        def __init__(self, verticalDatumInfo: str):
            self._elevation: Optional[UnitQuantity] = None
            self._native_datum: Optional[str] = None
            self._current_datum: Optional[str] = None
            self._ngvd_29_offset: Optional[UnitQuantity] = None
            self._navd_88_offset: Optional[UnitQuantity] = None
            self._ngvd29_offset_is_estimate: Optional[bool] = None
            self._navd88_offset_is_estimate: Optional[bool] = None
            if verticalDatumInfo:
                root = ET.fromstring(verticalDatumInfo)
                elem = root.find("native-datum")
                if elem:
                    if _ngvd29_pattern.match(elem.text, re.I):
                        self._native_datum = "NGVD-29"
                    elif _navd88_pattern.match("^navd.?88$", elem.text, re.I):
                        self._native_datum = "NAVD-88"
                    elif _other_datum_pattern.match("^(local|other)$", elem.text, re.I):
                        self._native_datum = "OTHER"
                    else:
                        self._native_datum = elem.text
                    if self._native_datum == "OTHER":
                        elem = root.find("local-datum-name")
                        if elem:
                            self._native_datum = elem.text
                self._current_datum = self._native_datum
                if "unit" in root.attrib:
                    unit = root.attrib["unit"]
                    elem = root.find("elevation")
                    if elem:
                        self._elevation = UnitQuantity(
                            float(elem.text), root.attrib["unit"]
                        )
                    for elem in root.findall("offset"):
                        estimate = elem.attrib["estimate"] == "true"
                        if elem.find("to-dautm") and elem.find("value"):
                            datum = elem.find("to-datum").text
                            value = float(elem.find("value").text)
                            if datum == "NGVD-29":
                                self._ngvd_29_offset = unit.UnitQuantity(value, unit)
                                self._ngvd29_offset_is_estimate = estimate
                            elif datum == "NAVD-88":
                                self._navd_88_offset = unit.UnitQuantity(value, unit)
                                self._navd88_offset_is_estimate = estimate

        @property
        def elevation(self) -> Optional[UnitQuantity]:
            return self._elevation

        @property
        def native_datum(self) -> Optional[str]:
            return self._native_datum

        @property
        def current_datum(self) -> Optional[str]:
            return self._current_datum

        @property
        def ngvd_29_offset(self) -> Optional[UnitQuantity]:
            return self._ngvd_29_offset

        @property
        def navd_88_offset(self) -> Optional[UnitQuantity]:
            return self._navd_88_offset

        @property
        def ngvd_29_offset_is_estimate(self) -> Optional[bool]:
            return self._ngvd_29_offset_is_estimate

        @property
        def navd_88_offset_is_estimate(self) -> Optional[bool]:
            return self._navd_88_offset_is_estimate

        def clone(self) -> "ElevParameter.VerticalDatumInfo":
            other = ElevParameter.VerticalDatumInfo(None)
            other._elevation = self._elevation
            other._native_datum = self._native_datum
            other._current_datum = self._current_datum
            other._ngvd_29_offset = self._ngvd_29_offset
            other._navd_88_offset = self._navd_88_offset
            other._ngvd29_offset_is_estimate = self._ngvd29_offset_is_estimate
            other._navd88_offset_is_estimate = self._navd88_offset_is_estimate
            return other

        def get_offset_to(self, target_datum: str) -> Optional[UnitQuantity]:
            if _ngvd29_pattern.match(target_datum, re.I):
                if self.current_datum == "NGVD-29":
                    return None
                elif self.current_datum == "NAVD-88":
                    return self._ngvd_29_offset - self._navd_88_offset
                else:
                    return self._ngvd_29_offset
            elif _navd88_pattern.match(target_datum, re.I):
                if self.current_datum == "NAVD-88":
                    return None
                elif self.current_datum == "NGVD-29":
                    return self._navd_88_offset - self._ngvd_29_offset
                else:
                    return self._navd_88_offset
            elif (
                _other_datum_pattern.match(target_datum, re.I)
                or target_datum.upper() == self._native_datum.upper()
            ):
                if self.current_datum == "NGVD-29":
                    return -self._ngvd_29_offset
                elif self.current_datum == "NAVD-88":
                    return -self._navd_88_offset
                else:
                    return None
            else:
                raise ElevParameter.VerticalDatumException(
                    f"Invalid vertical datum:{target_datum}"
                )

        def to(
            self, unit_or_datum: Union[str, Unit], in_place: bool = False
        ) -> "ElevParameter.VerticalDatumInfo":
            converted = self if in_place else self.clone()
            if isinstance(unit_or_datum, Unit) or not (
                _all_datums_pattern.match(unit_or_datum)
                or unit_or_datum.upper() == self._native_datum.upper()
            ):
                if converted._elevation:
                    converted._elevation.ito(unit_or_datum)
                if converted._ngvd_29_offset:
                    converted._ngvd_29_offset.ito(unit_or_datum)
                if converted._navd_88_offset:
                    converted._navd_88_offset.ito(unit_or_datum)
            else:
                offset = converted.get_offset_to(unit_or_datum)
                if offset:
                    if converted._elevation:
                        converted._elevation += offset
                    if converted._ngvd_29_offset:
                        converted._ngvd_29_offset += offset
                    if converted._navd_88_offset:
                        converted._navd_88_offset += offset
            return converted

    def __init__(
        self,
        name: str,
        unit_or_system: Optional[str] = None,
        verticalDatumInfo: Optional[str] = None,
    ):
        super().__init__(name, unit_or_system)
        self._vertical_datum_info = (
            ElevParameter.VerticalDatumInfo(verticalDatumInfo)
            if verticalDatumInfo
            else None
        )

    @property
    def vertical_datum_info(self) -> Optional[VerticalDatumInfo]:
        return self._vertical_datum_info

    @property
    def elevation(self) -> Optional[UnitQuantity]:
        return (
            self._vertical_datum_info.elevation if self._vertical_datum_info else None
        )

    @property
    def native_datum(self) -> Optional[str]:
        return (
            self._vertical_datum_info.native_datum
            if self._vertical_datum_info
            else None
        )

    @property
    def current_datum(self) -> Optional[str]:
        return (
            self._vertical_datum_info.current_datum
            if self._vertical_datum_info
            else None
        )

    @property
    def ngvd_29_offset(self) -> Optional[UnitQuantity]:
        return (
            self._vertical_datum_info.ngvd_29_offset
            if self._vertical_datum_info
            else None
        )

    @property
    def navd_88_offset(self) -> Optional[UnitQuantity]:
        return (
            self._vertical_datum_info.navd_88_offset
            if self._vertical_datum_info
            else None
        )

    @property
    def ngvd_29_offset_is_estimate(self) -> Optional[bool]:
        return (
            self._vertical_datum_info.ngvd_29_offset_is_estimate
            if self._vertical_datum_info
            else None
        )

    @property
    def navd_88_offset_is_estimate(self) -> Optional[bool]:
        return (
            self._vertical_datum_info.navd_88_offset_is_estimate
            if self._vertical_datum_info
            else None
        )
