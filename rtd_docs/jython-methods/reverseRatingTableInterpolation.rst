reverseRatingTableInterpolation()
=================================

**Signature:**

.. code-block:: python

    reverse_rate(to_rate: Any, label: Optional[str] = None) -> Any

The hec-python-library equivalent of Jython method **reverseRatingTableInterpolation()**:

**Example:**

.. code-block:: python

    from hec import TimeSeries
    from hec.rating import PaireData

    ts1: TimeSeries
    pd: PairedData

    ts2 = pd.reverse_rate(ts1)
