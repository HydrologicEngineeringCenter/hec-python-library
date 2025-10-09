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

    <a name="rating_note"/>
    <fieldset style="border: 2px solid #999; padding: 1em;"><legend>Note on using DssDataStore objects with rating objects</legend><code>DssDataStore</code> objects can be used to store and retrieve
    <a href="rating/local_rating_set.html#LocalRatingSet"><code>LocalRatingSet</code></a> objects. Since <em>these objects are not
    identifiable with a single pathname</em>, rating specification identifiers (which are mapped to multiple pathnames) are used
    to retrieve <a href="rating/local_rating_set.html#LocalRatingSet"><code>LocalRatingSet</code></a> objects from the data store. The portions
    of rating sets (i.e., rating templates, rating specifications, and individual ratings) may be cataloged with the appropiate
    identifiers mathched by the <code>pattern</code> or <code>regex</code> keyword arguments to the <a href="#DssDataStore.catalog"><code>catalog()</code></a> method:
    <ul>
    <li>rating template identifiers are matched for <a href="rating/rating_template#RatingTemplate.html"><code>RatingTemplate</code></a> objects</li>
    <li>rating specification identifiers are matched for <a href="rating/rating_specification.html/RatingSpecification"><code>RatingSpecification</code></a> and
       <a href="rating/abstract_rating.html/AbstractRating"><code>AbstractRating</code></a> objects</li>
    </ul>
    For cataloging purposes, the <code>data_type</code> parameter must be specified (i.e., <code>"RATING_TEMPLATE"</code>,
    <code>"RATING_SPECIFICATION"</code> or <code>"RATING"</code>). The <a href="#DssDataStore.catalog"><code>catalog()</code></a> method normally returns
    identifiers for these data types, but specifying <code>pathnames=True</code> causes pathnames to be returned instead, as shown
    in the command-line session below.

    All rating related pathnames have D pathname parts that start with "Rating-". The mapping of the CWMS-style
    identifiers onto HEC-DSS pathnames is:
    <p>
    <table>
    <tr style="background-color: #f0f0f0;">
        <th>Object Type</th>
        <th>A&nbsp;Part</th>
        <th>B&nbsp;Part</th>
        <th>C&nbsp;Part</th>
        <th>D&nbsp;Part</th>
        <th>E&nbsp;Part</th>
        <th>F&nbsp;Part</th>
        <th>Record&nbsp;Body</td>
    </tr>
    <tr>
        <td>Rating Template</td>
        <td>Office ID</td>
        <td></td>
        <td>Parameters ID</td>
        <td>"Rating&#8209;Template"</td>
        <td>Template Version</td>
        <td></td>
        <td>Rating Template XML</td>
    </tr>
    <tr>
        <td>Rating Specification</td>
        <td>Office ID</td>
        <td>Location ID</td>
        <td>Parameters ID</td>
        <td>"Rating&#8209;Specification"</td>
        <td>Template Version</td>
        <td>Specification Version</td>
        <td>Rating Specification XML</td>
    </tr>
    <tr>
        <td>Rating</td>
        <td>Office ID</td>
        <td>Location ID</td>
        <td>Parameters ID</td>
        <td>"Rating&#8209;Body&#8209;<em>Effective&#8209;Time</em>"</td>
        <td>Template Version</td>
        <td>Specification Version</td>
        <td>Rating XML minus any TableRating points (for lazy loading)</td>
    </tr>
    <tr>
        <td>Table Rating Points</td>
        <td>Office ID</td>
        <td>Location ID</td>
        <td>Parameters ID</td>
        <td>"Rating&#8209;Points&#8209;<em>Effective&#8209;Time</em>"</td>
        <td>Template Version</td>
        <td>Specification Version</td>
        <td>Rating XML including any TableRating points (for populating after lazy loading)</td>
    </tr>
    </table>
    For example, in the image below, <a href="rating/local_rating_set.html#LocalRatingSet"><code>LocalRatingSet</code></a> with the following rating 
    specification identifiers have been stored to an empty HEC-DSS file. Both rating sets were for office SWT.
    <ul>
    <li>COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production/</li>
    <li>KEYS.Elev;Stor.Linear.Production/</li>
    </ul>

    <style>
    .expandable {{
    width: 725px;
    transition: width 0.3s ease;
    cursor: zoom-in;
    }}
    .expandable:active {{
    width: 1200px;
    cursor: zoom-out;
    }}
    </style>
    <img src="images/Rating_Pathnames.png" alt="Expandalbe image of HEC-DSSVue showing a catalog of rating set pathnames" class="expandable" title="Rating Pathnames">
    <p>
    <p>
    The following command line session demonstrates cataloging the file and retrieving one of the rating sets:
    <style>
    pre {{ font-family: monospace; }}
    .typed {{ color: darkred;}}
    .response {{ color: blue; }}
    </style>
    <pre>
    >>> <span class="typed">from hec import DssDataStore</span>
    >>> <span class="typed">dss = DssDataStore.open(r"U:\Devl\git\hec-python-library\\test\\resources\\rating\local_rating_set.dss")</span>
    <span class="response">16:50:45.507      -----DSS---zopen   Existing file opened,  File: U:\Devl\git\hec-python-library\\test\\resources\\rating\local_rating_set.dss
    16:50:45.507                         Handle 3;  Process: 18724;  DSS Versions - Software: 7-IU, File:  7-IU
    16:50:45.508                         Single-user advisory access mode</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING_TEMPLATE"): print(item)</span>
    ...
    <span class="response">Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard
    Elev;Stor.Linear</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING_TEMPLATE", pathnames=True): print(item)</span>
    ...
    <span class="response">/SWT//Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Template/Standard//
    /SWT//Elev;Stor/Rating-Template/Linear//</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING_SPECIFICATION"): print(item)</span>
    ...
    <span class="response">COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production
    KEYS.Elev;Stor.Linear.Production</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING_SPECIFICATION", pathnames=True): print(item)</span>
    ...
    <span class="response">/SWT/COUN/Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Specification/Standard/Production/
    /SWT/KEYS/Elev;Stor/Rating-Specification/Linear/Production/</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING"): print(item)</span>
    ...
    <span class="response">COUN.Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates.Standard.Production
    KEYS.Elev;Stor.Linear.Production</span>
    >>>
    >>> <span class="typed">for item in dss.catalog("RATING", pathnames=True): print(item)</span>
    ...
    <span class="response">/SWT/COUN/Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Body-2012-04-26T05:00:00Z/Standard/Production/
    /SWT/COUN/Count-Conduit_Gates,Opening-Conduit_Gates,Elev;Flow-Conduit_Gates/Rating-Body-2012-04-27T05:00:00Z/Standard/Production/
    /SWT/KEYS/Elev;Stor/Rating-Body-2009-01-14T06:00:00Z/Linear/Production/
    /SWT/KEYS/Elev;Stor/Rating-Body-2011-10-19T05:00:00Z/Linear/Production/
    /SWT/KEYS/Elev;Stor/Rating-Body-2020-08-01T05:00:00Z/Linear/Production/</span>
    >>>
    >>> <span class="typed">rs = dss.retrieve("KEYS.Elev;Stor.Linear.Production", office="SWT")</span>
    >>> <span class="typed">print(type(rs))</span>
    <span class="response"><class 'hec.rating.local_rating_set.LocalRatingSet'></span>
    >>>
    >>> <span class="typed">for effective_time in rs.ratings: print(effective_time.isoformat(), rs.ratings[effective_time])</span>
    ...
    <span class="response">2009-01-14T06:00:00+00:00 <hec.rating.table_rating.TableRating object at 0x0000019CBC556EB0>
    2011-10-19T05:00:00+00:00 <hec.rating.table_rating.TableRating object at 0x0000019CBC59C220>
    2020-08-01T05:00:00+00:00 <hec.rating.table_rating.TableRating object at 0x0000019CBC600880></span>
    </pre>
    </fieldset>
    """
