"""Port for the sentences of the user's library."""

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from ..entities import PracticeSentence


class PracticeSentenceRepository(Protocol):
    def get(self, sentence_id: int, user_id: UUID) -> PracticeSentence | None: ...

    def for_entry(self, entry_id: int, user_id: UUID) -> list[PracticeSentence]:
        """The user's sentences with a word linked to entry `entry_id`, oldest
        first: "the sentences of a word"."""
        ...

    def imported_by_text(
        self, texts: Iterable[str], user_id: UUID
    ) -> dict[str, PracticeSentence]:
        """The user's dictionary sentences among `texts`, by text: importing a
        word reuses a sentence the user already has from another word."""
        ...

    def needing_analysis(self, user_id: UUID) -> list[PracticeSentence]:
        """The user's sentences with a word to analyze: one with a span and
        no analysis, or one linked to a word but without a span."""
        ...

    def users_needing_analysis(self) -> list[UUID]:
        """The users with sentences `needing_analysis`. The one query across
        users: maintenance (`analyze-sentences`) goes user by user."""
        ...

    def add(self, sentence: PracticeSentence) -> PracticeSentence: ...

    def update(self, sentence: PracticeSentence) -> PracticeSentence:
        """Raises `EntityNotFoundError` if it isn't stored, or isn't the user's."""
        ...

    def delete(self, sentence: PracticeSentence) -> None: ...
