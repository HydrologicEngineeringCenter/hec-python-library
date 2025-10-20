ReferenceRatingSet Class
========================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#ReferenceRatingSet>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/rating_set_examples.ipynb>`_

ReferenceRatingSet
------------------

ReferenceRatingSet objects are references to rating sets within a CWMS database. They can be retrieved by using :doc:`CwmsDataStore </classes/CwmsDataStore>` objects.

Required Information
--------------------

 - **name**: str (the rating specification identifier)
 - **office**: str (the CWMS office that owns the ratings)
 - **method**: str (must be ``"REFERENCE"`` to retrieve a ReferenceRatingSet object - otherwise a :doc:`LocalRatingSet </classes/LocalRatingSet>` object is retrieved)
  
Notes
-----

.. include:: _rating_set_desc.rst
