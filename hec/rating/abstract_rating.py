from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Union

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
    """

    def __init__(self, specification: RatingSpecification):
        self._active: bool = True
        self._create_time: Optional[datetime] = None
        self._default_data_time: Optional[datetime] = None
        self._default_data_units: list[str]
        self._default_data_verical_datum: Optional[str] = None
        self._description: Optional[str] = None
        self._effective_time: Optional[datetime] = None
        self._rating_time: Optional[datetime] = None
        self._rating_units: list[str]
        self._specification: RatingSpecification
        self._transition_start_time: Optional[datetime] = None
        self._specification = specification.copy()
        for ind_param in self._specification.template._ind_params:
            self._rating_units.append(Parameter(ind_param.name).unit_name)
        self._rating_units.append(
            Parameter(self._specification.template.dep_param).unit_name
        )
        self._data_units = self._rating_units[:]

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {value.__class__.__name__}")

    @property
    def create_time(self) -> Optional[datetime]:
        return self._create_time

    @create_time.setter
    def create_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if not value:
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
    def default_data_time(self) -> Optional[datetime]:
        return self._default_data_time

    @default_data_time.setter
    def default_data_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if not value:
            self._default_data_time = None
        elif isinstance(value, str):
            self._default_data_time = HecTime(str).datetime()
        elif isinstance(value, HecTime):
            self._default_data_time = value.datetime()
        elif isinstance(value, datetime):
            self._default_data_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @property
    def default_data_units(self) -> list[str]:
        return self._default_data_units[:]

    @default_data_units.setter
    def default_data_units(self, value: list[str]) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list or tuple, got {value.__class__.__name__}")
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
        return self._default_data_verical_datum

    @default_data_vertical_datum.setter
    def default_data_vertical_datum(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if self._specification.location.vertical_datum_info is None:
            raise LocationException(
                f"Location {self._specification.location.name} doesn't have vertical datum info"
            )
        self._default_data_verical_datum = (
            self._specification.location.vertical_datum_info.normalize_datum_name(value)
        )

    @property
    def description(self) -> Optional[str]:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")

    @property
    def effective_time(self) -> Optional[datetime]:
        return self._effective_time

    @effective_time.setter
    def effective_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if not value:
            self._effective_time = None
        elif isinstance(value, str):
            self._effective_time = HecTime(str).datetime()
        elif isinstance(value, HecTime):
            self._effective_time = value.datetime()
        elif isinstance(value, datetime):
            self._effective_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @staticmethod
    @abstractmethod
    def from_xml(xml_str: str) -> "AbstractRating":
        raise AbstractRatingException("Method must be called on a sub-class")

    @property
    def office(self) -> Optional[str]:
        return self._specification.template.office

    @abstractmethod
    def rate(self, value: Any) -> Any:
        raise AbstractRatingException("Method must be called on a sub-class")

    @property
    def rating_time(self) -> Optional[datetime]:
        return self._rating_time

    @rating_time.setter
    def rating_time(
        self, value: Optional[Union[datetime, HecTime, str]] = None
    ) -> None:
        if not value:
            self._rating_time = None
        elif isinstance(value, str):
            self._rating_time = HecTime(str).datetime()
        elif isinstance(value, HecTime):
            self._rating_time = value.datetime()
        elif isinstance(value, datetime):
            self._rating_time = value
        else:
            raise TypeError(
                f"Expected datetime, HecTime, or str, got {value.__class__.__name__}"
            )

    @property
    def rating_units(self) -> list[str]:
        return self._rating_units[:]

    @rating_units.setter
    def rating_units(self, value: list[str]) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"Expected list or tuple, got {value.__class__.__name__}")
        if len(value) != self.template.ind_param_count + 1:
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
        self._rating_units = new_units

    @abstractmethod
    def reverse_rate(self, value: Any) -> Any:
        raise AbstractRatingException("Method must be called on a sub-class")

    @property
    def specification(self) -> RatingSpecification:
        return self._specification.copy()

    @property
    def specification_id(self) -> str:
        return self._specification.name

    @property
    def template(self) -> RatingTemplate:
        return self._specification.template

    @property
    def template_id(self) -> str:
        return self._specification.template.name

    @property
    def transition_start_time(self) -> Optional[datetime]:
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
        return self._specification.location.vertical_datum_info

    @property
    def vertical_datum_json(self) -> Optional[str]:
        return self._specification.location.vertical_datum_json

    @property
    def vertical_datum_xml(self) -> Optional[str]:
        return self._specification.location.vertical_datum_xml
