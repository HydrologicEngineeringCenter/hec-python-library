TimeSeries Class
================

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/timeseries_examples.ipynb>`_

General
-------

TimeSeries objects are named objects that represent time series in CWMS or DSS contexts.

Required Information
--------------------

 - **location**: :doc:`Location </classes/Location>`
 - **parameter**: :doc:`Parameter </classes/Parameter>`
 - **parameter_type:** :doc:`ParameterType </classes/ParameterType>`
 - **interval:** :doc:`Interval </classes/Interval>`
 - **duration:** :doc:`Duration </classes/Duration>` (CWMS context only)
 - **version:** str (CWMS context only)

Optional Information
--------------------

 - **watershed:** str
 - **duration:** :doc:`Duration <Duration>` (DSS context only)
 - **version:** str (DSS context only)
 - **data:** pandas.DataFrame

Notes
-----

A TimeSeries with a missing or empty ``_data`` [1]_ field is considered empty

The ``_data`` field has the following format:

 - index: ``pandas.DatetimeIndex`` [2]_
 - ``"value"`` column: ``numpy.float64``
 - ``"quality"`` column: ``numpy.int64``


.. [1] The ``_data`` field is accessible through the ``data`` property.

.. [2] The ``pandas.Timestamp`` type used by ``pandas.DatetimeIndex`` has a year range of approximately 1677..2262, which results in the inability of ``TimeSeries`` objects to include dates outside this range, which may occur in HEC-DSS files.