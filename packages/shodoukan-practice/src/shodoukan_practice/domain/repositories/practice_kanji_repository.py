"""Port for the user's imported kanji: loading, searching (also within a
collection) and storing them."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from ..entities import KanjiCollection, PracticeKanji
from ..searches import LibrarySearch, SearchScope


class PracticeKanjiRepository(Protocol):
    def get(self, kanji_id: int, user_id: UUID) -> PracticeKanji | None: ...

    def get_many(self, ids: Iterable[int], user_id: UUID) -> list[PracticeKanji]: ...

    def find(
        self,
        user_id: UUID,
        search: LibrarySearch,
        scope: SearchScope[KanjiCollection],
        limit: int,
        offset: int,
    ) -> list[PracticeKanji]:
        """The user's items that match `search` within `scope`, paginated.

        Best match first (`MatchTier`), then the scope's own order: most
        recently imported first in the library, the order they were added
        in a collection. Without text, only the scope and `active` filter.
        """
        ...

    def count(
        self, user_id: UUID, search: LibrarySearch, scope: SearchScope[KanjiCollection]
    ) -> int:
        """How many items `find` pages through."""
        ...

    def get_by_literal(self, literal: str, user_id: UUID) -> PracticeKanji | None:
        """The user's copy of kanji `literal`, if imported."""
        ...

    def practice_ids_by_literal(
        self, literals: Iterable[str], user_id: UUID
    ) -> dict[str, int]:
        """`{literal: practice id}` for the ones the user has imported.

        Lightweight: no snapshot is loaded.
        """
        ...

    def add(self, kanji: PracticeKanji) -> PracticeKanji: ...

    def add_if_absent(self, kanji: PracticeKanji) -> tuple[PracticeKanji, bool]:
        """Store `kanji` unless the user already has it.

        Returns the stored item and whether it was created. Safe against a
        concurrent import of the same item: the existing copy is returned.
        """
        ...

    def update(self, kanji: PracticeKanji) -> PracticeKanji: ...

    def delete(self, kanji: PracticeKanji) -> None:
        """Remove it from the library, with its collection links.

        Raises `EntityNotFoundError` if it isn't stored for its user.
        """
        ...
