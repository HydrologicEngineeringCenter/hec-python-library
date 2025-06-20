from hec.datastore import dss_imported, required_dss_version

if not dss_imported:
    raise ImportError(
        f"Cannot import hec.rating.paired_data_rating module: please install the hec-dss-python module or upgrade to {required_dss_version}"
    )

from hec.parameter import Parameter
from typing import Any, Optional

import hecdss  # type: ignore
import numpy as np
import numpy.typing as npt
import pandas as pd

from hec.rating import rating_shared


class PairedDataException(rating_shared.RatingException):
    pass


class PairedData:

    def __init__(self, paired_data: hecdss.PairedData):
        if not isinstance(paired_data, hecdss.PairedData):
            raise TypeError(
                f"Expected hecdss.PairedData for 'paired_data', got {paired_data.__class__.__name__}"
            )
        if len(paired_data.ordinates) == 0:
            raise ValueError("hecdss.PairedData object has no ordinates")
        if len(paired_data.values) != len(paired_data.ordinates):
            raise ValueError(
                f"hecdss.PairedData object has different numbers of ordinates ({len(paired_data.ordinates)}) and values ({len(paired_data.values)})"
            )
        self._pathname = paired_data.id
        c_part = self._pathname.split("/")[3]
        self._param_names = []
        for _ in c_part.split("-"):
            param = Parameter(_)
            self._param_names.append(f"{param.base_parameter}" + f"{'-'+param.subname if param.subname else ''}")
        self._labels = paired_data.labels[:]
        num_curves = len(paired_data.values[0])
        if len(self._labels) == 1 and not self._labels[0]:
            self._labels = ["dep"]
        for i in range(1, len(paired_data.values)):
            if len(paired_data.values[i]) != num_curves:
                raise ValueError(
                    "hec.PairedData object has inconsistent number curve value"
                )
        self._ind_log = paired_data.type_independent.upper().startswith("LOG")
        self._dep_log = paired_data.type_dependent.upper().startswith("LOG")
        self._ind_unit = paired_data.units_independent
        self._dep_unit = paired_data.units_dependent
        self._ordinates2: Optional[npt.NDArray[np.float64]]
        try:
            self._ordinates2 = np.array([np.float64(s) for s in paired_data.labels])
        except:
            self._ordinates2 = None
        data = {"ind": paired_data.ordinates}
        values_T = paired_data.values.T
        if num_curves > len(self._labels):
            for i in range(num_curves):
                data[f"dep{i+1}"] = values_T[i]
        else:
            for i in range(num_curves):
                data[self._labels[i]] = values_T[i]
        self._data = pd.DataFrame(data)
