from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional, Union, cast

import hec.shared
import hec.unit
from hec.hectime import HecTime
from hec.location import LocationException
from hec.parameter import ElevParameter, Parameter
from hec.rating import rating_shared
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
        self._rating_units: list[str]
        self._specification: RatingSpecification
        self._transition_start_time: Optional[datetime] = None
        self._specification = specification.copy()
        self.effective_time = effective_time
        for ind_param in self._specification.template._ind_params:
            self._rating_units.append(Parameter(ind_param.name).unit_name)
        self._rating_units.append(
            Parameter(self._specification.template.dep_param).unit_name
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
            AbstractRating._INCOMPATIBLE_XML_MESSAGE % (root_tag, cls.__name__)
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
    def from_xml(xml_str: str) -> "AbstractRating":
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
        for classname in AbstractRating._from_xml_methods:
            try:
                return AbstractRating._from_xml_methods[classname](xml_str)
            except AbstractRatingException as e:
                if (
                    len(e.args) == 1
                    and isinstance(e.args[0], str)
                    and e.args[0].split("<")[0]
                    == AbstractRating._INCOMPATIBLE_XML_MESSAGE.split("<")[0]
                ):
                    pass
                else:
                    raise
        raise AbstractRatingException(
            "No subclass of AbstractRating is registered to initialize from the specified XML"
        )

    @property
    def office(self) -> Optional[str]:
        """
        The rating's specification's office, if any

        Operations:
            Read-Only
        """
        return self._specification.template.office

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

    @abstractmethod
    def to_xml(self, indent_str: str = "  ", indent_level: int = 0) -> str:
        raise AbstractRatingException("Method must be called on a sub-class")

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
