RatingSpecification Class
=========================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating/rating_specification.html#RatingSpecification>`_

General
-------

RatingSpecification objects are named objects that specify the following information about `RatingSet <abstract_rating_set.html#AbstractRatingSet>`_ objects:
 - lookup methods for the effective times of ratings withing the rating set
 - the agency responsible for generating ratings in the rating set
 - rounding specifications for all independent parameter values and dependent parameter values output from calling ``rate(...)`` or ``reverse_rate(...)`` on the rating set (see `UsgsRounder <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rounding.html#UsgsRounder>`_)
 - whether rating sets with this specification are active (should be used)
 - whether ratings with this specification should be automatically updated from the source agency
 - whether ratings with this specification that are automatically updated from the source agency should automatically be marked as active
 - whether ratings with this specification that are automatically updated from the source agency should automatically have any rating extensions from the previous effective time applied

Required Information
--------------------

 - **name**: str (RatingSpecification ID)
 - **office**: str

Notes
-----

The name (RatingSpecification ID) consists of:
 1. the location ID
 2. a dot (``.``)
 3. the RatingTemplate ID of the `RatingTemplate <RatingTemplate.html>`_ used for this specification
 4. a dot (``.``)
 5. the specification version (separates this specification from others with the same location and template ID) 

Lookup methods are specified for:
 - **in-range** the lookup method to use if the date/time of the value(s) to be rated is within range of the effective times in the rating set
 - **out-range-low** the lookup method to use if the date/time of the value(s) to be rated is earlier than any effective time in the rating set
 - **out-range-high** the lookup method to use if the date/time of the value(s) to be rated is later than any effective time in the rating set

The available lookup methods for each are `here <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating/rating_shared.html#LookupMethod>`_

(see `UsgsRounder <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rounding.html#UsgsRounder>`_)

