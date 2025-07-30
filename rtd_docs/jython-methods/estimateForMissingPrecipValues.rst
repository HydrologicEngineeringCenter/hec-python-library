estimateForMissingPrecipValues()
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

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.estimate_missing_values>`_

The hec-python-library equivalent of Jython method **estimateForMissingPrecipValues()**:

For estimating accumulated precipitation, set the ``accumulation`` parameter to ``True``.

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.estimate_missing_values(12, True)

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

    ts1.estimate_missing_values(12, True)