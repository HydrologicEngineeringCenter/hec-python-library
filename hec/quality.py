"""
Provides quality code info and operations

<a id-"quality-code-rules"></a>
**Data Quality Rules:**

    1. Unless the Screened bit is set, no other bits can be set.

    2. Unused bits (21, 23, and 26-30) must be reset (zero).

    3. The Okay, Missing, Questioned and Rejected bits are mutually
       exclusive.

    4. No replacement cause or replacement method bits can be set unless
       the changed (different) bit is also set, and if the changed (different)
       bit is set, one of the cause bits and one of the replacement
       method bits must be set.

    5. Replacement Cause integer is in range 0..4.

    6. Replacement Method integer is in range 0..4

    7. The Test Failed bits are not mutually exclusive (multiple tests can be
       marked as failed).

<a id="bit-mapping"></a>
**Bit Mappings:**
```
       3                   2                   1
     1 0 9 8 7 6 5 4 3 2 1 0 9 8 7 6 5 4 3 2 1 0 9 8 7 6 5 4 3 2 1 0

     P - - - - - T T T T T T T T T T T M M M M C C C D R R V V V V S
     |           <---------+---------> <--+--> <-+-> | <+> <--+--> |
     |                     |              |      |   |  |     |    +------Screened Flag
     |                     |              |      |   |  |     +-----------Validity Exclusive Flags
     |                     |              |      |   |  +--------------Value Range Integer
     |                     |              |      |   +-------------------Different Flag
     |                     |              |      +---------------Replacement Cause Integer
     |                     |              +---------------------Replacement Method Integer
     |                     +-------------------------------------------Test Failed Inclusive Flags
     +-------------------------------------------------------------------Protected Flag
```
"""

import os
import re
import sys

_import_dir = os.path.abspath(".")
if not _import_dir in sys.path:
    sys.path.append(_import_dir)

from functools import total_ordering


class QualityException(Exception):
    pass


from typing import Any, Union

_NORMAL_QUALITY_MASK = 0b1000_0011_0101_1111_1111_1111_1111_1111

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
    """
    Sets bits unused by quality codes to zero

    Args:
        code (int): A quality code to normalize

    Returns:
        int: The input quality code with the unused bits set to zero
    """
    return code & _NORMAL_QUALITY_MASK


def screened_id(code: int) -> str:
    """
    Returns the text identifier for a valid screened code.

    This code is encoded in the quality code in bit 0 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0 or 1

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>UNSCREENED</td></tr>
            <tr><td>1</td><td>SCREENED</td></tr>
            </table>
    """
    return _screened_ids[code]


def validity_id(code: int) -> str:
    """
    Returns the text identifier for a valid validity code.

    This code is encoded in the quality code in bits 1-4 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0, 1, 2, 4, or 8

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>UNKNOWN</td></tr>
            <tr><td>1</td><td>OKAY</td></tr>
            <tr><td>2</td><td>MISSING</td></tr>
            <tr><td>4</td><td>QUESTIONABLE</td></tr>
            <tr><td>8</td><td>REJECTED</td></tr>
            </table>
    """
    return _validity_ids[code]


def range_id(code: int) -> str:
    """
    Returns the text identifier for a valid range code.

    This code is encoded in the quality code in bits 5 and 6 of 32

    Args:
        code (int): Must be 0, 1, 2, or 3 as diagrammed in the [bit-mapping](#bit-mapping)

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>NO_RANGE</td></tr>
            <tr><td>1</td><td>RANGE_1</td></tr>
            <tr><td>2</td><td>RANGE_2</td></tr>
            <tr><td>3</td><td>RANGE_3</td></tr>
            </table>
    """
    return _range_ids[code]


def changed_id(code: int) -> str:
    """
    Returns the text identifier for a valid changed code.

    This code is encoded in the quality code in bit 7 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0 or 1

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>ORIGINAL</td></tr>
            <tr><td>1</td><td>MODIFIED</td></tr>
            </table>
    """
    return _changed_ids[code]


def repl_cause_id(code: int) -> str:
    """
    Returns the text identifier for a valid replacement cause code.

    This code is encoded in the quality code in bits 8-10 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0, 1, 2, 3, or 4

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>NONE</td></tr>
            <tr><td>1</td><td>AUTOMATIC</td></tr>
            <tr><td>2</td><td>INTERACTIVE</td></tr>
            <tr><td>3</td><td>MANUAL</td></tr>
            <tr><td>4</td><td>RESTORED</td></tr>
            </table>
    """
    return _repl_cause_ids[code]


def repl_method_id(code: int) -> str:
    """
    Returns the text identifier for a valid replacement method code.

    This code is encoded in the quality code in bits 11-14 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0, 1, 2, 3, or 4

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>NONE</td></tr>
            <tr><td>1</td><td>LIN_INTERP</td></tr>
            <tr><td>2</td><td>EXPLICIT</td></tr>
            <tr><td>3</td><td>MISSING</td></tr>
            <tr><td>4</td><td>GRAPHICAL</td></tr>
            </table>
    """
    return _repl_method_ids[code]


def test_failed_id(code: int) -> str:
    """
    Returns the text identifier for a valid failed test code.

    This code is encoded in the quality code in bits 15-25 of 32 as diagrammed in the [bit-mapping](#bit-mapping), but bits 21 and 23 are not used

    Args:
        code (int): Must be 0 or sum of 1 or more of: 1, 2, 4, 8, 16, 32, 128, 512, and 1024
        (maximum of one ocrrence per number). Note that values 64 and 256 are not used.

    Returns:
        str: One or more of the following identifiers. `None` is always returned alone; if more that one
            identifier is returned, they will be concatenated with the `+` character into a single string.
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>NONE</td></tr>
            <tr><td>1</td><td>ABSOLUTE_VALUE</td></tr>
            <tr><td>2</td><td>CONSTANT_VALUE</td></tr>
            <tr><td>4</td><td>RATE_OF_CHANGE</td></tr>
            <tr><td>8</td><td>RELATIVE_VALUE</td></tr>
            <tr><td>16</td><td>DURATION_VALUE</td></tr>
            <tr><td>32</td><td>NEG_INCREMENT</td></tr>
            <tr><td>128</td><td>SKIP_LIST</td></tr>
            <tr><td>512</td><td>USER_DEFINED</td></tr>
            <tr><td>1024</td><td>DISTRIBUTION</td></tr>
            </table>
    """
    failed = []
    for key, val in _test_failed_ids.items():
        if code & key:
            failed.append(val)
    return "+".join(failed) if failed else "NONE"


def protection_id(code: int) -> str:
    """
    Returns the text identifier for a valid protection code.

    This code is encoded in the quality code in bit 31 of 32 as diagrammed in the [bit-mapping](#bit-mapping)

    Args:
        code (int): Must be 0 or 1

    Returns:
        str: One of the following identifiers:
            <table>
            <tr><th>code</th><th>returns</th></tr>
            <tr><td>0</td><td>UNPROTECTED</td></tr>
            <tr><td>1</td><td>PROTECTED</td></tr>
            </table>
    """
    return _protection_ids[code]


def get_component_codes(code: int) -> tuple[int, ...]:
    """
    Returns a tuple of component codes in a quality code

    Args:
        code (int): The quality code to return the component codes for

    Raises:
        QualityException: If the quality code is not valid according the the [quality code rules](#quality-code-rules)

    Returns:
        tuple[int, ...]: A tuple containing the following component codes in the order specified:
        * screened
        * validity
        * range
        * changed
        * replacement cause
        * replacement method
        * test failed
        * protection
    """
    screened = code & 0b1
    validity = (code >> 1) & 0b1111
    value_range = (code >> 5) & 0b11
    changed = (code >> 7) & 0b1
    repl_cause = (code >> 8) & 0b111
    repl_method = (code >> 11) & 0b1111
    test_failed = (code >> 15) & 0b111_1111_1111
    protection = (code >> 31) & 0b1

    if code & ~_NORMAL_QUALITY_MASK:
        raise QualityException(
            f"Invalid quality value: {code}: Unused bits must not be set. Call normalize_quality_code() first"
        )
    if not screened and (
        validity
        or value_range
        or changed
        or repl_cause
        or repl_method
        or test_failed
        or protection
    ):
        raise QualityException(
            f"Invalid quality value: {code}: All other bits must be zero if not screened"
        )
    if repl_method and not repl_cause:
        raise QualityException(
            f"Invalid quality value: {code}: Replacement method must not be specified unless replacement cause is specified"
        )
    if repl_cause and not repl_method:
        raise QualityException(
            f"Invalid quality value: {code}: A replacement method must be set when replacement cause is specified"
        )
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


def get_code_ids(code: int) -> tuple[str, ...]:
    """
    Returns a list of identifiers for the component codes in a quality code

    Args:
        code (int): The quality code to return the component code identifiers for

    Raises:
        QualityException: If the quality code is not valid according the the [quality code rules](#quality-code-rules)

    Returns:
        tuple[int, ...]: A tuple containing the following code identifiers in the order specified:
        * screened
        * validity
        * range
        * changed
        * replacement cause
        * replacement method
        * test failed
        * protection
    """
    ids = []
    (
        screened,
        validity,
        value_range,
        changed,
        repl_cause,
        repl_method,
        test_failed,
        protection,
    ) = get_component_codes(code)
    ids.append(screened_id(screened))
    ids.append(validity_id(validity))
    ids.append(range_id(value_range))
    ids.append(changed_id(changed))
    ids.append(repl_cause_id(repl_cause))
    ids.append(repl_method_id(repl_method))
    ids.append(test_failed_id(test_failed))
    ids.append(protection_id(protection))
    return tuple(ids)


def set_screened_code(code: int, screened: Union[bool, int]) -> int:
    """
    Encodes a screened code into a quality code

    Args:
        code (int): The quality code to encode the screened code into
        screened (Union[bool, int]): The screened code

    Returns:
        int: The modified quality code
    """
    if screened:
        code |= 0b0000_0000_0000_0000_0000_0000_0000_0001
    else:
        code &= 0b1111_1111_1111_1111_1111_1111_1111_1110
    return code


def set_validity_code(code: int, validity: int) -> int:
    """
    Encodes a validity code into a quality code

    Args:
        code (int): The quality code to encode the validity code into
        validity (Union[bool, int]): The validity code

    Returns:
        int: The modified quality code
    """
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


def set_range_code(code: int, value_range: int) -> int:
    """
    Encodes a range code into a quality code

    Args:
        code (int): The quality code to encode the range code into
        range (Union[bool, int]): The range code

    Returns:
        int: The modified quality code
    """
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


def set_changed_code(code: int, changed: Union[bool, int]) -> int:
    """
    Encodes a changed code into a quality code

    Args:
        code (int): The quality code to encode the changed code into
        changed (Union[bool, int]): The changed code

    Returns:
        int: The modified quality code
    """
    if changed:
        code |= 0b0000_0000_0000_0000_0000_0000_1000_0000
    else:
        code &= 0b1111_1111_1111_1111_1111_1111_0111_1111
    return code


def set_repl_cause_code(code: int, repl_cause: int) -> int:
    """
    Encodes a replacement cause code into a quality code

    Args:
        code (int): The quality code to encode the replacement cause code into
        replacement cause (Union[bool, int]): The replacement cause code

    Returns:
        int: The modified quality code
    """
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


def set_repl_method_code(code: int, repl_method: int) -> int:
    """
    Encodes a replacement method code into a quality code

    Args:
        code (int): The quality code to encode the replacement method code into
        replacement method (Union[bool, int]): The replacement method code

    Returns:
        int: The modified quality code
    """
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


def set_test_failed_code(code: int, test_failed: int) -> int:
    """
    Encodes a test failed code into a quality code

    Args:
        code (int): The quality code to encode the test failed code into
        test failed (Union[bool, int]): The test failed code

    Returns:
        int: The modified quality code
    """
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


def set_protection_code(code: int, protection: Union[bool, int]) -> int:
    """
    Encodes a protection code into a quality code

    Args:
        code (int): The quality code to encode the protection code into
        protection (Union[bool, int]): The protection code

    Returns:
        int: The modified quality code
    """
    if protection:
        code |= 0b1000_0000_0000_0000_0000_0000_0000_0000
    else:
        code &= 0b0111_1111_1111_1111_1111_1111_1111_1111
    return code


@total_ordering
class Quality:
    """
    Holds a quality code and provides quality tests and operations
    """

    _return_signed_codes: bool = True

    @classmethod
    def setReturnSignedCodes(cls, state: bool = True) -> None:
        """
        Sets the type (signed or unsigned of the `code` property)

        Args:
            state (bool, optional): Sets default type to signed if true, otherwise unsigned. Defaults to True.
        """
        cls._return_signed_codes = state

    @classmethod
    def setReturnUnsignedCodes(cls, state: bool = True) -> None:
        """
        Sets the type (signed or unsigned of the `code` property)

        Args:
            state (bool, optional): Sets default type to unsigned if true, otherwise signed. Defaults to True.
        """
        cls._return_signed_codes = not state

    def __init__(self, init_from: Any = 0):
        """
        Initializes a Quality object

        Args:
            init_from (Any, optional): The object to initialize from. Defaults to 0.
                * **Not specified**: the quality code is set to 0
                * **Integer**: the quality code is set to the integer
                * **String**: the quality code is set from the unique beginning of one of the following (case insensitive):
                    * "Unscreened": the quality code is 0 (Unscreened)
                    * "Unknown" or "Indeterminate": the quality code is 1 (Screened Indeterminate)
                    * "Okay": the quality code is 3 (Screened Okay)
                    * "Missing": the quality code is 5 (Screened Missing)
                    * "Questionable": the quality code is 9 (Screened Questionable)
                    * "Rejected": the quality code is 17 (Screened Rejected)
                * **Quality**: the quality code is set to the other object's quality code
                * **List or tuple**: the quality code is set from the list of component identifiers.<br>
                    The zero value can be set for any of the component by setting its identifier to `None`.<br>
                    The sequence must have a mininum length of 8, in this order:
                    * screened identifier
                    * validity identifier
                    * range identifier
                    * changed identifier
                    * replacement cause identifier
                    * replacement method identifier
                    * test failed identifier (may be multiple identifiers concatenated with `+` character)
                    * protected identifier
        """
        self._code: int = 0
        self._screened: int
        self._validity: int
        self._value_range: int
        self._changed: int
        self._repl_cause: int
        self._repl_method: int
        self._test_failed: int
        self._protection: int
        self._validated: bool = False
        if isinstance(init_from, int):
            self._code = normalize_quality_code(init_from)
        elif isinstance(init_from, Quality):
            self._code = init_from._code
        elif isinstance(init_from, str):
            s = init_from.upper()
            if "UNSCREENED".startswith(s) and not "UNKNOWN".startswith(s):
                self._code = 0
            elif (
                "UNKNOWN".startswith(s) and not "UNSCREENED".startswith(s)
            ) or "INDETERMINATE".startswith(s):
                self._code = 1
            elif "OKAY".startswith(s):
                self._code = 3
            elif "MISSING".startswith(s):
                self._code = 5
            elif "QUESTIONABLE".startswith(s):
                self._code = 9
            elif "REJECTED".startswith(s):
                self._code = 17
            else:
                raise QualityException(f"Invalid Quality initializer: '{init_from}'")
        elif isinstance(init_from, (list, tuple)):
            self._code = 0
            if init_from[_SCREENED]:
                self._code |= set_screened_code(
                    self._code, _screened_values[init_from[_SCREENED].upper()]
                )
            if init_from[_VALIDITY]:
                self._code |= set_validity_code(
                    self._code, _validity_values[init_from[_VALIDITY].upper()]
                )
            if init_from[_RANGE]:
                self._code |= set_range_code(
                    self._code, _range_values[init_from[_RANGE].upper()]
                )
            if init_from[_CHANGED]:
                self._code |= set_changed_code(
                    self._code, _changed_values[init_from[_CHANGED].upper()]
                )
            if init_from[_REPL_CAUSE]:
                self._code |= set_repl_cause_code(
                    self._code, _repl_cause_values[init_from[_REPL_CAUSE].upper()]
                )
            if init_from[_REPL_METHOD]:
                self._code |= set_repl_method_code(
                    self._code, _repl_method_values[init_from[_REPL_METHOD].upper()]
                )
            if init_from[_TEST_FAILED]:
                if isinstance(init_from[_TEST_FAILED], str):
                    tests_failed = set(
                        re.split(r"\W+", init_from[_TEST_FAILED].upper())
                    )
                elif isinstance(init_from[_TEST_FAILED], (list, tuple)):
                    tests_failed = set(init_from[_TEST_FAILED])
                self._code |= set_test_failed_code(
                    self._code, sum(map(lambda x: _test_failed_values[x], tests_failed))
                )
            if init_from[_PROTECTION]:
                self._code |= set_protection_code(
                    self._code, _protection_values[init_from[_PROTECTION].upper()]
                )
        (
            self._screened,
            self._validity,
            self._value_range,
            self._changed,
            self._repl_cause,
            self._repl_method,
            self._test_failed,
            self._protection,
        ) = get_component_codes(self._code)

    @property
    def code(self) -> int:
        """
        The internal quality code as a signed or unsigned integer depending on the default setting.<br>

        See
        * [setReturnSignedCodes](#Quality.setReturnSignedCodes)
        * [setReturnUnsignedCodes](#Quality.setReturnUnsignedCodes)

        Operations:
            Read Only
        """
        return self.signed if Quality._return_signed_codes else self.unsigned

    @property
    def signed(self) -> int:
        """
        The internal quality code as a signed integer.

        Operations:
            Read Only
        """
        if self._code > 0x7FFFFFFF:
            code = self._code & 0xFFFFFFFF
            code -= 0x100000000
        else:
            code = self._code
        return code

    @property
    def unsigned(self) -> int:
        """
        The internal quality code as an unsigned integer.

        Operations:
            Read Only
        """
        return self._code + 0x100000000 if self._code < 0 else self._code

    @property
    def text(self) -> str:
        """
        The text description of the quality.

        A space separated list of words specifying the state of the following, in order:
        * Screened: ("Unscreened" or "Screened")
        * Validity: ("Unknown", "Okay", "Missing", "Questionable", or "Rejected")
        * Range: ("No_range", "Range_1", "Range_2", or "Range_3")
        * Changed: ("Original" or "Modified")
        * Replacement Cause: ("None", "Automatic", "Interactive", "Manual", "Restored")
        * Replacement Method: ("None", "Lin_Interp", "Explicit", "Missing", "Graphical")
        * Test Failed: ("None" or one or more of the following concatenated with "+"):
            * "Absolute_Value"
            * "Constant_Value"
            * "Rate_Of_Change"
            * "Relative_Value"
            * "Duration_Value"
            * "Neg_Increment"
            * "Skip_List"
            * "User_Defined"
            * "Distribution"
        * Protection: ("Unprotected" or "Protected")

        Operations:
            Read Only
        """
        (
            _screened,
            _validity,
            _range,
            _changed,
            _repl_cause,
            _repl_method,
            _test_failed,
            _protection,
        ) = get_code_ids(self._code)
        return f"{_screened} {_validity} {_range} {_changed} {_repl_cause} {_repl_method} {_test_failed} {_protection}".title()

    @property
    def symbol(self) -> str:
        """
        The text symbol of the quality.

        The symbol will be one or two characters, with the first character being:
        * `~`: Not screened
        * `u` or 'U': Screened, validity is unknown
        * `o` or `O`: Screened, validity is okay
        * `m` or `M`: Screened, validity is missing
        * `q` or `Q`: Screened, validity is questioned
        * `r` or `R`: Screened, validity is rejected

        If a screened quality has the protection bit set, the first chanacter will be uppercase; if not, it will be lowercase.

        A second character of `+` signifies that the quality has additional information about one or more of the following:
        * value range
        * value replacement cause and method
        * test(s) failed

        This property is used when the quality is used in a string context (e.g., `print(q)`)

        Operations:
            Read Only
        """
        if not self._validated:
            self._validate()
        if not self._screened:
            s = "~"
        else:
            s = _validity_ids[self._validity][0]
            if self._value_range or self._changed or self._test_failed:
                s += "+"
            if not self.protection:
                s = s.lower()
        return s

    @property
    def screened(self) -> int:
        """
        The screened component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._screened

    @screened.setter
    def screened(self, value: int) -> None:
        self._code = set_screened_code(self._code, value)
        self._validated = False

    @property
    def screened_id(self) -> str:
        """
        The screened component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return screened_id(self._screened)

    @screened_id.setter
    def screened_id(self, id: str) -> None:
        self._code = set_screened_code(self._code, _screened_values[id.upper()])
        self._validated = False

    @property
    def validity(self) -> int:
        """
        The validity component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._validity

    @validity.setter
    def validity(self, value: int) -> None:
        self._code = set_validity_code(self._code, value)
        self._validated = False

    @property
    def validity_id(self) -> str:
        """
        The validity component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return validity_id(self._validity)

    @validity_id.setter
    def validity_id(self, id: str) -> None:
        self._code = set_validity_code(self._code, _validity_values[id.upper()])
        self._validated = False

    @property
    def range(self) -> int:
        """
        The range component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._value_range

    @range.setter
    def range(self, value: int) -> None:
        self._code = set_range_code(self._code, value)
        self._validated = False

    @property
    def range_id(self) -> str:
        """
        The range component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return range_id(self._value_range)

    @range_id.setter
    def range_id(self, id: str) -> None:
        self._code = set_range_code(self._code, _range_values[id.upper()])
        self._validated = False

    @property
    def changed(self) -> int:
        """
        The changed component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._changed

    @changed.setter
    def changed(self, value: int) -> None:
        self._code = set_changed_code(self._code, value)
        self._validated = False

    @property
    def changed_id(self) -> str:
        """
        The changed component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return changed_id(self._changed)

    @changed_id.setter
    def changed_id(self, id: str) -> None:
        self._code = set_changed_code(self._code, _changed_values[id.upper()])
        self._validated = False

    @property
    def repl_cause(self) -> int:
        """
        The replacement cause component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._repl_cause

    @repl_cause.setter
    def repl_cause(self, value: int) -> None:
        self._code = set_repl_cause_code(self._code, value)
        self._validated = False

    @property
    def repl_cause_id(self) -> str:
        """
        The replacement cause component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return repl_cause_id(self._repl_cause)

    @repl_cause_id.setter
    def repl_cause_id(self, id: str) -> None:
        self._code = set_repl_cause_code(self._code, _repl_cause_values[id.upper()])
        self._validated = False

    @property
    def repl_method(self) -> int:
        """
        The replacement method component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._repl_method

    @repl_method.setter
    def repl_method(self, value: int) -> None:
        self._code = set_repl_method_code(self._code, value)
        self._validated = False

    @property
    def repl_method_id(self) -> str:
        """
        The replacement method component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return repl_method_id(self._repl_method)

    @repl_method_id.setter
    def repl_method_id(self, id: str) -> None:
        self._code = set_repl_method_code(self._code, _repl_method_values[id.upper()])
        self._validated = False

    @property
    def score(self) -> int:
        """
        A score to compare qualities by:
        <table>
        <tr><th>Screened</th><th>Validity Code</th><th>Score</th></tr>
        <tr><td>UNSCREENED</td><td>UNKNOWN</td><td>1</td></tr>
        <tr><td>SCREENED</td><td>MISSING</td><td>0</td></tr>
        <tr><td>SCREENED</td><td>REJECTED</td><td>0</td></tr>
        <tr><td>SCREENED</td><td>UNKNOWN</td><td>2</td></tr>
        <tr><td>SCREENED</td><td>QUESTIONABLE</td><td>3</td></tr>
        <tr><td>SCREENED</td><td>OKAY</td><td>4</td></tr>
        </table>

        Operations:
            Read Only
        """
        if not self._validated:
            self._validate()
        # missing or rejected = 0
        # unscreened          = 1
        # unknown             = 2
        # questionable        = 3
        # okay                = 4
        return (
            1 if not self._screened else {0: 2, 1: 4, 2: 0, 4: 3, 8: 0}[self._validity]
        )

    @property
    def test_failed(self) -> int:
        """
        The test failed component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._test_failed

    @test_failed.setter
    def test_failed(self, value: int) -> None:
        self._code = set_test_failed_code(self._code, value)
        self._validated = False

    @property
    def test_failed_id(self) -> str:
        """
        The test failed component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return test_failed_id(self._test_failed)

    @test_failed_id.setter
    def test_failed_id(self, id: str) -> None:
        code = set_test_failed_code(self._code, 0)
        for failed_id in re.split(r"\W+", id.upper()):
            code |= set_test_failed_code(code, _test_failed_values[failed_id])
        self._code = code
        self._validated = False

    @property
    def protection(self) -> int:
        """
        The protection component code of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return self._protection

    @protection.setter
    def protection(self, value: int) -> None:
        self._code = set_protection_code(self._code, value)
        self._validated = False

    @property
    def protection_id(self) -> str:
        """
        The protection component identifier of the quality code

        Operations:
            Read-Write
        """
        if not self._validated:
            self._validate()
        return protection_id(self._protection)

    @protection_id.setter
    def protection_id(self, id: str) -> None:
        self._code = set_protection_code(self._code, _protection_values[id.upper()])
        self._validated = False

    def _validate(self) -> None:
        (
            self._screened,
            self._validity,
            self._value_range,
            self._changed,
            self._repl_cause,
            self._repl_method,
            self._test_failed,
            self._protection,
        ) = get_component_codes(self._code)
        self._validated = True

    def __repr__(self) -> str:
        return f"Quality({self.code})"

    def __str__(self) -> str:
        return str(self.symbol)

    def __format__(self, format: str) -> str:
        if format:
            if format[-1] in "bBxX":
                return self.unsigned.__format__(format)
            else:
                return self.code.__format__(format)
        else:
            return str(self)

    def __int__(self) -> int:
        return self.code

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Quality):
            return self.score == other.score
        elif isinstance(other, int):
            return self.score == Quality(other).score
        else:
            return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Quality):
            return self.score < other.score
        elif isinstance(other, int):
            return self.score < Quality(other).score
        else:
            return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Quality):
            return self.score > other.score
        elif isinstance(other, int):
            return self.score > Quality(other).score
        else:
            return NotImplemented

    def setScreened(self, value: Union[int, str]) -> "Quality":
        """
        Sets the screened component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `screened` or `screened_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The screened component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _screened_values[value.upper()]
        self._code = set_screened_code(self._code, val)
        self._validated = False
        return self

    def setValidity(self, value: Union[int, str]) -> "Quality":
        """
        Sets the validity component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `validity` or `validity_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The validity component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _validity_values[value.upper()]
        self._code = set_validity_code(self._code, val)
        self._validated = False
        return self

    def setRange(self, value: Union[int, str]) -> "Quality":
        """
        Sets the range component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `range` or `range_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The range component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _range_values[value.upper()]
        self._code = set_range_code(self._code, val)
        self._validated = False
        return self

    def setChanged(self, value: Union[int, str]) -> "Quality":
        """
        Sets the changed component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `changed` or `changed_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The changed component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _changed_values[value.upper()]
        self._code = set_changed_code(self._code, val)
        self._validated = False
        return self

    def setReplCause(self, value: Union[int, str]) -> "Quality":
        """
        Sets the replacement cause component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `repl_cause` or `repl_cause_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The replacement cause component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _repl_cause_values[value.upper()]
        self._code = set_repl_cause_code(self._code, val)
        self._validated = False
        return self

    def setReplMethod(self, value: Union[int, str]) -> "Quality":
        """
        Sets the replacement method component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `repl_method` or `repl_method_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The replacement method component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _repl_method_values[value.upper()]
        self._code = set_repl_method_code(self._code, val)
        self._validated = False
        return self

    def setTestFailed(self, value: Union[int, str]) -> "Quality":
        """
        Sets the test failed component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `test_failed` or `test_failed_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The test failed component code or identifier

        Returns:
            Quality: The modified object
        """
        if isinstance(value, int):
            self._code = set_test_failed_code(self._code, value)
        else:
            code = set_test_failed_code(self._code, 0)
            for failed_id in re.split(r"\W+", value.upper()):
                code |= set_test_failed_code(code, _test_failed_values[failed_id])
            self._code = code
        self._validated = False
        return self

    def setProtection(self, value: Union[int, str]) -> "Quality":
        """
        Sets the protection component of this object from a code or identifier and returns the modified object.

        Using this method instead of setting the `protection` or `protection_id` properties allows chained operations.

        Args:
            value (Union[int, str]): The protection component code or identifier

        Returns:
            Quality: The modified object
        """
        val = value if isinstance(value, int) else _protection_values[value.upper()]
        self._code = set_protection_code(self._code, val)
        return self

    def addTestFailed(self, value: Union[int, str]) -> "Quality":
        """
        Adds a failed test to the test failed component of this object from a code or identifier and returns the modified object

        Args:
            value (Union[int, str]): The test failed component code or identifier of the failed test to be added

        Returns:
            Quality: The modified object
        """
        if isinstance(value, int):
            self._code |= set_test_failed_code(self._code, value)
        else:
            code = self._code
            for failed_id in re.split(r"\W+", value.upper()):
                code |= set_test_failed_code(0, _test_failed_values[failed_id])
            self._code = code
        self._validated = False
        return self

    def removeTestFailed(self, value: Union[int, str]) -> "Quality":
        """
        Removes a failed test from the test failed component of this object from a code or identifier and returns the modified object

        Args:
            value (Union[int, str]): The test failed component code or identifier of the failed test to be removed

        Returns:
            Quality: The modified object
        """
        if isinstance(value, int):
            self._code &= ~set_test_failed_code(self._code, value)
        else:
            code = self._code
            for failed_id in re.split(r"\W+", value.upper()):
                test_code = set_test_failed_code(0, _test_failed_values[failed_id])
                code &= ~test_code
            self._code = code
        self._validated = False
        return self
