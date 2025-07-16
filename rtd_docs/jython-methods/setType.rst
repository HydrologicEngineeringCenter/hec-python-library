setType()
=========

**Signature:**

.. code-block:: python

    set_parameter_type(
        value: Union[hec.ParameterType, str],
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **setType()**:

.. include:: _in_place.rst

**Notes:** The *direct* equivalent requires using ``in_place=True`` or ``iset_parameter_type()``.

**Example:**

.. code-block:: python

    ts2 = ts1.set_parameter_type("Inst")

====

**Signature:**

.. code-block:: python

    iset_parameter_type(
        value: Union[hec.ParameterType, str],
    ) -> TimeSeries

Convenience method for callint ``set_parameter_type(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.iset_parameter_type("Inst")
