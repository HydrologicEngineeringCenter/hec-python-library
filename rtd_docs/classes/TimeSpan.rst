TimeSpan Class
==============

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timespan.html#TimeSpan>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/timespan_examples.ipynb>`_

General
-------

TimeSpan objects are unnamed objects that represent generic time periods to 1-second precision. The time
periods may contain calendar (year, month) and/or time [1]_ (day, hour, minute, second) portions. [2]_

Unlike :doc:`/classes/HecTime` objects:

 - The months and days values may be zero
 - The days value may be arbitrarily large (positive or negative) without impacting the months value
 - The signs of the years and days values may be different. In this case the string representation of the object
   cannot be specified in a single ISO 8601 Duration string and is represented by two strings (one for the calendar
   portion and one for the time portion) separated by a comma.



.. [1] In this context ``time`` portion or information means ``non-calendar`` portion or information.

.. [2] Although ``day`` is calendar information for time instances, it is time information when combining a time period with a time instance or another time period.