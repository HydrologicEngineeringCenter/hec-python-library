import re
from datetime import datetime
from typing import Any, Optional, Union, cast

import numpy as np

import hec

from .abstract_rating_set import AbstractRatingSet, AbstractRatingSetException


class ReferenceRatingSetException(AbstractRatingSetException):
    pass


class ReferenceRatingSet(AbstractRatingSet):
    """
    A sub-class of [AbstractRatingSet](#AbstractRatingSet) that performs all ratings in the CWMS database
    """

    def __init__(
        self,
        specification: Any,
        **kwargs: Any,
    ):
        """
        Initializer for ReferenceRatingSet objects.

        Args:
            specification (Any): A [RatingSpecification](#RatingSpecification) object to initialize from.
                This is typed as `Any` to avoid circular import dependencies.
            datastore ([CwmsDataStore](datastore.html#CwmsDataStore), must be passed by name): The [CwmsDataStore](datastore.html#CwmsDataStore)
                object used to perform the ratings in the database.

        Raises:
            TypeError: if `specification` is not a [RatingSpecification](#RatingSpecification) object.
        """
        super().__init__(specification, **kwargs)
        self._datastore: Optional[hec.datastore.CwmsDataStore] = None
        for kw in kwargs:
            if kw == "datastore":
                argval = kwargs[kw]
                if not isinstance(argval, hec.datastore.CwmsDataStore):
                    raise TypeError(
                        f"Expected CwmsDataStore for {kw}, got {argval.__class__.__name__}"
                    )
                self._datastore = argval
            else:
                raise ValueError(f"Unexpected keyword argument: {kw}")
        if self._datastore is None:
            raise ReferenceRatingSetException(
                "Required parameter 'datastore' not specified."
            )
        if self._has_elev_param():
            self._vertical_datum_info = cast(
                hec.location.Location,
                self._datastore.retrieve(self._specification.location.name),
            )._vertical_datum_info
            self._default_data_veritcal_datum = (
                self._vertical_datum_info.native_datum
                if self._vertical_datum_info
                else None
            )

    def rate_values(
        self,
        ind_values: list[list[float]],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRatingSet
        assert self._datastore is not None
        list_count = len(ind_values)
        if list_count != self.template.ind_param_count:
            raise ReferenceRatingSetException(
                f"Expected {self.template.ind_param_count} lists of input values, got {list_count}"
            )
        value_count = len(ind_values[0])
        for i in range(1, list_count):
            if len(ind_values[i]) != value_count:
                raise ReferenceRatingSetException(
                    f"Expected all input value lists to be of lenght {value_count}, "
                    f"got {len(ind_values[i])} on value list {i+1}."
                )
        if value_times is None:
            if self.default_data_time is not None:
                value_times = len(ind_values[0]) * [
                    cast(datetime, self._default_data_time)
                ]
            else:
                value_times = len(ind_values[0]) * [datetime.now()]
        times = [(int(dt.timestamp()) * 1000) for dt in value_times]
        _units = units if units else self._default_data_units
        if not _units:
            raise ReferenceRatingSetException(
                "Cannot perform rating. No data units are specified and rating set has no defaults"
            )
        if len(re.split(r"[;,]", cast(str, _units))) != list_count + 1:
            raise ReferenceRatingSetException(
                f"Expected {list_count+1} units, got {len(_units)}"
            )
        vd: Optional[str] = None
        if self._has_elev_param() and vertical_datum is not None:
            if hec.parameter._ngvd29_pattern.match(vertical_datum):
                vd = hec.parameter._NGVD29
            elif hec.parameter._navd88_pattern.match(vertical_datum):
                vd = hec.parameter._NAVD88
            elif hec.parameter._other_datum_pattern.match(vertical_datum):
                vd = hec.parameter._OTHER_DATUM
            else:
                raise ReferenceRatingSetException(
                    f"Invalid vertical datum: {vertical_datum}. Must be one of "
                    f"{hec.parameter._NGVD29}, {hec.parameter._NAVD88}, or {hec.parameter._OTHER_DATUM}"
                )
            if (
                self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None:
                    if bool(offset.magnitude):
                        for i in range(list_count):
                            if self.template.ind_params[i].startswith("Elev"):
                                offset_value = -offset.to(_units[i]).magnitude
                                ind_values[i] = [
                                    ind_values[i][j] + offset_value
                                    for j in range(value_count)
                                ]
        fake_values = [np.nanmean(iv) for iv in ind_values]
        masks = [[True if np.isnan(v) else False for v in iv] for iv in ind_values]
        mask = [not any(m) for m in list(zip(*masks))]
        response = self._datastore.native_data_store.ratings.ratings.rate_values(
            rating_id=self._specification.name,
            office_id=self._specification.template.office,
            units=_units,
            values=[
                [fake_values[i] if np.isnan(v) else v for v in ind_values[i]]
                for i in range(len(ind_values))
            ],
            times=times,
            rating_time=(
                int(rating_time.timestamp() * 1000) if rating_time else rating_time
            ),
            round=round,
        )
        response_values = cast(list[float], cast(dict[str, Any], response)["values"])
        if vd is not None and self.template.dep_param.startswith("Elev"):
            if (
                self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None and bool(offset.magnitude):
                    offset_value = offset.to(_units[-1]).magnitude
                    response_values = [v + offset_value for v in response_values]
        return [
            response_values[i] if mask[i] else np.nan
            for i in range(len(response_values))
        ]

    def reverse_rate_values(
        self,
        dep_values: list[float],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        vertical_datum: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRatingSet
        assert self._datastore is not None
        if value_times is None:
            if self.default_data_time is not None:
                value_times = len(dep_values) * [
                    cast(datetime, self._default_data_time)
                ]
            else:
                value_times = len(dep_values) * [datetime.now()]
        times = [(int(dt.timestamp()) * 1000) for dt in value_times]
        _units = units if units else self._default_data_units
        if not _units:
            raise ReferenceRatingSetException(
                "Cannot perform rating. No data units are specified and rating set has no defaults"
            )
        if len(re.split(r"[;,]", cast(str, units))) != 2:
            raise ReferenceRatingSetException(f"Expected 2 units, got {len(_units)}")
        vd: Optional[str] = None
        if self._has_elev_param() and vertical_datum is not None:
            if hec.parameter._ngvd29_pattern.match(vertical_datum):
                vd = hec.parameter._NGVD29
            elif hec.parameter._navd88_pattern.match(vertical_datum):
                vd = hec.parameter._NAVD88
            elif hec.parameter._other_datum_pattern.match(vertical_datum):
                vd = hec.parameter._OTHER_DATUM
            else:
                raise ReferenceRatingSetException(
                    f"Invalid vertical datum: {vertical_datum}. Must be one of "
                    f"{hec.parameter._NGVD29}, {hec.parameter._NAVD88}, or {hec.parameter._OTHER_DATUM}"
                )
            if (
                self.template.dep_param.startswith("Elev")
                and self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None:
                    if bool(offset.magnitude):
                        offset_value = -offset.to(
                            re.split(r"[;,]", cast(str, _units))[0]
                        ).magnitude
                        dep_values = [v + offset_value for v in dep_values]
        fake_value = np.nanmean(dep_values)
        mask = [False if np.isnan(v) else True for v in dep_values]
        response = (
            self._datastore.native_data_store.ratings.ratings.reverse_rate_values(
                rating_id=self._specification.name,
                office_id=self._specification.template.office,
                units=_units,
                values=[v if not np.isnan(v) else fake_value for v in dep_values],
                times=times,
                rating_time=(
                    int(rating_time.timestamp() * 1000) if rating_time else rating_time
                ),
                round=round,
            )
        )
        response_values = cast(list[float], cast(dict[str, Any], response)["values"])
        if vd is not None and self.template.ind_params[0].startswith("Elev"):
            if (
                self._vertical_datum_info
                and self._vertical_datum_info.native_datum
                and vd != self._vertical_datum_info.native_datum
            ):
                offset = self._vertical_datum_info.get_offset_to(vd)
                if offset is not None and bool(offset.magnitude):
                    offset_value = offset.to(
                        re.split(r"[;,]", cast(str, _units))[0]
                    ).magnitude
                    response_values = [v + offset_value for v in response_values]
        return [
            response_values[i] if mask[i] else np.nan
            for i in range(len(response_values))
        ]
