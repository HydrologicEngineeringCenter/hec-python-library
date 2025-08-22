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
 
 - AbstractRatingSet: :doc:`/classes/AbstractRatingSet`
 - ReferenceRatingSet: :doc:`/classes/ReferenceRatingSet`
 - PairedData: :doc:`/classes/PairedData`

Data Stores:
------------

- AbstractDataStore: :doc:`/classes/AbstractDataStore`
- CwmsDataStore: :doc:`/classes/CwmsDataStore`
- DssDataStore: :doc:`/classes/DssDataStore`

.. [1] For ``TimeSpan``, ``Interval``, and ``Duration``, the months position may also be a `Fraction <https://docs.python.org/3/library/fractions.html>`_ with denominator of 2 or 3 to support the ``Semi-Month`` and ``Tri-Month`` intervals in HEC-DSS