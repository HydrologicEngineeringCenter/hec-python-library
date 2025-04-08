"""
Module to provide native Python equivalent to HEC Java classes.

Quick links to Constants:
* [Combine](#Combine)
* [Safety](#Safety)
* [Selection](#Selection)
* [SelectionState](#SelectionState)

Quick links to Classes:
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
    "TimeSeries",
    "TimeSeriesException",
    "TimeSeriesValue",
    "TimeSpan",
    "TimeSpanException",
    "UnitQuantity",
    "UnitException",
    "const",
    "duration",
    "hectime",
    "interval",
    "location",
    "parameter",
    "quality",
    "timeseries",
    "timespan",
    "unit",
]

from .const import Combine, Safety, Select, SelectionState
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
