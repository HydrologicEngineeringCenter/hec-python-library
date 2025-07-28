skewCoefficient()
=================

**Signature:**

.. code-block:: python

    aggregate(
        func: Union[
            list[Union[Callable[[Any], Any], str]],
            Callable[[Any], Any],
            str
        ]
    ) -> Any

The hec-python-library equivalent of Jython method **skewCoefficient()**:

**Example:**

.. code-block:: python

    skew_coeff: float

    skew_coeff = ts.aggregate("skew")
