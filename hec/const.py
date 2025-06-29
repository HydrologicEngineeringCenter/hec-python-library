"""
Provides constants and related items
"""

from enum import Enum

UNDEFINED = -3.4028234663852886e38

CWMS = "CWMS"
DSS = "DSS"


class Combine(Enum):
    """
    Enumeration for combining selection states (current, new)

    * `NOOP`: Result is current selection state for all items
    * `REPLACE`: Result is new selection state for all items
    * `AND`: Result is current selection ANDed with new selection state
    * `OR`: Result is current selection ORed with new selection state
    * `XOR`: Result is current selection XORed with new selection state
    """

    NOOP = 0
    REPLACE = 1
    AND = 2
    OR = 3
    XOR = 4


class PercentileMethods(Enum):
    """
    Enumeration of methods for computing percentiles

    * `HECMATH`: is used only in [TimeSeries.cyclic_analysys()](timeseries.html#TimeSeries.cyclic_analysis) and specifies using the Java HecMath algorithm for computing
        the percentiles in the cyclic analysis statistics.
    * Others: See the [NumPy docs](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html) for descriptions

    """

    HECMATH = 0
    AVERAGED_INVERTED_CDF = 1
    CLOSEST_OBSERVATION = 2
    HAZEN = 3
    HIGHER = 4
    INTERPOLATED_INVERTED_CDF = 5
    INVERTED_CDF = 6
    LINEAR = 7
    LOWER = 8
    MEDIAN_UNBIASED = 9
    MIDPOINT = 10
    NEAREST = 11
    NORMAL_UNBIASED = 12
    WEIBULL = 13


class Safety(Enum):
    """
    Enumeration for specifying behavior of potentially unsafe operations.

    * `NOOP_ON_UNSAFE`: No action is taken on potientially unsafe operations
    * `WARN_ON_UNSAFE`: Potentially unsafe operations will generate a warning
    * `ERROR_ON_UNSAFE`: Potentially unsafe operations will raise an exception
    """

    NOOP_ON_UNSAFE = 0
    WARN_ON_UNSAFE = 1
    ERROR_ON_UNSAFE = 2


class Select(Enum):
    """
    Enumeration for specifying items to select

    * `NONE`: Set all items to unselected
    * `ALL`: Set all items to selected
    * `INVERT`: Set all items to the inverse of their currently selected state
    """

    NONE = 0
    ALL = 1
    INVERT = 2


class SelectionState(Enum):
    """
    Enumeration for specifying selection durability

    * `TRANSIENT`: Selection is cleared after next operation
    * `DURABLE`: Selection persists until explicitly modified
    """

    TRANSIENT = 0
    DURABLE = 1
