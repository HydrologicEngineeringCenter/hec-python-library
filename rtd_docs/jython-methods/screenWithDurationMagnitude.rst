screenWithDurationMagnitude()
=============================

**Signature:**

.. code-block:: python

    screen_with_duration_magnitude(
        duration: Union[hec.Duration, str],
        min_missing_limit: float = nan,
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
        max_missing_limit: float = nan,
        percent_valid_required: float = 0.0,
        in_place: bool = False
    ) -> TimeSeries:

`Detailed Documentation <https://hydrologicengineeringcenter.github.io/hec-python-library/hec/timeseries.html#TimeSeries.screen_with_duration_magnitude>`_

The hec-python-library equivalent of Jython method **screenWithDurationMagnitude()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.screen_with_duration_magnitude(
        "1Day",
        min_missing_limit=0.0,
        max_missing_limit=15.3
    )

====

**Signature:**

.. code-block:: python

    iscreen_with_duration_magnitude(
        duration: Union[hec.Duration, str],
        min_missing_limit: float = nan,
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
        max_missing_limit: float = nan,
        percent_valid_required: float = 0.0,
    ) -> TimeSeries:

Convenience method for calling ``screen_with_duration_magnitude(..)`` with ``in_place=True``

**Example:**

.. code-block:: python

    ts1.iscreen_with_duration_magnitude(
        "1Day",
        min_missing_limit=0.0,
        max_missing_limit=15.3
    )