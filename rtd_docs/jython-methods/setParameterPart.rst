setParameterPart()
==================

**Signature:**

.. code-block:: python

    set_parameter(
        value: Union[hec.Parameter, str],
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.set_parameter>`_

The hec-python-library equivalent of Jython method **setParameterPart()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    from hec import Parameter

    param: Parameter

    ts2 = ts1.set_parameter("Flow")

    ts4 = ts3.set_parameter(param)

====

**Signature:**

.. code-block:: python

    iset_parameter(value: Union[hec.Parameter, str]) -> TimeSeries

Convenience method for calling ``set_parameter(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    from hec import Parameter

    param: Parameter

    ts1.iset_parameter("Flow")

    ts2.iset_parameter(param)

