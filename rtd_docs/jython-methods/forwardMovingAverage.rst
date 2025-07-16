forwardMovingAverage()
=======================

**Signature:**

.. code-block:: python

    forward_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **forwardMovingAverage()**:

Computes and returns a time series that is the forward moving average of this time series.

A forward moving average sets the value at each time to be the average of the values at that
time and a number of previous consecutive times.

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    avg_ts = ts.forward_moving_average(
        7,     # average over 7 values at each time step
        True,  # ignore invalid values when averaging
        True   # use less than 7 values a start and end
    )

    
====


**Signature:**

.. code-block:: python

    iforward_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
    ) -> TimeSeries

Convenience method for executing ``forward_moving_average(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts.iforward_moving_average(
        7,     # average over 7 values at each time step
        True,  # ignore invalid values when averaging
        True   # use less than 7 values a start and end
    )
