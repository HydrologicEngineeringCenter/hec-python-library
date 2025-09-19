from typing import Generator, cast

import numpy as np
import pytest

from hec import UnitQuantity
from hec.rating import TableRating

rating_table_1_data = (
    [  # values are from test/resources/rating/generate_table_rating_test_data_1.sql
        [1, 0, 1223, 0],
        [1, 0, 1250.3, 0],
        [1, 0, 1281.7, 0],
        [1, 0, 1300, 0],
        [1, 1.2, 1223, 0],
        [1, 1.2, 1250.3, 270.56],
        [1, 1.2, 1281.7, 400.688],
        [1, 1.2, 1300, 459.72],
        [1, 3, 1223, 0],
        [1, 3, 1250.3, 660.9],
        [1, 3, 1281.7, 990.76],
        [1, 3, 1300, 1140.2],
        [1, 6.7, 1223, 0],
        [1, 6.7, 1250.3, 1413.46],
        [1, 6.7, 1281.7, 2192.788],
        [1, 6.7, 1300, 2538.72],
        [1, 12.1, 1223, 0],
        [1, 12.1, 1250.3, 2410.47],
        [1, 12.1, 1281.7, 4006.168],
        [1, 12.1, 1300, 4693.22],
        [2, 0, 1223, 0],
        [2, 0, 1250.3, 0],
        [2, 0, 1281.7, 0],
        [2, 0, 1300, 0],
        [2, 1.2, 1223, 0],
        [2, 1.2, 1250.3, 541.47637],
        [2, 1.2, 1281.7, 801.14773],
        [2, 1.2, 1300, 919.38552],
        [2, 3, 1223, 0],
        [2, 3, 1250.3, 1321.4344],
        [2, 3, 1281.7, 1981.98755],
        [2, 3, 1300, 2280.69434],
        [2, 6.7, 1223, 0],
        [2, 6.7, 1250.3, 2827.1428],
        [2, 6.7, 1281.7, 4385.00333],
        [2, 6.7, 1300, 5077.87981],
        [2, 12.1, 1223, 0],
        [2, 12.1, 1250.3, 4820.42767],
        [2, 12.1, 1281.7, 8012.64616],
        [2, 12.1, 1300, 9386.77987],
    ]
)
rating_table_2_data = (
    [  # values are from test/resources/rating/generate_table_rating_test_data_2.sql
        [660, 6.6],
        [692.3, 77883.9],
        [722.1, 416998],
        [756, 1670400],
        [770.5, 2663850],
    ]
)


@pytest.fixture
def rating_1_xml() -> str:
    with open("test/resources/rating/table_rating_1.xml") as f:
        return f.read()


@pytest.fixture
def rating_2_xml() -> str:
    with open("test/resources/rating/table_rating_2.xml") as f:
        return f.read()


@pytest.mark.parametrize(
    "count, opening, elevation, expected_flow",
    rating_table_1_data,
)
def test_table_rating_1_individual(
    rating_1_xml: str,
    count: float,
    opening: float,
    elevation: float,
    expected_flow: float,
) -> None:
    tr = cast(TableRating, TableRating.from_xml(rating_1_xml))
    ind_value = [count, opening, elevation]
    rated_flow = tr.rate_value(ind_value)
    print(f"{ind_value}\t{expected_flow}\t{rated_flow}")
    assert np.isclose(expected_flow, rated_flow)


def test_table_rating_1_list(rating_1_xml: str) -> None:
    tr = cast(TableRating, TableRating.from_xml(rating_1_xml))
    counts, openings, elevations, expected_flows = list(
        map(list, zip(*rating_table_1_data))
    )
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_flows = tr.rate_values([counts, openings, elevations], "unit,ft,ft;cfs")
    assert np.allclose(expected_flows, rated_flows)
    # -------------------------------------------- #
    # test with different units and vertical datum #
    # -------------------------------------------- #
    assert tr.vertical_datum_info is not None
    assert tr.vertical_datum_info.navd88_offset
    navd88_offset = tr.vertical_datum_info.navd88_offset.magnitude
    ft_to_m = UnitQuantity("ft").to("m").magnitude
    cms_to_cfs = UnitQuantity("cms").to("cfs").magnitude
    openings_m = list(map(lambda v: v * ft_to_m, openings))
    elevations_m_navd88 = list(map(lambda v: (v + navd88_offset) * ft_to_m, elevations))
    rated_flows = tr.rate_values(
        [counts, openings_m, elevations_m_navd88],
        "unit,m,m;cms",
        "NAVD-88",
    )
    assert np.allclose(expected_flows, list(map(lambda v: v * cms_to_cfs, rated_flows)))


@pytest.mark.parametrize(
    "elevation, expected_stor",
    rating_table_2_data,
)
def test_table_rating_2_individual(
    rating_2_xml: str,
    elevation: float,
    expected_stor: float,
) -> None:
    tr = cast(TableRating, TableRating.from_xml(rating_2_xml))
    rated_stor = tr.rate_value([elevation])
    assert np.isclose(expected_stor, rated_stor)
    reverse_rated_elev = tr.reverse_rate_value(rated_stor)
    assert np.isclose(elevation, reverse_rated_elev)


def test_table_rating_2_list(rating_2_xml: str) -> None:
    tr = cast(TableRating, TableRating.from_xml(rating_2_xml))
    elevations, expected_stors = list(map(list, zip(*rating_table_2_data)))
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_stors = tr.rate_values([elevations], "ft;ac-ft")
    assert np.allclose(expected_stors, rated_stors)


if __name__ == "__main__":
    with open("test/resources/rating/table_rating_2.xml") as f:
        xml = f.read()
    test_table_rating_2_list(xml)
