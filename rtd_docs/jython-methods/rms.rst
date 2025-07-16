rms()
=====

The hec-python-library equivalent of Jython method **rms()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    from hec import Timeseries

    ts_list: list[TimeSeries]

    ts_mean = TimeSeries.aggregate_ts(
        lambda s: np.sqrt(np.mean(np.array(s)**2)),
        ts_list
    )

