from hec import (
    CwmsDataStore,
    DssDataStore,
    TimeSeries,
)

from typing import cast

office_name = "SWT"
with CwmsDataStore.open(office=office_name) as db:
    db.is_read_only  = True
    catalog = db.catalog("timeseries", pattern="Keys*")
    db.time_window = "2025-04-01T00:01:00Z, 2025-07-01T00:00:00Z"
    with DssDataStore.open("WorkshopExample.dss", read_only=False) as dss:
        for tsid in catalog:
            try:
                ts = cast(TimeSeries, db.retrieve(tsid)).iconvert_to_time_zone("UTC")
            except Exception as e:
                print(f"==> Could not retrieve {tsid}")
                continue
            ts = ts.iset_location("WorkshopExample")
            print(ts)
            if len(ts) == 0:
                continue
            dss.store(ts)
