
Ratings are time-stamped objects that are used to transform independent parameter values to dependent parameter values and (sometimes) vice versa. The transformation method used depends on the specific type of rating object.
There are three times associated with each rating:

- **Effective time** (required) the primary time stamp of the rating; specifies the date/time at which the rating come into effect
- **Creation time** (optional) specifies the date/time the rating was created; used when the ``rating_time`` parameter is used on a ``rate(...)`` or ``reverse_rate(...)`` method of a :doc:`RatingSet </classes/AbstractRatingSet>` object
- **Transition start time** (optional) specifies the date/time (prior to the effective time) at which a transition from the previous rating in a rating set should begin

Ratings may have one or more independent parameters and one dependent parameter. Reverse rating is possible only with ratings with a single independent parameter.

Ratings are not normally used directly but rather are used indirectly by their inclusion in :doc:`RatingSet </classes/AbstractRatingSet>` objects. Therefore there are no :doc:`DataStore </classes/AbstractDataStore>` methods
to store or retrieve individual ratings, although catalog methods can be used to determine their various effective times.
