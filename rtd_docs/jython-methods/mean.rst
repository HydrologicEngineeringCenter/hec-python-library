mean()
=====

**Signature 1:**

.. code-block:: python

    mean(self) -> float

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.mean>`_

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

The hec-python-library equivalent of Jython method **mean()**:

Signature 2 is a static method and must be called on the ``TimeSeries`` class instead of an instance

**Example 1:**

.. code-block:: python

    mean_val = ts.mean_value()


**Example 2:**

.. code-block:: python

    from hec import TimeSeries

    ts_list: list[TimeSeries]

    ts_mean = TimeSeries.aggregate_ts("mean", ts_list)