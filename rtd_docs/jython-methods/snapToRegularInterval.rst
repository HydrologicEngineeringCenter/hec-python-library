snapToRegularInterval()
=======================

**Signature:**

.. code-block:: python

    snap_to_regular(
        interval: Union[
            hec.Interval,
            str
        ],
        offset: Union[
            hec.TimeSpan,
            datetime.timedelta,
            str,
            NoneType
        ] = None,
        backward: Union[
            hec.TimeSpan, 
            datetime.timedelta, 
            str, 
            NoneType
        ] = None,
        forward: Union[
            hec.TimeSpan, 
            datetime.timedelta, 
            str, 
            NoneType
        ] = None,
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.snap_to_regular>`_

The hec-python-library equivalent of Jython method **snapToRegularInterval()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.snap_to_regular("1Hour", None, "PT5M", "PT5M")

====

**Signature:**

.. code-block:: python

    isnap_to_regular(
        interval: Union[
            hec.Interval,
            str
        ],
        offset: Union[
            hec.TimeSpan,
            datetime.timedelta,
            str,
            NoneType
        ] = None,
        backward: Union[
            hec.TimeSpan, 
            datetime.timedelta, 
            str, 
            NoneType
        ] = None,
        forward: Union[
            hec.TimeSpan, 
            datetime.timedelta, 
            str, 
            NoneType
        ] = None,
    ) -> TimeSeries

Convenience method for calling ``snap_to_regular(...)`` with ``inplace=True``.

**Example:**

.. code-block:: python

    ts.isnap_to_regular("1Hour", None, "PT5M", "PT5M")