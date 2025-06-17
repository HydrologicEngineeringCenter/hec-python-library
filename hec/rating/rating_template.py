import warnings
from typing import Any, Optional

from hec.parameter import Parameter, ParameterException
from hec.rating.rating_shared import LookupMethod
from hec.shared import RatingException


class RatingTemplateException(RatingException):
    """
    Exception for rating templates
    """

    pass


DEFAULT_IN_RANGE_METHOD = LookupMethod.LINEAR
DEFAULT_OUT_RANGE_LOW_METHOD = LookupMethod.NEXT
DEFAULT_OUT_RANGE_HIGH_METHOD = LookupMethod.PREVIOUS


class RatingTemplate:
    class IndParameter:
        def __init__(
            self,
            name: str,
            lookup_methods: Optional[
                tuple[LookupMethod, LookupMethod, LookupMethod]
            ] = None,
        ):
            try:
                Parameter(name)
            except ParameterException as e:
                raise ValueError(e)
            self._name = name
            if lookup_methods:
                self._in_range_method = lookup_methods[0]
                self._out_range_low_method = lookup_methods[1]
                self._out_range_high_method = lookup_methods[2]
            else:
                self._in_range_method = DEFAULT_IN_RANGE_METHOD
                self._out_range_low_method = DEFAULT_OUT_RANGE_LOW_METHOD
                self._out_range_high_method = DEFAULT_OUT_RANGE_HIGH_METHOD

        @property
        def name(self) -> str:
            return self._name

        @property
        def in_range_method(self) -> str:
            return self._in_range_method.name

        @property
        def out_range_low_method(self) -> str:
            return self._out_range_low_method.name

        @property
        def out_range_high_method(self) -> str:
            return self._out_range_high_method.name

    def __init__(self, name: str, **kwargs: Any):
        if not isinstance(name, str):
            raise TypeError(f"Expected str for 'name', got {name.__class__.__name__}")
        self._office: Optional[str] = None
        self._ind_params: list[RatingTemplate.IndParameter] = []
        self._dep_param: str
        self._version: str
        self._description: Optional[str] = None

        parts = name.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"Name must be of format <ind-params>;<dep-param>.<version>, got {name}"
            )
        if not parts[1]:
            raise ValueError("Version cannot be an empty string")
        self._version = parts[1]
        params = parts[0].split(";")
        if len(params) != 2:
            raise ValueError(
                f"Name must be of format <ind-params>;<dep-param>.version, got {name}"
            )
        for ind_param in params[0].split(","):
            self._ind_params.append(RatingTemplate.IndParameter(ind_param))
        try:
            Parameter(params[1])
        except Exception as e:
            raise ValueError(e)
        self._dep_param = params[1]

        for kw in kwargs:
            argval = kwargs[kw]
            if kw == "office":
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'office', got {argval.__class__.__name__}"
                    )
                self._office = argval
            elif kw == "lookup":
                self.lookup = argval
            elif kw == "description":
                if not isinstance(argval, str):
                    raise TypeError(
                        f"Expected str for 'description', got {argval.__class__.__name__}"
                    )
                self._description = argval
            else:
                raise TypeError(
                    f"'{kw}' is an invalid keyword argument for RatingTemplate()"
                )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RatingTemplate):
            return False
        if other.name != self.name:
            return False
        if other.office != self.office:
            return False
        if other.lookup != self.lookup:
            return False
        if other.description != self.description:
            return False
        return True

    def __repr__(self) -> str:
        default_lookup = self.ind_param_count * [
            [
                DEFAULT_IN_RANGE_METHOD.name,
                DEFAULT_OUT_RANGE_LOW_METHOD.name,
                DEFAULT_OUT_RANGE_HIGH_METHOD.name,
            ]
        ]
        _repr = f"hec.rating.RatingTemplate('{self.name}'"
        if self.office:
            _repr += f", office='{self.office}'"
        if self.lookup != default_lookup:
            _repr += f", lookup={self.lookup}"
        if self.description:
            _repr += f", description='{self.description}'"
        _repr += ")"
        return _repr

    def __str__(self) -> str:
        return self.name

    def copy(self) -> "RatingTemplate":
        copy = RatingTemplate(self.name)
        copy.office = self.office
        copy.lookup = self.lookup
        copy.description = self.description
        return copy

    @property
    def dep_param(self) -> str:
        return self._dep_param

    @dep_param.setter
    def dep_param(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        try:
            Parameter(value)
        except ParameterException as e:
            raise ValueError(e)
        self._dep_param = value

    @property
    def description(self) -> Optional[str]:
        return self._description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if not isinstance(value, (str, type(None))):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        self._description = value

    @property
    def ind_param_count(self) -> int:
        return len(self._ind_params)

    @property
    def ind_params(self) -> list[str]:
        return [self._ind_params[i].name for i in range(self.ind_param_count)]

    @property
    def lookup(self) -> list[list[str]]:
        return [
            [
                i.in_range_method,
                i.out_range_low_method,
                i.out_range_high_method,
            ]
            for i in self._ind_params
        ]

    @lookup.setter
    def lookup(self, value: Any) -> None:
        methods: list[LookupMethod]
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                f"Expected list or tuple for 'lookup', got {value.__class__.__name__}"
            )
        if len(value) == 0 or len(value[0]) == 0:
            raise ValueError(f"Empty list or tuple passed for 'lookup'")
        if isinstance(value[0], str):
            if len(value) != 3:
                raise ValueError(f"Expected 3 values for 'lookup', got {len(value)}")
            if len(self._ind_params) > 1:
                warnings.warn(
                    f"Will reuse specified behaviors {value} for {len(self._ind_params)} independent parameters",
                    UserWarning,
                )
            methods = []
            for i in range(3):
                specified_method = value[i]
                methods.append(LookupMethod.get(specified_method))
            for i in range(len(self._ind_params)):
                self._ind_params[i]._in_range_method = methods[0]
                self._ind_params[i]._out_range_low_method = methods[1]
                self._ind_params[i]._out_range_high_method = methods[2]
        elif len(value) != len(self._ind_params):
            raise ValueError(
                f"Expected {len(self._ind_params)} values for 'lookup', got {len(value)}"
            )
        else:
            for i in range(len(self._ind_params)):
                if not isinstance(value[i], (list, tuple)):
                    raise TypeError(
                        f"Expected a list or tuple of stings, for 'lookup[{i}]', got {value[0].__class__.__name__}"
                    )
                methods = []
                if len(value[i]) != 3:
                    raise ValueError(
                        f"Expected 3 values for 'lookup[{i}]', got {len(value[i])}"
                    )
                for j in range(3):
                    if not isinstance(value[i][j], (str, int)):
                        raise TypeError(
                            f"Expected str for 'lookup[{i}][{j}]', got {value[i][j].__class__.__name__}"
                        )
                    specified_method = value[i][j]
                    methods.append(LookupMethod.get(specified_method))
                self._ind_params[i]._in_range_method = methods[0]
                self._ind_params[i]._out_range_low_method = methods[1]
                self._ind_params[i]._out_range_high_method = methods[2]

    @property
    def name(self) -> str:
        return f"{','.join([i._name for i in self._ind_params])};{self._dep_param}.{self._version}"

    @property
    def office(self) -> Optional[str]:
        return self._office

    @office.setter
    def office(self, value: Optional[str]) -> None:
        if not isinstance(value, (str, type(None))):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        self._office = value

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if not value:
            raise ValueError("Version cannot be an empty string")
        self._version = value
