from pint.errors import DimensionalityError
from hec import unit
import os, pint, pytest

scriptdir: str = os.path.dirname(__file__)
ureg = unit.ureg


# --------------------------- #
# build a dataset from a file #
# --------------------------- #
def dataset_from_file(filename: str) -> list[list[str]]:
    dataset: list[list[str]] = []
    with open(os.path.join(scriptdir, filename)) as f:
        for line in f.readlines():
            if not line or line.startswith("#"):
                continue
            dataset.append(list(line.strip().split("\t")))
    return dataset


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
