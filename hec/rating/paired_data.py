from typing import Any, Optional, Sequence, Union, cast

import hecdss  # type: ignore
import numpy as np
import numpy.typing as npt
import pandas as pd

import hec


class PairedDataException(hec.shared.RatingException):
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
            param = hec.parameter.Parameter(_)
            self._param_names.append(
                f"{param.base_parameter}"
                + f"{'-'+param.subname if param.subname else ''}"
            )
        self._labels = paired_data.labels[:]
        num_curves = len(paired_data.values[0])
        if num_curves == 1 and not self._labels[0]:
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
        if self._ind_log:
            arr = np.asarray(paired_data.ordinates)
            ordinates = np.full_like(arr, np.nan, dtype=np.float64)
            mask = arr > 0
            ordinates[mask] = np.log(arr[mask])
            if self._ordinates2:
                arr = np.asarray(self._ordinates2)
                self._ordinates2 = np.full_like(arr, np.nan, dtype=np.float64)
                mask = arr > 0
                self._ordinates2[mask] = np.log(arr[mask])
        else:
            ordinates = paired_data.ordinates
        data = {"ind": ordinates}
        values_T = paired_data.values.T
        if num_curves > len(self._labels):
            if len(self._param_names) == 3 and num_curves == 2:
                self._labels = self._param_names[1:]
                for i in range(num_curves):
                    data[self._labels[i]] = values_T[i]
            else:
                self._labels = []
                for i in range(num_curves):
                    label = f"dep{i+1}"
                    self._labels.append(label)
                    data[label] = values_T[i]
        else:
            for i in range(num_curves):
                data[self._labels[i]] = values_T[i]
        self._data = pd.DataFrame(data)
        if self._dep_log:
            for column_name in data:
                if column_name == "ind":
                    continue
                self._data[column_name] = np.where(
                    self._data[column_name] > 0, np.log(self._data[column_name]), np.nan
                )

    def rate(self, to_rate: Any, label: Optional[str] = None) -> Any:
        if to_rate is None:
            return None
        if label:
            for lbl in self._labels:
                if label.upper() == lbl.upper():
                    _label = lbl
                    break
            else:
                raise ValueError(f"No such column label: '{label}'")
        else:
            _label = "dep"
        if isinstance(to_rate, float):
            # ------------------- #
            # rate a single value #
            # ------------------- #
            if len(self._data.columns) > 2:
                raise PairedDataException(
                    "Multi-column PairedData object can't rate a single value with no label"
                )
            if self._ind_log:
                to_rate = np.log(to_rate)
                if np.isnan(cast(float, to_rate)):
                    return np.nan
            rated = np.interp(
                [to_rate],
                self._data["ind"],
                self._data[_label],
                left=np.nan,
                right=np.nan,
            )[0]
            if self._dep_log:
                rated = np.exp(rated)
            return float(rated)
        elif isinstance(to_rate, (list, tuple)):
            if isinstance(to_rate[0], float):
                if label:
                    # ------------------------------------------------- #
                    # rate a list of 1-value inputs on specified column #
                    # ------------------------------------------------- #
                    v = np.array(to_rate)
                    if self._ind_log:
                        rated = np.interp(
                            np.where(v > 0, np.log(v), np.nan),
                            self._data["ind"],
                            self._data[_label],
                            left=np.nan,
                            right=np.nan,
                        )
                    else:
                        rated = np.interp(
                            v,
                            self._data["ind"],
                            self._data[_label],
                            left=np.nan,
                            right=np.nan,
                        )
                    return rated
                elif len(to_rate) == 2:
                    # --------------------------- #
                    # rate a single 2-value input #
                    # --------------------------- #
                    if self._ordinates2 is None:
                        raise TypeError(
                            f"Expected float for 'to_rate', got {to_rate.__class__.__name__}"
                        )
                    if not isinstance(to_rate[1], float):
                        raise TypeError(
                            f"Expected float for 'to_rate[1]', got {to_rate[1].__class__.__name__}"
                        )
                    if self._ind_log:
                        to_rate = list(map(np.log, to_rate))
                    if any(map(np.isnan, to_rate)):
                        return np.nan
                    idx = np.searchsorted(self._ordinates2, to_rate[0]) - 1
                    if idx < 0 or idx == len(self._data) - 1:
                        return np.nan
                    fraction = float(to_rate[0] - self._ordinates2[idx]) / float(
                        self._ordinates2[idx + 1] - self._ordinates2[idx]
                    )
                    low_label = str(self._ordinates2[idx])
                    high_label = str(self._ordinates2[idx + 1])
                    low_val = float(
                        np.interp(
                            [to_rate[1]],
                            self._data["ind"],
                            self._data[low_label],
                            left=np.nan,
                            right=np.nan,
                        )[0]
                    )
                    if np.isnan(low_val):
                        return np.nan
                    high_val = float(
                        np.interp(
                            [to_rate[1]],
                            self._data["ind"],
                            self._data[high_label],
                            left=np.nan,
                            right=np.nan,
                        )[0]
                    )
                    if np.isnan(high_val):
                        return np.nan
                    rated = low_val + fraction * (high_val - low_val)
                    if self._dep_log:
                        rated = np.exp(rated)
                    return rated
                else:
                    # ------------------------------------------- #
                    # rate a list of 1-value inputs with no label #
                    # ------------------------------------------- #
                    if len(self._data.columns) > 2:
                        raise PairedDataException(
                            "Multi-column PairedData object can't rate a list of single values with no label"
                        )
                    if "dep" not in self._labels:
                        raise PairedDataException(
                            "Unexpected error finding 'dep' column"
                        )
                    v = np.array(to_rate)
                    if self._ind_log:
                        rated = np.interp(
                            np.where(v > 0, np.log(v), np.nan),
                            self._data["ind"],
                            self._data["dep"],
                            left=np.nan,
                            right=np.nan,
                        )
                    else:
                        rated = np.interp(
                            v,
                            self._data["ind"],
                            self._data["dep"],
                            left=np.nan,
                            right=np.nan,
                        )
                    if self._dep_log:
                        rated = np.exp(rated)
                    return rated
            elif isinstance(to_rate[0], (list, tuple)):
                # ----------------------------- #
                # rate a list of 2-value inputs #
                # ----------------------------- #
                if self._ordinates2 is None:
                    raise TypeError(f"Object is not a 2-D PairedData object")
                if not all([len(v) == 2 for v in to_rate]):
                    raise PairedDataException(
                        "2-D PairedData object required each input to be of length 2"
                    )
                if label:
                    raise ValueError("Cannot specify a label for 2-D PairedData object")
                rated = []
                if isinstance(to_rate[0][0], float):
                    for i in range(len(to_rate)):
                        if not isinstance(to_rate[i][1], float):
                            raise TypeError(
                                f"Expected float for 'to_rate[{i}][1]', got {to_rate[i][1].__class__.__name__}"
                            )
                        idx = np.searchsorted(self._ordinates2, to_rate[i][0]) - 1
                        if idx < 0 or idx == len(self._data) - 1:
                            rated.append(np.nan)
                            continue
                        fraction = float(to_rate[i][0] - self._ordinates2[idx]) / float(
                            self._ordinates2[idx + 1] - self._ordinates2[idx]
                        )
                        low_label = str(self._ordinates2[idx])
                        high_label = str(self._ordinates2[idx + 1])
                        low_val = float(
                            np.interp(
                                [to_rate[i][1]],
                                self._data["ind"],
                                self._data[low_label],
                                left=np.nan,
                                right=np.nan,
                            )[0]
                        )
                        if np.isnan(low_val):
                            rated.append(np.nan)
                            continue
                        high_val = float(
                            np.interp(
                                [to_rate[i][1]],
                                self._data["ind"],
                                self._data[high_label],
                                left=np.nan,
                                right=np.nan,
                            )[0]
                        )
                        if np.isnan(high_val):
                            rated.append(np.nan)
                            continue
                        rated.append(low_val + fraction * (high_val - low_val))
                        if self._dep_log:
                            rated[-1] = np.exp(rated[-1])
                    return rated
                elif isinstance(to_rate[0], hec.timeseries.TimeSeries):
                    if not isinstance(to_rate[1], hec.timeseries.TimeSeries):
                        raise TypeError(
                            f"Expected float for 'to_rate[1]', got {to_rate[1].__class__.__name__}"
                        )
                    if not len(to_rate[0]) or not len(to_rate[1]):
                        raise ValueError("Cannot rate an empty time series")
                    count = min(len(to_rate[0]), len(to_rate(1)))
                    copy = to_rate[0].copy().iexpand()[:count]
                    v0 = to_rate[0].values
                    v1 = to_rate[1].values
                    copy.data["value"] = self.rate(
                        [[v0[i], v1[i]] for i in range(count)]
                    )
                    return copy
                else:
                    raise TypeError(
                        f"Expected float, list, tuple, or TimeSeries for 'to_rate[0]', got {to_rate[0].__class__.__name__}"
                    )
        elif isinstance(to_rate, hec.timeseries.TimeSeries):
            if not len(to_rate):
                raise ValueError("Cannot rate an empty time series")
            copy = to_rate.copy().iexpand()
            data = cast(pd.DataFrame, copy.data)
            data["value"] = self.rate(data["value"].to_list(), label=label)
            return copy
        else:
            raise TypeError(
                f"Expected float, list, or tuple for 'value', got {to_rate.__class__.__name__}"
            )
