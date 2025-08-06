log10()
=====

The hec-python-library equivalent of Jython method **log10()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.log10(ts.data["value"])

.. include:: _data_warning.rst

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.log10.html>`_ for details

