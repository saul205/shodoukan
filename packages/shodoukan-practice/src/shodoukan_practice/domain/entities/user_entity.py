"""A practice user.

The user's library (every entry and kanji they have imported) is not held
here: it is the set of `PracticeEntry` / `PracticeKanji` rows whose
`user_id` points to this user, loaded through their repositories.
"""

from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    id: int | None
    username: str
    created_at: datetime
    updated_at: datetime
