import pytest
from lxml import etree

from hec.rating import RatingTemplate, RatingTemplateException


def test_valid_construction() -> None:

    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        lookup=[
            ["error", "error", "error"],
            ["linear", "null", "null"],
            ["linear", "error", "linear"],
        ],
        description="Gate Rating (Number, Opening, Elev) --> Flow",
    )

    assert (
        template.name
        == "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    with pytest.raises(AttributeError):
        template.name = "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"  # type: ignore
    assert template.ind_param_count == 3
    with pytest.raises(AttributeError):
        template.ind_param_count = 3  # type: ignore
    assert template.ind_params == [
        "Count-Conduit_Gates",
        "Opening-Conduit_Gates",
        "Elev",
    ]
    with pytest.raises(AttributeError):
        template.ind_params = ["Count-Conduit_Gates", "Opening-Conduit_Gates", "Elev"]  # type: ignore
    assert template.dep_param == "Flow-Conduit_Gates"
    template.dep_param = "Flow"
    assert template.dep_param == "Flow"
    assert template.lookup == [
        ["ERROR", "ERROR", "ERROR"],
        ["LINEAR", "NULL", "NULL"],
        ["LINEAR", "ERROR", "LINEAR"],
    ]
    template.lookup = [
        ["LINEAR", "NEAREST", "NEAREST"],
        ["LINEAR", "NEAREST", "NEAREST"],
        ["LINEAR", "NEAREST", "NEAREST"],
    ]
    assert template.lookup == [
        ["LINEAR", "NEAREST", "NEAREST"],
        ["LINEAR", "NEAREST", "NEAREST"],
        ["LINEAR", "NEAREST", "NEAREST"],
    ]
    assert template.version == "Standard"
    template.version = "LINEAR"
    assert template.version == "LINEAR"
    assert template.description == "Gate Rating (Number, Opening, Elev) --> Flow"
    template.description = None
    assert template.description is None

    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        lookup=[[2, 2, 2], [3, 1, 1], [3, 2, 3]],
        description="Gate Rating (Number, Opening, Elev) --> Flow",
    )

    assert (
        template.name
        == "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert template.ind_param_count == 3
    assert template.ind_params == [
        "Count-Conduit_Gates",
        "Opening-Conduit_Gates",
        "Elev",
    ]
    assert template.dep_param == "Flow-Conduit_Gates"
    assert template.lookup == [
        ["ERROR", "ERROR", "ERROR"],
        ["LINEAR", "NULL", "NULL"],
        ["LINEAR", "ERROR", "LINEAR"],
    ]
    assert template.version == "Standard"
    assert template.description == "Gate Rating (Number, Opening, Elev) --> Flow"

    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert (
        template.name
        == "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert template.ind_param_count == 3
    assert template.ind_params == [
        "Count-Conduit_Gates",
        "Opening-Conduit_Gates",
        "Elev",
    ]
    assert template.dep_param == "Flow-Conduit_Gates"
    assert template.lookup == [
        ["LINEAR", "NEXT", "PREVIOUS"],
        ["LINEAR", "NEXT", "PREVIOUS"],
        ["LINEAR", "NEXT", "PREVIOUS"],
    ]
    assert template.version == "Standard"
    assert template.description is None

    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        lookup=["linear", "null", "null"],
    )
    assert (
        template.name
        == "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert template.ind_param_count == 3
    assert template.ind_params == [
        "Count-Conduit_Gates",
        "Opening-Conduit_Gates",
        "Elev",
    ]
    assert template.dep_param == "Flow-Conduit_Gates"
    assert template.lookup == [
        ["LINEAR", "NULL", "NULL"],
        ["LINEAR", "NULL", "NULL"],
        ["LINEAR", "NULL", "NULL"],
    ]
    assert template.version == "Standard"
    assert template.description is None


def test_invalid_construction() -> None:

    with pytest.raises(ValueError, match="Name must be of format"):
        template = RatingTemplate(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        )

    with pytest.raises(
        ValueError, match="does not contain a recognized base parameter"
    ):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elevation;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "null", "null"],
                ["linear", "error", "linear"],
            ],
            description="Gate Rating (Number, Opening, Elev) --> Flow",
        )

    with pytest.raises(TypeError, match="Expected str for 'name', got"):
        template = RatingTemplate(
            5.2,  # type: ignore
        )

    with pytest.raises(ValueError, match="Empty list or tuple passed for 'lookup'"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[[], ["linear", "null", "null"], ["linear", "error", "linear"]],
        )

    with pytest.raises(ValueError, match="Empty list or tuple passed for 'lookup'"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[],
        )

    with pytest.raises(TypeError, match="Expected list or tuple for 'lookup'"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=12,
            description="Gate Rating (Number, Opening, Elev) --> Flow",
        )

    with pytest.raises(ValueError, match="Expected 3 values for 'lookup', got 2"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "null", "null"],
            ],
        )

    with pytest.raises(KeyError, match="IGNORE"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "null", "null"],
                ["linear", "error", "ignore"],
            ],
        )

    with pytest.raises(IndexError, match="0"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[[2, 2, 2], [3, 1, 1], [3, 2, 0]],
        )

    with pytest.raises(TypeError, match="Expected str for 'description', got"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "null", "null"],
                ["linear", "error", "linear"],
            ],
            description=7,
        )

    with pytest.raises(TypeError, match="'extra' is an invalid keyword"):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "null", "null"],
                ["linear", "error", "linear"],
            ],
            extra="some stuff",
        )


def test_xml_operations() -> None:

    xml_str = """<rating-template office="SWT">
  <parameters-id>Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates</parameters-id>
  <version>Standard</version>
  <ind-parameter-specs>
    <ind-parameter-spec position="1">
      <parameter>Count-Conduit_Gates</parameter>
      <in-range-method>ERROR</in-range-method>
      <out-range-low-method>ERROR</out-range-low-method>
      <out-range-high-method>ERROR</out-range-high-method>
    </ind-parameter-spec>
    <ind-parameter-spec position="2">
      <parameter>Opening-Conduit_Gates</parameter>
      <in-range-method>LINEAR</in-range-method>
      <out-range-low-method>NULL</out-range-low-method>
      <out-range-high-method>NULL</out-range-high-method>
    </ind-parameter-spec>
    <ind-parameter-spec position="3">
      <parameter>Elev</parameter>
      <in-range-method>LINEAR</in-range-method>
      <out-range-low-method>ERROR</out-range-low-method>
      <out-range-high-method>LINEAR</out-range-high-method>
    </ind-parameter-spec>
  </ind-parameter-specs>
  <dep-parameter>Flow-Conduit_Gates</dep-parameter>
  <description>Gate Rating (Number, Opening, Elev) --&gt; Flow</description>
</rating-template>
"""

    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        office="SWT",
        lookup=[
            ["error", "error", "error"],
            ["linear", "null", "null"],
            ["linear", "error", "linear"],
        ],
        description="Gate Rating (Number, Opening, Elev) --> Flow",
    )
    assert template.to_xml() == xml_str

    template2 = RatingTemplate.from_xml(xml_str)
    assert template2.to_xml() == xml_str


if __name__ == "__main__":
    test_valid_construction()
    test_invalid_construction()
    test_xml_operations()
