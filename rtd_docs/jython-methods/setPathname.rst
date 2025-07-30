setPathname()
=============

**Signature:**

.. code-block:: python

    name: str

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.name>`_

The hec-python-library equivalent of Jython method **setPathname()**:

.. include:: _property.rst

**Note:** The name must be a valid CWMS time series identifier or a valid HEC-DSS time series pathname

**Example:**

.. code-block:: python

    ts1.name = "New_Loc.Stage.Inst.1Hour.0.Test"

    ts2.name = "//New_loc/Stage//1Hour/Test/"
