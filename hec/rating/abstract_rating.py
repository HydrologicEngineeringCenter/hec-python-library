import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional, Union, cast

from lxml import etree

import hec.shared
import hec.unit
from hec.hectime import HecTime
from hec.location import LocationException
from hec.parameter import ElevParameter, Parameter
from hec.rating.rating_shared import replace_indent
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate


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
                specification.location.vertical_datum_info = vdi
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
        if self.vertical_datum_info:
            rating_elem.append(etree.fromstring(cast(str, self.vertical_datum_xml)))
        units_id_elem = etree.SubElement(rating_elem, "units-id")
        units_id_elem.text = (
            f"{','.join(self.template.ind_params)};{self.template.dep_param}"
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
        return rating_elem

    @abstractmethod
    def rate(self, value: Any) -> Any:
        raise AbstractRatingException("Method must be called on a sub-class")

    @property
    def rating_units(self) -> list[str]:
        """
        The native units of the rating, one for each independent parameter, plus the dependent parameter

        Operations:
            Read-Only
        """
        return self._rating_units[:]

    @abstractmethod
    def xml_tag_name(self) -> str:
        """
        The XML tag name for this rating type

        Oprations:
            Read-Only
        """
        raise AbstractRatingException("Method must be called on a sub-class")

    @abstractmethod
    def reverse_rate(self, value: Any) -> Any:
        raise AbstractRatingException("Method must be called on a sub-class")

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

    def to_xml(self, indent: str = "  ", prepend: Optional[str] = None) -> str:
        """
        Returns a formatted xml representation of the rating template.

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
