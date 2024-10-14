@echo off
setlocal
set PYTHONPATH=%~dp0
if "%1" == "" (set SLOW_TEST_COVERAGE=1) else (set SLOW_TEST_COVERAGE=%1)
:--------------------------------------------------------------:
: Warning - 100% coverage can take over 30 minutes to complete :
:                                                              :
: Test coverage of < 100% uses random subsets of the specified :
: size for each large resource file.                           :
:--------------------------------------------------------------:
echo Using SLOW_TEST_COVERAGE of %SLOW_TEST_COVERAGE%%%
pytest test
endlocal