screenWithMaxMin()
==================

**Signature:**

.. code-block:: python

    screen_with_value_range(
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **screenWithMaxMin()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.screen_with_value_range(
        510.4,
        532.0,
        774.25,
        820.0
    )

====

**Signature:**

.. code-block:: python

    iscreen_with_value_range(
        min_reject_limit: float = nan,
        min_question_limit: float = nan,
        max_question_limit: float = nan,
        max_reject_limit: float = nan,
    ) -> TimeSeries

Convenience method for call ``screen_with_value_range(...)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.screen_with_value_range(
        510.4,
        532.0,
        774.25,
        820.0
    )

