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
    "get_unit_system",
    "get_unit_names_for_unit_system",
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
import cwms  # type: ignore
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

# ------------------------------------------- #
# Pint units + unit system for each unit name #
# ------------------------------------------- #
unit_info_by_unit_name = {
    "%": ("%", None),
    "$": ("USD", None),
    "$/kaf": ("USD_per_kacre_foot", "EN"),
    "$/mcm": ("USD_per_Mcm", "SI"),
    "1/ft": ("1/ft", "EN"),
    "1/m": ("1/m", "SI"),
    "1000 m2": ("_1000_m2", "SI"),
    "1000 m3": ("_1000_m3", "SI"),
    "ac-ft": ("acre_foot", "EN"),
    "acre": ("acre", None),
    "ampere": ("amp", None),
    "B": ("B_unit", None),
    "bar": ("bar", None),
    "C-day": ("delta_degC*d", "SI"),
    "C": ("degC", "SI"),
    "cal": ("cal", "EN"),
    "cfs": ("ft**3/s", "EN"),
    "cfs/mi2": ("ft**3/s/mi**2", "EN"),
    "cm": ("cm", "SI"),
    "cm/day": ("cm/d", "SI"),
    "cm2": ("cm**2", "SI"),
    "cms": ("m**3/s", "SI"),
    "cms/km2": ("m**3/s/km** 2", "SI"),
    "day": ("d", None),
    "deg": ("deg", None),
    "dsf": ("ft**3/s*d", "EN"),
    "F-day": ("delta_degF*d", "EN"),
    "F": ("degF", "EN"),
    "FNU": ("FNU", None),
    "ft": ("ft", "EN"),
    "ft/hr": ("ft/h", "EN"),
    "ft/s": ("ft/s", "EN"),
    "ft2": ("ft**2", "EN"),
    "ft2/s": ("ft**2/s", "EN"),
    "ft3": ("ft**3", "EN"),
    "ftUS": ("US_survey_foot", "EN"),
    "g": ("g", "SI"),
    "g/l": ("g/l", "SI"),
    "g/m3": ("g/m**3", "SI"),
    "gal": ("gal", "EN"),
    "gm/cm3": ("g/cm**3", None),
    "gpm": ("gal/min", "EN"),
    "GW": ("GW", None),
    "GWh": ("GWh", None),
    "ha": ("ha", "SI"),
    "hr": ("h", None),
    "Hz": ("Hz", None),
    "in-hg": ("inHg", "EN"),
    "in": ("in", "EN"),
    "in/day": ("in/d", "EN"),
    "in/deg-day": ("in/(delta_degF*d)", "EN"),
    "in/hr": ("in/hr", "EN"),
    "J": ("J", "SI"),
    "J/m2": ("J/m**2", "SI"),
    "JTU": ("JTU", None),
    "K": ("K", "SI"),
    "k$": ("kUSD", None),
    "kaf": ("kacre_foot", "EN"),
    "KAF/mon": ("kacre_foot/month", "EN"),
    "kcfs": ("kcfs", "EN"),
    "kcms": ("kcms", "SI"),
    "kdsf": ("kdsf", "EN"),
    "kg": ("kg", "SI"),
    "kgal": ("kgal", "EN"),
    "kHz": ("kHz", None),
    "km": ("km", "SI"),
    "km2": ("km**2", "SI"),
    "km3": ("km**3", "SI"),
    "knot": ("knot", "EN"),
    "kPa": ("kPa", "SI"),
    "kph": ("kph", "SI"),
    "kW": ("kW", None),
    "kWh": ("kWh", None),
    "langley": ("langley", None),
    "langley/min": ("langley/min", None),
    "lb": ("lbf", "EN"),
    "lbm": ("lb", "EN"),
    "lbm/ft3": ("lb/ft**3", "EN"),
    "m": ("m", "SI"),
    "m/day": ("m/d", "SI"),
    "m/hr": ("m/h", "SI"),
    "m/s": ("mps", "SI"),
    "m2": ("m**2", "SI"),
    "m2/s": ("m**2/s", "SI"),
    "m3": ("m**3", "SI"),
    "mb": ("mbar", "SI"),
    "mcm": ("Mcm", "SI"),
    "mcm/mon": ("Mcm/month", "SI"),
    "mg": ("mg", "SI"),
    "mg/l": ("mg/l", "SI"),
    "mgal": ("Mgal", "EN"),
    "mgd": ("Mgal/d", "EN"),
    "mho": ("S", None),
    "MHz": ("MHz", None),
    "mi": ("mi", "EN"),
    "mile2": ("mi**2", "EN"),
    "mile3": ("mi**3", "EN"),
    "min": ("min", None),
    "MJ": ("MJ", "SI"),
    "mm-hg": ("mmHg", "SI"),
    "mm": ("mm", "SI"),
    "mm/day": ("mm/d", "SI"),
    "mm/deg-day": ("mm/(delta_degC*d)", "SI"),
    "mm/hr": ("mm/h", "SI"),
    "mph": ("mph", "EN"),
    "MW": ("MW", None),
    "MWh": ("MWh", None),
    "N": ("N", "SI"),
    "n/a": ("n_a", None),
    "NTU": ("NTU", None),
    "ppm": ("mg/l", None),
    "psi": ("psi", "EN"),
    "rad": ("rad", None),
    "rev": ("rev", None),
    "rpm": ("rpm", None),
    "S": ("S", None),
    "sec": ("s", None),
    "su": ("_pH", None),
    "ton": ("ton", "EN"),
    "ton/day": ("ton/d", "EN"),
    "tonne": ("tonne", "SI"),
    "tonne/day": ("tonne/d", "SI"),
    "TW": ("TW", None),
    "TWh": ("TWh", None),
    "ug": ("ug", "SI"),
    "ug/l": ("ug/l", "SI"),
    "umho": ("uS", None),
    "umho/cm": ("uS/cm", None),
    "unit": ("unit", None),
    "uS": ("uS", None),
    "volt": ("V", None),
    "W": ("W", None),
    "W/m2": ("W/m**2", None),
    "Wh": ("Wh", None),
}

# ----------------------------- #
# Pint units for each unit name #
# ----------------------------- #
pint_units_by_unit_name = {k: v[0] for k, v in unit_info_by_unit_name.items()}

# ------------------------------ #
# unit system for each unit name #
# ------------------------------ #
unit_system_by_unit_name = {k: v[1] for k, v in unit_info_by_unit_name.items()}
# ------------------------------- #

# ------------------------------- #
# unit names for each unit system #
# ------------------------------- #
unit_names_by_unit_system = {
    "EN": [u for u in unit_system_by_unit_name if unit_system_by_unit_name[u] != "SI"],
    "SI": [u for u in unit_system_by_unit_name if unit_system_by_unit_name[u] != "EN"],
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


def get_unit_name(name_alias_or_unit: Union[str, pint.Unit]) -> str:
    """
    Returns the unit name of unit name, unit alias, or Pint unit (string or object)

    Args:
        name_alias_or_unit (Union[str, pint.Unit]): A unit name, unit alias or a Pint unit

    Raises:
        KeyError: If no unit name exists for the unit alias or Pint unit

    Returns:
        str: The unit_name
    """
    unit_str = str(name_alias_or_unit)
    if unit_str in pint_units_by_unit_name:
        return unit_str
    try:
        return unit_names_by_pint_repr[unit_str]
    except KeyError:
        return unit_names_by_alias[unit_str]


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


def get_unit_system(unit: str) -> Optional[str]:
    """
    Returns the unit system of a unit name or unit alias

    Args:
        unit (str): A unit name or unit alias

    Raises:
        KeyError: if the specified unit is not an existing unit name or a Pint Unit
            (definition or object) referenced by a unit_name

    Returns:
        Optional[str]: "EN" if English, "SI" if Système International, or None if both
    """
    unit_name_or_alias = str(unit)
    try:
        unit_name = unit_names_by_alias[unit_name_or_alias]
    except KeyError:
        unit_name = unit_name_or_alias
    if unit_name not in pint_units_by_unit_name:
        raise KeyError(unit_name)
    return unit_system_by_unit_name[unit_name]


def get_unit_names_for_unit_system(unit_system: Optional[str]) -> list[str]:
    """
    Returns a list of unit names for the specified unit system

    Args:
        unit_system (Optional[str]): "EN", "SI", or None

    Raises:
        KeyError: if the specified unit system is not "EN", "SI", or None

    Returns:
        list[str]: A list of English unit names, Système International unit names,
            or unit names used by both (if `unit_system` is None)
    """
    if unit_system is None:
        return [
            u for u in unit_system_by_unit_name if unit_system_by_unit_name[u] is None
        ]
    else:
        return unit_names_by_unit_system[unit_system.upper()]


def convert_units(
    to_convert: Any,
    from_unit: Union[pint.Unit, str],
    to_unit: Union[pint.Unit, str],
    in_place: bool = False,
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
            * cwms.types.Data
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
        in_place (bool): for list and cwms.type.Data types, specifies whether to convert the object
            in-place. Ignored for all other data types. If True, the converted object is returned.
            If False, a converted copy is returned. Defaults to False

    Raises:
        UnitException: If:
            * A string is passed for one of the units that is not:
                * a unit name
                * a unit alias
                * a valid Pint unit string
            * The object to convert is Pint quantity or cwms.types.Data object whose
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
        * **list:**, a *list* returned with each item either converted or not as specified
            in the rules above. If `in_place` == `True`, the return value can be ignored if desired.
        * **tuple:**, a *tuple* returned with each item either converted or not as specified
            in the rules above. If in_place == True, the return value can be ignored if desired.
        * **cwms.type.Data:**, a *cwms.type.Data* object is returned. If `in_place` == `True`, the return
            value can be ignored if desired.

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
        converted = to_convert if in_place else copy.deepcopy(to_convert)
        for i in range(len(to_convert)):
            converted[i] = convert_units(to_convert[i], from_unit, to_unit, in_place)
        return converted
    elif isinstance(to_convert, tuple):
        # ----- #
        # tuple #
        # ----- #
        return tuple(convert_units(list(to_convert), from_unit, to_unit))
    elif isinstance(to_convert, cwms.types.Data):
        data_unit = get_pint_unit(to_convert.json["units"])
        if src_unit != data_unit:
            raise UnitException(
                f"From unit of {from_unit} differs from data unit of {to_convert.json['units']}"
            )
        factor: float = convert_units(1, src_unit, dst_unit)
        converted = to_convert if in_place else copy.deepcopy(to_convert)
        json = converted.json  # type: ignore
        if convert_units(10, src_unit, dst_unit) == 10 * factor:
            json["values"] = [[v[0], v[1] * factor, v[2]] for v in json["values"]]
        else:
            json["values"] = [
                [v[0], convert_units(v[1], src_unit, dst_unit), v[2]]
                for v in json["values"]
            ]
        json["units"] = to_unit
        try:
            vdi = json["vertical-datum-info"]
        except KeyError:
            pass
        else:
            vdi["elevation"] = convert_units(vdi["elevation"], src_unit, dst_unit)
            for i in range(len(vdi["offsets"])):
                vdi["offsets"][i]["value"] = convert_units(
                    vdi["offsets"][i]["value"], src_unit, dst_unit
                )
            vdi["unit"] = to_unit

        converted.json = json  # type: ignore
        converted._df = None  # type: ignore
        return converted

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

    def __neg__(self) -> "UnitQuantity":
        return UnitQuantity(-self._quantity.magnitude, self._specified_unit)

    def __round__(self, ndigits) -> "UnitQuantity":
        return UnitQuantity(
            round(self._quantity.magnitude, ndigits), self._specified_unit
        )

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
    def specified_unit(self) -> str:
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
