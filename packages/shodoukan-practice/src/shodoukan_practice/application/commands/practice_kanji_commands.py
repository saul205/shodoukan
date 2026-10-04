"""Use cases that customise a kanji in the user's library.

Same shape as `practice_entry_commands`: load the user's kanji, call one
domain method, store and return it. None of them commit.
"""

from uuid import UUID

from ...domain.entities import KanjiPart, PracticeKanji
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeKanjiRepository


class _KanjiCommand:
    def __init__(self, kanji: PracticeKanjiRepository) -> None:
        self._kanji = kanji

    def _load(self, user_id: UUID, kanji_id: int) -> PracticeKanji:
        kanji = self._kanji.get(kanji_id, user_id)
        if kanji is None:
            raise EntityNotFoundError(f"kanji {kanji_id} not found")
        return kanji


class SetKanjiActive(_KanjiCommand):
    """Activate or deactivate a kanji; inactive ones are left out of practice."""

    def execute(self, user_id: UUID, kanji_id: int, active: bool) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        if active:
            kanji.activate()
        else:
            kanji.deactivate()
        return self._kanji.update(kanji)


class SetKanjiNotes(_KanjiCommand):
    """Replace the kanji's note; a blank note removes it."""

    def execute(self, user_id: UUID, kanji_id: int, notes: str | None) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        kanji.set_notes(notes)
        return self._kanji.update(kanji)


class SetKanjiPartEnabled(_KanjiCommand):
    """Show or hide one reading (on, kun or nanori) or meaning."""

    def execute(
        self,
        user_id: UUID,
        kanji_id: int,
        part: KanjiPart,
        item_id: int,
        enabled: bool,
    ) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        kanji.set_enabled(part, item_id, enabled)
        return self._kanji.update(kanji)


class AddKanjiMeaning(_KanjiCommand):
    """Add a meaning of the user's own to the kanji."""

    def execute(
        self, user_id: UUID, kanji_id: int, text: str, lang: str
    ) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        kanji.add_meaning(text, lang)
        return self._kanji.update(kanji)


class EditKanjiMeaning(_KanjiCommand):
    """Change the text of one of the user's own meanings."""

    def execute(
        self, user_id: UUID, kanji_id: int, meaning_id: int, text: str
    ) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        kanji.edit_meaning(meaning_id, text)
        return self._kanji.update(kanji)


class RemoveKanjiMeaning(_KanjiCommand):
    """Remove one of the user's own meanings."""

    def execute(self, user_id: UUID, kanji_id: int, meaning_id: int) -> PracticeKanji:
        kanji = self._load(user_id, kanji_id)
        kanji.remove_meaning(meaning_id)
        return self._kanji.update(kanji)


class RemoveKanjiFromLibrary(_KanjiCommand):
    """Delete the user's copy of a kanji, and take it out of their collections."""

    def execute(self, user_id: UUID, kanji_id: int) -> None:
        self._kanji.delete(self._load(user_id, kanji_id))
