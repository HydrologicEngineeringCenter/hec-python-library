del dssmath_test.dss
(echo read data.txt & echo fi) > dssutl.in & call dssutl ds=DSSMATH_test.dss in=dssutl.in
del dssutl.in
call dssmath
