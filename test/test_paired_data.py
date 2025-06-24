from test.shared import dataset_from_file
from typing import Generator, cast

import numpy as np
import pytest

import hec
from hec import DssDataStore


@pytest.fixture
def dss() -> Generator[DssDataStore, None, None]:
    dss_file_name = "test/resources/rating/Paired_Data.dss"
    dssds: hec.datastore.DssDataStore = hec.datastore.DssDataStore.open(dss_file_name)
    yield dssds
    dssds.close()


@pytest.mark.parametrize(
    "pd_name, input_str, expected_str",
    dataset_from_file("resources/rating/Paired_Data.tsv"),
)
def test_paired_data(
    dss: DssDataStore, pd_name: str, input_str: str, expected_str: str
) -> None:
    input_ts_names = eval(input_str)
    expected_ts_names = eval(expected_str)
    dsspd: hec.rating.PairedData = dss.retrieve(pd_name)
    input_ts: list[hec.TimeSeries] = [
        dss.retrieve(ts_name, rounding="9999999993") for ts_name in input_ts_names
    ]
    expected_ts: list[hec.TimeSeries] = [
        dss.retrieve(ts_name, rounding="9999999992") for ts_name in expected_ts_names
    ]
    if len(input_ts) == 1:
        if len(expected_ts) == 1:
            # --------------------------- #
            # single input, single output #
            # --------------------------- #
            rated_ts = cast(hec.TimeSeries, dsspd.rate(input_ts[0]))
            if dsspd._dep_log and not dsspd._ind_log:
                # ---------------------------------------------- #
                # java paired data only does lin-lin and log-log #
                # ---------------------------------------------- #
                assert expected_ts[0].data is not None and not expected_ts[0].data.empty
                expected_ts[0].data["value"] = dsspd.rate(input_ts[0].values)
            # -------------------------------------------------------------------------------------- #
            # don't compare first and last values because java extrapolates while python sets to nan #
            # -------------------------------------------------------------------------------------- #
            assert np.allclose(
                expected_ts[0].values[1:-1], rated_ts.values[1:-1], equal_nan=True
            )
        else:
            # ----------------------------------------------------- #
            # single input, multiple outputs (e.g., elev-stor-area) #
            # ----------------------------------------------------- #
            for ts in expected_ts:
                print(ts)
                rated_ts = cast(hec.TimeSeries, dsspd.rate(input_ts[0], label = ts.parameter.name))
                assert np.allclose(
                    ts.values[1:-1], rated_ts.values[1:-1], equal_nan=True
                )

if __name__ == "__main__":
    dssf: hec.datastore.DssDataStore = hec.datastore.DssDataStore.open(
        "test/resources/rating/Paired_Data.dss"
    )
    dsspd: hec.rating.PairedData = dssf.retrieve(
        "/CARLYLE LAKE/POOL-AREA CAPACITY/ELEV-STOR-AREA////"
    )
    input_ts: hec.TimeSeries = dssf.retrieve(
        "/CARLYLE LAKE/POOL-AREA CAPACITY/ELEV//1Hour/Test/", rounding="9999999993"
    )
    expected_ts: hec.TimeSeries = dssf.retrieve(
        "/CARLYLE LAKE/POOL-AREA CAPACITY/STOR//1Hour/Test/", rounding="9999999992"
    )
    rated_ts: hec.TimeSeries = cast(hec.TimeSeries, dsspd.rate(input_ts, label=expected_ts.parameter.name))
    if dsspd._dep_log and not dsspd._ind_log:
        # ---------------------------------------------------------------------------------- #
        # java paired data only does lin-lin and log-log, so modify to lin-log manually here #
        # ---------------------------------------------------------------------------------- #
        assert expected_ts.data is not None and not expected_ts.data.empty
        expected_ts.data["value"] = dsspd.rate(input_ts.values)
    for v1, v2 in list(zip(expected_ts.values, rated_ts.values)):
        print(f"{v1}\t{v2}\t{np.isclose(v1, v2, equal_nan=True)}")
