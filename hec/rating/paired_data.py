import json
import re
from typing import Any, Optional, Sequence, Union, cast

import hecdss  # type: ignore
import numpy as np
import numpy.typing as npt
import pandas as pd

import hec


def _is_dss_pd_pathname(id: str) -> bool:
    A, B, C, D, E, F = 1, 2, 3, 4, 5, 6
    parts = id.split("/")
    if len(parts) != 8:
        return False
    c_parts = parts[C].split("-")
    if len(c_parts) == 1:
        return False
    for part in [part.strip() for part in c_parts]:
        try:
            hec.parameter.Parameter(re.split("[^a-zA-Z]+", part)[0])
        except hec.parameter.ParameterException:
            return False
    return True


class PairedDataException(hec.shared.RatingException):
    """
    Exception type for paired data operations
    """

    pass


class PairedData:
    """
    Class for directly using HEC-DSS Paired Data records for rating operations.

    Unlike the HEC Rating API, PairedData objects support multiple dependent parameters for a single independent parameter

    Multiple dependent parameters may be specified:
    * In the parameter portion of the name (e.g., HEC-DSS C pathname part):
        * Example: C part = 'Elev-Area-Stor' with no labels specifies 'Elev' as the independent parameter, and 'Area' and 'Stor' as the dependent parameters.
    * In the `labels` field of the PaireData object:
        * Example: C part = 'Stage-Currency' with labels of 'residential', 'agricultural', 'industrial', and 'municipal' specifies 'Stage' as the
        independent parameter, 'Currency' as the dependent parameter (as in a stage-damage curve) and the labels as the dependent sub-parameters
    * If labels are present and are all string representations of increasing numeric values, in addition to being able to perform a rating using the `label`
    keyword argument, the rating can be used as a rating with two independent parameters and one dependent parameter. The first indpendent parameter corresponds
    to the normal independent parameter of the rating and the second independent parameter corresponds to the numeric labels. Reverse ratings cannot be performed
    when using the PairedData object in this manner.

    When calling the `rate` or `reverse_rate` methods of a PairedData object that has more than one dependent parameter or sub-parameter, the `label` keyword argument
    must be provided to specify the dependent parameter or sub-parameter to use

    Unlike the Java hec.hecmath.PairedDataMath class, PairedData objects support linear and logarithmic interpolation of both independent and dependent parameters
    separately instead of requiring the same method on both parameters. However, PairedData object do not currently suppport the probability or percent axis type nor the
    horizontal axis selection that hec.HecMath.PairedDataMath and the hec.io.PairedDataContainer objects use for plotting control.

    PairedData objects are serialized to/from HEC-DSS files using the hec.DssDataStore class
    """

    def __init__(self, init_from: Union[hecdss.PairedData, str]):
        """
        Initializer

        Args:
            init_from (Union[hecdss.PairedData, str]): Either a hecdss.PairedData object or a JSON string.
                * **hecdss.PairedData**: A paired data record from an HEC-DSS file as retrieved by `hecdss.get()`
                * **str**: A JSON string of the same format as produced by the [`json`](#PairedData.json) property. The string must contain a JSON object with the following members:
                    * **`name` (string, required)**: The object's name. If this is a valid HEC-DSS paired data pathname, the parameters will be parsed from the C pathname part unless `parameters` is specified.
                    * **`ind_unit` (string, required)**: The unit of the independent parameter values
                    * **`ind_log` (boolean, optional)**: Whether to interpolate the independent parameter values logarithmically. Defaults to false.
                    * **`dep_unit` (string, required)**: The unit of the independent parameter values
                    * **`dep_log` (boolean, optional)**: Whether to interpolate the dependent parameter values logarithmically. Defaults to false.
                    * **`parameters` (array of strings, optional)**: The independent (first string) and dependent (subsequent strings)parameter names. If not specified, parameters are taken from the `name` member, if possible.
                    * **`labels` (array of strings, optional)**: The dependent sub-parameters or second independent parameter values, depending on usage.
                    * **`values` (array of array of numbers, required)**: The independent (first array) and dependent (subsequend arrays) parameter values.
        """
        self._name: str
        self._parameters: Sequence[str]
        self._ind_unit: str
        self._dep_unit: str
        self._ind_log: bool = False
        self._dep_log: bool = False
        self._labels: Sequence[str]
        self._ordinates2: Optional[npt.NDArray[np.float64]] = None
        self._can_reverse: dict[str, bool] = {}
        if isinstance(init_from, str):
            # --------------------- #
            # init from JSON string #
            # --------------------- #
            info: dict[str, Any] = json.loads(init_from)
            if not "name" in info:
                raise ValueError("JSON string must contain 'name'")
            if not isinstance(info["name"], str):
                raise TypeError(
                    f"Exepected JSON 'name' item to be str, got {info['name'].__class__.__name__}"
                )
            self._name = info["name"]
            if _is_dss_pd_pathname(self._name):
                c_part = self._name.split("/")[3]
                self._parameters = []
                for _ in c_part.split("-"):
                    param = hec.parameter.Parameter(_)
                    self._parameters.append(
                        f"{param.base_parameter}"
                        + f"{'-'+param.subname if param.subname else ''}"
                    )
            if not "ind_unit" in info:
                raise ValueError("JSON string must contain 'ind_unit'")
            if not isinstance(info["name"], str):
                raise TypeError(
                    f"Exepected JSON 'ind_unit' item to be str, got {info['ind_unit'].__class__.__name__}"
                )
            self._ind_unit = info["ind_unit"]
            if "ind_log" in info:
                if not isinstance(info["ind_log"], bool):
                    raise TypeError(
                        f"Exepected JSON 'ind_log' item to be bool, got {info['ind_log'].__class__.__name__}"
                    )
                self._ind_log = info["ind_log"]
            if not "dep_unit" in info:
                raise ValueError("JSON string must contain 'dep_unit'")
            if not isinstance(info["name"], str):
                raise TypeError(
                    f"Exepected JSON 'dep_unit' item to be str, got {info['dep_unit'].__class__.__name__}"
                )
            self._dep_unit = info["dep_unit"]
            if "dep_log" in info:
                if not isinstance(info["dep_log"], bool):
                    raise TypeError(
                        f"Exepected JSON 'dep_log' item to be bool, got {info['dep_log'].__class__.__name__}"
                    )
                self._dep_log = info["dep_log"]
            if "parameters" in info:
                if not isinstance(info["parameters"], (list, tuple)):
                    raise TypeError(
                        f"Exepected JSON 'parameters' item to be list or tuple, got {info['parameters'].__class__.__name__}"
                    )
                self._parameters = []
                for _ in info["parameters"]:
                    param = hec.parameter.Parameter(_)
                    self._parameters.append(
                        f"{param.base_parameter}"
                        + f"{'-'+param.subname if param.subname else ''}"
                    )
            if "labels" in info and info["labels"] is not None:
                if not isinstance(info["labels"], (list, tuple)):
                    raise TypeError(
                        f"Exepected JSON 'labels' item to be list or tuple, got {info['labels'].__class__.__name__}"
                    )
                self._labels = info["labels"]
                if len(self._labels) > 0:
                    if len([l.upper() for l in set(self._labels)]) < len(
                        [l.upper() for l in self._labels]
                    ):
                        raise PairedDataException(
                            "Cannot have multiple labels with the same (case insenitive) value"
                        )
            elif len(self._parameters) == 2:
                self._labels = ["dep"]
            else:
                self._labels = self._parameters[1:]
            if not "values" in info:
                raise ValueError("JSON string must contain 'values'")
            if not isinstance(info["values"], (list, tuple)):
                raise TypeError(
                    f"Exepected JSON 'values' item to be list or tuple, got {info['values'].__class__.__name__}"
                )
            num_curves = len(info["values"]) - 1
            if not self._labels:
                self._labels = [f"dep{i}" for i in range(1, num_curves)]
            for i in range(1, len(info["values"])):
                if len(info["values"][i]) != len(info["values"][0]):
                    raise PairedDataException(
                        "Inconsistent lengths in JSON 'value' item"
                    )
            data = {"ind": info["values"][0]}
            for i in range(num_curves):
                data[self._labels[i]] = info["values"][i + 1]
            self._data = pd.DataFrame(data)
            try:
                self._ordinates2 = np.array([np.float64(s) for s in self._labels])
            except:
                self._ordinates2 = None
            if self._ordinates2 is None:
                if (
                    self._parameters
                    and not self._labels
                    and len(self._parameters) != num_curves + 1
                ):
                    raise PairedDataException(
                        f"Expected {num_curves+1} parameters, got {len(self._parameters)}"
                    )
            if self._labels and len(self._labels) != num_curves:
                raise PairedDataException(
                    f"Expected {num_curves} labels, got {len(self._labels)}: {self._labels}"
                )
        elif isinstance(init_from, hecdss.PairedData):
            # --------------------------- #
            # init from hecdss.PairedData #
            # --------------------------- #
            paired_data: hecdss.PairedData = init_from
            if len(paired_data.ordinates) == 0:
                raise ValueError("hecdss.PairedData object has no ordinates")
            if len(paired_data.values) != len(paired_data.ordinates):
                raise ValueError(
                    f"hecdss.PairedData object has different numbers of ordinates ({len(paired_data.ordinates)}) and values ({len(paired_data.values)})"
                )
            self._name = paired_data.id
            c_part = self._name.split("/")[3]
            self._parameters = []
            for _ in c_part.split("-"):
                param = hec.parameter.Parameter(_)
                self._parameters.append(
                    f"{param.base_parameter}"
                    + f"{'-'+param.subname if param.subname else ''}"
                )
            self._labels = paired_data.labels[:] if paired_data.labels else []
            if len(self._labels) > 0:
                if len([l.upper() for l in set(self._labels)]) < len(
                    [l.upper() for l in self._labels]
                ):
                    print(self._labels)
                    raise PairedDataException(
                        "Cannot have multiple labels with the same (case insenitive) value"
                    )
            num_curves = len(paired_data.values[0])
            if num_curves == 1:
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
                if len(self._parameters) == 3 and num_curves == 2:
                    self._labels = self._parameters[1:]
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
                        self._data[column_name] > 0,
                        np.log(self._data[column_name]),
                        np.nan,
                    )
        if any(np.diff(self._data["ind"]) < 0):
            raise PairedDataException(
                "Independent parameter is not in increasing order"
            )
        if self._ordinates2 is not None and np.any(np.diff(self._ordinates2) < 0):
            raise PairedDataException(
                "Second independent parameter is not monotonically increasing"
            )
        for column in self._data.columns:
            self._can_reverse[column] = not np.any(np.diff(self._data[column]) < 0)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PairedData):
            return False
        return other.json == self.json

    def __repr__(self) -> str:
        return f"<hec.rating.PairedData('{self.name}')>"

    def copy(self) -> "PairedData":
        """
        Returns a copy of this object

        Returns:
            PairedData: the copy
        """
        return PairedData(self.json)

    @property
    def data(self) -> pd.DataFrame:
        """
        Returns the internal pandas DataFrame object (not a copy)

        Operations:
            Read-Only
        """
        return self._data

    @property
    def dep_log(self) -> bool:
        """
        Returns whether the dependent parameter is interpolated logarithmically

        Operations:
            Read-Only
        """
        return self._dep_log

    @property
    def dep_unit(self) -> str:
        """
        Returns the dependent parameter unit

        Operations:
            Read-Only
        """
        return self._dep_unit

    @property
    def dep_values(self) -> Sequence[Sequence[float]]:
        """
        Returns the dependent parameter values

        Operations:
            Read-Only
        """
        return [self._data[c].to_list() for c in self._data.columns if c != "ind"]

    @property
    def ind_log(self) -> bool:
        """
        Returns whether the independent parameter is interpolated logarithmically

        Operations:
            Read-Only
        """
        return self._ind_log

    @property
    def ind_unit(self) -> str:
        """
        Returns the independent parameter unit

        Operations:
            Read-Only
        """
        return self._ind_unit

    @property
    def ind_values(self) -> Sequence[float]:
        """
        Returns the independent parameter values

        Operations:
            Read-Only
        """
        return self._data["ind"].to_list()

    @property
    def json(self) -> str:
        """
        Returns a string containing a JSON representation of the object

        Operations:
            Read-Only
        """
        return json.dumps(
            {
                "name": self.name,
                "ind_unit": self.ind_unit,
                "ind_log": self.ind_log,
                "dep_unit": self.dep_unit,
                "dep_log": self.dep_log,
                "parameters": self.parameters,
                "labels": self.labels if self.labels != ["dep"] else None,
                "values": self.values,
            }
        )

    @property
    def labels(self) -> Optional[Sequence[str]]:
        """
        Returns the object's labels, if any

        Operations:
            Read-Only
        """
        return self._labels

    @property
    def name(self) -> str:
        """
        Returns the object's name

        Operations:
            Read-Only
        """
        return self._name

    @property
    def parameters(self) -> Sequence[str]:
        """
        Returns the object's parameters

        Operations:
            Read-Only
        """
        return self._parameters

    def rate(self, to_rate: Any, label: Optional[str] = None) -> Any:
        """
        Rates a single value, list of values, list of value sets, time series, or time series set.

        Args:
            to_rate (Any): The item(s) to be rated
                * **float**: returns a single dependent value for a single independent value
                * **sequence of floats**: returns a list of dependent values for a sequence of single independent values
                * **TimeSeries object**: returns a `TimeSeries` of dependent values for a single `TimeSeries` of independent values
                * **sequence of two-value sequences of floats**: returns a list of dependent values for a sequence of indepentent value sets
                * **sequence of two TimeSeries**: returns a `TimeSeries` of dependent values for set of two independent value time series
            label (Optional[str], optional): Specifies which dependent parameter or sub-parameter to use to rate single independent values.
                Must be specified when rating a single independent parameter with a multi-dependent parameter PairedData object. Must be one of the object's
                dependent parameters or sub-parameters. Defaults to None.

        Returns:
            Any: The rated value(s)
        """
        if to_rate is None:
            return None
        if label:
            if not self._labels:
                raise ValueError(f"No such column label: '{label}'")
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
        elif isinstance(to_rate, (list, tuple, np.ndarray)):
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
                    if self._dep_log:
                        rated = np.exp(rated)
                    return rated
                else:
                    # ------------------------------------------- #
                    # rate a list of 1-value inputs with no label #
                    # ------------------------------------------- #
                    if not self._labels or "dep" not in self._labels:
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
            elif isinstance(to_rate[0], (list, tuple, np.ndarray)):
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
                        x1: float = to_rate[i][0]
                        x2: float = to_rate[i][1]
                        if self._ind_log:
                            x1, x2 = np.log([x1, x2])
                        if not all(np.isfinite([x1, x2])):
                            rated.append(np.nan)
                            continue
                        idx = int(np.searchsorted(self._ordinates2, x2) - 1)
                        if idx < 0 or idx == len(self._data) - 1:
                            if x2 == self._ordinates2[0]:
                                idx = 0
                            elif x2 == self._ordinates2[-1]:
                                idx = len(self._ordinates2) - 2
                            else:
                                rated.append(np.nan)
                                continue
                        if idx == len(self._ordinates2) - 1:
                            if x2 == self._ordinates2[-1]:
                                idx = len(self._ordinates2) - 2
                            else:
                                rated.append(np.nan)
                                continue
                        fraction = float(x2 - self._ordinates2[idx]) / float(
                            self._ordinates2[idx + 1] - self._ordinates2[idx]
                        )
                        low_label = str(self._ordinates2[idx])
                        if low_label not in cast(list[str], self._labels):
                            low_label = str(int(self._ordinates2[idx]))
                            if low_label not in cast(list[str], self._labels):
                                raise PairedDataException(
                                    f"Cannot determine column label for value {self._ordinates2[idx]}"
                                )
                        high_label = str(self._ordinates2[idx + 1])
                        if high_label not in cast(list[str], self._labels):
                            high_label = str(int(self._ordinates2[idx + 1]))
                            if high_label not in cast(list[str], self._labels):
                                raise PairedDataException(
                                    f"Cannot determine column label for value {self._ordinates2[idx+1]}"
                                )
                        low_val = float(
                            np.interp(
                                [x1],
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
                                [x1],
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
                count = min(len(to_rate[0]), len(to_rate[1]))
                copy = to_rate[0].copy().iexpand()[:count]
                v0 = to_rate[0].values
                v1 = to_rate[1].values
                cast(pd.DataFrame, copy.data)["value"] = self.rate(
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

    def reverse_rate(self, to_rate: Any, label: Optional[str] = None) -> Any:
        """
        Reverse rates a single value, list of values, or time series

        Args:
            to_rate (Any): The item(s) to be reverse rated
                * **float**: returns an independent value for a dependent value
                * **sequence of floats**: returns a list of independent values for a sequence of dependent values
                * **TimeSeries object**: returns a `TimeSeries` of independent values for a `TimeSeries` of dependent values
            label (Optional[str], optional): Specifies which dependent parameter or sub-parameter to use to reverse rate dependent values.
                Must be specified when reverse rating a single dependent parameter with a multi-dependent parameter PairedData object. Must be one of the object's
                dependent parameters or sub-parameters. Defaults to None.

        Returns:
            Any: The reverse rated value(s)
        """
        if to_rate is None:
            return None
        if label:
            if not self._labels:
                raise ValueError(f"No such column label: '{label}'")
            for lbl in self._labels:
                if label.upper() == lbl.upper():
                    _label = lbl
                    break
            else:
                raise ValueError(f"No such column label: '{label}'")
        else:
            _label = "dep"
        if not self._can_reverse[_label]:
            if _label == "dep":
                raise PairedDataException(
                    "Cannont reverse rate: dependent values are not in increasing order"
                )
            else:
                raise PairedDataException(
                    f"Cannont reverse rate: dependent values for '{_label}' are not in increasing order"
                )
        if isinstance(to_rate, float):
            # --------------------------- #
            # reverse rate a single value #
            # --------------------------- #
            if self._dep_log:
                to_rate = np.log(to_rate)
                if np.isnan(cast(float, to_rate)):
                    return np.nan
            rated = np.interp(
                [to_rate],
                self._data[_label],
                self._data["ind"],
                left=np.nan,
                right=np.nan,
            )[0]
            if self._ind_log:
                rated = np.exp(rated)
            return float(rated)
        elif isinstance(to_rate, (list, tuple, np.ndarray)):
            if isinstance(to_rate[0], float):
                if label:
                    # ------------------------------------------------- #
                    # reverse rate a list of inputs on specified column #
                    # ------------------------------------------------- #
                    v = np.array(to_rate)
                    if self._dep_log:
                        rated = np.interp(
                            np.where(v > 0, np.log(v), np.nan),
                            self._data[_label],
                            self._data["ind"],
                            left=np.nan,
                            right=np.nan,
                        )
                    else:
                        rated = np.interp(
                            v,
                            self._data[_label],
                            self._data["ind"],
                            left=np.nan,
                            right=np.nan,
                        )
                    if self._ind_log:
                        rated = np.exp(rated)
                    return rated
                else:
                    # ----------------------------------- #
                    # rate a list of inputs with no label #
                    # ----------------------------------- #
                    if len(self._data.columns) > 2:
                        raise PairedDataException(
                            "Multi-column PairedData object can't rate a list of single values with no label"
                        )
                    if not self._labels or "dep" not in self._labels:
                        raise PairedDataException(
                            "Unexpected error finding 'dep' column"
                        )
                    v = np.array(to_rate)
                    if self._dep_log:
                        rated = np.interp(
                            np.where(v > 0, np.log(v), np.nan),
                            self._data["dep"],
                            self._data["ind"],
                            left=np.nan,
                            right=np.nan,
                        )
                    else:
                        rated = np.interp(
                            v,
                            self._data["dep"],
                            self._data["ind"],
                            left=np.nan,
                            right=np.nan,
                        )
                    if self._ind_log:
                        rated = np.exp(rated)
                    return rated
            else:
                raise TypeError(
                    f"Expected float, list, tuple, or TimeSeries for 'to_rate[0]', got {to_rate[0].__class__.__name__}"
                )
        elif isinstance(to_rate, hec.timeseries.TimeSeries):
            if not len(to_rate):
                raise ValueError("Cannot rate an empty time series")
            copy = to_rate.copy().iexpand()
            data = cast(pd.DataFrame, copy.data)
            data["value"] = self.reverse_rate(data["value"].to_list(), label=label)
            return copy
        else:
            raise TypeError(
                f"Expected float, list, or tuple for 'value', got {to_rate.__class__.__name__}"
            )

    @staticmethod
    def transform(
        values1: Sequence[float], values2: Sequence[float]
    ) -> Sequence[Sequence[float]]:
        """
        Transforms two list of indpendent values (1st and 2nd independent values) to a list of value sets suitable for use in the [`rate`](#PairedData.rate) method

        Args:
            values1 (Sequence[float]): The values for the 1st independent parameter
            values2 (Sequence[float]): The vaules for the 2nd independent parameter

        Raises:
            ValueError: An list of value sets with each value set containing a value from the 1st and 2nd independent parameters

        Returns:
            list[list[float]]: _description_
        """
        if len(values1) != len(values2):
            raise ValueError("Arguments values1 and values2 must be of the same length")
        return list(zip(values1, values2))

    @property
    def values(self) -> Sequence[Sequence[float]]:
        """
        Returns the object's values (indpendent and dependent)

        Operations:
            Read-Only
        """
        return [self._data[c].to_list() for c in self._data.columns]
