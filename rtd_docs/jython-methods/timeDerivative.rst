timeDerivative()
=======================

**Signature:**

.. code-block:: python

    time_derivative(in_place: bool = False) -> TimeSeries

The hec-python-library equivalent of Jython method **timeDerivative()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.time_derivative()

====

**Signature:**

.. code-block:: python

    itime_derivative() -> TimeSeries

**Example:**

.. code-block:: python

    ts.itime_derivative()
