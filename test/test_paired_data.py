import re
from test.shared import dataset_from_file
from typing import Generator, cast

import numpy as np
import pandas as pd
import pytest

import hec
from hec import DssDataStore
from hec.rounding import UsgsRounder


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
    if pd_name in [
        "/Lake Shelbyville/Tainters-Gate Rating/Elev-Flow/PairedValuesExt///",
        "/Carlyle Lake/Tainters-Gate Rating/Elev-Flow/PairedValuesExt///",
    ]:
        with pytest.raises(
            hec.rating.PairedDataException,
            match=re.escape(
                "Cannot have multiple labels with the same (case insenitive) value"
            ),
        ):
            dsspd: hec.rating.PairedData = dss.retrieve(pd_name)
        return
    dsspd = dss.retrieve(pd_name)
    assert dsspd.copy() == dsspd
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
            # -------------------- #
            # check reverse rating #
            # -------------------- #
            reverse_rated_ts = cast(hec.TimeSeries, dsspd.reverse_rate(rated_ts))
            if not np.allclose(
                input_ts[0].values[1:-1], reverse_rated_ts.values[1:-1], equal_nan=True
            ):
                # ---------------------------------------------------- #
                # reverse rating inexact values can magnify difference #
                # ---------------------------------------------------- #
                count_true = count_total = 0
                for v1, v2 in list(
                    zip(input_ts[0].values[1:-1], reverse_rated_ts.values[1:-1])
                ):
                    count_total += 1
                    count_true += 1 if np.isclose(v1, v2, equal_nan=True) else 0
                true_fraction = count_true / count_total
                assert 0.9 <= true_fraction
                sum1 = sum(
                    cast(pd.DataFrame, input_ts[0].data)["value"]
                    .copy()
                    .dropna()
                    .to_list()[1:-1]
                )
                if sum1 > 0:
                    sum2 = sum(
                        cast(pd.DataFrame, reverse_rated_ts.data)["value"]
                        .copy()
                        .dropna()
                        .to_list()[1:-1]
                    )
                    diff_fraction = abs((sum2 - sum1) / sum1)
                    assert 0.1 >= diff_fraction
        else:
            # ----------------------------------------------------- #
            # single input, multiple outputs (e.g., elev-stor-area) #
            # ----------------------------------------------------- #
            for ts in expected_ts:
                rated_ts = cast(
                    hec.TimeSeries, dsspd.rate(input_ts[0], label=ts.parameter.name)
                )
                assert np.allclose(
                    ts.values[1:-1], rated_ts.values[1:-1], equal_nan=True
                )
                # -------------------- #
                # check reverse rating #
                # -------------------- #
                if (
                    dsspd.name
                    == "/LAKE SHELBYVILLE/POOL-AREA CAPACITY/ELEV-STOR-AREA////"
                    and ts.name
                    == "/LAKE SHELBYVILLE/POOL-AREA CAPACITY/AREA//1Hour/Test/"
                ):
                    with pytest.raises(
                        hec.rating.PairedDataException,
                        match="are not in increasing order",
                    ):
                        reverse_rated_ts = cast(
                            hec.TimeSeries,
                            dsspd.reverse_rate(rated_ts, label=ts.parameter.name),
                        )
                    continue
                reverse_rated_ts = cast(
                    hec.TimeSeries,
                    dsspd.reverse_rate(rated_ts, label=ts.parameter.name),
                )
                if not np.allclose(
                    input_ts[0].values[1:-1],
                    reverse_rated_ts.values[1:-1],
                    equal_nan=True,
                ):
                    # ---------------------------------------------------- #
                    # reverse rating inexact values can magnify difference #
                    # ---------------------------------------------------- #
                    count_true = count_total = 0
                    for v1, v2 in list(
                        zip(input_ts[0].values[1:-1], reverse_rated_ts.values[1:-1])
                    ):
                        count_total += 1
                        count_true += 1 if np.isclose(v1, v2, equal_nan=True) else 0
                    true_fraction = count_true / count_total
                    assert 0.9 <= true_fraction
                    sum1 = sum(
                        cast(pd.DataFrame, input_ts[0].data)["value"]
                        .copy()
                        .dropna()
                        .to_list()[1:-1]
                    )
                    if sum1 > 0:
                        sum2 = sum(
                            cast(pd.DataFrame, reverse_rated_ts.data)["value"]
                            .copy()
                            .dropna()
                            .to_list()[1:-1]
                        )
                        diff_fraction = abs((sum2 - sum1) / sum1)
                        assert 0.1 >= diff_fraction
    elif len(input_ts) == 2:
        assert len(expected_ts) == 1
        # --------------------------------------------- #
        # gate rating with two inputs and single output #
        # --------------------------------------------- #
        rounder = UsgsRounder("9999999992")
        rated_ts = cast(hec.TimeSeries, dsspd.rate(input_ts))
        cast(pd.DataFrame, rated_ts.data)["value"] = rounder.round_f(
            cast(pd.DataFrame, rated_ts.data)["value"].to_list()
        )
        rated_ts = rated_ts[:-1]
        if not np.allclose(
            expected_ts[0].values[1:-1], rated_ts.values[1:-1], equal_nan=True
        ):
            # --------------------------------------------------------------------------------- #
            # these ratings can have more variance from the Java ones than single value ratings #
            # --------------------------------------------------------------------------------- #
            count_true = count_total = 0
            for v1, v2 in list(zip(expected_ts[0].values[1:-1], rated_ts.values[1:-1])):
                count_total += 1
                count_true += 1 if np.isclose(v1, v2, equal_nan=True) else 0
            true_fraction = count_true / count_total
            assert 0.75 <= true_fraction
            sum1 = sum(
                cast(pd.DataFrame, expected_ts[0].data)["value"]
                .copy()
                .dropna()
                .to_list()[1:-1]
            )
            if sum1 > 0:
                sum2 = sum(
                    cast(pd.DataFrame, rated_ts.data)["value"]
                    .copy()
                    .dropna()
                    .to_list()[1:-1]
                )
                diff_fraction = abs((sum2 - sum1) / sum1)
                assert 0.1 >= diff_fraction
    else:
        raise Exception(f"Expected inputs to be of length 1 or 2, got {len(input_ts)}")
