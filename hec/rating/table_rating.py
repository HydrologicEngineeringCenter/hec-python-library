from datetime import datetime
from typing import Any, Optional, Union, cast

from lxml import etree

from hec.datastore import AbstractDataStore
from hec.hectime import HecTime
from hec.parameter import Parameter
from hec.rating.abstract_rating import AbstractRating
from hec.rating.rating_shared import replace_indent
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
                    keys: list[tuple[float, ...]] = sorted(
                        [(v,) for v in rating_points]
                    )
                else:
                    new_keys: list[tuple[float, ...]] = []
                    for key in keys:
                        indices = f"[{']['.join([k for k in map(str, key)])}]"
                        dep_vals = eval(f"rating_points{indices}")
                        if isinstance(dep_vals, dict):
                            searchable_rating_points[key] = tuple(
                                sorted([v for v in dep_vals])
                            )
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

    def rate(self, value: Any) -> Any:
        raise NotImplementedError

    def reverse_rate(self, value: Any) -> Any:
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
            assert self._rating_points is not None # for mypy
            if self.template.ind_param_count > 1:
                for key in sorted(
                    [
                        key
                        for key in self._rating_points
                        if len(key) == self.template.ind_param_count - 1
                    ]
                ):
                    points_elem = etree.SubElement(rating_elem, "rating-points")
                    for i in range(len(key) - 1):
                        etree.SubElement(
                            points_elem,
                            "other-ind",
                            attrib={"position": f"{i+1}", "value": f"{key[i]}"},
                        )
                    rating_points = self._rating_points[key]
                    assert isinstance(rating_points, tuple) # for mypy
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
