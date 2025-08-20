"""
Sub-module to provide rating capabilities to hec module
"""

__all__ = [
    "AbstractRating",
    "AbstractRatingSet",
    "LookupMethod",
    "PairedData",
    "PairedDataException",
    "RatingSpecification",
    "RatingSpecificationException",
    "RatingTemplate",
    "RatingTemplateException",
    "ReferenceRatingSet",
    "abstract_rating",
    "abstract_rating_set",
    "reference_rating_set",
    "rating_shared",
]

from . import rating_shared, rating_specification
from .abstract_rating import AbstractRating
from .abstract_rating_set import AbstractRatingSet
from .paired_data import PairedData, PairedDataException
from .rating_shared import LookupMethod
from .rating_specification import RatingSpecification, RatingSpecificationException
from .rating_template import RatingTemplate, RatingTemplateException
from .reference_rating_set import ReferenceRatingSet

RatingSpecification.__init__.__doc__ = f"""
    Initializer for RatingSpecification objects

    Args:
        name (str): The rating specification identifier
        location (Optional[[Location](../hec/location.html#Location)], must be passed by name): A [Location](../hec/location.html#Location) object for the specification. 
            Defaults to None. If specified, the location name must match the location portion of the rating specification identifier
        template (Optional[[RatingTemplate](#RatingTemplate)], must be passed by name): A [RatingTemplate](#RatingTemplate) object for the specification.
            Defaults to None. If specified, the rating template identifier must match the template portion of the rating specification identifier.
        office (Optional[str], must be passed by name): The office for the rating specification. Defaults to None. If specified, overrides any office in the
            `location` and `template` parameters.
        agency (Optional[str], must be passed by name): The agency that generates the ratings for this specification. Defaults to None.
        lookup (Optional[list[str]], must be passed by value): [Methods](#LookupMethod) for time-based lookups using effective dates in rating sets with this specification.
            Defaults to None. If specified, must be an array of three strings, in the following order
            - method for value times within the range of effective dates
            - method for value times before the earliest effective date
            - method for value times after the latest effective date  
          If not specified, lookup methods of {[rating_specification.DEFAULT_IN_RANGE_METHOD.name, rating_specification.DEFAULT_OUT_RANGE_LOW_METHOD.name, rating_specification.DEFAULT_OUT_RANGE_HIGH_METHOD.name]} will be used. 
        rounding (Optional[list[str]], must be passed by name): Rounding specifications. Defaults to None. If specified:
            - must be the length of the number of independent parameters plus 1
            - all but the last item are applied to the independent parameters in position order
            - the last item is applied to the dependent parameter
            - each item must be a valid [rounding specification](../hec/rounding.html#UsgsRounder)  
          If not specified, the rounding specification of {rating_specification.DEFAULT_ROUNDING_SPEC} is used for all parameters
        active (Optional[bool], must be passed by name): Whether ratings and rating sets using this specification are active (should be used). Defaults to True.
        auto_update (Optional[bool], must be passed by name): Whether ratings and rating sets using this specification are active (should be used). Defaults to False.
        auto_activate (Optional[bool], must be passed by name): Whether automatically updated ratings should be set to active. Defaults to False.
        auto_update_migration (Optional[bool], must be passed by name): Whether automatically updated ratings should have any rating extension migrated to the new rating. Defaults to False.
        description (Optional[str], must be passed by name): A description for the rating specification. Defaults to None.

    Raises:
        ValueError: if the `name` parameter is not a properly-formed rating specification identifier
        TypeError: if one of the named parameters has an unexpected type
        RatingSpecificationException: if one of the named parameters is inconsistent with the rating specification identifier
    """
