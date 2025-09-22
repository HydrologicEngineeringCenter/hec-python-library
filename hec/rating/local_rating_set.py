import re
from datetime import datetime
from typing import Any, Optional, Type, TypeVar, Union, cast

import numpy as np
from lxml import etree

import hec

from .abstract_rating import AbstractRating
from .abstract_rating_set import AbstractRatingSet, AbstractRatingSetException
from .rating_specification import RatingSpecification
from .rating_template import RatingTemplate

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
                if not isinstance(argval, hec.datastore.AbstractDataStore):
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
            elif child.tag == "rating-specification":
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
                    rating._specification = specifications[rating.specification_id]
                ratings.setdefault(rating.specification_id, {})
                if rating.effective_time in ratings[rating.specification_id]:
                    raise LocalRatingSetException(
                        f"Cannot have more than one {rating.specification_id} rating with <effective-date> of {rating.effective_time.isoformat()}"
                    )
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

        return lrs
