variance()
==========

**Signature 1:**

.. code-block:: python

    aggregate(
        func: Union[
            list[Union[Callable[[Any], Any], str]],
            Callable[[Any], Any],
            str
        ]
    ) -> Any

**Signature 2:**

.. code-block:: python

    aggregate_ts(
        func: Union[
            list[Union[Callable[[Any], Any], str]],
            Callable[[Any], Any],
            str
        ],
        timeseries: list[TimeSeries]
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **variance()**:


Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

**Example 1:**

.. code-block:: python

    import statistics
    value: float

    value = ts.aggregate(statistics.variance)


**Example 2:**

.. code-block:: python

    import statistics
    from hec import TimeSeries
    ts_list: list[TimeSeries]

    ts2 = TimeSeries.aggregate_ts(statistics.variance, ts_list)
