from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Sequence, Union, cast

import numpy as np

import hec

from ..parameter import (
    _NAVD88,
    _NGVD29,
    _OTHER_DATUM,
    Parameter,
    _navd88_pattern,
    _ngvd29_pattern,
    _other_datum_pattern,
)
from ..shared import RatingException
from ..timeseries import TimeSeries
from .rating_specification import RatingSpecification
from .rating_template import RatingTemplate


class AbstractRatingSetException(RatingException):
    pass


class AbstractRatingSet(ABC):
    """
    Abstract class for all rating set classes.

    Specifies required methods for sub-classes, holds information and implements code common one or more sub-classes.
    """

    def __init__(self, specification: Any, **kwargs: Any):
        """
        Initializer for AbstractRatingSet objects.

        Args:
            specification (Any): A [RatingSpecification](#RatingSpecification) object to initialize from.
                This is typed as `Any` to avoid circular import dependencies.

        Raises:
            TypeError: if `specification` is not a [RatingSpecification](#RatingSpecification) object.
        """
        if not isinstance(specification, hec.rating.RatingSpecification):
            raise TypeError(
                f"Expected RatingSpecification for specification, got {specification.__class__.__name__}"
            )
        self._default_data_time: Optional[datetime] = None
        self._default_data_units: Optional[list[str]] = None
        self._default_data_veritcal_datum: Optional[str] = None
        self._rating_time: Optional[datetime] = datetime.max
        self._specification = specification.copy()

    @property
    def default_data_time(self) -> Optional[datetime]:
        """
        The default data time of the rating set.

        If not None, the default data time is used to rate values that don't otherwise have times specified.

        If None, the current time is used as the default data time

        Operations:
            Read/Write
        """
        return self._default_data_time

    @default_data_time.setter
    def default_data_time(self, default_data_time: Optional[datetime]) -> None:
        if not isinstance(default_data_time, (type(None), datetime)):
            raise AbstractRatingSetException(
                f"Expected None or datetime, got {default_data_time.__class__.__name__}"
            )
        self._default_data_time = default_data_time

    @property
    def default_data_units(self) -> Optional[list[str]]:
        """
        The units to use for independent and dependent parameter values when no units are specified for
        [rate_values](#AbstractRatingSet.rate_values) or [reverse_rate_values](#AbstractRatingSet.reverse_rate_values).

        If None and no data units are specified, the rating methods will raise an exception.

        Operations:
            Read/Write
        """
        return self._default_data_units

    @default_data_units.setter
    def default_data_units(self, units: list[str]) -> None:
        units_count = len(units)
        ind_param_count = self.template.ind_param_count
        if units_count != ind_param_count + 1:
            raise AbstractRatingSetException(
                f"Expected {ind_param_count+1} units, got {units_count}"
            )
        _units = []
        for i in range(ind_param_count):
            parameter = Parameter(self.template.ind_params[i], units[i])
            _units.append(parameter.unit_name)
        parameter = Parameter(self.template.ind_params[-1], units[-1])
        _units.append(parameter.unit_name)
        self._default_data_units = _units

    @property
    def default_vertical_datum(self) -> Optional[str]:
        """
        The default vertical datum for rating Elev parameter values.

        If not None, Elev parameter values will be converted to the default vertical datum before (input values) or after (output values) the rating is performed.

        If None, the native vertical datum will be used.

        When setting, must be None, NGVD-29, NAVD-99, or OTHER.

        Operations:
            Read/Write
        """
        return self._default_data_veritcal_datum

    @default_vertical_datum.setter
    def default_vertical_datum(self, default_vertical_datum: Optional[str]) -> None:
        if default_vertical_datum is None:
            self._default_data_veritcal_datum = None
        elif _navd88_pattern.match(default_vertical_datum):
            self._default_data_veritcal_datum = _NAVD88
        elif _ngvd29_pattern.match(default_vertical_datum):
            self._default_data_veritcal_datum = _NGVD29
        elif _other_datum_pattern.match(default_vertical_datum):
            self._default_data_veritcal_datum = _OTHER_DATUM
        else:
            raise AbstractRatingSetException(
                f"Expected {_NGVD29}, {_NAVD88},"
                f" or {_OTHER_DATUM}, got {default_vertical_datum}"
            )

    def rate(
        self,
        input: Union[list[list[float]], TimeSeries, Sequence[TimeSeries]],
        *,
        times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> Union[list[float], TimeSeries]:
        """
        Rates independent parameter values and returns dependent parameter values.

        Args:
            input (Union[list[list[float]], TimeSeries, Sequence[TimeSeries]]): The input parameter values.
                * If specified as a list of lists of floats:
                    * The list must be of the same length as the number of independent parameters of the rating set.
                    * Each list of values must have the same times and be of the same length
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A list of floats is returned
                * If specified as a TimeSeries:
                    * The rating set must have a single independent parameter
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
                * If specified as a list of TimeSeries:
                    * The list must be of the same length as the number of independent parameters of the rating set.
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
            times (Optional[list[datetime]], must be passed by name): The date/times of the independent parameter values. Defaults to None.
                * If specified and not None:
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If None or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str], optional, must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies units of the independent parameter values and the rated values. A comma-delimited string of
                  independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None. If not specified or None, the rating's
                  default data units are used, if specified. If the rating has no default data units, the rating units are used.
                * If specified as a TimeSeries or list of TimeSeries, this specifies the unit of the rated time series. If not specified or None, rating set's default
                  data unit for the dependent parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            rating_time (Optional[datetime], must be passed by name): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional, must be passed by name): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            Union[list[float], TimeSeries]: The dependent parameter values as described in `input` above
        """
        if isinstance(input, TimeSeries):
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self.rate_time_series(
                ts=input, unit=units, rating_time=rating_time, round=round
            )
        elif isinstance(input, list) and isinstance(input[0], TimeSeries):
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self.rate_time_series(
                ts=cast(list[TimeSeries], input),
                unit=units,
                rating_time=rating_time,
                round=round,
            )
        elif (
            isinstance(input, list)
            and isinstance(input[0], list)
            and isinstance(input[0][0], float)
        ):
            return self.rate_values(
                ind_values=cast(list[list[float]], input),
                value_times=times,
                units=units,
                rating_time=rating_time,
                round=round,
            )
        else:
            raise TypeError(f"Unexpected type for input: {input.__class__.__name__}")

    def rate_time_series(
        self,
        ts: Union[TimeSeries, Sequence[TimeSeries]],
        unit: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> TimeSeries:
        """
        Rates an independent parameter time series (or list of such) and returns a dependent parameter time series

        Args:
            ts (Union[TimeSeries, Sequence[TimeSeries]]): If a list/tuple of TimeSeries:
                * Must be the same number as the number of independent parameters of the rating set.
                * Each time series must have the same times.
            unit (Optional[str]): The unit of the rated time series. If not specified or None, rating set's default data unit for the dependent
                parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            rating_time (Optional[datetime]): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            TimeSeries: The rated (dependent value) time series
        """
        ts_list: list[TimeSeries]
        if isinstance(ts, (tuple, list)):
            for i in range(len(ts)):
                if not isinstance(ts[i], TimeSeries):
                    raise TypeError(
                        f"Expected TimeSeries for ts[{i}], got {ts[i].__class__.__name__}"
                    )
            ts_list = list(ts)
        elif isinstance(ts, TimeSeries):
            ts_list = [ts]
        else:
            raise TypeError(
                f"Expected TimeSeries or list/tuple of TimeSeries for parameter ts, got {ts.__class__.__name__}"
            )
        ts_count = len(ts_list)
        expected_ts_count = self._specification.template.ind_param_count
        if ts_count != expected_ts_count:
            raise ValueError(
                f"Expected {expected_ts_count} time series in ts, got {ts_count}"
            )
        time_strs = ts_list[0].times
        for i in range(1, ts_count):
            if ts_list[i].times != time_strs:
                raise ValueError(
                    f"Times for {ts[i].name} aren't the same as for {ts[0].name}"
                )
        values = [t.values for t in ts_list]
        times = [datetime.fromisoformat(t) for t in time_strs]
        dep_unit = (
            unit
            if unit
            else (
                self._default_data_units[-1]
                if self._default_data_units is not None
                else Parameter(self.template.dep_param).unit_name
            )
        )
        if len(ts_list[0]) > 0:
            units = f"{','.join([t.unit for t in ts_list])};{dep_unit}"
            rated_values = self.rate_values(
                ind_values=values,
                value_times=times,
                units=units,
                rating_time=rating_time,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts_list[0].copy()
        rated_ts.iset_parameter(
            Parameter(self._specification._template.dep_param, dep_unit)
        )
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def rate_values(
        self,
        ind_values: list[list[float]],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        """
        Rates list(s) of independent parameter values

        Args:
            ind_values (list[list[float]]): The independent parameter values. Values for each parameter are in its own list
                in the same order as the rating independent parameters. All parameter lists must be of the same length.
            value_times (Optional[list[datetime]]): The date/times of the independent parameter values. Defaults to None.
                * If specified and not None:
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If None or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str]): The units of the independent parameter values and the rated values. A comma-delimited string of
                independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None.
                * If not specified, the rating's default data units are used, if specified. If the rating has no default data units,
                    the rating units are used.
            rating_time (Optional[datetime]): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            list[float]: The rated (dependent parameter) values
        """
        raise AbstractRatingSetException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

    def reverse_rate_time_series(
        self,
        ts: TimeSeries,
        unit: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> TimeSeries:
        """
        Reverse rates a dependent parameter time series and returns an independent parameter time series

        Args:
            ts (TimeSeries): The dependent value time series to reverse-rate
            unit (Optional[str]): The unit of the rated time series. If not specified or None, rating set's default data unit for the independent
                parameter, if any, is used. Otherwise, the independent parameter's default unit will be used.
            rating_time (Optional[datetime]): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional): Whether to use the rating set's specification's independent rounding specification . Defaults to False.

        Returns:
            TimeSeries: The rated (independent value) time series
        """
        if not isinstance(ts, TimeSeries):
            raise TypeError(f"Expected TimeSeries for ts, got {ts.__class__.__name__}")
        ind_unit = (
            unit
            if unit
            else (
                self._default_data_units[0]
                if self._default_data_units
                else Parameter(self.template.ind_params[0]).unit_name
            )
        )
        if len(ts) > 0:
            units = f"{ind_unit};{ts.unit}"
            rated_values = self.reverse_rate_values(
                dep_values=ts.values,
                value_times=[datetime.fromisoformat(s) for s in ts.times],
                units=units,
                rating_time=rating_time,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts.copy()
        rated_ts.iset_parameter(Parameter(self.template.ind_params[0], ind_unit))
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def reverse_rate_values(
        self,
        dep_values: list[float],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        """
        Rates a list of dependent parameter values.

        May only be used on rating sets with a single independent parameter.

        Args:
            dep_values (list[float]): The dependent parameter values.
            value_times (Optional[list[datetime]]): The date/times of the independent parameter values. Defaults to None.
                * If specified and not None:
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If None or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str]): The units of the independent parameter values and the rated values.A comma-delimited string of
                independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None.
                * If not specified, the rating's default data units are used, if specified. If the rating has no default data units,
                    the rating units are used.
            rating_time (Optional[datetime]): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional): Whether to use the rating set's specification's independent rounding specification . Defaults to False.

        Returns:
            list[float]: The rated (independent parameter) values
        """
        raise AbstractRatingSetException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

    def reverse_rate(
        self,
        input: Union[list[float], TimeSeries],
        *,
        times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> Union[list[float], TimeSeries]:
        """
        Rates dependent parameter values and returns independent parameter values.

        Args:
            input (Union[list[float], TimeSeries]): The input parameter values.
                * If specified as a lists of floats:
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A list of floats is returned
                * If specified as a TimeSeries:
                    * The rating set must have a single independent parameter
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
            times (Optional[list[datetime]], must be passed by name): The date/times of the independent parameter values. Defaults to None.
                * If specified and not None:
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If None or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str], optional, must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies units of the independent parameter values and the rated values. A comma-delimited string of
                  independent value units concatendated with a semicolon and the dependent parameter unit. Defaults to None. If not specified or None, the rating's
                  default data units are used, if specified. If the rating has no default data units, the rating units are used.
                * If specified as a TimeSeries or list of TimeSeries, this specifies the unit of the rated time series. If not specified or None, rating set's default
                  data unit for the dependent parameter, if any, is used. Otherwise, the dependent parameter's default unit will be used.
            rating_time (Optional[datetime], must be passed by name): The maximum create date for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified date (no ratings with create dates
                later than this time will be used).
            round (bool, optional, must be passed by name): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            Union[list[float], TimeSeries]: The dependent parameter values as described in `input` above
        """
        if isinstance(input, TimeSeries):
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self.reverse_rate_time_series(
                ts=input, unit=units, rating_time=rating_time, round=round
            )
        elif isinstance(input, list) and isinstance(input[0], float):
            return self.reverse_rate_values(
                dep_values=input,
                value_times=times,
                units=units,
                rating_time=rating_time,
                round=round,
            )
        else:
            raise TypeError(f"Unexpected type for input: {input.__class__.__name__}")

    @property
    def specification(self) -> RatingSpecification:
        """
        The [RatingSpecification](#RatingSpecification) of the rating set

        Operations:
            Read-Only
        """
        return self._specification

    @property
    def template(self) -> RatingTemplate:
        """
        The [RatingTemplate](#RatingTemplate) of the rating set

        Operations:
            Read-Only
        """
        return self._specification.template
