TimeSeriesValue Class
=====================

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeriesValue>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/timeseries_examples.ipynb>`_

General
-------

TimeSeriesValue objects are unnamed objects that represent a single value in a time series

Required Information
--------------------

 - **time**: :doc:`HecTime </classes/HecTime>`
 - **value**: :doc:`UnitQuantity </classes/UnitQuantity>`
 - **quality**: :doc:`Quality </classes/Quality>`

Notes
-----

The read-only ``tsv`` :doc:`TimeSeries </classes/TimeSeries>` property returns a list of TimeSeriesValue objects