ElevParameter Class
===================

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.html#ElevParameter>`_

General
-------
ElevParameter objects are :doc:`Parameter <Parameter>` objects whose base parameter is ``Elev`` and have vertical datum information

Required Information
--------------------
 - **name** (must be ``Elev``)
 - **vertical datum info**


Notes
-----

The **vertical datum info** may have some or all of the following information:

 - unit (of elevation and offsets)
 - elevation
 - native datum
 - offset from native datum to NGVD-29
 - offset from native datum to NAVD-88
