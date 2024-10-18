"""Module for testing hec.timespan module
"""

import traceback
from datetime import timedelta
from fractions import Fraction
from typing import Optional

from hec.timespan import TimeSpan


def test_creation() -> None:
    assert TimeSpan().values == [0, 0, 0, 0, 0, 0]

    assert TimeSpan([1, 2, 3, 4, 5, 6]).values == [1, 2, 3, 4, 5, 6]
    assert TimeSpan([1, 2, 3, 4, 5]).values == [1, 2, 3, 4, 5, 0]
    assert TimeSpan([1, 2, 3, 4]).values == [1, 2, 3, 4, 0, 0]
    assert TimeSpan([1, 2, 3]).values == [1, 2, 3, 0, 0, 0]
    assert TimeSpan([1, 2]).values == [1, 2, 0, 0, 0, 0]
    assert TimeSpan([1]).values == [1, 0, 0, 0, 0, 0]

    assert TimeSpan(["1", "2", "3", "4", "5", "6"]).values == [1, 2, 3, 4, 5, 6]
    assert TimeSpan(["1", "2", "3", "4", "5"]).values == [1, 2, 3, 4, 5, 0]
    assert TimeSpan(["1", "2", "3", "4"]).values == [1, 2, 3, 4, 0, 0]
    assert TimeSpan(["1", "2", "3"]).values == [1, 2, 3, 0, 0, 0]
    assert TimeSpan(["1", "2"]).values == [1, 2, 0, 0, 0, 0]
    assert TimeSpan(["1"]).values == [1, 0, 0, 0, 0, 0]

    assert TimeSpan(1, 2, 3, 4, 5, 6).values == [1, 2, 3, 4, 5, 6]
    assert TimeSpan(1, 2, 3, 4, 5).values == [1, 2, 3, 4, 5, 0]
    assert TimeSpan(1, 2, 3, 4).values == [1, 2, 3, 4, 0, 0]
    assert TimeSpan(1, 2, 3).values == [1, 2, 3, 0, 0, 0]
    assert TimeSpan(1, 2).values == [1, 2, 0, 0, 0, 0]
    assert TimeSpan(1).values == [1, 0, 0, 0, 0, 0]

    assert TimeSpan("1", "2", "3", "4", "5", "6").values == [1, 2, 3, 4, 5, 6]
    assert TimeSpan("1", "2", "3", "4", "5").values == [1, 2, 3, 4, 5, 0]
    assert TimeSpan("1", "2", "3", "4").values == [1, 2, 3, 4, 0, 0]
    assert TimeSpan("1", "2", "3").values == [1, 2, 3, 0, 0, 0]
    assert TimeSpan("1", "2").values == [1, 2, 0, 0, 0, 0]
    assert TimeSpan("1").values == [1, 0, 0, 0, 0, 0]

    assert TimeSpan([1, Fraction(2, 3), 4, 5, 6, 7]).values == [
        1,
        Fraction(2, 3),
        4,
        5,
        6,
        7,
    ]
    assert TimeSpan(["1", "2/3", "4", "5", "6", "7"]).values == [
        1,
        Fraction(2, 3),
        4,
        5,
        6,
        7,
    ]
    assert TimeSpan(1, Fraction(2, 3), 4, 5, 6, 7).values == [
        1,
        Fraction(2, 3),
        4,
        5,
        6,
        7,
    ]
    assert TimeSpan("1", "2/3", "4", "5", "6", "7").values == [
        1,
        Fraction(2, 3),
        4,
        5,
        6,
        7,
    ]

    assert TimeSpan(timedelta(seconds=273906)).values == [0, 0, 3, 4, 5, 6]
    assert TimeSpan("P1Y2M3DT4H5M6S").values == [1, 2, 3, 4, 5, 6]
    assert TimeSpan("P1Y2M,-P3DT4H5M6S").values == [1, 2, -3, -4, -5, -6]
    assert TimeSpan("-P1Y2M,P3DT4H5M6S").values == [-1, -2, 3, 4, 5, 6]
    assert TimeSpan("P1Y2/3M4DT5H6M7S").values == [1, Fraction(2, 3), 4, 5, 6, 7]
    assert TimeSpan("P1Y2/3M,-P4DT5H6M7S").values == [1, Fraction(2, 3), -4, -5, -6, -7]
    assert TimeSpan("-P1Y2/3M,P4DT5H6M7S").values == [-1, Fraction(-2, 3), 4, 5, 6, 7]


def test_repr() -> None:
    assert repr(TimeSpan()) == "TimeSpan([0, 0, 0, 0, 0, 0])"

    assert repr(TimeSpan([1, 2, 3, 4, 5, 6])) == "TimeSpan([1, 2, 3, 4, 5, 6])"
    assert repr(TimeSpan([1, 2, 3, 4, 5])) == "TimeSpan([1, 2, 3, 4, 5, 0])"
    assert repr(TimeSpan([1, 2, 3, 4])) == "TimeSpan([1, 2, 3, 4, 0, 0])"
    assert repr(TimeSpan([1, 2, 3])) == "TimeSpan([1, 2, 3, 0, 0, 0])"
    assert repr(TimeSpan([1, 2])) == "TimeSpan([1, 2, 0, 0, 0, 0])"
    assert repr(TimeSpan([1])) == "TimeSpan([1, 0, 0, 0, 0, 0])"

    assert (
        repr(TimeSpan(["1", "2", "3", "4", "5", "6"])) == "TimeSpan([1, 2, 3, 4, 5, 6])"
    )
    assert repr(TimeSpan(["1", "2", "3", "4", "5"])) == "TimeSpan([1, 2, 3, 4, 5, 0])"
    assert repr(TimeSpan(["1", "2", "3", "4"])) == "TimeSpan([1, 2, 3, 4, 0, 0])"
    assert repr(TimeSpan(["1", "2", "3"])) == "TimeSpan([1, 2, 3, 0, 0, 0])"
    assert repr(TimeSpan(["1", "2"])) == "TimeSpan([1, 2, 0, 0, 0, 0])"
    assert repr(TimeSpan(["1"])) == "TimeSpan([1, 0, 0, 0, 0, 0])"

    assert repr(TimeSpan(1, 2, 3, 4, 5, 6)) == "TimeSpan([1, 2, 3, 4, 5, 6])"
    assert repr(TimeSpan(1, 2, 3, 4, 5)) == "TimeSpan([1, 2, 3, 4, 5, 0])"
    assert repr(TimeSpan(1, 2, 3, 4)) == "TimeSpan([1, 2, 3, 4, 0, 0])"
    assert repr(TimeSpan(1, 2, 3)) == "TimeSpan([1, 2, 3, 0, 0, 0])"
    assert repr(TimeSpan(1, 2)) == "TimeSpan([1, 2, 0, 0, 0, 0])"
    assert repr(TimeSpan(1)) == "TimeSpan([1, 0, 0, 0, 0, 0])"

    assert (
        repr(TimeSpan("1", "2", "3", "4", "5", "6")) == "TimeSpan([1, 2, 3, 4, 5, 6])"
    )
    assert repr(TimeSpan("1", "2", "3", "4", "5")) == "TimeSpan([1, 2, 3, 4, 5, 0])"
    assert repr(TimeSpan("1", "2", "3", "4")) == "TimeSpan([1, 2, 3, 4, 0, 0])"
    assert repr(TimeSpan("1", "2", "3")) == "TimeSpan([1, 2, 3, 0, 0, 0])"
    assert repr(TimeSpan("1", "2")) == "TimeSpan([1, 2, 0, 0, 0, 0])"
    assert repr(TimeSpan("1")) == "TimeSpan([1, 0, 0, 0, 0, 0])"

    assert repr(TimeSpan([1, 2 / 3, 4, 5, 6, 7])) == "TimeSpan([1, 2/3, 4, 5, 6, 7])"
    assert (
        repr(TimeSpan(["1", "2/3", "4", "5", "6", "7"]))
        == "TimeSpan([1, 2/3, 4, 5, 6, 7])"
    )
    assert repr(TimeSpan(1, 2 / 3, 4, 5, 6, 7)) == "TimeSpan([1, 2/3, 4, 5, 6, 7])"
    assert (
        repr(TimeSpan("1", "2/3", "4", "5", "6", "7"))
        == "TimeSpan([1, 2/3, 4, 5, 6, 7])"
    )

    assert repr(TimeSpan(timedelta(seconds=273906))) == "TimeSpan([0, 0, 3, 4, 5, 6])"
    assert repr(TimeSpan("P1Y2M3DT4H5M6S")) == "TimeSpan([1, 2, 3, 4, 5, 6])"
    assert repr(TimeSpan("P1Y2M,-P3DT4H5M6S")) == "TimeSpan([1, 2, -3, -4, -5, -6])"
    assert repr(TimeSpan("-P1Y2M,P3DT4H5M6S")) == "TimeSpan([-1, -2, 3, 4, 5, 6])"
    assert repr(TimeSpan("P1Y2/3M4DT5H6M7S")) == "TimeSpan([1, 2/3, 4, 5, 6, 7])"
    assert repr(TimeSpan("P1Y2/3M,-P4DT5H6M7S")) == "TimeSpan([1, 2/3, -4, -5, -6, -7])"
    assert repr(TimeSpan("-P1Y2/3M,P4DT5H6M7S")) == "TimeSpan([-1, -2/3, 4, 5, 6, 7])"


def test_str() -> None:
    assert str(TimeSpan()) == "PT0S"

    assert str(TimeSpan([1, 2, 3, 4, 5, 6])) == "P1Y2M3DT4H5M6S"
    assert str(TimeSpan([1, 2, 3, 4, 5])) == "P1Y2M3DT4H5M"
    assert str(TimeSpan([1, 2, 3, 4])) == "P1Y2M3DT4H"
    assert str(TimeSpan([1, 2, 3])) == "P1Y2M3D"
    assert str(TimeSpan([1, 2])) == "P1Y2M"
    assert str(TimeSpan([1])) == "P1Y"

    assert str(TimeSpan(["1", "2", "3", "4", "5", "6"])) == "P1Y2M3DT4H5M6S"
    assert str(TimeSpan(["1", "2", "3", "4", "5"])) == "P1Y2M3DT4H5M"
    assert str(TimeSpan(["1", "2", "3", "4"])) == "P1Y2M3DT4H"
    assert str(TimeSpan(["1", "2", "3"])) == "P1Y2M3D"
    assert str(TimeSpan(["1", "2"])) == "P1Y2M"
    assert str(TimeSpan(["1"])) == "P1Y"

    assert str(TimeSpan(1, 2, 3, 4, 5, 6)) == "P1Y2M3DT4H5M6S"
    assert str(TimeSpan(1, 2, 3, 4, 5)) == "P1Y2M3DT4H5M"
    assert str(TimeSpan(1, 2, 3, 4)) == "P1Y2M3DT4H"
    assert str(TimeSpan(1, 2, 3)) == "P1Y2M3D"
    assert str(TimeSpan(1, 2)) == "P1Y2M"
    assert str(TimeSpan(1)) == "P1Y"

    assert str(TimeSpan("1", "2", "3", "4", "5", "6")) == "P1Y2M3DT4H5M6S"
    assert str(TimeSpan("1", "2", "3", "4", "5")) == "P1Y2M3DT4H5M"
    assert str(TimeSpan("1", "2", "3", "4")) == "P1Y2M3DT4H"
    assert str(TimeSpan("1", "2", "3")) == "P1Y2M3D"
    assert str(TimeSpan("1", "2")) == "P1Y2M"
    assert str(TimeSpan("1")) == "P1Y"

    assert str(TimeSpan([1, 2 / 3, 4, 5, 6, 7])) == "P1Y2/3M4DT5H6M7S"
    assert str(TimeSpan(["1", "2/3", "4", "5", "6", "7"])) == "P1Y2/3M4DT5H6M7S"
    assert str(TimeSpan(1, 2 / 3, 4, 5, 6, 7)) == "P1Y2/3M4DT5H6M7S"
    assert str(TimeSpan("1", "2/3", "4", "5", "6", "7")) == "P1Y2/3M4DT5H6M7S"

    assert str(TimeSpan(timedelta(seconds=273906))) == "P3DT4H5M6S"
    assert str(TimeSpan("P1Y2M3DT4H5M6S")) == "P1Y2M3DT4H5M6S"
    assert str(TimeSpan("P1Y2M,-P3DT4H5M6S")) == "P1Y2M,-P3DT4H5M6S"
    assert str(TimeSpan("-P1Y2M,P3DT4H5M6S")) == "-P1Y2M,P3DT4H5M6S"
    assert str(TimeSpan("P1Y2/3M4DT5H6M7S")) == "P1Y2/3M4DT5H6M7S"
    assert str(TimeSpan("P1Y2/3M,-P4DT5H6M7S")) == "P1Y2/3M,-P4DT5H6M7S"
    assert str(TimeSpan("-P1Y2/3M,P4DT5H6M7S")) == "-P1Y2/3M,P4DT5H6M7S"


def test_add_subtract() -> None:
    # ----------------------------- #
    # add/subtract TimeSpan objects #
    # ----------------------------- #
    assert TimeSpan([10, 10, 10, 10, 10, 10]) + TimeSpan(
        [1, 2, 3, 4, 5, 6]
    ) == TimeSpan([11, 12, 13, 14, 15, 16])
    assert TimeSpan([10, 10, 10, 10, 10, 10]) - TimeSpan(
        [1, 2, 3, 4, 5, 6]
    ) == TimeSpan([9, 8, 7, 6, 5, 4])
    # -------------------------------------- #
    # in-place add/subtract TimeSpan objects #
    # -------------------------------------- #
    ts = TimeSpan([10, 10, 10, 10, 10, 10])
    ts += TimeSpan([1, 2, 3, 4, 5, 6])
    assert ts == TimeSpan([11, 12, 13, 14, 15, 16])
    ts = TimeSpan([10, 10, 10, 10, 10, 10])
    ts -= TimeSpan([1, 2, 3, 4, 5, 6])
    assert ts == TimeSpan([9, 8, 7, 6, 5, 4])
    # ------------------------------ #
    # add/subtract timedelta objects #
    # ------------------------------ #
    assert TimeSpan([10, 10, 10, 10, 10, 10]) + timedelta(
        days=3, hours=4, minutes=5, seconds=6
    ) == TimeSpan([10, 10, 13, 14, 15, 16])
    assert TimeSpan([10, 10, 10, 10, 10, 10]) - timedelta(
        days=3, hours=4, minutes=5, seconds=6
    ) == TimeSpan([10, 10, 7, 6, 5, 4])
    # --------------------------------------- #
    # in-place add/subtract timedelta objects #
    # --------------------------------------- #
    ts = TimeSpan([10, 10, 10, 10, 10, 10])
    ts += timedelta(days=3, hours=4, minutes=5, seconds=6)
    assert ts == TimeSpan([10, 10, 13, 14, 15, 16])
    ts = TimeSpan([10, 10, 10, 10, 10, 10])
    ts -= timedelta(days=3, hours=4, minutes=5, seconds=6)
    assert ts == TimeSpan([10, 10, 7, 6, 5, 4])
    # -------------------------------------- #
    # add/subtract to/from timedelta objects #
    # -------------------------------------- #
    dt: Optional[timedelta]
    try:
        # should raise excetption since years and months are set
        dt = timedelta(days=3, hours=4, minutes=5, seconds=6) + TimeSpan(
            [10, 10, 10, 10, 10, 10]
        )
    except:
        dt = None
    assert dt is None
    try:
        # should raise excetption since years and months are set
        dt = timedelta(days=3, hours=4, minutes=5, seconds=6) - TimeSpan(
            [10, 10, 10, 10, 10, 10]
        )
    except:
        dt = None
    assert dt is None
    try:
        dt = timedelta(days=3, hours=4, minutes=5, seconds=6) + TimeSpan(
            [0, 0, 10, 10, 10, 10]
        )
    except:
        dt = None
    assert dt == timedelta(days=13, hours=14, minutes=15, seconds=16)
    try:
        dt = timedelta(days=3, hours=4, minutes=5, seconds=6) - TimeSpan(
            [0, 0, 10, 10, 10, 10]
        )
    except:
        dt = None
    assert dt == timedelta(days=-7, hours=-6, minutes=-5, seconds=-4)


def test_total_seconds() -> None:
    seconds: Optional[int]
    try:
        # should raise excetption since years and months are set
        seconds = TimeSpan(1, 2, 3, 4, 5, 6).total_seconds()
    except:
        seconds = None
    assert seconds is None
    assert (
        TimeSpan([0, 0, 3, 4, 5, 6]).total_seconds()
        == 3 * 86400 + 4 * 3600 + 5 * 60 + 6
    )


def test_timedelta() -> None:
    dt: Optional[timedelta]
    try:
        # should raise excetption since years and months are set
        dt = TimeSpan(1, 2, 3, 4, 5, 6).timedelta()
    except:
        dt = None
    assert dt is None
    assert TimeSpan([0, 0, 3, 4, 5, 6]).timedelta() == timedelta(
        days=3, hours=4, minutes=5, seconds=6
    )
