from typing import Any, Optional, Sequence, Union

from hec.location import Location
from hec.rating.rating_shared import LookupMethod
from hec.rating.rating_template import RatingTemplate
from hec.shared import RatingException

DEFAULT_IN_RANGE_METHOD = LookupMethod.LINEAR
DEFAULT_OUT_RANGE_LOW_METHOD = LookupMethod.NEXT
DEFAULT_OUT_RANGE_HIGH_METHOD = LookupMethod.PREVIOUS
DEFAULT_ROUNDING_SPEC = "4444444449"


class RatingSpecificationException(RatingException):
    pass


class RatingSpecification:

    def __init__(self, name: str, **kwargs: Any):
        self._location: Location
        self._template: RatingTemplate
        self._version: str
        self._in_range_method = DEFAULT_IN_RANGE_METHOD
        self._out_range_low_method = DEFAULT_OUT_RANGE_LOW_METHOD
        self._out_range_high_method = DEFAULT_OUT_RANGE_HIGH_METHOD
        self._ind_rounding: list[str] = []
        self._dep_rounding = DEFAULT_ROUNDING_SPEC
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

        if "location" in kwargs:
            argval = kwargs["location"]
            self.location = argval
        if "template" in kwargs:
            argval = kwargs["template"]
            self.template = argval

        for kw in kwargs:
            argval = kwargs[kw]
            if kw == "office":
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for '{kw}', to {argval.__class__.__name__}"
                    )
                if self._template.office and self._template.office != argval:
                    raise RatingSpecificationException(
                        f"Rating specification for office {argval} cannot use template for office {self._template.office}"
                    )
                self._template.office = argval
                self._location.office = argval
            elif kw == "lookup":
                self.lookup = argval
            elif kw == "template_lookup":
                self._template.lookup = argval
            elif kw == "rounding":
                self.rounding = argval
            elif kw in ("location", "template"):
                pass
            else:
                raise TypeError(
                    f"'{kw}' is an invalid keyword argument for RatingSpecification()"
                )
        if self._location.office != self._template.office:
            raise RatingSpecificationException(
                f"Rating specification for office {self._location.office} cannot use template from {self._template.office}"
            )

        if "rounding" not in kwargs:
            self._ind_rounding = self._template.ind_param_count * [
                DEFAULT_ROUNDING_SPEC
            ]

        if self._template.office and not self._location.office:
            self._location.office = self._template.office

    def copy(self) -> "RatingSpecification":
        copy = RatingSpecification(
            self.name,
            location=self.location,
            template=self.template,
            rounding=self.rounding,
        )
        return copy

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
    def location(self) -> Location:
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
        return f"{self.location.name}.{self.template.name}.{self.version}"

    @property
    def rounding(self) -> list[str]:
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

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if not value:
            raise ValueError("version cannot be an empty string")
        self._version = value
