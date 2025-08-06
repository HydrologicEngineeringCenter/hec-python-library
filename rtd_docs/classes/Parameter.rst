Parameter Class
===============

`API Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/parameter.html#Parameter>`_

`Example Usage <https://github.com/HydrologicEngineeringCenter/hec-python-library/blob/main/examples/parameter_examples.ipynb>`_


General
-------
Parameter objects are named objects that indicate abstract or physical elements subject to measurement, computation, or estimation.

Required Information
--------------------
 - **name**
 - **unit**


Notes
-----
Parameter names comprise a base parameter name and an optional sub-parameter name. If the **name** is hyphenated, the portion
before the first hyphen is the base location name and the portion after the first hyphen is the sub-location name.

**Base Parameters**

Base parameter names are constrained to entries in the ``resrouces/base_parameters.txt`` file in the module installation directory.
When the module is installed, the file contains information shown in the table below. You can programmatically retrieve a list of
all available base parameters by executing:

.. code-block:: python

    from hec import Parameter
    print(Parameter.base_parameters())

.. code-block:: 

   ['%', 'Area', 'Code', 'Coeff', 'Conc', 'Cond', 'Count', 'Currency', 'Current', 'Date', 'Depth', 'DepthVelocity', 'Dir', 'Dist', 'Elev', 'Energy', 'Evap', 'EvapRate', 'Fish', 'Flow', 'Freq', 'Frost', 'Head', 'Height', 'Irrad', 'Length', 'Opening', 'Power', 'Precip', 'Pres', 'Probability', 'Rad', 'Ratio', 'Rotation', 'Speed', 'SpinRate', 'Stage', 'Stor', 'Temp', 'Thick', 'Timing', 'Travel', 'Turb', 'TurbF', 'TurbJ', 'TurbN', 'Volt', 'Volume', 'Width', 'pH']
 

**Base Parameter Units**

Parameter units are constrained to those that are compatible with the default units shown in the table below. You can retrieve a list of
all units compatible for a base parameter by executing the following for a specified base parameter:

.. code-block:: python

    from hec import Parameter
    print(Parameter.get_compatible_units(Parameter("Stor")))

.. code-block:: 

    ['1000 m3', 'ac-ft', 'dsf', 'ft3', 'gal', 'kaf', 'kdsf', 'kgal', 'km3', 'm3', 'mcm', 'mgal', 'mile3']

**Unit Aliases**

Many units have aliases that can be used in place of the actual unit. You may can retrieve a list of aliases by executing the following
for a specified unit:

.. code-block:: python

    from hec import unit
    print(unit.get_unit_aliases("ac-ft"))

.. code-block:: 

    ['AC-FT', 'ACFT', 'acft', 'acre-feet', 'acre-ft']

You can register a new unit alias by executing the following for a specified unit and alias:

.. code-block:: python

    from hec import unit
    unit.add_unit_alias("ac-ft", "ft-acre")
    print(unit.get_unit_aliases("ac-ft"))

.. code-block:: 

    ['AC-FT', 'ACFT', 'acft', 'acre-feet', 'acre-ft', 'ft-acre']

You can unregister a new unit alias by executing the following for a specified unit and alias:

.. code-block:: python

    from hec import unit
    unit.delete_unit_alias("ac-ft", "ft-acre")
    print(unit.get_unit_aliases("ac-ft"))

.. code-block:: 

    ['AC-FT', 'ACFT', 'acft', 'acre-feet', 'acre-ft']

Base Parameters Table
---------------------
.. include:: ../base_parameter_table.rst
