shiftInTime()
=============

The hec-python-library equivalent of Jython method **shiftInTime()**:

.. include:: _not_implemented.rst

``TimeSeries`` objects use standard python shift operators instead of a method.

**Example**

.. code-block:: python

    from datetime import timedelta
    from hec import TimeSeries, TimeSpan

    ts1: TimeSeries
    ts2: TimeSeries
    tspan: TimeSpan
    tdelta: timedelta

    ts2 = ts1 << 6 # number of intervals (must be regular time series)
    ts2 = ts1 << tspan
    ts2 = ts1 << tdelta

    ts2 = ts1 >> 6 # number of intervals (must be regular time series)
    ts2 = ts1 >> tspan
    ts2 = ts1 >> tdelta

    ts1 <<= 6 # number of intervals (must be regular time series)
    ts1 <<= tspan
    ts1 <<= tdelta

    ts1 >>= 6 # number of intervals (must be regular time series)
    ts1 >>= tspan
    ts1 >>= tdelta
