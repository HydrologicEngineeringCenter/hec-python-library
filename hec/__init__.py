"""
Module to provide native Python equivalent to HEC Java classes.

Quick links to Constants:
* [Combine](#Combine)
* [Safety](#Safety)
* [Select](#Select)
* [SelectionState](#SelectionState)

Quick links to Classes:
* [AbstractDataStore](#AbstractDataStore)
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
    "AbstractDataStore",
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
    "UsgsRounder",
    "const",
    "datastore",
    "duration",
    "hectime",
    "interval",
    "location",
    "parameter",
    "quality",
    "rating",
    "shared",
    "timeseries",
    "timespan",
    "unit",
]


from . import datastore, rating, shared
from .const import Combine, Safety, Select, SelectionState
from .datastore import (
    AbstractDataStore,
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
from .rounding import UsgsRounder
from .timeseries import TimeSeries, TimeSeriesException, TimeSeriesValue
from .timespan import TimeSpan, TimeSpanException
from .unit import UnitException, UnitQuantity

# ------------------------------------------------------------ #
# dynamic class docstrings defined here for pdoc compatibility #
# ------------------------------------------------------------ #
datastore.CwmsDataStore.__doc__ = f"""
    Class to facilitate cataloging, storing, retrieving, and deleting data in CWMS databases.

    Requires installation of the [cwms-python](https://pypi.org/project/cwms-python/) {shared.required_cwms_version}.
    """

datastore.DssDataStore.__doc__ = f"""
    Class to facilitate cataloging, storing, retrieving, and deleting data in HEC-DSS files.

    Requires installation of the 'hecdss' package {shared.required_dss_version}.
    """
