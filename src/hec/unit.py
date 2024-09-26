"""
Module for unit definitions and conversions.

Uses the [Pint unit library](https://pint.readthedocs.io) for operations.
For any unit some or all of the following exist:
* **Pint unit:** The Pint Unit object or a valid name or definition used to create a Pint Unit object
* **Unit name:** The local name used to refer to the Pint unit
* **Unit aliases:** (Optional) Aliases for the unit name
All Pint Units may be defined in a Pint unit registry with specified names. However those
names (but not the definitions) must adhere to Python identifier rules which elimiates many
common unit names. Although non-identifier aliases can (sometimes) be associated with the
unit definitions, there is no mechanism to output the units in those aliases. If a Pint Unit
does not have a name, its definition is output in its place. For this reason,unit names and
aliaes are maintained in dictionaries separate from the Pint library.<br>

**Example 1:** Unit name is not a valid Python identifier but is the same as the Pint Unit definition
* Unit name = `g/l`
* Pint unit definition = `g/l`
* Unit aliases =
    * `gm/l`
    * `grams per liter`
    * `grams/liter`

```
>>> from hec import unit
>>> g_per_l_unit = unit.get_pint_unit('g/l')
>>> print(repr(g_per_l_unit))
<Unit('gram / liter')>
>>> print(g_per_l_unit)
gram / liter
>>> print(f"{g_per_l_unit:D}")
gram / liter
>>> print(f"{g_per_l_unit:~D}")
g / l
>>> print(f"{g_per_l_unit:C}")
gram/liter
>>> print(f"{g_per_l_unit:~C}")
g/l
>>> print(f"{g_per_l_unit:P}")
gram/liter
>>> print(f"{g_per_l_unit:~P}")
g/l
>>> print(unit.get_unit_name(g_per_l_unit))
g/l
>>>
```

**Example 2:** Unit name is a valid Python identifier but is not the same as the Pint Unit definition
* Pint unit definition = `ft**3/s`
* Unit name = `cfs`
* Unit aliases =
    * `CFS`
    * `FT3/S`
    * `FT3/SEC`
    * `cu-ft/sec`
    * `cuft/sec`
    * `ft3/s`
    * `ft3/sec`
    * `ft^3/s`

```
>>> from hec import unit
>>> cfs_unit = unit.get_pint_unit("CFS")
>>> print(repr(cfs_unit))
<Unit('foot ** 3 / second')>
>>> print(cfs_unit)
foot ** 3 / second
>>> print(f"{cfs_unit:D}")
foot ** 3 / second
>>> print(f"{cfs_unit:~D}")
ft ** 3 / s
>>> print(f"{cfs_unit:C}")
foot**3/second
>>> print(f"{cfs_unit:~C}")
ft**3/s
>>> print(f"{cfs_unit:P}")
foot³/second
>>> print(f"{cfs_unit:~P}")
ft³/s
>>> print(unit.get_unit_name(cfs_unit))
cfs
>>>
```
"""

__all__ = [
    "get_unit_registry",
    "get_unit_context",
    "get_pint_unit",
    "get_unit_name",
    "get_unit_aliases",
    "get_compatible_units",
    "convert_units",
    "UnitException",
    "UnitQuantity",
]
import copy, math, os, sys

import pint.facets

import_dir = os.path.abspath(".")
if not import_dir in sys.path:
    sys.path.append(import_dir)

from functools import total_ordering
from fractions import Fraction
from typing import Any
from typing import Optional
from typing import Union
from typing import cast
from pint.errors import UndefinedUnitError
import pint


class UnitException(Exception):
    """
    Exception specific to Unit operations
    """

    pass


ureg = pint.UnitRegistry()
# -------------------------------------- #
# define additional deminsions for units #
# -------------------------------------- #
ureg.define("USD = [currency]")
ureg.define("USD_per_kacre_foot = USD/kacre_foot")
ureg.define("USD_per_Mcm = USD/Mcm")
ureg.define("US_survey_foot = [length]")
ureg.define("FNU = [turbidity_fnu]")
ureg.define("JTU = [turbidity_jtu]")
ureg.define("NTU = [turbidity_ntu]")
ureg.define("n_a = []")
ureg.define("unit = []")
ureg.define("_pH = [hydrogen_ion_concentration_index]")
ureg.define("B_unit = [time]**0.5")
# --------------------------------------------------- #
# define units that are magnitudes of other units but #
# can't use standard SI prefixes                      #
# --------------------------------------------------- #
ureg.define("Mcm = 1e6 m**3")
ureg.define("_1000_m2 = 1000*m**2")
ureg.define("_1000_m3 = 1000*m**3")
ureg.define("US_survey_foot = 1200/3937 m")
ureg.define("kcfs = 1e3*ft**3/s")
ureg.define("kcms = 1e3*m**3/s")
ureg.define("kdsf = kcfs*d")
ureg.define("rev = 360*deg")
# -------------------------------------------- #
# define a local context for unit redefinition #
# -------------------------------------------- #
ctx = ureg.Context()
ctx.redefine("acre = 43560*ft**2")  # default is based on obsolete US survey foot
ctx.redefine("acre_foot = 43560*ft**3")  # default is based on obsolete US survey foot
ctx.redefine("US_survey_foot = 1200/3937*m")  # definition of obsoluete US survey foot

# ----------------------------- #
# Pint units for each unit name #
# ----------------------------- #
pint_units_by_unit_name = {
    "%": "%",
    "$": "USD",
    "$/kaf": "USD_per_kacre_foot",
    "$/mcm": "USD_per_Mcm",
    "1/ft": "1/ft",
    "1/m": "1/m",
    "1000 m2": "_1000_m2",
    "1000 m3": "_1000_m3",
    "ac-ft": "acre_foot",
    "acre": "acre",
    "ampere": "amp",
    "B": "B_unit",
    "bar": "bar",
    "C-day": "delta_degC*d",
    "C": "degC",
    "cal": "cal",
    "cfs": "ft**3/s",
    "cfs/mi2": "ft**3/s/mi**2",
    "cm": "cm",
    "cm/day": "cm/d",
    "cm2": "cm**2",
    "cms": "m**3/s",
    "cms/km2": "m**3/s/km** 2",
    "day": "d",
    "deg": "deg",
    "dsf": "ft**3/s*d",
    "F-day": "delta_degF*d",
    "F": "degF",
    "FNU": "FNU",
    "ft": "ft",
    "ft/hr": "ft/h",
    "ft/s": "ft/s",
    "ft2": "ft**2",
    "ft2/s": "ft**2/s",
    "ft3": "ft**3",
    "ftUS": "US_survey_foot",
    "g": "g",
    "g/l": "g/l",
    "g/m3": "g/m**3",
    "gal": "gal",
    "gm/cm3": "g/cm**3",
    "gpm": "gal/min",
    "GW": "GW",
    "GWh": "GWh",
    "ha": "ha",
    "hr": "h",
    "Hz": "Hz",
    "in-hg": "inHg",
    "in": "in",
    "in/day": "in/d",
    "in/deg-day": "in/(delta_degF*d)",
    "in/hr": "in/hr",
    "J": "J",
    "J/m2": "J/m**2",
    "JTU": "JTU",
    "K": "K",
    "k$": "kUSD",
    "kaf": "kacre_foot",
    "KAF/mon": "kacre_foot/month",
    "kcfs": "kcfs",
    "kcms": "kcms",
    "kdsf": "kdsf",
    "kg": "kg",
    "kgal": "kgal",
    "kHz": "kHz",
    "km": "km",
    "km2": "km**2",
    "km3": "km**3",
    "knot": "knot",
    "kPa": "kPa",
    "kph": "kph",
    "kW": "kW",
    "kWh": "kWh",
    "langley": "langley",
    "langley/min": "langley/min",
    "lb": "lbf",
    "lbm": "lb",
    "lbm/ft3": "lb/ft**3",
    "m": "m",
    "m/day": "m/d",
    "m/hr": "m/h",
    "m/s": "mps",
    "m2": "m**2",
    "m2/s": "m**2/s",
    "m3": "m**3",
    "mb": "mbar",
    "mcm": "Mcm",
    "mcm/mon": "Mcm/month",
    "mg": "mg",
    "mg/l": "mg/l",
    "mgal": "Mgal",
    "mgd": "Mgal/d",
    "mho": "S",
    "MHz": "MHz",
    "mi": "mi",
    "mile2": "mi**2",
    "mile3": "mi**3",
    "min": "min",
    "MJ": "MJ",
    "mm-hg": "mmHg",
    "mm": "mm",
    "mm/day": "mm/d",
    "mm/deg-day": "mm/(delta_degC*d)",
    "mm/hr": "mm/h",
    "mph": "mph",
    "MW": "MW",
    "MWh": "MWh",
    "N": "N",
    "n/a": "n_a",
    "NTU": "NTU",
    "ppm": "mg/l",
    "psi": "psi",
    "rad": "rad",
    "rev": "rev",
    "rpm": "rpm",
    "S": "S",
    "sec": "s",
    "su": "_pH",
    "ton": "ton",
    "ton/day": "ton/d",
    "tonne": "tonne",
    "tonne/day": "tonne/d",
    "TW": "TW",
    "TWh": "TWh",
    "ug": "ug",
    "ug/l": "ug/l",
    "umho": "uS",
    "umho/cm": "uS/cm",
    "unit": "unit",
    "uS": "uS",
    "volt": "V",
    "W": "W",
    "W/m2": "W/m**2",
    "Wh": "Wh",
}

# -------------------------- #
# aliases for each unit name #
# -------------------------- #
unit_names_by_alias = {
    "$/KAF": "$/kaf",
    "1000 M2": "1000 m2",
    "1000 M3": "1000 m3",
    "1000 ac-ft": "kaf",
    "1000 ac-ft/mon": "KAF/mon",
    "1000 cfs": "kcfs",
    "1000 cfs-day": "kdsf",
    "1000 cms": "kcms",
    "1000 cu m": "1000 m3",
    "1000 cu-ft/sec": "kcfs",
    "1000 dsf": "kdsf",
    "1000 ft3/sec": "kcfs",
    "1000 gallon": "kgal",
    "1000 gallons": "kgal",
    "1000 sfd": "kdsf",
    "1000 sq m": "1000 m2",
    "1000 sq meters": "1000 m2",
    "1000000 m3": "mcm",
    "AC-FT": "ac-ft",
    "ACFT": "ac-ft",
    "ACRE": "acre",
    "ACRES": "acre",
    "AMP": "ampere",
    "AMPERE": "ampere",
    "AMPERES": "ampere",
    "AMPS": "ampere",
    "ATM": "bar",
    "ATMOSPHERE": "bar",
    "ATMOSPHERES": "bar",
    "Amp": "ampere",
    "Ampere": "ampere",
    "Amperes": "ampere",
    "Amps": "ampere",
    "BAR": "bar",
    "BARS": "bar",
    "B_UNIT": "B_unit",
    "CELSIUS": "C",
    "CENTIGRADE": "C",
    "CFS": "cfs",
    "CMS": "cms",
    "Celsius": "C",
    "Centigrade": "C",
    "DAY": "day",
    "DAYS": "day",
    "DEG C": "C",
    "DEG F": "F",
    "DEG-C": "C",
    "DEG-F": "F",
    "DEGC-D": "C-day",
    "DEGF": "F",
    "DEGF-D": "F-day",
    "DSF": "dsf",
    "Deg-C": "C",
    "Deg-F": "F",
    "DegC": "C",
    "DegF": "F",
    "FAHRENHEIT": "F",
    "FEET": "ft",
    "FT": "ft",
    "FT/S": "ft/s",
    "FT3/S": "cfs",
    "FT3/SEC": "cfs",
    "Fahrenheit": "F",
    "Feet": "ft",
    "GAL": "gal",
    "GPM": "gpm",
    "GWH": "GWh",
    "Gal/min": "gpm",
    "HOUR": "hr",
    "HOURS": "hr",
    "HR": "hr",
    "HZ": "Hz",
    "IN": "in",
    "INCHES": "in",
    "Inch": "in",
    "JOULE": "J",
    "JOULES": "J",
    "K$": "k$",
    "KAF": "kaf",
    "KCFS": "kcfs",
    "KCMS": "kcms",
    "KDSF": "kdsf",
    "KELVIN": "K",
    "KELVINS": "K",
    "KGAL": "kgal",
    "KHZ": "kHz",
    "KHz": "kHz",
    "KSFD": "kdsf",
    "KW": "kW",
    "KWH": "kWh",
    "M/S": "m/s",
    "M2": "m2",
    "M3": "m3",
    "M3/S": "cms",
    "M3/SEC": "cms",
    "MEGAJOULE": "MJ",
    "MEGAJOULES": "MJ",
    "METER": "m",
    "METERS PER SECOND": "m/s",
    "METERS": "m",
    "METRE": "m",
    "METRES": "m",
    "MG/L": "mg/l",
    "MGAL": "mgal",
    "MGD": "mgd",
    "MHZ": "MHz",
    "MILES PER HOUR": "mph",
    "MIN": "min",
    "MINUTE": "min",
    "MINUTES": "min",
    "MM": "mm",
    "MPH": "mph",
    "MPS": "m/s",
    "MWH": "MWh",
    "Mile": "mi",
    "PERCENT": "%",
    "POUNDS": "lb",
    "SEC": "sec",
    "SECOND": "sec",
    "SECONDS": "sec",
    "SFD": "dsf",
    "SURVEY FEET": "ftUS",
    "SURVEY FOOT": "ftUS",
    "TGAL": "kgal",
    "TWH": "TWh",
    "UMHO/CM": "umho/cm",
    "UMHOS/CM": "umho/cm",
    "VOLT": "volt",
    "VOLTS": "volt",
    "Volt": "volt",
    "Volts": "volt",
    "WH": "Wh",
    "acft": "ac-ft",
    "acre-feet": "ac-ft",
    "acre-ft": "ac-ft",
    "acres": "acre",
    "amp": "ampere",
    "amperes": "ampere",
    "amps": "ampere",
    "atm": "bar",
    "atmosphere": "bar",
    "atmospheres": "bar",
    "b": "B",
    "b-unit": "B",
    "b_unit": "B",
    "bars": "bar",
    "calorie": "cal",
    "calories": "cal",
    "celsius": "C",
    "centimeter": "cm",
    "centimeters": "cm",
    "cfs-day": "dsf",
    "cu ft": "ft3",
    "cu km": "km3",
    "cu m": "m3",
    "cu meter": "m3",
    "cu meters": "m3",
    "cu mile": "mile3",
    "cu miles": "mile3",
    "cu-ft/sec": "cfs",
    "cu-meters/sec": "cms",
    "cubic feet": "ft3",
    "cubic meters": "m3",
    "cuft/sec": "cfs",
    "cusecs": "cfs",
    "cycles/s": "Hz",
    "cycles/sec": "Hz",
    "day": "day",
    "days": "day",
    "deg C": "C",
    "deg F": "F",
    "deg c": "C",
    "deg f": "F",
    "degC": "C",
    "degC-day": "C-day",
    "degF": "F",
    "degF-day": "F-day",
    "fahrenheit": "F",
    "feet": "ft",
    "fnu": "FNU",
    "foot": "ft",
    "fps": "ft/s",
    "ft/sec": "ft/s",
    "ft3/s": "cfs",
    "ft3/sec": "cfs",
    "ft^3/s": "cfs",
    "g/cm3": "gm/cm3",
    "gallon": "gal",
    "gallons per minute": "gpm",
    "gallons": "gal",
    "gm": "g",
    "gm/l": "g/l",
    "gm/m3": "g/m3",
    "grams per liter": "g/l",
    "grams/liter": "g/l",
    "hectare": "ha",
    "hectares": "ha",
    "hour": "hr",
    "hours": "hr",
    "hz": "Hz",
    "in/deg-d": "in/deg-day",
    "inch": "in",
    "inches": "in",
    "joule": "J",
    "joules": "J",
    "jtu": "JTU",
    "k": "K",
    "kN/m2": "kPa",
    "kcfs-day": "kdsf",
    "kelvin": "K",
    "kelvins": "K",
    "khz": "kHz",
    "kilometer": "km",
    "kilometers": "km",
    "knots": "knot",
    "ksecond-foot-day": "kdsf",
    "ksfd": "kdsf",
    "kt": "knot",
    "lb/ft3": "lbm/ft3",
    "lbf": "lb",
    "lbs": "lb",
    "lbs/ft3": "lbm/ft3",
    "lbs/sqin": "psi",
    "m3/s": "cms",
    "m3/sec": "cms",
    "mHz": "MHz",
    "mbar": "mb",
    "mbars": "mb",
    "megajoule": "MJ",
    "megajoules": "MJ",
    "meter": "m",
    "meters per second": "m/s",
    "meters": "m",
    "metre": "m",
    "metres": "m",
    "mg/L": "mg/l",
    "mhz": "MHz",
    "mi2": "mile2",
    "micrograms": "ug",
    "micrograms/L": "ug/l",
    "micrograms/l": "ug/l",
    "mile": "mi",
    "miles per hour": "mph",
    "miles": "mi",
    "millgrams/liter": "mg/l",
    "millibar": "mb",
    "millibars": "mb",
    "milligrams per liter": "mg/l",
    "millimeter": "mm",
    "millimeters": "mm",
    "million gallon": "mgal",
    "million gallons/day": "mgd",
    "millon gallons": "mgal",
    "minute": "min",
    "minutes": "min",
    "mm/deg-d": "mm/deg-day",
    "mps": "m/s",
    "newton": "N",
    "newtons": "N",
    "ntu": "NTU",
    "percent": "%",
    "pounds": "lb",
    "rev/min": "rpm",
    "revolutions per minute": "rpm",
    "second": "sec",
    "second-foot-day": "dsf",
    "seconds": "sec",
    "sfd": "dsf",
    "sq ft": "ft2",
    "sq km": "km2",
    "sq m": "m2",
    "sq meter": "m2",
    "sq meters": "m2",
    "sq mi": "mile2",
    "sq mile": "mile2",
    "sq miles": "mile2",
    "sq.km": "km2",
    "sqkm": "km2",
    "square feet": "ft2",
    "square meters": "m2",
    "square miles": "mile2",
    "survey feet": "ftUS",
    "survey foot": "ftUS",
    "tgal": "kgal",
    "umhos/cm": "umho/cm",
    "volts": "volt",
}

# -------------------------------------------- #
# Unit names for each Pint unit representation #
# -------------------------------------------- #
unit_names_by_pint_repr = {}
for unit_name in pint_units_by_unit_name:
    for format in (":D", ":P", ":C", ":~D", ":~P", ":~C"):
        pint_repr = (
            f"f\"{{ureg('{pint_units_by_unit_name[unit_name]}').units{format}}}\""
        )
        unit_names_by_pint_repr[eval(pint_repr)] = unit_name


def get_unit_registry() -> pint.registry.UnitRegistry:
    """
    Returns the Pint unit registry. Pint doesn't share unit information between
    registries so this registry must be used for any modification to the Pint behavior.
    See [Pint documentation](https://pint.readthedocs.io) for more details.

    Returns:
        pint.registry.UnitRegistry: the Pint unit registry currently in use
    """
    return ureg


def get_unit_context() -> pint.facets.context.objects.Context:
    """
    Returns the Pint unit registry context.
    See [Pint documentation](https://pint.readthedocs.io) for more details.

    Returns:
        pint.facets.context.objects.Context: The unit registry context
    """
    return ctx


def get_pint_unit(unit: str) -> pint.Unit:
    """
    Gets the Pint unit object for a specified unit string

    Args:
        unit (str): The specified unit. May be a unit name, unit alias, or a Pint unit string

    Raises:
        UnitException: If the specified unit is not a valid unit name, unit alias, or Pint unit string

    Returns:
        pint.Unit: The Pint unit object
    """
    try:
        unit_str = pint_units_by_unit_name[unit]
    except KeyError:
        try:
            unit_str = pint_units_by_unit_name[unit_names_by_alias[unit]]
        except KeyError:
            unit_str = unit
    try:
        obj = ureg(unit_str)
        if isinstance(obj, pint.Quantity):
            return cast(pint.Unit, obj.units)
        elif isinstance(obj, pint.Unit):
            return obj
        else:
            raise UnitException(f"Unexpected object type: type(obj).__name__")
    except UndefinedUnitError:
        raise UnitException(f"Unknown unit: {unit}")


def get_unit_name(pint_unit: Union[str, pint.Unit]) -> str:
    """
    Returns the unit name of a Pint unit (string or object)

    Args:
        pint_unit (Union[str, pint.Unit]): The Pint unit

    Raises:
        KeyError: If no unit name exists for the Pint unit

    Returns:
        str: The unit_name
    """
    return unit_names_by_pint_repr[str(pint_unit)]


def get_unit_aliases(unit: Union[str, pint.Unit]) -> list[str]:
    """
    Returns a list of aliases for the specified unit

    Args:
        unit (Union[str, pint.Unit]): A unit name, Pint Unit definition, or Pint Unit object

    Raises:
        KeyError: if the specified unit is not an existing unit name or a Pint Unit
            (definition or object) referenced by a unit_name

    Returns:
        list[str]: A list of aliases for the specified unit
    """
    if unit == "lb":
        unit_name = "lb"
    else:
        unit_name_or_alias = str(unit)
        try:
            unit_name = unit_names_by_alias[unit_name_or_alias]
        except KeyError:
            unit_name = unit_name_or_alias
        if unit_name not in pint_units_by_unit_name:
            raise KeyError(unit_name)
    return [k for k in unit_names_by_alias if unit_names_by_alias[k] == unit_name]


def get_compatible_units(unit: Union[str, pint.Unit]) -> list[str]:
    """
    Returns a list of units names that are convertable to/from the specified unit

    Args:
        unit (Union[str, pint.Unit]): The unit to get compatible units for

    Returns:
        list[str]: The list of compatible unit names
    """
    dimensionality = str(get_pint_unit(str(unit)).dimensionality)
    compatible = [
        u
        for u in pint_units_by_unit_name
        if str(get_pint_unit(u).dimensionality) == dimensionality
    ]
    return compatible


def convert_units(
    to_convert: Any, from_unit: Union[pint.Unit, str], to_unit: Union[pint.Unit, str]
) -> Any:
    """
    Converts an object from one unit to another. If the object is non-convertable
    it is returned unchanged.

    Args:
        to_convert (Any): The object to convert. May be:
            * integer
            * float
            * string
            * Pint Quantity
            * list
            * tuple
        from_unit (Union[pint.Unit, str]): The unit to convert from. May be:
            * a unit name
            * a unit alias
            * a valid Pint unit string
            * a Pint unit
        to_unit (Union[pint.Unit, str]): The unit to conver to. May be:
            * a unit name
            * a unit alias
            * a valid Pint unit string
            * a Pint unit

    Raises:
        UnitException: If:
            * A string is passed for one of the units that is not:
                * a unit name
                * a unit alias
                * a valid Pint unit string
            * The object to convert is (or contains) a Pint quantity whose
                unit is not the same as the `from_unit`.

    Returns:
        Any: if `to_convert` is:
        * **integer** or **float:** a *float* is returned
        * **Pint Quantity:**
            * if `from_unit` is the same as the unit of `to_convert`, a converted *Pint Quantity* is returned
            * if `from_unit` is not the same as the unit of `to_convert`, a `UnitException` is raised
        * **string:** a *string* is returned
            * if the string is numeric the returned string will be a string of the converted value
            * if the string is not numeric, it is returned unchanged
        * **list** or **tuple:**, the *same type* returned with each item either converted or not as specified
            in the rules above

        Otherwise `to_convert` is returned unchanged

    """
    src_unit = (
        from_unit if isinstance(from_unit, pint.Unit) else get_pint_unit(from_unit)
    )
    dst_unit = to_unit if isinstance(to_unit, pint.Unit) else get_pint_unit(to_unit)
    if isinstance(to_convert, (int, float)):
        # ------- #
        # numeric #
        # ------- #
        if src_unit == ureg("B_unit"):
            # -------------- #
            # B -> frequency #
            # -------------- #
            if dst_unit == src_unit:
                return 1
            hz = pint.Quantity(math.sqrt(to_convert * 1000), ureg.Hz)  # type: ignore
            return hz.to(dst_unit).magnitude
        elif dst_unit == ureg("B_unit"):
            # -------------- #
            # frequency -> B #
            # -------------- #
            if dst_unit == src_unit:
                return 1
            hz = pint.Quantity(to_convert, src_unit).to(ureg("Hz")).magnitude
            return hz**2 / 1000.0
        else:
            return ureg.Quantity(to_convert, src_unit).to(dst_unit, ctx).magnitude
    elif isinstance(to_convert, pint.Quantity):
        # ------------- #
        # Pint Quantity #
        # ------------- #
        if src_unit != to_convert.units:
            raise UnitException(
                f"From unit of {from_unit} differs from Quantity unit of {to_convert.units}"
            )
        if src_unit == ureg("B_unit"):
            # -------------- #
            # B -> frequency #
            # -------------- #
            if dst_unit == src_unit:
                return ureg("B_unit")
            hz = pint.Quantity(math.sqrt(to_convert.magnitude * 1000), ureg.Hz)  # type: ignore
            return hz.to(dst_unit)
        elif dst_unit == ureg("B_unit"):
            # -------------- #
            # frequency -> B #
            # -------------- #
            if dst_unit == src_unit:
                return ureg("B_unit")
            hz = pint.Quantity(to_convert.magnitude, src_unit).to(ureg("Hz")).magnitude
            return pint.Quantity(hz**2 / 1000.0, ureg.B_unit)  # type: ignore
        else:
            return to_convert.to(dst_unit, ctx)
    elif isinstance(to_convert, str):
        # ------ #
        # String #
        # ------ #
        try:
            return str(convert_units(float(to_convert), src_unit, dst_unit))
        except:
            return to_convert
    elif isinstance(to_convert, list):
        # ---- #
        # list #
        # ---- #
        converted = copy.deepcopy(to_convert)
        for i in range(len(to_convert)):
            converted[i] = convert_units(to_convert[i], from_unit, to_unit)
        return converted
    elif isinstance(to_convert, tuple):
        # ----- #
        # tuple #
        # ----- #
        return tuple(convert_units(list(to_convert), from_unit, to_unit))
    else:
        # ----- #
        # other #
        # ----- #
        return to_convert


@total_ordering
class UnitQuantity:
    """
    Class for scalar values with units.

    Thinly wraps pint.UnitRegistry.Quantity, but allows non-identifier unit names to be
    associated with quantities. Can be used with mathematical, comparison, and conversion
    operators in conjuction with pint.UnitRegistry.Quantity objects and scalars (ints and floats).

    """

    _default_output_format: Optional[str] = None

    @classmethod
    def setDefaultOutputFormat(cls, format: Optional[str]) -> None:
        """
        Sets the default output format for new UnitQuantity objects

        Args:
            format (Optional[str]): <br>
                * None: (default value) outputs the units as specified when the UnitQuantity object was created
                * Other: Must be a valid [Pint format specification](https://pint.readthedocs.io/en/stable/user/formatting.html)
        """
        cls._default_output_format = format

    def __init__(self, *args: Any):
        """
        Creates a UnitQuantity object

        Args:
            One argument:<br>
                * `str`: A valid string for [Pint string parsing](https://pint.readthedocs.io/en/stable/user/defining-quantities.html)
                * `UnitQuantity`: Another UnitQuantity object
                * `pint.Quantity`: A Pint Quantity object
            Two arguments:<br>
                * args[0] (`Union[int, float, Fraction]`): The magnitude of the quantity
                * args[1] (`Union[str, pint.Unit`): The uni of the quantity

        Raises:
            UnitException: if in valid arguments are specified
        """
        arg_count = len(args)
        if arg_count == 1:
            if isinstance(args[0], str):
                self._quantity = ureg(args[0])
                self._specified_unit = str(self._quantity.units)
            elif isinstance(args[0], UnitQuantity):
                self._quantity = args[0]._quantity
                self._specified_unit = args[0]._specified_unit
            elif isinstance(args[0], pint.Quantity):
                self._quantity = args[0]
                self._specified_unit = str(args[0].units)
            else:
                raise UnitException(
                    f"Expected type of single argument to be 'UnitQuantity', 'pint.Quantity' or 'str', got '{type(args[0])}'"
                )
        elif arg_count == 2:
            if isinstance(args[1], str):
                self._quantity = ureg.Quantity(args[0], get_pint_unit(args[1]))
            else:
                self._quantity = ureg.Quantity(args[0], args[1])
            self._specified_unit = str(args[1])
        else:
            raise UnitException(f"Expected 1..2 arguments, got {arg_count}")
        self._output_format = UnitQuantity._default_output_format

    def __repr__(self) -> str:
        return f"UnitQuantity({self._quantity.magnitude}, '{self._specified_unit}')"

    def __str__(self) -> str:
        if self._output_format:
            return cast(
                str,
                eval(
                    'f"{self._quantity:' + self.output_format
                    if self.output_format
                    else "" + '}"'
                ),
            )
        else:
            return f"{self._quantity.magnitude} {self._specified_unit}"

    def __bool__(self) -> bool:
        return True if self._quantity.magnitude else False

    def __int__(self) -> int:
        return int(self._quantity.magnitude)

    def __float__(self) -> float:
        return float(self._quantity.magnitude)

    def __format__(self, format: str) -> str:
        return cast(str, eval('f"{self._quantity:' + format + '}"'))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnitQuantity):
            return cast(bool, self._quantity == other._quantity)
        elif isinstance(other, pint.Quantity):
            return cast(bool, self._quantity == other)
        elif isinstance(other, (int, float)):
            return cast(bool, self._quantity.magnitude == other)
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, UnitQuantity):
            return cast(bool, self._quantity < other._quantity)
        elif isinstance(other, pint.Quantity):
            return cast(bool, self._quantity < other)
        elif isinstance(other, (int, float)):
            return cast(bool, self._quantity.magnitude < other)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, UnitQuantity):
            return cast(bool, self._quantity > other._quantity)
        elif isinstance(other, pint.Quantity):
            return cast(bool, self._quantity > other)
        elif isinstance(other, (int, float)):
            return cast(bool, self._quantity.magnitude > other)
        return NotImplemented

    def __add__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity + other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity + other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude + other, self._specified_unit)
        return NotImplemented

    def __sub__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity - other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity - other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude - other, self._specified_unit)
        return NotImplemented

    def __mul__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity * other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity * other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude * other, self._specified_unit)
        return NotImplemented

    def __truediv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity / other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity / other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude / other, self._specified_unit)
        return NotImplemented

    def __mod__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity % other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity % other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude % other, self._specified_unit)
        return NotImplemented

    def __floordiv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = self._quantity // other._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = self._quantity // other
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(self._quantity.magnitude // other, self._specified_unit)
        return NotImplemented

    def __pow__(self, other: object) -> "UnitQuantity":
        if isinstance(other, (int, float)):
            return UnitQuantity(
                self._quantity.magnitude**other, f"({self._specified_unit})**{other}"
            )
        return NotImplemented

    def __iadd__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity += other._quantity  # type: ignore
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity += other  # type: ignore
            return self
        elif isinstance(other, (int, float)):
            self._quantity += UnitQuantity(other, self._specified_unit)  # type: ignore
            return self
        return NotImplemented

    def __isub__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity -= other._quantity
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity -= other
            return self
        elif isinstance(other, (int, float)):
            self._quantity -= UnitQuantity(other, self._specified_unit)
            return self
        return NotImplemented

    def __imul__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity *= other._quantity
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity *= other
            return self
        elif isinstance(other, (int, float)):
            self._quantity *= UnitQuantity(other, self._specified_unit)
            return self
        return NotImplemented

    def __itruediv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity /= other._quantity
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity /= other
            return self
        elif isinstance(other, (int, float)):
            self._quantity /= UnitQuantity(other, self._specified_unit)
            return self
        return NotImplemented

    def __imod__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity %= other._quantity
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity %= other
            return self
        elif isinstance(other, (int, float)):
            self._quantity %= UnitQuantity(other, self._specified_unit)
            return self
        return NotImplemented

    def __ifloordiv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            self._quantity //= other._quantity
            return self
        elif isinstance(other, pint.Quantity):
            self._quantity //= other
            return self
        elif isinstance(other, (int, float)):
            self._quantity //= UnitQuantity(other, self._specified_unit)
            return self
        return NotImplemented

    def __ipow__(self, other: object) -> "UnitQuantity":
        if isinstance(other, (int, float)):
            self._specified_unit = f"({self._specified_unit})**{other}"
            self._quantity = UnitQuantity(self._quantity.magnitude**other, self._specified_unit)  # type: ignore
            return self
        return NotImplemented

    def __radd__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity + self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other + self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other + self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    def __rsub__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity - self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other - self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other - self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    def __rmul__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity * self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other * self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other * self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    def __rtruediv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity / self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other / self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other / self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    def __rmod__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity % self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other % self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other % self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    def __rfloordiv__(self, other: object) -> "UnitQuantity":
        if isinstance(other, UnitQuantity):
            q = other._quantity // self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, pint.Quantity):
            q = other // self._quantity
            return UnitQuantity(q.magnitude, q.units)
        elif isinstance(other, (int, float)):
            return UnitQuantity(other // self._quantity.magnitude, self._specified_unit)
        return NotImplemented

    @property
    def output_format(self) -> Optional[str]:
        """
        The output format used for this object if a format specifier is not used. Any format specifier used
        will override this property.

        If `None`, the unit name or alias specified when the object was creaed will be output (e.g., 10 dsf).
        See [Pint format specification](https://pint.readthedocs.io/en/stable/user/formatting.html) for other formats.

        Operations:
            Read/Write
        """
        return self._output_format

    @output_format.setter
    def output_format(self, format: Optional[str]) -> None:
        self._output_format = format

    @property
    def magnitude(self) -> Any:
        """
        The magnitude of the object (unitless value)

        Operations:
            Read/Only
        """
        return self._quantity.magnitude

    @property
    def units(self) -> pint.Unit:
        """
        The Pint unit of the object

        Operations:
            Read/Only
        """
        return self._quantity.units  # type: ignore

    @property
    def dimensionality(self) -> pint.util.UnitsContainer:
        """
        The dimensionality of the object

        Operations:
            Read/Only
        """
        return self._quantity.dimensionality

    @property
    def specified_units(self) -> str:
        """
        The unit specified when the object was created. May be a unit name, alias, or a pint unit definition

        Operations:
            Read/Only
        """
        return self._specified_unit

    def to(self, unit: Union[str, pint.Unit], in_place: bool = False) -> "UnitQuantity":
        """
        Converts this object to a different unit

        Args:
            unit (Union[str, pint.Unit]): The unit to convert to
            in_place (bool, optional): If True, this object is modified and returned Otherwise
                a new object is returned. Defaults to False. Using this method with `in_place=True`
                differs from `ito()` in that the converted object is returned.

        Returns:
            UnitQuantity: The converted object
        """
        if isinstance(unit, str):
            _unit_str = unit
            _unit = get_pint_unit(unit)
        else:
            _unit = unit
            _unit_str = str(_unit)
        if in_place:
            self._quantity.ito(_unit, ctx)
            self._specified_unit = _unit_str
            return self
        else:
            return UnitQuantity(self._quantity.to(_unit, ctx), _unit_str)

    def ito(self, unit: Union[str, pint.Unit]) -> None:
        """
        Converts this object to a different unit in place. Unlike `.to(..., in_place=True)`
        no object is returned after the conversion

        Args:
            unit (Union[str, pint.Unit]): The unit ot convert to
        """
        self.to(unit, in_place=True)

    def getUnitAliases(self) -> list[str]:
        """
        Returns a list of unit aliases for the specified unit of this object

        Returns:
            list[str]: The list of unit aliases for this object's specified unit
        """
        return get_unit_aliases(self._specified_unit)

    def getCompatibleUnits(self) -> list[str]:
        """
        Returns a list of compatible unit unit names for the specified unit of this object.
        Compatible units are those that have the same dimensionality.

        Returns:
            list[str]: The list of compatible unit names for this object's specified unit
        """
        return get_compatible_units(self._specified_unit)
