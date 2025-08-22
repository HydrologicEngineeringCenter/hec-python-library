ReferenceRatingSet Class
========================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#ReferenceRatingSet>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/datastore_examples.ipynb>`_

ReferenceRatingSet
------------------

ReferenceRatingSet objects are references to rating sets within a CWMS database. They can be retrieved by using :doc:`CwmsDataStore </classes/CwmsDataStore>` objects.

Required Information
--------------------

 - **name**: str (the rating specification identifier)
 - **office**: str (the CWMS office that owns the ratings)
  
Notes
-----

Rating sets are collections of ratings for the same location and parameters. A rating set may have one or more ratings, each with its own effective date, and can
be thought of as an irregluar time series of ratings.

Ratings (and thus rating sets) may have one or more independent parameters and one dependent parameter. Reverse rating is possible only with ratings with a single independent parameter.
