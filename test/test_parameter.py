"""
Module for testing hec.parameter module
"""

from hec.parameter import Parameter
from hec.parameter import ElevParameter
from hec.parameter import ParameterException
from hec.unit import UnitQuantity as UQ
import pytest


def test_parameter() -> None:
    p = Parameter("FLOW-IN", "KCFS")
    assert repr(p) == "Parameter('FLOW-IN', 'kcfs')"
    assert str(p) == "FLOW-IN (kcfs)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit == "kcfs"

    assert p.get_compatible_units() == ['cfs', 'cms', 'gpm', 'KAF/mon', 'kcfs', 'kcms', 'mcm/mon', 'mgd']

    assert repr(p.to("mgd")) == "Parameter('FLOW-IN', 'mgd')"
    assert str(p.to("mgd")) == "FLOW-IN (mgd)"

    assert repr(p.to("EN")) == "Parameter('FLOW-IN', 'cfs')"
    assert str(p.to("EN")) == "FLOW-IN (cfs)"

    assert repr(p.to("SI")) == "Parameter('FLOW-IN', 'cms')"
    assert str(p.to("SI")) == "FLOW-IN (cms)"

    with pytest.raises(ParameterException) as excinfo:
        p.to("ac-ft")
    assert str(excinfo.value).startswith("ac-ft is not a vaild unit for base parameter Flow")

    assert repr(p) == "Parameter('FLOW-IN', 'kcfs')"
    assert str(p) == "FLOW-IN (kcfs)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit == "kcfs"

    p.to("SI", in_place=True)
    assert repr(p) == "Parameter('FLOW-IN', 'cms')"
    assert str(p) == "FLOW-IN (cms)"
    assert p.name == "FLOW-IN"
    assert p.basename == "FLOW"
    assert p.subname == "IN"
    assert p.base_parameter == "Flow"
    assert p.unit == "cms"

def test_elev_parameter() -> None:
    xml = """
          <vertical-datum-info unit="ft">
          <native-datum>OTHER</native-datum>
          <local-datum-name>Pensacola</local-datum-name>
          <elevation>757</elevation>
          <offset estimate="true">
              <to-datum>NAVD-88</to-datum>
              <value>1.457</value>
          </offset>
          <offset estimate="false">
              <to-datum>NGVD-29</to-datum>
              <value>1.07</value>
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
    assert p.unit == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.ngvd_29_offset == UQ(1.07, "ft")
    assert p.ngvd_29_offset_is_estimate == False
    assert p.navd_88_offset == UQ(1.457, "ft")
    assert p.navd_88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p2 = p.to("NAVD88")
    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p2.name == "Elev"
    assert p2.basename == "Elev"
    assert p2.subname is None
    assert p2.base_parameter == "Elev"
    assert p2.unit == "ft"
    assert p2.elevation == UQ(757, "ft") + p.get_offset_to("navd-88")
    assert p2.native_datum == "Pensacola"
    assert p2.current_datum == "NAVD-88"
    assert p2.ngvd_29_offset == UQ(1.07, "ft")
    assert p2.ngvd_29_offset_is_estimate == False
    assert p2.navd_88_offset == UQ(1.457, "ft")
    assert p2.navd_88_offset_is_estimate == True
    assert p2.get_offset_to("ngvd-29") == UQ(-0.387, "ft")
    assert p2.get_offset_to("navd-88") is None

    assert repr(p) == "ElevParameter('Elev', <vertical-datum-info>)"
    assert str(p) == "Elev (<vertical-datum-info>)"
    assert p.name == "Elev"
    assert p.basename == "Elev"
    assert p.subname is None
    assert p.base_parameter == "Elev"
    assert p.unit == "ft"
    assert p.elevation == UQ(757, "ft")
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.ngvd_29_offset == UQ(1.07, "ft")
    assert p.ngvd_29_offset_is_estimate == False
    assert p.navd_88_offset == UQ(1.457, "ft")
    assert p.navd_88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29") == UQ(1.07, "ft")
    assert p.get_offset_to("navd-88") == UQ(1.457, "ft")

    p.to("m", in_place=True)
    assert p.unit == "m"
    assert p.elevation.magnitude == pytest.approx(757 * .3048)
    assert p.elevation.specified_unit == "m"
    assert p.native_datum == "Pensacola"
    assert p.current_datum == "Pensacola"
    assert p.ngvd_29_offset.magnitude == pytest.approx(1.07 * .3048)
    assert p.ngvd_29_offset.specified_unit == "m"
    assert p.ngvd_29_offset_is_estimate == False
    assert p.navd_88_offset.magnitude == pytest.approx(1.457 * .3048)
    assert p.navd_88_offset.specified_unit == "m"
    assert p.navd_88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29").magnitude == pytest.approx(1.07 * .3048)
    assert p.get_offset_to("ngvd-29").specified_unit == "m"
    assert p.get_offset_to("navd-88").magnitude == pytest.approx(1.457 * .3048)
    assert p.get_offset_to("navd-88").specified_unit == "m"


    p.to("NAVD88", in_place=True)
    assert p.unit == "m"
    assert p.current_datum == "NAVD-88"
    assert p.ngvd_29_offset.magnitude == pytest.approx(1.07 * .3048)
    assert p.ngvd_29_offset.specified_unit == "m"
    assert p.ngvd_29_offset_is_estimate == False
    assert p.navd_88_offset.magnitude == pytest.approx(1.457 * .3048)
    assert p.navd_88_offset.specified_unit == "m"
    assert p.navd_88_offset_is_estimate == True
    assert p.get_offset_to("ngvd-29").magnitude == pytest.approx(-0.387 * .3048)
    assert p.get_offset_to("ngvd-29").specified_unit == "m"
    assert p.get_offset_to("navd-88") is None
