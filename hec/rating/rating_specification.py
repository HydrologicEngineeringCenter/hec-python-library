from hec.location import Location
from hec.rating.rating_shared import LookupMethod, RatingException
from hec.rating.rating_template import RatingTemplate


from typing import Any, Optional, Union

class RatingSpecificationException(RatingException):
    pass


class RatingSpecification:

    def __init__(self, name: str, **kwargs: Any):
        self._location: Location
        self._template: RatingTemplate
        self._version: Optional[str] = None
        self._in_range_method = LookupMethod.LINEAR
        self._out_range_low_method = LookupMethod.ERROR
        self._out_range_high_method = LookupMethod.NEAREST
        if not isinstance(name, str) :
            raise TypeError(f"Expected str for 'name', got {name.__class__.__name__}")
        parts = name.split(".")
        if len(parts) != 4:
            raise ValueError(
                f"Name must be of format <location>.<ind-params>;<dep-param>.<template-version>.<specification-version>, got {name}"
            )
        self._location = Location(parts[0])
        self._template = RatingTemplate(".".join(parts[1:3]))
        self._version = parts[3]

        if "location" in kwargs:
            argval = kwargs["template"]
            if not isinstance(argval, Location):
                raise TypeError(f"Expected Location for 'location', got {argval.__class__.__name__}")
            self._location = argval.copy()
        if "template" in kwargs:
            argval = kwargs["template"]
            if not isinstance(argval, RatingTemplate):
                raise TypeError(f"Expected RatingTemplate for 'template', got {argval.__class__.__name__}")
            self._template = argval.copy()

        for kw in kwargs:
            argval = kwargs[kw]
            if kw == "office":
                if not isinstance(argval, str):
                    raise TypeError(f"Expected str for '{kw}', to {argval.__class__.__name__}")
                if self._template.office and self._template.office != argval:
                    raise RatingSpecificationException(f"Rating specification for office {argval} cannot use template for office {self._template.office}")
                self._template.office = argval
                self._location.office = argval
            elif kw == "version":
                if not isinstance(argval, str):
                    raise TypeError(f"Expected str for '{kw}', to {argval.__class__.__name__}")
                self._version = argval
            elif kw == "lookup":
                self.lookup = argval
            elif kw == "template_lookup":
                self._template.lookup = argval
            elif kw in ("location", "template"):
                pass
            else:
                raise TypeError(
                    f"'{kw}' is an invalid keyword argument for RatingSpecification()"
                )
        if self._location.office != self._template.office:
            raise RatingSpecificationException(f"Rating specification for office {self._location.office} cannot use template from {self._template.office}")


    @property
    def lookup(self) -> list[str]:
        return [self._in_range_method.name, self._out_range_low_method.name, self._out_range_high_method.name]

    @lookup.setter
    def lookup(self, value: Union[list[Union[str, int]], tuple[Union[str, int], ...]]) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list or tuple for 'value', got {value.__class__.__name__}")
        if len(value) != 3:
            raise ValueError(f"Expected 'value' to be len = 3, got len = {len(value)}")
        for i in range(3):
            if not isinstance(value[i], (str, int)):
                raise TypeError(f"Expected str or int for 'value[{i}]', got {value[i].__class__.__name__}")
        self._in_range_method = LookupMethod.get(value[0])
        self._out_range_low_method = LookupMethod.get(value[1])
        self._out_range_high_method = LookupMethod.get(value[2])
