"""Port for kanji collections and their membership (link table)."""

from collections.abc import Sequence
from typing import Protocol

from ..entities import KanjiCollection, PracticeKanji


class KanjiCollectionRepository(Protocol):
    def get(self, collection_id: int, user_id: int) -> KanjiCollection | None: ...

    def list_for_user(self, user_id: int) -> list[KanjiCollection]: ...

    def list_for_item(self, kanji: PracticeKanji) -> list[KanjiCollection]:
        """Collections the kanji belongs to (its tags)."""
        ...

    def add_item(self, collection: KanjiCollection, kanji: PracticeKanji) -> None: ...

    def remove_item(
        self, collection: KanjiCollection, kanji: PracticeKanji
    ) -> None: ...

    def item_ids(self, collections: Sequence[KanjiCollection]) -> set[int]:
        """Distinct kanji ids across the collections."""
        ...

    def add(self, collection: KanjiCollection) -> KanjiCollection: ...

    def update(self, collection: KanjiCollection) -> KanjiCollection: ...

    def delete(self, collection: KanjiCollection) -> None: ...
