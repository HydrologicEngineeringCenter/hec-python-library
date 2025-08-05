setTimeInterval()
=================

**Signature:**

.. code-block:: python

    set_interval(
        value: Union[hec.Interval, str, int],
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.set_interval>`_

The hec-python-library equivalent of Jython method **setTimeInterval()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    from hec import Interval

    ts2 = ts1.set_interval(
        Interval.get_any_cwms(lambda i: i.minutes==60 and i.is_psueudo_regular)
    )

    ts4 = ts3.set_interval("1Hour")

    ts6 = ts5.set_interval(60)

====

**Signature:**

.. code-block:: python

    iset_interval(value: Union[hec.Interval, str, int]) -> TimeSeries

Convenience method for calling ``setTimeInterval(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    from hec import Interval

    ts1.iset_interval(
        Interval.get_any_cwms(
            lambda i: i.minutes==60 and i.is_psueudo_regular
        )
    )

    ts2.iset_interval("1Hour")

    ts3.iset_interval(60)