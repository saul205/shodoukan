import pytest
from factories import (
    hand_drawn,
    kanjivg_reference,
    kanjivg_strokes,
    make_reference,
    make_reference_word,
)

from shodoukan_practice.domain.entities import (
    CellsAnswer,
    ReferenceKanji,
    ReferenceWord,
    WordGrade,
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


# Telling kana apart in a word, on KanjiVG's own strokes (`kanjivg_paths`).

ALPHABET = {k: kanjivg_reference(k) for k in "へべばぱはるろれねきゃやいつった"}


def _word(text: str, written: list[tuple[str, float]]) -> WordGrade:
    """`text` written as `written`: each cell a character at a scale."""
    word = ReferenceWord(text=text, characters=tuple(ALPHABET[c] for c in text))
    cells = tuple(
        hand_drawn(kanjivg_strokes(char), seed=i, scale=scale)
        for i, (char, scale) in enumerate(written)
    )
    return grade_word(CellsAnswer(cells=cells), [word], ALPHABET)


def test_a_word_with_another_kana_is_wrong_and_says_which() -> None:
    grade = _word("たべる", [("た", 0.9), ("べ", 0.9), ("ろ", 0.9)])

    assert grade.verdict == "wrong"
    assert (grade.cells[2].verdict, grade.cells[2].looks_like) == ("wrong", "ろ")
    assert _word("たべる", [("た", 0.9), ("べ", 0.9), ("る", 0.9)]).verdict == "correct"


def test_small_kana_are_told_from_big_ones_by_size_in_the_word() -> None:
    # KanjiVG already draws ゃ / っ small: drawn at the same scale, they're small.
    assert _word("きゃ", [("き", 0.9), ("ゃ", 0.9)]).verdict == "correct"
    assert _word("いった", [("い", 0.9), ("っ", 0.9), ("た", 0.9)]).verdict == "correct"

    big = _word("きゃ", [("き", 0.9), ("や", 0.9)])
    assert (big.verdict, big.cells[1].looks_like) == ("wrong", "や")
    small = _word("いった", [("い", 0.9), ("つ", 0.9), ("た", 0.9)])
    assert (small.verdict, small.cells[1].looks_like) == ("wrong", "つ")


def test_a_size_between_small_and_big_is_close() -> None:
    grade = _word("きゃ", [("き", 0.9), ("ゃ", 0.9 * 1.13)])

    assert (grade.verdict, grade.cells[1].looks_like) == ("close", None)


def test_a_slip_in_a_kana_leaves_the_word_close() -> None:
    word = ReferenceWord(text="たい", characters=(ALPHABET["た"], ALPHABET["い"]))
    ta = kanjivg_strokes("た")[:3]  # a stroke missing
    cells = (hand_drawn(ta), hand_drawn(kanjivg_strokes("い"), seed=2))

    assert grade_word(CellsAnswer(cells=cells), [word], ALPHABET).verdict == "close"
