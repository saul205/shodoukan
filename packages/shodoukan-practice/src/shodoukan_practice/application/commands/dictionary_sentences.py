"""The JMDict example sentences of an entry the user just imported.

Shared by the use cases that import dictionary entries (one at a time, or
with a collection).
"""

from ...domain.entities import (
    JAPANESE,
    PracticeEntry,
    PracticeExampleSentence,
    PracticeSentence,
    SentenceTranslation,
)
from ...domain.repositories import PracticeSentenceRepository


def add_dictionary_sentences(
    sentences: PracticeSentenceRepository, entry: PracticeEntry
) -> None:
    """Store the entry's dictionary examples as sentences linked to it.

    A sentence the user already has from another word (same text) gets this
    word as one more of its words instead of being stored twice. A sentence
    under two senses of the entry is linked to the first.
    """
    if entry.id is None:
        raise ValueError("the entry must be stored first")
    examples = [
        (sense.id, example, _japanese(example.sentences))
        for sense in entry.senses
        for example in sense.examples
        if example.origin == "imported"
    ]
    texts = [text for _, _, text in examples if text]
    existing = sentences.imported_by_text(texts, entry.user_id)
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
                    if s.lang != JAPANESE
                ],
                word=example.text,
                entry_id=entry.id,
                sense_id=sense_id,
            )
    for sentence in created.values():
        sentences.add(sentence)
    for sentence in changed.values():
        sentences.update(sentence)


def _japanese(sentences: list[PracticeExampleSentence]) -> str:
    return next((s.text.strip() for s in sentences if s.lang == JAPANESE), "")
