med()
=====

.. include:: _not_implemented.rst

The following example performs the equivalent:

**Example 1:**


.. code-block:: python

    median_val: float

    median_val = ts.aggregate("median")


**Example 2:**

.. code-block:: python

    from hec import TimeSeries

    ts_list: list[TimeSeries]
    ts_median: TimeSeries

    ts_median = TimeSeries.aggregate_ts("median", ts_list)