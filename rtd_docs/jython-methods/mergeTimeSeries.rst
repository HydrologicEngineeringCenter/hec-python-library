mergeTimeSeries()
=================

**Signature:**

.. code-block:: python

    merge(
        other: Union[TimeSeries, List[TimeSeries]],
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.merge>`_

The hec-python-library equivalent of Jython method **mergeTimeSeries()**:

.. include:: _in_place.rst

**Example 1:**

.. code-block:: python

    ts_merged = ts1.merge(ts2)

**Example 2:**

.. code-block:: python

    ts_merged = ts1.merge(ts2).merge(ts3)

**Example 3:**

.. code-block:: python

    ts_merged = ts1.merge([ts2, ts3])

====

**Signature:**

.. code-block:: python

    imerge(
        other: Union[TimeSeries, List[TimeSeries]],
    ) -> TimeSeries

Convenience method for calling ``merge(...)`` with ``in_place=True``.

**Example 1:**

.. code-block:: python

    ts1.imerge(ts2)

**Example 2:**

.. code-block:: python

    ts1.imerge(ts2).merge(ts3)

**Example 3:**

.. code-block:: python

    ts1.imerge([ts2, ts3])