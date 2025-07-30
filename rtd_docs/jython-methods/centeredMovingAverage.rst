centeredMovingAverage()
=======================

**Signature:**

.. code-block:: python

    centered_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.centered_moving_average>`_

The hec-python-library equivalent of Jython method **centeredMovingAverage()**:

Computes and returns a time series that is the centered moving average of this time series.

A centered moving average sets the value at each time to be the average of the values at that
time and a number of previous and following consecutive times.

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    avg_ts = ts.centered_moving_average(
        7,     # average over 7 values at each time step
        True,  # ignore invalid values when averaging
        True   # use less than 7 values a start and end
    )

    
====


**Signature:**

.. code-block:: python

    icentered_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
    ) -> TimeSeries

Convenience method for executing ``centered_moving_average(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts.icentered_moving_average(
        7,     # average over 7 values at each time step
        True,  # ignore invalid values when averaging
        True   # use less than 7 values a start and end
    )
