"""
Sub-module to provide rating capabilities to hec module

**Quick links to Constants:**

* [LookupMethod](#LookupMethod)
* [RatingSetRetrievalMethod](../hec/shared.html#RatingSetRetrievalMethod)

**Quick links to Classes:**

<table/>
    <table>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Ratings - Individual Rating Objects</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="rating/abstract_rating.html#AbstractRating">AbstractRating</a></td>
        <td><a href="rating/abstract_rating.html#AbstractRatingException">AbstractRatingException</a></td>
        <td>Abstract base class for all rating types</td>
    </tr>
    <tr><td><a href="rating/simple_rating.html#SimpleRating">SimpleRating</a></td>
        <td><a href="rating/simple_rating.html#SimpleRatingException">SimpleRatingException</a></td>
        <td>Abstract base class for <code>ExpressionRating</code> and <code>TableRating</code> objects, which both use the <code>&lt;simple-rating&gt;</code> xml element
    </tr>
    <tr><td><a href="rating/table_rating.html#TableRating">TableRating</a></td>
        <td><a href="rating/table_rating.html#TableRatingException">TableRatingException</a></td>
        <td>Ratings that use tables of lookup values</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Rating Sets - Time Series of Rating Objects</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="rating/abstract_rating_set.html#AbstractRatingSet">AbstractRatingSet</a></td>
        <td><a href="rating/abstract_rating_set.html#AbstractRatingSetException">AbstractRatingSetException</a></td>
        <td>Abstract base class for all rating set types</td>
    </tr>
    <tr><td><a href="rating/local_rating_set.html#LocalRatingSet">LocalRatingSet</a></td>
        <td><a href="rating/local_rating_set.html#LocaltRatingSetException">LocalRatingSetException</a></td>
        <td>Rating sets that perform all operations in local code</td>
    </tr>
    <tr><td><a href="rating/reference_rating_set.html#ReferenceRatingSet">ReferenceRatingSet</a></td>
        <td><a href="rating/reference_rating_set.html#ReferenceRatingSetException">ReferenceRatingSetException</a></td>
        <td>Rating sets that perform all operations in the CWMS database by sending/receiving data on each operation</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Other Rating Info</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="rating/paired_data.html#PairedData">PairedData</a></td>
        <td><a href="rating/paired_data.html#PairedDataException">PairedDataException</a></td>
        <td>HEC-DSS-style paired data objects</td>
    </tr>
    <tr><td><a href="rating/rating_specification.html#RatingSpecification">RatingSpecification</a></td>
        <td><a href="rating/rating_specification.html#RatingSpecificationException">RatingSpecificationException</a></td>
        <td>Location ID, template ID, time-based lookup methods and rounding parameter specifications for rating sets</td>
    </tr>
    <tr><td><a href="rating/rating_template.html#RatingTemplate">RatingTemplate</a></td>
        <td><a href="rating/rating_template.html#RatingTemplateException">RatingTemplateException</a></td>
        <td>Parameter names, parameter lookup behaviors for ratings</td>
    </tr>
    </table>
"""

__all__ = [
    "AbstractRating",
    "AbstractRatingSet",
    "LocalRatingSet",
    "LocalRatingSetException",
    "LookupMethod",
    "PairedData",
    "PairedDataException",
    "RatingSpecification",
    "RatingSpecificationException",
    "RatingTemplate",
    "RatingTemplateException",
    "ReferenceRatingSet",
    "TableRating",
    "TableRatingException",
    "SimpleRating",
    "abstract_rating",
    "abstract_rating_set",
    "local_rating_set",
    "paired_data",
    "rating_shared",
    "rating_template",
    "rating_specification",
    "reference_rating_set",
    "simple_rating",
    "table_rating",
]

from hec.rating import rating_shared, rating_specification
from hec.rating.abstract_rating import AbstractRating
from hec.rating.abstract_rating_set import AbstractRatingSet
from hec.rating.local_rating_set import LocalRatingSet, LocalRatingSetException
from hec.rating.paired_data import PairedData, PairedDataException
from hec.rating.rating_shared import LookupMethod
from hec.rating.rating_specification import (
    RatingSpecification,
    RatingSpecificationException,
)
from hec.rating.rating_template import RatingTemplate, RatingTemplateException
from hec.rating.reference_rating_set import ReferenceRatingSet
from hec.rating.simple_rating import SimpleRating
from hec.rating.table_rating import TableRating, TableRatingException

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
