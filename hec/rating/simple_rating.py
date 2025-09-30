import re
from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional, Union, cast

from lxml import etree

import hec.rating
from hec.hectime import HecTime
from hec.parameter import ElevParameter
from hec.rating.abstract_rating import AbstractRating, AbstractRatingException
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate


class SimpleRatingException(AbstractRatingException):
    pass


class SimpleRating(AbstractRating):

    def __init__(
        self,
        specification: RatingSpecification,
        effective_time: Union[datetime, HecTime, str],
    ):
        super().__init__(specification, effective_time)

    @staticmethod
    def from_xml(
        xml_str: str, specification: Optional[RatingSpecification] = None
    ) -> AbstractRating:

        from hec.rating.table_rating import TableRating

        root, spec = AbstractRating._find_rating_root(xml_str)
        if root.tag != "simple-rating":
            SimpleRating._raise_incompatible_xml_error(root.tag)
        if spec and not specification:
            specification = spec
        if root.find("./formula") is not None:
            # ---------------- #
            # ExpressionRating #
            # ---------------- #
            raise NotImplementedError("ExpressionRating is not yet implemented")
            # rating = ExpressionRating.from_element(root, specification)
        else:
            # ----------- #
            # TableRating #
            # ----------- #
            rating = TableRating.from_element(root, specification)
        return rating

    @property
    @abstractmethod
    def xml_element(self) -> etree._Element:
        """
        The rating as an lxml.etree.Element object

        Operations:
            Read-Only
        """
        raise AbstractRatingException("Method must be called on a sub-class")

    def xml_tag_name(self) -> str:
        return "simple-rating"


SimpleRating._from_xml_methods[SimpleRating.__name__] = SimpleRating.from_xml

if __name__ == "__main__":
    with open("t:/rating.xml") as f:
        rating = AbstractRating.from_xml(f.read())
        from hec.rating.table_rating import TableRating

        tr = cast(TableRating, rating)
        flow = tr.rate_value([2, 0, 1250.5])
        print(flow)
        # with open("t:/rating2.xml", "w") as f:
        #     f.write(rating.to_xml())
