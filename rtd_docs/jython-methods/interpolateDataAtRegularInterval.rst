interpolateDataAtRegularInterval()
==================================

**Signature:**

.. code-block:: python

    resample(
        operation: str,
        interval: Union[
                TimeSeries, 
                hec.TimeSpan, 
                datetime.timedelta, 
                NoneType
            ] = None,
        offset: Union[
                int, 
                hec.TimeSpan, 
                datetime.timedelta, 
                NoneType
            ] = None,
        start_time: Union[
                str,
                datetime.datetime, 
                hec.HecTime, 
                NoneType
            ] = None,
        end_time: Union[
                str, 
                datetime.datetime, 
                hec.HecTime, 
                NoneType
            ] = None,
        max_missing_percent: float = 25.0,
        entire_interval: Optional[bool] = None,
        before: Union[str, float] = 0.0,
        after: Union[str, float] = 'LAST',
        in_place: bool = False
    ) -> TimeSeries    

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.resample>`_

The hec-python-library equivalent of Jython method **interpolateDataAtRegularInterval()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    from hec import Interval

    intvl = Interval.get_cwms("1Day")

    ts2 = ts1.resample("Interpolate", intvl)

====

**Signature:**

.. code-block:: python

    iresample(
        operation: str,
        interval: Union[
                TimeSeries, 
                hec.TimeSpan, 
                datetime.timedelta, 
                NoneType
            ] = None,
        offset: Union[
                int, 
                hec.TimeSpan, 
                datetime.timedelta, 
                NoneType
            ] = None,
        start_time: Union[
                str,
                datetime.datetime, 
                hec.HecTime, 
                NoneType
            ] = None,
        end_time: Union[
                str, 
                datetime.datetime, 
                hec.HecTime, 
                NoneType
            ] = None,
        max_missing_percent: float = 25.0,
        entire_interval: Optional[bool] = None,
        before: Union[str, float] = 0.0,
        after: Union[str, float] = 'LAST',
    ) -> TimeSeries    

Convenience method for calling ``interpolateDataAtRegularInterval(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    from hec import Interval

    intvl = Interval.get_cwms("1Day")

    ts1.iresample("Interpolate", intvl)
