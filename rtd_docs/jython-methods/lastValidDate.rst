lastValidDate()
===============

**Signature:**

.. code-block:: python

    last_valid_time: Optional[numpy.datetime64]

The hec-python-library equivalent of Jython method **lastValidDate()**:

.. include:: _property.rst

The property value will be ``None`` if the time series is empty.

**Example:**

.. code-block:: python

    from datetime import datetime
    from hec import HecTime, TimeSeries

    ts: TimeSeries
    dt: Optional[datetime]

    if ts.last_valid_time:
        dt = ts.HecTime(last_valid_time).datetime()
    else:
        dt = None
