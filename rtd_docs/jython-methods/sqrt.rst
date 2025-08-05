sqrt()
======

The hec-python-library equivalent of Jython method **sqrt()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    import numpy as np

    ts.data["value"] = np.sqrt(ts.data["value"]).fillna(0)

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.sqrt.html>`_ for details
