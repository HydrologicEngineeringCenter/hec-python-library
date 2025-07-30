generateRegularIntervalTimeSeries()
===================================

**Signature:**

.. code-block:: python

    new_regular_time_series(
        name: str,
        start: Union[hec.HecTime, datetime.datetime, str],
        end: Union[hec.HecTime, datetime.datetime, str, int],
        interval: Union[hec.Interval, datetime.timedelta, str],
        offset: Union[hec.TimeSpan, datetime.timedelta, str, int, NoneType] = None,
        time_zone: Optional[str] = None,
        values: Union[List[float], float, NoneType] = None,
        qualities: Union[list[Union[hec.Quality, int]], hec.Quality, int, NoneType] = None
    ) -> TimeSeries    

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.new_regular_time_series>`_

The hec-python-library equivalent of Jython method **generateRegularIntervalTimeSeries()**:

Generates and returns a new regular (possibly local regular) interval time series with the
specified times, values, and qualities.

This is a static method and must be called on the ``TimeSeires`` class instead of a instance.

**Example:**

.. code-block:: python

    from hec import TimeSeries
    from datetime import datetime, timedelta

    values: list[float]

    ts1 = TimeSeries.new_regular_time_series(
        "Green_River.Stage.Inst.1Hour.0.Generated", # name
        "2025-01-01T01:00:00"                       # start
        len(values),                                # end
        "1Hour",                                    # interval
        values,                                     # values
    )

    dt = datetime(dt.now().year, 1, 1, 1)
    ts2 = TimeSeries.new_regular_time_series(
        "Green_River.Flow.Inst.1Hour.0.Generated", # name
        dt,                                        # start
        dt + timedelta(days=31),                   # end
        "1Hour",                                   # interval
        0                                          # values
    )
