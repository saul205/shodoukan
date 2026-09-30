"""A practice user.

The user's library (every entry and kanji they have imported) is not held
here: it is the set of `PracticeEntry` / `PracticeKanji` rows whose
`user_id` points to this user, loaded through their repositories.
"""

from .timestamped_entity import TimestampedEntity


class User(TimestampedEntity):
    id: int | None
    username: str
