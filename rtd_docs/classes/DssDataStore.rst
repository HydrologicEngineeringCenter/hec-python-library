DssDataStore Class
==================

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/datastore.html#DssDataStore>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/datastore_examples.ipynb>`_

General
-------

DssDataStore objects are named objects that provide the ability to

 - catalog records in an HEC-DSS file
 - store and retrieve objects to/from an HEC-DSS file

Required Information
--------------------

 - **name**: (the HEC-DSS file path)

Notes
-----

Cataloging may be performed on all HEC-DSS record types or restricted to one of the following record types:

 - arrays
 - grids
 - locations
 - paired data
 - text
 - time series
 - time series profiles
 - tins

The following object types may be stored or retrieved:

 - :doc:`paired data </classes/PairedData>`
 - :doc:`time series </classes/TimeSeries>`
