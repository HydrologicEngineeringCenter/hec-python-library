# hec-python-library

This package provides many of the capabilities of using Jython to access HEC's Java
class libraries. The library is focused on working with time series objects and associated infrasturcture:
   - locations
   - parameters
   - parameter types
   - times
   - intervals
   - durations
   - ratings

The package interoperates with the following packages for storing and retrieving data:
  - [CWMSpy](https://github.com/HydrologicEngineeringCenter/cwms-python/blob/main/README.md): Stores/retrieves data to/from CWMS databases using the CWMS Data API (CDA)
  - [HECDSS Python Wrapper](https://github.com/HydrologicEngineeringCenter/hec-dss-python/blob/main/Readme.md): Store/retrieves data to/from HEC-DSS files

## Requirements.

Python 3.9+

## Installation & Usage

### pip install

```sh
pip install hec-python-library
```

Then import the package:

```python
import hec
```

## Getting Started

```python
import os
from hec import CwmsDataStore, DssDataStore

assert os.getenv("cda_api_root") is not None
assert os.getenv("cda_api_office") is not None

with CwmsDataStore.open() as db:
    db.time_window = "t-30h, t"
    # ---------------------------------------------------------- #
    # retrieve an elevation time series and rate it to a storage #
    # ---------------------------------------------------------- #
    raw_elev_ts = db.retrieve("Bluestem.Elev.Inst.1Hour.0.Raw")
    print(raw_elev_ts)
    # ----------------------- #
    # do some quality control #
    # ----------------------- #
    rev_elev_ts = raw_elev_ts\
        .estimate_missing_values(max_missing_count=4)\
        .iolympic_moving_average(window=7, only_valid=True, use_reduced=True)
    rev_elev_ts.version = "Rev"
    rev_elev_ts = rev_elev_ts[6:] # don't keep the start of smoothing
    print(rev_elev_ts)
    # ------------------------------------ #
    # transform the elevations to storages #
    # ------------------------------------ #
    rating = db.retrieve("Bluestem.Elev;Stor.Linear.Production")
    stor_ts = rating_set.rate(rev_elev_ts)
    print(stor_ts)
    print("")
    # ---------------------------- #
    # print the time series values #
    # ---------------------------- #
    for i in range(len(rev_elev_ts)):
        print(f"{rev_elev_ts.times[i]}\t{round(rev_elev_ts.values[i], 2):.2f}\t{round(stor_ts.values[i], -1)}")
    print("")
    # ----------------------------------- #
    # store the time series to a DSS file #
    # ----------------------------------- #
    with DssDataStore.open("demo.dss", read_only=False) as dss:
        dss.store(raw_elev_ts)
        dss.store(rev_elev_ts)
        dss.store(stor_ts)
        for pathname in dss.catalog():
            print(pathname)

```
```
Bluestem.Elev.Inst.1Hour.0.Raw 30 values in ft
Bluestem.Elev.Inst.1Hour.0.Rev 24 values in ft
Bluestem.Stor.Inst.1Hour.0.Rev 24 values in ac-ft

2025-10-21 10:00:00-05:00       725.08  436090.0
2025-10-21 11:00:00-05:00       725.09  436170.0
2025-10-21 12:00:00-05:00       725.09  436170.0
2025-10-21 13:00:00-05:00       725.08  436060.0
2025-10-21 14:00:00-05:00       725.07  435760.0
2025-10-21 15:00:00-05:00       725.04  435250.0
2025-10-21 16:00:00-05:00       725.01  434700.0
2025-10-21 17:00:00-05:00       724.97  434040.0
2025-10-21 18:00:00-05:00       724.93  433390.0
2025-10-21 19:00:00-05:00       724.90  432910.0
2025-10-21 20:00:00-05:00       724.89  432600.0
2025-10-21 21:00:00-05:00       724.88  432470.0
2025-10-21 22:00:00-05:00       724.88  432470.0
2025-10-21 23:00:00-05:00       724.88  432500.0
2025-10-22 00:00:00-05:00       724.89  432710.0
2025-10-22 01:00:00-05:00       724.90  432880.0
2025-10-22 02:00:00-05:00       724.92  433120.0
2025-10-22 03:00:00-05:00       724.93  433290.0
2025-10-22 04:00:00-05:00       724.94  433490.0
2025-10-22 05:00:00-05:00       724.95  433670.0
2025-10-22 06:00:00-05:00       724.96  433910.0
2025-10-22 07:00:00-05:00       724.97  434000.0
2025-10-22 08:00:00-05:00       724.97  434100.0
2025-10-22 09:00:00-05:00       724.98  434220.0

09:35:42.041      -----DSS---zopen   New file opened,  File: U:\Devl\git\hec-python-library\demo.dss
09:35:42.042                         Handle 3;  Process: 23056;  DSS Version:  7-IW
09:35:42.042                         Single-user advisory access mode
09:35:49.240 -----DSS--- zwrite  Handle 3;  Version 1:  //Bluestem/Elev/01Oct2025/1Hour/Raw/
09:35:49.329 -----DSS--- zwrite  Handle 3;  Version 1:  //Bluestem/Elev/01Oct2025/1Hour/Rev/
09:35:49.427 -----DSS--- zwrite  Handle 3;  Version 1:  //Bluestem/Stor/01Oct2025/1Hour/Rev/
//Bluestem/Elev/01Oct2025/1Hour/Raw/
//Bluestem/Elev/01Oct2025/1Hour/Rev/
//Bluestem/Stor/01Oct2025/1Hour/Rev/
09:35:49.428      -----DSS---zclose  Handle 3;  Process: 23056;  File: U:\Devl\git\hec-python-library\demo.dss
09:35:49.428                         Number records:         3
09:35:49.428                         File size:              15990  64-bit words
09:35:49.428                         File size:              124 Kb;  0 Mb
09:35:49.428                         Dead space:             0
09:35:49.428                         Hash range:             8192
09:35:49.429                         Number hash used:       3
09:35:49.429                         Max paths for hash:     1
09:35:49.429                         Corresponding hash:     759
09:35:49.429                         Number non unique hash: 0
09:35:49.429                         Number bins used:       3
09:35:49.429                         Number overflow bins:   0
09:35:49.429                         Number physical reads:  25
09:35:49.429                         Number physical writes: 37
09:35:49.429                         Number denied locks:    0
```

## Documentation

Scripting Guide at: https://hec-python-library.readthedocs.io/en/latest/

Examples at: https://github.com/HydrologicEngineeringCenter/hec-python-library/tree/main/examples

API Documentation at https://hydrologicengineeringcenter.github.io/hec-python-library/index.html
