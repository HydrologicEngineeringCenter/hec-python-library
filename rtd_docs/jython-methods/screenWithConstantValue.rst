screenWithConstantValue()
=========================

**Signature:**

.. code-block:: python

    screen_with_constant_value(
        duration: Union[hec.Duration, str],
        missing_limit: float = nan,
        reject_limit: float = nan,
        question_limit: float = nan,
        min_threshold: float = nan,
        percent_valid_required: float = nan,
        in_place: bool = False
    ) -> TimeSeries

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.screen_with_constant_value>`_

The hec-python-library equivalent of Jython method **screenWithConstantValue()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.screen_with_constant_value(
        "1Day", 
        0.1, 
        min_threshold=1.0
    )

====

**Signature:**

.. code-block:: python

    iscreen_with_constant_value(
        duration: Union[hec.Duration, str],
        missing_limit: float = nan,
        reject_limit: float = nan,
        question_limit: float = nan,
        min_threshold: float = nan,
        percent_valid_required: float = nan,
    ) -> TimeSeries

Convenience method for calling ``screen_with_constant_value(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.iscreen_with_constant_value(
        "1Day", 
        0.1, 
        min_threshold=1.0
    )
