from test.shared import dataset_from_file

import pytest

from hec import quality
from hec.quality import Quality


# ------------------------------------------------ #
# test quality operations                          #
#                                                  #
# runs routine 348,161 times, each with 9 or 10    #
# assertions, skip with pytest -m "not slow"       #
# or set SLOW_TEST_COVERAGE env var to < 100 to    #
# run a random subset of the specified percentage  #
# ------------------------------------------------ #
@pytest.mark.slow
@pytest.mark.parametrize(
    "qual, screened, validity, value_range, changed, repl_cause, repl_method, test_failed, protection",
    dataset_from_file("resources/quality/cwms_db_quality_codes.txt", slow=True),
)
def test_cwms_db_compatibility(
    qual: str,
    screened: str,
    validity: str,
    value_range: str,
    changed: str,
    repl_cause: str,
    repl_method: str,
    test_failed: str,
    protection: str,
) -> None:
    quality_code = int(qual)
    messages = quality.get_code_ids(quality_code)
    assert messages[0] == screened
    assert messages[1] == validity
    assert messages[2] == value_range
    assert messages[3] == changed
    assert messages[4] == repl_cause
    assert messages[5] == repl_method
    assert messages[6] == test_failed
    assert messages[7] == protection

    q = Quality(
        [
            screened,
            validity,
            value_range,
            changed,
            repl_cause,
            repl_method,
            test_failed,
            protection,
        ]
    )
    assert q.unsigned == quality_code
    if q.signed != q.unsigned:
        assert Quality(q.signed).unsigned == quality_code


def test_misc() -> None:
    q = Quality()
    assert q.code == 0
    assert q.screened_id == "UNSCREENED"
    assert q.validity_id == "UNKNOWN"
    assert q.range_id == "NO_RANGE"
    assert q.changed_id == "ORIGINAL"
    assert q.repl_cause_id == "NONE"
    assert q.repl_method_id == "NONE"
    assert q.test_failed_id == "NONE"
    assert q.protection_id == "UNPROTECTED"

    q.screened_id = "screened"
    q.validity_id = "questionable"
    q.range_id = "range_3"
    q.changed_id = "modified"
    q.repl_cause_id = "automatic"
    q.repl_method_id = "lin_interp"
    q.test_failed_id = "distribution user_defined"
    q.protection_id = "protected"

    assert q.screened_id == "SCREENED"
    assert q.validity_id == "QUESTIONABLE"
    assert q.range_id == "RANGE_3"
    assert q.changed_id == "MODIFIED"
    assert q.repl_cause_id == "AUTOMATIC"
    assert q.repl_method_id == "LIN_INTERP"
    assert q.test_failed_id == "USER_DEFINED+DISTRIBUTION"
    assert q.protection_id == "PROTECTED"

    q.addTestFailed("RATE_OF_CHANGE")
    assert q.test_failed_id == "RATE_OF_CHANGE+USER_DEFINED+DISTRIBUTION"

    q.removeTestFailed("USER_DEFINED")
    assert q.test_failed_id == "RATE_OF_CHANGE+DISTRIBUTION"

    q = (
        Quality()
        .setScreened("screened")
        .setValidity("questionable")
        .setRange("range_3")
        .setChanged("modified")
        .setReplCause("automatic")
        .setReplMethod("lin_interp")
        .setTestFailed("distribution user_defined")
        .setProtection("protected")
        .addTestFailed("rate_of_change")
        .removeTestFailed("user_defined")
    )

    assert q.screened_id == "SCREENED"
    assert q.validity_id == "QUESTIONABLE"
    assert q.range_id == "RANGE_3"
    assert q.changed_id == "MODIFIED"
    assert q.repl_cause_id == "AUTOMATIC"
    assert q.repl_method_id == "LIN_INTERP"
    assert q.test_failed_id == "RATE_OF_CHANGE+DISTRIBUTION"
    assert q.protection_id == "PROTECTED"
