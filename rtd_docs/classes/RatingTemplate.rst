RatingTemplate Class
====================

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating/rating_template.html#RatingTemplate>`_

General
-------

RatingTemplate objects are named objects that specify the lookup methods for each independent parameter of any `TableRating <TableRating.html>`_ objects using the template.

The name (RatingTemplate ID) consists of:
 1. the parameters ID:
  a. a comma (``,``) separated ordered list of independent parameter IDs
  b. a semicolon (``;``)
  c. the dependent parameter ID
 2. a dot (``.``)
 3. the version (separates this template from others with the same parameters ID) 

For each independent parameter, lookup methods are specified for:
 - **in-range** the lookup method to use if the independent parameter value is within the range of the table values for the independent parameter
 - **out-range-low** the lookup method to use if the independent parameter value lower than all table values for the independent parameter
 - **out-range-high** the lookup method to use if the independent parameter value higher than all table values for the independent parameter

The available lookup methods for each are `here <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/rating/rating_shared.html#LookupMethod>`_

