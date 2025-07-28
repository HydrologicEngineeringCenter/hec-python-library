successiveDifferences()
=======================

**Signature:**

.. code-block:: python

    diff(in_place: bool = False) -> TimeSeries

The hec-python-library equivalent of Jython method **successiveDifferences()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.diff()

====

**Signature:**

.. code-block:: python

    idiff() -> TimeSeries

**Example:**

.. code-block:: python

    ts.idiff()
