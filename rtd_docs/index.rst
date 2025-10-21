.. hec-python-library documentation master file, created by
   sphinx-quickstart on Mon Jul 14 19:48:28 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Scripting Guide for hec-python-library |release|
=================================================

General
-------
The hec-python-library is a pure python (python 3.9+) module that provides many of the capabilities of using Jython to access HEC's Java
class libraries. The library is focused on working with time series objects and associated infrasturcture:
   - locations
   - parameters
   - parameter types
   - times
   - intervals
   - durations
   - ratings

Pythonic Character
------------------
Since this module is written in Python, many operations that require class methods in Java are implemented as Python operators or
properties. This includes all arithmetic operaions on time series and shifting time series in time.

No Access to Java Programs
--------------------------
Unlike using Jython from with HEC's Java programs such as HEC-RTS, this module cannot access the state or data that exists only
in a currently-executing Java Virtual Machine. This means that this module cannot access, for example, the current RTS tab, alternative,
or forecast. Jython is still required for those types of requirements.


Storing/Retrieving Data
-----------------------
This module makes use of other modules to allow the storage and retrieval of time series and ratings. There are no hard dependencies
on these modules, but they must be installed in order to utilize the data stores.

+-----------------+----------------+-----------------+---------------------+
| Data Store Type | Module in PyPI | Minimum Version | Notes               |
+=================+================+=================+=====================+
| HEC-DSS Files   | hecdss         | 0.1.28          | HEC-DSS v7 only     |
+-----------------+----------------+-----------------+---------------------+
| CWMS Database   | cwms-python    | 0.8.2           | Access via CDA only | 
+-----------------+----------------+-----------------+---------------------+
   
More Info
---------
 - :doc:`CrossReference`
 - :doc:`classes/ClassOverviews`
 - `Examples <https://github.com/HydrologicEngineeringCenter/hec-python-library/tree/main/examples>`_
 - `Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec.html>`_
