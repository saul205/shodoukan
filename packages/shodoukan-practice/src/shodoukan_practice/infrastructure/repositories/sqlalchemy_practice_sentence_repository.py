from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, exists, or_, select
from sqlalchemy.orm import Session, selectinload

from ...domain.entities import PracticeSentence
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import PracticeSentenceRepository
from ..db.mappers import practice_sentence_to_db, practice_sentence_to_domain
from ..db.orm import PracticeSentenceORM, PracticeSentenceWordORM

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
