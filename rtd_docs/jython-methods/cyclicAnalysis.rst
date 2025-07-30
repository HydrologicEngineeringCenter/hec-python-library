cyclicAnalysis()
================

**Signature:**

.. code-block:: python

    cyclic_analysis(method: str = "linear") -> list[TimeSeries]

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.cyclic_analysis>`_

The hec-python-library equivalent of Jython method **cyclicAnalysis()**:

**Example:**

.. code-block:: python

    stats = ts.cyclic_analysis()

**Notes:**

1. The same set of statistics as the Jython method is generated.
2. The statistical method used is settable. Specify "hecmath" to use the same method used by the Jython method.
3. Version |release| sets the target year to 2100 instead of 3000 as in Jython due to a limitaion on Pandas DatetimeIndex type.
