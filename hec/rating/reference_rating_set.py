from datetime import datetime
from typing import Any, Optional, Union, cast

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

    def rate_values(
        self,
        ind_values: list[list[float]],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRatingSet
        assert self._datastore is not None
        if value_times is None and self.default_data_time is not None:
            value_times = len(ind_values[0]) * [cast(datetime, self._default_data_time)]
        if units is None:
            unit_list = (
                self.default_data_units
                if self.default_data_units is not None
                else self.rating_units
            )
            _units = f"{','.join(unit_list[:-1])};{unit_list[-1]}"
        else:
            _units = units
        response = self._datastore.native_data_store.ratings.ratings.rate_values(
            rating_id=self._specification.name,
            office_id=self._specification.template.office,
            units=_units,
            values=ind_values,
            times=value_times,
            rating_time=rating_time,
            round=round,
        )
        return cast(list[float], cast(dict[str, Any], response)["values"])

    def reverse_rate_values(
        self,
        dep_values: list[float],
        value_times: Optional[list[datetime]] = None,
        units: Optional[str] = None,
        rating_time: Optional[datetime] = None,
        round: bool = False,
    ) -> list[float]:
        # docstring is in AbstractRatingSet
        assert self._datastore is not None
        if value_times is None and self.default_data_time is not None:
            value_times = len(dep_values) * [cast(datetime, self._default_data_time)]
        if units is None:
            unit_list = (
                self.default_data_units
                if self.default_data_units is not None
                else self.rating_units
            )
            _units = f"{unit_list[0]};{unit_list[1]}"
        else:
            _units = units
        response = (
            self._datastore.native_data_store.ratings.ratings.reverse_rate_values(
                rating_id=self._specification.name,
                office_id=self._specification.template.office,
                units=_units,
                values=dep_values,
                times=value_times,
                rating_time=rating_time,
                round=round,
            )
        )
        return cast(list[float], cast(dict[str, Any], response)["values"])
