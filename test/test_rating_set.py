import os
import warnings
from datetime import datetime
from typing import cast

import numpy as np

from hec import Combine, CwmsDataStore, TimeSeries, UnitQuantity
from hec.rating import AbstractRatingSet, ReferenceRatingSet
from hec.shared import import_cwms


def can_use_cda() -> bool:
    try:
        import_cwms()
    except:
        return False
    if os.getenv("cda_api_root") != "https://wm.swt.ds.usace.army.mil:8243/swt-data/":
        return False
    if os.getenv("cda_api_office") != "SWT":
        return False
    return True


def test_reference_rating_set() -> None:
    if not can_use_cda():
        skip_test_message = "Test test_reference_rating_set() is skipped because CDA is not accessible to test"
        warnings.warn(skip_test_message)
        return
    with CwmsDataStore.open() as db:
        db.time_window = "t-1d, t"  # type: ignore
        # -------------------------------------------- #
        # get a reference rating set from the database #
        # -------------------------------------------- #
        rating_set = cast(
            ReferenceRatingSet, db.retrieve("KEYS.Elev;Stor.Linear.Production")
        )
        # ----------------------------------- #
        # get a time series from the database #
        # ----------------------------------- #
        elev_ts = cast(TimeSeries, db.retrieve("KEYS.Elev.Inst.1Hour.0.Ccp-Rev"))
        assert elev_ts.unit == "ft"
        # -------------------- #
        # rate the time series #
        # -------------------- #
        stor_ts = cast(TimeSeries, rating_set.rate(elev_ts))
        assert stor_ts.unit == "ac-ft"
        assert len(stor_ts) == len(elev_ts)
        assert stor_ts.has_same_times(elev_ts)
        # ---------------------------------- #
        # reverse rate the rated time series #
        # ---------------------------------- #
        elev_ts2 = cast(TimeSeries, rating_set.reverse_rate(stor_ts))
        assert elev_ts2.unit == elev_ts.unit
        assert len(elev_ts2) == len(elev_ts)
        assert elev_ts.has_same_times(elev_ts)
        assert np.allclose(elev_ts.values, elev_ts2.values, equal_nan=True)
        # ----------------------------- #
        # introduce some missing values #
        # ----------------------------- #
        undefined_positions = (len(elev_ts) // 3, 2 * len(elev_ts) // 3)
        elev_ts3 = elev_ts.copy()
        for i in undefined_positions:
            elev_ts3.iselect(i, Combine.OR)
        elev_ts3.iset_value_quality(np.nan, 5)
        # -------------------- #
        # rate the time series #
        # -------------------- #
        stor_ts = cast(TimeSeries, rating_set.rate(elev_ts3))
        assert stor_ts.unit == "ac-ft"
        assert len(stor_ts) == len(elev_ts)
        assert stor_ts.has_same_times(elev_ts)
        for i in undefined_positions:
            assert np.isnan(stor_ts.values[i])
            assert stor_ts.qualities[i] == 5
        # ---------------------------------- #
        # reverse rate the rated time series #
        # ---------------------------------- #
        elev_ts4 = cast(TimeSeries, rating_set.reverse_rate(stor_ts))
        assert elev_ts4.unit == elev_ts3.unit
        assert len(elev_ts4) == len(elev_ts3)
        assert elev_ts4.has_same_times(elev_ts3)
        assert np.allclose(elev_ts4.values, elev_ts3.values, equal_nan=True)
        for i in undefined_positions:
            assert np.isnan(elev_ts4.values[i])
            assert elev_ts4.qualities[i] == 5
        # ------------------------- #
        # rate with different units #
        # ------------------------- #
        elev_ts_m = elev_ts3.to("m")
        stor_ts_mcm = stor_ts.to("mcm")
        # EN -> SI
        stor_ts3 = cast(TimeSeries, rating_set.rate(elev_ts3, units="mcm"))
        assert stor_ts3.unit == "mcm"
        assert np.allclose(stor_ts3.values, stor_ts_mcm.values, equal_nan=True)
        # SI -> SI
        stor_ts4 = cast(TimeSeries, rating_set.rate(elev_ts_m, units="mcm"))
        assert stor_ts4.unit == "mcm"
        assert np.allclose(stor_ts4.values, stor_ts_mcm.values, equal_nan=True)
        # SI -> EN
        stor_ts5 = cast(TimeSeries, rating_set.rate(elev_ts_m))
        assert stor_ts5.unit == "ac-ft"
        assert np.allclose(stor_ts5.values, stor_ts.values, equal_nan=True)
        # --------------------------------- #
        # reverse rate with different units #
        # --------------------------------- #
        # EN -> SI
        elev_ts5 = cast(TimeSeries, rating_set.reverse_rate(stor_ts, units="m"))
        assert elev_ts5.unit == "m"
        assert np.allclose(elev_ts5.values, elev_ts_m.values, equal_nan=True)
        # SI -> SI
        elev_ts6 = cast(TimeSeries, rating_set.reverse_rate(stor_ts_mcm, units="m"))
        assert elev_ts6.unit == "m"
        assert np.allclose(elev_ts6.values, elev_ts_m.values, equal_nan=True)
        # SI -> EN
        elev_ts7 = cast(TimeSeries, rating_set.reverse_rate(stor_ts_mcm))
        assert elev_ts7.unit == "ft"
        assert np.allclose(elev_ts7.values, elev_ts3.values, equal_nan=True)


if __name__ == "__main__":
    test_reference_rating_set()
