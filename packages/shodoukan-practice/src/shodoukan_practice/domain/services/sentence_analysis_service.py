"""What a sentence's words are, from its morphemes.

`analyze_gap` gives what a sentence word stores about a gap (lemma, reading
in context, part of speech, inflection); `find_gap` finds where a linked word
is when it has no span yet (an inflected own sentence: 引いた for 引く);
`propose_words` finds the library words a new sentence uses
(`candidate_forms` says which forms to look up).
`forms` are the linked word's enabled spellings and readings, so the lemma
stored is the word's own form when one of its dictionary forms matches.

See docs/practice/proposals/sentences.md.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from ..entities import Inflection
from ..gateways import Morpheme
from .inflection_service import (
    gap_dictionary_forms,
    gap_head,
    gap_inflection,
    is_content_word,
)
from .study_field_service import kana_key

# Morphemes an expression of the dictionary may span (持っ + て + いく).
_LONGEST_EXPRESSION = 4
_KATAKANA = frozenset(chr(c) for c in range(ord("ァ"), ord("ヺ") + 1)) | {"ー"}


@dataclass(frozen=True)
class WordProposal:
    """A word of a new sentence that is in the library."""

    start: int
    end: int
    # The library form it was found by (引く for 引いた, 持っていく).
    form: str
    entry_ids: tuple[int, ...]
    # Found by a spelling with kanji; a kana-only match (はし) is a guess.
    certain: bool


@dataclass(frozen=True)
class GapAnalysis:
    lemma: str
    reading: str
    pos: tuple[str, ...]
    inflection: Inflection | None


def span_morphemes(
    morphemes: Sequence[Morpheme], start: int, end: int
) -> list[Morpheme] | None:
    """The morphemes exactly covering `start` to `end`; `None` when the span
    cuts one (心地 inside 使い心地)."""
    inside = [m for m in morphemes if m.start < end and m.end > start]
    if inside and inside[0].start == start and inside[-1].end == end:
        return inside
    return None


def analyze_gap(
    morphemes: Sequence[Morpheme], forms: Collection[str] = ()
) -> GapAnalysis:
    """A gap made of `morphemes` (in order, covering it): its lemma (the
    linked word's form among its dictionary forms, else the best guess), its
    reading in context (hiragana, katakana for a katakana word), its head's
    part of speech and its inflection."""
    if not morphemes:
        raise ValueError("a gap has at least one morpheme")
    candidates = gap_dictionary_forms(morphemes)
    lemma = next((f for f in candidates if _matches(f, forms)), candidates[0])
    head = gap_head(morphemes)
    return GapAnalysis(
        lemma=lemma,
        reading=_reading(morphemes),
        pos=head.pos if head else (),
        inflection=gap_inflection(morphemes),
    )


def find_gap(
    morphemes: Sequence[Morpheme],
    forms: Collection[str],
    taken: Sequence[tuple[int, int]] = (),
) -> tuple[int, int] | None:
    """Where a word with these `forms` is in the sentence: the first content
    morpheme whose lemma is one of them, or that starts an expression which
    is (持って + いっ for 持っていく: the morphemes as written, the last one's
    lemma), with what inflects it (auxiliaries, te-form て / で), clear of
    the `taken` spans; `None` if it isn't there."""
    for i, morpheme in enumerate(morphemes):
        if not is_content_word(morpheme):
            continue
        last = _expression_end(morphemes, i, forms)
        if last is None:
            continue
        while last + 1 < len(morphemes) and _inflects(morphemes[last + 1]):
            last += 1
        start, end = morpheme.start, morphemes[last].end
        if all(end <= s or start >= e for s, e in taken):
            return start, end
    return None


def candidate_forms(morphemes: Sequence[Morpheme]) -> set[str]:
    """Every form `propose_words` may look up in the library."""
    forms: set[str] = set()
    for i, morpheme in enumerate(morphemes):
        if is_content_word(morpheme):
            for form, _ in _expressions(morphemes, i):
                forms |= {form, kana_key(form)}
    return forms


def propose_words(
    morphemes: Sequence[Morpheme], library: Mapping[str, Sequence[int]]
) -> list[WordProposal]:
    """The library words a sentence uses, left to right, never overlapping.

    `library` maps forms to the user's entries that have them (enabled
    spellings and readings). From each content morpheme, the longest
    expression that is a library form wins (日本語 over 日本), with what
    inflects it.
    """
    proposals: list[WordProposal] = []
    i = 0
    while i < len(morphemes):
        best: tuple[int, str, Sequence[int]] | None = None
        if is_content_word(morphemes[i]):
            for form, last in _expressions(morphemes, i):
                ids = library.get(form) or library.get(kana_key(form))
                if ids:
                    best = (last, form, ids)
        if best is None:
            i += 1
            continue
        last, form, ids = best
        while last + 1 < len(morphemes) and _inflects(morphemes[last + 1]):
            last += 1
        proposals.append(
            WordProposal(
                start=morphemes[i].start,
                end=morphemes[last].end,
                form=form,
                entry_ids=tuple(ids),
                certain=any(_is_kanji(char) for char in form),
            )
        )
        i = last + 1
    return proposals


def _expressions(morphemes: Sequence[Morpheme], first: int) -> list[tuple[str, int]]:
    """`(form, last morpheme)` of the words and expressions starting at
    `first`, shortest first: as written, and with the last one's lemma."""
    expressions: list[tuple[str, int]] = []
    written = ""
    for last in range(first, min(first + _LONGEST_EXPRESSION, len(morphemes))):
        expressions.append((written + morphemes[last].lemma, last))
        written += morphemes[last].surface
        expressions.append((written, last))
    return expressions


def _is_kanji(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff" or char in "々〆ヶ"


def _expression_end(
    morphemes: Sequence[Morpheme], first: int, forms: Collection[str]
) -> int | None:
    """The last morpheme of the shortest word or expression starting at
    `first` that is one of `forms`."""
    for form, last in _expressions(morphemes, first):
        if _matches(form, forms):
            return last
    return None


def _matches(text: str, forms: Collection[str]) -> bool:
    return text in forms or kana_key(text) in {kana_key(f) for f in forms}


def _inflects(morpheme: Morpheme) -> bool:
    return morpheme.pos[:1] == ("助動詞",) or (
        morpheme.pos[:2] == ("助詞", "接続助詞") and morpheme.lemma in ("て", "で")
    )


def _reading(morphemes: Sequence[Morpheme]) -> str:
    reading = "".join(m.reading for m in morphemes)
    surface = "".join(m.surface for m in morphemes)
    if all(char in _KATAKANA for char in surface):
        return reading
    return kana_key(reading)
