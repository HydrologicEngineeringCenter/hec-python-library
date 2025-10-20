ceil()
======

The hec-python-library equivalent of Jython method **ceil()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    # ts is a TimeSeries object
    import numpy as np

    ts.data["value"] = np.ceil(ts.data["value"])

.. include:: _data_warning.rst

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.ceil.html>`_ for details
