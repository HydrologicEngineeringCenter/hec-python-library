from typing import Generator, cast

import numpy as np
import pytest

from hec.rating import TableRating


@pytest.fixture
def rating_1_xml() -> str:
    with open("test/resources/rating/table_rating_1.xml") as f:
        return f.read()

@pytest.mark.parametrize(
    "count, opening, elevation, expected_flow",
    [  # values are from test/resources/rating/generate_table_rating_test_data_1.sql
        [1, 0, 1223, 0],
        [1, 0, 1250.5, 0],
        [1, 0, 1281.2, 0],
        [1, 0, 1300, 0],
        [1, 1.5, 1223, 0],
        [1, 1.5, 1250.5, 338.5],
        [1, 1.5, 1281.2, 497.68],
        [1, 1.5, 1300, 573.6],
        [1, 3, 1223, 0],
        [1, 3, 1250.5, 663.5],
        [1, 3, 1281.2, 986.36],
        [1, 3, 1300, 1140.2],
        [1, 6.5, 1223, 0],
        [1, 6.5, 1250.5, 1380.5],
        [1, 6.5, 1281.2, 2117.56],
        [1, 6.5, 1300, 2462],
        [1, 12.5, 1223, 0],
        [1, 12.5, 1250.5, 2491.25],
        [1, 12.5, 1281.2, 4125.22],
        [1, 12.5, 1300, 4862.9],
        [2, 0, 1223, 0],
        [2, 0, 1250.5, 0],
        [2, 0, 1281.2, 0],
        [2, 0, 1300, 0],
        [2, 1.5, 1223, 0],
        [2, 1.5, 1250.5, 676.93455],
        [2, 1.5, 1281.2, 995.30339],
        [2, 1.5, 1300, 1147.62225],
        [2, 3, 1223, 0],
        [2, 3, 1250.5, 1326.6768],
        [2, 3, 1281.2, 1973.19925],
        [2, 3, 1300, 2280.69434],
        [2, 6.5, 1223, 0],
        [2, 6.5, 1250.5, 2760.95667],
        [2, 6.5, 1281.2, 4234.62834],
        [2, 6.5, 1300, 4924.75875],
        [2, 12.5, 1223, 0],
        [2, 12.5, 1250.5, 4982.40942],
        [2, 12.5, 1281.2, 8250.48863],
        [2, 12.5, 1300, 9725.74084],
    ],
)
def test_table_rating_1(
    rating_1_xml: str, count: float, opening: float, elevation: float, expected_flow
) -> None:
    tr = cast(TableRating, TableRating.from_xml(rating_1_xml))
    ind_value = [count, opening, elevation]
    rated_flow = tr.rate_value(ind_value)
    print(f"{ind_value}\t{expected_flow}\t{rated_flow}")
    assert np.isclose(expected_flow, rated_flow)
