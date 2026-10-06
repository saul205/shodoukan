"""Grading drawings against real KanjiVG strokes.

The drawings are the references themselves, moved, resized and shaken with a
seeded random, the mistakes people make (a stroke backwards, two swapped, one
left out), and other kanji.
"""

from random import Random

import pytest

from shodoukan.utils.svg_path import path_points
from shodoukan_practice.domain.entities import (
    Point,
    ReferenceKanji,
    ReferenceStroke,
    StrokesAnswer,
)
from shodoukan_practice.domain.services import grade_drawing

# KanjiVG's strokes, in writing order.
PATHS = {
    "木": [
        "M19.5,39.86c2.45,0.57,5.23,0.8,8.04,0.57C40.75,39.38,63,36.5,79.78,36.15"
        "c2.8-0.06,4.54,0.1,7.34,0.5",
        "M51.75,10.5c1.19,1.19,2,3,2,5c0,8.65,0,55.15-0.14,74.75"
        "c-0.03,4.19-0.07,7.15-0.11,8.25",
        "M50.75,39.5c0,1.12-0.61,2.44-1.42,3.95C41.75,57.5,26.7,73.93,15.75,80.25",
        "M54.5,39c4.62,6,23,25.75,31.76,34.61c2.27,2.29,4.61,4.39,7.49,5.64",
    ],
    "本": [
        "M20.5,33.5c1.93,0.62,4.91,1.07,8.1,0.75C42.43,32.88,66,30.75,79.64,30"
        "c3.2-0.18,7.22,0.25,9.23,0.5",
        "M52.1,11.12c1.25,1.25,2.05,3.23,2.05,4.99c0,0.84,0,57.16-0.02,76.76"
        "c-0.01,3.96-0.01,6.42-0.02,6.62",
        "M51.75,33.5c0,1-0.41,2.22-1.29,3.88C43.62,50.25,30.12,65.5,13.25,75.5",
        "M54.75,35.5c4.92,5.74,23.48,23.33,32.85,31.27c2.58,2.18,5.16,4.41,8.52,5.23",
        "M33.88,73.92c1.5,0.46,2.74,0.75,5.3,0.59c9.95-0.63,21.2-2.13,27.96-2.95"
        "c1.93-0.23,3.62-0.31,6-0.02",
    ],
    "二": [
        "M25.25,32.4c1.77,0.37,4.78,0.56,6.55,0.37c10.82-1.15,28.82-3.4,41.24-3.76"
        "c2.95-0.09,4.73,0.18,6.21,0.36",
        "M12,80.75c2.37,0.5,6.73,0.67,9.09,0.5c23.79-1.75,45.04-4.12,67.49-4.74"
        "c3.95-0.11,6.32,0.24,8.3,0.49",
    ],
    "三": [
        "M27.5,23.65c3.09,0.73,6.29,0.36,9.4,0.06c10.2-1,27-2.94,38.97-3.57"
        "c3.06-0.16,6.09-0.2,9.14,0.23",
        "M28.75,55.14c3.13,0.76,6.46,0.43,9.64,0.2c10.03-0.72,23.97-2.63,34.73-3.12"
        "c2.7-0.12,5.45-0.16,8.13,0.3",
        "M13,87.83c3.94,1.01,7.72,0.96,11.75,0.72c18.41-1.07,41.27-3.39,61.12-4.07"
        "c3.63-0.13,7.2-0.1,10.75,0.78",
    ],
}

Stroke = list[Point]


def reference(literal: str) -> ReferenceKanji:
    return ReferenceKanji(
        literal=literal,
        strokes=tuple(
            ReferenceStroke(path=d, label=None, points=tuple(path_points(d, 2)))
            for d in PATHS[literal]
        ),
    )


def strokes(literal: str) -> list[Stroke]:
    return [list(s.points) for s in reference(literal).strokes]


def drawn(strokes: list[Stroke], seed: int = 1) -> StrokesAnswer:
    """`strokes` drawn by hand: smaller and off centre, each stroke a little
    out of place, every point shaky."""
    rng = Random(seed)
    scale, dx, dy = 0.8, -6.0, 5.0
    shaken = []
    for stroke in strokes:
        ox, oy = rng.uniform(-2, 2), rng.uniform(-2, 2)
        shaken.append(
            tuple(
                (
                    (x - 54.5) * scale + 54.5 + dx + ox + rng.gauss(0, 1),
                    (y - 54.5) * scale + 54.5 + dy + oy + rng.gauss(0, 1),
                )
                for x, y in stroke[::2]
            )
        )
    return StrokesAnswer(strokes=tuple(shaken))


def statuses(literal_drawn: StrokesAnswer, literal: str) -> list[str]:
    return [
        f.status for f in grade_drawing(literal_drawn, [reference(literal)]).strokes
    ]


def test_the_reference_itself_is_perfect() -> None:
    exact = StrokesAnswer(strokes=tuple(tuple(s) for s in strokes("木")))

    result = grade_drawing(exact, [reference("木")])

    assert (result.verdict, result.score, result.matched) == ("correct", 100, "木")
    assert [(f.drawn, f.reference, f.status) for f in result.strokes] == [
        (i, i, "ok") for i in range(4)
    ]


@pytest.mark.parametrize("literal", ["木", "本", "二", "三"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_a_shaky_drawing_anywhere_on_the_canvas_is_correct(
    literal: str, seed: int
) -> None:
    result = grade_drawing(drawn(strokes(literal), seed), [reference(literal)])

    assert result.verdict == "correct"
    assert 60 <= result.score < 100


def test_a_stroke_drawn_backwards_is_close() -> None:
    kanji = strokes("本")
    kanji[1] = kanji[1][::-1]

    result = grade_drawing(drawn(kanji), [reference("本")])

    assert result.verdict == "close"
    assert [(f.drawn, f.status) for f in result.strokes if f.status != "ok"] == [
        (1, "reversed")
    ]


def test_two_strokes_swapped_are_one_mistake() -> None:
    kanji = strokes("木")
    kanji[0], kanji[1] = kanji[1], kanji[0]

    result = grade_drawing(drawn(kanji), [reference("木")])

    assert result.verdict == "close"
    assert statuses(drawn(kanji), "木").count("out_of_order") == 1


def test_a_missing_stroke_is_close_in_a_kanji_of_five() -> None:
    result = grade_drawing(drawn(strokes("本")[:4]), [reference("本")])

    assert result.verdict == "close"
    assert result.strokes[-1].status == "missing"
    assert result.strokes[-1].reference == 4


def test_a_missing_stroke_is_another_kanji_when_it_has_few() -> None:
    # 三 without its last stroke is 二.
    result = grade_drawing(drawn(strokes("三")[:2]), [reference("三")])

    assert result.verdict == "wrong"


@pytest.mark.parametrize(
    ("literal_drawn", "literal"), [("本", "木"), ("三", "二"), ("木", "二")]
)
def test_another_kanji_is_wrong(literal_drawn: str, literal: str) -> None:
    result = grade_drawing(drawn(strokes(literal_drawn)), [reference(literal)])

    assert result.verdict == "wrong"


def test_the_closest_accepted_kanji_grades_it() -> None:
    result = grade_drawing(drawn(strokes("本")), [reference("木"), reference("本")])

    assert (result.verdict, result.matched) == ("correct", "本")


def test_a_tap_is_a_stroke_too() -> None:
    tap = StrokesAnswer(strokes=(((50.0, 50.0),),))

    result = grade_drawing(tap, [reference("二")])

    assert result.verdict == "wrong"
    assert len(result.strokes) >= 2


def test_needs_a_reference() -> None:
    with pytest.raises(ValueError):
        grade_drawing(drawn(strokes("二")), [])
