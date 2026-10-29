"""Read use cases on the sentences of the user's library."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from ...domain.entities import PracticeSentence
from ...domain.exceptions import EntityNotFoundError
from ...domain.gateways import Morpheme, MorphologyGateway
from ...domain.repositories import (
    PracticeEntryRepository,
    PracticeSentenceRepository,
    SentenceSearch,
)
from ...domain.services import WordProposal, candidate_forms, propose_words

# A bulk add analyzes at most this many sentences per request.
MAX_ANALYZED_SENTENCES = 200


@dataclass(frozen=True)
class SentencePage:
    items: list[PracticeSentence]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class SentenceProposal:
    """A sentence to add, analyzed: its morphemes (to pick words from) and
    the library words it uses."""

    text: str
    morphemes: list[Morpheme]
    words: list[WordProposal]


class GetSentence:
    def __init__(self, sentences: PracticeSentenceRepository) -> None:
        self._sentences = sentences

    def execute(self, user_id: UUID, sentence_id: int) -> PracticeSentence:
        sentence = self._sentences.get(sentence_id, user_id)
        if sentence is None:
            raise EntityNotFoundError(f"sentence {sentence_id} not found")
        return sentence


class SearchSentences:
    """A page of the user's sentences matching `search`, newest first."""

    def __init__(self, sentences: PracticeSentenceRepository) -> None:
        self._sentences = sentences

    def execute(
        self, user_id: UUID, search: SentenceSearch, limit: int, offset: int
    ) -> SentencePage:
        return SentencePage(
            items=self._sentences.find(user_id, search, limit, offset),
            total=self._sentences.count(user_id, search),
            limit=limit,
            offset=offset,
        )


class ListSentencesOfEntry:
    """The sentences of one of the user's words, oldest first."""

    def __init__(
        self,
        sentences: PracticeSentenceRepository,
        entries: PracticeEntryRepository,
    ) -> None:
        self._sentences = sentences
        self._entries = entries

    def execute(self, user_id: UUID, entry_id: int) -> list[PracticeSentence]:
        if self._entries.get(entry_id, user_id) is None:
            raise EntityNotFoundError(f"entry {entry_id} not found")
        return self._sentences.for_entry(entry_id, user_id)


class AnalyzeSentenceTexts:
    """Analyze sentences before adding them: their morphemes, and the user's
    library words each one uses (`propose_words`). Nothing is stored. At most
    `MAX_ANALYZED_SENTENCES` texts; blank ones are skipped."""

    def __init__(
        self,
        entries: PracticeEntryRepository,
        morphology: MorphologyGateway,
    ) -> None:
        self._entries = entries
        self._morphology = morphology

    def execute(self, user_id: UUID, texts: Sequence[str]) -> list[SentenceProposal]:
        if len(texts) > MAX_ANALYZED_SENTENCES:
            raise ValueError(
                f"at most {MAX_ANALYZED_SENTENCES} sentences can be analyzed at once"
            )
        analyzed = [
            (text, self._morphology.morphemes(text))
            for text in (t.strip() for t in texts)
            if text
        ]
        library = self._entries.ids_by_form(
            set().union(*(candidate_forms(m) for _, m in analyzed)), user_id
        )
        return [
            SentenceProposal(
                text=text, morphemes=morphemes, words=propose_words(morphemes, library)
            )
            for text, morphemes in analyzed
        ]
