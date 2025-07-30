product()
=========

The hec-python-library equivalent of Jython method **product()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    ts_list: list[TimeSeries]
    
    ts_prod = ts_list[1].copy()
    for ts in ts_list[1:]:
        ts_prod *= ts
