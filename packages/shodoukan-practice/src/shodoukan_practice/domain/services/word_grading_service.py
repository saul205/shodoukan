"""Grade a word written by hand, a character per cell.

Each cell is graded on its own against its character, with
`handwriting_grading_service` (the same rules as a kanji); an empty cell is
that character missing. A kana cell is also told apart from the other kana
(`grade_kana`, given the `alphabet` of kana references): written as another
kana it's wrong and names it, while a slip in the right kana is at worst
close. The word's verdict is its worst cell's, since a word with a character
wrong is another word (たべる with ろ for る), and its score the cells'
average. Like a kanji, the word is graded against each word the question
accepts and the closest one counts.

**Small kana.** Grading normalizes each drawing by its own box, so ゃ and や
are the same shape. They're told apart by size, against the word's other
kana (きゃ: ゃ is smaller than き; kanji are left out, as they're drawn bigger
and some are flat, like 一), as KanjiVG draws them (a small kana is about
`SMALL_RATIO` of its big twin): a cell closer in size to its twin is that
twin (wrong), one in between (`SIZE_BAND`) is close. With no other big kana
to compare with, it's measured against its own reference, and only a size
clearly the twin's (`ALONE_MARGIN`) counts, since how big people write varies.
"""

from collections.abc import Mapping, Sequence
from statistics import median

from ..entities import (
    CellsAnswer,
    HandwritingGrade,
    Point,
    ReferenceKanji,
    ReferenceWord,
    StrokeFeedback,
    StrokesAnswer,
    Verdict,
    WordGrade,
)
from .handwriting_grading_service import grade_drawing, grade_kana

_VERDICT_RANK: dict[Verdict, int] = {"correct": 2, "close": 1, "wrong": 0}

# Every kana, hiragana and katakana (with ー), as KanjiVG draws them.
KANA = frozenset(
    [chr(c) for c in range(ord("ぁ"), ord("ゖ") + 1)]
    + [chr(c) for c in range(ord("ァ"), ord("ヺ") + 1)]
    + ["ー"]
)
# Small kana and their big twins, both ways.
_SMALL = "ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ"
_BIG = "あいうえおつやゆよわかけアイウエオツヤユヨワカケ"
SMALL_TWINS: dict[str, str] = dict(zip(_SMALL, _BIG, strict=True))
TWINS: dict[str, str] = {**SMALL_TWINS, **{b: s for s, b in SMALL_TWINS.items()}}
# Kana drawn alike in both scripts: never told apart by shape.
_SAME_SHAPE = [frozenset("へヘ"), frozenset("べベ"), frozenset("ぺペ")]

# A small kana's size against its big twin's, as KanjiVG draws them (ゃ is 60
# to や's 76); the size between them (their geometric mean), relative to the
# rest of the word, splits small from big. Within `SIZE_BAND` of it (as a
# share), it can't be told.
SMALL_RATIO = 0.78
SIZE_BAND = 0.05
# Alone, a cell is its twin only past this share of the way to the twin's size.
ALONE_MARGIN = 0.9


def grade_word(
    answer: CellsAnswer,
    words: Sequence[ReferenceWord],
    alphabet: Mapping[str, ReferenceKanji] | None = None,
) -> WordGrade:
    """The grade against the closest of `words` (at least one; the first is the
    word asked) with as many characters as cells; there's always the first.
    `alphabet` holds the kana's references, to tell kana apart; without it,
    kana are graded like kanji."""
    if not words:
        raise ValueError("a word is graded against at least one word")
    candidates = [
        w
        for i, w in enumerate(words)
        if i == 0 or len(w.characters) == len(answer.cells)
    ]
    if len(candidates[0].characters) != len(answer.cells):
        raise ValueError("a word is written in as many cells as it has characters")
    grades = [_grade_one(answer, word, alphabet or {}) for word in candidates]
    return max(grades, key=lambda g: (_VERDICT_RANK[g.verdict], g.score))


def _grade_one(
    answer: CellsAnswer, word: ReferenceWord, alphabet: Mapping[str, ReferenceKanji]
) -> WordGrade:
    cells = [
        _grade_cell(cell, reference, alphabet)
        for cell, reference in zip(answer.cells, word.characters, strict=True)
    ]
    cells = _check_sizes(answer.cells, word.characters, cells)
    return WordGrade(
        score=round(sum(c.score for c in cells) / len(cells)),
        verdict=min((c.verdict for c in cells), key=_VERDICT_RANK.__getitem__),
        matched=word.text,
        cells=tuple(cells),
    )


def _grade_cell(
    cell: Sequence[Sequence[Point]],
    reference: ReferenceKanji,
    alphabet: Mapping[str, ReferenceKanji],
) -> HandwritingGrade:
    if not cell:
        return HandwritingGrade(
            score=0,
            verdict="wrong",
            matched=reference.literal,
            strokes=tuple(
                StrokeFeedback(drawn=None, reference=i, status="missing")
                for i in range(len(reference.strokes))
            ),
        )
    drawing = StrokesAnswer(strokes=tuple(tuple(stroke) for stroke in cell))
    if reference.literal in KANA and alphabet:
        return grade_kana(drawing, reference, _rivals(reference.literal, alphabet))
    return grade_drawing(drawing, [reference])


def _rivals(
    literal: str, alphabet: Mapping[str, ReferenceKanji]
) -> list[ReferenceKanji]:
    """The kana a drawing of `literal` could be taken for: all but itself, those
    drawn alike in the other script, and its small or big twin (told apart by
    size instead)."""
    alike = next((group for group in _SAME_SHAPE if literal in group), frozenset())
    excluded = {literal, TWINS.get(literal, literal), *alike}
    return [ref for char, ref in alphabet.items() if char not in excluded]


def _check_sizes(
    cells: Sequence[Sequence[Sequence[Point]]],
    characters: Sequence[ReferenceKanji],
    grades: list[HandwritingGrade],
) -> list[HandwritingGrade]:
    """Small and big kana told apart by size (see the module docs)."""
    sizes = [
        _size([p for stroke in cell for p in stroke]) if cell else 0.0 for cell in cells
    ]
    checked = list(grades)
    for i, reference in enumerate(characters):
        twin = TWINS.get(reference.literal)
        if twin is None or not cells[i] or grades[i].verdict == "wrong":
            continue
        neighbours = [
            k
            for k, other in enumerate(characters)
            if k != i
            and cells[k]
            and other.literal in KANA
            and other.literal not in SMALL_TWINS
        ]
        looks_twin, unclear = _size_verdict(
            sizes[i],
            [sizes[k] for k in neighbours],
            reference,
            [
                _size([p for s in characters[k].strokes for p in s.points])
                for k in neighbours
            ],
            reference.literal in SMALL_TWINS,
        )
        if looks_twin:
            checked[i] = grades[i].model_copy(
                update={"verdict": "wrong", "looks_like": twin}
            )
        elif unclear and grades[i].verdict == "correct":
            checked[i] = grades[i].model_copy(update={"verdict": "close"})
    return checked


def _size_verdict(
    size: float,
    others: list[float],
    reference: ReferenceKanji,
    others_reference: list[float],
    small: bool,
) -> tuple[bool, bool]:
    """Whether a cell of `size` looks like its twin, and whether it's unclear."""
    own = _size([p for stroke in reference.strokes for p in stroke.points])
    if others:
        # The size it should have against the word's other big kana, as their
        # references are drawn (い is narrower than た), and its twin's.
        expected = own / median(others_reference)
        ratio = size / median(others)
    else:
        # Alone: against its own reference, and only a clear twin counts.
        expected, ratio = 1.0, size / own
    twin = expected / SMALL_RATIO if small else expected * SMALL_RATIO
    split = (expected * twin) ** 0.5
    if not others:
        past = expected + ALONE_MARGIN * (twin - expected)
        return (ratio > past if small else ratio < past), False
    unclear = abs(ratio / split - 1) <= SIZE_BAND
    looks_twin = not unclear and (ratio > split if small else ratio < split)
    return looks_twin, unclear


def _size(points: Sequence[Point]) -> float:
    """The longer side of the points' bounding box, in canvas units."""
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
