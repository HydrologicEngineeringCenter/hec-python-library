import hec

from test.shared import dataset_from_file

import pytest

@pytest.fixture
def dss():
    dss_file_name = "test/resources/rating/Paired_Data.dss"
    dssds:hec.datastore.DssDataStore = hec.datastore.DssDataStore.open(dss_file_name)
    yield dssds
    dssds.close()

@pytest.mark.parametrize(
    "pd_name, input_ts_names, expected_ts_names", dataset_from_file("resources/rating/Paired_Data.tsv")
)
def test_paired_data(dss, pd_name: str, input_ts_names: list[str], expected_ts_names: list[str]) -> None:
    dsspd = dss.retrieve(pd_name)
    input_ts = [dss.retrieve(ts_name) for ts_name in input_ts_names]
    expected_ts = [dss.retrieve(ts_name) for ts_name in expected_ts_names]

