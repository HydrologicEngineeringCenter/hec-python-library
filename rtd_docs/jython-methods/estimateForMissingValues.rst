estimateForMissingValues()
================================

**Signature:**

.. code-block:: python

    estimate_missing_values(
        max_missing_count: int,
        accumulation: bool = False,
        estimate_rejected: bool = True,
        set_questioned: bool = True,
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **estimateForMissingValues()**:

Unless estimating accumulated precipitation, set the ``accumulation`` parameter to ``False``.

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.estimate_missing_values(12)

====

**Signature:**

.. code-block:: python

    iestimate_missing_values(
        max_missing_count: int,
        accumulation: bool = False,
        estimate_rejected: bool = True,
        set_questioned: bool = True,
    ) -> TimeSeries

Convenience method for executing ``estimate_missing_values(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.estimate_missing_values(12)