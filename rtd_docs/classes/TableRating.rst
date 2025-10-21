TableRating Class
=================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#TableRating>`_

General
-------

TableRating objects named objects that use lookup tables of independent and dependent parameter values. The lookup values are used in conjuction with lookup behaviors specified in the `RatingTemplate <RatingTemplate.html>`_ referenced in the object's identifier
to perform the transformation.

TableRating objects support the ``reverse_rate(...)`` method, but only on ratings with a single independent parameter.

Notes
-----

.. include:: _rating_desc.rst
