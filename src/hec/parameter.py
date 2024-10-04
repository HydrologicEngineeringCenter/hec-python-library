"""
Provides parameer info
"""

import os, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from typing import Any
from typing import Optional
from typing import Union
from hec import unit
from hec.unit import UnitQuantity
from pint import Unit
from io import StringIO
import xml.etree.ElementTree as ET
import re

_NGVD29 = "NGVD-29"
_NAVD88 = "NAVD-88"
_OTHER_DATUM = "OTHER"

_ngvd29_pattern = re.compile("^ngvd.?29$", re.I)
_navd88_pattern = re.compile("^navd.?88$", re.I)
_other_datum_pattern = re.compile("^(local|other)$", re.I)
_all_datums_pattern = re.compile("^(ngvd.?29|navd.?88|local|other)$", re.I)

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
            Parameter.to(self, unit_or_system, in_place=True) # don't use to() method in sublcass when instantiating from subclass
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

    def to(self, unit_or_system: str, in_place: bool = False) -> "Parameter":
        """
        Assigns a unit to this parameter or a copy of this parameter

        Args:
            unit_or_system (str):<br>
                * If `EN`, the default English unit for the base parameter will be assigned
                * if `SI`,  the default Système International unit for the base parameter will be assigned
                * Otherwise the specified unit will be assigned

        Raises:
            ParameterException: If the specified unit is not valid for the parameter

        Returns:
            Parameter: The converted object (self if in_place == True, otherwise a converted copy)
        """
        converted = self if in_place else Parameter(self.name)
        if unit_or_system.upper() == "EN":
            converted._unit = _parameter_info[converted._base_parameter]["default_en_unit"]
        elif unit_or_system.upper() == "SI":
            converted._unit = _parameter_info[converted._base_parameter]["default_si_unit"]
        else:
            unit_name = unit.get_unit_name(unit_or_system)
            if not unit_name in unit.get_compatible_units(
                _parameter_info[self._base_parameter]["default_en_unit"]
            ):
                raise ParameterException(
                    f"{unit_or_system} is not a vaild unit for base parameter {self._base_parameter}"
                )
            converted._unit = unit_name
        return converted
    
    def get_compatible_units(self) -> list[str]:
        return unit.get_compatible_units(self.unit)


class ElevParameter(Parameter):

    class VerticalDatumException(ParameterException):
        pass

    class VerticalDatumInfo:
        def __init__(self, verticalDatumInfo: Union[str, dict[str, Any]]):
            self._unit_str: str
            self._unit: Unit
            self._elevation: Optional[UnitQuantity] = None
            self._native_datum: Optional[str] = None
            self._current_datum: Optional[str] = None
            self._ngvd29_offset: Optional[UnitQuantity] = None
            self._navd88_offset: Optional[UnitQuantity] = None
            self._ngvd29_offset_is_estimate: Optional[bool] = None
            self._navd88_offset_is_estimate: Optional[bool] = None
            if verticalDatumInfo:
                if isinstance(verticalDatumInfo, dict) :
                    # --------------------------------------------- #
                    # dictionary as from cwms-python get_timeseries #
                    # --------------------------------------------- #
                    if "unit" in verticalDatumInfo:
                        self._unit_str = verticalDatumInfo["unit"]
                        self._unit = unit.get_pint_unit(self._unit_str)
                    else:
                        raise ElevParameter.VerticalDatumException(
                            f"No unit in dictionary"
                        )
                    if "native-datum" in verticalDatumInfo:
                        text = verticalDatumInfo["native-datum"]
                        if _ngvd29_pattern.match(text):
                            self._native_datum = _NGVD29
                        elif _navd88_pattern.match(text):
                            self._native_datum = _NAVD88
                        elif _other_datum_pattern.match(text):
                            self._native_datum = _OTHER_DATUM
                        else:
                            self._native_datum = text
                        if self._native_datum == _OTHER_DATUM:
                            elem = root.find("local-datum-name")
                            if elem is not None:
                                self._native_datum = elem.text
                    if "elevation" in verticalDatumInfo:
                        self._elevation = UnitQuantity(verticalDatumInfo["elevation"], self._unit)
                elif isinstance(verticalDatumInfo, str) :
                    # ------------------------------------- #
                    # XML string as from CWMS db or HEC-DSS #
                    # ------------------------------------- #
                    root = ET.fromstring(verticalDatumInfo)
                    if root.tag != "vertical-datum-info":
                        raise ElevParameter.VerticalDatumException(
                            f"Expected root element of <vertical-datum-info>, got <{root.tag}>"
                        )
                    if "unit" in root.attrib:
                        self._unit_str = root.attrib["unit"]
                        self._unit = unit.get_pint_unit(self._unit_str)
                    else:
                        raise ElevParameter.VerticalDatumException(
                            f"No unit attribute on root element"
                        )
                    elem = root.find("native-datum")
                    if elem is not None and elem.text:
                        if _ngvd29_pattern.match(elem.text):
                            self._native_datum = _NGVD29
                        elif _navd88_pattern.match(elem.text):
                            self._native_datum = _NAVD88
                        elif _other_datum_pattern.match(elem.text):
                            self._native_datum = _OTHER_DATUM
                        else:
                            self._native_datum = elem.text
                        if self._native_datum == _OTHER_DATUM:
                            elem = root.find("local-datum-name")
                            if elem is not None:
                                self._native_datum = elem.text
                    self._current_datum = self._native_datum
                    elem = root.find("elevation")
                    if elem is not None and elem.text:
                        self._elevation = UnitQuantity(float(elem.text), self._unit)
                    for elem in root.findall("offset"):
                        estimate = elem.attrib["estimate"] == "true"
                        datum_elem = elem.find("to-datum")
                        value_elem = elem.find("value")
                        if datum_elem is not None and datum_elem.text and value_elem is not None and value_elem.text:
                            datum = datum_elem.text
                            value = float(value_elem.text)
                            if datum == _NGVD29:
                                self._ngvd29_offset = unit.UnitQuantity(value, self._unit)
                                self._ngvd29_offset_is_estimate = estimate
                            elif datum == _NAVD88:
                                self._navd88_offset = unit.UnitQuantity(value, self._unit)
                                self._navd88_offset_is_estimate = estimate

        @property
        def unit_str(self) -> str:
            return self._unit_str

        @property
        def unit(self) -> Unit:
            return self._unit

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
            return self._ngvd29_offset

        @property
        def navd_88_offset(self) -> Optional[UnitQuantity]:
            return self._navd88_offset

        @property
        def ngvd_29_offset_is_estimate(self) -> Optional[bool]:
            return self._ngvd29_offset_is_estimate

        @property
        def navd_88_offset_is_estimate(self) -> Optional[bool]:
            return self._navd88_offset_is_estimate

        def clone(self) -> "ElevParameter.VerticalDatumInfo":
            other = ElevParameter.VerticalDatumInfo("")
            other._elevation = self._elevation
            other._native_datum = self._native_datum
            other._current_datum = self._current_datum
            other._ngvd29_offset = self._ngvd29_offset
            other._navd88_offset = self._navd88_offset
            other._ngvd29_offset_is_estimate = self._ngvd29_offset_is_estimate
            other._navd88_offset_is_estimate = self._navd88_offset_is_estimate
            return other

        def __str__(self) -> str:
            buf = StringIO()
            buf.write(f'<vertical-datum-info unit="{self._unit_str}">')
            if self._native_datum in (_NGVD29, _NAVD88, _OTHER_DATUM):
                buf.write(f"\n  <native-datum>{self._native_datum}</native-datum>")
            else:
                buf.write(f"\n  <native-datum>OTHER</native-datum>")
                buf.write(
                    f"\n  <local-datum-name>{self._native_datum}</local-datum-name>"
                )
            if self._elevation is not None:
                buf.write(f"\n  <elevation>{self._elevation.magnitude}</elevation>")
            if self._ngvd29_offset is not None:
                buf.write(
                    f'\n  <offset estimate="{"true" if self._ngvd29_offset_is_estimate else "false"}">'
                )
                buf.write("\n    <to-datum>NGVD-29</to-datum>")
                buf.write(
                    f"\n    <value>{self._ngvd29_offset.magnitude}</value>"
                )
                buf.write("\n  </offset>")
            if self._navd88_offset is not None:
                buf.write(
                    f'\n  <offset estimate="{"true" if self._navd88_offset_is_estimate else "false"}">'
                )
                buf.write("\n    <to-datum>NAVD-88</to-datum>")
                buf.write(
                    f"\n    <value>{self._navd88_offset.magnitude}</value>"
                )
                buf.write("\n  </offset>")
            buf.write("\n</vertical-datum-info>")
            s = buf.getvalue()
            buf.close()
            return s

        def get_datum(self, datum_str: str) -> str:
            if _ngvd29_pattern.match(datum_str):
                return _NGVD29
            elif _navd88_pattern.match(datum_str):
                return _NAVD88
            elif (
                _other_datum_pattern.match(datum_str)
                or self._native_datum and (datum_str.upper() == self._native_datum.upper())
            ):
                if not self.native_datum or not self._native_datum in (_NGVD29, _NAVD88):
                    raise ElevParameter.VerticalDatumException(
                        f"Invalid vertical datum:{datum_str}"
                    )
                return self._native_datum
            else:
                raise ElevParameter.VerticalDatumException(
                    f"Invalid vertical datum:{datum_str}"
                )

        def get_offset_to(self, target_datum: str) -> Optional[UnitQuantity]:
            target_datum = self.get_datum(target_datum)
            if target_datum == self._current_datum:
                return None
            if target_datum == _NGVD29:
                if self.current_datum == _NAVD88:
                    if self._ngvd29_offset is None or self._navd88_offset is None:
                        return None
                    return self._ngvd29_offset - self._navd88_offset
                else:
                    return self._ngvd29_offset
            elif target_datum == _NAVD88:
                if self.current_datum == _NGVD29:
                    if self._ngvd29_offset is None or self._navd88_offset is None:
                        return None
                    return self._navd88_offset - self._ngvd29_offset
                else:
                    return self._navd88_offset
            else:
                if self.current_datum == _NGVD29:
                    return -self._ngvd29_offset if self._ngvd29_offset is not None else None
                elif self.current_datum == _NAVD88:
                    return -self._navd88_offset if self._navd88_offset is not None else None
                else:
                    raise ElevParameter.VerticalDatumException(
                        f"Cannot determine offset to {target_datum}"
                    )

        def to(
            self, unit_or_datum: Union[str, Unit], in_place: bool = False
        ) -> "ElevParameter.VerticalDatumInfo":
            converted = self if in_place else self.clone()
            if isinstance(unit_or_datum, Unit) or not (
                _all_datums_pattern.match(unit_or_datum)
                or (self._native_datum and unit_or_datum.upper() == self._native_datum.upper())
            ):
                # ---------------------- #
                # convert to target unit #
                # ---------------------- #
                if isinstance(unit_or_datum, Unit):
                    converted._unit = unit_or_datum
                    converted._unit_str = str(unit)
                else:
                    converted._unit_str = unit_or_datum
                    converted._unit = unit.get_pint_unit(converted._unit_str)
                if converted._elevation:
                    converted._elevation.ito(converted._unit_str)
                if converted._ngvd29_offset:
                    converted._ngvd29_offset.ito(converted._unit_str)
                if converted._navd88_offset:
                    converted._navd88_offset.ito(converted._unit_str)
            else:
                # ----------------------- #
                # convert to target datum #
                # ----------------------- #
                target_datum = self.get_datum(unit_or_datum)
                offset = converted.get_offset_to(target_datum)
                if offset:
                    offset = offset.to(self._unit_str)
                    if converted._elevation:
                        converted._elevation += offset
                    if converted._ngvd29_offset:
                        converted._ngvd29_offset += offset
                    if converted._navd88_offset:
                        converted._navd88_offset += offset
                converted._current_datum = target_datum
            return converted

    def __init__(
        self,
        name: str,
        verticalDatumInfo: str,
    ):
        _verticalDatumInfo = ElevParameter.VerticalDatumInfo(verticalDatumInfo)
        super().__init__(name, _verticalDatumInfo.unit_str)
        self._vertical_datum_info = _verticalDatumInfo

    def clone(self) -> "ElevParameter":
        return ElevParameter(self._name, str(self._vertical_datum_info))

    def __repr__(self) -> str:
        return f"ElevParameter('{self.name}', <vertical-datum-info>)"
    
    def __str__(self) -> str:
        return f"{self.name} (<vertical-datum-info>)"

    @property
    def unit(self) -> str:
        return self._vertical_datum_info._unit_str

    @property
    def vertical_datum_info(self) -> Optional[VerticalDatumInfo]:
        return self._vertical_datum_info

    @property
    def elevation(self) -> Optional[UnitQuantity]:
        return self._vertical_datum_info.elevation

    @property
    def native_datum(self) -> Optional[str]:
        return self._vertical_datum_info.native_datum

    @property
    def current_datum(self) -> Optional[str]:
        return self._vertical_datum_info.current_datum

    @property
    def ngvd_29_offset(self) -> Optional[UnitQuantity]:
        return self._vertical_datum_info.ngvd_29_offset

    @property
    def navd_88_offset(self) -> Optional[UnitQuantity]:
        return self._vertical_datum_info.navd_88_offset

    @property
    def ngvd_29_offset_is_estimate(self) -> Optional[bool]:
        return self._vertical_datum_info.ngvd_29_offset_is_estimate

    @property
    def navd_88_offset_is_estimate(self) -> Optional[bool]:
        return self._vertical_datum_info.navd_88_offset_is_estimate

    def get_offset_to(self, target_datum: str) -> Optional[UnitQuantity]:
        return self.vertical_datum_info.get_offset_to(target_datum)

    def to(
        self, unit_or_datum: Union[str, Unit], in_place: bool = False
    ) -> "ElevParameter":
        converted = self if in_place else self.clone()
        converted._vertical_datum_info.to(unit_or_datum, in_place=True)
        converted._unit = converted.vertical_datum_info.unit_str
        return converted

xml = """
        <vertical-datum-info unit="ft">
        <native-datum>OTHER</native-datum>
        <local-datum-name>Pensacola</local-datum-name>
        <elevation>757</elevation>
        <offset estimate="true">
            <to-datum>NAVD-88</to-datum>
            <value>1.457</value>
        </offset>
        <offset estimate="false">
            <to-datum>NGVD-29</to-datum>
            <value>1.07</value>
        </offset>
        </vertical-datum-info>
        """
p = ElevParameter("Elev", xml)
p2 = p.to("NAVD-88")
print(p2.current_datum)