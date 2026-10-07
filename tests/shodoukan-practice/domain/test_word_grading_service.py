import pytest
from factories import make_reference, make_reference_word

from shodoukan_practice.domain.entities import (
    CellsAnswer,
    ReferenceKanji,
    ReferenceWord,
)
from shodoukan_practice.domain.services import grade_word


def _drawn(reference: ReferenceKanji) -> tuple[tuple[tuple[float, float], ...], ...]:
    """A character drawn exactly as its reference."""
    return tuple(stroke.points for stroke in reference.strokes)


VERTICAL = ReferenceKanji.model_validate(
    {
        "literal": "丨",
        "strokes": [
            {
                "path": "M54,10c0,30,0,60,0,90",
                "label": None,
                "points": [(54.0, 10.0 + 8 * i) for i in range(11)],
            }
        ],
    }
)


def test_a_word_written_as_its_references_is_correct() -> None:
    word = make_reference_word("一一")
    answer = CellsAnswer(cells=tuple(_drawn(c) for c in word.characters))

    grade = grade_word(answer, [word])

    assert (grade.verdict, grade.matched) == ("correct", "一一")
    assert len(grade.cells) == 2
    assert grade.score == round(sum(c.score for c in grade.cells) / 2)


def test_the_worst_cell_decides_and_an_empty_one_is_missing() -> None:
    word = make_reference_word("一一")
    answer = CellsAnswer(cells=(_drawn(word.characters[0]), ()))

    grade = grade_word(answer, [word])

    assert grade.verdict == "wrong"
    assert grade.cells[0].verdict == "correct"
    empty = grade.cells[1]
    assert (empty.score, empty.verdict, empty.matched) == (0, "wrong", "一")
    assert [s.status for s in empty.strokes] == ["missing"]


def test_the_closest_accepted_word_of_as_many_characters_grades_it() -> None:
    asked = make_reference_word("一一")
    other = ReferenceWord(text="一丨", characters=(make_reference("一"), VERTICAL))
    longer = make_reference_word("一一一")
    answer = CellsAnswer(cells=(_drawn(make_reference()), _drawn(VERTICAL)))

    grade = grade_word(answer, [asked, longer, other])

    assert (grade.verdict, grade.matched) == ("correct", "一丨")


def test_needs_a_word_as_long_as_the_cells() -> None:
    with pytest.raises(ValueError, match="at least one"):
        grade_word(CellsAnswer(cells=(_drawn(make_reference()),)), [])
    with pytest.raises(ValueError, match="as many cells"):
        grade_word(
            CellsAnswer(cells=(_drawn(make_reference()),)),
            [make_reference_word("一一")],
        )
