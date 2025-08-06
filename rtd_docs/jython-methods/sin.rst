sin()
=====

The hec-python-library equivalent of Jython method **sin()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.sin(ts.data["value"])

.. include:: _data_warning.rst

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.sin.html>`_ for details
