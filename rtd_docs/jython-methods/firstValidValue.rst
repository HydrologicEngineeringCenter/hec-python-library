firstValidValue()
================

**Signature:**

.. code-block:: python

    first_valid_value: Optional[float]

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.first_valid_value>`_

The hec-python-library equivalent of Jython method **firstValidValue()**:

.. include:: _property.rst

The property value will be ``None`` if the time series is empty.

**Example:**

.. code-block:: python

    from hec import TimeSeries

    ts: TimeSeries
    val: Optional[float]

    val = ts.first_valid_value