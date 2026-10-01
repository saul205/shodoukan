"""Port for the user's imported kanji, including reads through a collection."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from ..entities import KanjiCollection, PracticeKanji


class PracticeKanjiRepository(Protocol):
    def get(self, kanji_id: int, user_id: UUID) -> PracticeKanji | None: ...

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeKanji]: ...

    def list_by_collection(
        self, collection: KanjiCollection, limit: int, offset: int
    ) -> list[PracticeKanji]:
        """Active kanji in the collection, paginated in the database."""
        ...

    def get_by_literal(self, literal: str, user_id: UUID) -> PracticeKanji | None:
        """The user's copy of kanji `literal`, if imported."""
        ...

    def add(self, kanji: PracticeKanji) -> PracticeKanji: ...

    def add_if_absent(self, kanji: PracticeKanji) -> tuple[PracticeKanji, bool]:
        """Store `kanji` unless the user already has it.

        Returns the stored item and whether it was created. Safe against a
        concurrent import of the same item: the existing copy is returned.
        """
        ...

    def update(self, kanji: PracticeKanji) -> PracticeKanji: ...
