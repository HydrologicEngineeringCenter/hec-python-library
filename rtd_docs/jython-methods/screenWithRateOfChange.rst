screenWithRateOfChange()
========================

**Signature:**

.. code-block:: python

    screen_with_value_change_rate(
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **screenWithRateOfChange()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.screen_with_value_change_rate(
        -5.0,
        -1.0,
        1.0,
        5.0
    )

====

**Signature:**

.. code-block:: python

    iscreen_with_value_change_rate(
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
    ) -> TimeSeries

Convenience method for calling ``screen_with_value_change_rate(...)`` with ``in_place=True``.
**Example:**

.. code-block:: python

    ts1.iscreen_with_value_change_rate(
        -5.0,
        -1.0,
        1.0,
        5.0
    )


