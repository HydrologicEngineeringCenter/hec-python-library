CwmsDataStore Class
===================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/datastore.html#CwmsDataStore>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/datastore_examples.ipynb>`_

General
-------

CwmsDataStore objects are named objects that provide the ability to

 - catalog objects in a CWMS database
 - store and retrieve objects to/from a CWMS database
 - perform raintgs in a CWMS database

Required Information
--------------------

 - **name**: (API root)

Optional Information
--------------------

 - **api_key**: (required for storing or rating)

Notes
-----

The following object types may be cataloged:

 - locations
 - ratings
 - time series

The following object types may be stored or retrieved:

 - :doc:`locations </classes/Location>`
 - :doc:`ratings </classes/ReferenceRatingSet>` (currently retrieve-only)
 - :doc:`time series </classes/TimeSeries>`

