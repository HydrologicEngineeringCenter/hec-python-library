import re
import warnings
from typing import Any, Optional, Sequence, Union

from lxml import etree

from hec.location import Location, _is_cwms_location
from hec.rating.rating_shared import LookupMethod, replace_indent
from hec.rating.rating_template import RatingTemplate
from hec.shared import RatingException

DEFAULT_IN_RANGE_METHOD = LookupMethod.LINEAR
DEFAULT_OUT_RANGE_LOW_METHOD = LookupMethod.NEXT
DEFAULT_OUT_RANGE_HIGH_METHOD = LookupMethod.PREVIOUS
DEFAULT_ROUNDING_SPEC = "4444444449"


def _is_rating_specification(id: str) -> bool:
    parts = id.split(".")
    if len(parts) != 4:
        return False
    if not _is_cwms_location(parts[0]):
        return False
    if not parts[2] or not parts[3]:
        return False
    parts = parts[1].split(";")
    if not len(parts) == 2:
        return False
    return True


class RatingSpecificationException(RatingException):
    pass


class RatingSpecification:
    """
    Holds the following information about ratings and rating sets;

    - rating idendifier, comprised of
      - location identifier
      - template identifier
        - independent parameters
        - dependent parameter
        - template version
      - specification version
    - source agency
    - [lookup methods](rating.html#LookupMethod) for multiple effective dates in rating sets
      - method for value times within the range of effective dates
      - method for value times before the earliest effective date
      - method for value times after the latest effective date
    - [rounding specifications](../hec/rounding.html#UsgsRounder)
      - one for each independent parameter
      - one for the dependent parameter
    - whether the specification is active (should be used)
    - whether the ratings with this specification should be automatically updated from the source agency
    - whether automatically updated ratings should be set to active
    - whether automatically updated ratings should have any rating extension migrated to the new rating
    - a description of the rating specification
    """

    def __init__(self, name: str, **kwargs: Any):
        """
        Actual docstring is in /hec/rating.__init__.py so that it can have dynamic content
        """
        self._location: Location
        self._template: RatingTemplate
        self._version: str
        self._agency: Optional[str] = None
        self._in_range_method = DEFAULT_IN_RANGE_METHOD
        self._out_range_low_method = DEFAULT_OUT_RANGE_LOW_METHOD
        self._out_range_high_method = DEFAULT_OUT_RANGE_HIGH_METHOD
        self._ind_rounding: list[str] = []
        self._dep_rounding = DEFAULT_ROUNDING_SPEC
        self._active: bool = True
        self._auto_update: bool = False
        self._auto_activate: bool = False
        self._auto_migrate_extension: bool = False
        self._description: Optional[str] = None
        if not isinstance(name, str):
            raise TypeError(f"Expected str for 'name', got {name.__class__.__name__}")
        parts = name.split(".")
        if len(parts) != 4:
            raise ValueError(
                f"Name must be of format <location>.<ind-params>;<dep-param>.<template-version>.<specification-version>, got {name}"
            )
        self._location = Location(parts[0])
        self._template = RatingTemplate(".".join(parts[1:3]))
        if not parts[3]:
            raise ValueError("Version cannot be an empty string")
        self._version = parts[3]

        kw: Any
        argval: Any

        def assert_type(argtype: Union[type, tuple[type, type]]) -> None:
            nonlocal kw, argval
            if not isinstance(argval, argtype):
                raise TypeError(
                    f"Expected {argtype} for '{kw}', got {argval.__class__.__name__}"
                )

        for kw in kwargs:
            argval = kwargs[kw]
            if kw == "location":
                assert_type(Location)
                if argval.name != self._location.name:
                    raise RatingSpecificationException(
                        f"Expected location ID to be {self._location.name}, got {argval.name}"
                    )
                self._location = argval.copy()
            elif kw == "template":
                assert_type(RatingTemplate)
                if argval.name != self._template.name:
                    raise RatingSpecificationException(
                        f"Expected template ID to be {self._template.name}, got {argval.name}"
                    )
                self._template = argval.copy()
            elif kw == "office":
                assert_type(str)
                if self._location.office and self._location.office != argval:
                    warnings.warn(
                        f"Overriding existing location office of {self._location.office} with specified office of {argval}"
                    )
                if self._template.office and self._template.office != argval:
                    warnings.warn(
                        f"Overriding existing template office of {self._template.office} with specified office of {argval}"
                    )
                self._location.office = argval
                self._template.office = argval
            elif kw == "agency":
                assert_type((str, type(None)))
                self._agency = argval
            elif kw == "lookup":
                self.lookup = argval
            elif kw == "rounding":
                self.rounding = argval
            elif kw == "active":
                assert_type(bool)
                self.active = argval
            elif kw == "auto_update":
                assert_type(bool)
                self.auto_update = argval
            elif kw == "auto_activate":
                assert_type(bool)
                self.auto_activate = argval
            elif kw == "auto_migrate_extension":
                assert_type(bool)
                self.auto_migrate_extension = argval
            elif kw == "description":
                assert_type((str, type(None)))
                self.description = argval
            else:
                raise TypeError(
                    f"'{kw}' is an invalid keyword argument for RatingSpecification()"
                )
        if self._location.office != self._template.office:
            if self._template.office:
                raise RatingSpecificationException(
                    f"Rating specification for office {self._location.office} cannot use template from {self._template.office}"
                )
            else:
                self._template.office = self._location.office

        if "rounding" not in kwargs:
            self._ind_rounding = self._template.ind_param_count * [
                DEFAULT_ROUNDING_SPEC
            ]

        if self._template.office and not self._location.office:
            self._location.office = self._template.office

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RatingSpecification):
            return False
        if other.name != self.name:
            return False
        if other.location != self.location:
            return False
        if other.template != self.template:
            return False
        if other.rounding != self.rounding:
            return False
        if other._agency != self._agency:
            return False
        if other._auto_update != self._auto_update:
            return False
        if other._auto_activate != self._auto_activate:
            return False
        if other._auto_migrate_extension != self._auto_migrate_extension:
            return False
        return True

    def __repr__(self) -> str:
        default_lookup = [
            DEFAULT_IN_RANGE_METHOD.name,
            DEFAULT_OUT_RANGE_LOW_METHOD.name,
            DEFAULT_OUT_RANGE_HIGH_METHOD.name,
        ]
        default_template_lookup = self.template.ind_param_count * [
            [
                DEFAULT_IN_RANGE_METHOD.name,
                DEFAULT_OUT_RANGE_LOW_METHOD.name,
                DEFAULT_OUT_RANGE_HIGH_METHOD.name,
            ]
        ]
        default_rounding = (self.template.ind_param_count + 1) * [DEFAULT_ROUNDING_SPEC]
        _repr = f"hec.rating.RatingSpecification({self.name}"
        office_included = False
        if (
            self.location._latitude
            or self.location._longitude
            or self.location._horizontal_datum
            or self.location._elevation
            or self.location._vertical_datum
            or self.location._time_zone
            or self.location._kind
            or self.location._vertical_datum_info
        ):
            _repr += f", location={repr(self.location)}"
            office_included = True
        if self.template.lookup != default_template_lookup or self.template.description:
            _repr += f", template={repr(self.template)}"
            office_included = True
        if self.location.office and not office_included:
            _repr += f", office='{self.location.office}'"
        if self.lookup != default_lookup:
            _repr += f", lookup={self.lookup}"
        if self.rounding != default_rounding:
            _repr += f", rounding={self.rounding}"
        _repr += ")"
        return _repr

    def __str__(self) -> str:
        return self.name

    @property
    def active(self) -> bool:
        """
        Whether ratings using this specification are active (should be used)

        Operations:
            Read/Write
        """
        return self._active

    @active.setter
    def active(self, active: bool) -> None:
        self._active = active

    @property
    def agency(self) -> Optional[str]:
        """
        The agency responsible for generating ratings using this specification

        Operations:
            Read/Write
        """
        return self._agency

    @agency.setter
    def agency(self, agency: Optional[str]) -> None:
        self._agency = agency

    @property
    def auto_update(self) -> bool:
        """
        Whether the ratings with this specification should be automatically updated from the source agency

        Operations:
            Read/Write
        """
        return self._auto_update

    @auto_update.setter
    def auto_update(self, auto_update: bool) -> None:
        self._auto_update = auto_update

    @property
    def auto_activate(self) -> bool:
        """
        Whether automatically updated ratings should be set to active

        Operations:
            Read/Write
        """
        return self._auto_activate

    @auto_activate.setter
    def auto_activate(self, auto_activate: bool) -> None:
        self._auto_activate = auto_activate

    @property
    def auto_migrate_extension(self) -> bool:
        """
        Whether automatically updated ratings should have any rating extension migrated to the new rating

        Operations:
            Read/Write
        """
        return self._auto_migrate_extension

    @auto_migrate_extension.setter
    def auto_migrate_extension(self, auto_migrate_extension: bool) -> None:
        self._auto_migrate_extension = auto_migrate_extension

    def copy(self) -> "RatingSpecification":
        """
        Creates and returns a copy of this specificaiton

        Returns:
            RatingSpecification: The copy
        """
        # if kw == "location":
        #     assert_type(Location)
        #     if argval.name != self._location.name:
        #         raise RatingSpecificationException(
        #             f"Expected location ID to be {self._location.name}, got {argval.name}"
        #         )
        #     self._location = argval.copy()
        # elif kw == "template":
        #     assert_type(RatingTemplate)
        #     if argval.name != self._template.name:
        #         raise RatingSpecificationException(
        #             f"Expected template ID to be {self._template.name}, got {argval.name}"
        #         )
        #     self._template = argval.copy()
        # elif kw == "office":
        #     assert_type(str)
        #     if self._location.office and self._location.office != argval:
        #         warnings.warn(
        #             f"Overriding existing location office of {self._location.office} with specified office of {argval}"
        #         )
        #     if self._template.office and self._template.office != argval:
        #         warnings.warn(
        #             f"Overriding existing template office of {self._template.office} with specified office of {argval}"
        #         )
        #     self._location.office = argval
        #     self._template.office = argval
        # elif kw == "agency":
        #     assert_type((str, type(None)))
        #     self._agency = argval
        # elif kw == "lookup":
        #     self.lookup = argval
        # elif kw == "rounding":
        #     self.rounding = argval
        # elif kw == "active":
        #     assert_type(bool)
        #     self.active = argval
        # elif kw == "auto_update":
        #     assert_type(bool)
        #     self.auto_update = argval
        # elif kw == "auto_activate":
        #     assert_type(bool)
        #     self.auto_activate = argval
        # elif kw == "auto_migrate_extension":
        #     assert_type(bool)
        #     self.auto_migrate_extension = argval
        # elif kw == "description":
        #     assert_type(str)
        #     self.description = argval

        copy = RatingSpecification(
            self.name,
            location=self.location,
            template=self.template,
            agency=self._agency,
            lookup=self.lookup,
            rounding=self.rounding,
            active=self._active,
            auto_update=self._auto_update,
            auto_activate=self._auto_activate,
            auto_migrate_extension=self._auto_migrate_extension,
            description=self.description,
        )
        return copy

    @property
    def description(self) -> Optional[str]:
        """
        The description of the rating specification

        Operations:
            Read/Write
        """
        return self._description

    @description.setter
    def description(self, description: Optional[str]) -> None:
        self._description = description

    @staticmethod
    def from_xml(xml: str) -> "RatingSpecification":
        """
        Generates a RatingSpecification object from an XML string representation

        Args:
            xml (str): The XML string representation

        Raises:
            RatingSpecificationException: if there is an error in the XML string

        Returns:
            RatingSpecification: The generated RatingSpecification object
        """

        def str_to_bool(s: Optional[str]) -> Optional[bool]:
            if s is None:
                return None
            if s not in ("true", "false"):
                raise RatingSpecificationException(
                    f"Expected value of true or false, got {s}"
                )
            return s == "true"

        spec_elem = etree.fromstring(xml)
        if spec_elem.tag != "rating-spec":
            raise RatingSpecificationException(
                f"Expected <rating-spec>, got <{spec_elem.tag}>"
            )
        office = spec_elem.get("office-id")
        if not office:
            raise RatingSpecificationException(
                "No office specified in <rating-template>"
            )
        spec_id = spec_elem.findtext("rating-spec-id")
        if not spec_id:
            raise RatingSpecificationException("No data found for <rating-spec-id>")
        parts = spec_id.split(".")
        if len(parts) != 4:
            raise RatingSpecificationException(f"Invalid <rating-spec-id> of {spec_id}")
        template = ".".join(parts[1:3])
        ind_param_count = len(parts[1].split(","))
        template_id = spec_elem.findtext("template-id")
        if not template_id:
            raise RatingSpecificationException("No data found for <template-id>")
        if template_id != template:
            raise RatingSpecificationException(
                f"<template-id> of {template_id} doesn't match template specified in <rating-spec-id> of {template}"
            )
        location_id = spec_elem.findtext("location-id")
        if not location_id:
            raise RatingSpecificationException(f"No data found for <location-id>")
        if location_id != parts[0]:
            raise RatingSpecificationException(
                f"<location-id> of {location_id} doesn't match location specified in <rating-spec-id> of {parts[0]}"
            )
        version = spec_elem.findtext("version")
        if not version:
            raise RatingSpecificationException(f"No data found for <version>")
        if version != parts[3]:
            raise RatingSpecificationException(
                f"<version> of {version} doesn't match location specified in <rating-spec-id> of {parts[3]}"
            )
        agency = spec_elem.findtext("source-agency")
        in_range_method = spec_elem.findtext("in-range-method")
        if not in_range_method:
            raise RatingSpecificationException(f"No data found for <in-range-method>")
        out_range_low_method = spec_elem.findtext("out-range-low-method")
        if not out_range_low_method:
            raise RatingSpecificationException(
                f"No data found for <out-range-low-method>"
            )
        out_range_high_method = spec_elem.findtext("out-range-high-method")
        if not out_range_high_method:
            raise RatingSpecificationException(
                f"No data found for <out-range-high-method>"
            )
        active = str_to_bool(spec_elem.findtext("active"))
        auto_update = str_to_bool(spec_elem.findtext("auto-update"))
        auto_activate = str_to_bool(spec_elem.findtext("auto-activate"))
        auto_migrate_extension = str_to_bool(
            spec_elem.findtext("auto-migrate-extension")
        )
        ind_rounding = []
        ind_rounding_specs_elems = spec_elem.findall("./ind-rounding-specs")
        if len(ind_rounding_specs_elems) > 1:
            raise RatingSpecificationException(
                f"Expected 0 or 1 <ind-rounding-specs> element, got {len(ind_rounding_specs_elems)}"
            )
        if ind_rounding_specs_elems:
            ind_rounding_spec_elems = ind_rounding_specs_elems[0].findall(
                "./ind-rounding-spec"
            )
            if len(ind_rounding_spec_elems) != ind_param_count:
                raise RatingSpecificationException(
                    f"Expected {ind_param_count} <ind-rounding-spec> elements, got {len(ind_rounding_spec_elems)}"
                )
            for i in range(ind_param_count):
                pos = ind_rounding_spec_elems[i].get("position")
                if pos is None or not pos.isdigit() or int(pos) != i + 1:
                    raise RatingSpecificationException(
                        f'Expected attribute of position="{i+1}" on <ind-rounding-spec>[{i}], got {pos}'
                    )
                ind_rounding.append(ind_rounding_spec_elems[i].text)
        dep_rounding = spec_elem.findtext("dep-rounding-spec")
        description = spec_elem.findtext("description")
        kwargs: dict[str, Any] = {
            "office": office,
            "lookup": [in_range_method, out_range_low_method, out_range_high_method],
            "agency": agency,
            "active": active,
            "auto_update": auto_update,
            "auto_activate": auto_activate,
            "auto_migrate_extension": auto_migrate_extension,
            "description": description,
        }
        if ind_rounding or dep_rounding:
            rounding = ind_rounding if ind_rounding else 3 * [DEFAULT_ROUNDING_SPEC]
            rounding.append(dep_rounding if dep_rounding else DEFAULT_ROUNDING_SPEC)
            kwargs["rounding"] = rounding
        return RatingSpecification(spec_id, **kwargs)

    @property
    def location(self) -> Location:
        """
        The location object of the specification

        Operations:
            Read/Write
        """
        return self._location.copy()

    @location.setter
    def location(self, value: Union[Location, str]) -> None:
        if isinstance(value, str):
            self._location = Location(value)
            self._location.office = self._template.office
        elif isinstance(value, Location):
            if (
                value.office
                and self._template.office
                and value.office != self._template.office
            ):
                raise ValueError(
                    f"Cannot assign a location with office='{value.office}' to a rating specification with a template office='{self.template.office}'"
                )
            self._location = value.copy()
            if self._location.office:
                self._template.office = self._location.office
            else:
                self.location.office = self.template.office
        else:
            raise TypeError(f"Expected str or Location, got {value.__class__.__name__}")

    @property
    def lookup(self) -> list[str]:
        """
        The lookup methods of the specification

        Operations:
            Read/Write
        """
        return [
            self._in_range_method.name,
            self._out_range_low_method.name,
            self._out_range_high_method.name,
        ]

    @lookup.setter
    def lookup(self, value: Sequence[Union[str, int]]) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                f"Expected list or tuple for 'value', got {value.__class__.__name__}"
            )
        if len(value) != 3:
            raise ValueError(f"Expected 'value' to be len = 3, got len = {len(value)}")
        for i in range(3):
            if not isinstance(value[i], (str, int)):
                raise TypeError(
                    f"Expected str or int for 'value[{i}]', got {value[i].__class__.__name__}"
                )
        self._in_range_method = LookupMethod.get(value[0])
        self._out_range_low_method = LookupMethod.get(value[1])
        self._out_range_high_method = LookupMethod.get(value[2])

    @property
    def name(self) -> str:
        """
        The specification identifier

        Operations:
            Read-Only
        """
        return f"{self.location.name}.{self.template.name}.{self.version}"

    @property
    def rounding(self) -> list[str]:
        """
        The rounding specifications of the specification

        Operations:
            Read/Write
        """
        return self._ind_rounding + [self._dep_rounding]

    @rounding.setter
    def rounding(self, value: list[str]) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list or tuple, got {value.__class__.__name__}")
        if len(value) != self._template.ind_param_count + 1:
            raise ValueError(
                f"Expected {self._template.ind_param_count + 1} items, got {len(value)}"
            )
        for i in range(len(value)):
            if not isinstance(value[i], str):
                raise TypeError(
                    f"Expected str for 'value[{i}]', got {value[i].__class__.__name__}"
                )
            if not value[i].isdigit() or len(value[i]) != 10:
                raise TypeError(
                    f"Expected 10-digit str for 'value[{i}]', got '{value[i]}'"
                )
        self._ind_rounding = value[:-1]
        self._dep_rounding = value[-1]

    @property
    def template(self) -> RatingTemplate:
        """
        The RatingTemplate of the specification

        Operations:
            Read/Write
        """
        return self._template.copy()

    @template.setter
    def template(self, value: RatingTemplate) -> None:
        if not isinstance(value, RatingTemplate):
            raise TypeError(
                f"Expected RatingTemplate for 'template', got {value.__class__.__name__}"
            )
        if (
            value.office
            and self.location.office
            and value.office != self.location.office
        ):
            raise ValueError(
                f"Cannot assign a template with office='{value.office}' to a rating specification with a location office='{self.location.office}'"
            )
        self._template = value.copy()
        if self.location.office:
            self.template.office = self.location.office
        else:
            self.location.office = self.template.office

    def to_xml(self, indent: str = "  ", prepend: str = "") -> str:
        """
        Returns a formatted xml representation of the rating specification.

        For unformatted xml use `etree.tostring(<specification_obj>.xml_element)`

        Args:
            indent (str, optional): The string to use for each level of indentation. Defaults to "  ".
            prepend (Optional[str], optional): A string to prepend to each line. Defaults to None.

        Returns:
            str: The formatted xml
        """
        elem = self.xml_element
        for e in elem.iter():
            if e.text and e.text.strip() == "":
                e.text = None
            if e.tail and e.tail.strip() == "":
                e.tail = None
        xml: str = etree.tostring(elem, pretty_print=True).decode()
        if indent != "  ":
            xml = replace_indent(xml, indent)
        if prepend:
            xml = "".join([prepend + line for line in xml.splitlines(keepends=True)])
        return xml

    @property
    def version(self) -> str:
        """
        The version string of the specification

        Operations:
            Read/Write
        """
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if not value:
            raise ValueError("version cannot be an empty string")
        self._version = value

    @property
    def xml_element(self) -> etree._Element:
        """
        The rating specification as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        spec_elem = etree.Element(
            "rating-spec",
            attrib={"office-id": self.template.office if self.template.office else ""},
        )
        spec_id_elem = etree.SubElement(spec_elem, "rating-spec-id")
        spec_id_elem.text = self.name
        templ_id_elem = etree.SubElement(spec_elem, "template-id")
        templ_id_elem.text = self.template.name
        loc_id_elem = etree.SubElement(spec_elem, "location-id")
        loc_id_elem.text = self.location.name
        vers_elem = etree.SubElement(spec_elem, "version")
        vers_elem.text = self.version
        agency_elem = etree.SubElement(spec_elem, "source-agency")
        if self._agency:
            agency_elem.text = self._agency
        in_range_elem = etree.SubElement(spec_elem, "in-range-method")
        in_range_elem.text = self._in_range_method.name
        out_range_low_elem = etree.SubElement(spec_elem, "out-range-low-method")
        out_range_low_elem.text = self._out_range_low_method.name
        out_range_high_elem = etree.SubElement(spec_elem, "out-range-high-method")
        out_range_high_elem.text = self._out_range_high_method.name
        active_elem = etree.SubElement(spec_elem, "active")
        active_elem.text = str(self.active).lower()
        auto_update_elem = etree.SubElement(spec_elem, "auto-update")
        auto_update_elem.text = str(self.auto_update).lower()
        auto_activate_elem = etree.SubElement(spec_elem, "auto-activate")
        auto_activate_elem.text = str(self.auto_activate).lower()
        auto_migrate_elem = etree.SubElement(spec_elem, "auto-migrate-extension")
        auto_migrate_elem.text = str(self.auto_migrate_extension).lower()
        ind_rounding_specs_elem = etree.SubElement(spec_elem, "ind-rounding-specs")
        for i in range(len(self._ind_rounding)):
            ind_rounding_spec = etree.SubElement(
                ind_rounding_specs_elem, "ind-rounding-spec", position=str(i + 1)
            )
            ind_rounding_spec.text = self._ind_rounding[i]
        dep_rounding_specs_elem = etree.SubElement(spec_elem, "dep-rounding-spec")
        dep_rounding_specs_elem.text = self._dep_rounding
        description_elem = etree.SubElement(spec_elem, "description")
        if self._description:
            description_elem.text = self._description
        return spec_elem
