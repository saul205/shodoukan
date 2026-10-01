"""Port for reading the shodoukan dictionary.

The dictionary is an external, read-only source. The gateway hands back fresh
practice entities ready to be stored in a user's library, so the domain never
depends on the dictionary's own models.
"""

from typing import Protocol

from ..entities import PracticeEntry, PracticeKanji


class DictionaryGateway(Protocol):
    def new_practice_entry(
        self, source_entry_id: int, user_id: int
    ) -> PracticeEntry | None:
        """Snapshot of dictionary entry `source_entry_id` for `user_id`.

        `None` if the dictionary has no such entry. The result isn't stored:
        ids are `None`, everything is enabled and `origin="imported"`.
        """
        ...

    def new_practice_kanji(self, literal: str, user_id: int) -> PracticeKanji | None:
        """Snapshot of dictionary kanji `literal` for `user_id`, or `None`."""
        ...
