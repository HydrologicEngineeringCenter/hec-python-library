from shared import dataset_from_file
from hec import quality
import pytest


# Tab-separated fields
# 1: QUALITY_CODE   (0..2204083441)
# 2: SCREENED_ID    shift =  0, bits =  1 (0=UNSCREENED, 1=SCREENED)
# 3: VALIDITY_ID    shift =  1, bits =  4 (0=UNKNOWN, 1=OKAY, 2=MISSING, 4=QUESTIONABLE, 8=REJECTED)
# 4: RANGE_ID       shift =  5, bits =  2 (0=NO_RANGE, 1=RANGE_1, 2=RANGE_2, 3=RANGE_3)
# 5: CHANGED_ID     shift =  7, bits =  1 (0=ORIGINAL, 1=MODIFIED)
# 6: REPL_CAUSE_ID  shift =  8, bits =  3 (0=NONE, 1=AUTOMATIC, 2=MANUAL, 3=RESTORED)
# 7: REPL_METHOD_ID shift = 11, bits =  4 (0=NONE, 1=LIN_INTERP, 2=EXPLICIT, 3=MISSING, 4=GRAPHICAL)
# 8: TEST_FAILED_ID shift = 15, bits = 11 (0=NONE, [1=ABSOLUTE_VALUE, 2=CONSTANT_VALUE, 4=RATE_OF_CHANGE, 8=RELATIVE_VALUE, 16=DURATION_VALUE, 32=NEG_INCREMENT, 128=SKIP_LIST, 512=USER_DEFINED, 1024=DISTRIBUTION])
# 9: PROTECTION_ID  shift = 31, bits =  1 (0=UNPROTECTED, 1=PROTECTED)


# --------------------- #
# test unit conversions #
# --------------------- #
@pytest.mark.parametrize(
    "qual, screened, validity, range, changed, repl_cause, repl_method, test_failed, protection",
    dataset_from_file("resources/quality/cwms_db_quality_codes.txt", slow=True),
)
def test_analyze_quality_codes(
    qual: str,
    screened: str,
    validity: str,
    range: str,
    changed: str,
    repl_cause: str,
    repl_method: str,
    test_failed: str,
    protection: str,
) -> None:
    quality_code = int(qual)
    messages = quality.get_code_messages(quality_code)
    assert messages[0] == screened
    assert messages[1] == validity
    assert messages[2] == range
    assert messages[3] == changed
    assert messages[4] == repl_cause
    assert messages[5] == repl_method
    assert messages[6] == test_failed
    assert messages[7] == protection
