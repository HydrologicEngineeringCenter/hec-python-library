import sys
from datetime import datetime
from typing import cast

from hec import CwmsDataStore, DssDataStore, HecTime, Location, TimeSeries

office_name = "SWT"
start_time = datetime(2025, 6, 1, 0, 1)  # 2025-06-01T00:01:00
end_time = datetime(2025, 7, 1)  # 2025-07-01T00:00:00
time_series_pattern = "*"
dss_time_zone = "UTC"  # for HEC-DSS records that don't specify time zone
verify = True  # verify by retrieving after storing
A, B, C, D, E, F = 1, 2, 3, 4, 5, 6  # pathname part indices

# --------------------------------------------------------------- #
# In order to store a location, the following items are required: #
# --------------------------------------------------------------- #
#   name                                                          #
#   office                                                        #
#   kind                                                          #
#   latitutde                                                     #
#   longitude                                                     #
#   horizontal_datum                                              #
#   time_zone                                                     #
# --------------------------------------------------------------- #
new_locations = [
    # DSS Locations not already in CWMS db
    Location(
        "WorkshopExample",
        office="SWT",
        kind="PROJECT",
        latitude=34.5,
        longitude=-98.4,
        horizontal_datum="NAD83",
        time_zone="US/Central",
    ),
]
new_locations_by_name = {loc.name.upper(): loc for loc in new_locations}

cwms_location_names = set()
DssDataStore.set_message_level(2)  # critical output plus file open/close
with DssDataStore.open("WorkshopExample.dss") as dss:
    # -------------------------------------------------------------------------------- #
    # If you don't set a time window for the DSS data store, the hecdss module will    #
    # retrieve all times for a specified time series, regardless of whether the D part #
    # of the pathname is specified or not.                                             #
    # -------------------------------------------------------------------------------- #
    dss.time_window = f"{start_time.isoformat()}, {end_time.isoformat()}"
    data_set_names = dss.catalog(
        "timeseries", pattern=time_series_pattern, condensed=True
    )  # one entry per time series
    with CwmsDataStore.open(
        office=office_name, read_only=False
    ) as db:  # cda_api_root and cda_api_key in environment
        if verify:
            db.time_zone = "UTC"
        for data_set_name in data_set_names:
            location_name = data_set_name.split("/")[B]
            if location_name.upper() not in cwms_location_names:
                # location not in local set
                catalog = db.catalog("location", pattern=location_name)
                if catalog:
                    # location is in CWMS db, so add to local set
                    cwms_location_names.add(catalog[0].upper())
                else:
                    # location is not in CWMS db
                    if location_name.upper() in new_locations_by_name:
                        # store the location to the CWMS db and add to local set
                        print(
                            f"==> Storing location {new_locations_by_name[location_name.upper()].name}"
                        )
                        db.store(new_locations_by_name[location_name.upper()])
                        cwms_location_names.add(location_name.upper())
                    else:
                        # skip time series with unknown location
                        print(
                            f"==> Can't store time series {data_set_name} with unknown location: {location_name}"
                        )
                        continue
            # retrieve the time series from HEC-DSS
            try:
                ts = cast(TimeSeries, dss.retrieve(data_set_name))
            except Exception as e:
                print(f"==> Error retrieving {data_set_name}\n\t{str(e)}")
                continue
            print(f"Retrieved {ts}")
            if len(ts) == 0:
                continue
            ts.context = "CWMS"
            if ts.time_zone is None:
                ts.ilabel_as_time_zone(dss_time_zone, on_already_set=0)
            # ---------------------------------------------- #
            # Perform any renaming or other conversions here #
            # ---------------------------------------------- #
            ts.version = (
                "FromArchive" if not ts.version else ts.version + "-FromArchive"
            )
            # store the time series to CWMS db
            sys.stdout.write(f"\tStoring {ts}...")
            sys.stdout.flush()
            db.store(ts)
            print("done")
            if verify:
                sys.stdout.write("\tRetrieving...")
                sys.stdout.flush()
                db.time_zone = ts.time_zone  # type: ignore
                db.start_time = HecTime(ts.times[0])
                db.end_time = HecTime(ts.times[-1])
                ts2 = db.retrieve(ts.name)
                if len(ts2) != len(ts):
                    print(f"\tError: expected {len(ts)} values, got {len(ts2)}")
                else:
                    print("\tVerified")
