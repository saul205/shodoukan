"""Grade a word written by hand, a character per cell.

Each cell is graded on its own against its character, with
`handwriting_grading_service` (the same rules as a kanji, kana included); an
empty cell is that character missing. The word's verdict is its worst cell's,
since a word with one character wrong is wrong, and its score the cells'
average. Like a kanji, the word is graded against each word the question
accepts and the closest one counts.
"""

from collections.abc import Sequence

from ..entities import (
    CellsAnswer,
    HandwritingGrade,
    ReferenceKanji,
    ReferenceWord,
    StrokeFeedback,
    StrokesAnswer,
    Verdict,
    WordGrade,
)
from .handwriting_grading_service import grade_drawing

_VERDICT_RANK: dict[Verdict, int] = {"correct": 2, "close": 1, "wrong": 0}


def grade_word(answer: CellsAnswer, words: Sequence[ReferenceWord]) -> WordGrade:
    """The grade against the closest of `words` (at least one; the first is the
    word asked) with as many characters as cells; there's always the first."""
    if not words:
        raise ValueError("a word is graded against at least one word")
    candidates = [
        w
        for i, w in enumerate(words)
        if i == 0 or len(w.characters) == len(answer.cells)
    ]
    if len(candidates[0].characters) != len(answer.cells):
        raise ValueError("a word is written in as many cells as it has characters")
    grades = [_grade_one(answer, word) for word in candidates]
    return max(grades, key=lambda g: (_VERDICT_RANK[g.verdict], g.score))


def _grade_one(answer: CellsAnswer, word: ReferenceWord) -> WordGrade:
    cells = tuple(
        _grade_cell(cell, reference)
        for cell, reference in zip(answer.cells, word.characters, strict=True)
    )
    return WordGrade(
        score=round(sum(c.score for c in cells) / len(cells)),
        verdict=min((c.verdict for c in cells), key=_VERDICT_RANK.__getitem__),
        matched=word.text,
        cells=cells,
    )


def _grade_cell(
    cell: Sequence[Sequence[tuple[float, float]]], reference: ReferenceKanji
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
    return grade_drawing(drawing, [reference])
