"""Use cases on the sentences of the user's library.

Every change that leaves a word with a span and no analysis, or a linked
word without a span, completes it with the analyzer (`complete_words`), so
the API never returns a gap it can't ask.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from ...domain.entities import PracticeEntry, PracticeSentence
from ...domain.exceptions import EntityNotFoundError, SentenceWordError
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


@dataclass(frozen=True)
class WordDraft:
    """A word of a new sentence: where it is and the library word it is."""

    start: int | None
    end: int | None
    entry_id: int | None = None
    sense_id: int | None = None


@dataclass(frozen=True)
class SentenceDraft:
    """A sentence of the user's own, reviewed, to store (`AddSentences`)."""

    text: str
    translation: str | None
    lang: str
    words: Sequence[WordDraft] = field(default_factory=tuple)


def entry_forms(
    entries: PracticeEntryRepository, ids: Iterable[int], user_id: UUID
) -> dict[int, tuple[str, ...]]:
    """Each of the user's entries among `ids` as its enabled spellings and
    readings: what a gap linked to it may be written as."""
    return {
        text.id: (*text.spellings, *text.readings)
        for text in entries.study_texts(set(ids), user_id, _ANY_LANG)
    }


def complete_words(
    sentence: PracticeSentence,
    morphology: MorphologyGateway,
    forms: dict[int, tuple[str, ...]],
    result: SentenceAnalysis | None = None,
) -> None:
    """Analyze the sentence's gaps that aren't, and find the gap of its linked
    words without one (by `forms` of the entries they're linked to).

    What's analyzed already is left as it is: the user may have corrected it.
    """
    result = result if result is not None else SentenceAnalysis()
    morphemes = morphology.morphemes(sentence.text)
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
        span = span_morphemes(morphemes, word.start, word.end) or _alone(
            morphology, sentence.text, word.start, word.end
        )
        analysis = analyze_gap(span, word_forms)
        sentence.analyze_word(
            word_id, analysis.lemma, analysis.reading, analysis.pos, analysis.inflection
        )
        result.analyzed += 1


def _alone(
    morphology: MorphologyGateway, text: str, start: int, end: int
) -> list[Morpheme]:
    """The gap's morphemes when it cuts one of the sentence's (心地 in
    使い心地): its own text analyzed, at its place."""
    return [
        m._replace(start=m.start + start, end=m.end + start)
        for m in morphology.morphemes(text[start:end])
    ]


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
            pending = self._sentences.needing_analysis(user_id)
            forms = entry_forms(
                self._entries,
                {w.entry_id for s in pending for w in s.words if w.entry_id},
                user_id,
            )
            for sentence in pending:
                complete_words(sentence, self._morphology, forms, result)
                self._sentences.update(sentence)
                result.sentences += 1
        return result


class _SentenceCommand:
    """A use case that changes one of the user's sentences. Doesn't commit."""

    def __init__(
        self,
        sentences: PracticeSentenceRepository,
        entries: PracticeEntryRepository,
        morphology: MorphologyGateway,
    ) -> None:
        self._sentences = sentences
        self._entries = entries
        self._morphology = morphology

    def _get(self, user_id: UUID, sentence_id: int) -> PracticeSentence:
        sentence = self._sentences.get(sentence_id, user_id)
        if sentence is None:
            raise EntityNotFoundError(f"sentence {sentence_id} not found")
        return sentence

    def _entry(self, user_id: UUID, entry_id: int, sense_id: int | None) -> None:
        """Check the word (and sense) to link is the user's."""
        entry = self._entries.get(entry_id, user_id)
        _check_sense(entry, entry_id, sense_id)

    def _store(self, sentence: PracticeSentence) -> PracticeSentence:
        """Complete the sentence's words and store it."""
        stored = (
            self._sentences.add(sentence)
            if sentence.id is None
            else self._sentences.update(sentence)
        )
        forms = entry_forms(
            self._entries,
            {w.entry_id for w in stored.words if w.entry_id},
            stored.user_id,
        )
        before = stored.model_copy(deep=True)
        complete_words(stored, self._morphology, forms)
        return self._sentences.update(stored) if stored != before else stored


class AddSentence(_SentenceCommand):
    """Add a sentence of the user's own, linked to one of their words if
    `entry_id` is given (the gap is found where that word is, inflected or
    not; if it isn't there, the word is linked without a gap)."""

    def execute(
        self,
        user_id: UUID,
        text: str,
        translation: str | None,
        lang: str,
        entry_id: int | None = None,
        sense_id: int | None = None,
    ) -> PracticeSentence:
        sentence = PracticeSentence.create_own(user_id, text, translation, lang)
        if entry_id is not None:
            self._entry(user_id, entry_id, sense_id)
            sentence.add_word(None, None, entry_id=entry_id, sense_id=sense_id)
        return self._store(sentence)


class AddSentences(_SentenceCommand):
    """Store several reviewed sentences of the user's own at once (a bulk
    add), each with its words. Every linked word must be the user's, or
    nothing is stored (`EntityNotFoundError`)."""

    def execute(
        self, user_id: UUID, drafts: Sequence[SentenceDraft]
    ) -> list[PracticeSentence]:
        links = {
            (w.entry_id, w.sense_id)
            for d in drafts
            for w in d.words
            if w.entry_id is not None
        }
        entries = {
            e.id: e for e in self._entries.get_many({e for e, _ in links}, user_id)
        }
        for entry_id, sense_id in links:
            _check_sense(entries.get(entry_id), entry_id or 0, sense_id)
        sentences = []
        for draft in drafts:
            sentence = PracticeSentence.create_own(
                user_id, draft.text, draft.translation, draft.lang
            )
            for word in draft.words:
                sentence.add_word(
                    word.start,
                    word.end,
                    entry_id=word.entry_id,
                    sense_id=word.sense_id,
                )
            sentences.append(self._store(sentence))
        return sentences


class RewriteSentence(_SentenceCommand):
    """Rewrite one of the user's own sentences (`PracticeSentence.rewrite`)."""

    def execute(
        self,
        user_id: UUID,
        sentence_id: int,
        text: str,
        translation: str | None,
        lang: str,
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        sentence.rewrite(text, translation, lang)
        return self._store(sentence)


class SetSentenceActive(_SentenceCommand):
    def execute(
        self, user_id: UUID, sentence_id: int, active: bool
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        if active:
            sentence.activate()
        else:
            sentence.deactivate()
        return self._sentences.update(sentence)


class SetSentenceNotes(_SentenceCommand):
    def execute(
        self, user_id: UUID, sentence_id: int, notes: str | None
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        sentence.set_notes(notes)
        return self._sentences.update(sentence)


class RemoveSentence(_SentenceCommand):
    """Remove a sentence from the library. A copy of someone's is remembered
    on the words it was linked to, so their source doesn't bring it back."""

    def execute(self, user_id: UUID, sentence_id: int) -> None:
        sentence = self._get(user_id, sentence_id)
        linked = {w.entry_id for w in sentence.words if w.entry_id is not None}
        for entry in self._entries.get_many(linked, user_id):
            if entry.dismiss_example(sentence):
                self._entries.update(entry)
        self._sentences.delete(sentence)


class AddSentenceWord(_SentenceCommand):
    """Mark a word of the sentence (`start`/`end`), linked to one of the
    user's words or not; without a span, `entry_id` is required (the gap is
    then found where that word is)."""

    def execute(
        self,
        user_id: UUID,
        sentence_id: int,
        start: int | None,
        end: int | None,
        entry_id: int | None = None,
        sense_id: int | None = None,
    ) -> PracticeSentence:
        if start is None and entry_id is None:
            raise SentenceWordError("a word without a span must be linked")
        sentence = self._get(user_id, sentence_id)
        if entry_id is not None:
            self._entry(user_id, entry_id, sense_id)
        sentence.add_word(start, end, entry_id=entry_id, sense_id=sense_id)
        return self._store(sentence)


class MarkSentenceWord(_SentenceCommand):
    """Move a word's span; it's analyzed again."""

    def execute(
        self, user_id: UUID, sentence_id: int, word_id: int, start: int, end: int
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        sentence.mark_word(word_id, start, end)
        return self._store(sentence)


class LinkSentenceWord(_SentenceCommand):
    """Link a word to one of the user's words (and sense), or unlink it
    (`entry_id=None`)."""

    def execute(
        self,
        user_id: UUID,
        sentence_id: int,
        word_id: int,
        entry_id: int | None,
        sense_id: int | None = None,
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        if entry_id is None:
            sentence.unlink_word(word_id)
        else:
            self._entry(user_id, entry_id, sense_id)
            sentence.link_word(word_id, entry_id, sense_id)
        return self._store(sentence)


class CorrectSentenceWord(_SentenceCommand):
    """The user's own lemma and reading for a word (the analyzer's can be
    wrong)."""

    def execute(
        self,
        user_id: UUID,
        sentence_id: int,
        word_id: int,
        lemma: str,
        reading: str,
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        sentence.correct_word(word_id, lemma, reading)
        return self._sentences.update(sentence)


class RemoveSentenceWord(_SentenceCommand):
    def execute(
        self, user_id: UUID, sentence_id: int, word_id: int
    ) -> PracticeSentence:
        sentence = self._get(user_id, sentence_id)
        sentence.remove_word(word_id)
        return self._sentences.update(sentence)


def _check_sense(
    entry: PracticeEntry | None, entry_id: int, sense_id: int | None
) -> None:
    if entry is None:
        raise EntityNotFoundError(f"entry {entry_id} not found")
    if sense_id is not None and all(s.id != sense_id for s in entry.senses):
        raise EntityNotFoundError(f"sense {sense_id} not found")
