``TimeSeries`` objects use standard python mathematial operators instead of mathematical methods.

Note that the result of a mathematical operation involving two ``TimeSeries`` objects will have
only the times contained in both ``TimeSeries``.

.. code-block:: python

    # instead of add()
    ts2 = ts1 + 5.4
    ts1 += 5.4
    ts3 = ts1 + ts2
    ts1 += ts2

    # instead of subtract()
    ts2 = ts1 - 5.4
    ts1 -= 5.4
    ts3 = ts1 - ts2
    ts1 -= ts2

    # instead of multiply()
    ts2 = ts1 * 5.4
    ts1 *= 5.4
    ts3 = ts1 * ts2
    ts1 *= ts2

    # instead of divide()
    ts2 = ts1 / 5.4
    ts1 /= 5.4
    ts3 = ts1 / ts2
    ts1 /= ts2

    # instead of integerDivide()
    ts2 = ts1 // 5.4
    ts1 //= 5.4
    ts3 = ts1 // ts2
    ts1 //= ts2

    # instead of exponentiation()
    ts2 = ts1 ** 5.4
    ts1 **= 5.4
    ts3 = ts1 ** ts2
    ts1 **= ts2

