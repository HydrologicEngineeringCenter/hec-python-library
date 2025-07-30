lastValidValue()
================

**Signature:**

.. code-block:: python

    last_valid_value: Optional[float]

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.last_valid_value>`_

The hec-python-library equivalent of Jython method **lastValidValue()**:

.. include:: _property.rst

The property value will be ``None`` if the time series is empty.

**Example:**

.. code-block:: python

    from hec import TimeSeries

    ts: TimeSeries
    val: Optional[float]

    val = ts.last_valid_value