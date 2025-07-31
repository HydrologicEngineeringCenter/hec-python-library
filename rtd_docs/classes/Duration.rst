Duration Class
==============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.html#Duration>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/duration_examples.ipynb>`_

General
-------

Duration objects are named :doc:`TimeSpan </classes/TimeSpan>` objects that represent effective time periods of
values in :doc:`TimeSeries </classes/TimeSeries>`.

Non-instantaneous Durations come in two varieties:

 - **EOP:** (end-of-period) For these durations the value for the period is recorded at the time instance ending of the period.
 - **BOP:** (beginning-of-period) For these durations the value for the period is recorded at the time instance beginning of the period. 

Note that HEC-DSS time series do not have associated Durations; their durations are normally interpreted to be instaneous or
the same as the time series interval, depending on the :doc:`ParameterType </classes/ParameterType>`

Duration objects are not created by the user, but pre-created Duration objects are retrieved for specific
:doc:`Intervals </classes/Interval>`. Unless specified otherwise, EOP durations are returned.

