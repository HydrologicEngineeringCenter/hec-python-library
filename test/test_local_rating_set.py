import os
import sys
import warnings
from datetime import datetime
from typing import Any, Optional, cast

import numpy as np
import pytest

from hec import CwmsDataStore, TimeSeries, UnitQuantity
from hec.rating import AbstractRatingSet, LocalRatingSet
from hec.shared import import_cwms

_db: Optional[CwmsDataStore] = None
_rs_reference: Optional[AbstractRatingSet] = None
_rs_eager: Optional[AbstractRatingSet] = None
_rs_lazy: Optional[AbstractRatingSet] = None


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
def rating_set_1() -> LocalRatingSet:
    with open("test/resources/rating/local_rating_set_1.xml") as f:
        return LocalRatingSet.from_xml(f.read())


@pytest.fixture
def rating_set_2() -> LocalRatingSet:
    with open("test/resources/rating/local_rating_set_2.xml") as f:
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


def generate_local_rating_set_1_list_data() -> list[list[Any]]:
    test_data = []
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
        test_data.append([timestrs, counts, openings, elevations, expected_flows])
    return test_data


def generate_local_rating_set_1_ts_data() -> list[list[Any]]:
    with open("test/resources/rating/local_rating_set_1.xml") as f:
        rating_set_1 = LocalRatingSet.from_xml(f.read())
    test_data = []
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
        test_data.append([counts_ts, openings_ts, elevations_ts, expected_flows])
    return test_data


def generate_local_rating_set_2_list_data() -> list[list[Any]]:
    test_data = []
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
        test_data.append([timestrs, elevations, expected_stors])
    return test_data


def generate_local_rating_set_2_ts_data() -> list[list[Any]]:
    with open("test/resources/rating/local_rating_set_2.xml") as f:
        rating_set_2 = LocalRatingSet.from_xml(f.read())
    test_data = []
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
        test_data.append([elevations_ts, expected_stors])
    return test_data


@pytest.mark.parametrize(
    "timestr, count, opening, elevation, expected_flow",
    rating_set_1_data,
)
def test_local_rating_set_1_individual(
    rating_set_1: LocalRatingSet,
    timestr: str,
    count: float,
    opening: float,
    elevation: float,
    expected_flow: float,
) -> None:
    rated_flow = rating_set_1.rate_values(
        [[count], [opening], [elevation]],
        [datetime.fromisoformat(timestr)],
        "unit,ft,ft;cfs",
    )[0]
    assert np.isclose(expected_flow, rated_flow)


@pytest.mark.parametrize(
    "timestrs, counts, openings, elevations, expected_flows",
    generate_local_rating_set_1_list_data(),
)
def test_local_rating_set_1_list(
    rating_set_1: LocalRatingSet,
    timestrs: list[str],
    counts: list[float],
    openings: list[float],
    elevations: list[float],
    expected_flows: list[float],
) -> None:
    rated_flows = rating_set_1.rate_values(
        [counts, openings, elevations],
        list(map(datetime.fromisoformat, timestrs)),
        "unit,ft,ft;cfs",
    )
    assert np.allclose(expected_flows, rated_flows)


@pytest.mark.parametrize(
    "counts_ts, openings_ts, elevations_ts, expected_flows",
    generate_local_rating_set_1_ts_data(),
)
def test_local_rating_set_1_ts(
    rating_set_1: LocalRatingSet,
    counts_ts: TimeSeries,
    openings_ts: TimeSeries,
    elevations_ts: TimeSeries,
    expected_flows: list[float],
) -> None:
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_flows = rating_set_1.rate_time_series(
        [counts_ts, openings_ts, elevations_ts], unit="cfs"
    )
    assert np.allclose(expected_flows, rated_flows.values)
    # --------------------------------------------------- #
    # test with different units and native vertical datum #
    # --------------------------------------------------- #
    rated_flows = rating_set_1.rate_time_series(
        [counts_ts, openings_ts.to("m"), elevations_ts.to("m").to("NAVD-88")],
        unit="cfs",
        vertical_datum="NAVD-88",
    )
    assert np.allclose(expected_flows, rated_flows.values)


@pytest.mark.parametrize(
    "timestr, elevation, expected_stor",
    rating_set_2_data,
)
def test_local_rating_set_2_individual(
    rating_set_2: LocalRatingSet,
    timestr: str,
    elevation: float,
    expected_stor: float,
) -> None:
    rated_stor = rating_set_2.rate_values(
        [[elevation]],
        [datetime.fromisoformat(timestr)],
        "ft;ac-ft",
    )[0]
    assert np.isclose(expected_stor, rated_stor)


@pytest.mark.parametrize(
    "timestrs, elevations, expected_stors", generate_local_rating_set_2_list_data()
)
def test_local_rating_set_2_list(
    rating_set_2: LocalRatingSet,
    timestrs: list[str],
    elevations: list[float],
    expected_stors: list[float],
) -> None:
    rated_stors = rating_set_2.rate_values(
        [elevations],
        list(map(datetime.fromisoformat, timestrs)),
        "ft;ac-ft",
    )
    assert np.allclose(expected_stors, rated_stors)


@pytest.mark.parametrize(
    "elevations_ts, expected_stors", generate_local_rating_set_2_ts_data()
)
def test_local_rating_set_2_ts(
    rating_set_2: LocalRatingSet,
    elevations_ts: TimeSeries,
    expected_stors: list[float],
) -> None:
    # ------------------------------------------------ #
    # test with rating units and native vertical datum #
    # ------------------------------------------------ #
    rated_stors = rating_set_2.rate_time_series([elevations_ts], unit="ac-ft")
    assert np.allclose(expected_stors, rated_stors.values)
    # --------------------------------------------------------------------------------- #
    # perform the reverse rating to make sure it doesn't blow up, but 2-D interpolation #
    # (time and elevation being the dimensions) is not generally inversible             #
    # --------------------------------------------------------------------------------- #
    reverse_rated_elevs = rating_set_2.reverse_rate_time_series(rated_stors, unit="ft")
    # --------------------------------------------------- #
    # test with different units and native vertical datum #
    # --------------------------------------------------- #
    rated_stors = rating_set_2.rate_time_series(
        elevations_ts.to("m").to("NAVD-88"), unit="mcm"
    )
    acft_to_mcm = UnitQuantity("ac-ft").to("mcm").magnitude
    assert np.allclose(
        list(map(lambda v: v * acft_to_mcm, expected_stors)), rated_stors.values
    )
    # --------------------------------------------------------------------------------- #
    # perform the reverse rating to make sure it doesn't blow up, but 2-D interpolation #
    # (time and elevation being the dimensions) is not generally inversible             #
    # --------------------------------------------------------------------------------- #
    reverse_rated_elevs = rating_set_2.reverse_rate_time_series(
        rated_stors, unit="m", vertical_datum="NAVD-88"
    )


@pytest.mark.parametrize(
    "counts_ts, openings_ts, elevations_ts, expected_flows",
    generate_local_rating_set_1_ts_data(),
)
def test_load_from_cwms(
    counts_ts: TimeSeries,
    openings_ts: TimeSeries,
    elevations_ts: TimeSeries,
    expected_flows: list[float],
) -> None:
    global _db, _rs_reference, _rs_eager, _rs_lazy
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    if _db is None:
        _db = CwmsDataStore.open()
    rating_id = "COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production"
    if _rs_reference is None:
        _rs_reference = cast(
            AbstractRatingSet, _db.retrieve(rating_id, method="REFERENCE")
        )
    if _rs_eager is None:
        _rs_eager = cast(AbstractRatingSet, _db.retrieve(rating_id, method="EAGER"))
    if _rs_lazy is None:
        _rs_lazy = cast(AbstractRatingSet, _db.retrieve(rating_id, method="LAZY"))
    rated_flows_reference = _rs_reference.rate_time_series(
        [counts_ts, openings_ts, elevations_ts], unit="cfs"
    )
    rated_flows_eager = _rs_eager.rate_time_series(
        [counts_ts, openings_ts, elevations_ts], unit="cfs"
    )
    assert np.allclose(
        rated_flows_reference.values, rated_flows_eager.values, equal_nan=True
    )
    rated_flows_lazy = _rs_lazy.rate_time_series(
        [counts_ts, openings_ts, elevations_ts], unit="cfs"
    )
    assert np.allclose(
        rated_flows_reference.values, rated_flows_lazy.values, equal_nan=True
    )
