cos()
=====

The hec-python-library equivalent of Jython method **cos()**:

.. include:: _not_supported.rst

You can work around this in the following manner.

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.cos(ts.data["value"])
