import re
import warnings
from typing import Any, Optional

from lxml import etree

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
    """
    Holds independent and dependent parameter names, independent parameter lookup methods, and version string for all associated ratings.

    Ratings are associated by using a rating identifier that includes the template identifier.
    """
    class IndParameter:
        """
        Associates lookup methods with an independent parameter for a RatingTemplate object
        """
        def __init__(
            self,
            name: str,
            lookup_methods: Optional[
                tuple[LookupMethod, LookupMethod, LookupMethod]
            ] = None,
        ):
            """
            Initializes the IndParameter object

            Args:
                name (str): The associated independent parameter name
                **lookup_methods (Optional[ tuple[
                    [LookupMethod](rating.html#LookupMethod),
                    [LookupMethod](rating.html#LookupMethod),
                    [LookupMethod](rating.html#LookupMethod)
                    ] ]):** The lookup methods associated with the independent parameter. Defaults to None.
                    If specified, the lookup methods are in the order of in-range, out-of-range-low, out-of-range-high. If not specified, the default methods of [
                    [LINEAR](rating.html#LookupMethod.LINEAR),
                    [NEXT](rating.html#LookupMethod.NEXT),
                    [PREVIOUS](rating.html#LookupMethod.PREVIOUS)
                    ] are used.

            Raises:
                ValueError: if the name is not a valid [Parameter](https://hydrologicengineeringcenter.github.io/hec-python-library/hec/parameter.html#Parameter) name
            """
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
            """
            The independent parameter name

            Operations:
                Read-Only

            """
            return self._name

        @property
        def in_range_method(self) -> str:
            """
            The in-range lookup behavior for the independent parameter

            Operations:
                Read-Only

            """
            return self._in_range_method.name

        @property
        def out_range_low_method(self) -> str:
            """
            The out-of-range-low lookup behavior for the independent parameter

            Operations:
                Read-Only

            """
            return self._out_range_low_method.name

        @property
        def out_range_high_method(self) -> str:
            """
            The out-of-range-low lookup behavior for the independent parameter

            Operations:
                Read-Only

            """
            return self._out_range_high_method.name

    def __init__(self, name: str, **kwargs: Any):
        """
        Initializes the RatingTemplate object

        Args:
            name (str): The rating template identifier
            lookup_methods (Optional[ tuple[LookupMethod, LookupMethod, LookupMethod] ]): _description_. Defaults to None.

        Raises:
            ValueError: _description_
        """
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
        """
        Returns a copy of the rating template

        Returns:
            RatingTemplate: The copy
        """
        copy = RatingTemplate(self.name)
        copy.office = self.office
        copy.lookup = self.lookup
        copy.description = self.description
        return copy

    @property
    def dep_param(self) -> str:
        """
        The depdendent parameter

        Operations:
            Read/Write
        """
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
        """
        The rating template description

        Operations:
            Read/Write
        """
        return self._description

    @description.setter
    def description(self, value: Optional[str]) -> None:
        if not isinstance(value, (str, type(None))):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        self._description = value

    @staticmethod
    def from_xml(xml: str) -> "RatingTemplate":
        """
        Generates a RatingTemplate object from an XML string representation

        Args:
            xml (str): The XML string representation

        Raises:
            RatingTemplateException: if there is an error in the XML string

        Returns:
            RatingTemplate: The generated RatingTemplate object
        """
        template_elem = etree.fromstring(xml)
        if template_elem.tag != "rating-template":
            raise RatingTemplateException(
                f"Expected <rating-template>, got <{template_elem.tag}>"
            )
        office = template_elem.get("office")
        if not office:
            raise RatingTemplateException("No office specified in <rating-template>")
        parameters = template_elem.findtext("parameters-id")
        if not parameters:
            raise RatingTemplateException("No data found for <parameters-id>")
        parts = parameters.split(";")
        if len(parts) != 2:
            raise RatingTemplateException(f"Mal-formed <parameter-id>: {parameters}")
        dep_param = template_elem.findtext("dep-parameter")
        if dep_param != parts[1]:
            raise RatingTemplateException(
                f"<dep-parameter> of {dep_param} doesn't match parameter in <parameters-id> of {parts[1]}"
            )
        version = template_elem.findtext("version")
        if not version:
            raise RatingTemplateException("No data found for <version>")
        description = template_elem.findtext("description")
        ind_params = parts[0].split(",")
        ind_param_count = len(ind_params)
        lookups: list[list[str]] = ind_param_count * []
        specs_elems = template_elem.findall("./ind-parameter-specs")
        if len(specs_elems) != 1:
            raise RatingTemplateException(
                f"Expected 1 <ind-parameter-specs> element, got {len(specs_elems)}"
            )
        specs_elem = specs_elems[0]
        spec_elems = specs_elem.findall("./ind-parameter-spec")
        if len(spec_elems) != ind_param_count:
            raise RatingTemplateException(
                f"Expected {ind_param_count} <ind-parameter-spec> elements, got {len(spec_elems)}"
            )
        for i in range(ind_param_count):
            lookups.append([])
            pos = spec_elems[i].get("position")
            if pos is None or not pos.isdigit() or int(pos) != i + 1:
                raise RatingTemplateException(
                    f'Expected attribute of position="{i+1}" on <ind-parameter-spec>[{i}], got {pos}'
                )
            param = spec_elems[i].findtext("parameter")
            if param != ind_params[i]:
                raise RatingTemplateException(
                    f"Expected <parameter> of {ind_params[i]} on <ind-parameter-spec>[{i}], got {param}"
                )
            method = spec_elems[i].findtext("in-range-method")
            if not method:
                raise RatingTemplateException(
                    f"No data found for <in-range-method> on <ind-parameter-spec>[{i}]"
                )
            lookups[-1].append(method)
            method = spec_elems[i].findtext("out-range-low-method")
            if not method:
                raise RatingTemplateException(
                    f"No data found for <out-range-low-method> on <ind-parameter-spec>[{i}]"
                )
            lookups[-1].append(method)
            method = spec_elems[i].findtext("out-range-high-method")
            if not method:
                raise RatingTemplateException(
                    f"No data found for <out-range-high-method> on <ind-parameter-spec>[{i}]"
                )
            lookups[-1].append(method)

        template = RatingTemplate(
            f"{parameters}.{version}",
            office=office,
            lookup=lookups,
            description=description,
        )
        return template

    @property
    def ind_param_count(self) -> int:
        """
        The number of independent parameters

        Operations:
            Read-Only
        """
        return len(self._ind_params)

    @property
    def ind_params(self) -> list[str]:
        """
        The indepdendent parameters as a list of strings

        Operations:
            Read-Only
        """
        return [self._ind_params[i].name for i in range(self.ind_param_count)]

    @property
    def lookup(self) -> list[list[str]]:
        """
        The rating independent parameter lookup behaviors in in-range, out-range-low, out-range-high order
        as a list of lists of strings (one list for each independent parameter)

        Operations:
            Read/Write
        """
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
        """
        The rating template identifier

        Operations:
            Read-Only
        """
        return f"{','.join([i._name for i in self._ind_params])};{self._dep_param}.{self._version}"

    @property
    def office(self) -> Optional[str]:
        """
        The rating template office

        Operations:
            Read/Write
        """
        return self._office

    @office.setter
    def office(self, value: Optional[str]) -> None:
        if not isinstance(value, (str, type(None))):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        self._office = value

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

        def replace_indent(s: str, new_indent: str) -> str:
            old_indent = "  "
            pattern = f"^(?:{re.escape(old_indent)})+"

            def repl(match: re.Match[str]) -> str:
                count = len(match.group(0)) // len(old_indent)
                return new_indent * count

            return re.sub(pattern, repl, s, flags=re.MULTILINE)

        xml = etree.tostring(self.xml_element, pretty_print=True).decode()
        if indent != "  ":
            xml = replace_indent(xml, indent)
        if prepend:
            xml = "".join([prepend + line for line in xml.splitlines(keepends=True)])
        return xml

    @property
    def version(self) -> str:
        """
        The rating template version

        Operations:
            Read/Write
        """
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {value.__class__.__name__}")
        if not value:
            raise ValueError("Version cannot be an empty string")
        self._version = value

    @property
    def xml_element(self) -> etree._Element:
        """
        The rating template as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        template_elem = etree.Element(
            "rating-template", office=self.office if self.office else ""
        )
        parameters_id_elem = etree.SubElement(template_elem, "parameters-id")
        parameters_id_elem.text = f"{','.join(self.ind_params)};{self._dep_param}"
        version_elem = etree.SubElement(template_elem, "version")
        version_elem.text = self.version
        ind_params_elem = etree.SubElement(template_elem, "ind-parameter-specs")
        for i in range(self.ind_param_count):
            ind_param_elem = etree.SubElement(
                ind_params_elem, "ind-parameter-spec", position=str(i + 1)
            )
            parameter_elem = etree.SubElement(ind_param_elem, "parameter")
            parameter_elem.text = self._ind_params[i].name
            in_range_elem = etree.SubElement(ind_param_elem, "in-range-method")
            in_range_elem.text = self._ind_params[i].in_range_method
            out_range_low_elem = etree.SubElement(
                ind_param_elem, "out-range-low-method"
            )
            out_range_low_elem.text = self._ind_params[i].out_range_low_method
            out_range_high_elem = etree.SubElement(
                ind_param_elem, "out-range-high-method"
            )
            out_range_high_elem.text = self._ind_params[i].out_range_high_method
        dep_param_elem = etree.SubElement(template_elem, "dep-parameter")
        dep_param_elem.text = self.dep_param
        description_elem = etree.SubElement(template_elem, "description")
        description_elem.text = self.description
        return template_elem
