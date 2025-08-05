PairedData Class
================

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.rating.html.PairedData>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/paired_data_examples.ipynb>`_

General
=======

PairedData objects are named rating-like objects that can be used to rate values of a one or two independent parameter to values of one or more dependent parameters.

Required Information
--------------------

 - **name**: str (normally the associated HEC-DSS pathname)
  
Notes
-----

PairedData objects may not be store to or retrieved from CWMS databases; they may be stored to and retrieved from HEC-DSS files

Unlike ratings objects:

 - PairedData objects may have only one or two independent parameters
 - PairedData objects may have multiple dependent parameters
 - PairedData objects can contain only table-based rating Information
 - When used as a two-independent variable rating, each second independent parameter value must have identical first independent parameter values

PairedData objects are structured to have a primary independent parameter with one or more secondary parameters:

 - If only one secondary parameter is used, it need not be labeled, and becomes the single dependent parameter
 - If more than one secondary parameter is used, they must each be labeled
 
   -  If two or more secondary parameters are labeled with increasing numeric values (in text form), the labels may be used as values of a second independent parameter with the values of those secondary parameters being the values of the single dependent parameter
   -  Otherwise the labels are considered to be sub-parameters of the dependent base parameter and their values constitute the values of the multiple dependent parameters