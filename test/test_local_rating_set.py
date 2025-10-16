import os
import re
import warnings
from datetime import datetime
from typing import Any, Optional, cast

import numpy as np
import pytest
from lxml import etree

from hec import CwmsDataStore, DssDataStore, TimeSeries, UnitQuantity
from hec.rating import AbstractRatingSet, LocalRatingSet
from hec.shared import import_cwms, import_hecdss

_db: Optional[CwmsDataStore] = None
_dss: Optional[DssDataStore] = None
_rs_reference_cwms: Optional[AbstractRatingSet] = None
_rs_eager_cwms: Optional[AbstractRatingSet] = None
_rs_lazy_cwms: Optional[AbstractRatingSet] = None
_rs_eager_dss: Optional[AbstractRatingSet] = None
_rs_lazy_dss: Optional[AbstractRatingSet] = None

rating_set_3_ind_params_file_name = (
    "test/resources/rating/local_rating_set_3_ind_params.xml"
)
rating_set_1_ind_param_file_name = (
    "test/resources/rating/local_rating_set_1_ind_param.xml"
)
rating_set_large_file_name = "test/resources/rating/local_rating_set_large.xml"

dss_file_name = "test/resources/rating/local_rating_set.dss"


def replace_indent(s: str, old_indent: str, new_indent: str) -> str:
    pattern = f"^(?:{re.escape(old_indent)})+"

    def repl(match: re.Match[str]) -> str:
        count = len(match.group(0)) // len(old_indent)
        return new_indent * count

    return re.sub(pattern, repl, s, flags=re.MULTILINE)


def can_use_cda() -> bool:
    try:
        import_cwms()
    except:
        return False
    if os.getenv("cda_api_root") != "https://wm.swt.ds.usace.army.mil:8243/swt-data/":
        return False
    if os.getenv("cda_api_office") != "SWT":
        return False
    return os.getenv("USERNAME", "").lower() == "q0hecmdp"


@pytest.fixture
def rating_set_3_ind_params() -> LocalRatingSet:
    with open(rating_set_3_ind_params_file_name) as f:
        return LocalRatingSet.from_xml(f.read())


@pytest.fixture
def rating_set_1_ind_param() -> LocalRatingSet:
    with open(rating_set_1_ind_param_file_name) as f:
        return LocalRatingSet.from_xml(f.read())


@pytest.fixture
def rating_set_large() -> LocalRatingSet:
    with open(rating_set_large_file_name) as f:
        return LocalRatingSet.from_xml(f.read())


rating_set_1_data = (
    [  # values are from test/resources/rating/generate_local_rating_set_test_data_1.sql
        ["2012-04-26T00:00:00+00:00", 1, 0, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 1, 0, 1250.3, 0],
        ["2012-04-26T00:00:00+00:00", 1, 0, 1281.7, 0],
        ["2012-04-26T00:00:00+00:00", 1, 0, 1300, 0],
        ["2012-04-26T00:00:00+00:00", 1, 1.2, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 1, 1.2, 1250.3, 270.56],
        ["2012-04-26T00:00:00+00:00", 1, 1.2, 1281.7, 400.688],
        ["2012-04-26T00:00:00+00:00", 1, 1.2, 1300, 459.72],
        ["2012-04-26T00:00:00+00:00", 1, 3, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 1, 3, 1250.3, 660.9],
        ["2012-04-26T00:00:00+00:00", 1, 3, 1281.7, 990.76],
        ["2012-04-26T00:00:00+00:00", 1, 3, 1300, 1140.2],
        ["2012-04-26T00:00:00+00:00", 1, 6.7, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 1, 6.7, 1250.3, 1413.46],
        ["2012-04-26T00:00:00+00:00", 1, 6.7, 1281.7, 2192.788],
        ["2012-04-26T00:00:00+00:00", 1, 6.7, 1300, 2538.72],
        ["2012-04-26T00:00:00+00:00", 1, 12.1, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 1, 12.1, 1250.3, 2410.47],
        ["2012-04-26T00:00:00+00:00", 1, 12.1, 1281.7, 4006.168],
        ["2012-04-26T00:00:00+00:00", 1, 12.1, 1300, 4693.22],
        ["2012-04-26T00:00:00+00:00", 2, 0, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 2, 0, 1250.3, 45.91889],
        ["2012-04-26T00:00:00+00:00", 2, 0, 1281.7, 67.36861],
        ["2012-04-26T00:00:00+00:00", 2, 0, 1300, 77.17773],
        ["2012-04-26T00:00:00+00:00", 2, 1.2, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 2, 1.2, 1250.3, 541.47637],
        ["2012-04-26T00:00:00+00:00", 2, 1.2, 1281.7, 801.14773],
        ["2012-04-26T00:00:00+00:00", 2, 1.2, 1300, 919.38552],
        ["2012-04-26T00:00:00+00:00", 2, 3, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 2, 3, 1250.3, 1321.4344],
        ["2012-04-26T00:00:00+00:00", 2, 3, 1281.7, 1981.98755],
        ["2012-04-26T00:00:00+00:00", 2, 3, 1300, 2280.69434],
        ["2012-04-26T00:00:00+00:00", 2, 6.7, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 2, 6.7, 1250.3, 2827.1428],
        ["2012-04-26T00:00:00+00:00", 2, 6.7, 1281.7, 4385.00333],
        ["2012-04-26T00:00:00+00:00", 2, 6.7, 1300, 5077.87981],
        ["2012-04-26T00:00:00+00:00", 2, 12.1, 1223, 0],
        ["2012-04-26T00:00:00+00:00", 2, 12.1, 1250.3, 4820.42767],
        ["2012-04-26T00:00:00+00:00", 2, 12.1, 1281.7, 8012.64616],
        ["2012-04-26T00:00:00+00:00", 2, 12.1, 1300, 9386.77987],
        ["2012-04-27T00:00:00+00:00", 1, 0, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 1, 0, 1250.3, 0],
        ["2012-04-27T00:00:00+00:00", 1, 0, 1281.7, 0],
        ["2012-04-27T00:00:00+00:00", 1, 0, 1300, 0],
        ["2012-04-27T00:00:00+00:00", 1, 1.2, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 1, 1.2, 1250.3, 270.56],
        ["2012-04-27T00:00:00+00:00", 1, 1.2, 1281.7, 400.688],
        ["2012-04-27T00:00:00+00:00", 1, 1.2, 1300, 459.72],
        ["2012-04-27T00:00:00+00:00", 1, 3, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 1, 3, 1250.3, 660.9],
        ["2012-04-27T00:00:00+00:00", 1, 3, 1281.7, 990.76],
        ["2012-04-27T00:00:00+00:00", 1, 3, 1300, 1140.2],
        ["2012-04-27T00:00:00+00:00", 1, 6.7, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 1, 6.7, 1250.3, 1413.46],
        ["2012-04-27T00:00:00+00:00", 1, 6.7, 1281.7, 2192.788],
        ["2012-04-27T00:00:00+00:00", 1, 6.7, 1300, 2538.72],
        ["2012-04-27T00:00:00+00:00", 1, 12.1, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 1, 12.1, 1250.3, 2410.47],
        ["2012-04-27T00:00:00+00:00", 1, 12.1, 1281.7, 4006.168],
        ["2012-04-27T00:00:00+00:00", 1, 12.1, 1300, 4693.22],
        ["2012-04-27T00:00:00+00:00", 2, 0, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 2, 0, 1250.3, 45.91889],
        ["2012-04-27T00:00:00+00:00", 2, 0, 1281.7, 67.36861],
        ["2012-04-27T00:00:00+00:00", 2, 0, 1300, 77.17773],
        ["2012-04-27T00:00:00+00:00", 2, 1.2, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 2, 1.2, 1250.3, 541.47637],
        ["2012-04-27T00:00:00+00:00", 2, 1.2, 1281.7, 801.14773],
        ["2012-04-27T00:00:00+00:00", 2, 1.2, 1300, 919.38552],
        ["2012-04-27T00:00:00+00:00", 2, 3, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 2, 3, 1250.3, 1321.4344],
        ["2012-04-27T00:00:00+00:00", 2, 3, 1281.7, 1981.98755],
        ["2012-04-27T00:00:00+00:00", 2, 3, 1300, 2280.69434],
        ["2012-04-27T00:00:00+00:00", 2, 6.7, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 2, 6.7, 1250.3, 2827.1428],
        ["2012-04-27T00:00:00+00:00", 2, 6.7, 1281.7, 4385.00333],
        ["2012-04-27T00:00:00+00:00", 2, 6.7, 1300, 5077.87981],
        ["2012-04-27T00:00:00+00:00", 2, 12.1, 1223, 0],
        ["2012-04-27T00:00:00+00:00", 2, 12.1, 1250.3, 4820.42767],
        ["2012-04-27T00:00:00+00:00", 2, 12.1, 1281.7, 8012.64616],
        ["2012-04-27T00:00:00+00:00", 2, 12.1, 1300, 9386.77987],
        ["2012-04-28T00:00:00+00:00", 1, 0, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 1, 0, 1250.3, 0],
        ["2012-04-28T00:00:00+00:00", 1, 0, 1281.7, 0],
        ["2012-04-28T00:00:00+00:00", 1, 0, 1300, 0],
        ["2012-04-28T00:00:00+00:00", 1, 1.2, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 1, 1.2, 1250.3, 270.56],
        ["2012-04-28T00:00:00+00:00", 1, 1.2, 1281.7, 400.688],
        ["2012-04-28T00:00:00+00:00", 1, 1.2, 1300, 459.72],
        ["2012-04-28T00:00:00+00:00", 1, 3, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 1, 3, 1250.3, 660.9],
        ["2012-04-28T00:00:00+00:00", 1, 3, 1281.7, 990.76],
        ["2012-04-28T00:00:00+00:00", 1, 3, 1300, 1140.2],
        ["2012-04-28T00:00:00+00:00", 1, 6.7, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 1, 6.7, 1250.3, 1413.46],
        ["2012-04-28T00:00:00+00:00", 1, 6.7, 1281.7, 2192.788],
        ["2012-04-28T00:00:00+00:00", 1, 6.7, 1300, 2538.72],
        ["2012-04-28T00:00:00+00:00", 1, 12.1, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 1, 12.1, 1250.3, 2410.47],
        ["2012-04-28T00:00:00+00:00", 1, 12.1, 1281.7, 4006.168],
        ["2012-04-28T00:00:00+00:00", 1, 12.1, 1300, 4693.22],
        ["2012-04-28T00:00:00+00:00", 2, 0, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 2, 0, 1250.3, 0],
        ["2012-04-28T00:00:00+00:00", 2, 0, 1281.7, 0],
        ["2012-04-28T00:00:00+00:00", 2, 0, 1300, 0],
        ["2012-04-28T00:00:00+00:00", 2, 1.2, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 2, 1.2, 1250.3, 541.47637],
        ["2012-04-28T00:00:00+00:00", 2, 1.2, 1281.7, 801.14773],
        ["2012-04-28T00:00:00+00:00", 2, 1.2, 1300, 919.38552],
        ["2012-04-28T00:00:00+00:00", 2, 3, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 2, 3, 1250.3, 1321.4344],
        ["2012-04-28T00:00:00+00:00", 2, 3, 1281.7, 1981.98755],
        ["2012-04-28T00:00:00+00:00", 2, 3, 1300, 2280.69434],
        ["2012-04-28T00:00:00+00:00", 2, 6.7, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 2, 6.7, 1250.3, 2827.1428],
        ["2012-04-28T00:00:00+00:00", 2, 6.7, 1281.7, 4385.00333],
        ["2012-04-28T00:00:00+00:00", 2, 6.7, 1300, 5077.87981],
        ["2012-04-28T00:00:00+00:00", 2, 12.1, 1223, 0],
        ["2012-04-28T00:00:00+00:00", 2, 12.1, 1250.3, 4820.42767],
        ["2012-04-28T00:00:00+00:00", 2, 12.1, 1281.7, 8012.64616],
        ["2012-04-28T00:00:00+00:00", 2, 12.1, 1300, 9386.77987],
    ]
)
rating_set_2_data = [  # values are from test/resources/rating/generate_local_rating_set_test_data_2.sql],
    ["2009-01-01T00:00:00+00:00", 660, 6.6],
    ["2009-01-01T00:00:00+00:00", 692.3, 81444.3],
    ["2009-01-01T00:00:00+00:00", 722.1, 425315],
    ["2009-01-01T00:00:00+00:00", 756, 1676820],
    ["2009-01-01T00:00:00+00:00", 770.5, 2679390],
    ["2010-01-01T00:00:00+00:00", 660, 6.6],
    ["2010-01-01T00:00:00+00:00", 692.3, 80201.81739],
    ["2010-01-01T00:00:00+00:00", 722.1, 422412.59357],
    ["2010-01-01T00:00:00+00:00", 756, 1674579.59489],
    ["2010-01-01T00:00:00+00:00", 770.5, 2673966.96333],
    ["2011-01-01T00:00:00+00:00", 660, 6.6],
    ["2011-01-01T00:00:00+00:00", 692.3, 78912.53195],
    ["2011-01-01T00:00:00+00:00", 722.1, 419400.85697],
    ["2011-01-01T00:00:00+00:00", 756, 1672254.79641],
    ["2011-01-01T00:00:00+00:00", 770.5, 2668339.64739],
    ["2012-01-01T00:00:00+00:00", 660, 8.57153],
    ["2012-01-01T00:00:00+00:00", 692.3, 77658.85623],
    ["2012-01-01T00:00:00+00:00", 722.1, 416299.69526],
    ["2012-01-01T00:00:00+00:00", 756, 1668377.53943],
    ["2012-01-01T00:00:00+00:00", 770.5, 2661340.52374],
    ["2013-01-01T00:00:00+00:00", 660, 18.35014],
    ["2013-01-01T00:00:00+00:00", 692.3, 76542.65948],
    ["2013-01-01T00:00:00+00:00", 722.1, 412836.16686],
    ["2013-01-01T00:00:00+00:00", 756, 1658346.31773],
    ["2013-01-01T00:00:00+00:00", 770.5, 2648893.74824],
    ["2014-01-01T00:00:00+00:00", 660, 28.10204],
    ["2014-01-01T00:00:00+00:00", 692.3, 75429.51245],
    ["2014-01-01T00:00:00+00:00", 722.1, 409382.10164],
    ["2014-01-01T00:00:00+00:00", 756, 1648342.50374],
    ["2014-01-01T00:00:00+00:00", 770.5, 2636480.98031],
    ["2015-01-01T00:00:00+00:00", 660, 37.85394],
    ["2015-01-01T00:00:00+00:00", 692.3, 74316.36542],
    ["2015-01-01T00:00:00+00:00", 722.1, 405928.03643],
    ["2015-01-01T00:00:00+00:00", 756, 1638338.68975],
    ["2015-01-01T00:00:00+00:00", 770.5, 2624068.21238],
    ["2016-01-01T00:00:00+00:00", 660, 47.60584],
    ["2016-01-01T00:00:00+00:00", 692.3, 73203.21839],
    ["2016-01-01T00:00:00+00:00", 722.1, 402473.97122],
    ["2016-01-01T00:00:00+00:00", 756, 1628334.87575],
    ["2016-01-01T00:00:00+00:00", 770.5, 2611655.44446],
    ["2017-01-01T00:00:00+00:00", 660, 57.38445],
    ["2017-01-01T00:00:00+00:00", 692.3, 72087.02164],
    ["2017-01-01T00:00:00+00:00", 722.1, 399010.44281],
    ["2017-01-01T00:00:00+00:00", 756, 1618303.65405],
    ["2017-01-01T00:00:00+00:00", 770.5, 2599208.66895],
    ["2018-01-01T00:00:00+00:00", 660, 67.13635],
    ["2018-01-01T00:00:00+00:00", 692.3, 70973.8746],
    ["2018-01-01T00:00:00+00:00", 722.1, 395556.3776],
    ["2018-01-01T00:00:00+00:00", 756, 1608299.84006],
    ["2018-01-01T00:00:00+00:00", 770.5, 2586795.90102],
    ["2019-01-01T00:00:00+00:00", 660, 76.88824],
    ["2019-01-01T00:00:00+00:00", 692.3, 69860.72757],
    ["2019-01-01T00:00:00+00:00", 722.1, 392102.31239],
    ["2019-01-01T00:00:00+00:00", 756, 1598296.02607],
    ["2019-01-01T00:00:00+00:00", 770.5, 2574383.13309],
    ["2020-01-01T00:00:00+00:00", 660, 86.64014],
    ["2020-01-01T00:00:00+00:00", 692.3, 68747.58054],
    ["2020-01-01T00:00:00+00:00", 722.1, 388648.24717],
    ["2020-01-01T00:00:00+00:00", 756, 1588292.21208],
    ["2020-01-01T00:00:00+00:00", 770.5, 2561970.36517],
    ["2021-01-01T00:00:00+00:00", 660, 92.33654],
    ["2021-01-01T00:00:00+00:00", 692.3, 68097.35527],
    ["2021-01-01T00:00:00+00:00", 722.1, 386630.6157],
    ["2021-01-01T00:00:00+00:00", 756, 1582448.66],
    ["2021-01-01T00:00:00+00:00", 770.5, 2554719.665],
]


rating_set_1_list_data: Optional[list[list[Any]]] = None
rating_set_1_ts_data: Optional[list[list[Any]]] = None
rating_set_2_list_data: Optional[list[list[Any]]] = None
rating_set_2_ts_data: Optional[list[list[Any]]] = None


def generate_local_rating_set_3_ind_params_list_data() -> list[list[Any]]:
    global rating_set_1_list_data
    if rating_set_1_list_data is None:
        rating_set_1_list_data = []
        timestrs, counts, openings, elevations, expected_flows = list(
            map(list, zip(*rating_set_1_data))
        )
        timestrs, counts, openings, elevations, expected_flows = list(
            map(list, zip(*rating_set_1_data))
        )
        num_unique_times = len(set(timestrs))
        num_each_time = int(len(rating_set_1_data) / num_unique_times)
        data = sorted(rating_set_1_data)
        for i in range(num_each_time):
            timestrs = []
            counts = []
            openings = []
            elevations = []
            expected_flows = []
            for j in range(num_unique_times):
                offset = j * num_each_time + i
                timestrs.append(data[offset][0])
                counts.append(data[offset][1])
                openings.append(data[offset][2])
                elevations.append(data[offset][3])
                expected_flows.append(data[offset][4])
            rating_set_1_list_data.append(
                [timestrs, counts, openings, elevations, expected_flows]
            )
    return rating_set_1_list_data


def generate_local_rating_set_3_ind_params_ts_data() -> list[list[Any]]:
    global rating_set_1_ts_data
    if rating_set_1_ts_data is None:
        with open(rating_set_3_ind_params_file_name) as f:
            rating_set_1 = LocalRatingSet.from_xml(f.read())
        rating_set_1_ts_data = []
        timestrs, counts, openings, elevations, expected_flows = list(
            map(list, zip(*rating_set_1_data))
        )
        location_name = rating_set_1.specification.location.name
        num_unique_times = len(set(timestrs))
        num_each_time = int(len(rating_set_1_data) / num_unique_times)
        data = sorted(rating_set_1_data)
        for i in range(num_each_time):
            timestrs = []
            counts = []
            openings = []
            elevations = []
            expected_flows = []
            for j in range(num_unique_times):
                offset = j * num_each_time + i
                timestrs.append(data[offset][0])
                counts.append(data[offset][1])
                openings.append(data[offset][2])
                elevations.append(data[offset][3])
                expected_flows.append(data[offset][4])

            counts_ts = TimeSeries(
                name=f"{location_name}.Count-Sluice_Gates.Inst.1Day.0.Test",
                times=timestrs,
                values=counts,
                qualities=0,
            )
            openings_ts = TimeSeries(
                name=f"{location_name}.Opening-Sluice_Gates.Inst.1Day.0.Test",
                times=timestrs,
                values=openings,
                qualities=0,
            )
            elevations_ts = TimeSeries(
                name=f"{location_name}.Elev-Pool.Inst.1Day.0.Test",
                times=timestrs,
                values=elevations,
                qualities=0,
            )
            vdi = rating_set_1.vertical_datum_info
            if vdi:
                elevations_ts.iset_vertical_datum_info(str(vdi))
            rating_set_1_ts_data.append(
                [counts_ts, openings_ts, elevations_ts, expected_flows]
            )
    return rating_set_1_ts_data


def generate_local_rating_set_1_ind_param_list_data() -> list[list[Any]]:
    global rating_set_2_list_data
    if rating_set_2_list_data is None:
        rating_set_2_list_data = []
        timestrs, elevations, expected_stors = list(map(list, zip(*rating_set_2_data)))
        num_unique_times = len(set(timestrs))
        num_each_time = int(len(rating_set_2_data) / num_unique_times)
        data = sorted(rating_set_2_data)
        for i in range(num_each_time):
            timestrs = []
            elevations = []
            expected_stors = []
            for j in range(num_unique_times):
                offset = j * num_each_time + i
                timestrs.append(data[offset][0])
                elevations.append(data[offset][1])
                expected_stors.append(data[offset][2])
            rating_set_2_list_data.append([timestrs, elevations, expected_stors])
    return rating_set_2_list_data


def generate_local_rating_set_1_ind_param_ts_data() -> list[list[Any]]:
    global rating_set_2_ts_data
    if rating_set_2_ts_data is None:
        with open("test/resources/rating/local_rating_set_1_ind_param.xml") as f:
            rating_set_2 = LocalRatingSet.from_xml(f.read())
        rating_set_2_ts_data = []
        timestrs, elevations, expected_stors = list(map(list, zip(*rating_set_2_data)))
        location_name = rating_set_2.specification.location.name
        num_unique_times = len(set(timestrs))
        num_each_time = int(len(rating_set_2_data) / num_unique_times)
        data = sorted(rating_set_2_data)
        for i in range(num_each_time):
            timestrs = []
            elevations = []
            expected_stors = []
            for j in range(num_unique_times):
                offset = j * num_each_time + i
                timestrs.append(data[offset][0])
                elevations.append(data[offset][1])
                expected_stors.append(data[offset][2])

            elevations_ts = TimeSeries(
                name=f"{location_name}.Elev-Pool.Inst.1Day.0.Test",
                times=timestrs,
                values=elevations,
                qualities=0,
            )
            vdi = rating_set_2.vertical_datum_info
            if vdi:
                elevations_ts.iset_vertical_datum_info(str(vdi))
            rating_set_2_ts_data.append([elevations_ts, expected_stors])
    return rating_set_2_ts_data


@pytest.mark.parametrize(
    "timestr, count, opening, elevation, expected_flow",
    rating_set_1_data,
)
def test_local_rating_set_3_ind_params_individual(
    rating_set_3_ind_params: LocalRatingSet,
    timestr: str,
    count: float,
    opening: float,
    elevation: float,
    expected_flow: float,
) -> None:
    rated_flow = rating_set_3_ind_params.rate(
        [count, opening, elevation],
        times=datetime.fromisoformat(timestr),
        units="unit,ft,ft;cfs",
    )
    assert np.isclose(expected_flow, rated_flow)


@pytest.mark.parametrize(
    "timestrs, counts, openings, elevations, expected_flows",
    generate_local_rating_set_3_ind_params_list_data(),
)
def test_local_rating_set_3_ind_params_list(
    rating_set_3_ind_params: LocalRatingSet,
    timestrs: list[str],
    counts: list[float],
    openings: list[float],
    elevations: list[float],
    expected_flows: list[float],
) -> None:
    rated_flows = rating_set_3_ind_params.rate(
        [counts, openings, elevations],
        times=list(map(datetime.fromisoformat, timestrs)),
        units="unit,ft,ft;cfs",
    )
    assert np.allclose(expected_flows, rated_flows)


@pytest.mark.parametrize(
    "counts_ts, openings_ts, elevations_ts, expected_flows",
    generate_local_rating_set_3_ind_params_ts_data(),
)
def test_local_rating_set_3_ind_params_ts(
    rating_set_3_ind_params: LocalRatingSet,
    counts_ts: TimeSeries,
    openings_ts: TimeSeries,
    elevations_ts: TimeSeries,
    expected_flows: list[float],
) -> None:
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_flows = rating_set_3_ind_params.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    assert np.allclose(expected_flows, rated_flows.values)
    # --------------------------------------------------- #
    # test with different units and native vertical datum #
    # --------------------------------------------------- #
    rated_flows = rating_set_3_ind_params.rate(
        [counts_ts, openings_ts.to("m"), elevations_ts.to("m").to("NAVD-88")],
        units="cfs",
        vertical_datum="NAVD-88",
    )
    assert np.allclose(expected_flows, rated_flows.values)


@pytest.mark.parametrize(
    "timestr, elevation, expected_stor",
    rating_set_2_data,
)
def test_local_rating_set_1_ind_param_individual(
    rating_set_1_ind_param: LocalRatingSet,
    timestr: str,
    elevation: float,
    expected_stor: float,
) -> None:
    rated_stor = rating_set_1_ind_param.rate(
        [elevation],
        times=datetime.fromisoformat(timestr),
        units="ft;ac-ft",
    )
    assert np.isclose(expected_stor, rated_stor)


@pytest.mark.parametrize(
    "timestrs, elevations, expected_stors",
    generate_local_rating_set_1_ind_param_list_data(),
)
def test_local_rating_set_1_ind_param_list(
    rating_set_1_ind_param: LocalRatingSet,
    timestrs: list[str],
    elevations: list[float],
    expected_stors: list[float],
) -> None:
    rated_stors = rating_set_1_ind_param.rate(
        [elevations],
        times=list(map(datetime.fromisoformat, timestrs)),
        units="ft;ac-ft",
    )
    assert np.allclose(expected_stors, rated_stors)


@pytest.mark.parametrize(
    "elevations_ts, expected_stors", generate_local_rating_set_1_ind_param_ts_data()
)
def test_local_rating_set_1_ind_param_ts(
    rating_set_1_ind_param: LocalRatingSet,
    elevations_ts: TimeSeries,
    expected_stors: list[float],
) -> None:
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_stors = rating_set_1_ind_param.rate([elevations_ts], units="ac-ft")
    assert np.allclose(expected_stors, rated_stors.values)
    # --------------------------------------------------------------------------------- #
    # perform the reverse rating to make sure it doesn't blow up, but 2-D interpolation #
    # (time and elevation being the dimensions) is not generally inversible             #
    # --------------------------------------------------------------------------------- #
    reverse_rated_elevs = rating_set_1_ind_param.reverse_rate(rated_stors, units="ft")
    # --------------------------------------------------- #
    # test with different units and native vertical datum #
    # --------------------------------------------------- #
    rated_stors = rating_set_1_ind_param.rate(
        elevations_ts.to("m").to("NAVD-88"), units="mcm"
    )
    acft_to_mcm = UnitQuantity("ac-ft").to("mcm").magnitude
    assert np.allclose(
        list(map(lambda v: v * acft_to_mcm, expected_stors)), rated_stors.values
    )
    # --------------------------------------------------------------------------------- #
    # perform the reverse rating to make sure it doesn't blow up, but 2-D interpolation #
    # (time and elevation being the dimensions) is not generally inversible             #
    # --------------------------------------------------------------------------------- #
    reverse_rated_elevs = rating_set_1_ind_param.reverse_rate(
        rated_stors, units="m", vertical_datum="NAVD-88"
    )


@pytest.mark.parametrize(
    "counts_ts, openings_ts, elevations_ts, expected_flows",
    generate_local_rating_set_3_ind_params_ts_data(),
)
def test_load_methods_with_cwms(
    counts_ts: TimeSeries,
    openings_ts: TimeSeries,
    elevations_ts: TimeSeries,
    expected_flows: list[float],
) -> None:
    global _db, _rs_reference_cwms, _rs_eager_cwms, _rs_lazy_cwms
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    if _db is None:
        _db = CwmsDataStore.open()
    rating_id = "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    if _rs_reference_cwms is None:
        _rs_reference_cwms = cast(
            AbstractRatingSet, _db.retrieve(rating_id, method="REFERENCE")
        )
    if _rs_eager_cwms is None:
        _rs_eager_cwms = cast(
            AbstractRatingSet, _db.retrieve(rating_id, method="EAGER")
        )
    if _rs_lazy_cwms is None:
        _rs_lazy_cwms = cast(AbstractRatingSet, _db.retrieve(rating_id, method="LAZY"))
    rated_flows_reference = _rs_reference_cwms.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    rated_flows_eager = _rs_eager_cwms.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    assert np.allclose(
        rated_flows_reference.values, rated_flows_eager.values, equal_nan=True
    )
    rated_flows_lazy = _rs_lazy_cwms.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    assert np.allclose(
        rated_flows_reference.values, rated_flows_lazy.values, equal_nan=True
    )


@pytest.mark.parametrize(
    "counts_ts, openings_ts, elevations_ts, expected_flows",
    generate_local_rating_set_3_ind_params_ts_data(),
)
def test_load_methods_with_dss(
    counts_ts: TimeSeries,
    openings_ts: TimeSeries,
    elevations_ts: TimeSeries,
    expected_flows: list[float],
) -> None:
    global _dss, _rs_eager_dss, _rs_lazy_dss
    DssDataStore.set_message_level(0)
    if _dss is None:
        _dss = DssDataStore.open(dss_file_name, read_only=False)
        for rating_set_file_name in (
            rating_set_3_ind_params_file_name,
            rating_set_1_ind_param_file_name,
            rating_set_large_file_name,
        ):
            with open(rating_set_file_name) as f:
                _dss.store(LocalRatingSet.from_xml(f.read()))
    rating_id = "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    if _rs_eager_dss is None:
        _rs_eager_dss = cast(
            AbstractRatingSet, _dss.retrieve(rating_id, office="SWT", method="EAGER")
        )
    if _rs_lazy_dss is None:
        _rs_lazy_dss = cast(
            AbstractRatingSet, _dss.retrieve(rating_id, office="SWT", method="LAZY")
        )
    rated_flows_eager = _rs_eager_dss.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    assert np.allclose(expected_flows, rated_flows_eager.values, equal_nan=True)
    rated_flows_lazy = _rs_lazy_dss.rate(
        [counts_ts, openings_ts, elevations_ts], units="cfs"
    )
    assert np.allclose(expected_flows, rated_flows_lazy.values, equal_nan=True)



@pytest.mark.parametrize(
    "rating_set_file_name",
    [
        rating_set_3_ind_params_file_name,
        rating_set_1_ind_param_file_name,
        rating_set_large_file_name,
    ],
)
def test_dss_store_retrieve(rating_set_file_name: str) -> None:
    global _dss
    DssDataStore.set_message_level(1)
    if _dss is None:
        _dss = DssDataStore.open(dss_file_name, read_only=False)
    with open(rating_set_file_name) as f:
        xml1 = f.read()
    rs1 = LocalRatingSet.from_xml(xml1)
    _dss.store(rs1)
    rs2 = _dss.retrieve(
        rs1.specification.name, office=rs1.template.office, method="EAGER"
    )
    xml2 = rs2.to_xml()
    # -------------------------- #
    # format xml1 for comparison #
    # -------------------------- #
    # remove opening <?xml version="1.0" encoding="utf-8"?> line
    if xml1.startswith("<?xml"):
        xml1 = xml1.split("?>")[1].strip()
    # remove null vertical datum offsets
    xml1 = re.sub(
        r"<offset .+?>\s*<to-datum>.+?</to-datum>\s*<value>0.0</value>\s*</offset>\s*",
        "",
        xml1,
    )
    # parse and re-generate
    xml1 = etree.tostring(etree.fromstring(xml1), pretty_print=True).decode()
    # change indentations for comparison
    lines = xml1[:1000].split("\n")
    indention = lines[1][:lines[1].find("<")]
    xml1 = replace_indent(xml1, indention, "  ")
    # ------------------------- #
    # finally do the comparison #
    # ------------------------- #
    assert xml2 == xml1, rating_set_file_name


def test_dss_catalog() -> None:
    global _dss
    rating_sets: list[LocalRatingSet] = []
    DssDataStore.set_message_level(1)
    if _dss is None:
        _dss = DssDataStore.open(dss_file_name, read_only=False)
    for rating_set_file_name in (
        rating_set_3_ind_params_file_name,
        rating_set_1_ind_param_file_name,
        rating_set_large_file_name,
    ):
        with open(rating_set_file_name) as f:
            rs = LocalRatingSet.from_xml(f.read())
            rating_sets.append(rs)
            _dss.store(rs)
    # --------------------------------------- #
    # catalog rating templates as identifiers #
    # --------------------------------------- #
    catalog = _dss.catalog("RATING_TEMPLATE", office="SWT")
    assert len(catalog) == 3
    assert (
        "Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard"
    ) in catalog
    assert "Elev;Stor.Linear" in catalog
    assert "Stage;Flow.Linear" in catalog
    # -------------------------------------------- #
    # catalog rating specifications as identifiers #
    # -------------------------------------------- #
    catalog = _dss.catalog("RATING_SPECIFICATION", office="SWT")
    assert len(catalog) == 3
    assert (
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    ) in catalog
    assert "KEYS.Elev;Stor.Linear.Production" in catalog
    assert "BARN.Stage;Flow.Linear.Step" in catalog
    # ------------------------------ #
    # catalog ratings as identifiers #
    # ------------------------------ #
    catalog = _dss.catalog("RATING", office="SWT")
    assert len(catalog) == 3
    assert (
        "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    ) in catalog
    assert "KEYS.Elev;Stor.Linear.Production" in catalog
    assert "BARN.Stage;Flow.Linear.Step" in catalog
    
    # ------------------------------------- #
    # catalog rating templates as pathnames #
    # ------------------------------------- #
    catalog = _dss.catalog("RATING_TEMPLATE", office="SWT", pathnames=True)
    assert len(catalog) == 3
    assert (
        "/SWT//Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Template/Standard//"
    ) in catalog
    assert "/SWT//Elev;Stor/Rating-Template/Linear//" in catalog
    assert "/SWT//Stage;Flow/Rating-Template/Linear//" in catalog
    # ------------------------------------------ #
    # catalog rating specifications as pathnames #
    # ------------------------------------------ #
    catalog = _dss.catalog("RATING_SPECIFICATION", office="SWT", pathnames=True)
    assert len(catalog) == 3
    assert (
        "/SWT/COUN/Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Specification/Standard/Production/"
    ) in catalog
    assert "/SWT/KEYS/Elev;Stor/Rating-Specification/Linear/Production/" in catalog
    assert "/SWT/BARN/Stage;Flow/Rating-Specification/Linear/Step/" in catalog
    # ---------------------------- #
    # catalog ratings as pathnames #
    # ---------------------------- #
    catalog = _dss.catalog("RATING", office="SWT", pathnames=True)
    assert len(catalog) == 73
    for effective_time in ["2012-04-26T05:00:00Z", "2012-04-27T05:00:00Z"] :
        assert (
            f"/SWT/COUN/Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Body-{effective_time}/Standard/Production/"
        ) in catalog
    for effective_time in [
        "2009-01-14T06:00:00Z",
        "2011-10-19T05:00:00Z",
        "2020-08-01T05:00:00Z",
    ]:
        assert (
            f"/SWT/KEYS/Elev;Stor/Rating-Body-{effective_time}/Linear/Production/"
            in catalog
        )
    for effective_time in [
        "2023-10-27T18:25:00Z",
        "2018-10-22T15:30:00Z",
        "2019-03-12T17:45:00Z",
        "2019-03-14T18:45:00Z",
        "2019-04-22T17:35:00Z",
        "2019-06-06T16:00:00Z",
        "2019-09-04T18:40:00Z",
        "2019-09-05T18:40:00Z",
        "2019-10-02T17:05:00Z",
        "2019-10-03T03:00:00Z",
        "2020-03-04T05:59:00Z",
        "2020-03-04T12:00:00Z",
        "2020-06-19T16:10:00Z",
        "2020-07-27T15:10:00Z",
        "2020-07-27T22:00:00Z",
        "2020-07-29T05:59:00Z",
        "2020-08-31T13:51:00Z",
        "2020-10-16T05:59:00Z",
        "2020-11-19T19:10:00Z",
        "2021-01-07T19:34:00Z",
        "2021-02-27T15:00:00Z",
        "2021-03-12T05:59:00Z",
        "2021-03-17T19:00:00Z",
        "2021-06-30T18:00:00Z",
        "2021-07-27T05:59:00Z",
        "2021-08-03T22:55:00Z",
        "2021-10-26T17:30:00Z",
        "2021-10-28T19:55:00Z",
        "2021-11-01T23:40:00Z",
        "2021-11-22T23:30:00Z",
        "2022-02-17T20:40:00Z",
        "2022-03-03T00:25:00Z",
        "2022-03-31T01:25:00Z",
        "2022-04-25T20:30:00Z",
        "2022-07-18T19:35:00Z",
        "2022-07-27T18:55:00Z",
        "2022-08-09T00:40:00Z",
        "2022-08-27T00:05:00Z",
        "2022-09-28T01:50:00Z",
        "2022-10-24T19:30:00Z",
        "2022-10-26T23:35:00Z",
        "2022-12-06T23:30:00Z",
        "2023-02-15T02:35:00Z",
        "2023-03-16T00:05:00Z",
        "2023-05-23T17:40:00Z",
        "2023-06-13T22:30:00Z",
        "2023-08-18T20:20:00Z",
        "2023-06-16T21:30:00Z",
        "2023-06-20T23:25:00Z",
        "2023-06-22T22:45:00Z",
        "2023-07-28T19:25:00Z",
        "2023-10-17T00:00:00Z",
        "2023-10-20T20:15:00Z",
        "2023-12-02T00:40:00Z",
        "2024-03-04T23:15:00Z",
        "2024-03-19T01:25:00Z",
        "2024-04-19T17:50:00Z",
        "2024-07-31T00:15:00Z",
        "2024-08-02T16:40:00Z",
        "2024-08-16T00:32:00Z",
        "2024-08-19T21:15:00Z",
        "2024-11-05T21:50:00Z",
        "2025-02-13T20:00:00Z",
        "2025-03-04T21:55:00Z",
        "2025-03-05T20:00:00Z",
        "2025-04-25T21:30:00Z",
        "2025-06-19T01:05:00Z",
        "2025-07-25T21:20:00Z",
    ]:
        assert (
            f"/SWT/BARN/Stage;Flow/Rating-Body-{effective_time}/Linear/Step/"
            in catalog
        )


if __name__ == "__main__":
    test_dss_catalog()
