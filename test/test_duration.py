"""Module for testing hec.duration module
"""

from hec.duration import Duration
from hec.interval import Interval


def test_durations() -> None:
    for intvl in Interval.getAllCwms():
        print(intvl.name)
        if intvl.name.startswith("~") or intvl.name.endswith("Local"):
            continue
        for bop in (False, True):
            dur = Duration.forInterval(intvl, bop)
            print(dur, dur.name, dur.minutes, dur.isBop)
            if intvl.minutes == 0:
                assert str(dur) == str(intvl)
                assert dur.isBop
                assert dur.isEop
            else:
                if bop:
                    assert dur.name == f"{intvl.name}BOP"
                else:
                    assert dur.name == intvl.name
                assert str(dur) == str(intvl) + (":BOP" if bop else ":EOP")
                assert dur.isBop == bop
                assert dur.isEop == (not bop)
            assert dur.minutes == intvl.minutes


if __name__ == "__main__":
    test_durations()
