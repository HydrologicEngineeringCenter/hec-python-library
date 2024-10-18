"""
Module for testing hec.parameter module
"""

import pytest

from hec.parameter import (
    ElevParameter,
    Parameter,
    ParameterException,
    ParameterType,
    ParameterTypeException,
)
from hec.unit import UnitQuantity as UQ


def test_parameter() -> None:
    p = Parameter("FLOW-IN", "KCFS")
    assert repr(p) == "Parameter('FLOW-IN', 'kcfs')"
    assert str(p) == "FLOW-IN (kcfs)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit_name == "kcfs"

    assert p.get_compatible_units() == [
        "cfs",
        "cms",
        "gpm",
        "KAF/mon",
        "kcfs",
        "kcms",
        "mcm/mon",
        "mgd",
    ]

    assert repr(p.to("mgd")) == "Parameter('FLOW-IN', 'mgd')"
    assert str(p.to("mgd")) == "FLOW-IN (mgd)"

    assert repr(p.to("EN")) == "Parameter('FLOW-IN', 'cfs')"
    assert str(p.to("EN")) == "FLOW-IN (cfs)"

    assert repr(p.to("SI")) == "Parameter('FLOW-IN', 'cms')"
    assert str(p.to("SI")) == "FLOW-IN (cms)"

    with pytest.raises(ParameterException) as excinfo:
        p.to("ac-ft")
    assert str(excinfo.value).startswith(
        "ac-ft is not a vaild unit for base parameter Flow"
    )

    assert repr(p) == "Parameter('FLOW-IN', 'kcfs')"
    assert str(p) == "FLOW-IN (kcfs)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit_name == "kcfs"

    p.to("SI", in_place=True)
    assert repr(p) == "Parameter('FLOW-IN', 'cms')"
    assert str(p) == "FLOW-IN (cms)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit_name == "cms"


def test_elev_parameter_with_xml() -> None:
    # ".0" on elevation and order of offsets matter for comparison at end of function
    xml = """
          <vertical-datum-info unit="ft">
          <native-datum>OTHER</native-datum>
          <local-datum-name>Pensacola</local-datum-name>
          <elevation>757.0</elevation>
          <offset estimate="false">
              <to-datum>NGVD-29</to-datum>
              <value>1.07</value>
          </offset>
          <offset estimate="true">
              <to-datum>NAVD-88</to-datum>
              <value>1.457</value>
          </offset>
          </vertical-datum-info>
          """
    p = ElevParameter("Elev", xml)
    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p.name == "Elev"
    assert p.basename == "Elev"
    assert p.subname is None
    assert p.base_parameter == "Elev"
    assert p.unit_name == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.ngvd29_offset == UQ(1.07, "ft")
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft")
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p2 = p.to("NAVD88")
    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p2.name == "Elev"
    assert p2.basename == "Elev"
    assert p2.subname is None
    assert p2.base_parameter == "Elev"
    assert p2.unit_name == "ft"
    assert p2.elevation == UQ(757, "ft") + p.get_offset_to("navd-88")
    assert p2.native_datum == "Pensacola"
    assert p2.current_datum == "NAVD-88"
    assert p2.ngvd29_offset == UQ(1.07, "ft")
    assert p2.ngvd29_offset_is_estimate == False
    assert p2.navd88_offset == UQ(1.457, "ft")
    assert p2.navd88_offset_is_estimate == True
    assert p2.get_offset_to("ngvd-29") == UQ(-0.387, "ft")
    assert p2.get_offset_to("navd-88") is None

    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p.name == "Elev"
    assert p.basename == "Elev"
    assert p.subname is None
    assert p.base_parameter == "Elev"
    assert p.unit_name == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.ngvd29_offset == UQ(1.07, "ft")
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft")
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p.to("m", in_place=True)
    assert p.unit_name == "m"
    assert p.elevation == UQ(757 * 0.3048, "m").round(9)
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.elevation == UQ(757 * 0.3048, "m").round(9)
    assert p.ngvd29_offset == UQ(1.07 * 0.3048, "m").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457 * 0.3048, "m").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07 * 0.3048, "m").round(9)
    assert p.get_offset_to("navd-88") == UQ(1.457 * 0.3048, "m").round(9)

    p.to("NAVD88", in_place=True)
    assert p.unit_name == "m"
    assert p.current_datum == "NAVD-88"
    assert p.elevation == UQ(758.457 * 0.3048, "m").round(9)
    assert p.ngvd29_offset == UQ(1.07 * 0.3048, "m").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457 * 0.3048, "m").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(-0.387 * 0.3048, "m").round(9)
    assert p.get_offset_to("navd-88") is None

    p.to("ft", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "NAVD-88"
    assert p.elevation == UQ(758.457, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(-0.387, "ft").round(9)
    assert p.get_offset_to("navd-88") is None

    p.to("ngvd-29", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "NGVD-29"
    assert p.elevation == UQ(758.07, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") is None
    assert p.get_offset_to("navd-88") == UQ(0.387, "ft").round(9)

    p.to("local", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "Pensacola"
    assert p.elevation == UQ(757, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft").round(9)
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft").round(9)

    with pytest.raises(ParameterException) as excinfo:
        p.to("Bad-Datum")
    assert str(excinfo.value) == (
        "Invalid unit for base parameter Elev or or invalid vertical datum: Bad-Datum"
    )

    assert "".join(p.vertical_datum_info_xml.split()) == "".join(xml.split())


def test_elev_parameter_with_dict() -> None:
    # order of offsets matters for comparison at end of function
    props = {
        "office": "SWT",
        "unit": "ft",
        "location": "PENS",
        "native-datum": "OTHER",
        "elevation": 757,
        "offsets": [
            {"estimate": False, "to-datum": "NGVD-29", "value": 1.07},
            {"estimate": True, "to-datum": "NAVD-88", "value": 1.457},
        ],
    }
    p = ElevParameter("Elev", props)
    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p.name == "Elev"
    assert p.basename == "Elev"
    assert p.subname is None
    assert p.base_parameter == "Elev"
    assert p.unit_name == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "OTHER"
    assert p.current_datum == "OTHER"
    assert p.ngvd29_offset == UQ(1.07, "ft")
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft")
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p2 = p.to("NAVD88")
    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p2.name == "Elev"
    assert p2.basename == "Elev"
    assert p2.subname is None
    assert p2.base_parameter == "Elev"
    assert p2.unit_name == "ft"
    assert p2.elevation == UQ(757, "ft") + p.get_offset_to("navd-88")
    assert p2.native_datum == "OTHER"
    assert p2.current_datum == "NAVD-88"
    assert p2.ngvd29_offset == UQ(1.07, "ft")
    assert p2.ngvd29_offset_is_estimate == False
    assert p2.navd88_offset == UQ(1.457, "ft")
    assert p2.navd88_offset_is_estimate == True
    assert p2.get_offset_to("ngvd-29") == UQ(-0.387, "ft")
    assert p2.get_offset_to("navd-88") is None

    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p.name == "Elev"
    assert p.basename == "Elev"
    assert p.subname is None
    assert p.base_parameter == "Elev"
    assert p.unit_name == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "OTHER"
    assert p.current_datum == "OTHER"
    assert p.ngvd29_offset == UQ(1.07, "ft")
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft")
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p.to("m", in_place=True)
    assert p.unit_name == "m"
    assert p.elevation == UQ(757 * 0.3048, "m").round(9)
    assert p.native_datum == "OTHER"
    assert p.current_datum == "OTHER"
    assert p.elevation == UQ(757 * 0.3048, "m").round(9)
    assert p.ngvd29_offset == UQ(1.07 * 0.3048, "m").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457 * 0.3048, "m").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07 * 0.3048, "m").round(9)
    assert p.get_offset_to("navd-88") == UQ(1.457 * 0.3048, "m").round(9)

    p.to("NAVD88", in_place=True)
    assert p.unit_name == "m"
    assert p.current_datum == "NAVD-88"
    assert p.elevation == UQ(758.457 * 0.3048, "m").round(9)
    assert p.ngvd29_offset == UQ(1.07 * 0.3048, "m").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457 * 0.3048, "m").round(9)
    assert p.get_offset_to("ngvd-29") == UQ(-0.387 * 0.3048, "m").round(9)
    assert p.get_offset_to("navd-88") is None

    p.to("ft", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "NAVD-88"
    assert p.elevation == UQ(758.457, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(-0.387, "ft").round(9)
    assert p.get_offset_to("navd-88") is None

    p.to("ngvd-29", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "NGVD-29"
    assert p.elevation == UQ(758.07, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset.specified_unit == "ft"
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") is None
    assert p.get_offset_to("navd-88") == UQ(0.387, "ft").round(9)

    p.to("local", in_place=True)
    assert p.unit_name == "ft"
    assert p.current_datum == "OTHER"
    assert p.elevation == UQ(757, "ft").round(9)
    assert p.ngvd29_offset == UQ(1.07, "ft").round(9)
    assert p.ngvd29_offset_is_estimate == False
    assert p.navd88_offset == UQ(1.457, "ft").round(9)
    assert p.navd88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft").round(9)
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft").round(9)

    with pytest.raises(ParameterException) as excinfo:
        p.to("Bad-Datum")
    assert str(excinfo.value) == (
        "Invalid unit for base parameter Elev or or invalid vertical datum: Bad-Datum"
    )

    del props["office"]
    del props["location"]
    assert p.vertical_datum_info_dict == props


def test_parameter_type_raw() -> None:
    ParameterType.setDefaultContext("RAW")
    ptype = ParameterType("total")
    assert ptype.name == "Total"
    assert ptype.getRawName() == "Total"
    assert ptype.getCwmsName() == "Total"
    assert ptype.getDssName() == "PER-CUM"
    ptype = ParameterType("maximum")
    assert ptype.name == "Maximum"
    assert ptype.getRawName() == "Maximum"
    assert ptype.getCwmsName() == "Max"
    assert ptype.getDssName() == "PER-MAX"
    ptype = ParameterType("minimum")
    assert ptype.name == "Minimum"
    assert ptype.getRawName() == "Minimum"
    assert ptype.getCwmsName() == "Min"
    assert ptype.getDssName() == "PER-MIN"
    ptype = ParameterType("constant")
    assert ptype.name == "Constant"
    assert ptype.getRawName() == "Constant"
    assert ptype.getCwmsName() == "Const"
    assert ptype.getDssName() == "CONST"
    ptype = ParameterType("average")
    assert ptype.name == "Average"
    assert ptype.getRawName() == "Average"
    assert ptype.getCwmsName() == "Ave"
    assert ptype.getDssName() == "PER-AVER"
    ptype = ParameterType("instantaneous")
    assert ptype.name == "Instantaneous"
    assert ptype.getRawName() == "Instantaneous"
    assert ptype.getCwmsName() == "Inst"
    assert ptype.getDssName() == "INST-VAL"
    assert ptype.getDssName(True) == "INST-CUM"


def test_parameter_type_cwms() -> None:
    ParameterType.setDefaultContext("CWMS")
    ptype = ParameterType("total")
    assert ptype.name == "Total"
    assert ptype.getRawName() == "Total"
    assert ptype.getCwmsName() == "Total"
    assert ptype.getDssName() == "PER-CUM"
    ptype = ParameterType("max")
    assert ptype.name == "Max"
    assert ptype.getRawName() == "Maximum"
    assert ptype.getCwmsName() == "Max"
    assert ptype.getDssName() == "PER-MAX"
    ptype = ParameterType("min")
    assert ptype.name == "Min"
    assert ptype.getRawName() == "Minimum"
    assert ptype.getCwmsName() == "Min"
    assert ptype.getDssName() == "PER-MIN"
    ptype = ParameterType("const")
    assert ptype.name == "Const"
    assert ptype.getRawName() == "Constant"
    assert ptype.getCwmsName() == "Const"
    assert ptype.getDssName() == "CONST"
    ptype = ParameterType("ave")
    assert ptype.name == "Ave"
    assert ptype.getRawName() == "Average"
    assert ptype.getCwmsName() == "Ave"
    assert ptype.getDssName() == "PER-AVER"
    ptype = ParameterType("inst")
    assert ptype.name == "Inst"
    assert ptype.getRawName() == "Instantaneous"
    assert ptype.getCwmsName() == "Inst"
    assert ptype.getDssName() == "INST-VAL"
    assert ptype.getDssName(True) == "INST-CUM"


def test_parameter_type_dss() -> None:
    ParameterType.setDefaultContext("DSS")
    ptype = ParameterType("PER-CUM")
    assert ptype.name == "PER-CUM"
    assert ptype.getRawName() == "Total"
    assert ptype.getCwmsName() == "Total"
    assert ptype.getDssName() == "PER-CUM"
    ptype = ParameterType("PER-MAX")
    assert ptype.name == "PER-MAX"
    assert ptype.getRawName() == "Maximum"
    assert ptype.getCwmsName() == "Max"
    assert ptype.getDssName() == "PER-MAX"
    ptype = ParameterType("PER-MIN")
    assert ptype.name == "PER-MIN"
    assert ptype.getRawName() == "Minimum"
    assert ptype.getCwmsName() == "Min"
    assert ptype.getDssName() == "PER-MIN"
    ptype = ParameterType("CONST")
    assert ptype.name == "CONST"
    assert ptype.getRawName() == "Constant"
    assert ptype.getCwmsName() == "Const"
    assert ptype.getDssName() == "CONST"
    ptype = ParameterType("PER-AVER")
    assert ptype.name == "PER-AVER"
    assert ptype.getRawName() == "Average"
    assert ptype.getCwmsName() == "Ave"
    assert ptype.getDssName() == "PER-AVER"
    ptype = ParameterType("INST-VAL")
    assert ptype.name == "INST-VAL"
    assert ptype.getRawName() == "Instantaneous"
    assert ptype.getCwmsName() == "Inst"
    assert ptype.getDssName() == "INST-VAL"
    assert ptype.getDssName(True) == "INST-CUM"


def test_parameter_type_bad_context() -> None:
    with pytest.raises(ParameterTypeException) as excinfo:
        ParameterType.setDefaultContext("JUNK")
    assert (
        str(excinfo.value) == "Invalid context: JUNK. Must be one of RAW, CWMS, or DSS"
    )
