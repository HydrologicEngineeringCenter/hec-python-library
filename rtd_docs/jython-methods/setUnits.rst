setUnits()
==========

**Signature:**

.. code-block:: python

    set_unit(
        value: Union[pint.registry.Unit, str],
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **setUnits()**:

.. include:: _in_place.rst

**Notes:**

1. The *direct* equivalent requires using ``in_place=True`` or ``iset_unit()``.
2. Setting the unit does *not* convert the values to the specified unit. For that
   functionality use the ``to()`` or ``ito()`` method.

**Example:**

.. code-block:: python

    ts2 = ts1.set_unit("cfs")

====

**Signature:**

.. code-block:: python

    iset_unit(
        value: Union[pint.registry.Unit, str],
        in_place: bool = False
    ) -> TimeSeries

Convenience method for callint ``set_unit(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.iset_unit("cfs")
