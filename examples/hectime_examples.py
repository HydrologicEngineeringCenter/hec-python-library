import os, sys

sys.path.append(os.path.abspath("."))
from hec import hectime
from hec.hectime import HecTime
from hec.interval import Interval
from typing import cast
import sys

print("---")
print("--- End-of-month 1Month intervals for a time window")
print("---")
intvl = cast(Interval, Interval.getAny(lambda i: i.name == "1Month"))
start_time = HecTime("2024-01-31, 24:00")
end_time = start_time + "1Y"
count = start_time.computeNumberIntervals(end_time, intvl)
times = [start_time + f"{i}M" for i in range(count)]
for t in times:
    print(t)

print("---")
print("--- LRTS Daily Times in UTC")
print("---")
intvl = cast(Interval, Interval.getAny(lambda i: i.name == "1Day"))
offset = 7 * Interval.MINUTES["1Hour"]
for month in ("Mar", "Nov"):
    start_time = HecTime(f"01{month}2024, 00:00").atTimeZone("US/Central")
    end_time = start_time + "1M"
    first_time = HecTime(start_time)
    if first_time.adjustToIntervalOffset(intvl, offset) < start_time:
        first_time.increment(1, intvl)
    count = first_time.computeNumberIntervals(end_time, intvl)
    times = [(first_time + f"{i}D").astimezone("UTC") for i in range(count)]
    prev = None
    for t in times:
        if prev:
            print(f"{t}\t{(t-prev).total_seconds() // 3600}")
        else:
            print(t)
        prev = t
    print("")

print("---")
print("--- Interval boundaries")
print("---")
t = HecTime.now(hectime.SECOND_GRANULARITY)
t.midnight_as_2400 = False
print("Current Time\t\tIntvl\tTop of Prev\t\tTop of Next")
for intvl in Interval.getAll(lambda i: i.minutes > 0):
    prev = HecTime(t).adjustToIntervalOffset(intvl, 0)
    next = HecTime(prev).increment(1, intvl)
    print(f"{t}\t{intvl}\t{prev}\t{next}")

print("---")
print("--- Date/Time Styles (Generate Style Table)")
print("---")
width = 18
t = HecTime("30Sep2024, 12:34").atTimeZone("local")
print(f"Time = {t}")
print(
    " +----------------------------------------------------------------------------------------------------+"
)
print(
    " | Base Styles                                                                                        |"
)
print(
    " +-----------------------+------------------------+-------------------------+-------------------------+"
)
for row in range(10):
    for col in (0, 10, 100, 110):
        style = row + col
        sys.stdout.write(f" | {style}: {t.date(style).rjust(width)}")
    print(" |")
    print(
        " +-----------------------+------------------------+-------------------------+-------------------------+"
    )
print(
    " | Extended Styles                                                                                    |"
)
print(
    " +-----------------------+------------------------+-------------------------+-------------------------+"
)
for row in (-1, -2, -3):
    for col in (0, 10, 100, 110):
        style = row - col
        if style == -3:
            sys.stdout.write(" |                      ")
        elif style in (-103, -113):
            sys.stdout.write(" |                        ")
        else:
            sys.stdout.write(f" |{style}: {t.date(style).rjust(width)}")
    print(" |")
    print(
        " +-----------------------+------------------------+-------------------------+-------------------------+"
    )

format = "%A, %B %d, %Y %H:%M:%S %z"
dateTimeStr = t.strftime(format)
print(f"Using strftime()  : {dateTimeStr}")
t.setUndefined()
t.atTimeZone(None)
print(f"Before strptime() : {repr(t)}")
print(f"After strptime()  : {t.strptime(dateTimeStr, format)}")
