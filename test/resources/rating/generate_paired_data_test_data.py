"""
This is a jython script.
"""
from hec.heclib.dss import HecDss
from hec.heclib.util import Heclib, HecTime
from hec.hecmath import PairedDataMath, TimeSeriesMath
from hec.io import TimeSeriesContainer
from java.lang import Exception as JavaException

A, B, C, D, E, F = 1, 2, 3, 4, 5, 6
def generate_test_data(pathname):
    global dss, out
    test_data = []
    pdm = dss.read(pathname)
    if not isinstance(pdm, PairedDataMath):
        return
    pathname_parts = pathname.split("/")
    params = pathname_parts[C].split("-")
    pdc = pdm.getData()
    length = len(pdc.xOrdinates)
    width = len(pdc.yOrdinates)
    x1 = pdc.xOrdinates
    x1vals = [x1[0] - (x1[1]-x1[0]) / 2., x1[0]]
    for i in range(1, length):
        x1vals.extend([(x1[i-1] + x1[i]) / 2., x1[i]])
    x1vals.append(x1[-1] + (x1[-1] - x1[-2]) / 2.)
    ht = HecTime()
    ht.set("01Jan2025, 01:00")
    base_time = ht.value()
    new_pathname = "/{}/{}/{}//1Hour/Test/".format(pathname_parts[A], pathname_parts[B], params[0])
    tsc1 = TimeSeriesContainer()
    tsc1.fullName = new_pathname
    tsc1.watershed = pathname_parts[A]
    tsc1.location = pathname_parts[B]
    tsc1.parameter = params[0]
    tsc1.type = "INST-VAL"
    tsc1.units = pdc.xunits
    tsc1.version = pathname_parts[F]
    tsc1.times = [base_time + i * 60 for i in range(len(x1vals))]
    tsc1.values = x1vals
    tsc1.numberValues = len(x1vals)
    tsm1 = TimeSeriesMath(tsc1)
    if len(params) == 2:
        if width == 1:
            dss.put(tsc1)
            tsc3 = pdm.ratingTableInterpolation(tsm1).getData()
            dss.put(tsc3)
            out.write("{}\t['{}']\t['{}']\n".format(pdc.fullName, tsc1.fullName, tsc3.fullName))
        else:
            pass # Can't get twoVariableRatingTableInterpolation() to work
            # try:
            #     x2 = [float(label) for label in pdc.labels]
            # except:
            #     return
            # assert pdc.numberCurves == len(pdc.labels)
            # dss.put(tsc1)
            # x2vals = [x2[0] - (x2[1]-x2[0]) / 2., x2[0]]
            # for i in range(1, pdc.numberCurves):
            #     x2vals.extend([(x2[i-1] + x2[i]) / 2., x2[i]])
            # x2vals.append(x2[-1] + (x2[-1] - x2[-2]) / 2.)
            # for x2 in x2vals:
            #     tsc2 = tsc1.clone()
            #     tsc2.version += "-{}".format(x2)
            #     pathname_parts[C] = "Opening"
            #     pathname_parts[D] = ""
            #     pathname_parts[E] = "1Hour"
            #     pathname_parts[F] = tsc2.version
            #     tsc2.fullName = "/".join(pathname_parts)
            #     tsc2.values = tsc2.numberValues * [x2]
            #     dss.put(tsc2)
            #     try:
            #         tsc3 = pdm.twoVariableRatingTableInterpolation(tsm1, TimeSeriesMath(tsc2)).getData()
            #     except Exception as e:
            #         print("ERROR -> {}".format(e))
            #     except JavaException as e:
            #         e.printStackTrace()
            #     else:
            #         tsc3.version += "-{}".format(x2)
            #         pathname_parts[F] = tsc3.version
            #         tsc3.fullName = "/{}/".format("/".join(pathname_parts))
            #         dss.put(tsc3)
    elif len(params) > 2:
        dss.put(tsc1)
        pdcs = []
        tscs = []
        for i in range(1, len(params)):
            pdcs.append(pdc.clone())
            pathname_parts[C] = "{}-{}".format(params[0], params[i])
            pdcs[-1].yparameter = params[i]
            pdcs[-1].numberCurves = 1
            pdcs[-1].yOrdinates = [pdc.yOrdinates[i-1]]
        for pdc in pdcs:
            tscs.append(PairedDataMath(pdc).ratingTableInterpolation(TimeSeriesMath(tsc1)).getData())
            dss.put(tscs[-1])
        out.write("{}\t['{}']\t['{}']\n".format(pdc.fullName, tsc1.fullName, "', '".join([tsc.fullName for tsc in tscs])))
        return
    

import os, sys
dss_filename = os.path.join(os.path.dirname(sys.argv[0]), "Paired_Data.dss")
out_filename = os.path.join(os.path.dirname(sys.argv[0]), "Paired_Data.tsv")
assert os.path.exists(dss_filename), "File {} exists".format(dss_filename)
dss = None
out = None
try:
    Heclib.zset("MLVL", "", 0)
    dss = HecDss.open(dss_filename)
    out = open(out_filename, "wb")
    out.write("# Tab-separated\n")
    out.write("# Field 1: PairedData record in Paired_Data.dss file\n")
    out.write("# Field 2: Input time series (comma separated)")
    out.write("# Field 3: Expected output time series (comma separated)")
    for pn in [pn for pn in dss.getCatalogedPathnames() if pn.split("/")[E] != "1Hour"]:
        generate_test_data(pn)
finally:
    for resource in dss, out:
        if resource:
            resource.close()
    