Interval Class
==============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.html#Interval>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/interval_examples.ipynb>`_

General
-------

Interval objects are named :doc:`TimeSpan </classes/TimeSpan>` objects that represent the recurrence time periods for
values in :doc:`TimeSeries </classes/TimeSeries>` or the time periods that a DSS block can contain.

Interval objects are not created by the user, but pre-created Interval objects are retrieved for specific contexts:

 - **Cwms:** Intervals for time series stored to or retrieved from CWMS databases
 
   - Regular Intervals
   - Irregular Interval
   - Pseudo-Regular Intervals
   - Local-Regular Intervals

 - **Dss:** Intervals for time series stored to or retrieved from HEC-DSS files

   - Regular Intervals
   - Irregular Interval
   - Pseudo-Regular Intervals

 - **DssBlock:** Intervals for subsequent HEC-DSS blocks for storing time series

   - Regular Intervals


