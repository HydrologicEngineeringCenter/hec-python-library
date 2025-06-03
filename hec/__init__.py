"""
Module to provide native Python equivalent to HEC Java classes.

Quick links to Constants:
* [Combine](#Combine)
* [Safety](#Safety)
* [Select](#Select)
* [SelectionState](#SelectionState)

Quick links to Classes:
* [CwmsDataStore](#CwmsDataStore)
* [DssDataStore](#DssDataStore)
* [Duration](#Duration)
* [ElevParameter](#ElevParameter)
* [HecTime](#HecTime)
* [Interval](#Interval)
* [Location](#Location)
* [Parameter](#Parameter)
* [ParameterType](#ParameterType)
* [Quality](#Quality)
* [TimeSeries](#TimeSeries)
* [TimeSeriesValue](#TimeSeriesValue)
* [TimeSpan](#TimeSpan)
* [UnitQuantity](#UnitQuantity)

Quick links to Exceptions:
* [DataStoreException](#DataStoreException)
* [DurationException](#DurationException)
* [HecTimeException](#HecTimeException)
* [IntervalException](#IntervalException)
* [LocationException](#LocationException)
* [ParameterException](#ParameterException)
* [ParameterTypeException](#ParameterTypeException)
* [TimeSeriesException](#TimeSeriesException)
* [TimeSpanException](#TimeSpanException)
* [UnitException](#UnitException)

"""

__all__ = [
    "Combine",
    "CwmsDataStore",
    "DataStoreException",
    "DeleteAction",
    "DssDataStore",
    "Duration",
    "DurationException",
    "ElevParameter",
    "HecTime",
    "HecTimeException",
    "Interval",
    "IntervalException",
    "Location",
    "LocationException",
    "Parameter",
    "ParameterException",
    "ParameterType",
    "ParameterTypeException",
    "Quality",
    "QualityException",
    "Safety",
    "Select",
    "SelectionState",
    "StoreRule",
    "TimeSeries",
    "TimeSeriesException",
    "TimeSeriesValue",
    "TimeSpan",
    "TimeSpanException",
    "UnitQuantity",
    "UnitException",
    "const",
    "datastore",
    "duration",
    "hectime",
    "interval",
    "location",
    "parameter",
    "quality",
    "shared",
    "timeseries",
    "timespan",
    "unit",
]

from . import datastore
from .const import Combine, Safety, Select, SelectionState
from .datastore import (
    CwmsDataStore,
    DataStoreException,
    DeleteAction,
    DssDataStore,
    StoreRule,
)
from .duration import Duration, DurationException
from .hectime import HecTime, HecTimeException
from .interval import Interval, IntervalException
from .location import Location, LocationException
from .parameter import (
    ElevParameter,
    Parameter,
    ParameterException,
    ParameterType,
    ParameterTypeException,
)
from .quality import Quality, QualityException
from .timeseries import TimeSeries, TimeSeriesException, TimeSeriesValue
from .timespan import TimeSpan, TimeSpanException
from .unit import UnitException, UnitQuantity

# ------------------------------------------------------------ #
# dynamic class docstrings defined here for pdoc compatibility #
# ------------------------------------------------------------ #
datastore.CwmsDataStore.__doc__ = f"""
    Class to facilitate cataloging, storing, retrieving, and deleting data in CWMS databases.

    Requires installation of the [cwms-python](https://pypi.org/project/cwms-python/) {datastore._required_cwms_version}.
    """

datastore.DssDataStore.__doc__ = f"""
    Class to facilitate cataloging, storing, retrieving, and deleting data in HEC-DSS files.

    Requires installation of the 'hecdss' package {datastore._required_dss_version}.
    """
