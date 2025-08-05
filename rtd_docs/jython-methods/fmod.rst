fmod()
======

**Signature:**

.. code-block:: python

    fmod(
        divisor: Union[TimeSeries, UnitQuantity, float, int],
        in_place: bool = False)

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.fmod>`_

The hec-python-library equivalent of Jython method **fmod()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.fmod(5.34)
    ts3 = ts1.fmod(ts2)

====

**Signature:**

.. code-block:: python

    ifmod(divisor: Union[TimeSeries, UnitQuantity, float, int])

Convenience method for executing ``fmod(...)`` with ``in_place=True``.


**Example:**

.. code-block:: python

    ts1.fmod(5.34)
    ts1.fmod(ts2)
