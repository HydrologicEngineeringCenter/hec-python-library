ceil()
======

The hec-python-library equivalent of Jython method **ceil()**:

.. include:: _not_implemented.rst

The following example performs the equivalent:

.. code-block:: python

    # ts is a TimeSeires object
    import numpy as np

    ts.data["value"] = np.ceil(ts.data["value"])
