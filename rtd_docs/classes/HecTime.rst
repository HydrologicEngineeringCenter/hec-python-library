HecTime Class
=============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/hectime.html#HecTime>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/hectime_examples.ipynb>`_

General
=======

HecTime objects are unnamed objects that represent time instances in a proleptic Julian calendar. The instances
may be specified at various granularities (precisions) that affect range of instances supported:

+-------------------------+----------------------------------------+-------------------+------------+
| Granularity / Precision | Available Fields                       | Year Range        | Time Zone? |
+=========================+========================================+===================+============+
| Second                  | year, month, day, hour, minute, second | 1901..2038        | Yes        |
+-------------------------+----------------------------------------+-------------------+------------+
| Minute                  | year, month, day, hour, minute         | -2184..5938       | Yes        |
+-------------------------+----------------------------------------+-------------------+------------+
| Hour                    | year, month, day, hour                 | -243084..246883   | Yes        |
+-------------------------+----------------------------------------+-------------------+------------+
| Day                     | year, month, day                       | -5877711..5879610 | No         |
+-------------------------+----------------------------------------+-------------------+------------+

The default granularity is 1 Minute.

Backward Compatibility
----------------------

The HecTime class provides complete compatibility for HEC's `hec.heclib.util.HecTime <https://www.hec.usace.army.mil/confluence/dssdocs/dssvueum/scripting/hectime-class>`_
Java class, which is necessary to process and generate the vast range of time integer values used in existing HEC-DSS files. [1]_

HecTime supports all the methods of the Java class, although some of the support is through properties and operators
instead of methods. The python method names are in snake case instead of camel case as in Java (e.g., 
``adjustToIntervalOffset()`` becomes ``adjust_to_interval_offset()``) .

Compatibility with ``datetime.datetime``
----------------------------------------

HecTime is designed to interoperate with Python's `datetime.datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_. It has many of the same methods, properites
and operators and is easily convertible to/from ``datetime.datetime``. [2]_ [3]_


.. [1] While HecTime supports the full range of possible HEC-DSS times, as of release |release|, the :doc:`/classes/TimeSeries` class does not.

.. [2] Only for HecTime objects that are within ``datetime.datetime``'s range

.. [3] Creating an HecTime object from at ``datetime.datetime`` object loses any microsecond information