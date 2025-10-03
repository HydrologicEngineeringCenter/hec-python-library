"""Module for testing hec.location module"""

import pytest

import hec
from hec import Location, LocationException
from hec import UnitQuantity as UQ


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
    assert loc.horizontal_datum is None
    assert loc.elevation is None
    assert loc.vertical_datum is None
    assert loc.kind is None
    assert loc.time_zone is None


def test_all_args_positional() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
    )
    assert loc.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc.basename == "A_Base_Name"
    assert loc.subname == "A_Sub_Name-With-Hyphens"
    assert loc.office == "SWT"
    assert loc.latitude == 35.4844444
    assert loc.longitude == -94.3927778
    assert loc.elevation == UQ(408, "ft")
    assert loc.horizontal_datum == "NAD83"
    assert loc.vertical_datum == "NGVD-29"
    assert loc.time_zone == "Etc/GMT+7"
    assert loc.kind == "OUTLET"


def test_all_args_keyword() -> None:
    loc = Location(
        kind="project",
        time_zone="Z",
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
    assert loc.horizontal_datum == "NAD83"
    assert loc.elevation == UQ(408, "ft")
    assert loc.vertical_datum == "NGVD-29"
    assert loc.time_zone == "UTC"
    assert loc.kind == "PROJECT"


def test_attributes() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
    )
    loc.name = "A New Name"
    assert loc.name == "A New Name"
    with pytest.raises(AttributeError):
        loc.basename = "Bad Try 1"  # type: ignore
    with pytest.raises(AttributeError):
        loc.subname = "Bad Try 2"  # type: ignore
    loc.office = "SWL"
    assert loc.office == "SWL"
    loc.latitude = 35.0
    assert loc.latitude == 35.0
    loc.longitude = -95.0
    assert loc.longitude == -95.0
    loc.horizontal_datum = "WGS84"
    assert loc.horizontal_datum == "WGS84"
    loc.elevation = UQ(100, "m")
    assert loc.elevation == UQ(100, "m")
    loc.vertical_datum = "NAVD88"
    assert loc.vertical_datum == "NAVD-88"
    loc.time_zone = "US/Pacific"
    assert loc.time_zone == "US/Pacific"
    loc.kind = "basin"
    assert loc.kind == "BASIN"


def test_repr() -> None:
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
    )
    assert str(loc) == "SWT/A_Base_Name-A_Sub_Name-With-Hyphens"
    loc2: Location = eval(repr(loc))
    assert loc2.name == "A_Base_Name-A_Sub_Name-With-Hyphens"
    assert loc2.basename == "A_Base_Name"
    assert loc2.subname == "A_Sub_Name-With-Hyphens"
    assert loc2.office == "SWT"
    assert loc2.latitude == 35.4844444
    assert loc2.longitude == -94.3927778
    assert loc2.elevation == UQ(408, "ft")
    assert loc2.horizontal_datum == "NAD83"
    assert loc2.vertical_datum == "NGVD-29"
    assert loc2.time_zone == "Etc/GMT+7"
    assert loc2.kind == "OUTLET"
    loc2.name = "A New Name"
    loc2.office = "SWL"
    loc2.latitude = None
    loc2.longitude = None
    loc2.horizontal_datum = None
    assert str(loc2) == "SWL/A New Name"
    assert (
        repr(loc2)
        == "hec.Location(name='A New Name',office='SWL',elevation=408.0,elevation_unit='ft',vertical_datum='NGVD-29',time_zone='Etc/GMT+7',kind='OUTLET')"
    )


def test_bad_time_zone() -> None:
    with pytest.raises(LocationException, match="Invalid time zone: -07:30"):
        loc = Location(
            "A_Base_Name-A_Sub_Name-With-Hyphens",
            "SWT",
            35.4844444,
            -94.3927778,
            "NAD83",
            408,
            "ft",
            "NGVD29",
            "-07:30",
            "outlet",
        )
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
    )
    with pytest.raises(LocationException, match="Invalid time zone: -07:30"):
        loc.time_zone = "-07:30"


def test_bad_kind() -> None:
    with pytest.raises(LocationException, match="Invalid kind: STREAM_GAUGE"):
        loc = Location(
            "A_Base_Name-A_Sub_Name-With-Hyphens",
            "SWT",
            35.4844444,
            -94.3927778,
            "NAD83",
            408,
            "ft",
            "NGVD29",
            "-07:00",
            "stream_gauge",
        )
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
    )
    with pytest.raises(LocationException, match="Invalid kind: STREAM_GAUGE"):
        loc.kind = "stream_gauge"


def test_vertical_datum_info() -> None:
    xml = """<vertical-datum-info office="SWT" unit="ft">
  <location>A_Base_Name-A_Sub_Name-With-Hyphens</location>
  <native-datum>OTHER</native-datum>
  <local-datum-name>Pensacola</local-datum-name>
  <elevation>615.23</elevation>
  <offset estimate="false">
    <to-datum>NGVD-29</to-datum>
    <value>1.07</value>
  </offset>
  <offset estimate="true">
    <to-datum>NAVD-88</to-datum>
    <value>1.3625</value>
  </offset>
</vertical-datum-info>"""
    json = (
        '{"office":"SWT","location":"A_Base_Name-A_Sub_Name-With-Hyphens","elevation":615.23,"unit":"ft","native-datum":"Pensacola",'
        '"offsets":[{"to-datum":"NAVD-88","value":1.3625,"estimate":"true"},{"to-datum":"NGVD-29","value":1.07,"estimate":false}]}'
    )
    loc = Location(
        "A_Base_Name-A_Sub_Name-With-Hyphens",
        "SWT",
        35.4844444,
        -94.3927778,
        "NAD83",
        408,
        "ft",
        "NGVD29",
        "-07:00",
        "outlet",
        xml,
    )
    assert loc.elevation == UQ(615.23, "ft")
    assert loc.vertical_datum == "Pensacola"
    assert loc.vertical_datum_xml == xml
    assert loc.vertical_datum_json == json
    loc2: Location = eval(repr(loc))
    print(repr(loc))
    print(repr(loc2))
    assert loc2.elevation == UQ(615.23, "ft")
    assert loc2.vertical_datum == "Pensacola"
    assert loc2.vertical_datum_xml == xml
    assert loc2.vertical_datum_json == json
