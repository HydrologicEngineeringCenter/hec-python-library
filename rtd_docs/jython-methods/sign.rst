sign()
======

The hec-python-library equivalent of Jython method **sign()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    import numpy as np

    ts.data["value"] = np.sign(ts.data["value"]).fillna(0)

.. include:: _data_warning.rst

See the `numpy documentation <https://numpy.org/doc/stable/reference/generated/numpy.sign.html>`_ for details