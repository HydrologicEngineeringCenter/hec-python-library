firstValidDate()
================

**Signature:**

.. code-block:: python

    first_valid_time: Optional[numpy.datetime64]

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.first_valid_time>`_

The hec-python-library equivalent of Jython method **firstValidDate()**:

.. include:: _property.rst

The property value will be ``None`` if the time series is empty.

**Example:**

.. code-block:: python

    from datetime import datetime
    from hec import HecTime, TimeSeries

    ts: TimeSeries
    dt: Optional[datetime]

    if ts.first_valid_time:
        dt = ts.HecTime(first_valid_time).datetime()
    else:
        dt = None
