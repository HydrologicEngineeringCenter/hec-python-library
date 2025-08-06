Location Class
==============

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/location.html#Location>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/location_examples.ipynb>`_

General
-------
Location objects are named objects that indicate sites with which information is associated.
They may include geodetic and/or organizational information.

Required Information
--------------------

 - **name**

Optional Information
--------------------

 - **latitude**
 - **longitude**
 - **horizontal datum**
 - **elevation**
 - **vertical datum**
 - **time zone**
 - **office**
 - **kind**

Notes
-----
 
The only information required for a location is it's **name**. Location names comprise a base location name and an
optional sub-location name. If the **name** is hyphenated, the portion before the first hyphen is the base location name
and the portion after the first hyphen is the sub-location name.

If **vertical datum** is specified and can't be interpreted as ``NGVD-29`` or ``NAVD-88``, it will be set to ``OTHER``

If **office** is specified, it is normally the CWMS office ID for the locaiton

If **kind** is specified, it must be one of the following (case-insensitive):
 - ``BASIN``
 - ``EMBANKMENT``
 - ``ENTITY``
 - ``GATE``
 - ``LOCK``
 - ``OUTLET``
 - ``OVERFLOW``
 - ``PROJECT``
 - ``PUMP``
 - ``SITE``
 - ``STREAM``
 - ``STREAM_GAGE``
 - ``STREAM_LOCATION``
 - ``STREAM_REACH``
 - ``TURBINE``
 - ``WEATHER_GAGE``