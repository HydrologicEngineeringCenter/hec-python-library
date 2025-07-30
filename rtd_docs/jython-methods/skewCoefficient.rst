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

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.aggregate>`_

The hec-python-library equivalent of Jython method **skewCoefficient()**:

**Example:**

.. code-block:: python

    skew_coeff: float

    skew_coeff = ts.aggregate("skew")
