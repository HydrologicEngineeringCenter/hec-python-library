gmean()
=======

The hec-python-library equivalent of Jython method **gmean()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    from hec import Timeseries

    ts_list: list[TimeSeries]

    ts_mean = TimeSeries.aggregate_ts(
        statistics.geometric_mean,
        ts_list
    )
