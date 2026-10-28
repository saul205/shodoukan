"""PracticeSentence <-> practice_sentences, its translations and its words.

List order in the domain is stored as `position` (the list index).
"""

from typing import Literal

from ....domain.entities import (
    Inflection,
    PracticeSentence,
    SentenceTranslation,
    SentenceWord,
)
from ..orm import (
    PracticeSentenceORM,
    PracticeSentenceTranslationORM,
    PracticeSentenceWordORM,
)
from .practice_entry_mapper import source_refs


def _origin(value: str) -> Literal["imported", "added"]:
    if value in ("imported", "added"):
        return "imported" if value == "imported" else "added"
    raise ValueError(f"unknown origin {value!r}")


def practice_sentence_to_domain(row: PracticeSentenceORM) -> PracticeSentence:
    return PracticeSentence(
        id=row.id,
        user_id=row.user_id,
        text=row.text,
        translations=[
            SentenceTranslation(lang=t.lang, text=t.text) for t in row.translations
        ],
        words=[_word_to_domain(w) for w in row.words],
        is_active=row.is_active,
        notes=row.notes,
        origin=_origin(row.origin),
        original_id=row.original_id,
        source_id=row.source_id,
        edited_id=row.edited_id,
        revision=row.revision,
        source_collection_ids=source_refs(row.source_collection_ids),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def practice_sentence_to_db(entity: PracticeSentence) -> PracticeSentenceORM:
    return PracticeSentenceORM(
        id=entity.id,
        user_id=entity.user_id,
        text=entity.text,
        is_active=entity.is_active,
        notes=entity.notes,
        origin=entity.origin,
        original_id=entity.original_id,
        source_id=entity.source_id,
        edited_id=entity.edited_id,
        revision=entity.revision,
        source_collection_ids=list(entity.source_collection_ids),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        # Translations have no identity in the domain: rewritten each time.
        translations=[
            PracticeSentenceTranslationORM(position=i, lang=t.lang, text=t.text)
            for i, t in enumerate(entity.translations)
        ],
        words=[_word_to_db(i, w) for i, w in enumerate(entity.words)],
    )


def _word_to_domain(row: PracticeSentenceWordORM) -> SentenceWord:
    inflection = (
        None
        if row.inflection_endings is None
        else Inflection(endings=tuple(row.inflection_endings), form=row.inflection_form)
    )
    return SentenceWord(
        id=row.id,
        start=row.span_start,
        end=row.span_end,
        lemma=row.lemma,
        reading=row.reading,
        pos=list(row.pos),
        inflection=inflection,
        entry_id=row.entry_id,
        sense_id=row.sense_id,
    )


def _word_to_db(position: int, word: SentenceWord) -> PracticeSentenceWordORM:
    return PracticeSentenceWordORM(
        id=word.id,
        position=position,
        span_start=word.start,
        span_end=word.end,
        lemma=word.lemma,
        reading=word.reading,
        pos=list(word.pos),
        inflection_endings=(
            None if word.inflection is None else list(word.inflection.endings)
        ),
        inflection_form=None if word.inflection is None else word.inflection.form,
        entry_id=word.entry_id,
        sense_id=word.sense_id,
    )
