import os, sys

sys.path.append(os.path.abspath("."))

from datetime import datetime
from datetime import timedelta
from hec.hectime import HecTime
from hec.timespan import TimeSpan
from typing import Union

ht1 = HecTime("01Jan2024, 01:00")
ht2 = HecTime("15Jun2025, 07:05")
diff = ht2 - ht1
print(f"ht1 = {ht1} ({repr(ht1)})")
print(f"ht2 = {ht2} ({repr(ht2)})")
print(f"\tht2 - ht1 = {diff} ({repr(diff)})")
diff = ht2 - ht1.datetime()
print(f"\tht2.datetime() = {ht2.datetime()} ({repr(ht2.datetime())})")
print(f"\tht2 - ht1.datetime() = {diff} ({repr(diff)})")
print("")
now1 = HecTime.now()
now2 = HecTime(datetime.now())
print(f"HecTime.now() = {now1} ({repr(now1)})")
print(f"HecTime(datetime.now()) = {now2} ({repr(now2)})")

ts1 = TimeSpan(years=1, days=3, seconds=45)
ts2 = TimeSpan(months=7, hours=6, minutes=4)
print("")
print(f"ts1 = {ts1} ({repr(ts1)})")
print(f"ts2 = {ts2} ({repr(ts2)})")
summ: Union[TimeSpan, timedelta] = ts1 + ts2
print(f"\tts1 + ts2 = {summ} ({repr(summ)})")
diff = ts2 - ts1
print(f"\tts2 - ts1 = {diff} ({repr(diff)})")
try:
    ts1.timedelta()
except Exception as e:
    print(f'\tts1.timedelta() = {e.__class__.__name__}: "{str(e)}"')
print("")
ts3 = TimeSpan(seconds=123456)
td1 = timedelta(seconds=234567)
print(f"ts3 = {ts3} ({repr(ts3)})")
print(f"td1 = {td1} ({repr(td1)})")
summ = ts3 + td1
print(f"\tts3 + td1 = {summ} ({repr(summ)})")
summ = td1 + ts3
print(f"\ttd1 + ts3 = {summ} ({repr(summ)})")
diff = td1 - ts3
print(f"\ttd1 - ts3 = {diff} ({repr(diff)})")
print(f"\tts3.timedelta() = {ts3.timedelta()} ({repr(ts3.timedelta())})")
