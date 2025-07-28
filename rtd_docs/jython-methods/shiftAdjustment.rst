shiftAdjustment()
=================

**Signature**

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

The hec-python-library equivalent of Jython method **shiftAdjustment()**:

.. include:: _in_place.rst

**Example**

.. code-block:: python

    ts3 = ts1.resample("interp", ts2)

====

**Signature**

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

Convenience method for calling ``resample`(...)` with ``in_place=True``.

**Example**

.. code-block:: python

    ts1.iresample("interp", ts2)
