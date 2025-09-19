import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional, Sequence, Union, cast

import numpy as np
from lxml import etree

import hec.shared
import hec.unit
from hec.hectime import HecTime
from hec.location import LocationException
from hec.parameter import (
    _NAVD88,
    _NGVD29,
    _OTHER_DATUM,
    ElevParameter,
    Parameter,
    _navd88_pattern,
    _ngvd29_pattern,
    _other_datum_pattern,
)
from hec.rating.rating_shared import replace_indent
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate
from hec.timeseries import TimeSeries


class AbstractRatingException(hec.shared.RatingException):
    pass


class AbstractRating(ABC):
    """
    Abstract class for all rating classes;

    Specifies required methods for sub-classes, holds information and implements code common one or more sub-classes.
    """

    _INCOMPATIBLE_XML_MESSAGE = "Unexpected root element of <%s> for class %s"
    _from_xml_methods: dict[str, Callable[[str], "AbstractRating"]] = {}

    valid_rating_tags = [
        "simple-rating",
        "usgs-stream-rating",
        "virtual-rating",
        "transitional-rating",
    ]

    def __init__(
        self,
        specification: RatingSpecification,
        effective_time: Union[datetime, HecTime, str],
    ):
        """
        Initializer for AbstractRating objects.

        Args:
            specification (Any): A [RatingSpecification](#RatingSpecification) object to initialize from.
                This is typed as `Any` to avoid circular import dependencies.
            effective_time (Union[datetime, HecTime, str]): The effective date/time of the rating

        Raises:
            TypeError: if `specification` is not a [RatingSpecification](#RatingSpecification) object.
        """
        if not isinstance(specification, hec.rating.RatingSpecification):
            raise TypeError(
                f"Expected RatingSpecification for specification, got {specification.__class__.__name__}"
            )
        self._active: bool = True
        self._create_time: Optional[datetime] = None
        self._default_data_units: Optional[list[str]] = None
        self._default_data_vertical_datum: Optional[str] = None
        self._description: Optional[str] = None
        self._effective_time: datetime
        self._rating_units: list[str] = []
        self._specification: RatingSpecification
        self._transition_start_time: Optional[datetime] = None
        self._specification = specification.copy()
        self.effective_time = effective_time
        for ind_param in self._specification.template._ind_params:
            self._rating_units.append(Parameter(ind_param.name).unit_name)
        self._rating_units.append(
            Parameter(self._specification.template.dep_param).unit_name
        )

    @staticmethod
    def _find_rating_root(
        xml_str: str,
    ) -> tuple[etree._Element, Optional[RatingSpecification]]:
        specification: Optional[RatingSpecification] = None
        template: Optional[RatingTemplate] = None
        if xml_str.startswith("<?xml"):
            xml_str = xml_str.split("?>", 1)[1]
        root = etree.fromstring(xml_str)
        if root.tag == "ratings":
            for child in root:
                if child.tag in ("rating-template", "rating-spec"):
                    if not template and child.tag == "rating-template":
                        template = RatingTemplate.from_xml(
                            etree.tostring(child).decode()
                        )
                    if not specification and child.tag == "rating-spec":
                        specification = RatingSpecification.from_xml(
                            etree.tostring(child).decode()
                        )
                        if template:
                            specification.template = template
                    continue
                root = child
                break
        if root.tag not in AbstractRating.valid_rating_tags:
            raise AbstractRatingException(f"Unexpected rating element: <{root.tag}>")
        return (root, specification)

    @staticmethod
    def _parse_common_info(
        root: etree._Element, specification: Optional[RatingSpecification]
    ) -> tuple[Any, ...]:
        """
        Parses <xxx-rating> elements common to all rating XML structures

        Args:
            root (etree._Element): The <simple-rating> element
            specification (RatingSpecification): The rating specification passed to [`AbstractRating.from_xml`](abstract_rating.html#AbstractRating.from_xml), if any

        Raises:
            AbstractRatingException: if expected element is not present or date/time format is invalid

        Returns:
            tuple[Any]: Contains
                * `specification` (RatingSpecification): The specified specification (possibly updated from XML) or one created from the XML if the specified one is None
                * `active` (bool): The active flag from the XML
                * `units` (list[str]): The native units from the XML
                * `effective_time` (datetime): The effective date/time from the XML
                * `create_time` (datetime|None): The creation date/time from the XML, may be None
                * `transition_start_time (datetime|None)`: The start of transition date/time from the XML, may be None
                * `description` (str|None): The description from the XML, may be None
        """
        active: bool = True
        units: list[str]
        effective_time: datetime
        create_time: Optional[datetime] = None
        transition_start_time: Optional[datetime] = None
        description: Optional[str] = None
        office = root.get("office-id")
        if not office:
            raise AbstractRatingException("No office specified in <simple-rating>")
        if specification and office != specification.template.office:
            raise AbstractRatingException(
                f"Office in <simple-rating> ({office}) is not the same as in specification ({specification.template.office})"
            )
        spec_elem = root.find("./rating-spec-id")
        if spec_elem is None:
            raise AbstractRatingException(
                "No <rating-spec-id> element in <simple-rating>"
            )
        if not specification:
            specification = RatingSpecification(etree.tostring(spec_elem).decode())
        vertical_datum_elem = root.find("./vertical-datum-info")
        if vertical_datum_elem is not None:
            vdi = ElevParameter._VerticalDatumInfo(
                etree.tostring(vertical_datum_elem).decode()
            )
            if specification.location.vertical_datum_info:
                if specification.location.vertical_datum_info != vdi:
                    raise AbstractRatingException(
                        f"{str(vdi)}\n does not equal location vertical datum info of\n"
                        f"{specification.location.vertical_datum_xml}"
                    )
            else:
                specification._location._vertical_datum_info = vdi
        units_elem = root.find("./units-id")
        if units_elem is None:
            raise AbstractRatingException("no <units-id> in <simple-rating>")
        units = re.split(r"[;,]", cast(str, units_elem.text))
        if len(units) != specification.template.ind_param_count + 1:
            raise AbstractRatingException(
                f"Expected {specification.template.ind_param_count+1} units in <units-id>, got {len(units)}"
            )
        effective_date_elem = root.find("./effective-date")
        if effective_date_elem is None:
            raise AbstractRatingException("No <effective-date> in <simple-rating>")
        effective_time_str = effective_date_elem.text
        effective_time = cast(datetime, HecTime(effective_time_str).datetime())
        if not effective_time:
            raise AbstractRatingException(
                f"Invalid <effective-date>: {effective_time_str}"
            )
        create_date_elem = root.find("./create-date")
        if create_date_elem is not None:
            create_time_str = create_date_elem.text
            create_time = HecTime(create_time_str).datetime()
            if not create_time:
                raise AbstractRatingException(
                    f"Invalid <create-date>: {create_time_str}"
                )
        transition_start_date_elem = root.find("./transition-start-date")
        if transition_start_date_elem is not None:
            transition_start_time_str = transition_start_date_elem.text
            transition_start_time = HecTime(transition_start_time_str).datetime()
            if not transition_start_time:
                raise AbstractRatingException(
                    f"Invalid <transition_start-date>: {transition_start_time_str}"
                )
        active_elem = root.find("./active")
        if active_elem is not None:
            active = etree.tostring(active_elem).decode() == "true"
        description_elem = root.find("./description")
        if description_elem is not None:
            description = etree.tostring(description_elem).decode()
        return (
            specification,
            active,
            units,
            effective_time,
            create_time,
            transition_start_time,
            description,
        )

    @classmethod
    def _raise_incompatible_xml_error(cls, root_tag: str) -> None:
        """
        Provides a consistent exception format for sub-classes when from_xml() is callsed with an incompatible XML instance

        Args:
            root_tag (the tag name of the incompatible root element): _description_

        Raises:
            AbstractRatingException:
        """
        raise AbstractRatingException(
            AbstractRating._INCOMPATIBLE_XML_MESSAGE % (root_tag, cls.__name__),
            root_tag,
        )

    @property
    def active(self) -> bool:
        """
        Whether the rating is marked as active

        Operations:
            Read/Write
        """
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {value.__class__.__name__}")

    @staticmethod
    def convert_units(
        values: Sequence[float], from_unit: str, to_unit: str
    ) -> Sequence[float]:
        """
        Converts a tuple or list of value from/to the specified units

        Args:
            values (Sequence[float]): The values to convert
            from_unit (str): The unit to convert from
            to_unit (str): The unit to convert to

        Returns:
            Sequence[float]: The converted values
        """
        converted1 = hec.unit.UnitQuantity(1.0, from_unit).to(to_unit).magnitude
        if np.isclose(1.0, converted1):
            # no conversion
            return values[:]
        else:
            converted2 = hec.unit.UnitQuantity(10.0, from_unit).to(to_unit).magnitude
            if np.isclose(10 * converted1, converted2):
                # scalar conversion
                converted_values = list(map(lambda x: x * converted1, values))
            else:
                # non-scalar conversion
                converted_values = list(
                    map(
                        lambda x: hec.unit.UnitQuantity(x, from_unit)
                        .to(to_unit)
                        .magnitude,
                        values,
                    )
                )
            return (
                tuple(converted_values)
                if isinstance(values, tuple)
                else converted_values
            )

    @property
    def create_time(self) -> Optional[datetime]:
        """
        The creation date/time of the rating, if any

        Operations:
            Read/Write
        """
        return self._create_time

    @create_time.setter
    def create_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if value is None:
            self._create_time = None
        elif isinstance(value, str):
            self._create_time = HecTime(str).datetime()
        elif isinstance(value, HecTime):
            self._create_time = value.datetime()
        elif isinstance(value, datetime):
            self._create_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @property
    def default_data_units(self) -> Optional[list[str]]:
        """
        The default data units, if any.

        The default data units are used if the [`rate`](#AbstractRating.rate) or [`reverse_rate`](#AbstractRating.reverse_rate)
        methods are called without any specified units.

        Operations:
            Read/Write
        """
        return self._default_data_units[:] if self._default_data_units else None

    @default_data_units.setter
    def default_data_units(self, value: Optional[list[str]]) -> None:
        if not isinstance(value, (type(None), list, tuple)):
            raise TypeError(f"Expected list or tuple, got {value.__class__.__name__}")
        if value is None:
            self._default_data_units = None
        else:
            if len(value) != self.template.ind_param_count:
                raise ValueError(
                    f"Expected list or tuple of length {self.template.ind_param_count+1}, got length of {len(value)}"
                )
            new_units: list[str] = []
            for i in range(len(value)):
                if not isinstance(value[i], str):
                    raise TypeError(
                        f"Expected str for 'value[{i}]', got {value[i].__class__.__name__}"
                    )
                param_name = (
                    self.template.ind_params[i]
                    if i < self.template.ind_param_count
                    else self.template.dep_param
                )
                try:
                    unit_name = hec.unit.get_unit_name(value[i])
                except:
                    raise ValueError(f"'{value[i]}' is not a valid unit name or alias")
                if value[i] not in Parameter(param_name).get_compatible_units():
                    raise ValueError(
                        f"'{value[i]}' is not a valid unit for parameter '{param_name}'"
                    )
                new_units.append(unit_name)
            self._default_data_units = new_units

    @property
    def default_data_vertical_datum(self) -> Optional[str]:
        """
        The default vertical datum for rating Elev parameter values.

        If not None, Elev parameter values will be converted to the default vertical datum before (input values) or after (output values) the rating is performed.

        If None, the native vertical datum will be used.

        When setting, must be None, NGVD-29, NAVD-99, or OTHER.

        Operations:
            Read/Write
        """
        return self._default_data_vertical_datum

    @default_data_vertical_datum.setter
    def default_data_vertical_datum(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if self._specification.location.vertical_datum_info is None:
            raise LocationException(
                f"Location {self._specification.location.name} doesn't have vertical datum info"
            )
        self._default_data_vertical_datum = (
            self._specification.location.vertical_datum_info.normalize_datum_name(value)
        )

    @property
    def description(self) -> Optional[str]:
        """
        The description of the rating object, if any.

        Operations:
            Read/Write
        """
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")

    @property
    def effective_time(self) -> datetime:
        """
        The effective date/time of the rating

        Operations:
            Read/Write
        """
        return self._effective_time

    @effective_time.setter
    def effective_time(self, value: Union[datetime, HecTime, str]) -> None:
        if isinstance(value, str):
            self._effective_time = cast(datetime, HecTime(str).datetime())
        elif isinstance(value, HecTime):
            self._effective_time = cast(datetime, value.datetime())
        elif isinstance(value, datetime):
            self._effective_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @staticmethod
    @abstractmethod
    def from_xml(
        xml_str: str, specification: Optional[RatingSpecification] = None
    ) -> "AbstractRating":
        """
        Creates a rating object from an XML instance

        Args:
            xml_str (str): The XML instance to create the rating from

        Raises:
            AbstractRatingException: if no subclass of AbstractRating has a registered from_xml()
            method that is compatible with the specified XML instance

        Returns:
            AbstractRating: The rating created from the XML instance
        """
        rating_tag: Optional[str] = None
        for classname in AbstractRating._from_xml_methods:
            try:
                return AbstractRating._from_xml_methods[classname](xml_str)
            except AbstractRatingException as e:
                if (
                    len(e.args) == 2
                    and isinstance(e.args[0], str)
                    and e.args[0].split("<")[0]
                    == AbstractRating._INCOMPATIBLE_XML_MESSAGE.split("<")[0]
                ):
                    rating_tag = e.args[1]
                else:
                    raise
        raise AbstractRatingException(
            f"No rating class is registered to initialize from <{rating_tag}>"
            if rating_tag
            else "Un-recognized XML structure"
        )

    @property
    def has_elev_param(self) -> bool:
        """
        Whether the rating has "Elev" as the base parameter for one of the indpendent parameters or the dependent parameter

        Operations:
            Read-Only
        """
        return (
            "Elev" in list(map(lambda s: s.split("-")[0], self.template.ind_params))
            or "Elev" == self.template.dep_param.split("-")[0]
        )

    def make_datum_offsets(self, vertical_datum: str) -> list[Optional[float]]:
        """
        Creates a list of offsets (in rating units) from the specified vertical datum to the rating native vertical datum plus
        the offset for from the rating native vertical datum to the specified vertical datum.

        All offsets except the last one are for independent parameter values in the same position. The last offset is for
        the dependent parameter value (hence the difference in offset direction).

        In any postion, the offset will be None if:
            * The parameter at that position is not an elevation parameter
            * The offset is zero

        Args:
            vertical_datum (str): The specified vertical datum

        Returns:
            list[Optional[float]]: The list of offsets.
        """
        datum_offsets: list[Any] = (self.template.ind_param_count + 1) * [
            None
        ]
        if self.has_elev_param and vertical_datum is not None:
            datum_offset: Optional[hec.unit.UnitQuantity] = None
            vd: Optional[str] = None
            if _ngvd29_pattern.match(vertical_datum):
                vd = _NGVD29
            elif _navd88_pattern.match(vertical_datum):
                vd = _NAVD88
            elif _other_datum_pattern.match(vertical_datum):
                vd = _OTHER_DATUM
            else:
                raise AbstractRatingException(
                    f"Invalid vertical datum: {vertical_datum}. Must be one of "
                    f"{_NGVD29}, {_NAVD88}, or {_OTHER_DATUM}"
                )
            if (
                self.vertical_datum_info
                and self.vertical_datum_info.native_datum
                and vd != self.vertical_datum_info.native_datum
            ):
                datum_offset = self.vertical_datum_info.get_offset_to(vd)
                if datum_offset is not None and datum_offset.magnitude:
                    for i in range(self.template.ind_param_count + 1):
                        if (
                            i < self.template.ind_param_count
                            and self.template.ind_params[i].startswith("Elev")
                        ) or (
                            i == self.template.ind_param_count
                            and self.template.dep_param.startswith("Elev")
                        ):
                            if (
                                self.vertical_datum_info.unit_name
                                != self._rating_units[i]
                            ):
                                datum_offsets[i] = datum_offset.to(
                                    self._rating_units[i]
                                ).magnitude * (
                                    1 if i == self.template.ind_param_count else -1
                                )
                            else:
                                datum_offsets[i] = datum_offset.magnitude * (
                                    1 if i == self.template.ind_param_count else -1
                                )
        return datum_offsets

    def make_reverse_datum_offsets(self, vertical_datum: str) -> list[Optional[float]]:
        """
        Creates a list of two vertical datum offsets (in rating units). The first is from the specified vertical datum to the
        rating native vertical datum; the second from the rating native vertical datum to the specified datum.

        The first offset will be None if the base parameter of the rating dependent parameter is not "Elev" or the offset is zero.
        The secons offset will be None if the base parameter of the (single) rating independent parameter is not "Elev" or the offset is zero.

        Args:
            vertical_datum (str): The specified vertical datum

        Returns:
            list[Optional[float]]: The list of offsets.
        """
        if self.template.ind_param_count != 1:
            raise AbstractRatingException(
                "Cannot call make_reverse_datum_offsets on a rating with more than one independent parameter"
            )
        datum_offsets: list[Any] = 2 * [None]
        if self.has_elev_param and vertical_datum is not None:
            datum_offset: Optional[hec.unit.UnitQuantity] = None
            vd: Optional[str] = None
            if _ngvd29_pattern.match(vertical_datum):
                vd = _NGVD29
            elif _navd88_pattern.match(vertical_datum):
                vd = _NAVD88
            elif _other_datum_pattern.match(vertical_datum):
                vd = _OTHER_DATUM
            else:
                raise AbstractRatingException(
                    f"Invalid vertical datum: {vertical_datum}. Must be one of "
                    f"{_NGVD29}, {_NAVD88}, or {_OTHER_DATUM}"
                )
            if (
                self.vertical_datum_info
                and self.vertical_datum_info.native_datum
                and vd != self.vertical_datum_info.native_datum
            ):
                datum_offset = self.vertical_datum_info.get_offset_to(vd)
                if datum_offset is not None and datum_offset.magnitude:
                    if self.template.dep_param.startswith("Elev"):
                        if self.vertical_datum_info.unit_name != self._rating_units[1]:
                            datum_offsets[0] = datum_offset.to(
                                self._rating_units[1]
                            ).magnitude
                        else:
                            datum_offsets[0] = datum_offset.magnitude
                    if self.template.ind_params[0].startswith("Elev"):
                        if self.vertical_datum_info.unit_name != self._rating_units[1]:
                            datum_offsets[0] = -datum_offset.to(
                                self._rating_units[1]
                            ).magnitude
                        else:
                            datum_offsets[0] = -datum_offset.magnitude
        return datum_offsets

    def make_reverse_unit_conversions(
        self, unit_list: list[str]
    ) -> list[Optional[Callable[[float], float]]]:
        """
        Creates a list of unit conversion functions (each optionally None for the identity function) for converting
        the dependent parameter values to rating units and the independent parameter value to specified unit

        Args:
            unit_list (list[str]): The list of [dependent parameter unit, independent parameter unit].

        Returns:
            list[Optional[Callable[[float], float]]]: The list of unit conversions. The first is for
                converting the specified unit to the rating dependent parameter unit. The
                second one is for converting from the rating independent parameter unit to the specified unit.
        """
        if self.template.ind_param_count != 1:
            raise AbstractRatingException(
                "Cannot call make_reverse_unit_conversions on a rating with more than one independent parameter"
            )
        if len(unit_list) != len(self._rating_units):
            raise AbstractRatingException(
                f"Expected {len(self._rating_units)} units for conversion, got {len(unit_list)}"
            )
        return [
            AbstractRating.make_unit_conversion(unit_list[0], self._rating_units[0]),
            AbstractRating.make_unit_conversion(self._rating_units[1], unit_list[1]),
        ]

    @staticmethod
    def make_unit_conversion(
        from_unit: str, to_unit: str
    ) -> Optional[Callable[[float], float]]:
        """
        Creates a function that converts a value from/to specified units

        Args:
            from_unit (str): The unit to convert from
            to_unit (str): The unit to conver to

        Returns:
            Optional[Callable[[float],float]]: The conversion function or None for the identity conversion
        """
        converted1 = hec.unit.UnitQuantity(1.0, from_unit).to(to_unit).magnitude
        if np.isclose(1.0, converted1):
            # no conversion
            return None
        else:
            converted2 = hec.unit.UnitQuantity(10.0, from_unit).to(to_unit).magnitude
            if np.isclose(10 * converted1, converted2):
                # scalar conversion
                return lambda x: x * converted1
            else:
                # non-scalar conversion
                return (
                    lambda x: hec.unit.UnitQuantity(x, from_unit).to(to_unit).magnitude
                )

    def make_unit_conversions(
        self, unit_list: list[str]
    ) -> list[Optional[Callable[[float], float]]]:
        """
        Creates a list of unit conversion functions (each optionally None for the identity function) for converting
        independent parameter values to rating units and the dependent parameter value to specified unit

        Args:
            unit_list (list[str]): The list of independent parameter units plus the dependent parameter unit.

        Returns:
            list[Optional[Callable[[float], float]]]: The list of unit conversions. All but the last one are for
                converting the specified unit to the rating unit for the independent parameter at that position. The
                last one is for converting from the rating dependent parameter unit to the specified unit.
        """
        if len(unit_list) != len(self._rating_units):
            raise AbstractRatingException(
                f"Expected {len(self._rating_units)} units for conversion, got {len(unit_list)}"
            )
        return [
            AbstractRating.make_unit_conversion(from_unit, to_unit)
            for from_unit, to_unit in zip(unit_list[:-1], self._rating_units[:-1])
        ] + [AbstractRating.make_unit_conversion(self._rating_units[-1], unit_list[-1])]

    @property
    def office(self) -> Optional[str]:
        """
        The rating's specification's office, if any

        Operations:
            Read-Only
        """
        return self._specification.template.office

    def populate_xml_element(self, rating_elem: etree._Element) -> etree._Element:
        """
        The info common to all ratings as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        rating_spec_id_elem = etree.SubElement(rating_elem, "rating-spec-id")
        rating_spec_id_elem.text = self.specification_id
        base_params = sorted(
            map(
                lambda s: s.split("-")[0],
                re.split(r"[;,]", self.specification_id.split(".")[1]),
            )
        )
        if "Elev" in base_params:
            if self.vertical_datum_info:
                vertical_datum_info_elem = etree.fromstring(
                    cast(str, self.vertical_datum_xml)
                )
                del vertical_datum_info_elem.attrib["office"]
                location_elem = vertical_datum_info_elem.find("location")
                if location_elem is not None:
                    vertical_datum_info_elem.remove(location_elem)
            else:
                vertical_datum_info_elem = etree.Element("vertical-datum-info")
            rating_elem.append(vertical_datum_info_elem)
        units_id_elem = etree.SubElement(rating_elem, "units-id")
        units_id_elem.text = (
            f"{','.join(self.rating_units[:-1])};{self.rating_units[-1]}"
        )
        effective_time_elem = etree.SubElement(rating_elem, "effective-date")
        effective_time_elem.text = self.effective_time.replace(
            microsecond=0
        ).isoformat()
        create_time_elem = etree.SubElement(rating_elem, "create-date")
        if self.create_time:
            create_time_elem.text = self.create_time.replace(microsecond=0).isoformat()
        transition_time_elem = etree.SubElement(rating_elem, "transition-start-date")
        if self.transition_start_time:
            transition_time_elem.text = self.transition_start_time.replace(
                microsecond=0
            ).isoformat()
        active_elem = etree.SubElement(rating_elem, "active")
        active_elem.text = "true" if self.active else "false"
        desciption_elem = etree.SubElement(rating_elem, "description")
        if self.description:
            desciption_elem.text = self.description
        return rating_elem

    def rate(
        self,
        input: Union[list[list[float]], TimeSeries, Sequence[TimeSeries]],
        *,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> Union[list[float], TimeSeries]:
        """
        Rates independent parameter values and returns dependent parameter values.

        Args:
            input (Union[list[list[float]], TimeSeries, Sequence[TimeSeries]]): The input parameter values.
                * If specified as a list of lists of floats:
                    * The list must be of the same length as the number of independent parameters of the rating.
                    * Each list of values must have the same times and be of the same length
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A list of floats is returned
                * If specified as a TimeSeries:
                    * The rating must have a single independent parameter
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
                * If specified as a list of TimeSeries:
                    * The list must be of the same length as the number of independent parameters of the rating.
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
            units (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies units of the independent parameter values and the rated values. A comma-delimited string of
                  independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None. If not specified or None, the rating's
                  default data units are used, if specified. If the rating has no default data units, the rating units are used.
                * If specified as a TimeSeries or list of TimeSeries, this specifies the unit of the rated time series. If not specified or None, rating's default
                  data unit for the dependent parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            vertical_datum (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies the vertical datum of any input elevation value and the desired vertical datum of any
                  output elevation values. If None, or not specified, the location's native vertical datum is used.
                * If specified as a TimeSeries or list of TimeSeries, this specifies the desired vertical datum for any output elevation values. Any input elevation
                  values will be in the vertical datum of the input time series.
            round (bool, optional, must be passed by name): Whether to use the rating's specification's dependent rounding specification . Defaults to False.

        Returns:
            Union[list[float], TimeSeries]: The dependent parameter values as described in `input` above
        """
        if isinstance(input, TimeSeries):
            return self.rate_time_series(ts=input, unit=units, round=round)
        elif isinstance(input, list) and isinstance(input[0], TimeSeries):
            return self.rate_time_series(
                ts=cast(list[TimeSeries], input),
                unit=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        elif (
            isinstance(input, list)
            and isinstance(input[0], list)
            and isinstance(input[0][0], float)
        ):
            return self.rate_values(
                ind_values=cast(list[list[float]], input),
                units=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        else:
            raise TypeError(f"Unexpected type for input: {input.__class__.__name__}")

    def rate_time_series(
        self,
        ts: Union[TimeSeries, Sequence[TimeSeries]],
        unit: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> TimeSeries:
        """
        Rates an independent parameter time series (or list of such) and returns a dependent parameter time series

        Args:
            ts (Union[TimeSeries, Sequence[TimeSeries]]): If a list/tuple of TimeSeries:
                * Must be the same number as the number of independent parameters of the rating.
                * Each time series must have the same times.
            unit (Optional[str]): The unit of the rated time series. If not specified or None, rating's default data unit for the dependent
                parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            vertical_datum (Optional[str]): The desired vertical datum for any output elevation time series. Any input elevation time series are expected
                to specify their own vertical datums. Defaults to None, in which case the location's native vertical datum is used.
            round (bool, optional): Whether to use the rating's specification's dependent rounding specification . Defaults to False.

        Returns:
            TimeSeries: The rated (dependent value) time series
        """
        ts_list: list[TimeSeries]
        if isinstance(ts, (tuple, list)):
            for i in range(len(ts)):
                if not isinstance(ts[i], TimeSeries):
                    raise TypeError(
                        f"Expected TimeSeries for ts[{i}], got {ts[i].__class__.__name__}"
                    )
            ts_list = list(ts)
        elif isinstance(ts, TimeSeries):
            ts_list = [ts]
        else:
            raise TypeError(
                f"Expected TimeSeries or list/tuple of TimeSeries for parameter ts, got {ts.__class__.__name__}"
            )
        ts_count = len(ts_list)
        for i in range(ts_count):
            if (
                ts_list[i].parameter.base_parameter == "Elev"
                and ts_list[i].vertical_datum_info is not None
            ):
                if (
                    cast(
                        hec.parameter.ElevParameter._VerticalDatumInfo,
                        ts_list[i].vertical_datum_info,
                    ).native_datum
                    is None
                ):
                    raise AbstractRatingException(
                        f"Time series {ts_list[i].name} must have native vertical datum info since vertical "
                        f"datum of {vertical_datum} is specified to rate_time_series() method"
                    )
                ts_list[i] = ts_list[i].to(
                    cast(
                        str,
                        cast(
                            hec.parameter.ElevParameter._VerticalDatumInfo,
                            ts[i].vertical_datum_info,
                        ).native_datum,
                    )
                    if vertical_datum is None
                    else vertical_datum
                )
        expected_ts_count = self._specification.template.ind_param_count
        if ts_count != expected_ts_count:
            raise ValueError(
                f"Expected {expected_ts_count} time series in ts, got {ts_count}"
            )
        time_strs = ts_list[0].times
        for i in range(1, ts_count):
            if ts_list[i].times != time_strs:
                raise ValueError(
                    f"Times for {ts[i].name} aren't the same as for {ts[0].name}"
                )
        values = [t.values for t in ts_list]
        times = [datetime.fromisoformat(t) for t in time_strs]
        dep_unit = (
            unit
            if unit
            else (
                self._default_data_units[-1]
                if self._default_data_units is not None
                else Parameter(self.template.dep_param).unit_name
            )
        )
        if len(ts_list[0]) > 0:
            units = f"{','.join([t.unit for t in ts_list])};{dep_unit}"
            rated_values = self.rate_values(
                ind_values=values,
                units=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts_list[0].copy()
        if self.template.dep_param.startswith("Elev") and self.vertical_datum_info:
            vdi = self.vertical_datum_info.copy()
            vdi.unit_name = dep_unit
            elev_param = hec.parameter.ElevParameter(
                self.template.ind_params[0], str(vdi)
            )
            if vertical_datum:
                elev_param.current_datum = vertical_datum
            rated_ts.iset_parameter(elev_param)
        else:
            rated_ts.iset_parameter(Parameter(self.template.dep_param, dep_unit))
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def rate_values(
        self,
        ind_values: list[list[float]],
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> list[float]:
        """
        Rates list(s) of independent parameter values

        Args:
            ind_values (list[list[float]]): The independent parameter values. Values for each parameter are in its own list
                in the same order as the rating independent parameters. All parameter lists must be of the same length.
            units (Optional[str]): The units of the independent parameter values and the rated values. A comma-delimited string of
                independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None.
                * If not specified, the rating's default data units are used, if specified. If the rating has no default data units,
                    the rating units are used.
            vertical_datum (Optional[str]): The vertical datum of any input elevation values and the desired vertical datum of any
                output elevation values. Defaults to None, in which case the location's native datum is assumed.
            round (bool, optional): Whether to use the rating's specification's dependent rounding specification . Defaults to False.

        Returns:
            list[float]: The rated (dependent parameter) values
        """
        raise AbstractRatingException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

    @property
    def rating_units(self) -> list[str]:
        """
        The native units of the rating, one for each independent parameter, plus the dependent parameter

        Operations:
            Read-Only
        """
        return self._rating_units[:]

    def reverse_rate(
        self,
        input: Union[list[float], TimeSeries],
        *,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> Union[list[float], TimeSeries]:
        """
        Rates dependent parameter values and returns independent parameter values.

        Args:
            input (Union[list[float], TimeSeries]): The input parameter values.
                * If specified as a lists of floats:
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A list of floats is returned
                * If specified as a TimeSeries:
                    * The rating must have a single independent parameter
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
            units (Optional[str], optional, must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies units of the independent parameter values and the rated values. A comma-delimited string of
                  independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None. If not specified or None, the rating's
                  default data units are used, if specified. If the rating has no default data units, the rating units are used.
                * If specified as a TimeSeries or list of TimeSeries, this specifies the unit of the rated time series. If not specified or None, rating's default
                  data unit for the dependent parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            round (bool, optional, must be passed by name): Whether to use the rating's specification's dependent rounding specification . Defaults to False.

        Returns:
            Union[list[float], TimeSeries]: The dependent parameter values as described in `input` above
        """
        if isinstance(input, TimeSeries):
            return self.reverse_rate_time_series(
                ts=input,
                unit=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        elif isinstance(input, list) and isinstance(input[0], float):
            return self.reverse_rate_values(
                dep_values=input,
                units=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        else:
            raise TypeError(f"Unexpected type for input: {input.__class__.__name__}")

    def reverse_rate_time_series(
        self,
        ts: TimeSeries,
        unit: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> TimeSeries:
        """
        Reverse rates a dependent parameter time series and returns an independent parameter time series

        Args:
            ts (TimeSeries): The dependent value time series to reverse-rate
            unit (Optional[str]): The unit of the rated time series. If not specified or None, rating's default data unit for the independent
                parameter, if any, is used. Otherwise, the independent parameter's default unit will be used.
            vertical_datum (Optional[str]): The desired vertical datum of any output elevation time series. Any input elevation time series is
                expected to specify its own vertical datum. Defaults to None, in which case the location's native vertical datum will be used.
            round (bool, optional): Whether to use the rating's specification's independent rounding specification . Defaults to False.

        Returns:
            TimeSeries: The rated (independent value) time series
        """
        if not isinstance(ts, TimeSeries):
            raise TypeError(f"Expected TimeSeries for ts, got {ts.__class__.__name__}")
        ind_unit = (
            unit
            if unit
            else (
                self._default_data_units[0]
                if self._default_data_units
                else Parameter(self.template.ind_params[0]).unit_name
            )
        )
        if len(ts) > 0:
            units = f"{ind_unit};{ts.unit}"
            rated_values = self.reverse_rate_values(
                dep_values=ts.values,
                units=units,
                vertical_datum=vertical_datum,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts.copy()
        if self.template.ind_params[0].startswith("Elev") and self.vertical_datum_info:
            vdi = self.vertical_datum_info.copy()
            vdi.unit_name = ind_unit
            elev_param = hec.parameter.ElevParameter(
                self.template.ind_params[0], str(vdi)
            )
            if vertical_datum:
                elev_param.current_datum = vertical_datum
            rated_ts.iset_parameter(elev_param)
        else:
            rated_ts.iset_parameter(Parameter(self.template.ind_params[0], ind_unit))
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def reverse_rate_values(
        self,
        dep_values: list[float],
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> list[float]:
        """
        Rates a list of dependent parameter values.

        May only be used on ratings with a single independent parameter.

        Args:
            dep_values (list[float]): The dependent parameter values.
            units (Optional[str]): The units of the independent parameter values and the rated values.A comma-delimited string of
                independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None.
                * If not specified, the rating's default data units are used, if specified. If the rating has no default data units,
                    the rating units are used.
            vertical_datum (Optional[str]): The vertical datum of any input elevation values and the desired vertical datum of any
                output elevation values. Defaults to None, in which case the location's native vertical datum will be used.
            round (bool, optional): Whether to use the rating's specification's independent rounding specification . Defaults to False.

        Returns:
            list[float]: The rated (independent parameter) values
        """
        raise AbstractRatingException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

    @property
    def specification(self) -> RatingSpecification:
        """
        A copy of the rating's specification

        Operations:
            Read-Only
        """
        return self._specification.copy()

    @property
    def specification_id(self) -> str:
        """
        The rating's specification identifer

        Operations:
            Read-Only
        """
        return self._specification.name

    @property
    def template(self) -> RatingTemplate:
        """
        A copy of the rating's template

        Operations:
            Read-Only
        """
        return self._specification.template.copy()

    @property
    def template_id(self) -> str:
        """
        The rating's template identifer

        Operations:
            Read-Only
        """
        return self._specification.template.name

    def to_xml(self, indent: str = "  ", prepend: Optional[str] = None) -> str:
        """
        Returns a formatted xml representation of the rating.

        For unformatted xml use `etree.tostring(<template_obj>.xml_element)`

        Args:
            indent (str, optional): The string to use for each level of indentation. Defaults to "  ".
            prepend (Optional[str], optional): A string to prepend to each line. Defaults to None.

        Returns:
            str: The formatted xml
        """
        xml: str = etree.tostring(self.xml_element, pretty_print=True).decode()
        if indent != "  ":
            xml = replace_indent(xml, indent)
        if prepend:
            xml = "".join([prepend + line for line in xml.splitlines(keepends=True)])
        return xml

    @property
    def transition_start_time(self) -> Optional[datetime]:
        """
        The date/time of beginning of transition from the previous rating, if any

        Operations:
            Read/Write
        """
        return self._transition_start_time

    @transition_start_time.setter
    def transition_start_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if not value:
            self._transition_start_time = None
        elif isinstance(value, str):
            self._transition_start_time = HecTime(str).datetime()
        elif isinstance(value, HecTime):
            self._transition_start_time = value.datetime()
        elif isinstance(value, datetime):
            self._transition_start_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @property
    def vertical_datum_info(self) -> Optional[ElevParameter._VerticalDatumInfo]:
        """
        The vertical datum info of the rating's specification's location, if any

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_info

    @property
    def vertical_datum_json(self) -> Optional[str]:
        """
        The vertical datum info of the rating's specification's location, if any, as a JSON object

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_json

    @property
    def vertical_datum_xml(self) -> Optional[str]:
        """
        The vertical datum info of the rating's specification's location, if any, as an XML instance

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_xml

    @property
    @abstractmethod
    def xml_element(self) -> etree._Element:
        """
        The rating as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        raise AbstractRatingException("Method must be called on a sub-class")

    @abstractmethod
    def xml_tag_name(self) -> str:
        """
        The XML tag name for this rating type

        Oprations:
            Read-Only
        """
        raise AbstractRatingException("Method must be called on a sub-class")
