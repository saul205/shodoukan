"""The sentences a word brings when it's imported: its JMDict examples
(`add_dictionary_sentences`), and a shared collection's examples of it
(`merge_shared_sentences`).

Shared by the use cases that import words (one at a time, or with a
collection). Whatever they create or change is stored and completed with the
analyzer (`save_sentences`), so an imported word's gaps can be asked at once.
"""

from collections.abc import Mapping, Sequence

from ...domain.entities import (
    JAPANESE,
    PracticeEntry,
    PracticeSentence,
    SentenceTranslation,
    SharedEntry,
    SharedExample,
    SourceRef,
)
from ...domain.gateways import (
    DictionaryExample,
    DictionaryExampleSentence,
    MorphologyGateway,
)
from ...domain.repositories import PracticeEntryRepository, PracticeSentenceRepository
from ...domain.services import entry_study_text, merge_examples
from .practice_sentence_commands import complete_words, entry_forms

# Study texts are read for the forms only; the meanings' language is moot.
_ANY_LANG = "eng"


def add_dictionary_sentences(
    sentences: PracticeSentenceRepository,
    entries: PracticeEntryRepository,
    morphology: MorphologyGateway,
    entry: PracticeEntry,
    sense_examples: Sequence[Sequence[DictionaryExample]],
) -> None:
    """Store the dictionary examples of a word just imported (`entry`; the
    examples of each of its dictionary senses, `sense_examples`) as sentences
    linked to it and to their sense.

    A sentence the user already has from another word (same text) gets this
    word as one more of its words instead of being stored twice. A sentence
    under two senses of the entry is linked to the first.
    """
    if entry.id is None:
        raise ValueError("the entry must be stored first")
    imported = [s for s in entry.senses if s.origin == "imported"]
    examples = [
        (sense.id, example, _japanese(example.sentences))
        for sense, examples in zip(imported, sense_examples, strict=False)
        for example in examples
    ]
    existing = sentences.imported_by_text(
        [text for _, _, text in examples if text], entry.user_id
    )
    created: dict[str, PracticeSentence] = {}
    changed: dict[str, PracticeSentence] = {}
    for sense_id, example, text in examples:
        if not text:
            continue
        if text in existing:
            if existing[text].add_dictionary_word(example.text, entry.id, sense_id):
                changed[text] = existing[text]
        elif text in created:
            created[text].add_dictionary_word(example.text, entry.id, sense_id)
        else:
            created[text] = PracticeSentence.from_dictionary(
                entry.user_id,
                text,
                [
                    SentenceTranslation(lang=s.lang, text=s.text)
                    for s in example.sentences
                ],
                word=example.text,
                entry_id=entry.id,
                sense_id=sense_id,
            )
    save_sentences(
        sentences,
        entries,
        morphology,
        list(created.values()),
        list(changed.values()),
        forms=word_forms(entry),
    )


def save_sentences(
    sentences: PracticeSentenceRepository,
    entries: PracticeEntryRepository,
    morphology: MorphologyGateway,
    created: Sequence[PracticeSentence],
    changed: Sequence[PracticeSentence],
    forms: Mapping[int, Sequence[str]] | None = None,
) -> list[PracticeSentence]:
    """Complete the words of new and changed sentences with the analyzer (a
    gap analyzed, a linked word given its gap), then store them, each once.
    `forms` are the linked entries' spellings and readings when the caller
    has them (a word it just imported); otherwise they're read."""
    pending = [*created, *changed]
    if not pending:
        return []
    if forms is None:
        forms = entry_forms(
            entries,
            {w.entry_id for s in pending for w in s.words if w.entry_id},
            pending[0].user_id,
        )
    for sentence in pending:
        complete_words(sentence, morphology, forms)
    return [sentences.add(s) for s in created] + [sentences.update(s) for s in changed]


def word_forms(entry: PracticeEntry) -> dict[int, tuple[str, ...]]:
    """The entry's enabled spellings and readings, by its id: `save_sentences`'
    `forms` for a word in memory."""
    if entry.id is None:
        return {}
    text = entry_study_text(entry, _ANY_LANG)
    return {entry.id: (*text.spellings, *text.readings)}


def merge_shared_sentences(
    sentences: PracticeSentenceRepository,
    entries: PracticeEntryRepository,
    morphology: MorphologyGateway,
    entry: PracticeEntry,
    shared: SharedEntry,
    *,
    created: bool,
    source: SourceRef | None,
) -> None:
    """Bring the shared word's examples into the user's sentences
    (`merge_examples`), for the user's stored copy of it (`entry`)."""
    if entry.id is None:
        raise ValueError("the entry must be stored first")
    examples = [e for sense in shared.senses for e in sense.examples]
    if not examples:
        return
    texts = [
        text
        for e in examples
        if e.origin == "imported" and (text := _shared_japanese(e))
    ]
    versions = {e.version for e in examples if e.origin == "added" and e.version}
    # A word just created has only the sentences found by text or version.
    of_word = [] if created else sentences.for_entry(entry.id, entry.user_id)
    candidates = {
        s.id: s
        for s in [
            *of_word,
            *sentences.imported_by_text(texts, entry.user_id).values(),
            *sentences.by_versions(versions, entry.user_id),
        ]
    }
    merge = merge_examples(
        entry, shared, list(candidates.values()), created=created, source=source
    )
    save_sentences(
        sentences,
        entries,
        morphology,
        merge.created,
        merge.changed,
        forms=word_forms(entry),
    )


def _japanese(sentences: Sequence[DictionaryExampleSentence]) -> str:
    return next((s.text.strip() for s in sentences if s.lang == JAPANESE), "")


def _shared_japanese(example: SharedExample) -> str:
    return next((s.text.strip() for s in example.sentences if s.lang == JAPANESE), "")
