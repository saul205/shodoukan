"""A practice user.

`subject` is the user's id in the identity provider (the access token's
`sub` claim); it's how a request is matched to a user.

The user's library (every entry and kanji they have imported) is not held
here: it is the set of `PracticeEntry` / `PracticeKanji` rows whose
`user_id` points to this user, loaded through their repositories.
"""

from .timestamped_entity import TimestampedEntity


class User(TimestampedEntity):
    id: int | None
    subject: str
    username: str
