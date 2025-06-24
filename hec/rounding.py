"""
Module for various rounding classes
"""

import math
from typing import Any, Sequence


class UsgsRounder:
    """
    Provides functionality of USGS rounding arrays (called rounding specifications in this package).
    The full description of using rounding arrays can be found in Section 3.5 (Data Rounding Convention) of the
    [ADAPS Section of the National Water Information System User's Manual]("http://pubs.usgs.gov/of/2003/ofr03123/").

    Specifically, the rounding specifications are strings of 10 digits with the following meanings (left to right):
    1. Number of significant digits for values < 0.01
    2. Number of significant digits for values >= 0.01 and < 0.1
    3. Number of significant digits for values >= 0.1 and < 1.0
    4. Number of significant digits for values >= 1.0 and < 10
    5. Number of significant digits for values >= 10 and < 100
    6. Number of significant digits for values >= 100 and < 1000
    7. Number of significant digits for values >= 1,000 and < 10,000
    8. Number of significant digits for values >= 10,000 and < 100,000
    9. Number of significant digits for values >= 100,000
    10. Maximum number of decimal places regardless of magnitude
    """

    _default = "4444444444"

    def __init__(self, rounding_spec: str = _default):
        _rounding_spec: str
        self.rounding_spec = rounding_spec

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, UsgsRounder):
            return False
        return self.rounding_spec == other.rounding_spec

    def __repr__(self) -> str:
        return f"hec.UsgsRounder('{self._rounding_spec}')"

    def __str__(self) -> str:
        return self._rounding_spec

    def round_f(
        self, values: Sequence[float], round_half_even: bool = True
    ) -> list[float]:
        return [float(v) for v in self.round_s(values)]

    def round_s(
        self, values: Sequence[float], round_half_even: bool = True
    ) -> list[str]:
        results: list[str] = []
        for value in values:
            if not math.isfinite(value):
                results.append(str(value))
                continue
            max_dec_places = int(self.rounding_spec[-1])
            format = f".{max_dec_places}f"
            if value == 0.0:
                results.append(f"{0.:{format}}")
                continue
            magnitude = int(math.floor(math.log10(abs(value))))
            index = min(5, max(-3, magnitude)) + 3
            sig_digits = int(self._rounding_spec[index])

            if sig_digits + magnitude < sig_digits:
                sig_digits = min(max_dec_places, sig_digits + magnitude + 1)
            factor = math.pow(10, magnitude - sig_digits + 1)
            value /= factor
            sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
            integer = int(value)
            fraction = abs(value - integer)
            if abs(fraction - 0.5) < 1.0e-8:
                if round_half_even and not integer % 2:
                    pass
                else:
                    integer += sign
            else:
                integer = int(value + 0.5 * sign)
            result = f"{float(integer * factor):{format}}".rstrip("0")
            if result.endswith("."):
                result += "0"
            results.append(result)
        return results

    @property
    def rounding_spec(self) -> str:
        return self._rounding_spec

    @rounding_spec.setter
    def rounding_spec(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"Expected str for 'rounding_spec', got {value.__class__.__name__}"
            )
        if not value.isdigit() or len(value) != 10:
            raise ValueError(
                f"Expected a 10-digit string for 'rounding_spec', got '{value}'"
            )
        self._rounding_spec = value
