There is no separation of the "math object" and the "data container" in this library. ``TimeSeries`` objects have
read-only properties named ``times``, ``values``, and ``qualities`` that allow access to those items. In addition,
the ``tsv`` read-only property presents a list of ``TimeSeriesValue`` objects, each with its own time, value, and quality.

For advanced usage, the ``data`` read-only property allows direct access to a ``TimeSeries`` object's internal data
frame. While the data frame cannot be replaced via the property, it *can* be modified (for an example see :doc:`exp`).