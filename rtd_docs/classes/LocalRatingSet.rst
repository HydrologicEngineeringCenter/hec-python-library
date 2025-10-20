LocalRatingSet Class
========================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#LocalRatingSet>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/rating_set_examples.ipynb>`_

LocalRatingSet
------------------

LocalRatingSet objects are instances of rating sets in python. They can be retrieved by using :doc:`CwmsDataStore </classes/CwmsDataStore>`
objects and stored to and retrieved from :doc:`DssDataStore </classes/DssDataStore>` objects. LocalRatingSet objects may also be serialized
to and deserialized from text files in XML format.

Required Information
--------------------

 - **name**: str (the rating specification identifier - even when retrieving from :doc:`DssDataStore </classes/DssDataStore>` objects [1_])
 - **office**: str (the CWMS office that owns the ratings)
 - **method**: str (must be ``"LAZY"`` (default) or ``"EAGER"`` - if ``"REFERENCE"`` is used with a :doc:`CwmsDataStore </classes/CwmsDataStore>` object a :doc:`LocalRatingSet </classes/ReferenceRatingSet>` object is retrieved")
  
Notes
-----

.. include:: _rating_set_desc.rst

All TableRating objects in LocalRatingSet objects retrieved with ``method="EAGER"`` have their ratings points populated on retrieval. This may load ratings points for effective times that
will not be used in subsequent calls to ``rate(...)`` or ``reverse_rate(...)``.

All TableRatings objects in LocalRatingSet objects retrieved with ``method="LAZY"`` (or no method specified) do not have their rating points populated on retrieval. The ratings points
for an effective time will be populated only when the specific rating is first used in a call to ``rate(...)`` or ``reverse_rate(...)``. Depending on the use case, this may substantially
speed up the overall retrieval and use of the rating set.

.. [1] See `this note <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#rating_note>`_ for using :doc:`DssDataStore </classes/DssDataStore>` objects to store LocalRatingSet objects.
