"""
Module to provide native Python equivalent to HEC Java classes.

**Quick links to Constants:**

* [Combine](const.html#Combine)
* [Safety](const.html#Safety)
* [Select](const.html#Select)
* [SelectionState](const.html#SelectionState)

**Quick links to Classes:**

<table/>
    <table>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Time Instances and Periods</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="hectime.html#HecTime">HecTime</a></td>
        <td><a href="hectime.html#HecTimeException">HecTimeException</a></td>
        <td>Provides time instance-related calculations and manipulations. Mimics hec.helib.util.HecTime Java class</td>
    </tr>
    <tr><td><a href="timespan.html#TimeSpan">TimeSpan</a></td>
        <td><a href="timespan.html#TimeSpanException">TimeSpanException</a></td>
        <td>Provides generic time- and calendar-based time span (period) information/operations</td>
    </tr>
    <tr><td><a href="interval.html#Interval">Interval</a></td>
        <td><a href="interval.html#IntervalException">IntervalException</a></td>
        <td>Provides time series recurrence interval information/operations</td>
    </tr>
    <tr><td><a href="duration.html#Duration">Duration</a></td>
        <td><a href="duration.html#DurationException">DurationException</a></td>
        <td>Provides time series value duration information/operations</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Numerical Quantities</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="unit.html#UnitQuantity">UnitQuantity</a></td>
        <td><a href="unit.html#UnitException">UnitException</a></td>
        <td>Provides value (magnitude+unit) information/operations including unit conversions</td>
    </tr>
    <tr><td><a href="quality.html#Quality">Quality</a></td>
        <td></td>
        <td>Holds quality assessments for numerical values</td>
    <tr><td><a href="hec/rounding.html#UsgsRounder">UsgsRounder</a></td>
        <td></td>
        <td>Provides rounding operations for numerical values</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Locations</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="location.html#Location">Location</a></td>
        <td><a href="location.html#LocationException">LocationException</a></td>
        <td>Holds information about locations</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Parameters</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="parameter.html#Parameter">Parameter</a></td>
        <td><a href="parameter.html#ParameterException">ParameterException</a></td>
        <td>Holds information about parameters for time series, ratings, etc...</td>
    </tr>
    <tr><td><a href="parameter.html#ElevParameter">ElevParameter</a></td>
        <td><a href="parameter.html#ParameterException">ParameterException</a></td>
        <td>Holds information about elevation parameters (including vertical datum information)</td>
    </tr>
    <tr><td><a href="parameter.html#ParameterType">ParameterType</a></td>
        <td><a href="parameter.html#ParameterException">ParameterTypeException</a></td>
        <td>Holds information about the relation of parameters to durations</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Time Series</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="timeseries.html#TimeSeries">TimeSeries</a></td>
        <td><a href="timeseries.html#TimeSeriesException">TimeSeriesException</a></td>
        <td>Holds time series information and provides operations for time series</td>
    </tr>
    <tr><td><a href="timeseries.html#TimeSeriesValue">TimeSeriesValue</a></td>
        <td><a href="timeseries.html#TimeSeriesException">TimeSeriesException</a></td>
        <td>Holds information and provides operations for single time series values</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3">Data Stores</th></tr>
    <tr style="background-color: #f0f0f0;"><th>Class</th><th>Exception</th><th>Description</th></tr>
    <tr><td><a href="datastore.html#AbstractDataStore">AbstractDataStore</a></td>
        <td><a href="datastore.html#DataStoreException">DataStoreException</a></td>
        <td>Abstract base class for all data store classes</td>
    </tr>
    <tr><td><a href="datastore.html#CwmsDataStore">CwmsDataStore</a></td>
        <td><a href="datastore.html#DataStoreException">DataStoreException</a></td>
        <td>Provides operations using CWMS databases for cataloging, retrieving, and storing data</td>
    </tr>
    <tr><td><a href="datastore.html#DssDataStore">DssDataStore</a></td>
        <td><a href="datastore.html#DataStoreException">DataStoreException</a></td>
        <td>Provides operations using HEC-DSS files for cataloging, retrieving, and storing data</td>
    </tr>
    <tr style="background-color: #f0f0f0;"><th colspan="3"><a href="hec/rating.html">Rating-related Classes</a></th></tr>
    </table>

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
    "rounding",
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
