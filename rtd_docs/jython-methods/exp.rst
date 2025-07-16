exp()
=====

The hec-python-library equivalent of Jython method **exp()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.exp(ts.data["value"])

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.exp.html>`_ for details

