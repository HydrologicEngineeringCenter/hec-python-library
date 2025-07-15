``TimeSeries`` objects use the ``to`` method (or ``ito`` for in-place) various conversions, including converting to a specific
unit or the default unit of the parameter in a specified unit system.

.. code-block::  python

    # instead of convertToEnglishUnits()
    ts2 = ts1.to("EN")
    ts1.ito("EN")

    # instead of convertToMetricUnits()
    ts2 = ts1.to("SI")
    ts1.ito("SI")