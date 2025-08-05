standardDeviation()
===================

**Signature 1:**

.. code-block:: python

    aggregate(
        func: Union[
            list[Union[Callable[[Any], Any], str]],
            Callable[[Any], Any],
            str
        ]
    ) -> Any

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.aggregate>`_

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

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.aggregate_ts>`_

The hec-python-library equivalent of Jython method **standardDeviation()**:

Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

**Example 1:**

.. code-block:: python

    stddev: float

    stddev = ts.aggregate("std")


**Example 2:**

.. code-block:: python

    ts_list: list[TimeSeries]

    ts_stddev = TimeSeries.aggregate_ts("std", ts_list)
