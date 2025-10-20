Overview of hec-python-library Classes
======================================


Locations:
----------
 
 - :doc:`/classes/Location`
 
Parameters:
-----------

 - General: :doc:`/classes/Parameter`
 - Elevations: :doc:`/classes/ElevParameter`
 - Types: :doc:`/classes/ParameterType`

Times:
-----

All time-related classes have a ``values`` read/write property that is a list of six integers [1]_ representing:
  - year(s)
  - month(s)
  - day(s)
  - hour(s)
  - minute(s)
  - second(s)

 - Instances: :doc:`/classes/HecTime`
 - Periods:

   - Generic: :doc:`/classes/TimeSpan`
   - Value Recurrence: :doc:`/classes/Interval`
   - Value Duration: :doc:`/classes/Duration`

Values:
-------
 
 - Quantity: :doc:`/classes/UnitQuantity`
 - Quality: :doc:`/classes/Quality`

TimeSeries:
-----------

 - Individual Values: :doc:`/classes/TimeSeriesValue`
 - Sequence of Values: :doc:`/classes/TimeSeries`

Ratings:
--------
 
**Object Types**
 +---------------------------------------------+------------+---------------+------------------------+--------------------+
 | Object Type                                 | CWMS Store | CWMS Retrieve | HEC-DSS Store/Retrieve | XML Store/Retrieve |
 +=============================================+============+===============+========================+====================+
 | `Individual Ratings <AbstractRating.html>`_ | No         | No            | No                     | **Yes**            |
 +---------------------------------------------+------------+---------------+------------------------+--------------------+
 | `Rating Sets <AbstractRatingSet.html>`_     | No         | **Yes**       | **Yes**                | **Yes**            |
 +---------------------------------------------+------------+---------------+------------------------+--------------------+
 | `Paired Data <PairedData.html>`_            | No         | No            | **Yes**                | No                 | 
 +---------------------------------------------+------------+---------------+------------------------+--------------------+

**Naming**
 Individual ratings and ratings sets (but not paired data) share a naming convention that references metadata objects for the ratings/sets [2]_. There are four parts (separated by dot (``.``) characters) to this naming convention:
  1. The location identifier
  2. The parameters identifier:
    a. an ordered list of independent parameters, separated by comma (``,``) characters
    b. a semicolon (``;``) character
    c. the dependent parameter
  3. The template version
  4. The specification version

 Parts 2-3 (the rating template identifier) references a `RatingTemplate <RatingTemplate.html>`_ with the specified identifier.

 Parts 1-4 (the rating specification identifier) references a `RatingSpecification <RatingSpecification.html>`_ with the specified identifier.

 Paired data objects use the normal HEC-DSS pathname convention for paired data.

**Office**
 Rating sets and all included objects (individual ratings, specifications, templates) require an office identifier. Therefore, when retrieving them from
 a data store the data store must have a default office specified or the ``retrieve(...)`` method must use the ``office=`` parameter.

**Methods**
 All ratings objects (including paired data objects) have the following methods:
  - ``rate(...)`` for transforming independent parameter values to dependent parameter values
  - ``reverse_rate(...)`` for transforming dependent parameter values to independent parameter values. Not all classes support ``reverse_rate(...)``
 
**Classes**
 All classes directly related to ratings objects are:
  - :doc:`/classes/RatingTemplate`
  - :doc:`/classes/RatingSpecification`
  - :doc:`/classes/AbstractRating`
  - :doc:`/classes/SimpleRating`
  - :doc:`/classes/TableRating`
  - ExpressionRating: (not implemented yet)
  - VirtualRating: (not implemented yet)
  - TransitionalRating:  (not implemented yet)
  - :doc:`/classes/AbstractRatingSet`
  - :doc:`/classes/LocalRatingSet`
  - :doc:`/classes/ReferenceRatingSet`
  - :doc:`/classes/PairedData`

Data Stores:
------------

- AbstractDataStore: :doc:`/classes/AbstractDataStore`
- CwmsDataStore: :doc:`/classes/CwmsDataStore`
- DssDataStore: :doc:`/classes/DssDataStore`

.. [1] For ``TimeSpan``, ``Interval``, and ``Duration``, the months position may also be a `Fraction <https://docs.python.org/3/library/fractions.html>`_ with denominator of 2 or 3 to support the ``Semi-Month`` and ``Tri-Month`` intervals in HEC-DSS
.. [2] Even when using HEC-DSS files to store rating sets. See `this note <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#rating_note>`_.