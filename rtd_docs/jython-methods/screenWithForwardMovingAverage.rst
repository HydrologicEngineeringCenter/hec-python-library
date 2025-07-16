screenWithForwardMovingAverage()
================================

**Signature:**

.. code-block:: python

    screen_with_forward_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
        diff_limit: float,
        failed_validity: str = 'M',
        in_place: bool = False
    ) -> TimeSeries

The hec-python-library equivalent of Jython method **screenWithForwardMovingAverage()**:

.. include:: _in_place.rst

**Example:**

.. code-block:: python

    ts2 = ts1.screen_with_forward_moving_average(
        7,
        True,
        True,
        5.5
    )

====

**Signature:**

.. code-block:: python

    iscreen_with_forward_moving_average(
        window: int,
        only_valid: bool,
        use_reduced: bool,
        diff_limit: float,
        failed_validity: str = 'M',
    ) -> TimeSeries

Convenience method for calling ``screen_with_forward_moving_average(..)`` with ``in_place=True``.

**Example:**

.. code-block:: python

    ts1.iscreen_with_forward_moving_average(
        7,
        True,
        True,
        5.5
    )
