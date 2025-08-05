setLocation()
=============

**Signature:**

.. code-block:: python

    set_location(
        value: Union[hec.Location, str],
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.set_location>`_

The hec-python-library equivalent of Jython method **setLocation()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    from hec import Location

    loc: Location

    ts2 = ts1.set_location("New_Location")

    ts4 = ts3.set_location(loc)

====

**Signature:**

.. code-block:: python

    iset_location(value: Union[hec.Location, str]) -> TimeSeries

Convenience method for calling ``set_location(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    from hec import Location

    loc: Location

    ts1.iset_location("New_Location")

    ts2.iset_location(loc)

