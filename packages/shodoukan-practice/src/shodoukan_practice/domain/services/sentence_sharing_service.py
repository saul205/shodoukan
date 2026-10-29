"""A word's sentences in the portable form of a collection, and back.

They travel as the word's `examples`, under the sense they're linked to, as
examples did before sentences, so older files and publications still import
and their versions still match. Each carries where the word is in it
(`SharedExample.word`).

- `with_examples`: what an export carries of a word's sentences.
- `merge_examples`: what importing a word brings. A dictionary sentence is
  only located (the user's with the same text) and linked; its flag is taken
  only when the word was created by this import. Someone's own sentence is
  copied unless the user has that version already (then it's linked to the
  word too, and remembers one more collection that brings it), or removed
  it before (`example:<identity>` in the word's `dismissed_parts`).
- `preview_sentences`: a shared word's examples as the sentences importing it
  would give, for a preview (nothing stored, no ids, not linked).
- `prune_examples`: an update from a source lets go of the copies it brought,
  untouched, that its new version no longer has; one nothing brings any more
  goes.
"""

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from uuid import UUID

from ..entities import (
    JAPANESE,
    Inflection,
    PracticeEntry,
    PracticeSentence,
    SentenceTranslation,
    SentenceWord,
    SharedEntry,
    SharedEntryCollection,
    SharedExample,
    SharedSentence,
    SharedSentenceWord,
    SourceRef,
)
from ..entities.nested_item_lookup import dismissed_of


@dataclass
class SentenceMerge:
    """What importing a word's examples does to the user's sentences."""

    created: list[PracticeSentence] = field(default_factory=list)
    changed: list[PracticeSentence] = field(default_factory=list)

    def touch(self, sentence: PracticeSentence) -> None:
        if sentence.id is not None and all(s is not sentence for s in self.changed):
            self.changed.append(sentence)


def with_examples(
    shared: SharedEntry, entry: PracticeEntry, sentences: Sequence[PracticeSentence]
) -> SharedEntry:
    """`shared` (the word's `to_shared()`) with its sentences as examples,
    each under the sense its word is linked to (the first when none)."""
    if not shared.senses or entry.id is None:
        return shared
    positions = {sense.id: i for i, sense in enumerate(entry.senses)}
    examples: list[list[SharedExample]] = [[] for _ in shared.senses]
    for sentence in sentences:
        for word in sentence.words_of(entry.id):
            position = positions.get(word.sense_id, 0)
            examples[min(position, len(examples) - 1)].append(
                _shared_example(sentence, word)
            )
    return shared.model_copy(
        update={
            "senses": [
                sense.model_copy(update={"examples": examples[i]})
                for i, sense in enumerate(shared.senses)
            ]
        }
    )


def merge_examples(
    entry: PracticeEntry,
    shared: SharedEntry,
    candidates: list[PracticeSentence],
    *,
    created: bool,
    source: SourceRef | None,
) -> SentenceMerge:
    """What the shared word's examples bring into the user's sentences.

    `entry` is the user's stored word; `candidates`, the user's sentences
    that may be the shared ones (those of the word, the dictionary ones with
    the same texts, the copies with the same versions). New copies are added
    to `candidates` too, so a sentence that comes twice (two words, two
    senses) is copied once.
    """
    result = SentenceMerge()
    if entry.id is None:
        raise ValueError("the word must be stored first")
    dismissed = dismissed_of(entry.dismissed_parts, "example")
    for sense_id, part in zip(
        entry.shared_sense_ids(shared), shared.senses, strict=True
    ):
        for example in part.examples:
            text = _japanese(example)
            if not text:
                continue
            if example.origin == "imported":
                _merge_imported(
                    entry, sense_id, example, text, candidates, created, result
                )
            elif example.identity not in dismissed:
                _merge_copy(entry, sense_id, example, text, candidates, source, result)
    return result


def preview_sentences(shared: SharedEntry, user_id: UUID) -> list[PracticeSentence]:
    """The shared word's examples as sentences, each once, with the word's
    gap and analysis: what a preview shows. Nothing is stored, so they have
    no ids and aren't linked to a library word."""
    sentences: dict[str, PracticeSentence] = {}
    for part in shared.senses:
        for example in part.examples:
            text = _japanese(example)
            if not text or text in sentences:
                continue
            sentence = PracticeSentence(
                id=None,
                user_id=user_id,
                text=text,
                translations=_translations(example),
                is_active=example.enabled,
                origin=example.origin,
            )
            _link_preview(sentence, example.word)
            sentences[text] = sentence
    return list(sentences.values())


def _link_preview(
    sentence: PracticeSentence, shared: SharedSentenceWord | None
) -> None:
    if shared is None or shared.start is None or shared.end is None:
        return
    # Outside the sentence: shown without its gap.
    with suppress(ValueError):
        sentence.add_word(shared.start, shared.end, analysis=_analysis(shared))


def prune_examples(
    sentences: Sequence[PracticeSentence],
    shared: SharedEntryCollection,
    source: int,
) -> tuple[list[PracticeSentence], list[PracticeSentence]]:
    """`(changed, removed)`: the copies `source` brought, untouched, that its
    new version (`shared`) no longer has let go of it; those nothing brings
    any more are removed."""
    kept = {
        example.version
        for item in shared.items
        for sense in item.senses
        for example in sense.examples
        if example.origin == "added"
    }
    changed: list[PracticeSentence] = []
    removed: list[PracticeSentence] = []
    for sentence in sentences:
        if not sentence.untouched_from(source) or sentence.version in kept:
            continue
        (removed if sentence.let_go(source) else changed).append(sentence)
    return changed, removed


def _merge_imported(
    entry: PracticeEntry,
    sense_id: int | None,
    example: SharedExample,
    text: str,
    candidates: list[PracticeSentence],
    created: bool,
    result: SentenceMerge,
) -> None:
    assert entry.id is not None
    same = [s for s in candidates if s.origin == "imported" and s.text == text]
    target = next((s for s in same if s.words_of(entry.id)), None) or next(
        iter(same), None
    )
    if target is None:
        return  # dictionary sentences come from the dictionary, not the file
    if not target.words_of(entry.id):
        _link(target, example.word, entry.id, sense_id)
        result.touch(target)
    if created and target.is_active != example.enabled:
        if example.enabled:
            target.activate()
        else:
            target.deactivate()
        result.touch(target)


def _merge_copy(
    entry: PracticeEntry,
    sense_id: int | None,
    example: SharedExample,
    text: str,
    candidates: list[PracticeSentence],
    source: SourceRef | None,
    result: SentenceMerge,
) -> None:
    assert entry.id is not None
    target = next(
        (
            s
            for s in candidates
            if example.version is not None and s.version == example.version
        ),
        None,
    )
    if target is None:
        copy = PracticeSentence.copied(
            entry.user_id,
            text,
            _translations(example),
            is_active=example.enabled,
            original_id=example.identity,
            source_id=example.id,
            edited_id=example.edited_id,
            revision=example.revision,
            source=source,
        )
        _link(copy, example.word, entry.id, sense_id)
        candidates.append(copy)
        result.created.append(copy)
        return
    changed = False
    if not target.words_of(entry.id):
        _link(target, example.word, entry.id, sense_id)
        changed = True
    if source is not None:
        changed |= target.brought_by(source)
    if changed:
        result.touch(target)


def _link(
    sentence: PracticeSentence,
    shared: SharedSentenceWord | None,
    entry_id: int,
    sense_id: int | None,
) -> None:
    """Link the word at its shared gap when it fits, with the owner's
    analysis; otherwise without a gap (the analyzer finds it)."""
    if shared is not None and shared.start is not None and shared.end is not None:
        try:
            sentence.add_word(
                shared.start,
                shared.end,
                entry_id=entry_id,
                sense_id=sense_id,
                analysis=_analysis(shared),
            )
            return
        except ValueError:
            pass  # over another word, or outside the sentence
    sentence.add_word(None, None, entry_id=entry_id, sense_id=sense_id)


def _analysis(
    shared: SharedSentenceWord,
) -> tuple[str, str, list[str], Inflection | None] | None:
    """The owner's analysis of a shared gap, if it has one."""
    if not shared.lemma or not shared.reading:
        return None
    inflection = (
        None
        if shared.endings is None
        else Inflection(endings=tuple(shared.endings), form=shared.form)
    )
    return shared.lemma, shared.reading, list(shared.pos), inflection


def _shared_example(sentence: PracticeSentence, word: SentenceWord) -> SharedExample:
    return SharedExample(
        origin=sentence.origin,
        id=sentence.id,
        original_id=sentence.identity,
        edited_id=sentence.edited_id if sentence.edited_id is not None else sentence.id,
        revision=sentence.revision,
        enabled=sentence.is_active,
        sentences=[
            SharedSentence(lang=JAPANESE, text=sentence.text),
            *(SharedSentence(lang=t.lang, text=t.text) for t in sentence.translations),
        ],
        word=SharedSentenceWord(
            start=word.start,
            end=word.end,
            lemma=word.lemma,
            reading=word.reading,
            pos=list(word.pos),
            endings=None if word.inflection is None else list(word.inflection.endings),
            form=None if word.inflection is None else word.inflection.form,
        ),
    )


def _japanese(example: SharedExample) -> str:
    return next((s.text.strip() for s in example.sentences if s.lang == JAPANESE), "")


def _translations(example: SharedExample) -> list[SentenceTranslation]:
    return [
        SentenceTranslation(lang=s.lang, text=s.text.strip())
        for s in example.sentences
        if s.lang != JAPANESE and s.text.strip()
    ]
