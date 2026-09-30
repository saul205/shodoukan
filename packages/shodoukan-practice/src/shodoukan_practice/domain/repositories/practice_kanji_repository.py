"""Port for the user's imported kanji, including reads through a collection."""

from collections.abc import Iterable
from typing import Protocol

from ..entities import KanjiCollection, PracticeKanji


class PracticeKanjiRepository(Protocol):
    def get(self, kanji_id: int, user_id: int) -> PracticeKanji | None: ...

    def get_many(self, ids: Iterable[int], user_id: int) -> list[PracticeKanji]: ...

    def list_by_collection(
        self, collection: KanjiCollection, limit: int, offset: int
    ) -> list[PracticeKanji]:
        """Active kanji in the collection, paginated in the database."""
        ...

    def add(self, kanji: PracticeKanji) -> PracticeKanji: ...

    def update(self, kanji: PracticeKanji) -> PracticeKanji: ...
