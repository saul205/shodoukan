"""Use cases on the sentences of the user's library."""

from dataclasses import dataclass
from uuid import UUID

from ...domain.entities import PracticeSentence
from ...domain.gateways import Morpheme, MorphologyGateway
from ...domain.repositories import PracticeEntryRepository, PracticeSentenceRepository
from ...domain.services import analyze_gap, find_gap, span_morphemes

# Study texts are read for the forms only; the meanings' language is moot.
_ANY_LANG = "eng"


@dataclass
class SentenceAnalysis:
    """What `AnalyzeSentences` did."""

    users: int = 0
    sentences: int = 0
    # Gaps analyzed; linked words that got a gap; those still without one.
    analyzed: int = 0
    marked: int = 0
    unmarked: int = 0


class AnalyzeSentences:
    """Complete the sentences' words with the analyzer, for every user.

    A gap not analyzed yet gets its lemma, reading in context, part of speech
    and inflection; a word linked to a library word but without a span gets
    one where that word is in the sentence, inflected or not (引いた for 引く),
    and is analyzed. A linked word that isn't found stays without a span.
    What the user corrected is never overwritten: only words without an
    analysis are analyzed. Safe to run again. Maintenance: run after a
    migration that adds sentences, by `shodoukan_practice.cli`. Doesn't
    commit.
    """

    def __init__(
        self,
        sentences: PracticeSentenceRepository,
        entries: PracticeEntryRepository,
        morphology: MorphologyGateway,
    ) -> None:
        self._sentences = sentences
        self._entries = entries
        self._morphology = morphology

    def execute(self) -> SentenceAnalysis:
        result = SentenceAnalysis()
        for user_id in self._sentences.users_needing_analysis():
            result.users += 1
            self._analyze_user(user_id, result)
        return result

    def _analyze_user(self, user_id: UUID, result: SentenceAnalysis) -> None:
        pending = self._sentences.needing_analysis(user_id)
        entry_ids = {w.entry_id for s in pending for w in s.words if w.entry_id}
        forms = {
            text.id: (*text.spellings, *text.readings)
            for text in self._entries.study_texts(entry_ids, user_id, _ANY_LANG)
        }
        for sentence in pending:
            self._analyze(sentence, forms, result)
            self._sentences.update(sentence)
            result.sentences += 1

    def _analyze(
        self,
        sentence: PracticeSentence,
        forms: dict[int, tuple[str, ...]],
        result: SentenceAnalysis,
    ) -> None:
        morphemes = self._morphology.morphemes(sentence.text)
        for word_id in [w.id for w in sentence.words if w.id is not None]:
            word = next(w for w in sentence.words if w.id == word_id)
            word_forms = forms.get(word.entry_id, ()) if word.entry_id else ()
            if word.start is None and word.entry_id is not None:
                taken = [
                    (w.start, w.end)
                    for w in sentence.words
                    if w.start is not None and w.end is not None
                ]
                gap = find_gap(morphemes, word_forms, taken)
                if gap is None:
                    result.unmarked += 1
                    continue
                sentence.mark_word(word_id, *gap)
                result.marked += 1
                word = next(w for w in sentence.words if w.id == word_id)
            if word.start is None or word.end is None or word.is_analyzed:
                continue
            span = span_morphemes(morphemes, word.start, word.end) or self._alone(
                sentence.text, word.start, word.end
            )
            analysis = analyze_gap(span, word_forms)
            sentence.analyze_word(
                word_id,
                analysis.lemma,
                analysis.reading,
                analysis.pos,
                analysis.inflection,
            )
            result.analyzed += 1

    def _alone(self, text: str, start: int, end: int) -> list[Morpheme]:
        """The gap's morphemes when it cuts one of the sentence's (心地 in
        使い心地): its own text analyzed, at its place."""
        return [
            m._replace(start=m.start + start, end=m.end + start)
            for m in self._morphology.morphemes(text[start:end])
        ]
