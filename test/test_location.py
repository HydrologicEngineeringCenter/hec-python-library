"""Module for testing hec.location module
"""

import os
import sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

import pytest

from hec.location import Location


def test_without_name() -> None:
    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        loc = Location()  # type: ignore


def test_name_only() -> None:
    loc = Location("A_Base_Name-A_Sub_Name-With-Hyphens")
    assert loc.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc.basename == "A_Base_Name"
    assert loc.subname == "A_Sub_Name-With-Hyphens"
    assert loc.office is None
    assert loc.latitude is None
    assert loc.longitude is None
    assert loc.elevation is None
    assert loc.elevation_unit is None
    assert loc.horizontal_datum is None
    assert loc.vertical_datum is None


def test_all_args_positional() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        408,
        "ft",
        "NAD83",
        "NGVD29",
    )
    assert loc.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc.basename == "A_Base_Name"
    assert loc.subname == "A_Sub_Name-With-Hyphens"
    assert loc.office == "SWT"
    assert loc.latitude == 35.4844444
    assert loc.longitude == -94.3927778
    assert loc.elevation == 408
    assert loc.elevation_unit == "ft"
    assert loc.horizontal_datum == "NAD83"
    assert loc.vertical_datum == "NGVD29"


def test_all_args_keyword() -> None:
    loc = Location(
        elevation=408,
        elevation_unit="ft",
        horizontal_datum="NAD83",
        latitude=35.4844444,
        longitude=-94.3927778,
        name="A_Base_Name-A_Sub_Name-With-Hyphens",
        office="SWT",
        vertical_datum="NGVD29",
    )
    assert loc.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc.basename == "A_Base_Name"
    assert loc.subname == "A_Sub_Name-With-Hyphens"
    assert loc.office == "SWT"
    assert loc.latitude == 35.4844444
    assert loc.longitude == -94.3927778
    assert loc.elevation == 408
    assert loc.elevation_unit == "ft"
    assert loc.horizontal_datum == "NAD83"
    assert loc.vertical_datum == "NGVD29"


def test_attributes() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        408,
        "ft",
        "NAD83",
        "NGVD29",
    )
    loc.name = "A New Name"
    assert loc.name == "A New Name"
    with pytest.raises(AttributeError, match="can't set attribute"):
        loc.basename = "Bad Try 1"  # type: ignore
    with pytest.raises(AttributeError, match="can't set attribute"):
        loc.subname = "Bad Try 2"  # type: ignore
    loc.office = "SWL"
    assert loc.office == "SWL"
    loc.latitude = 35.0
    assert loc.latitude == 35.0
    loc.longitude = -95.0
    assert loc.longitude == -95.0
    loc.elevation = 100
    assert loc.elevation == 100
    loc.elevation_unit = "m"
    assert loc.elevation_unit == "m"
    loc.horizontal_datum = "WGS84"
    assert loc.horizontal_datum == "WGS84"
    loc.vertical_datum = "NAVD88"
    assert loc.vertical_datum == "NAVD88"


def test_repr() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        408,
        "ft",
        "NAD83",
        "NGVD29",
    )
    assert str(loc) == "SWT/A_Base_Name-A_Sub_Name-With-Hyphens"
    loc2 = eval(repr(loc))
    assert loc2.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc2.basename == "A_Base_Name"
    assert loc2.subname == "A_Sub_Name-With-Hyphens"
    assert loc2.office == "SWT"
    assert loc2.latitude == 35.4844444
    assert loc2.longitude == -94.3927778
    assert loc2.elevation == 408
    assert loc2.elevation_unit == "ft"
    assert loc2.horizontal_datum == "NAD83"
    assert loc2.vertical_datum == "NGVD29"
    loc2.name = "A New Name"
    loc2.office = "SWL"
    loc2.latitude = None
    loc2.longitude = None
    loc2.horizontal_datum = None
    assert str(loc2) == "SWL/A New Name"
    assert (
        repr(loc2)
        == "Location(name='A New Name',office='SWL',elevation=408.0,elevation_unit='ft',vertical_datum='NGVD29')"
    )
