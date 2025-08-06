Quality Class
=============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/quality.html#Quality>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/quality_examples.ipynb>`_

General
-------

Quality objects are unnamed objects that represent the quality assessments of :doc:`TimeSeries </classes/TimeSeries>` values.

The quality code is integer whose lower 32 bit are mapped to specific meanings in the following categories:
  - screened?
  - validity flags
  - value range
  - modificatied?
  - modification cause
  - modification method
  - tests failed
  - protected?

Quality objects provide properties and methods to manage the values of the categories.

Required Information
--------------------

 - **code**
