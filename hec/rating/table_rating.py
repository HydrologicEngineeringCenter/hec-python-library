import bisect
import math
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, cast

import numpy as np
from lxml import etree

if TYPE_CHECKING:
    from hec.datastore import AbstractDataStore
from hec.hectime import HecTime
from hec.parameter import (
    _NAVD88,
    _NGVD29,
    _OTHER_DATUM,
    Parameter,
    _navd88_pattern,
    _ngvd29_pattern,
    _other_datum_pattern,
)
from hec.rating.abstract_rating import AbstractRating
from hec.rating.rating_shared import LookupMethod, replace_indent
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate
from hec.rating.simple_rating import SimpleRating, SimpleRatingException
from hec.rounding import UsgsRounder
from hec.unit import UnitQuantity


class TableRatingException(SimpleRatingException):
    pass


class TableRating(SimpleRating):

    def __init__(
        self,
        specification: RatingSpecification,
        effective_time: Union[datetime, HecTime, str],
    ):
        super().__init__(specification, effective_time)
        from hec.datastore import AbstractDataStore

        self._data_store: Optional[AbstractDataStore] = None
        self._rating_points: Optional[
            dict[tuple[float, ...], Union[tuple[float], float]]
        ] = None

    @staticmethod
    def _parse_rating_points(
        root: etree._Element, ind_param_count: int
    ) -> Optional[dict[tuple[float, ...], Union[tuple[float], float]]]:
        # ----------------------------------------------------- #
        # parse the rating points into dictionaries for staging #
        # ----------------------------------------------------- #
        rating_points_elems = root.findall("./rating-points")
        if rating_points_elems is not None:
            ind_param_count = ind_param_count
            rating_points: dict[float, Any] = {}
            for i in range(len(rating_points_elems)):
                other_ind_elems = rating_points_elems[i].findall("./other-ind")
                if len(other_ind_elems) != ind_param_count - 1:
                    raise TableRatingException(
                        f"Expected {ind_param_count - 1} <other-ind> elements "
                        f"on <rating-point> element {i+1}, got {len(other_ind_elems)}"
                    )
                other_ind_vals = []
                for j in range(ind_param_count - 1):
                    pos = int(cast(str, other_ind_elems[j].get("position")))
                    if pos != j + 1:
                        raise TableRatingException(
                            f"<{etree.tostring(other_ind_elems[j]).decode()}> on <rating-points> element {i+1} is out of order"
                        )
                    val = float(cast(str, other_ind_elems[j].get("value")))
                    other_ind_vals.append(val)
                for point_elem in rating_points_elems[i].findall("./point"):
                    vals = other_ind_vals[:]
                    ind_elem = point_elem.find("./ind")
                    dep_elem = point_elem.find("./dep")
                    if ind_elem is None or dep_elem is None:
                        raise TableRatingException(
                            "Invalid XML structure in <point> element"
                        )
                    vals.append(float(cast(str, ind_elem.text)))
                    vals.append(float(cast(str, dep_elem.text)))
                    d = rating_points
                    for k in range(ind_param_count):
                        if k == ind_param_count - 1:
                            d[vals[k]] = vals[k + 1]
                        else:
                            d.setdefault(vals[k], {})
                            d = d[vals[k]]
            # --------------------------------------------------------- #
            # re-parse rating point dictionaries into searchable tuples #
            # --------------------------------------------------------- #
            searchable_rating_points: dict[
                tuple[float, ...], Union[tuple[float], float]
            ] = {}
            for i in range(ind_param_count + 1):
                if i == 0:
                    keys: list[tuple[float, ...]] = [(v,) for v in rating_points]
                    if sorted(set(keys)) != keys:
                        raise TableRatingException(
                            "Values for Independent parameter 1 are not monotonically increasing"
                        )
                else:
                    new_keys: list[tuple[float, ...]] = []
                    for key in keys:
                        indices = f"[{']['.join([k for k in map(str, key)])}]"
                        dep_vals = eval(f"rating_points{indices}")
                        if isinstance(dep_vals, dict):
                            points = [v for v in dep_vals]
                            if sorted(set(points)) != points:
                                raise TableRatingException(
                                    f"Values for key {key} are not monotonically increasing"
                                )
                            searchable_rating_points[key] = tuple(sorted(points))
                            new_keys.extend(
                                [
                                    tuple(list(key) + [v])
                                    for v in cast(
                                        tuple[float, ...], searchable_rating_points[key]
                                    )
                                ]
                            )
                        elif isinstance(dep_vals, float):
                            searchable_rating_points[key] = dep_vals
                    keys = new_keys
        return searchable_rating_points

    @staticmethod
    def from_element(
        root: etree._Element, specification: Optional[RatingSpecification]
    ) -> SimpleRating:
        """
        Creates a TableRating from a <simple-rating> XML element and rating spec

        Args:
            root (etree._Element): The <simple-rating> element
            specification (Optional[RatingSpecification]): The rating specification.
                * If specified: If specification vertical datum info is None, it will be created from any vertical datum info in the XML
                * If not specified: The rating spec for the rating will be constructed from the XML

        Raises:
            AbstractRatingException: If there is any invalid XML in the portion common to all ratings
            TableRatingException: If there is any invalid XML in the <rating-points> elements

        Returns:
            SimpleRating: The created rating
        """
        # ------------------------------------------------------------ #
        # parse the portion common to TableRating and ExpressionRating #
        # ------------------------------------------------------------ #
        (
            specification,
            active,
            units,
            effective_time,
            create_time,
            transition_start_time,
            description,
        ) = AbstractRating._parse_common_info(root, specification)
        # --------------------------------------------- #
        # verify the units are valid for the parameters #
        # --------------------------------------------- #
        for i in range(specification.template.ind_param_count):
            try:
                Parameter(specification.template.ind_params[i], units[i])
            except Exception as e:
                raise TableRatingException(e)
        try:
            Parameter(specification.template.dep_param, units[-1])
        except Exception as e:
            raise TableRatingException(e)
        # --------------------------------- #
        # create and return the TableRating #
        # --------------------------------- #
        tr = TableRating(specification, effective_time)
        tr.active = active
        tr._rating_units = units
        tr.create_time = create_time
        tr.transition_start_time = transition_start_time
        tr.description = description
        tr._rating_points = TableRating._parse_rating_points(
            root, specification.template.ind_param_count
        )
        return tr

    @property
    def has_rating_points(self) -> bool:
        """
        Whether the table rating has rating points

        Concrete (non-reference) rating sets may be initailized with or without data points from a data store by
        specifying EAGER or LAZY loading, respectively. A TableRating in a concrete rating set loaded with LAZY loading
        keeps a reference to the datastore in order to retrieve rating points on the first call to a rating or
        reverse rating methods.

        Operations:
            Read/Write
        """
        return self._rating_points is not None

    @staticmethod
    def interpolate_or_select(
        x: float, x0: float, x1: float, y0: float, y1: float, lookup: str
    ) -> float:
        """
        Performs dependent value interpolation, extrapolation, or selection based on specified behavior

        Args:
            x (float): The independent value
            x0 (float): The nearest independent value <= `x` in a sorted list
            x1 (float): The nearest independent value >= `x` in a sorted list
            y0 (float): The dependent value corresponding to `x0`
            y1 (float): The dependent value corresponding to `x1`
            lookup (str): The computation or selection behavior to use. See [LookupMethod](rating_shared.html#LookupMethod)

        Returns:
            float: The interpolated, extrapolated, or selected dependent value
        """
        if x == x0 == x1:
            return y0
        if lookup in (
            LookupMethod.LINEAR.name,
            LookupMethod.LOGARITHMIC.name,
            LookupMethod.LINLOG.name,
            LookupMethod.LOGLIN.name,
        ):
            # --------------------------- #
            # interpolation/extrapolation #
            # --------------------------- #
            X, X0, X1 = x, x0, x1  # save for fallback
            x_log_used = False
            y_log_used = False
            if lookup in (
                LookupMethod.LOGARITHMIC.name,
                LookupMethod.LOGLIN.name,
            ):
                # ---------------- #
                # logarithmic on x #
                # ---------------- #
                try:
                    # take logarithm if possible
                    x, x0, x1 = np.log10([x, x0, x1])
                    x_log_used = True
                except Exception:
                    # fall back to linear
                    pass
            if (
                lookup == LookupMethod.LOGARITHMIC.name and x_log_used
            ) or lookup == LookupMethod.LINLOG.name:
                # ---------------- #
                # logarithmic on y #
                # ---------------- #
                try:
                    # take logarithm if possible
                    y0, y1 = np.log10([y0, y1])
                    y_log_used = True
                except Exception:
                    # fall back to linear
                    if x_log_used:
                        x, x0, x1 = X, X0, X1
                        x_log_used = False
            if x0 == x1:
                y = y0
            else:
                fraction = (x - x0) / (x1 - x0)
                y = y0 + fraction * (y1 - y0)
            if y_log_used:
                y = math.pow(10, y)
            return y
        else:
            # --------- #
            # selection #
            # --------- #
            if lookup in (
                LookupMethod.PREVIOUS.name,
                LookupMethod.LOWER.name,
            ):
                return y0
            elif lookup in (LookupMethod.NEXT.name, LookupMethod.HIGHER.name):
                return y1
            else:  # in_range in (LookupMethod.NEAREST.name, LookupMethod.CLOSEST.name)
                return y0 if x - x0 <= x1 - x else y1

    def rate_value(
        self, ind_value: list[float], lo_key: list[float] = [], hi_key: list[float] = []
    ) -> float:
        """
        Rates a single independent parameter value set

        The value set is expected to be in the native units and vertical datum of the rating. To specify units, vertical datum
        or rounding use [`rate_values`](#TableRating.rate_values), nesting `ind_value` in a list and extracting
        the result from the returned list.

        Args:
            ind_value (list[float]): The list of values (one for each independent parameter) that comprises the input value set
            lo_key (list[float], optional): Do not set; only used internally on recursion. Defaults to [].
            hi_key (list[float], optional): Do not set; only used internally on recursion.  Defaults to [].

        Returns:
            float: The rated (dependent parameter) value
        """
        if not self.has_rating_points:
            raise TableRatingException(
                "Cannot perform rating: table has no rating points"
            )
        rating_points = cast(
            dict[tuple[float, ...], Union[tuple[float], float]], self._rating_points
        )
        i = self.template.ind_param_count - len(ind_value)
        in_range, out_range_lo, out_range_hi = self.template.lookup[i]
        if not lo_key:
            if hi_key:
                raise TableRatingException("hi_key specified without lo_key")
        else:
            if not hi_key:
                raise TableRatingException("lo_key specified without hi_key")
            if i == 0 and len(ind_value) != self.template.ind_param_count:
                raise TableRatingException(
                    f"Rating has {self.template.ind_param_count} indpendent "
                    f"parameters; received value set of length {len(ind_value)}"
                )
            if len(lo_key) != len(hi_key):
                raise TableRatingException("lo_key and hi_key have different lengths")
        hi_val: float
        lo_val: float
        for j, key in enumerate([lo_key, hi_key]):
            if key:
                key_vals = [v for v in cast(tuple[float], rating_points[tuple(key)])]
            else:
                key_vals = [v[0] for v in rating_points if len(v) == 1]
            hi = bisect.bisect(key_vals, ind_value[0])
            if hi > 0 and ind_value[0] == key_vals[hi - 1]:
                hi -= 1
            if hi == len(key_vals):
                # ----------------- #
                # out of range high #
                # ----------------- #
                if out_range_hi in (
                    LookupMethod.ERROR.name,
                    LookupMethod.NEXT.name,
                    LookupMethod.HIGHER.name,
                ):
                    raise TableRatingException(
                        f"Independent value[{i+1}] ({ind_value[0]}) is out of range "
                        f"high and lookup behavior is {out_range_hi}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    return np.nan
                else:
                    hi -= 1
                    if out_range_hi in (
                        LookupMethod.PREVIOUS.name,
                        LookupMethod.LOWER.name,
                        LookupMethod.NEAREST.name,
                        LookupMethod.CLOSEST.name,
                    ):
                        in_range = LookupMethod.NEXT.name
                    elif out_range_hi in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_hi
            lo = hi - 1
            if lo < len(key_vals) - 1 and ind_value[0] == key_vals[lo + 1]:
                lo += 1
            if lo == -1:
                # ---------------- #
                # out of range low #
                # ---------------- #
                if out_range_lo in (
                    LookupMethod.ERROR.name,
                    LookupMethod.PREVIOUS.name,
                    LookupMethod.LOWER.name,
                ):
                    raise TableRatingException(
                        f"Independent value[{i+1}] ({ind_value[0]}) is out of range "
                        f"low and lookup behavior is {out_range_lo}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    return np.nan
                else:
                    lo += 1
                    if out_range_hi in (
                        LookupMethod.NEXT.name,
                        LookupMethod.HIGHER.name,
                        LookupMethod.NEAREST.name,
                        LookupMethod.CLOSEST.name,
                    ):
                        in_range = LookupMethod.PREVIOUS.name
                    elif out_range_hi in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_lo
            # -------------------------------- #
            # either in range or extrapolating #
            # -------------------------------- #
            if in_range == LookupMethod.ERROR.name:
                if ind_value[0] not in (key_vals[lo], key_vals[hi]):
                    raise TableRatingException(
                        f"Independent value[{i+1}] ({ind_value[0]}) is between "
                        f"{key_vals[lo]} and {key_vals[hi]} "
                        f"and lookup behavior is {in_range}"
                    )
                return self.rate_value(
                    ind_value[1:], lo_key + [key_vals[lo]], hi_key + [key_vals[hi]]
                )
            elif in_range == LookupMethod.NULL.name:
                return np.nan
            elif i == self.template.ind_param_count - 1:
                # ----------------------------------- #
                # deepest independent parameter value #
                # ----------------------------------- #
                if in_range in (
                    LookupMethod.LINEAR.name,
                    LookupMethod.LOGARITHMIC.name,
                    LookupMethod.LINLOG.name,
                    LookupMethod.LOGLIN.name,
                ):
                    return TableRating.interpolate_or_select(
                        ind_value[0],
                        key_vals[lo],
                        key_vals[hi],
                        cast(float, rating_points[tuple(key + [key_vals[lo]])]),
                        cast(float, rating_points[tuple(key + [key_vals[hi]])]),
                        in_range,
                    )
            else:
                if j == 0:
                    lo_val = self.rate_value(
                        ind_value[1:], lo_key + [key_vals[lo]], lo_key + [key_vals[hi]]
                    )
                else:
                    if lo_key == hi_key:
                        hi_val = self.rate_value(
                            ind_value[1:],
                            hi_key + [key_vals[hi]],
                            hi_key + [key_vals[hi]],
                        )
                    else:
                        hi_val = self.rate_value(
                            ind_value[1:],
                            hi_key + [key_vals[lo]],
                            hi_key + [key_vals[hi]],
                        )

        return TableRating.interpolate_or_select(
            ind_value[0],
            key_vals[lo],
            key_vals[hi],
            lo_val,
            hi_val,
            in_range,
        )

    def rate_values(
        self,
        ind_values: list[list[float]],
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRating
        ind_param_count = len(ind_values)
        if ind_param_count != self.template.ind_param_count:
            raise TableRatingException(
                f"Expected {self.template.ind_param_count} lists of input values, got {ind_param_count}"
            )
        value_count = len(ind_values[0])
        for i in range(1, ind_param_count):
            if len(ind_values[i]) != value_count:
                raise TableRatingException(
                    f"Expected all input value lists to be of lenght {value_count}, "
                    f"got {len(ind_values[i])} on value list {i+1}."
                )
        _units = units if units else self._default_data_units
        if not _units:
            raise TableRatingException(
                "Cannot perform rating. No data units are specified and rating has no defaults"
            )
        unit_list = re.split(r"[;,]", cast(str, _units))
        if len(unit_list) != ind_param_count + 1:
            raise TableRatingException(
                f"Expected {ind_param_count+1} units, got {len(unit_list)}"
            )
        # ------------------------ #
        # prepare unit conversions #
        # ------------------------ #
        unit_conversions = self.make_unit_conversions(unit_list)
        unit_convertion_indices = [
            i
            for i in range(self.template.ind_param_count)  # ind params only
            if unit_conversions[i] is not None
        ]
        # ---------------------------------- #
        # prepare vertical datum conversions #
        # ---------------------------------- #
        datum_offsets = (
            self.make_datum_offsets(vertical_datum)
            if vertical_datum
            else len(unit_list) * [None]
        )
        datum_offset_indices = [
            i
            for i in range(self.template.ind_param_count)  # ind params only
            if datum_offsets[i] is not None
        ]
        # --------------- #
        # rate the values #
        # --------------- #
        rated_values: list[float] = []
        for i in range(value_count):
            ind_value = [ind_values[j][i] for j in range(ind_param_count)]
            # ------------- #
            # convert units #
            # ------------- #
            for j in unit_convertion_indices:
                ind_value[j] = cast(Callable[[float], float], unit_conversions[j])(
                    ind_value[j]
                )
            # -------------- #
            # convert datums #
            # -------------- #
            for j in datum_offset_indices:
                ind_value[j] += cast(float, datum_offsets[j])
            # ---- #
            # rate #
            # ---- #
            rated_values.append(self.rate_value(ind_value))
        # --------------------------------- #
        # convert rated datum, if necessary #
        # --------------------------------- #
        if datum_offsets[-1] is not None:
            if unit_list[-1] != [self._rating_units[-1]]:
                offset_value = (
                    UnitQuantity(datum_offsets[-1], unit_list[-1])
                    .to(self._rating_units[-1])
                    .magnitude
                )
            else:
                offset_value = datum_offsets[-1]
            rated_values = [v + offset_value for v in rated_values]
        # -------------------------------- #
        # convert rated unit, if necessary #
        # -------------------------------- #
        if unit_conversions[-1]:
            rated_values = list(map(unit_conversions[-1], rated_values))
        # ------------------------- #
        # round values if specified #
        # ------------------------- #
        if round:
            rounder = UsgsRounder(self.specification._dep_rounding)
            rated_values = rounder.round_f(rated_values)
        return rated_values

    def reverse_rate_value(self, dep_value: float) -> float:
        """
        Reverse rates a single dependent parameter value

        The dependent parameter value is expected to be in the native unit and vertical datum of the rating. To specify units, vertical datum
        or rounding use [`reverse_rate_values`](#TableRating.reverse_rate_values), putting `dep_value` in a list and extracting
        the result from the returned list.

        Args:
            dep_value (float): The dependent parameter value to reverse rate

        Returns:
            float: The rated (independent parameter) value
        """
        return self.reverse_rate_values(
            [dep_value], f"{','.join(self._rating_units[:-1])};{self._rating_units[-1]}"
        )[0]

    def reverse_rate_values(
        self,
        dep_values: list[float],
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRating
        if self.template.ind_param_count > 1:
            raise TableRatingException(
                "Cannot reverse rate using a rating with more than one independent value"
            )
        if not self.has_rating_points:
            raise TableRatingException(
                "Cannot perform reverse rating: table has no rating points"
            )
        ind_vals: list[float] = [
            k[0]
            for k in list(
                cast(dict[tuple[float, ...], float], self._rating_points).keys()
            )
        ]
        dep_vals: list[float] = list(
            cast(dict[tuple[float, ...], float], self._rating_points).values()
        )
        if sorted(dep_vals) != dep_vals:
            raise TableRatingException(
                "Cannot perform reverse rating: dependent values are not monotonically increasing"
            )
        _units = units if units else self._default_data_units
        if not _units:
            raise TableRatingException(
                "Cannot perform rating. No data units are specified and rating has no defaults"
            )
        unit_list = re.split(r"[;,]", cast(str, _units))
        if len(unit_list) != 2:
            raise TableRatingException(f"Expected 2 units, got {len(unit_list)}")
        lookups = self.template.lookup[0][:]
        for i in (0, 1, 2):
            if lookups[i] == LookupMethod.LINLOG.name:
                lookups[i] = LookupMethod.LOGLIN.name
            elif lookups[i] == LookupMethod.LOGLIN.name:
                lookups[i] = LookupMethod.LINLOG.name
        # ------------------------ #
        # prepare unit conversions #
        # ------------------------ #
        unit_conversions = self.make_reverse_unit_conversions(unit_list)
        # ---------------------------------- #
        # prepare vertical datum conversions #
        # ---------------------------------- #
        datum_offsets = (
            self.make_reverse_datum_offsets(vertical_datum)
            if vertical_datum
            else 2 * [None]
        )
        # --------------- #
        # rate the values #
        # --------------- #
        rated_values: list[float] = []
        for i in range(len(dep_values)):
            in_range, out_range_lo, out_range_hi = lookups
            # ------------------------ #
            # convert units and datums #
            # ------------------------ #
            dep_value = dep_values[i]
            if unit_conversions[1]:
                dep_value = unit_conversions[1](dep_value)
            if datum_offsets[1]:
                dep_value += datum_offsets[1]
            # ------------------ #
            # perform the rating #
            # ------------------ #
            hi = bisect.bisect(dep_vals, dep_value)
            if hi > 0 and dep_value == dep_vals[hi - 1]:
                hi -= 1
            if hi == len(dep_vals):
                # ----------------- #
                # out of range high #
                # ----------------- #
                if out_range_hi in (
                    LookupMethod.ERROR.name,
                    LookupMethod.NEXT.name,
                    LookupMethod.HIGHER.name,
                ):
                    raise TableRatingException(
                        f"Dependent value ({dep_value}) is out of range "
                        f"high and lookup behavior is {out_range_hi}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    rated_values[i] = np.nan
                    continue
                else:
                    hi -= 1
                    if out_range_hi in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_hi
            lo = hi - 1
            if lo < len(dep_vals) - 1 and dep_value == dep_vals[lo + 1]:
                lo += 1
            if lo == -1:
                # ---------------- #
                # out of range low #
                # ---------------- #
                if out_range_lo in (
                    LookupMethod.ERROR.name,
                    LookupMethod.PREVIOUS.name,
                    LookupMethod.LOWER.name,
                ):
                    raise TableRatingException(
                        f"Dependent value[{i+1}] ({dep_value}) is out of range "
                        f"low and lookup behavior is {out_range_lo}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    rated_values.append(np.nan)
                    continue
                else:
                    lo += 1
                    if out_range_hi in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_lo
            # -------------------------------- #
            # either in range or extrapolating #
            # -------------------------------- #
            if in_range == LookupMethod.ERROR.name:
                if dep_value == dep_vals[lo]:
                    rated_values.append(ind_vals[lo])
                elif dep_value == dep_vals[hi]:
                    rated_values.append(ind_vals[hi])
                else:
                    raise TableRatingException(
                        f"Dependent value ({dep_value}) is between "
                        f"{dep_vals[lo]} and {dep_vals[hi]} "
                        f"and lookup behavior is {in_range}"
                    )
            elif in_range == LookupMethod.NULL.name:
                rated_values.append(np.nan)
                continue
            else:
                rated_values.append(
                    TableRating.interpolate_or_select(
                        dep_value,
                        dep_vals[lo],
                        dep_vals[hi],
                        ind_vals[lo],
                        ind_vals[hi],
                        in_range,
                    )
                )
        # ------------------------ #
        # convert datums and units #
        # ------------------------ #
        if datum_offsets[0]:
            rated_values = list(map(lambda v: v - datum_offsets[0], rated_values))  # type: ignore
        if unit_conversions[0]:
            rated_values = list(map(unit_conversions[0], rated_values))
        return rated_values

    @property
    def xml_element(self) -> etree._Element:
        """
        The rating as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        rating_elem = etree.Element(
            "simple-rating",
            attrib={"office-id": self.template.office if self.template.office else ""},
        )
        AbstractRating.populate_xml_element(self, rating_elem)
        if self.has_rating_points:
            assert self._rating_points is not None  # for mypy
            if self.template.ind_param_count > 1:
                for key in sorted(
                    [
                        key
                        for key in self._rating_points
                        if len(key) == self.template.ind_param_count - 1
                    ]
                ):
                    points_elem = etree.SubElement(rating_elem, "rating-points")
                    for i in range(len(key)):
                        etree.SubElement(
                            points_elem,
                            "other-ind",
                            attrib={"position": f"{i+1}", "value": f"{key[i]}"},
                        )
                    rating_points = self._rating_points[key]
                    assert isinstance(rating_points, tuple)  # for mypy
                    for ind_val in rating_points:
                        key2 = tuple(list(key) + [ind_val])
                        dep_val = self._rating_points[key2]
                        point_elem = etree.SubElement(points_elem, "point")
                        ind_elem = etree.SubElement(point_elem, "ind")
                        ind_elem.text = str(ind_val)
                        dep_elem = etree.SubElement(point_elem, "dep")
                        dep_elem.text = str(dep_val)
            else:
                for key in sorted([key for key in self._rating_points]):
                    ind_val = key[0]
                    dep_val = self._rating_points[key]
                    point_elem = etree.SubElement(points_elem, "point")
                    ind_elem = etree.SubElement(point_elem, "ind")
                    ind_elem.text = str(ind_val)
                    dep_elem = etree.SubElement(point_elem, "dep")
                    dep_elem.text = str(dep_val)
        return rating_elem

    def xml_tag_name(self) -> str:
        return "simple-rating"
