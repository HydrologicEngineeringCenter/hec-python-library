"""
Provides quality code info and operations
"""

import os, re, sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)


class QualityException(Exception):
    pass


from typing import Any

(
    _SCREENED,
    _VALIDITY,
    _RANGE,
    _CHANGED,
    _REPL_CAUSE,
    _REPL_METHOD,
    _TEST_FAILED,
    _PROTECTION,
) = range(8)

_screened_values = {
    "UNSCREENED": 0,
    "SCREENED": 1,
}
_validity_values = {
    "UNKNOWN": 0,
    "OKAY": 1,
    "MISSING": 2,
    "QUESTIONABLE": 4,
    "REJECTED": 8,
}
_range_values = {
    "NO_RANGE": 0,
    "RANGE_1": 1,
    "RANGE_2": 2,
    "RANGE_3": 3,
}
_changed_values = {
    "ORIGINAL": 0,
    "MODIFIED": 1,
}
_repl_cause_values = {
    "NONE": 0,
    "AUTOMATIC": 1,
    "INTERACTIVE": 2,
    "MANUAL": 3,
    "RESTORED": 4,
}
_repl_method_values = {
    "NONE": 0,
    "LIN_INTERP": 1,
    "EXPLICIT": 2,
    "MISSING": 3,
    "GRAPHICAL": 4,
}
_test_failed_values = {
    "NONE": 0,
    "ABSOLUTE_VALUE": 1,
    "CONSTANT_VALUE": 2,
    "RATE_OF_CHANGE": 4,
    "RELATIVE_VALUE": 8,
    "DURATION_VALUE": 16,
    "NEG_INCREMENT": 32,
    "SKIP_LIST": 128,
    "USER_DEFINED": 512,
    "DISTRIBUTION": 1024,
}
_protection_values = {
    "UNPROTECTED": 0,
    "PROTECTED": 1,
}
_screened_ids = {v: k for k, v in _screened_values.items()}
_validity_ids = {v: k for k, v in _validity_values.items()}
_range_ids = {v: k for k, v in _range_values.items()}
_changed_ids = {v: k for k, v in _changed_values.items()}
_repl_cause_ids = {v: k for k, v in _repl_cause_values.items()}
_repl_method_ids = {v: k for k, v in _repl_method_values.items()}
_test_failed_ids = {v: k for k, v in _test_failed_values.items()}
_protection_ids = {v: k for k, v in _protection_values.items()}


def normalize_quality_code(code: int) -> int:
    return code & 0b1000_0011_0101_1111_1111_1111_1111_1111


def screened_message(code: int) -> str:
    return _screened_ids[code]


def validity_message(code: int) -> str:
    return _validity_ids[code]


def range_message(code: int) -> str:
    return _range_ids[code]


def changed_message(code: int) -> str:
    return _changed_ids[code]


def repl_cause_message(code: int) -> str:
    return _repl_cause_ids[code]


def repl_method_message(code: int) -> str:
    return _repl_method_ids[code]


def test_failed_message(code: int) -> str:
    failed = []
    for key, val in _test_failed_ids.items():
        if code & key:
            failed.append(val)
    return "+".join(failed) if failed else "NONE"


def protection_message(code: int) -> str:
    return _protection_ids[code]


def analyze_quality_code(code: int) -> list[Any]:
    screened = code & 0b1
    validity = (code >> 1) & 0b1111
    value_range = (code >> 5) & 0b11
    changed = (code >> 7) & 0b1
    repl_cause = (code >> 8) & 0b111
    repl_method = (code >> 11) & 0b1111
    test_failed = (code >> 15) & 0b111_1111_1111
    protection = (code >> 31) & 0b1
    if validity not in (0, 1, 2, 4, 8):
        raise QualityException(
            f"Invalid validity value: {validity} in quality code {code}"
        )
    if repl_cause not in (0, 1, 2, 3, 4):
        raise QualityException(
            f"Invalid replacement cause value: {repl_cause} in quality code {code}"
        )
    if repl_method not in (0, 1, 2, 3, 4):
        raise QualityException(
            f"Invalid replacement method value: {repl_method} in quality code {code}"
        )
    return (
        screened,
        validity,
        value_range,
        changed,
        repl_cause,
        repl_method,
        test_failed,
        protection,
    )


def get_code_messages(code: int) -> list[str]:
    messages = []
    (
        screened,
        validity,
        value_range,
        changed,
        repl_cause,
        repl_method,
        test_failed,
        protection,
    ) = analyze_quality_code(code)
    messages.append(screened_message(screened))
    messages.append(validity_message(validity))
    messages.append(range_message(value_range))
    messages.append(changed_message(changed))
    messages.append(repl_cause_message(repl_cause))
    messages.append(repl_method_message(repl_method))
    messages.append(test_failed_message(test_failed))
    messages.append(protection_message(protection))
    return messages


def set_screened(code: int, screened: bool) -> int:
    if screened:
        code |= 0b0000_0000_0000_0000_0000_0000_0000_0001
    else:
        code &= 0b1111_1111_1111_1111_1111_1111_1111_1110
    return code


def set_validity(code: int, validity: int) -> int:
    if validity == 0:
        code &= 0b1111_1111_1111_1111_1111_1111_1110_0001
    elif validity == 1:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1110_0001
            | 0b0000_0000_0000_0000_0000_0000_0000_0010
        )
    elif validity == 2:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1110_0001
            | 0b0000_0000_0000_0000_0000_0000_0000_0100
        )
    elif validity == 4:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1110_0001
            | 0b0000_0000_0000_0000_0000_0000_0000_1000
        )
    elif validity == 8:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1110_0001
            | 0b0000_0000_0000_0000_0000_0000_0001_0000
        )
    else:
        raise QualityException(f"Invalid validity: {validity}")
    return code


def set_range(code: int, value_range: int) -> int:
    if value_range == 0:
        code &= 0b1111_1111_1111_1111_1111_1111_1001_1111
    elif value_range == 1:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1001_1111
            | 0b0000_0000_0000_0000_0000_0000_0010_0000
        )
    elif value_range == 2:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1001_1111
            | 0b0000_0000_0000_0000_0000_0000_0100_0000
        )
    elif value_range == 3:
        code = (
            code & 0b1111_1111_1111_1111_1111_1111_1001_1111
            | 0b0000_0000_0000_0000_0000_0000_0110_0000
        )
    else:
        raise QualityException(f"Invalid range: {value_range}")
    return code


def set_changed(code: int, changed: bool) -> int:
    if changed:
        code |= 0b0000_0000_0000_0000_0000_0000_1000_0000
    else:
        code &= 0b1111_1111_1111_1111_1111_1111_0111_1111
    return code


def set_repl_cause(code: int, repl_cause: int) -> int:
    if repl_cause == 0:
        code &= 0b1111_1111_1111_1111_1111_1000_1111_1111
    elif repl_cause == 1:
        code = (
            code & 0b1111_1111_1111_1111_1111_1000_1111_1111
            | 0b0000_0000_0000_0000_0000_0001_0000_0000
        )
    elif repl_cause == 2:
        code = (
            code & 0b1111_1111_1111_1111_1111_1000_1111_1111
            | 0b0000_0000_0000_0000_0000_0010_0000_0000
        )
    elif repl_cause == 3:
        code = (
            code & 0b1111_1111_1111_1111_1111_1000_1111_1111
            | 0b0000_0000_0000_0000_0000_0011_0000_0000
        )
    elif repl_cause == 4:
        code = (
            code & 0b1111_1111_1111_1111_1111_1000_1111_1111
            | 0b0000_0000_0000_0000_0000_0100_0000_0000
        )
    else:
        raise QualityException(f"Invalid replacement cause: {repl_cause}")
    return code


def set_repl_method(code: int, repl_method: int) -> int:
    if repl_method == 0:
        code &= 0b1111_1111_1111_1111_1000_0111_1111_1111
    elif repl_method == 1:
        code = (
            code & 0b1111_1111_1111_1111_1000_0111_1111_1111
            | 0b0000_0000_0000_0000_0000_1000_0000_0000
        )
    elif repl_method == 2:
        code = (
            code & 0b1111_1111_1111_1111_1000_0111_1111_1111
            | 0b0000_0000_0000_0000_0001_0000_0000_0000
        )
    elif repl_method == 3:
        code = (
            code & 0b1111_1111_1111_1111_1000_0111_1111_1111
            | 0b0000_0000_0000_0000_0001_1000_0000_0000
        )
    elif repl_method == 4:
        code = (
            code & 0b1111_1111_1111_1111_1000_0111_1111_1111
            | 0b0000_0000_0000_0000_0010_0000_0000_0000
        )
    else:
        raise QualityException(f"Invalid replacement method: {repl_method}")
    return code


def set_test_failed(code: int, test_failed: int) -> int:
    code &= 0b1111_1100_0000_0000_0111_1111_1111_1111
    if test_failed & 0b000_0000_0001:  # 1
        code |= 0b0000_0000_0000_0000_1000_0000_0000_0000
    if test_failed & 0b000_0000_0010:  # 2
        code |= 0b0000_0000_0000_0001_0000_0000_0000_0000
    if test_failed & 0b000_0000_0100:  # 4
        code |= 0b0000_0000_0000_0010_0000_0000_0000_0000
    if test_failed & 0b000_0000_1000:  # 8
        code |= 0b0000_0000_0000_0100_0000_0000_0000_0000
    if test_failed & 0b000_0001_0000:  # 16
        code |= 0b0000_0000_0000_1000_0000_0000_0000_0000
    if test_failed & 0b000_0010_0000:  # 32
        code |= 0b0000_0000_0001_0000_0000_0000_0000_0000
    if test_failed & 0b000_1000_0000:  # 128
        code |= 0b0000_0000_0100_0000_0000_0000_0000_0000
    if test_failed & 0b010_0000_0000:  # 512
        code |= 0b0000_0001_0000_0000_0000_0000_0000_0000
    if test_failed & 0b100_0000_0000:  # 1024
        code |= 0b0000_0010_0000_0000_0000_0000_0000_0000
    return code


def set_protection(code: int, protection: bool) -> int:
    if protection:
        code |= 0b1000_0000_0000_0000_0000_0000_0000_0000
    else:
        code &= 0b0111_1111_1111_1111_1111_1111_1111_1111
    return code


class Quality:
    def __init__(self, init_from: Any = 0):
        if isinstance(init_from, int):
            self._code = init_from
        elif isinstance(init_from, Quality):
            self._code = init_from.code
        elif isinstance(init_from, (list, tuple)):
            self._code = 0
            if init_from[_SCREENED]:
                self._code |= set_screened(
                    self._code, _screened_values[init_from[_SCREENED].upper()]
                )
            if init_from[_VALIDITY]:
                self._code |= set_validity(
                    self._code, _validity_values[init_from[_VALIDITY].upper()]
                )
            if init_from[_RANGE]:
                self._code |= set_range(
                    self._code, _range_values[init_from[_RANGE].upper()]
                )
            if init_from[_CHANGED]:
                self._code |= set_changed(
                    self._code, _changed_values[init_from[_CHANGED].upper()]
                )
            if init_from[_REPL_CAUSE]:
                self._code |= set_repl_cause(
                    self._code, _repl_cause_values[init_from[_REPL_CAUSE].upper()]
                )
            if init_from[_REPL_METHOD]:
                self._code |= set_repl_method(
                    self._code, _repl_method_values[init_from[_REPL_METHOD].upper()]
                )
            if init_from[_TEST_FAILED]:
                if isinstance(init_from[_TEST_FAILED], str):
                    tests_failed = set(
                        re.split(r"\W+", init_from[_TEST_FAILED].upper())
                    )
                elif isinstance(init_from[_TEST_FAILED], (list, tuple)):
                    tests_failed = set(init_from[_TEST_FAILED])
                self._code |= set_test_failed(
                    self._code, sum(map(lambda x: _test_failed_values[x], tests_failed))
                )
            if init_from[_PROTECTION]:
                self._code |= set_protection(
                    self._code, _protection_values[init_from[_PROTECTION].upper()]
                )

    @property
    def code(self) -> int:
        return self._code


129857
q = Quality(
    [
        "SCREENED",
        "UNKNOWN",
        "RANGE_1",
        "MODIFIED",
        "MANUAL",
        "GRAPHICAL",
        "ABSOLUTE_VALUE+RATE_OF_CHANGE+RELATIVE_VALUE+DURATION_VALUE+NEG_INCREMENT+SKIP_LIST+DISTRIBUTION",
        "UNPROTECTED",
    ]
)
print("hello")
print(q.code)
