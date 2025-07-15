Math Function Reference
=======================

A guide for moving Jython scripts that use hec.hecmath classes and methods to the hec-python-library.


.. dropdown:: Lookup by topic in `HEC-DSSVue User's Manual <https://www.hec.usace.army.mil/confluence/dssdocs/dssvueum/scripting/math-functions>`_

   - Absolute Value: :doc:`jython-methods/abs`
   - Accumulation (Running) :doc:`jython-methods/accumulation`
   - Arccosine Trigonometric Function :doc:`jython-methods/acos`
   - Add a Constant :doc:`jython-methods/add`
   - Add a Data Set :doc:`jython-methods/add`
   - Apply Multiple Linear Regression Equation :doc:`jython-methods/add`
   - Arcsine Trigonometric Function :doc:`/jython-methods/applyMultipleLinearRegression`
   - Arctangent Trigonometric Function :doc:`/jython-methods/atan`
   - Ceiling Function :doc:`/jython-methods/ceil`
   - Centered Moving Average Smoothing :doc:`/jython-methods/centeredMovingAverage`
   - Conic Interpolation from Elevation/Area Table :doc:`/jython-methods/conicInterpolation`
   - Convert Values to English Units :doc:`/jython-methods/convertToEnglishUnits`
   - Convert Values to Metric (SI) Units :doc:`/jython-methods/convertToMetricUnits`
   - Correlation Coefficients :doc:`/jython-methods/correlationCoefficients`
   - Cosine Trigonometric Function :doc:`jython-methods/cos`
   - Cyclic Analysis (Time Series) :doc:`/jython-methods/cyclicAnalysis`
   - Decaying Basin Wetness Parameter :doc:`/jython-methods/decayingBasinWetnessParameter`
   - Divide by a Constant :doc:`/jython-methods/divide`
   - Divide by a Data Set :doc:`/jython-methods/divide`
   - Estimate Values for Missing Precipitation Data :doc:`/jython-methods/estimateForMissingPrecipValues`
   - Estimate Values for Missing Data :doc:`/jython-methods/estimateForMissingValues`
   - Exponent :doc:`/jython-methods/exp`
   - Exponentiation Function :doc:`/jython-methods/exponentiation`
   - Exponentiation Timeseries Function :doc:`/jython-methods/exponentiation`
   - Extract Time Series Data at Unique Time Specification :doc:`/jython-methods/extractTimeSeriesDataForTimeSpecification`
   - First Valid Date :doc:`/jython-methods/firstValidDate`
   - First Valid Value :doc:`/jython-methods/firstValidValue`
   - Floor Function :doc:`/jython-methods/floor`
   - Flow Accumulator Gage (Compute Period Average Flows) :doc:`/jython-methods/flowAccumulatorGageProcessor`
   - Modulo Function with both Arguments are Greater than Zero :doc:`/jython-methods/fmod`
   - Forward Moving Average Smoothing :doc:`/jython-methods/forwardMovingAverage`
   - Forward Moving Average Smoothing of Time Series :doc:`/jython-methods/forwardMovingAverage`
   - Generate Paired Data from Two Time Series :doc:`/jython-methods/generatePairedData`
   - Generate a Regular Interval Time Series :doc:`/jython-methods/generateRegularIntervalTimeSeries`
   - Get Data Container :doc:`/jython-methods/getData`
   - Get Data Type for Time Series Data Set :doc:`/jython-methods/getType`
   - Get Units Label for Data Set :doc:`/jython-methods/getUnits`
   - Gmean :doc:`/jython-methods/gmean`
   - Hmean :doc:`/jython-methods/hmean`
   - Integer Division by a Constant :doc:`/jython-methods/integerDivide`
   - Integer Divison by an Object :doc:`/jython-methods/integerDivide`
   - Interpolate Time Series Data at Regular Intervals :doc:`/jython-methods/interpolateDataAtRegularInterval`
   - Inverse (1/X) Function :doc:`/jython-methods/inverse`
   - Determine if Data is in English Units :doc:`/jython-methods/isEnglish`
   - Determine if Data is in Metric Units :doc:`/jython-methods/isMetric`
   - Determine if Computation Stable for Given Muskingum Routing Parameters :doc:`/jython-methods/isMuskingumRoutingStable`
   - Last Valid Value's Date and Time :doc:`/jython-methods/lastValidDate`
   - Last Valid Value in a Time Series :doc:`/jython-methods/lastValidValue`
   - Natural Log, Base "e" Function :doc:`/jython-methods/log`
   - Log Base 10 Function :doc:`/jython-methods/log10`
   - Maximum Value in a Time Series :doc:`/jython-methods/max`
   - Maximum Value in a Time Series (tsMathArrary) :doc:`/jython-methods/max`
   - Maximum Value's Date and Time :doc:`/jython-methods/maxDate`
   - Mean Time Series Value :doc:`/jython-methods/mean`
   - Mean Time Series Value (tsMathArray) :doc:`/jython-methods/mean`
   - Median Time Series Value :doc:`/jython-methods/med`
   - Merge Paired Data Sets :doc:`/jython-methods/mergePairedData`
   - Merge Two Time Series Data Sets :doc:`/jython-methods/mergeTimeSeries`
   - Minimum Value in a Time Series :doc:`/jython-methods/min`
   - Minimum Value in a Time Series (tsMathArray) :doc:`/jython-methods/min`
   - Minimum Value's Date and Time :doc:`/jython-methods/minDate`
   - Modified Puls or Working R&D Routing Function :doc:`/jython-methods/modifiedPulsRouting`
   - Modulo :doc:`/jython-methods/modulo`
   - Modulo (tsMath) :doc:`/jython-methods/modulo`
   - Multiple Linear Regression Coefficients :doc:`/jython-methods/multipleLinearRegression`
   - Multiply by a Constant :doc:`/jython-methods/multiply`
   - Multiply by a Data Set :doc:`/jython-methods/multiply`
   - Muskingum Hydrologic Routing Function :doc:`/jython-methods/muskingumRouting`
   - Negation Function :doc:`/jython-methods/negative`
   - Number of Invalid Values in a Time Series :doc:`/jython-methods/numberInvalidValues`
   - Number of Missing Values in a Time Series :doc:`/jython-methods/numberMissingValues`
   - Number of Questioned Values in a Time Series :doc:`/jython-methods/numberQuestionedValues`
   - Number of Rejected Values in a Time Series :doc:`/jython-methods/numberRejectedValues`
   - Number of Valid Values in a Time Series :doc:`/jython-methods/numberValidValues`
   - Olympic Smoothing :doc:`/jython-methods/olympicSmoothing`
   - P1 Function :doc:`/jython-methods/p1`
   - P2 Function :doc:`/jython-methods/p2`
   - P5 Function :doc:`/jython-methods/p5`
   - P10 Function :doc:`/jython-methods/p10`
   - P20 Function :doc:`/jython-methods/p20`
   - P25 Function :doc:`/jython-methods/p25`
   - P75 Function :doc:`/jython-methods/p75`
   - P80 Function :doc:`/jython-methods/p80`
   - *P89 Function (mislabeled in doc)* :doc:`/jython-methods/p98`
   - P90 Function :doc:`/jython-methods/p90`
   - P95 Function :doc:`/jython-methods/p95`
   - *P98 Function (missing from doc)* :doc:`/jython-methods/p98`
   - P99 Function :doc:`/jython-methods/p99`
   - Period Constants Generation :doc:`/jython-methods/periodConstants`
   - Polynomial Transformation :doc:`/jython-methods/polynomialTransformation`
   - Polynomial Transformation with Integral :doc:`/jython-methods/polynomialTransformationWithIntegral`
   - Product Function :doc:`/jython-methods/product`
   - Rating Table Interpolation :doc:`/jython-methods/ratingTableInterpolation`
   - Replace Specific Values :doc:`/jython-methods/replaceSpecificValues`
   - Reverse Rating Table Interpolation :doc:`/jython-methods/reverseRatingTableInterpolation`
   - RMS Function :doc:`/jython-methods/rms`
   - Round to Nearest Whole Number :doc:`/jython-methods/round`
   - Round Off to Specified Precision :doc:`/jython-methods/roundOff`
   - Screen for Erroneous Values Based on Constant Value :doc:`/jython-methods/screenWithConstantValue`
   - Screen for Erroneous Values Based on Duration Magnitude :doc:`/jython-methods/screenWithDurationMagnitude`
   - Screen for Erroneous Values Based on Forward Moving Average :doc:`/jython-methods/screenWithForwardMovingAverage`
   - Screen for Erroneous Values Based on Forward Moving Average (Missing Values) :doc:`/jython-methods/screenWithForwardMovingAverage`
   - Screen for Erroneous Values Based on Maximum/Minimum Range (Missing Values) :doc:`/jython-methods/screenWithMaxMin`
   - Screen for Erroneous Values Based on Maximum/Minimum Range :doc:`/jython-methods/screenWithMaxMin`
   - Screen for Erroneous Values Based on Maximum/Minimum Range (Quality) :doc:`/jython-methods/screenWithMaxMin`
   - Screen for Erroneous Values Based on Maximum/Minimum Range (Limits) :doc:`/jython-methods/screenWithMaxMin`
   - Screen for Erroneous Values Based on Rate of Change :doc:`/jython-methods/screenWithRateOfChange`
   - Select a Paired Data Curve by Curve Label :doc:`/jython-methods/setCurve`
   - Select a Paired Data Curve by Curve Number :doc:`/jython-methods/setCurve`
   - Set Data Container :doc:`/jython-methods/setData`
   - Set Location Name for Data Set :doc:`/jython-methods/setLocation`
   - Set Parameter for Data Set :doc:`/jython-methods/setParameterPart`
   - Set Pathname for Data Set :doc:`/jython-methods/setPathname`
   - Set Time Interval for Data Set :doc:`/jython-methods/setTimeInterval`
   - Set Data Type for Time Series Data Set :doc:`/jython-methods/setType`
   - Set Units Label for Data Set :doc:`/jython-methods/setUnits`
   - Set Version Name for Data Set :doc:`/jython-methods/setVersion`
   - Set Watershed Name for Data Set :doc:`/jython-methods/setWatershed`
   - Shift Adjustment of Time Series Data :doc:`/jython-methods/shiftAdjustment`
   - Shift Time Series in Time :doc:`/jython-methods/shiftInTime`
   - Sign Function :doc:`/jython-methods/sign`
   - Sine Trigonometric Function :doc:`/jython-methods/sin`
   - Skew Coefficient :doc:`/jython-methods/skewCoefficient`
   - Snap Irregular Times to Nearest Regular Period :doc:`/jython-methods/snapToRegularInterval`
   - Square Root :doc:`/jython-methods/sqrt`
   - Standard Deviation of Time Series :doc:`/jython-methods/standardDeviation`
   - Standard Deviation of Time Series (tsMathArray) :doc:`/jython-methods/standardDeviation`
   - Straddle Stagger Hydrologic Routing :doc:`/jython-methods/straddleStaggerRouting`
   - Subtract a Constant :doc:`/jython-methods/subtract`
   - Subtract a Data Set :doc:`/jython-methods/subtract`
   - Successive Differences for Time Series :doc:`/jython-methods/successiveDifferences`
   - Sum Values in Time Series :doc:`/jython-methods/sum`
   - Sum Values in Time Series (tsMathArray) :doc:`/jython-methods/sum`
   - Tangent Trigonometric Function :doc:`/jython-methods/tan`
   - Time Derivative (Difference per Unit Time) :doc:`/jython-methods/timeDerivative`
   - Transform Time Series to Regular Interval :doc:`/jython-methods/transformTimeSeries`
   - Transform Time Series to Irregular Interval :doc:`/jython-methods/transformTimeSeries`
   - Truncate to Whole Numbers :doc:`/jython-methods/truncate`
   - Two Variable Rating Table Interpolation :doc:`/jython-methods/twoVariableRatingTableInterpolation`
   - Variance Function :doc:`/jython-methods/variance`

.. toctree::
   :maxdepth: 1
   :caption: Jython method names:

   jython-methods/abs
   jython-methods/accumulation
   jython-methods/acos
   jython-methods/add
   jython-methods/applyMultipleLinearRegression
   jython-methods/asin
   jython-methods/atan
   jython-methods/ceil
   jython-methods/centeredMovingAverage
   jython-methods/conicInterpolation
   jython-methods/convertToEnglishUnits
   jython-methods/convertToMetricUnits
   jython-methods/correlationCoefficients
   jython-methods/cos
   jython-methods/cyclicAnalysis
   jython-methods/decayingBasinWetnessParameter
   jython-methods/divide
   jython-methods/estimateForMissingPrecipValues
   jython-methods/exp
   jython-methods/exponentiation
   jython-methods/extractTimeSeriesDataForTimeSpecification
   jython-methods/firstValidDate
   jython-methods/firstValidValue
   jython-methods/floor
   jython-methods/flowAccumulatorGageProcessor
   jython-methods/fmod
   jython-methods/forwardMovingAverage
   jython-methods/generatePairedData
   jython-methods/generateRegularIntervalTimeSeries
   jython-methods/getData
   jython-methods/getType
   jython-methods/getUnits
   jython-methods/hmean
   jython-methods/integerDivide
   jython-methods/interpolateDataAtRegularInterval
   jython-methods/inverse
   jython-methods/isEnglish
   jython-methods/isMetric
   jython-methods/isMuskingumRoutingStable
   jython-methods/lastValidDate
   jython-methods/lastValidValue
   jython-methods/log
   jython-methods/log10
   jython-methods/max
   jython-methods/maxDate
   jython-methods/mean
   jython-methods/med
   jython-methods/mergePairedData
   jython-methods/min
   jython-methods/minDate
   jython-methods/modifiedPulsRouting
   jython-methods/modulo
   jython-methods/multipleLinearRegression
   jython-methods/multiply
   jython-methods/muskingumRouting
   jython-methods/negative
   jython-methods/numberInvalidValues
   jython-methods/numberMissingValues
   jython-methods/numberQuestionedValues
   jython-methods/numberValidValues
   jython-methods/olympicSmoothing
   jython-methods/p1
   jython-methods/p2
   jython-methods/p5
   jython-methods/p10
   jython-methods/p20
   jython-methods/p25
   jython-methods/p75
   jython-methods/p80
   jython-methods/p89
   jython-methods/p90
   jython-methods/p95
   jython-methods/p99
   jython-methods/periodConstants
   jython-methods/polynomialTransformation
   jython-methods/product
   jython-methods/ratingTableInterpolation
   jython-methods/replaceSpecificValues
   jython-methods/reverseRatingTableInterpolation
   jython-methods/rms
   jython-methods/round
   jython-methods/roundOff
   jython-methods/screenWithConstantValue
   jython-methods/screenWithDurationMagnitude
   jython-methods/screenWithForwardMovingAverage
   jython-methods/screenWithMaxMin
   jython-methods/screenWithRateOfChange
   jython-methods/setCurve
   jython-methods/setData
   jython-methods/setLocation
   jython-methods/setParameterPart
   jython-methods/setPathname
   jython-methods/setTimeInterval
   jython-methods/setType
   jython-methods/setUnits
   jython-methods/setVersion
   jython-methods/setWatershed
   jython-methods/shiftAdjustment
   jython-methods/shiftInTime
   jython-methods/sign
   jython-methods/sin
   jython-methods/skewCoefficient
   jython-methods/snapToRegularInterval
   jython-methods/sqrt
   jython-methods/standardDeviation
   jython-methods/straddleStaggerRouting
   jython-methods/subtract
   jython-methods/successiveDifferences
   jython-methods/sum
   jython-methods/tan
   jython-methods/timeDerivative
   jython-methods/transformTimeSeries
   jython-methods/truncate
   jython-methods/twoVariableRatingTableInterpolation
   jython-methods/variance
