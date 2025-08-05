accumulation()
==============

**Signature:**

.. code-block:: python

    accum(in_place: bool = False) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.accum>`_

The hec-python-library equivalent of Jython method **accumulation()**:

Returns a time series whose values are the accumulation of values in this time series.

.. include:: _in_place.rst

Missing values are ignored; the accumulation at those times is the same as for the previous time.

If a selection is present, all non-selected items are set to missing before the accumulation is computed. They remain missing in the retuned time series.

**Example:**

.. code-block:: python

    accum_ts = ts.accum()

    
====


**Signature:**

.. code-block:: python

    iaccum() -> TimeSeries

Convenience method for executing ``accum(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts.iaccum() # modifies ts to be the accumulation

