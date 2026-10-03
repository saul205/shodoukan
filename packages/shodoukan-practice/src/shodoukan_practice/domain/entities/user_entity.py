"""A practice user.

`id` is the user's id in the identity provider (the access token's `sub`
claim, a UUID): practice users map 1:1 to provider users. `username` is a
display name taken from the provider (`preferred_username`), not an identity.

The user's library (every entry and kanji they have imported) is not held
here: it is the set of `PracticeEntry` / `PracticeKanji` rows whose
`user_id` points to this user, loaded through their repositories.
"""

from uuid import UUID

from .timestamped_entity import TimestampedEntity


class User(TimestampedEntity):
    id: UUID
    username: str
