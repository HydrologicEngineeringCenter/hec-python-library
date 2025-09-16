import bisect
import math
import re
from datetime import datetime
from typing import Any, Optional, Union, cast

import numpy as np
from lxml import etree

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


class TableRatingException(SimpleRatingException):
    pass


class TableRating(SimpleRating):

    def __init__(
        self,
        specification: RatingSpecification,
        effective_time: Union[datetime, HecTime, str],
    ):
        super().__init__(specification, effective_time)
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
    def _rate_value(
            value: float,
            ind_values: list[float],
            dep_values: list[float],
            lookups: list[str]
    ) -> list[float]: # [rated, lo_ind, hi_ind]
        in_range, out_range_lo, out_range_hi = lookups
        hi = bisect.bisect_right(ind_values, value)
        if hi == len(ind_values):
            # -------------------------- #
            # value is out of range high #
            # -------------------------- #
            if out_range_hi in (
                LookupMethod.ERROR.name,
                LookupMethod.NEXT.name,
                LookupMethod.HIGHER.name,
            ):
                raise TableRatingException("Out of range high")
            elif out_range_hi == LookupMethod.NULL.name:
                return [np.nan, np.nan, np.nan]
            else:
                hi -= 1
                in_range = out_range_hi
        if lo == -1:
            # ------------------------- #
            # value is out of range low #
            # ------------------------- #
            if out_range_lo in (
                LookupMethod.ERROR.name,
                LookupMethod.PREVIOUS.name,
                LookupMethod.LOWER.name,
            ):
                raise TableRatingException("Out of range low")
            elif out_range_lo == LookupMethod.NULL.name:
                return [np.nan, np.nan, np.nan]
            else:
                lo += 1
                in_range = out_range_lo
        # ----------------------------------------- #
        # value is in range or we are extrapolating #
        # ----------------------------------------- #
        if in_range == LookupMethod.ERROR.name:
            if value not in (ind_values[lo], ind_values[hi]):
                raise TableRatingException(f"Value {value} cannot be between {ind_values[lo]} and {ind_values[hi]}")
            return [value, ind_values[lo], ind_values[hi]]
        elif in_range == LookupMethod.NULL:
            return [np.nan, ind_values[lo], ind_values[hi]]
        elif in_range in (LookupMethod.NEXT, LookupMethod.HIGHER):
            return [ind_values[hi], ind_values[lo], ind_values[hi]]
        elif in_range in (LookupMethod.PREVIOUS, LookupMethod.LOWER):
            return [ind_values[lo], ind_values[lo], ind_values[hi]]
        # ------------------- #
        # compute rated value #
        # ------------------- #
        log_used = False
        v, vlo, vhi = value, ind_values[lo], ind_values[hi]
        if in_range in (LookupMethod.LOGARITHMIC, LookupMethod.LOGLIN):
            try:
                # try logarithmic
                v, vlo, vhi = np.log10([v, vlo, vhi])
                log_used = True
            except Exception:
                # fall back to linear
                pass
        fraction = (v - vlo) / (vhi - vlo)
        rated = dep_values[lo] + fraction * (dep_values[hi] - dep_values[lo])
        if in_range == LookupMethod.LINLOG or (LookupMethod.LOGARITHMIC and log_used):
            rated = math.pow(10, rated)
        return [rated, ind_values[lo], ind_values[hi]]

    def rate_values(
        self,
        ind_values: list[list[float]],
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRating
        list_count = len(ind_values)
        if list_count != self.template.ind_param_count:
            raise TableRatingException(
                f"Expected {self.template.ind_param_count} lists of input values, got {list_count}"
            )
        value_count = len(ind_values[0])
        for i in range(1, list_count):
            if len(ind_values[i]) != value_count:
                raise TableRatingException(
                    f"Expected all input value lists to be of lenght {value_count}, "
                    f"got {len(ind_values[i])} on value list {i+1}."
                )
        _units = units if units else self._default_data_units
        if not _units:
            raise TableRatingException(
                "Cannot perform rating. No data units are specified and rating set has no defaults"
            )
        if len(re.split(r"[;,]", cast(str, _units))) != list_count + 1:
            raise TableRatingException(
                f"Expected {list_count+1} units, got {len(_units)}"
            )
        vd: Optional[str] = None
        if self._has_elev_param() and vertical_datum is not None:
            if _ngvd29_pattern.match(vertical_datum):
                vd = _NGVD29
            elif _navd88_pattern.match(vertical_datum):
                vd = _NAVD88
            elif _other_datum_pattern.match(vertical_datum):
                vd = _OTHER_DATUM
            else:
                raise TableRatingException(
                    f"Invalid vertical datum: {vertical_datum}. Must be one of "
                    f"{_NGVD29}, {_NAVD88}, or {_OTHER_DATUM}"
                )
            if (
                self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None:
                    if bool(offset.magnitude):
                        for i in range(list_count):
                            if self.template.ind_params[i].startswith("Elev"):
                                offset_value = -offset.to(_units[i]).magnitude
                                ind_values[i] = [
                                    ind_values[i][j] + offset_value
                                    for j in range(value_count)
                                ]
        rated_values: list[float] = []
        for i in range(value_count):
            rated_value: float
            lo_key: list[float] = []
            hi_key: list[float] = []
            for j in range(list_count):
                if j == 0:
                    key_values = [v for v in self._rating_points]
                    rated, lo_key_val, hi_key_val = TableRating._rate_value(
                        ind_values[i][j],
                        key_values,
                        key_values,
                        self.template.lookup[j]
                    )
                    lo_key.append(lo_key_val)
                    hi_key.append(hi_key_val)
                rated_lo, lo_key_val, hi_key_val = TableRating._rate_value(
                    ind_values[i][j],
                    key_values,
                    self._rating_points[tuple(lo_key)],
                    self.template.lookup[j]
                )
                lo_key.append(lo_key_val)
                rated_hi, lo_key_val, hi_key_val = TableRating._rate_value(
                    ind_values[i][j],
                    key_values,
                    self._rating_points[tuple(hi_key)],
                    self.template.lookup[j]
                )
                hi_key.append(hi_key_val)
            rated_values.append((rated_lo + rated_hi) / 2)

        if vd is not None and self.template.dep_param.startswith("Elev"):
            if (
                self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None and bool(offset.magnitude):
                    offset_value = offset.to(_units[-1]).magnitude
                    rated_values = [v + offset_value for v in rated_values]
        return rated_values

    def reverse_rate_values(
        self,
        dep_values: list[float],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        raise NotImplementedError

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
