sum()
=====

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

The hec-python-library equivalent of Jython method **sum()**:

Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

**Example 1:**

.. code-block:: python

    value: float

    value = ts.aggregate("sum")


**Example 2:**

.. code-block:: python

    ts_list: list[TimeSeries]

    ts_sum = TimeSeries.aggregate_ts("sum", ts_list)
