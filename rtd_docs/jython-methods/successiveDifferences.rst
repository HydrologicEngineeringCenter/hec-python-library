successiveDifferences()
=======================

**Signature:**

.. code-block:: python

    diff(in_place: bool = False) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.diff>`_

The hec-python-library equivalent of Jython method **successiveDifferences()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.diff()

====

**Signature:**

.. code-block:: python

    idiff() -> TimeSeries

Convenience method for calling ``successiveDifferences(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts.idiff()
