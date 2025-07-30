min()
=====

**Signature 1:**

.. code-block:: python

    min_value(self) -> float

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.min_value>`_

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

The hec-python-library equivalent of Jython method **min()**:

Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

**Example 1:**

.. code-block:: python

    min_val = ts.min_value()


**Example 2:**

.. code-block:: python

    from hec import TimeSeries

    ts_list: list[TimeSeries]

    ts_min = TimeSeries.aggregate_ts("min", ts_list)