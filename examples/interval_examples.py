import os, sys

sys.path.append(os.path.abspath("."))

from hec.hectime import HecTime
from hec.interval import Interval

i = Interval.getAnyDss(lambda i: i.name == "1Hour")
print(f'\nInterval.getAnyDss(lambda i: i.name=="1Hour") = {i} ({repr(i)})')

i = Interval.getAnyCwms(lambda i: i.name == "1Hour")
print(f'\nInterval.getAnyCwms(lambda i: i.name=="1Hour") = {i} ({repr(i)})')

i = Interval.getAnyDss(lambda i: i.name == "2Hour")
print(f'\nInterval.getAnyDss(lambda i: i.name=="2Hour") = {i} ({repr(i)})')

i = Interval.getAnyCwms(lambda i: i.name == "2Hour")
print(f'\nInterval.getAnyCwms(lambda i: i.name=="2Hour") = {i} ({repr(i)})')

i = Interval.getAnyDss(lambda i: i.name == "2Hours")
print(f'\nInterval.getAnyDss(lambda i: i.name=="2Hours") = {i} ({repr(i)})')

i = Interval.getAnyCwms(lambda i: i.name == "2Hours")
print(f'\nInterval.getAnyCwms(lambda i: i.name=="2Hours") = {i} ({repr(i)})')

intvls = Interval.getAll(lambda i: i.name.startswith("2Hour"))
print(f'\nInterval.getAll(lambda i: i.name.startswith("2Hour")) = {intvls}')

names = Interval.getAllDssNames(lambda i: i.name.find("Month") != -1)
print(
    f'\nintvl = Interval.getAllDssNames(lambda i: i.name.find("Month") != -1) = {names}'
)

intnamesvls = Interval.getAllCwmsNames(lambda i: i.name.find("Month") != -1)
print(
    f'\nintvl = Interval.getAllCwmsNames(lambda i: i.name.find("Month") != -1) = {names}'
)

names = Interval.getAllNames(lambda i: i.name.find("Month") != -1)
print(f'\nintvl = Interval.getAllNames(lambda i: i.name.find("Month") != -1) = {names}')
print(f"\nInterval.getAllDssNames() = {Interval.getAllDssNames()}")
print(f"\nInterval.getAllCwmsNames() = {Interval.getAllCwmsNames()}")
print(f"\nInterval.getAllDssBlockNames() = {Interval.getAllDssBlockNames()}")
print("\nInterval.MINUTES = {")
for k in Interval.MINUTES:
    kk = f"'{k}'"
    print(f"\t{kk.ljust(12)} : {Interval.MINUTES[k]:8d},")
print("}")
