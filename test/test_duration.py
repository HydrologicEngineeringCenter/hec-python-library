"""Module for testing hec.duration module"""

from hec import Duration, Interval


def test_durations() -> None:
    for intvl in Interval.get_all_cwms():
        print(intvl.name)
        if intvl.name.startswith("~") or intvl.name.endswith("Local"):
            continue
        for bop in (False, True):
            dur = Duration.for_interval(intvl, bop)
            print(dur, dur.name, dur.minutes, dur.is_bop)
            if intvl.minutes == 0:
                assert str(dur) == str(intvl)
                assert dur.is_bop
                assert dur.is_eop
            else:
                if bop:
                    assert dur.name == f"{intvl.name}BOP"
                else:
                    assert dur.name == intvl.name
                assert str(dur) == str(intvl) + (":BOP" if bop else ":EOP")
                assert dur.is_bop == bop
                assert dur.is_eop == (not bop)
            assert dur.minutes == intvl.minutes


if __name__ == "__main__":
    test_durations()
