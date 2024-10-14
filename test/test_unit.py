import os
import warnings
from test.shared import dataset_from_file

import pytest
from pint.errors import DimensionalityError

from hec import unit

try:
    import cwms  # type: ignore

    cwms_imported = True
except ImportError:
    cwms_imported = False

ureg = unit.get_unit_registry()


# --------------------- #
# test unit conversions #
# --------------------- #
@pytest.mark.parametrize(
    "from_unit, to_unit, _expected",
    dataset_from_file("resources/unit/cwms_db_conversions.txt"),
)
def test_db_conversions(from_unit: str, to_unit: str, _expected: str) -> None:
    if _expected == "unconvertable":
        with pytest.raises(DimensionalityError) as excinfo:
            unit.convert_units(1.0, from_unit, to_unit)
        assert str(excinfo.value).startswith("Cannot convert from ")
    else:
        expected = float(_expected)
        assert unit.convert_units(1.0, from_unit, to_unit) == pytest.approx(expected)
        src_unit = unit.get_pint_unit(from_unit)
        assert unit.convert_units(
            ureg(f"{src_unit}"), from_unit, to_unit
        ).magnitude == pytest.approx(expected)


# ----------------------------------- #
# test unit conversion on time series #
# ----------------------------------- #
def test_convert_timeseries() -> None:
    if cwms_imported:
        elevData = cwms.cwms_types.Data(
            {
                "begin": "2024-10-01T12:54:22+0000[Z]",
                "end": "2024-10-01T18:54:22+0000[UTC]",
                "interval": "PT0S",
                "interval-offset": 0,
                "name": "KEYS.Elev.Inst.1Hour.0.Ccp-Rev",
                "office-id": "SWT",
                "page": "MTcyNzc4NzYwMDAwMHx8Nnx8NTAwMDAw",
                "page-size": 500000,
                "time-zone": "US/Central",
                "total": 6,
                "units": "m",
                "value-columns": [
                    {
                        "name": "date-time",
                        "ordinal": 1,
                        "datatype": "java.sql.Timestamp",
                    },
                    {"name": "value", "ordinal": 2, "datatype": "java.lang.Double"},
                    {"name": "quality-code", "ordinal": 3, "datatype": "int"},
                ],
                "values": [
                    [1727787600000, 219.465144, 0],
                    [1727791200000, 219.465144, 0],
                    [1727794800000, 219.465144, 0],
                    [1727798400000, 219.465144, 0],
                    [1727802000000, 219.462096, 0],
                    [1727805600000, 219.462096, 0],
                ],
                "vertical-datum-info": {
                    "office": "SWT",
                    "unit": "m",
                    "location": "KEYS",
                    "native-datum": "NGVD-29",
                    "elevation": 187.522,
                    "offsets": [
                        {"estimate": True, "to-datum": "NAVD-88", "value": 0.1105}
                    ],
                },
            }
        )
        unit.convert_units(elevData, "m", "ft", in_place=True)
        assert elevData.json["units"] == "ft"
        for i in range(0, 4):
            assert elevData.json["values"][i][1] == pytest.approx(720.03)
        for i in range(4, 6):
            assert elevData.json["values"][i][1] == pytest.approx(720.02)
        assert elevData.json["vertical-datum-info"]["unit"] == "ft"
        assert elevData.json["vertical-datum-info"]["offsets"][0][
            "value"
        ] == pytest.approx(0.1105 / 0.3048)
    else:
        warnings.warn(
            f"Cannot run test test_convert_timeseries() because cwms module is not installed",
            UserWarning,
        )


# ----------------- #
# test unit aliases #
# ----------------- #
def test_unit_aliases() -> None:
    for unit_name in unit.pint_units_by_unit_name:
        expected_aliases = [
            alias
            for alias in unit.unit_names_by_alias
            if unit.unit_names_by_alias[alias] == unit_name
        ]
        assert unit.get_unit_aliases(unit_name) == expected_aliases


# --------------------- #
# test compaitble units #
# --------------------- #
def test_compatible_units() -> None:
    for unit_name in unit.pint_units_by_unit_name:
        dimesionality = str(unit.get_pint_unit(unit_name).dimensionality)
        for compatible_unit_name in unit.get_compatible_units(unit_name):
            assert (
                str(unit.get_pint_unit(compatible_unit_name).dimensionality)
                == dimesionality
            )
