asin()
======

The hec-python-library equivalent of Jython method **asin()**:

.. include:: _not_supported.rst

You can work around this in the following manner.

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.arcsin(ts.data["value"])

