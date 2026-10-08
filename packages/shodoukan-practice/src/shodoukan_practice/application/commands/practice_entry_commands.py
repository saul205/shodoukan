"""Use cases that customise an entry in the user's library.

Each loads the user's entry (`EntityNotFoundError` if it isn't theirs),
calls one domain method and stores the result, which it returns so the
caller can show the entry as it is now. The domain enforces that dictionary
data is only ever disabled (`OriginalDataError` otherwise). None of them
commit; the caller owns the transaction.
"""

from uuid import UUID

from ...domain.entities import EntryPart, PracticeEntry
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeEntryRepository


class _EntryCommand:
    def __init__(self, entries: PracticeEntryRepository) -> None:
        self._entries = entries

    def _load(self, user_id: UUID, entry_id: int) -> PracticeEntry:
        entry = self._entries.get(entry_id, user_id)
        if entry is None:
            raise EntityNotFoundError(f"entry {entry_id} not found")
        return entry


class SetEntryActive(_EntryCommand):
    """Activate or deactivate an entry; inactive ones are left out of practice."""

    def execute(self, user_id: UUID, entry_id: int, active: bool) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        if active:
            entry.activate()
        else:
            entry.deactivate()
        return self._entries.update(entry)


class SetEntryNotes(_EntryCommand):
    """Replace the entry's general note; a blank note removes it."""

    def execute(self, user_id: UUID, entry_id: int, notes: str | None) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.set_notes(notes)
        return self._entries.update(entry)


class SetSenseNotes(_EntryCommand):
    """Replace the note on one of the entry's senses."""

    def execute(
        self, user_id: UUID, entry_id: int, sense_id: int, notes: str | None
    ) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.set_sense_notes(sense_id, notes)
        return self._entries.update(entry)


class SetEntryPartEnabled(_EntryCommand):
    """Show or hide one spelling, reading, sense, meaning or example."""

    def execute(
        self,
        user_id: UUID,
        entry_id: int,
        part: EntryPart,
        item_id: int,
        enabled: bool,
    ) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.set_enabled(part, item_id, enabled)
        return self._entries.update(entry)


class AddEntrySense(_EntryCommand):
    """Add a sense of the user's own to the entry, with its first meaning."""

    def execute(
        self, user_id: UUID, entry_id: int, text: str, lang: str
    ) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.add_sense(text, lang)
        return self._entries.update(entry)


class RemoveEntrySense(_EntryCommand):
    """Remove one of the user's own senses, with its meanings and examples."""

    def execute(self, user_id: UUID, entry_id: int, sense_id: int) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.remove_sense(sense_id)
        return self._entries.update(entry)


class AddEntryGloss(_EntryCommand):
    """Add a meaning of the user's own to one of the entry's senses."""

    def execute(
        self, user_id: UUID, entry_id: int, sense_id: int, text: str, lang: str
    ) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.add_gloss(sense_id, text, lang)
        return self._entries.update(entry)


class EditEntryGloss(_EntryCommand):
    """Change the text of one of the user's own meanings."""

    def execute(
        self, user_id: UUID, entry_id: int, gloss_id: int, text: str
    ) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.edit_gloss(gloss_id, text)
        return self._entries.update(entry)


class RemoveEntryGloss(_EntryCommand):
    """Remove one of the user's own meanings."""

    def execute(self, user_id: UUID, entry_id: int, gloss_id: int) -> PracticeEntry:
        entry = self._load(user_id, entry_id)
        entry.remove_gloss(gloss_id)
        return self._entries.update(entry)


class RemoveEntryFromLibrary(_EntryCommand):
    """Delete the user's copy of an entry, and take it out of their collections.

    The dictionary entry itself is untouched and can be imported again.
    """

    def execute(self, user_id: UUID, entry_id: int) -> None:
        self._entries.delete(self._load(user_id, entry_id))
