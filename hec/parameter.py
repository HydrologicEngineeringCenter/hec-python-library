"""
Provides parameter info and operations

Comprises the classes:
* [Parameter](#Parameter)
* [ElevParameter](#ElevParameter)
* [ParameterType](#ParameterType)

<a name="base_parameter_definitions"></a>
**Base Parameter Definitions**
The tab separated variable file `resources/base_parameters.tsv` in this module's installation provides the following information about base parameters.
<table>
<tr><th>Field No.</th><th>Content</th><th>Type</th><th>Notes</th></tr>
<tr><td>1</td><td>Base Parameter Identifier</td><td>String</td><td>Required</td></tr>
<tr><td>2</td><td>Long Name</td><td>String</td><td>Required</td></tr>
<tr><td>3</td><td>Description</td><td>String</td><td>Required</td></tr>
<tr><td>4</td><td>Default English Unit</td><td>String</td><td>Required</td></tr>
<tr><td>5</td><td>Default SI Unit</td><td>String</td><td>Required</td></tr>
<tr><td>6</td><td>Parameter is Accumuatable Over Time</td><td>Boolean</td><td>Required</td></tr>
<tr><td>7</td><td>Integrated Base Parameter</td><td>String</td><td>Optional. Base Parameter of integrating the base parameter in Field 1 over time</td></tr>
<tr><td>8</td><td>Differentiated Base Parameter</td><td>String</td><td>Optional. Base Parameter of differentiating the base parameter in Field 1 with respect to time</td></tr>
<tr><td>9</td><td>English Differentiation Conversion Factor</td><td>Numeric</td><td>Required if Field 8 is present. Factor to convert:
    <ul>
    <li><b>From</b> standard English unit of dividing the base parameter in Field 1 by a number of seconds</li>
    <li><b>To</b> the standard English unit of the base parameter in Field 8</li>
    </ul></td></tr>
<tr><td>10</td><td>SI Differentiation Conversion Factor</td><td>Numeric</td><td>Required if Field 8 is present. Factor to convert:
    <ul>
    <li><b>From</b> standard SI unit of dividing the base parameter in Field 1 by a number of seconds</li>
    <li><b>To</b> the standard SI unit of the base parameter in Field 8</li>
    </ul></td></tr>
</table>
"""

import os
import re
import xml.etree.ElementTree as ET
from io import StringIO
from typing import Any, List, Optional, Union, cast

from pint import Unit

from hec import unit
from hec.unit import UnitQuantity

_NGVD29 = "NGVD-29"
_NAVD88 = "NAVD-88"
_OTHER_DATUM = "OTHER"

_ngvd29_pattern = re.compile("^ngvd.?29$", re.I)
_navd88_pattern = re.compile("^navd.?88$", re.I)
_other_datum_pattern = re.compile("^(local|other)$", re.I)
_all_datums_pattern = re.compile("^(ngvd.?29|navd.?88|local|other)$", re.I)

_parameter_info = {}
_compatible_parameters_set: dict[str, set[str]] = {}
_accumulation_parameters = set()
_integration_parameters = {}
_differentiation_parameters = {}
with open(
    os.path.join(os.path.dirname(__file__), "resources", "base_parameters.tsv")
) as f:
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
        if eval(parts[5]):
            _accumulation_parameters.add(parts[0])
        if len(parts) > 6:
            if parts[6] and parts[6].strip():
                _integration_parameters[parts[0]] = parts[6]
            if len(parts) > 7 and parts[7].strip():
                _differentiation_parameters[parts[0]] = {
                    "base_parameter": parts[7],
                    "EN": eval(parts[8]),
                    "SI": eval(parts[9]),
                }
        for u in unit.get_compatible_units(parts[3]):
            _compatible_parameters_set.setdefault(u, set()).add(parts[0])

_compatible_parameters: dict[str, list[str]] = {}
for u in _compatible_parameters_set:
    _compatible_parameters[u] = sorted(_compatible_parameters_set[u])

_base_parameters = {}
for base_parameter in _parameter_info:
    _base_parameters[base_parameter.upper()] = base_parameter

_parameter_type_info: dict[str, Any] = {
    #    Type             CWMS       HEC-DSS
    #    --------------   ---------- -----------------------
    "Total": ("Total", "PER-CUM"),
    "Maximum": ("Max", "PER-MAX"),
    "Minimum": ("Min", "PER-MIN"),
    "Constant": ("Const", "CONST"),
    "Average": ("Ave", "PER-AVER"),
    "Instantaneous": ("Inst", ("INST-VAL", "INST-CUM")),  # (Other, Precip/Count)
    #   "Cumulative"    : ("Cum",    "INST-CUM"),             # Precip/Count, Duration = 0
    #   "Incremental"   : ("Inc",    "PER-CUM"),              # Precip/Count, Duration > 0
    #   "Median"        : ("Median", "MEDIAN")
}
_cwms_parameter_types: dict[str, Union[str, tuple[str, str]]] = {}
_dss_parameter_types: dict[str, str] = {}
_parameter_types: dict[str, str] = {}
for param_type in _parameter_type_info:
    cwms, dss = _parameter_type_info[param_type]
    _parameter_types[param_type] = param_type
    _parameter_types[cwms] = param_type
    _dss_parameter_types[param_type] = dss
    _dss_parameter_types[cwms] = dss
    _cwms_parameter_types[param_type] = cwms
    if isinstance(dss, tuple):
        for item in dss:
            _parameter_types[item] = param_type
            _cwms_parameter_types[item] = cwms
    else:
        _parameter_types[dss] = param_type
        _cwms_parameter_types[dss] = cwms


def get_compatible_parameters(unitspec: Union[str, Unit]) -> list[str]:
    """
    Returns a list of base parameter names that are compatible with the specified unit

    Args:
        unit Union[str, Unit]): The unit to get the compatible parameters for

    Returns:
        list[str]: The list of compatible base parameter names
    """
    u = str(unitspec)
    return _compatible_parameters[u] if u in _compatible_parameters else []


class ParameterException(Exception):
    """
    Exception specific to Parameter operations
    """

    pass


class Parameter:
    """
    Holds info (name and unit) for a parameter.

    See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.
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
        self._unit_name: str
        self._unit: Unit
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
            Parameter.to(
                self, unit_or_system, in_place=True
            )  # don't use to() method in sublcass when instantiating from subclass
        else:
            self._unit_name = _parameter_info[self._base_parameter]["default_en_unit"]
            self._unit = unit.get_pint_unit(self._unit_name)

    def __repr__(self) -> str:
        return f"Parameter('{self._name}', '{self._unit_name}')"

    def __str__(self) -> str:
        return f"{self._name} ({self._unit_name})"

    @staticmethod
    def accumulatable_base_parameters(context: str = "CWMS") -> List[str]:
        """
        Returns a list of base parameter names that can be accumulated over time for the specified context

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            context (str): The context for the base parameter names. Currently only "CWMS" is supported. Defaults to "CWMS"

        Raises:
            ParameterException: If an invalid context is specified

        Returns:
            List[str]: A sorted list of names of base parameter that can be integrated over time for the context
        """
        if context == "CWMS":
            return sorted(list(_accumulation_parameters))
        raise ParameterException(
            f"No such context exists for base parameter names: '{context}'"
        )

    @property
    def base_parameter(self) -> str:
        """
        The actual base parameter used. Will be same as `basename` unless the
        parameter was created using a parameter alias

        Operations:
            Read Only
        """
        return self._base_parameter

    @staticmethod
    def base_parameters(context: str = "CWMS") -> List[str]:
        """
        Returns a list of valid base parameter names for the specified context

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            context (str): The context for the base parameter names. Currently only "CWMS" is supported. Defaults to "CWMS"

        Raises:
            ParameterException: If an invalid context is specified

        Returns:
            List[str]: A sorted list of valid base parameter names for the context
        """
        if context == "CWMS":
            return sorted(list(_parameter_info.keys()))
        raise ParameterException(
            f"No such context exists for base parameter names: '{context}'"
        )

    @property
    def basename(self) -> str:
        """
        The name of the parameter as specified up to any initial '-' character

        Operations:
            Read Only
        """
        return self._name.split("-", 1)[0]

    @staticmethod
    def differentiable_base_parameters(context: str = "CWMS") -> List[str]:
        """
        Returns a list of base parameter names that can be differentiated with respect to time for the specified context

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            context (str): The context for the base parameter names. Currently only "CWMS" is supported. Defaults to "CWMS"

        Raises:
            ParameterException: If an invalid context is specified

        Returns:
            List[str]: A sorted list of names of base parameter that can be differentiated with respect to time for the context
        """
        if context == "CWMS":
            return sorted(list(_differentiation_parameters.keys()))
        raise ParameterException(
            f"No such context exists for base parameter names: '{context}'"
        )

    @staticmethod
    def differentiation_info(
        base_parameter: str, context: str = "CWMS"
    ) -> dict[str, Any]:
        """
        Returns differentiation information for a base parameter name

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            base_parameter (str): The base parameter to get the information for.
            context (str): The context for the base parameter names. Currently only "CWMS" is supported. Defaults to "CWMS"

        Returns:
            dict: A dictionary with the following content:
            {
                "base_parameter": <base_parameter_name of differentiated time series>,
                "EN" : <floating point factor for converting original parameter unit/second to the differentiated parameter unit>,
                "SI" : <floating point factor for convertiig original parameter unit/second to the differentiated parameter unit>,
            }
        """
        return _differentiation_parameters[base_parameter]

    def get_compatible_units(self) -> list[str]:
        """
        Returns the list of unit names compatible with this parameter's unit

        Returns:
            list[str]: The list of compatible unit names
        """
        return unit.get_compatible_units(self.unit_name)

    @staticmethod
    def integrable_base_parameters(context: str = "CWMS") -> List[str]:
        """
        Returns a list of base parameter names that can be integrated over time for the specified context

        See [base_parameter_definitions](parameter.html#base_parameter_definitions) for information on base parameters and their conversions.

        Args:
            context (str): The context for the base parameter names. Currently only "CWMS" is supported. Defaults to "CWMS"

        Raises:
            ParameterException: If an invalid context is specified

        Returns:
            List[str]: A sorted list of names of base parameter that can be integrated over time for the context
        """
        if context == "CWMS":
            return sorted(list(_integration_parameters.keys()))
        raise ParameterException(
            f"No such context exists for base parameter names: '{context}'"
        )

    def ito(self, unit_or_system: str) -> "Parameter":
        """
        Assigns a unit to this parameter.

        Identical to calling [.to(unit_or_system, in_place=True)](#Parameter.to)

        Args:
            unit_or_system (str):<br>
                * If `EN`, the default English unit for the base parameter will be assigned
                * if `SI`,  the default Système International unit for the base parameter will be assigned
                * Otherwise the specified unit will be assigned

        Raises:
            ParameterException: If the specified unit is not valid for the parameter

        Returns:
            Parameter: The converted object
        """
        return self.to(unit_or_system, in_place=True)

    @property
    def name(self) -> str:
        """
        The full name of the parameter as specified

        Operations:
            Read Only
        """
        return self._name

    @property
    def subname(self) -> Optional[str]:
        """
        The name of the parameter as specified after any initial '-' character

        Operations:
            Read Only
        """
        parts = self._name.split("-", 1)
        return None if len(parts) == 1 else parts[1]

    def to(self, unit_or_system: str, in_place: bool = False) -> "Parameter":
        """
        Assigns a unit to this parameter or a copy of this parameter

        Args:
            unit_or_system (str):<br>
                * If `EN`, the default English unit for the base parameter will be assigned
                * if `SI`,  the default Système International unit for the base parameter will be assigned
                * Otherwise the specified unit will be assigned
            in_place (bool, optional): Specifies whether to modify and return this object (True)
                or a copy of this object (False). Defaults to False.

        Raises:
            ParameterException: If the specified unit is not valid for the parameter

        Returns:
            Parameter: The converted object (self if in_place == True, otherwise a converted copy)
        """
        converted = self if in_place else Parameter(self.name)
        if unit_or_system.upper() == "EN":
            converted._unit_name = _parameter_info[converted._base_parameter][
                "default_en_unit"
            ]
        elif unit_or_system.upper() == "SI":
            converted._unit_name = _parameter_info[converted._base_parameter][
                "default_si_unit"
            ]
        else:
            unit_name = unit.get_unit_name(unit_or_system)
            if not unit_name in unit.get_compatible_units(
                _parameter_info[self._base_parameter]["default_en_unit"]
            ):
                raise ParameterException(
                    f"{unit_or_system} is not a vaild unit for base parameter {self._base_parameter}"
                )
            converted._unit_name = unit_name
        converted._unit = unit.get_pint_unit(converted._unit_name)
        return converted

    @property
    def unit(self) -> Unit:
        """
        The unit assigned to the parameter

        Operations:
            Read Only
        """
        return self._unit

    @property
    def unit_name(self) -> str:
        """
        The unit name assigned to the parameter

        Operations:
            Read Only
        """
        return self._unit_name


class ElevParameter(Parameter):
    """
    Holds info (name and vertical datum information) for an elevation parameter
    """

    class VerticalDatumException(ParameterException):
        """
        Exception specific to vertical datum operations
        """

        pass

    class _VerticalDatumInfo:
        """
        Holds vertical datum information and provides datum operations
        """

        def __init__(self, vertical_datum_info: Union[str, dict[str, Any]]):
            """
            Initializes a VerticalDatumInfo object.<br>
            * Use str(*object*) to retrieve an xml representation
            * Use *object*.to_dict() to retireve a dictionary representation

            Args:
                vertical_datum_info (Union[str, dict[str, Any]]): An xml string or a dictionary:
                    * `str`: An xml vertical datum string as returned by the CWMS database or HEC-DSS for elevations.
                    * `dict`: The value of the "vertical-datum-info" key in the dictionary returned by the `.json`
                        attribute of a timeseries retrieved by cwms-python.

            Raises:
                ElevParameter.VerticalDatumException: If no unit is present in the vertical datum info
            """
            self._unit_name: str
            self._unit: Unit
            self._elevation: Optional[UnitQuantity] = None
            self._native_datum: Optional[str] = None
            self._current_datum: Optional[str] = None
            self._ngvd29_offset: Optional[UnitQuantity] = None
            self._navd88_offset: Optional[UnitQuantity] = None
            self._ngvd29_offset_is_estimate: Optional[bool] = None
            self._navd88_offset_is_estimate: Optional[bool] = None
            if vertical_datum_info:
                if isinstance(vertical_datum_info, dict):
                    # --------------------------------------------- #
                    # dictionary as from cwms-python get_timeseries #
                    # --------------------------------------------- #
                    if "unit" in vertical_datum_info:
                        self._unit_name = vertical_datum_info["unit"]
                        self._unit = unit.get_pint_unit(self._unit_name)
                    else:
                        raise ElevParameter.VerticalDatumException(
                            f"No unit in dictionary"
                        )
                    if "native-datum" in vertical_datum_info:
                        text = vertical_datum_info["native-datum"]
                        if _ngvd29_pattern.match(text):
                            self._native_datum = _NGVD29
                        elif _navd88_pattern.match(text):
                            self._native_datum = _NAVD88
                        elif _other_datum_pattern.match(text):
                            self._native_datum = _OTHER_DATUM
                        else:
                            self._native_datum = text
                    self._current_datum = self._native_datum
                    if "elevation" in vertical_datum_info:
                        self._elevation = UnitQuantity(
                            vertical_datum_info["elevation"], self._unit_name
                        )
                    if "offsets" in vertical_datum_info:
                        for offset_props in vertical_datum_info["offsets"]:
                            if offset_props["to-datum"] == _NGVD29:
                                self._ngvd29_offset = UnitQuantity(
                                    offset_props["value"], self._unit_name
                                )
                                self._ngvd29_offset_is_estimate = offset_props[
                                    "estimate"
                                ]
                            elif offset_props["to-datum"] == _NAVD88:
                                self._navd88_offset = UnitQuantity(
                                    offset_props["value"], self._unit_name
                                )
                                self._navd88_offset_is_estimate = offset_props[
                                    "estimate"
                                ]
                elif isinstance(vertical_datum_info, str):
                    vertical_datum_info = vertical_datum_info.strip()
                    if vertical_datum_info.startswith("{"):
                        # ----------------------- #
                        # JSON string as from CDA #
                        # ----------------------- #
                        s = re.sub(
                            r"\b(true|false)\b",
                            lambda m: m.group(0).title(),
                            vertical_datum_info,
                        )
                        vdi = ElevParameter._VerticalDatumInfo(eval(s))
                        self._unit_name = vdi._unit_name
                        self._unit = vdi._unit
                        self._elevation = vdi._elevation
                        self._native_datum = vdi._native_datum
                        self._current_datum = vdi._current_datum
                        self._ngvd29_offset = vdi._ngvd29_offset
                        self._navd88_offset = vdi._navd88_offset
                        self._ngvd29_offset_is_estimate = vdi._ngvd29_offset_is_estimate
                        self._navd88_offset_is_estimate = vdi._navd88_offset_is_estimate
                    elif vertical_datum_info.startswith("<"):
                        # ------------------------------------- #
                        # XML string as from CWMS db or HEC-DSS #
                        # ------------------------------------- #
                        root = ET.fromstring(vertical_datum_info)
                        if root.tag != "vertical-datum-info":
                            raise ElevParameter.VerticalDatumException(
                                f"Expected root element of <vertical-datum-info>, got <{root.tag}>"
                            )
                        if "unit" in root.attrib:
                            self._unit_name = root.attrib["unit"]
                            self._unit = unit.get_pint_unit(self._unit_name)
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
                            self._elevation = UnitQuantity(
                                float(elem.text), self._unit_name
                            )
                        for elem in root.findall("offset"):
                            estimate = elem.attrib["estimate"] == "true"
                            datum_elem = elem.find("to-datum")
                            value_elem = elem.find("value")
                            if (
                                datum_elem is not None
                                and datum_elem.text
                                and value_elem is not None
                                and value_elem.text
                            ):
                                datum = datum_elem.text
                                value = float(value_elem.text)
                                if datum == _NGVD29:
                                    self._ngvd29_offset = unit.UnitQuantity(
                                        value, self._unit
                                    )
                                    self._ngvd29_offset_is_estimate = estimate
                                elif datum == _NAVD88:
                                    self._navd88_offset = unit.UnitQuantity(
                                        value, self._unit
                                    )
                                    self._navd88_offset_is_estimate = estimate

        def __str__(self) -> str:
            if (
                self.current_datum
                and self.native_datum
                and self.current_datum != self.native_datum
            ):
                return str(cast(str, self.to(self.native_datum)))
            buf = StringIO()
            buf.write(f'<vertical-datum-info unit="{self._unit_name}">')
            if self.native_datum:
                if self._native_datum in (_NGVD29, _NAVD88, _OTHER_DATUM):
                    buf.write(f"\n  <native-datum>{self.native_datum}</native-datum>")
                else:
                    buf.write(f"\n  <native-datum>OTHER</native-datum>")
                    buf.write(
                        f"\n  <local-datum-name>{self.native_datum}</local-datum-name>"
                    )
            if self.elevation is not None:
                buf.write(f"\n  <elevation>{self.elevation.magnitude}</elevation>")
            if self.ngvd29_offset is not None:
                buf.write(
                    f'\n  <offset estimate="{"true" if self._ngvd29_offset_is_estimate else "false"}">'
                )
                buf.write("\n    <to-datum>NGVD-29</to-datum>")
                buf.write(f"\n    <value>{self.ngvd29_offset.magnitude}</value>")
                buf.write("\n  </offset>")
            if self.navd88_offset is not None:
                buf.write(
                    f'\n  <offset estimate="{"true" if self._navd88_offset_is_estimate else "false"}">'
                )
                buf.write("\n    <to-datum>NAVD-88</to-datum>")
                buf.write(f"\n    <value>{self.navd88_offset.magnitude}</value>")
                buf.write("\n  </offset>")
            buf.write("\n</vertical-datum-info>")
            s = buf.getvalue()
            buf.close()
            return s

        def clone(self) -> "ElevParameter._VerticalDatumInfo":
            """
            Returns a copy of this opject

            Returns:
                ElevParameter.VerticalDatumInfo: The copy
            """
            other = ElevParameter._VerticalDatumInfo("")
            other._elevation = self._elevation
            other._unit = unit.get_pint_unit(self._unit_name)
            other._unit_name = self._unit_name
            other._native_datum = self._native_datum
            other._current_datum = self._current_datum
            other._ngvd29_offset = self._ngvd29_offset
            other._navd88_offset = self._navd88_offset
            other._ngvd29_offset_is_estimate = self._ngvd29_offset_is_estimate
            other._navd88_offset_is_estimate = self._navd88_offset_is_estimate
            return other

        @property
        def current_datum(self) -> Optional[str]:
            """
            The current vertical datum

            Operations:
                Read Only
            """
            return self._current_datum

        @property
        def elevation(self) -> Optional[UnitQuantity]:
            """
            The elevation in the current vertical datum and unit

            Operations:
                Read Only
            """
            return self._elevation.round(9) if self._elevation else None

        def get_offset_to(self, target_datum: str) -> Optional[UnitQuantity]:
            """
            Returns the offset from the current vertical datum to the specified target datum in the current unit.

            Args:
                target_datum (str): The target datum

            Raises:
                ElevParameter.VerticalDatumException: If the target datum is invalid or the
                    object does not specify an offset to the target datum

            Returns:
                Optional[UnitQuantity]: The offset from the current datum to the target datum
                    or `None` if the current and target datums are the same.
            """
            target_datum = self.normalize_datum_name(target_datum)
            if target_datum == self._current_datum:
                return None
            if target_datum == _NGVD29:
                if self.current_datum == _NAVD88:
                    if self._ngvd29_offset is None or self._navd88_offset is None:
                        return None
                    return (self._ngvd29_offset - self._navd88_offset).to(
                        self._unit_name
                    )
                else:
                    return self._ngvd29_offset
            elif target_datum == _NAVD88:
                if self.current_datum == _NGVD29:
                    if self._ngvd29_offset is None or self._navd88_offset is None:
                        return None
                    return (self._navd88_offset - self._ngvd29_offset).to(
                        self._unit_name
                    )
                else:
                    return self._navd88_offset
            else:
                if self.current_datum == _NGVD29:
                    return (
                        -self._ngvd29_offset
                        if self._ngvd29_offset is not None
                        else None
                    )
                elif self.current_datum == _NAVD88:
                    return (
                        -self._navd88_offset
                        if self._navd88_offset is not None
                        else None
                    )
                else:
                    raise ElevParameter.VerticalDatumException(
                        f"Cannot determine offset to {target_datum}"
                    )

        def ito(
            self, unit_or_datum: Union[str, Unit]
        ) -> "ElevParameter._VerticalDatumInfo":
            """
            Converts this object to the specified unit or vertical datum and returns it.

            Identical to calling [].to(unit_or_datum, in_place=True)](#ElevParameter._VerticalDatumInfo.to)

            Args:
                unit_or_datum (Union[str, Unit]): The unit or vertical datum to convert to
            Returns:
                ElevParameter.VerticalDatumInfo: The converted object
            """
            return self.to(unit_or_datum, in_place=True)

        @property
        def native_datum(self) -> Optional[str]:
            """
            The native vertical datum

            Operations:
                Read Only
            """
            return self._native_datum

        @property
        def navd88_offset(self) -> Optional[UnitQuantity]:
            """
            The offset from the native vertical datum to NAVD-88 in the current unit, or `None` if<br>
            * the native vertical datum is NAVD-88
            * the native vertical datum is not NAVD-88, but the object does not have such an offset

            Operations:
                Read Only
            """
            return self._navd88_offset.round(9) if self._navd88_offset else None

        @property
        def navd88_offset_is_estimate(self) -> Optional[bool]:
            """
            Whether the offset from the native vertical datum to NAVD-88 is an estimate (e.g, VERTCON)
            or `None` if the native vertical datum is NAVD-88 or the object does not have such and offset

            Operations:
                Read Only
            """
            return self._navd88_offset_is_estimate

        @property
        def ngvd29_offset(self) -> Optional[UnitQuantity]:
            """
            The offset from the native vertical datum to NGVD-29 in the current unit, or `None` if<br>
            * the native vertical datum is NGVD-29
            * the native vertical datum is not NGVD-29, but the object does not have such an offset

            Operations:
                Read Only
            """
            return self._ngvd29_offset.round(9) if self._ngvd29_offset else None

        @property
        def ngvd29_offset_is_estimate(self) -> Optional[bool]:
            """
            Whether the offset from the native vertical datum to NGVD-29 is an estimate (e.g, VERTCON)
            or `None` if the native vertical datum is NGVD-29 or the object does not have such and offset

            Operations:
                Read Only
            """
            return self._ngvd29_offset_is_estimate

        def normalize_datum_name(self, datum_str: str) -> str:
            """
            Returns a normalized version of the specified datum

            Args:
                datum_str (str): The datum to normalize. Valid inputs are:
                    * "NGVD-29", "NAVD-88", "OTHER", or "LOCAL" in any case with the "-" deleted or replaced by any character
                    * The actual local datum name in any case

            Raises:
                ElevParameter.VerticalDatumException:
                    * *Objects with local datum**: If the normalized datum is not one of "NGVD-29",
                        "NAVD-88", "OTHER", "LOCAL" or the actual local datum name.
                    * *Objects without local datum**: If the normalized datum is not one of "NGVD-29",
                         or "NAVD-88".
            Returns:
                str: _description_
            """
            if _ngvd29_pattern.match(datum_str):
                return _NGVD29
            elif _navd88_pattern.match(datum_str):
                return _NAVD88
            elif (
                _other_datum_pattern.match(datum_str)
                or self._native_datum
                and (datum_str.upper() == self._native_datum.upper())
            ):
                if not self.native_datum:
                    raise ElevParameter.VerticalDatumException(
                        f"Invalid vertical datum: {datum_str}"
                    )
                return self.native_datum
            else:
                raise ElevParameter.VerticalDatumException(
                    f"Invalid vertical datum: {datum_str}"
                )

        def to(
            self, unit_or_datum: Union[str, Unit], in_place: bool = False
        ) -> "ElevParameter._VerticalDatumInfo":
            """
            Converts either this object or a copy of it to the specified unit or vertical datum and returns it

            Args:
                unit_or_datum (Union[str, Unit]): The unit or vertical datum to convert to
                in_place (bool, optional): If `True`, this object is converted and returned, otherwise a copy is
                    converted and returned. Defaults to False.

            Returns:
                ElevParameter.VerticalDatumInfo: The converted object - whether this object or a copy of this object
            """
            converted = self if in_place else self.clone()
            try:
                if isinstance(unit_or_datum, Unit) or not (
                    _all_datums_pattern.match(unit_or_datum)
                    or (
                        self._native_datum
                        and unit_or_datum.upper() == self._native_datum.upper()
                    )
                    or unit_or_datum.upper() in ("EN", "SI")
                ):
                    # ---------------------- #
                    # convert to target unit #
                    # ---------------------- #
                    if isinstance(unit_or_datum, Unit):
                        converted._unit_name = unit.get_unit_name(unit_or_datum)
                        converted._unit = unit_or_datum
                    else:
                        converted._unit_name = unit.get_unit_name(unit_or_datum)
                        converted._unit = unit.get_pint_unit(converted._unit_name)
                    if converted._elevation is not None:
                        converted._elevation.ito(converted._unit_name)
                    if converted._ngvd29_offset is not None:
                        converted._ngvd29_offset.ito(converted._unit_name)
                    if converted._navd88_offset is not None:
                        converted._navd88_offset.ito(converted._unit_name)
                else:
                    # ----------------------- #
                    # convert to target datum #
                    # ----------------------- #
                    target_datum = self.normalize_datum_name(unit_or_datum)
                    offset = converted.get_offset_to(target_datum)
                    if offset:
                        offset = offset.to(self._unit_name)
                        if converted._elevation:
                            converted._elevation += offset
                    converted._current_datum = target_datum
                return converted
            except:
                raise ElevParameter.VerticalDatumException(
                    f"Invalid unit or datum: {unit_or_datum}"
                )

        def to_dict(self) -> dict[str, Any]:
            """
            Retrieves a dictionary representation of this object

            Returns:
                dict[str, Any]: _description_
            """
            d: dict[str, Any] = {}
            if self.native_datum:
                d["native-datum"] = self.native_datum
            if self.elevation is not None:
                d["elevation"] = self.elevation.magnitude
            if self.unit_name:
                d["unit"] = self.unit_name
            if self.ngvd29_offset is not None or self.navd88_offset is not None:
                d["offsets"] = []
                if self.ngvd29_offset is not None:
                    d["offsets"].append(
                        {
                            "to-datum": _NGVD29,
                            "estimate": self.ngvd29_offset_is_estimate,
                            "value": self.ngvd29_offset.magnitude,
                        }
                    )
                if self.navd88_offset is not None:
                    d["offsets"].append(
                        {
                            "to-datum": _NAVD88,
                            "estimate": self.navd88_offset_is_estimate,
                            "value": self.navd88_offset.magnitude,
                        }
                    )
            return d

        @property
        def unit(self) -> Unit:
            """
            The unit assigned to the parameter

            Operations:
                Read Only
            """
            return self._unit

        @property
        def unit_name(self) -> str:
            """
            The unit name assigned to the parameter

            Operations:
                Read Only
            """
            return self._unit_name

    def __init__(
        self,
        name: str,
        vertical_datum_info: Optional[Union[str, dict[str, Any]]] = None,
    ):
        """
        Initializes the ElevParameter object

        Args:
            name (str): The full parameter name
            vertical_datum_info (Union[str, dict[str, Any]]): The vertical datum info as an xml string or dictionary

        Raises:
            ElevParameter.VerticalDatumException: If `vertical datum` info is invalid
            ParameterException: If the base parameter is not 'Elev'
        """
        if vertical_datum_info:
            _vertical_datum_info = ElevParameter._VerticalDatumInfo(vertical_datum_info)
            unit_name = _vertical_datum_info.unit_name
        else:
            unit_name = None
        super().__init__(name, unit_name)
        if self.base_parameter != "Elev":
            raise ParameterException(
                f"Cannot instantiate an ElevParameter object with base parameter of {self.base_parameter}"
            )
        self._vertical_datum_info = _vertical_datum_info

    def __repr__(self) -> str:
        return f"ElevParameter('{self.name}', <vertical-datum-info>)"

    def __str__(self) -> str:
        return f"{self.name} (<vertical-datum-info>)"

    def clone(self) -> "ElevParameter":
        """
        Returns a copy of this object

        Returns:
            ElevParameter: The copy
        """
        return ElevParameter(self._name, str(self._vertical_datum_info))

    @property
    def current_datum(self) -> Optional[str]:
        """
        The current datum of this object

        Operations:
            Read Only
        """
        return self.vertical_datum_info.current_datum

    @property
    def elevation(self) -> Optional[UnitQuantity]:
        """
        The elevation of this object in the current datum and unit

        Operations:
            Read Only
        """
        return self.vertical_datum_info.elevation

    def get_offset_to(self, target_datum: str) -> Optional[UnitQuantity]:
        """
        Returns the offset from the current vertical datum to the specified target datum in the current unit.

        Args:
            target_datum (str): The target datum

        Raises:
            ElevParameter.VerticalDatumException: If the target datum is invalid or the
                object does not specify an offset to the target datum

        Returns:
            Optional[UnitQuantity]: The offset from the current datum to the target datum
                or `None` if the current and target datums are the same.
        """
        return self.vertical_datum_info.get_offset_to(target_datum)

    def ito(self, unit_or_system_or_datum: Union[str, Unit]) -> "ElevParameter":
        """
        Converts this object to the specified unit or vertical datum and returns it.

        Identical to calling [.to(unit_or_system_or_datum, in_place=True](#ElevParameter.to)

        Args:
            unit_or_system_or_datum (Union[str, Unit]): The unit, unit_system, or vertical datum to convert to.
                If unit system ("EN" or "SI"), the default Elev unit for that system is used.

        Returns:
            ElevParameter: The converted object, whether this object of a copy of it
        """
        return self.to(unit_or_system_or_datum, in_place=True)

    @property
    def native_datum(self) -> Optional[str]:
        """
        The native datum of this object

        Operations:
            Read Only
        """
        return self.vertical_datum_info.native_datum

    @property
    def navd88_offset(self) -> Optional[UnitQuantity]:
        """
        The offset from the native datum of this object to NGVD-29, in the current unit, or `None` if<br>
            * the native vertical datum is NGVD-29
            * the native vertical datum is not NGVD-29, but the object does not have such an offset

        Operations:
            Read Only
        """
        return self.vertical_datum_info.navd88_offset

    @property
    def navd88_offset_is_estimate(self) -> Optional[bool]:
        """
        Whether the offset from the native vertical datum to NGVD-29 is an estimate (e.g, VERTCON)
        or `None` if the native vertical datum is NGVD-29 or the object does not have such and offset

        Operations:
            Read Only
        """
        return self._vertical_datum_info.navd88_offset_is_estimate

    @property
    def ngvd29_offset(self) -> Optional[UnitQuantity]:
        """
        The offset from the native datum of this object to NGVD-29, in the current unit, or `None` if<br>
            * the native vertical datum is NGVD-29
            * the native vertical datum is not NGVD-29, but the object does not have such an offset

        Operations:
            Read Only
        """
        return self.vertical_datum_info.ngvd29_offset

    @property
    def ngvd29_offset_is_estimate(self) -> Optional[bool]:
        """
        Whether the offset from the native vertical datum to NGVD-29 is an estimate (e.g, VERTCON)
        or `None` if the native vertical datum is NGVD-29 or the object does not have such and offset

        Operations:
            Read Only
        """
        return self._vertical_datum_info.ngvd29_offset_is_estimate

    def to(
        self, unit_or_system_or_datum: Union[str, Unit], in_place: bool = False
    ) -> "ElevParameter":
        """
        Converts either this object or a copy of it to the specified unit or vertical datum and returns it

        Args:
            unit_or_system_or_datum (Union[str, Unit]): The unit, unit_system, or vertical datum to convert to.
                If unit system ("EN" or "SI"), the default Elev unit for that system is used.
            in_place (bool, optional): If `True`, this object is converted and returned, otherwise a copy is
                converted and returned. Defaults to False.

        Returns:
            ElevParameter: The converted object, whether this object of a copy of it
        """
        try:
            converted = self if in_place else self.clone()
            if isinstance(
                unit_or_system_or_datum, str
            ) and unit_or_system_or_datum.upper() in ("EN", "SI"):
                if unit_or_system_or_datum.upper() == "EN":
                    converted._unit_name = _parameter_info[converted.base_parameter][
                        "default_en_unit"
                    ]
                else:
                    converted._unit_name = _parameter_info[converted.base_parameter][
                        "default_si_unit"
                    ]
                converted._unit_name = unit.get_unit_name(converted._unit_name)
                converted._vertical_datum_info.to(converted._unit_name, in_place=True)
                converted._unit = converted.vertical_datum_info.unit
            else:
                converted._vertical_datum_info.to(
                    unit_or_system_or_datum, in_place=True
                )
                converted._unit_name = converted.vertical_datum_info.unit_name
                converted._unit = converted.vertical_datum_info.unit
            return converted
        except:
            raise ParameterException(
                f"Invalid unit for base parameter Elev or or invalid vertical datum: {unit_or_system_or_datum}"
            )

    @property
    def unit(self) -> Unit:
        """
        The unit of this object

        Operations:
            Read Only
        """
        return self._vertical_datum_info.unit

    @property
    def unit_name(self) -> str:
        """
        The unit name of this object

        Operations:
            Read Only
        """
        return self._vertical_datum_info.unit_name

    @property
    def vertical_datum_info(self) -> _VerticalDatumInfo:
        """
        The VerticalDatumInfo object of this parameter

        Operations:
            Read Only
        """
        return self._vertical_datum_info

    @property
    def vertical_datum_info_dict(self) -> dict[str, Any]:
        """
        The VerticalDatumInfo object of this parameter as a dictionary

        Operations:
            Read Only
        """
        return self.vertical_datum_info.to_dict()

    @property
    def vertical_datum_info_xml(self) -> str:
        """
        The VerticalDatumInfo object of this parameter as an xml string

        Operations:
            Read Only
        """
        return str(self.vertical_datum_info)


class ParameterTypeException(Exception):
    """
    Exception specific to ParameterType operations
    """

    pass


class ParameterType:
    """
    Holds info about parameter types.

    Parameter types have 3 separate contexts, RAW, CWMS, and DSS. There's not much use for the RAW context
    except for providing a bridge between the CWMS and DSS contexts. Users would normally work in either
    the CWMS or DSS context.

    The contexts of already-instantiated objects can also be set.

    Parameter type names in the different contexts are:
    <table>
    <tr><th>RAW</th><th>CWMS</th><th>DSS</th></tr>
    <tr><td>Total</td><td>Total</td><td>PER-CUM</td></tr>
    <tr><td>Maximum</td><td>Max</td><td>PER-MAX</td></tr>
    <tr><td>Minimum</td><td>Min</td><td>PER-MIN</td></tr>
    <tr><td>Constant</td><td>Const</td><td>CONST</td></tr>
    <tr><td>Average</td><td>Ave</td><td>PER-AVER</td></tr>
    <tr><td rowspan="2">Instantaneous</td><td rowspan="2">Inst</td><td>INST-CUM (for Precip or Count)</td></tr><tr><td>INST-VAL (for others)</td></tr>
    </table>
    """

    _default_context: str = "RAW"

    def __init__(self, param_type: str, context: Optional[str] = None):
        """
        Initializes a ParameterType object

        Args:
            param_type (str): The name of the parameter type

        Raises:
            ParameterTypeException: If `param_type` is not one of the values listed in the table above (context-insensitive)
        """
        self._context = ParameterType._default_context
        self._name: str
        ptype = param_type.upper()
        for key in _parameter_types:
            if key.upper() == ptype:
                self._name = _parameter_types[key]
                break
        else:
            raise ParameterTypeException(f"{param_type} is not a valid parameter type")
        if context is not None:
            self.set_context(context)

    @property
    def context(self) -> str:
        """
        The context of this object

        Operations:
            Read Only
        """
        return self._context

    def get_cwms_name(self) -> str:
        """
        Returns the name of the parameter time for the CWMS context

        Returns:
            str: The CWMS context name
        """
        return cast(str, _cwms_parameter_types[self._name])

    def get_dss_name(self, is_precip: bool = False) -> str:
        """
        Returns the name of the parameter time for the DSS context

        Args:
            is_precip (bool, optional): Whether the parameter type is for a precipitation parameter.
                This matters only for the `Instantaneous` parameter type (CWMS=`Inst`). Defaults to False.
                * `False`: `INST-CUM`
                * `True` : `INST-VAL`

        Returns:
            str: The DSS context name
        """
        dss_type = _dss_parameter_types[self._name]
        if isinstance(dss_type, tuple):
            return dss_type[int(is_precip)]
        else:
            return dss_type

    def get_raw_name(self) -> str:
        """
        Returns the name of the parameter time for the RAW context

        Returns:
            str: The RAW context name
        """
        return self._name

    @property
    def name(self) -> str:
        """
        The context-specific name of the object

        Operations:
            Read Only
        """
        if self.context == "RAW":
            return self._name
        elif self.context == "CWMS":
            return cast(str, _cwms_parameter_types[self._name])
        elif self.context == "DSS":
            dss_type = _dss_parameter_types[self._name]
            if isinstance(dss_type, tuple):
                return dss_type[0]
            else:
                return dss_type
        else:
            raise ParameterTypeException(f"Invalid context: {self._context}")

    @staticmethod
    def parameter_type_names(context: str) -> List[str]:
        """
        Returns a list of valid parameter type names for the context.

        Args:
            context (str): The context for the parameter type names. Currently only "RAW", "CWMS", "DSS", and "ALL" are supported.
            If "RAW", the parameter types for all contexts are returned

        Raises:
            ParameterTypeException: If an invlid context is specified

        Returns:
            List[str]: A sorted list of valid parameter type names for the context
        """
        if context == "ALL":
            param_types = []
            for ctx in "RAW", "CWMS", "DSS":
                param_types += ParameterType.parameter_type_names(ctx)
            return sorted(param_types)
        if context == "RAW":
            return sorted(_parameter_type_info.keys())
        if context == "CWMS":
            return sorted([v[0] for v in _parameter_type_info.values()])
        if context == "DSS":
            return sorted(
                [
                    v[1] if isinstance(v[1], str) else ", ".join(v[1])
                    for v in _parameter_type_info.values()
                ]
            )
        raise ParameterTypeException(
            f"No such context exists for parameter type names: '{context}'"
        )

    def set_context(self, context: str) -> None:
        """
        Sets the context for this object

        Args:
            context (str): The context - must be one of RAW, CWMS, or DSS

        Raises:
            ParameterTypeException: If the specified context isn't one of the valid values
        """
        ctx = context.upper()
        if ctx in ("RAW", "CWMS", "DSS"):
            self._context = ctx
        else:
            raise ParameterTypeException(
                f"Invalid context: {ctx}. Must be one of RAW, CWMS, or DSS"
            )

    @classmethod
    def set_default_context(cls, context: str) -> None:
        """
        Sets the default context for new ParameterType objects

        Args:
            context (str): The default context (RAW, CWMS, or DSS)

        Raises:
            ParameterTypeException: If an invalid context is specified
        """
        ctx = context.upper()
        if ctx in ("RAW", "CWMS", "DSS"):
            cls._default_context = ctx
        else:
            raise ParameterTypeException(
                f"Invalid context: {ctx}. Must be one of RAW, CWMS, or DSS"
            )
