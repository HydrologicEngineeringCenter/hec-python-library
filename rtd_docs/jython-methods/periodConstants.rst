periodConstants()
=================

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

The hec-python-library equivalent of Jython method **periodConstants()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts3 = ts1.resample("prev", ts2, before="missing")

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


**Example:**

.. code-block:: python

    ts1.iresample("prev", ts2, before="missing")
