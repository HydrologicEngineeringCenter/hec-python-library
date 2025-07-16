extractTimeSeriesDataForTimeSpecification()
===========================================

The hec-python-library equivalent of Jython method **extractTimeSeriesDataForTimeSpecification()**:

.. include:: _not_implemented.rst

Instead, use the ``select()``, ``filter()``, and ``set_interval`` methods (or ``iselect()``, ``ifilter()``, and ``iset_interval``
to modify in-place).

.. code-block:: python

    # instead of this Jython:
    tsm2 = tsm1.extractTimeSeriesForTimeSpecification(
        "DAYWEEK", 
        "SUN-MON", 
        True, 
        0, 
        True)

    #use this
    ts2 = ts1 \
        .set_interval("Irr") \
        .select(lambda t: t.time.dayOfWeekName()[:3] in ("Sun", "Mon")) \
        .filter()

    # instead of this Jython:
    tsm1 = tsm1.extractTimeSeriesForTimeSpecification(
        "DAYWEEK", 
        "SUN-MON", 
        True, 
        0, 
        True)

    #use this
    ts1 \
        .iset_interval("Irr") \
        .iselect(lambda t: t.time.dayOfWeekName()[:3] in ("Sun", "Mon")) \
        .ifilter()

