SimpleRating Class
==================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating.html#SimpleRating>`_

General
-------

SimpleRating is a non-instantiable base class of instantiable sub-classes, both of which use the ``<simple-rating>`` tag in XML serialized form.

Notes
-----

.. include:: _rating_desc.rst

SimpleRating provides:

 - signatures for methods required in sub-classes
 - implementation of methods with common code

The instantiable sub-classes are:

 - :doc:`TableRating </classes/TableRating>`
 - :doc:`ExpressionRating </classes/ExpressionRating>` (not yet implemented)
