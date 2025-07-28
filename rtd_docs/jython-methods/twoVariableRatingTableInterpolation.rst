twoVariableRatingTableInterpolation()
=====================================

**Signature:**

.. code-block:: python

    rate(to_rate: Any, label: Optional[str] = None) -> Any

The hec-python-library equivalent of Jython method **twoVariableRatingTableInterpolation()**:

**Example:**

.. code-block:: python

    from hec import TimeSeries
    from hec.rating import PaireData

    ts1: TimeSeries
    ts2: TimeSeries
    pd: PairedData

    ts3 = pd.rate([ts1, ts2])
