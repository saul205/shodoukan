from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import Inflection, PracticeSentence
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    GapText,
    PracticeSentenceRepository,
    SentenceSearch,
)
from ..db.mappers import practice_sentence_to_db, practice_sentence_to_domain
from ..db.orm import (
    PracticeSentenceORM,
    PracticeSentenceTranslationORM,
    PracticeSentenceWordORM,
)

_LOAD = (
    selectinload(PracticeSentenceORM.translations),
    selectinload(PracticeSentenceORM.words),
)

# A word to analyze: a gap not analyzed yet, or a linked word with no gap.
_TO_ANALYZE = or_(
    and_(
        PracticeSentenceWordORM.span_start.is_not(None),
        PracticeSentenceWordORM.lemma.is_(None),
    ),
    and_(
        PracticeSentenceWordORM.span_start.is_(None),
        PracticeSentenceWordORM.entry_id.is_not(None),
    ),
)


class SqlAlchemyPracticeSentenceRepository(PracticeSentenceRepository):
    """Flushes but never commits: the caller owns the transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, sentence_id: int, user_id: UUID) -> PracticeSentence | None:
        query = self._select(user_id).where(PracticeSentenceORM.id == sentence_id)
        row = self._session.scalars(query).one_or_none()
        return practice_sentence_to_domain(row) if row else None

    def for_entry(self, entry_id: int, user_id: UUID) -> list[PracticeSentence]:
        return self._find(user_id, PracticeSentenceWordORM.entry_id == entry_id)

    def gaps(
        self, entry_ids: Iterable[int], user_id: UUID, translation_lang: str
    ) -> list[GapText]:
        wanted = list(set(entry_ids))
        if not wanted:
            return []
        word, sentence = PracticeSentenceWordORM, PracticeSentenceORM
        translation = (
            select(PracticeSentenceTranslationORM.text)
            .where(
                PracticeSentenceTranslationORM.sentence_id == sentence.id,
                PracticeSentenceTranslationORM.lang == translation_lang,
            )
            .order_by(PracticeSentenceTranslationORM.position)
            .limit(1)
            .scalar_subquery()
        )
        rows = self._session.execute(
            select(
                word.entry_id,
                sentence.id,
                sentence.text,
                word.span_start,
                word.span_end,
                word.reading,
                word.pos,
                word.inflection_endings,
                word.inflection_form,
                translation,
            )
            .join(sentence, sentence.id == word.sentence_id)
            .where(
                sentence.user_id == user_id,
                sentence.is_active,
                word.entry_id.in_(wanted),
                word.span_start.is_not(None),
                word.reading.is_not(None),
            )
            .order_by(sentence.id, word.position)
        )
        return [
            GapText(
                entry_id=entry_id,
                sentence_id=sentence_id,
                sentence=text,
                start=start,
                end=end,
                reading=reading,
                pos=pos[0] if pos else None,
                inflection=(
                    None
                    if endings is None
                    else Inflection(endings=tuple(endings), form=form)
                ),
                translation=translated,
            )
            for (
                entry_id,
                sentence_id,
                text,
                start,
                end,
                reading,
                pos,
                endings,
                form,
                translated,
            ) in rows
        ]

    def for_entries(
        self, entry_ids: Iterable[int], user_id: UUID
    ) -> list[PracticeSentence]:
        wanted = list(set(entry_ids))
        if not wanted:
            return []
        return self._find(user_id, PracticeSentenceWordORM.entry_id.in_(wanted))

    def by_versions(
        self, versions: Iterable[tuple[int, int]], user_id: UUID
    ) -> list[PracticeSentence]:
        wanted = set(versions)
        if not wanted:
            return []
        row = func.coalesce(PracticeSentenceORM.edited_id, PracticeSentenceORM.id)
        query = (
            self._select(user_id)
            .where(row.in_({r for r, _ in wanted}))
            .order_by(PracticeSentenceORM.id)
        )
        found = [practice_sentence_to_domain(r) for r in self._session.scalars(query)]
        return [s for s in found if s.version in wanted]

    def copies(self, user_id: UUID) -> list[PracticeSentence]:
        query = (
            self._select(user_id)
            .where(PracticeSentenceORM.source_id.is_not(None))
            .order_by(PracticeSentenceORM.id)
        )
        return [practice_sentence_to_domain(r) for r in self._session.scalars(query)]

    def find(
        self, user_id: UUID, search: SentenceSearch, limit: int, offset: int
    ) -> list[PracticeSentence]:
        query = (
            self._select(user_id)
            .where(*self._filters(search))
            .order_by(PracticeSentenceORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [practice_sentence_to_domain(r) for r in self._session.scalars(query)]

    def count(self, user_id: UUID, search: SentenceSearch) -> int:
        query = select(func.count(PracticeSentenceORM.id)).where(
            PracticeSentenceORM.user_id == user_id, *self._filters(search)
        )
        return self._session.scalar(query) or 0

    def imported_by_text(
        self, texts: Iterable[str], user_id: UUID
    ) -> dict[str, PracticeSentence]:
        wanted = list(dict.fromkeys(texts))
        if not wanted:
            return {}
        query = self._select(user_id).where(
            PracticeSentenceORM.origin == "imported",
            PracticeSentenceORM.text.in_(wanted),
        )
        found: dict[str, PracticeSentence] = {}
        # Oldest first: converted examples may hold the same text twice.
        for row in self._session.scalars(query.order_by(PracticeSentenceORM.id)):
            found.setdefault(row.text, practice_sentence_to_domain(row))
        return found

    def needing_analysis(self, user_id: UUID) -> list[PracticeSentence]:
        return self._find(user_id, _TO_ANALYZE)

    def users_needing_analysis(self) -> list[UUID]:
        query = (
            select(PracticeSentenceORM.user_id)
            .where(self._has_word(_TO_ANALYZE))
            .distinct()
            .order_by(PracticeSentenceORM.user_id)
        )
        return list(self._session.scalars(query))

    def add(self, sentence: PracticeSentence) -> PracticeSentence:
        row = practice_sentence_to_db(sentence)
        self._session.add(row)
        self._session.flush()
        return practice_sentence_to_domain(row)

    def update(self, sentence: PracticeSentence) -> PracticeSentence:
        """Replace the stored sentence: words with an id are updated, those
        without one inserted, and stored words missing from it deleted."""
        self._require_row(sentence)
        row = self._session.merge(practice_sentence_to_db(sentence))
        self._session.flush()
        return practice_sentence_to_domain(row)

    def delete(self, sentence: PracticeSentence) -> None:
        self._session.delete(self._require_row(sentence))
        self._session.flush()

    def _require_row(self, sentence: PracticeSentence) -> PracticeSentenceORM:
        stored = (
            self._session.get(PracticeSentenceORM, sentence.id) if sentence.id else None
        )
        if stored is None or stored.user_id != sentence.user_id:
            raise EntityNotFoundError(f"sentence {sentence.id} not found")
        return stored

    def _find(self, user_id: UUID, word: ColumnElement[bool]) -> list[PracticeSentence]:
        query = (
            self._select(user_id)
            .where(self._has_word(word))
            .order_by(PracticeSentenceORM.id)
        )
        return [practice_sentence_to_domain(r) for r in self._session.scalars(query)]

    def _filters(self, search: SentenceSearch) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        text = (search.text or "").strip().lower()
        if text:
            in_translation = exists().where(
                PracticeSentenceTranslationORM.sentence_id == PracticeSentenceORM.id,
                func.lower(PracticeSentenceTranslationORM.text).contains(
                    text, autoescape=True
                ),
            )
            filters.append(
                or_(
                    PracticeSentenceORM.text.contains(text, autoescape=True),
                    in_translation,
                )
            )
        if search.entry_id is not None:
            filters.append(
                self._has_word(PracticeSentenceWordORM.entry_id == search.entry_id)
            )
        if search.linked is not None:
            linked = self._has_word(PracticeSentenceWordORM.entry_id.is_not(None))
            filters.append(linked if search.linked else ~linked)
        if search.active is not None:
            filters.append(PracticeSentenceORM.is_active.is_(search.active))
        return filters

    @staticmethod
    def _has_word(word: ColumnElement[bool]) -> ColumnElement[bool]:
        return exists().where(
            PracticeSentenceWordORM.sentence_id == PracticeSentenceORM.id, word
        )

    @staticmethod
    def _select(user_id: UUID) -> Select[PracticeSentenceORM]:
        return (
            select(PracticeSentenceORM)
            .options(*_LOAD)
            .where(PracticeSentenceORM.user_id == user_id)
        )
