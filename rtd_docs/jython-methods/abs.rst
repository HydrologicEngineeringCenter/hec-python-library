abs()
=====

The hec-python-library equivalent of Jython method **abs()**:

**Signature:**

.. code-block:: python

    abs(ts: TimeSeries) -> TimeSeries

Returns a ``TimeSeries`` object whose values are the absolute values of ``TimeSeries`` on which it is called.

This is not a ``TimeSeries`` method but the standard python ``abs()`` function applit to a ``TimeSeries``

**Example:**

.. code-block:: python

    abs_ts = abs(ts)