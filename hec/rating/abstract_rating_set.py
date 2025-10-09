from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Sequence, Union, cast

import numpy as np

import hec
from hec.rating.rating_specification import RatingSpecification
from hec.rating.rating_template import RatingTemplate
from hec.shared import RatingException
from hec.timeseries import TimeSeries

from ..parameter import (
    _NAVD88,
    _NGVD29,
    _OTHER_DATUM,
    ElevParameter,
    Parameter,
    _navd88_pattern,
    _ngvd29_pattern,
    _other_datum_pattern,
)


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
        self._default_data_vertical_datum: Optional[str] = None
        self._vertical_datum_info: Optional[ElevParameter._VerticalDatumInfo] = None
        self._rating_time: Optional[datetime] = datetime.max
        self._specification = specification.copy()

    def _has_elev_param(self) -> bool:
        return (
            any(
                map(
                    lambda s: s.split("-")[0] == "Elev",
                    self._specification.template.ind_params,
                )
            )
            or self.specification.template.dep_param.split("-")[0] == "Elev"
        )

    def _rate_time_series(
        self,
        ts: Union[TimeSeries, Sequence[TimeSeries]],
        unit: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> TimeSeries:
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
        for i in range(ts_count):
            if (
                ts_list[i].parameter.base_parameter == "Elev"
                and ts_list[i].vertical_datum_info is not None
            ):
                if (
                    cast(
                        hec.parameter.ElevParameter._VerticalDatumInfo,
                        ts_list[i].vertical_datum_info,
                    ).native_datum
                    is None
                ):
                    raise AbstractRatingSetException(
                        f"Time series {ts_list[i].name} must have native vertical datum info since vertical "
                        f"datum of {vertical_datum} is specified to rate() method"
                    )
                ts_list[i] = ts_list[i].to(
                    cast(
                        str,
                        cast(
                            hec.parameter.ElevParameter._VerticalDatumInfo,
                            ts[i].vertical_datum_info,
                        ).native_datum,
                    )
                    if vertical_datum is None
                    else vertical_datum
                )
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
            rated_values = self._rate_values(
                ind_values=values,
                value_times=times,
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts_list[0].copy()
        if self.template.dep_param.startswith("Elev") and self._vertical_datum_info:
            vdi = self._vertical_datum_info.copy()
            vdi.unit_name = dep_unit
            elev_param = hec.parameter.ElevParameter(
                self.template.ind_params[0], str(vdi)
            )
            if vertical_datum:
                elev_param.current_datum = vertical_datum
            rated_ts.iset_parameter(elev_param)
        else:
            rated_ts.iset_parameter(Parameter(self.template.dep_param, dep_unit))
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def _rate_values(
        self,
        ind_values: list[list[float]],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        raise AbstractRatingSetException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

    def _reverse_rate_time_series(
        self,
        ts: TimeSeries,
        unit: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> TimeSeries:
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
            rated_values = self._reverse_rate_values(
                dep_values=ts.values,
                value_times=[datetime.fromisoformat(s) for s in ts.times],
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        else:
            rated_values = []
        rated_ts = ts.copy()
        if self.template.ind_params[0].startswith("Elev") and self._vertical_datum_info:
            vdi = self._vertical_datum_info.copy()
            vdi.unit_name = ind_unit
            elev_param = hec.parameter.ElevParameter(
                self.template.ind_params[0], str(vdi)
            )
            if vertical_datum:
                elev_param.current_datum = vertical_datum
            rated_ts.iset_parameter(elev_param)
        else:
            rated_ts.iset_parameter(Parameter(self.template.ind_params[0], ind_unit))
        if rated_ts.data is not None:
            rated_ts.data["value"] = rated_values
            rated_ts.data["quality"] = [5 if np.isnan(v) else 0 for v in rated_values]
        return rated_ts

    @abstractmethod
    def _reverse_rate_values(
        self,
        dep_values: list[float],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        raise AbstractRatingSetException(
            f"Method cannot be called on {self.__class__.__name__} object"
        )

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
        [rate](#AbstractRatingSet.rate).

        If `None` and no data units are specified, the rating methods will raise an exception.

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
    def default_data_vertical_datum(self) -> Optional[str]:
        """
        The default vertical datum for rating Elev parameter values.

        If not None, Elev parameter values will be converted to the default vertical datum before (input values) or after (output values) the rating is performed.

        If None, the native vertical datum will be used.

        When setting, must be None, NGVD-29, NAVD-99, or OTHER.

        Operations:
            Read/Write
        """
        return self._default_data_veritcal_datum

    @default_data_vertical_datum.setter
    def default_data_vertical_datum(
        self, default_vertical_datum: Optional[str]
    ) -> None:
        if self._vertical_datum_info is None:
            raise AbstractRatingSetException(
                "Rating set has no vertical datum information"
            )
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
        input: Union[list[float], list[list[float]], TimeSeries, Sequence[TimeSeries]],
        *,
        times: Optional[Union[datetime, list[datetime]]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> Any:
        """
        Rates independent parameter values and returns dependent parameter values.

        The times of the values are used in conjuction with the effective times of the individual ratings and rating set specification lookup methods
        to determine which ratings in the rating set are used - and the manner in which they are used - to compute the rated values.

        Args:
            input (Union[list[float], list[list[float]]): The input (independnent parameter(s)) values.
                * <b>If specified as a float or a list of floats</b> (for rating a single input value set using a single- or multi-independent-parameter rating set):
                    * The list must be of the same length as the number of independent parameters of the rating set.
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A single float is returned
                * <b>If specified as a list of lists of floats</b> (for rating a list of input value sets using a single- or multi-independent-parameter rating set):
                    * The list must be of the same length as the number of independent parameters of the rating set.
                    * Each list of values must have the same times and be of the same length
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A list of floats is returned
                * <b>If specified as a TimeSeries</b> (for rating a single time series using a single-independent-parameter rating set):
                    * The rating set must have a single independent parameter
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
                * <b>If specified as a list of TimeSeries</b> (for rating a list of time series using a multi-independent-parameter rating set):
                    * The list must be of the same length as the number of independent parameters of the rating set.
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the rated time series
                    * A time series is returned
            times (Optional[Union[datetime, list[datetime]]], must be passed by name): The date/times of the independent parameter values. Defaults to None.
                * If specified and not None:
                  * Specifying a datetime object is the same as specifying that datetime object in a list of length 1.
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If `None` or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of floats or a list of list of floats:
                    * Specifies units of the independent parameter values and the rated values as comma-delimited string of
                      independent value units concatendated with a semicolon and the dependent parameter unit (e.g., "ft;ac-ft", "unit,ft,ft;cfs").
                    * If not specified or None:
                        * The rating's default data units, if any, are used
                        * If the rating has no default data units, an exception is raised.
                * If `input` is a TimeSeries or list of TimeSeries:
                    * Specifies the unit of the rated (dependent parameter) time series.
                    * If not specified or None:
                        * The rating's default data units, if any, are used
                        * If the rating has no default data units, an exception is raised.
            vertical_datum (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of floats or a list of list of floats, this specifies:
                    * Specifies:
                        * The vertical datum of any input (independent parameter) elevation values
                        * The desired vertical datum of any rated (dependent parameter) elevation values.
                    * If None, or not specified, the location's native vertical datum is used.
                * If `input` is a TimeSeries or list of TimeSeries:
                    * Specifies only the desired vertical datum for any rated (dependent parameter) elevation values.
                    * Any input (independent parameter) elevation values will be in the vertical datum of the input time series.
                    * If None, or not specified, the location's native vertical datum is used.
            rating_time (Optional[datetime], must be passed by name): The maximum effective time and creation time for the rating set to use to perform the rating. Defaults to None.
                Causes the rating to be performed as if the current date/time were the specified time (no ratings with effective times or creation times
                later than this time will be used).
            round (bool, optional, must be passed by name): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            Any: The dependent parameter value(s) as described in `input` above
        """
        if isinstance(input, TimeSeries):
            # ------------------ #
            # single time series #
            # ------------------ #
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self._rate_time_series(
                ts=input, unit=units, rating_time=rating_time, round=round
            )
        elif isinstance(input, list) and isinstance(input[0], TimeSeries):
            # -------------------- #
            # multiple time series #
            # -------------------- #
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self._rate_time_series(
                ts=cast(list[TimeSeries], input),
                unit=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        elif isinstance(input, list) and isinstance(input[0], (int, float)):
            # ---------------- #
            # single value set #
            # ---------------- #
            return self._rate_values(
                ind_values=cast(list[list[float]], [[v] for v in input]),
                value_times=times if isinstance(times, (type(None), list)) else [times],
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )[0]
        elif (
            isinstance(input, list)
            and isinstance(input[0], list)
            and isinstance(input[0][0], (int, float))
        ):
            # ------------------- #
            # multiple value sets #
            # ------------------- #
            return self._rate_values(
                ind_values=cast(list[list[float]], input),
                value_times=times if isinstance(times, (type(None), list)) else [times],
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        else:
            raise TypeError(f"Unexpected type for input: {input.__class__.__name__}")

    def reverse_rate(
        self,
        input: Union[float, list[float], TimeSeries],
        *,
        times: Optional[Union[datetime, list[datetime]]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> Any:
        """
        Rates dependent parameter values and returns independent parameter values.

        May only be used on rating sets with a single independent parameter.

        <table border="1">
        <tr><th>Important Note</th></tr>
        <tr><td>
        Unlike single-independent-parameter ratings, two-dimensional (time and parameter value) rating sets are not
        generally invertible. That is, if you rate value <code>x</code> at time <code>t</code> using a rating set to generate value <code>y</code>, using
        the same rating set to reverse rate value <code>y</code> at time <code>t</code> will generally not result in <code>x</code>.
        </td></tr>
        </table>

        Args:
            input (Union[float, list[float], TimeSeries]): The input (dependent parameter) value(s).
                * <b>If specified as a float</b> (for reverse rating a single dependent parameter value using a single-independent-parameter rating set):
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of each independent and dependent parameter.
                    * A float is returned
                * <b>If specified as a lists of floats</b> (for reverse rating a multiple dependent parameter values using a single-independent-parameter rating set):
                    * The `times` parameter is used, if specified
                    * The `units`, if specified, is the unit of the independent and dependent parameters as shown below.
                    * A list of floats is returned
                * <b>If specified as a TimeSeries</b> (for reverse rating a dependent parameter time series using a single-independent-parameter rating set):
                    * The `times` parameter is not used and will cause an exception if specified
                    * The `units` parameter, if specified, is the unit of the reverse rated time series
                    * A time series is returned
            times (Optional[list[datetime]], must be passed by name): The date/times of the independent parameter value(s). Defaults to None.
                * If specified and not None:
                  * Specifying a datetime object is the same as specifying that datetime object in a list of length 1.
                  * If shorter than the independent parameter value list(s), the last time will be used for the remainging values.
                  * If longer than the independent parameter values list(s), the beginning portion of the list will be used.
                * If `None` or not specified:
                  * If the rating set's default data time is not None, that time is used for each value
                  * If the rating set's default data time is None, the current time is used for each value
            units (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of floats:
                    * Specifies units of the independent parameter value and the dependent parameter values as the
                    independent value units concatendated with a semicolon and the dependent parameter unit (e.g., "ft;ac-ft").
                    * If not specified or None:
                        * The rating's default data units, if any, are used
                        * If the rating has no default data units, an exception is raised.
                * If `input` is a TimeSeries:
                    * Specifies the unit of the reverse rated (independent parameter) time series.
                    * If not specified or None:
                        * The rating's default data units, if any, are used
                        * If the rating has no default data units, an exception is raised.
            vertical_datum (Optional[str], must be passed by name): Defaults to None.
                * If `input` is a list of list of floats, this specifies:
                    * Specifies:
                        * The vertical datum of any input (dependent parameter) elevation value
                        * The desired vertical datum of any reverse rated (independent parameter) elevation values.
                    * If None, or not specified, the location's native vertical datum is used.
                * If `input` is a TimeSeries:
                    * Specifies only the desired vertical datum for any reverse rated (independent parameter) elevation values.
                    * Any input (dependent parameter) elevation values will be in the vertical datum of the input time series.
                    * If None, or not specified, the location's native vertical datum is used.
            rating_time (Optional[datetime], must be passed by name): The maximum effective time and creation time for the rating set to use to perform the reverse rating. Defaults to None.
                Causes the reverse rating to be performed as if the current date/time were the specified time (no ratings with effective times or creation times
                later than this time will be used).
            round (bool, optional, must be passed by name): Whether to use the rating set's specification's dependent rounding specification . Defaults to False.

        Returns:
            Any: The dependent parameter value(s) as described in `input` above
        """
        if isinstance(input, TimeSeries):
            if times:
                raise AbstractRatingSetException(
                    "May not specify times parameter when rating TimeSeires objects"
                )
            return self._reverse_rate_time_series(
                ts=input,
                unit=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        elif isinstance(input, list) and isinstance(input[0], float):
            return self._reverse_rate_values(
                dep_values=input,
                value_times=times if isinstance(times, (type(None), list)) else [times],
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )
        elif isinstance(input, float):
            return self._reverse_rate_values(
                dep_values=[input],
                value_times=times if isinstance(times, (type(None), list)) else [times],
                units=units,
                vertical_datum=vertical_datum,
                rating_time=rating_time,
                round=round,
            )[0]
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

    @property
    def vertical_datum_info(self) -> Optional[ElevParameter._VerticalDatumInfo]:
        """
        The vertical datum info of the rating set's specification's location, if any

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_info

    @property
    def vertical_datum_json(self) -> Optional[str]:
        """
        The vertical datum info of the rating set's specification's location, if any, as a JSON object

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_json

    @property
    def vertical_datum_xml(self) -> Optional[str]:
        """
        The vertical datum info of the rating set's specification's location, if any, as an XML instance

        Operations:
            Read-Only
        """
        return self._specification.location.vertical_datum_xml
