ParameterType Class
===================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/parameter.html#ParameterType>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/parameter_examples.ipynb>`_

General
-------
ParameterType objects are named objects that indicate how the values in a :doc:`time series </classes/TimeSeries>` are to be interpreted with respect to the
:doc:`duration </classes/Duration>` [1]_ of the time series values.

ParameterTypes have three contexts:

 - **RAW**: The context for time series not associated with any data store type.
 - **CWMS**: The context for CWMS time series. In this context the ParameterType name is part of the time series name
 - **DSS**: The context for HEC-DSS time series. In this context the ParameterType name is not part of the time series name, but of its metadata

Required Information
--------------------
 - **name**
 - **context**

Notes
-----

ParameterType context-specific names and descriptions:

+-------------------+-----------+------------------------------------+-----------------------------------------+
| RAW               | CWMS      | DSS                                | Description                             |
+===================+===========+====================================+=========================================+
| ``Total``         | ``Total`` | ``PER-CUM``                        | Accumulation over duration              |
+-------------------+-----------+------------------------------------+-----------------------------------------+
| ``Maximum``       | ``Max``   | ``PER-MAX``                        | Maximum value during duration           |
+-------------------+-----------+------------------------------------+-----------------------------------------+
| ``Minimum``       | ``Min``   | ``PER-MIN``                        | Minimum value during duration           |
+-------------------+-----------+------------------------------------+-----------------------------------------+
| ``Constant``      | ``Const`` | ``CONST``                          | Constant value over duration            |
+-------------------+-----------+------------------------------------+-----------------------------------------+
| ``Average``       | ``Ave``   | ``PER-AVER``                       | Average value over duration             |
+-------------------+-----------+------------------------------------+-----------------------------------------+
| ``Instantaneous`` | ``Inst``  | ``INST-CUM`` (for Precip or Count) | Value at end of duration [2]_           |
+                   |           +------------------------------------+                                         |
|                   |           | ``INST-VAL`` (for others)          |                                         |
+-------------------+-----------+------------------------------------+-----------------------------------------+

.. [1] HEC-DSS time series do not specify separate intervals and durations, so the implied duration is the interval

.. [2] Value at beginning of duration for BOP durations