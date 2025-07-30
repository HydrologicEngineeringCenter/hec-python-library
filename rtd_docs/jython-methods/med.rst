med()
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

The hec-python-library equivalent of Jython method **med()**:

Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

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