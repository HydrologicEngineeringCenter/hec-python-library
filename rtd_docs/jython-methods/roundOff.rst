roundOff()
==========

**Signature:**

.. code-block:: python

    round_off(
        precision: int,
        tens_place: int,
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **roundOff()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.round_off(5, -1)

====

**Signature:**

.. code-block:: python

    iround_off(
        precision: int,
        tens_place: int,
    ) -> TimeSeries

Convenience method for calling ``round_off(...)`` with ``in_place=True``

**Example:**

.. code-block:: python

    ts1.iround_off(5, -1)
