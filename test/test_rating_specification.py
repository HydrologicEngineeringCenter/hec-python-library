import re

import pytest

from hec import Location
from hec.rating import (
    LookupMethod,
    RatingSpecification,
    RatingSpecificationException,
    RatingTemplate,
    RatingTemplateException,
)
from hec.rating.rating_specification import (
    DEFAULT_IN_RANGE_METHOD,
    DEFAULT_OUT_RANGE_HIGH_METHOD,
    DEFAULT_OUT_RANGE_LOW_METHOD,
    DEFAULT_ROUNDING_SPEC,
)

default_lookup = [
    DEFAULT_IN_RANGE_METHOD.name,
    DEFAULT_OUT_RANGE_LOW_METHOD.name,
    DEFAULT_OUT_RANGE_HIGH_METHOD.name,
]


def test_construct_name_only() -> None:
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_bad_name() -> None:
    with pytest.raises(ValueError, match="Version cannot be an empty string"):
        spec = RatingSpecification(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard."
        )


def test_construct_with_location() -> None:
    location = Location(
        "COUN",
        "SWT",
        34.1234,
        -95.1234,
        "NAD83",
        783.23,
        "ft",
        "NGVD-29",
        "US/Central",
        "PROJECT",
    )
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        location=location,
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == location
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        office=location.office,
    )
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_bad_location() -> None:
    with pytest.raises(ValueError, match="Name cannot be an empty string"):
        location = Location(
            "",
            "SWT",
            34.1234,
            -95.1234,
            "NAD83",
            783.23,
            "ft",
            "NGVD-29",
            "US/Central",
            "PROJECT",
        )
        spec = RatingSpecification(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
            location=location,
        )


def test_construct_with_template() -> None:
    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        lookup=[
            ["error", "error", "error"],
            ["linear", "error", "error"],
            ["linear", "error", "null"],
        ],
        description="Test Template",
    )
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        template=template,
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == template
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_bad_template() -> None:
    with pytest.raises(
        ValueError, match="Elevation does not contain a recognized base parameter"
    ):
        template = RatingTemplate(
            "Count-Conduit_Gates,Opening-Conduit_Gates,Elevation;Flow-Conduit_Gates.Standard",
            lookup=[
                ["error", "error", "error"],
                ["linear", "error", "error"],
                ["linear", "error", "null"],
            ],
            description="Test Template",
        )
        spec = RatingSpecification(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
            template=template,
        )


def test_construct_with_lookup() -> None:
    lookup = [
        LookupMethod.LINEAR.name,
        LookupMethod.ERROR.name,
        LookupMethod.ERROR.name,
    ]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        lookup=lookup,
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert spec.version == "Production"
    assert spec.lookup == lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_bad_lookup() -> None:
    with pytest.raises(KeyError, match="IGNORE"):
        spec = RatingSpecification(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
            lookup=["linear", "error", "ignore"],
        )


def test_construct_with_rounding() -> None:
    rounding = ["1234567899", "1234567899", "1234567899", DEFAULT_ROUNDING_SPEC]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        rounding=rounding,
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == rounding


def test_construct_bad_rounding() -> None:
    with pytest.raises(
        TypeError,
        match=re.escape("Expected 10-digit str for 'value[1]', got '123456789'"),
    ):
        spec = RatingSpecification(
            "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
            rounding=["1234567899", "123456789", "1234567899", DEFAULT_ROUNDING_SPEC],
        )


def test_constuct_with_all() -> None:
    location = Location(
        "COUN",
        "SWT",
        34.1234,
        -95.1234,
        "NAD83",
        783.23,
        "ft",
        "NGVD-29",
        "US/Central",
        "PROJECT",
    )
    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        office="SWT",
        lookup=[
            ["error", "error", "error"],
            ["linear", "error", "error"],
            ["linear", "error", "null"],
        ],
        description="Test Template",
    )
    lookup = [
        LookupMethod.LINEAR.name,
        LookupMethod.ERROR.name,
        LookupMethod.ERROR.name,
    ]
    rounding = ["1234567899", "1234567899", "1234567899", DEFAULT_ROUNDING_SPEC]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production",
        location=location,
        template=template,
        lookup=lookup,
        rounding=rounding,
    )
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == location
    assert spec.template == template
    assert spec.version == "Production"
    assert spec.lookup == lookup
    assert spec.rounding == rounding


def construct_and_set_location() -> None:
    location = Location(
        "COUN",
        "SWT",
        34.1234,
        -95.1234,
        "NAD83",
        783.23,
        "ft",
        "NGVD-29",
        "US/Central",
        "PROJECT",
    )
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    spec.location = location
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == location
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        office=location.office,
    )
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_and_set_template() -> None:
    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        lookup=[
            ["error", "error", "error"],
            ["linear", "error", "error"],
            ["linear", "error", "null"],
        ],
        description="Test Template",
    )
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    spec.template = template
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == template
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_and_set_lookup() -> None:
    lookup = [
        LookupMethod.LINEAR.name,
        LookupMethod.ERROR.name,
        LookupMethod.ERROR.name,
    ]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    spec.lookup = lookup
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert spec.version == "Production"
    assert spec.lookup == lookup
    assert spec.rounding == (spec.template.ind_param_count + 1) * [
        DEFAULT_ROUNDING_SPEC
    ]


def test_construct_and_set_rounding() -> None:
    rounding = ["1234567899", "1234567899", "1234567899", DEFAULT_ROUNDING_SPEC]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    spec.rounding = rounding
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == Location("COUN")
    assert spec.template == RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    )
    assert spec.version == "Production"
    assert spec.lookup == default_lookup
    assert spec.rounding == rounding


def test_constuct_and_set_all() -> None:
    location = Location(
        "COUN",
        "SWT",
        34.1234,
        -95.1234,
        "NAD83",
        783.23,
        "ft",
        "NGVD-29",
        "US/Central",
        "PROJECT",
    )
    template = RatingTemplate(
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard",
        office="SWT",
        lookup=[
            ["error", "error", "error"],
            ["linear", "error", "error"],
            ["linear", "error", "null"],
        ],
        description="Test Template",
    )
    lookup = [
        LookupMethod.LINEAR.name,
        LookupMethod.ERROR.name,
        LookupMethod.ERROR.name,
    ]
    rounding = ["1234567899", "1234567899", "1234567899", DEFAULT_ROUNDING_SPEC]
    spec = RatingSpecification(
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    spec.location = location
    spec.template = template
    spec.lookup = lookup
    spec.rounding = rounding
    assert (
        spec.name
        == "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    )
    assert spec.location == location
    assert spec.template == template
    assert spec.version == "Production"
    assert spec.lookup == lookup
    assert spec.rounding == rounding


if __name__ == "__main__":
    test_construct_with_template()
