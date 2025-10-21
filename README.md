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
from hec import HecTime, CwmsDataStore, DssDataStore

assert os.getenv("cda_api_root") is not None
assert os.getenv("cda_api_office") is not None

with CwmsDataStore.open(start_time=HecTime.now() - "PT1D") as db:
    # ---------------------------------------------------------- #
    # retrieve an elevation time series and rate it to a storage #
    # ---------------------------------------------------------- #
    elev_ts = db.retrieve("Keys.Elev.Inst.1Hour.0.Ccp-rev")
    rating_set = db.retrieve("KEYS.Elev;Stor.Linear.Production")
    stor_ts = rating_set.rate(elev_ts)
    for i in range(len(elev_ts)):
        print(f"{elev_ts.times[i]}\t{round(elev_ts.values[i], 2):.2f}\t{round(stor_ts.values[i], -1)}")
```
```
2025-10-20 18:00:00-05:00       725.01  434740.0
2025-10-20 19:00:00-05:00       724.96  433870.0
2025-10-20 20:00:00-05:00       724.94  433530.0
2025-10-20 21:00:00-05:00       724.93  433360.0
2025-10-20 22:00:00-05:00       724.96  433870.0
2025-10-20 23:00:00-05:00       724.96  433870.0
2025-10-21 00:00:00-05:00       724.98  434220.0
2025-10-21 01:00:00-05:00       724.99  434390.0
2025-10-21 02:00:00-05:00       725.00  434560.0
2025-10-21 03:00:00-05:00       725.01  434740.0
2025-10-21 04:00:00-05:00       725.01  434740.0
2025-10-21 05:00:00-05:00       725.02  434920.0
2025-10-21 06:00:00-05:00       725.04  435290.0
2025-10-21 07:00:00-05:00       725.05  435470.0
2025-10-21 08:00:00-05:00       725.07  435840.0
2025-10-21 09:00:00-05:00       725.08  436020.0
2025-10-21 10:00:00-05:00       725.09  436200.0
2025-10-21 11:00:00-05:00       725.10  436390.0
2025-10-21 12:00:00-05:00       725.11  436570.0
2025-10-21 13:00:00-05:00       725.08  436020.0
2025-10-21 14:00:00-05:00       725.09  436200.0
2025-10-21 15:00:00-05:00       725.05  435470.0
2025-10-21 16:00:00-05:00       725.01  434740.0
2025-10-21 17:00:00-05:00       724.96  433870.0
```

## Documentation

Scripting Guide at: https://hec-python-library.readthedocs.io/en/latest/

Examples at: https://github.com/HydrologicEngineeringCenter/hec-python-library/tree/main/examples

API Documentation at https://hydrologicengineeringcenter.github.io/hec-python-library/index.html
