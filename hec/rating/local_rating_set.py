import bisect
import re
from datetime import datetime
from io import StringIO
from typing import Any, Optional, Type, TypeVar, Union, cast

import numpy as np
from lxml import etree

import hec
from hec.rating.abstract_rating import AbstractRating
from hec.rating.abstract_rating_set import AbstractRatingSet, AbstractRatingSetException
from hec.rating.rating_shared import LookupMethod, replace_indent
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate
from hec.rating.table_rating import TableRating

T = TypeVar("T", bound="LocalRatingSet")


class LocalRatingSetException(AbstractRatingSetException):
    pass


class LocalRatingSet(AbstractRatingSet):
    """
    A sub-class of [AbstractRatingSet](#AbstractRatingSet) that performs all ratings in local code
    """

    def __new__(cls: Type[T], *args: tuple[Any], **kwargs: dict[str, Any]) -> T:
        raise NotImplementedError(
            "Use LocalRatingSet.from_xml() to create a new LocalRatingSet object"
        )

    def _intialize_(self, specification: Any, **kwargs: Any) -> None:
        from hec.datastore import AbstractDataStore

        super().__init__(specification, **kwargs)
        self._datastore: Optional[hec.datastore.AbstractDataStore] = None
        self._ratings: dict[datetime, AbstractRating] = {}
        self._active_ratings: dict[datetime, AbstractRating] = {}

        self._rating_time: Optional[datetime] = datetime.max
        for kw in kwargs:
            if kw == "datastore":
                argval = kwargs[kw]
                if argval is not None and not isinstance(
                    argval, hec.datastore.AbstractDataStore
                ):
                    raise TypeError(
                        f"Expected CwmsDataStore for {kw}, got {argval.__class__.__name__}"
                    )
                self._datastore = argval
            else:
                raise ValueError(f"Unexpected keyword argument: {kw}")

    @classmethod
    def from_xml(
        cls, xml_str: str, datastore: Optional["hec.datastore.AbstractDataStore"] = None
    ) -> "LocalRatingSet":
        """
        Creates a LocalRatingSet object from an XML instance

        Args:
            xml_str (str): The XML instance
            datastore (Optional[AbstractDataStore]): The AbstractDataStore object to retrieve rating points from if the XML
                includes table ratings without rating points (used in lazy loading). Defaults to None. Not needed if the
                XML has no table ratings or all table ratings have rating points specified for all effective times.

        Raises:

        Returns:
            LocalRatingSet: The constructed LocalRatingSet object
        """
        if xml_str.startswith("<?xml"):
            xml_str = xml_str.split("?>", 1)[1]
        root = etree.fromstring(xml_str)
        if root.tag != "ratings":
            raise LocalRatingSetException(
                f"Expected root of <ratings>, got <{root.tag}>"
            )
        # ------------------------------------------------------------------------------------------------- #
        # in virtual and transitional ratings there may be many templates, specifications, and rating types #
        # ------------------------------------------------------------------------------------------------- #
        templates: dict[str, RatingTemplate] = {}
        specifications: dict[str, RatingSpecification] = {}
        ratings: dict[str, dict[datetime, AbstractRating]] = {}
        rating_set_specification_id: Optional[str] = None
        for child in root:
            if child.tag == "rating-template":
                template = RatingTemplate.from_xml(etree.tostring(child).decode())
                templates[template.name] = template
            elif child.tag == "rating-spec":
                specification = RatingSpecification.from_xml(
                    etree.tostring(child).decode()
                )
                if specification.template.name in templates:
                    specification.template = templates[specification.template.name]
                specifications[specification.name] = specification
            else:
                rating = AbstractRating.from_xml(etree.tostring(child).decode())
                if not rating_set_specification_id:
                    rating_set_specification_id = rating.specification_id
                if rating.specification_id in specifications:
                    vdi = (
                        None
                        if rating.vertical_datum_info is None
                        else rating.vertical_datum_info.copy()
                    )
                    rating._specification = specifications[rating.specification_id]
                    if not rating.vertical_datum_info:
                        rating._specification._location.vertical_datum_info = vdi
                ratings.setdefault(rating.specification_id, {})
                if rating.effective_time in ratings[rating.specification_id]:
                    raise LocalRatingSetException(
                        f"Cannot have more than one {rating.specification_id} rating with <effective-date> of {rating.effective_time.isoformat()}"
                    )
                if isinstance(rating, TableRating):
                    rating._data_store = datastore  # for lazy loading
                ratings[rating_set_specification_id][rating.effective_time] = rating
        # --------------------------------------------------------------------- #
        # for virtual and transitional ratings, will need to set source ratings #
        # but for now ignore ratings with different rating_specification_ids    #
        # --------------------------------------------------------------------- #
        if not rating_set_specification_id:
            raise LocalRatingSetException("No ratings specified in XML")
        lrs = super().__new__(cls)
        lrs._intialize_(
            specifications[rating_set_specification_id], datastore=datastore
        )
        for effective_time in ratings[rating_set_specification_id]:
            rating = ratings[rating_set_specification_id][effective_time]
            lrs._ratings[effective_time] = rating
            if rating.active:
                lrs._active_ratings[effective_time] = rating
        if lrs._vertical_datum_info is None:
            # ------------------------ #
            # first try active ratings #
            # ------------------------ #
            for effective_time in lrs._active_ratings:
                vdi = lrs._active_ratings[effective_time].vertical_datum_info
                if vdi:
                    lrs._vertical_datum_info = vdi.copy()
                    lrs._default_data_veritcal_datum = (
                        lrs._vertical_datum_info.native_datum
                    )
                    break
        if lrs._vertical_datum_info is None:
            # -------------------------------------------- #
            # next try source ratings and inactive ratings #
            # -------------------------------------------- #
            for spec_id in ratings:
                if spec_id.split(".")[0] == lrs.specification.location.name:
                    for effective_time in ratings[spec_id]:
                        vdi = ratings[spec_id][effective_time].vertical_datum_info
                        if vdi:
                            lrs._vertical_datum_info = vdi.copy()
                            lrs._default_data_veritcal_datum = (
                                lrs._vertical_datum_info.native_datum
                            )
                            break
                    if lrs._vertical_datum_info:
                        break

        return lrs

    def rate_values(
        self,
        ind_values: list[list[float]],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring in AbstractRating.rate_values
        ratings: dict[datetime, AbstractRating] = {}
        if rating_time is None:
            ratings = self._active_ratings
        else:
            for effective_time in self._active_ratings:
                if effective_time > rating_time:
                    continue
                else:
                    create_time = self._active_ratings[effective_time].create_time
                    if create_time and create_time > rating_time:
                        continue
        if not ratings:
            if rating_time:
                raise LocalRatingSetException(
                    f"Specified rating time ({rating_time.isoformat}) excludes all active ratings"
                )
            else:
                raise LocalRatingSetException("Rating set has no active ratings")
        ind_param_count = len(ind_values)
        value_count = len(ind_values[0])
        if ind_param_count != self.template.ind_param_count:
            raise LocalRatingSetException(
                f"Expected {self.template.ind_param_count} lists of input values, got {ind_param_count}"
            )
        for i in range(1, ind_param_count):
            if len(ind_values[i]) != value_count:
                raise LocalRatingSetException(
                    f"Expected all input value lists to be of lenght {value_count}, "
                    f"got {len(ind_values[i])} on value list {i+1}."
                )
        if value_times is None:
            if self.default_data_time is not None:
                value_times = value_count * [cast(datetime, self._default_data_time)]
            else:
                value_times = value_count * [datetime.now()]
        _units = units if units else self._default_data_units
        if not _units:
            raise LocalRatingSetException(
                "Cannot perform rating. No data units are specified and rating set has no defaults"
            )
        unit_list = re.split(r"[;,]", cast(str, _units))
        if len(unit_list) != ind_param_count + 1:
            raise LocalRatingSetException(
                f"Expected {ind_param_count+1} units, got {len(unit_list)}"
            )
        rated_values: list[float] = []
        effective_times = sorted(et for et in ratings)
        effective_times_count = len(effective_times)
        for i in range(value_count):
            in_range, out_range_lo, out_range_hi = self._specification.lookup
            ind_value = [[v[i]] for v in ind_values]
            if (
                i > 0
                and value_times[i] == value_times[i - 1]
                and ind_value == [[v[i - 1]] for v in ind_values]
            ):
                rated_values.append(rated_values[-1])
                continue
            hi = bisect.bisect(effective_times, value_times[i])
            if hi > 0 and value_times[i] == effective_times[hi - 1]:
                hi -= 1
            if hi == effective_times_count:
                # ------------------------------- #
                # value time is out of range high #
                # ------------------------------- #
                if out_range_hi in (
                    LookupMethod.ERROR.name,
                    LookupMethod.NEXT.name,
                    LookupMethod.HIGHER.name,
                ):
                    raise LocalRatingSetException(
                        f"Value time of {value_times[i].isoformat()} is out of range high "
                        f"and lookup method is {out_range_hi}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    rated_values.append(np.nan)
                    continue
                else:
                    hi -= 1
                    if out_range_lo in (
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
            if (
                lo < effective_times_count - 1
                and value_times[i] == effective_times[lo + 1]
            ):
                lo += 1
            if lo == -1:
                # ----------------------------- #
                # value time is out of range lo #
                # ----------------------------- #
                if out_range_lo in (
                    LookupMethod.ERROR.name,
                    LookupMethod.PREVIOUS.name,
                    LookupMethod.LOWER.name,
                ):
                    raise LocalRatingSetException(
                        f"Value time of {value_times[i].isoformat()} is out of range low "
                        f"and lookup method is {out_range_lo}"
                    )
                elif out_range_lo == LookupMethod.NULL.name:
                    rated_values.append(np.nan)
                    continue
                else:
                    lo += 1
                    if out_range_lo in (
                        LookupMethod.NEXT.name,
                        LookupMethod.HIGHER.name,
                        LookupMethod.NEAREST.name,
                        LookupMethod.CLOSEST.name,
                    ):
                        in_range = LookupMethod.PREVIOUS.name
                    elif out_range_lo in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_lo
            # ---------------------------------------------- #
            # value time is either in range or extrapolating #
            # ---------------------------------------------- #
            if in_range == LookupMethod.ERROR.name and value_times[i] not in (
                effective_times[lo],
                effective_times[hi],
            ):
                raise LocalRatingSetException(
                    f"Value time is between {effective_times[lo].isoformat()} and "
                    f"{effective_times[hi].isoformat()}, and lookup method is {in_range}"
                )
            elif in_range == LookupMethod.NULL.name:
                rated_values.append(np.nan)
                continue
            lo_val = ratings[effective_times[lo]].rate_values(
                ind_value, units, vertical_datum, round
            )[0]
            hi_val = ratings[effective_times[hi]].rate_values(
                ind_value, units, vertical_datum, round
            )[0]
            rated_values.append(
                TableRating.interpolate_or_select(
                    value_times[i].timestamp(),
                    effective_times[lo].timestamp(),
                    effective_times[hi].timestamp(),
                    lo_val,
                    hi_val,
                    in_range,
                )
            )
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
        # docstring in AbstractRating.reverse_rate_values
        if self.template.ind_param_count != 1:
            raise LocalRatingSetException(
                "Cannot reverse rate using a rating set with more than one independent value"
            )
        ratings: dict[datetime, AbstractRating] = {}
        if rating_time is None:
            ratings = self._active_ratings
        else:
            for effective_time in self._active_ratings:
                if effective_time > rating_time:
                    continue
                else:
                    create_time = self._active_ratings[effective_time].create_time
                    if create_time and create_time > rating_time:
                        continue
        if not ratings:
            if rating_time:
                raise LocalRatingSetException(
                    f"Specified rating time ({rating_time.isoformat}) excludes all active ratings"
                )
            else:
                raise LocalRatingSetException("Rating set has no active ratings")
        value_count = len(dep_values)
        if value_times is None:
            if self.default_data_time is not None:
                value_times = value_count * [cast(datetime, self._default_data_time)]
            else:
                value_times = value_count * [datetime.now()]
        _units = units if units else self._default_data_units
        if not _units:
            raise LocalRatingSetException(
                "Cannot perform rating. No data units are specified and rating set has no defaults"
            )
        unit_list = re.split(r"[;,]", cast(str, _units))
        if len(unit_list) != 2:
            raise LocalRatingSetException(f"Expected 2 units, got {len(unit_list)}")
        reverse_rated_values: list[float] = []
        effective_times = sorted(et for et in ratings)
        effective_times_count = len(effective_times)
        for i in range(value_count):
            in_range, out_range_lo, out_range_hi = self._specification.lookup
            if (
                i > 0
                and value_times[i] == value_times[i - 1]
                and dep_values[i] == dep_values[i - 1]
            ):
                reverse_rated_values.append(reverse_rated_values[-1])
                continue
            hi = bisect.bisect(effective_times, value_times[i])
            if hi > 0 and value_times[i] == effective_times[hi - 1]:
                hi -= 1
            if hi == effective_times_count:
                # ------------------------------- #
                # value time is out of range high #
                # ------------------------------- #
                if out_range_hi in (
                    LookupMethod.ERROR.name,
                    LookupMethod.NEXT.name,
                    LookupMethod.HIGHER.name,
                ):
                    raise LocalRatingSetException(
                        f"Value time of {value_times[i].isoformat()} is out of range high "
                        f"and lookup method is {out_range_hi}"
                    )
                elif out_range_hi == LookupMethod.NULL.name:
                    reverse_rated_values.append(np.nan)
                    continue
                else:
                    hi -= 1
                    if out_range_lo in (
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
            if (
                lo < effective_times_count - 1
                and value_times[i] == effective_times[lo + 1]
            ):
                lo += 1
            if lo == -1:
                # ----------------------------- #
                # value time is out of range lo #
                # ----------------------------- #
                if out_range_lo in (
                    LookupMethod.ERROR.name,
                    LookupMethod.PREVIOUS.name,
                    LookupMethod.LOWER.name,
                ):
                    raise LocalRatingSetException(
                        f"Value time of {value_times[i].isoformat()} is out of range low "
                        f"and lookup method is {out_range_lo}"
                    )
                elif out_range_lo == LookupMethod.NULL.name:
                    reverse_rated_values.append(np.nan)
                    continue
                else:
                    lo += 1
                    if out_range_lo in (
                        LookupMethod.NEXT.name,
                        LookupMethod.HIGHER.name,
                        LookupMethod.NEAREST.name,
                        LookupMethod.CLOSEST.name,
                    ):
                        in_range = LookupMethod.PREVIOUS.name
                    elif out_range_lo in (
                        LookupMethod.LINEAR.name,
                        LookupMethod.LINLOG.name,
                        LookupMethod.LOGARITHMIC.name,
                        LookupMethod.LOGLIN.name,
                    ):
                        in_range = out_range_lo
            # ---------------------------------------------- #
            # value time is either in range or extrapolating #
            # ---------------------------------------------- #
            if in_range == LookupMethod.ERROR.name and value_times[i] not in (
                effective_times[lo],
                effective_times[hi],
            ):
                raise LocalRatingSetException(
                    f"Value time is between {effective_times[lo].isoformat()} and "
                    f"{effective_times[hi].isoformat()}, and lookup method is {in_range}"
                )
            elif in_range == LookupMethod.NULL.name:
                reverse_rated_values.append(np.nan)
                continue
            lo_val = ratings[effective_times[lo]].reverse_rate_values(
                [dep_values[i]], units, vertical_datum, round
            )[0]
            hi_val = ratings[effective_times[hi]].reverse_rate_values(
                [dep_values[i]], units, vertical_datum, round
            )[0]
            reverse_rated_values.append(
                TableRating.interpolate_or_select(
                    value_times[i].timestamp(),
                    effective_times[lo].timestamp(),
                    effective_times[hi].timestamp(),
                    lo_val,
                    hi_val,
                    in_range,
                )
            )
        return reverse_rated_values

    def to_xml(self, indent: str = "  ", prepend: str = "") -> str:
        """
        Returns a formatted xml representation of the rating set.

        Args:
            indent (str, optional): The string to use for each level of indentation. Defaults to "  ".
            prepend (Optional[str], optional): A string to prepend to each line. Defaults to None.

        Returns:
            str: The formatted xml
        """
        # ---------------------------- #
        # first pass of xml generation #
        # ---------------------------- #
        buf = StringIO()
        buf.write(
            f"{prepend}<ratings>\n"
            f"{self.template.to_xml(indent=indent, prepend=prepend+'  ')}"
            f"{self.specification.to_xml(indent=indent, prepend=prepend+'  ')}"
        )
        for effective_time in sorted(self._ratings):
            rating = self._ratings[effective_time]
            if (
                isinstance(rating, hec.rating.TableRating)
                and not rating.has_rating_points
            ):
                rating.populate_rating_points()
            buf.write(f"{rating.to_xml(indent=indent, prepend=prepend+'  ')}")
        buf.write(f"{prepend if prepend else ''}</ratings>\n")
        xml: str = buf.getvalue()
        buf.close()
        # --------------------------------------------------------------------------------- #
        # reorganize for source ratings (templates, followed by specs, followed by ratings) #
        # --------------------------------------------------------------------------------- #
        root = etree.fromstring(xml)
        assert root.tag == "ratings"
        new_root = etree.fromstring(
            '<ratings xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.hec.usace.army.mil/xmlSchema/cwms/Ratings.xsd">\n</ratings>'
        )
        for elem in root.findall("./rating-template"):
            new_root.append(elem)
        for elem in root.findall("./rating-spec"):
            new_root.append(elem)
        for elem in [e for e in root if e.tag.endswith("-rating")]:
            new_root.append(elem)
        for e in new_root.iter():
            if e.text and e.text.strip() == "":
                e.text = None
            if e.tail and e.tail.strip() == "":
                e.tail = None
        xml = etree.tostring(new_root, pretty_print=True).decode()
        # ---------------------------------- #
        # handle weirdness with pretty-print #
        # ---------------------------------- #
        pos = xml.find(">")
        if xml[pos : pos + 3] == ">\n<":
            xml = xml[: pos + 2] + prepend + indent + xml[pos + 2 :]
        # ---------------------------- #
        # handle specified indentation #
        # ---------------------------- #
        if indent != "  ":
            xml = replace_indent(xml, indent)
        if prepend:
            xml = "".join([prepend + line for line in xml.splitlines(keepends=True)])
        return xml


if __name__ == "__main__":
    with open("test/resources/rating/table_rating_set_1.xml") as f:
        xml_str = f.read()
    rs = LocalRatingSet.from_xml(xml_str)
    print(rs)
