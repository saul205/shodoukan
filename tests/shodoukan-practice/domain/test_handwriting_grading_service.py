"""Grading drawings against real KanjiVG strokes.

The drawings are the references themselves, moved, resized and shaken with a
seeded random, the mistakes people make (a stroke backwards, two swapped, one
left out), and other kanji.
"""

import math
from random import Random

import pytest
from factories import hand_drawn, kanjivg_reference, kanjivg_strokes

from shodoukan.utils.svg_path import path_points
from shodoukan_practice.domain.entities import (
    HandwritingGrade,
    Point,
    ReferenceKanji,
    ReferenceStroke,
    StrokesAnswer,
)
from shodoukan_practice.domain.services import grade_drawing, grade_kana

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
    "未": [
        "M30.13,30.77c2.62,0.48,5.01,0.34,7.25,0.03c10.24-1.4,24.97-3.2,34.89-4.19"
        "c2.11-0.21,4.61-0.24,6.45-0.01",
        "M16.69,51.25c3.17,0.89,6.12,0.81,9.34,0.39c13.85-1.77,40.22-4.64,56.98-5.88"
        "c3.16-0.23,6.05-0.29,9.18,0.24",
        "M52.66,11c1.17,1.17,1.92,2.62,1.92,4.25c0,5.16-0.03,55.71-0.04,77"
        "c0,3.47,0,6.16,0,7.75",
        "M51.5,49.25c0,1.12-0.66,2.62-1.5,3.88C41.92,65.24,25.89,81.18,12.75,87.5",
        "M56.12,49.75c5.62,6.25,20.25,20.5,30.33,28.93c2.53,2.11,5.04,3.82,8.42,5.07",
    ],
    "末": [
        "M17.75,31.2c3.38,0.8,6.46,0.85,9.52,0.51c13.98-1.58,41.74-4.25,55.23-5"
        "c3.05-0.17,6-0.3,9,0.34",
        "M27.12,51.75c2.07,0.62,4.13,0.66,7.07,0.25c12.56-1.75,26.81-3.38,40.73-4.25"
        "c2.96-0.19,5.1,0,6.96,0.25",
        "M52.5,10.75c1.25,1.25,2.25,3,2.25,4.75c0,0.87,0,53.95,0,75.62"
        "c0,4.12,0,7.1,0,8.38",
        "M53.25,50.5c0,1.75-0.72,2.84-1.43,3.92C43.77,66.75,27.21,82.41,13.75,89",
        "M55.62,51.88c4.35,5.37,20.9,21.25,28.87,28.51c2.47,2.25,4.68,4.01,7.76,5.37",
    ],
    "土": [
        "M26.63,50.89c1.63,0.4,4.64,0.6,6.26,0.4C43.5,50,62.12,48,75.66,46.92"
        "c2.71-0.22,4.36,0.19,5.72,0.39",
        "M52.17,17.37c1.17,1.17,2.02,3.13,2.02,4.64c0,10.25,0.14,61.06,0.14,63.36",
        "M15.38,87.73c2.12,0.54,6.01,0.73,8.12,0.54C46,86.25,69,84.62,90.34,83.79"
        "c3.53-0.14,5.65,0.26,7.41,0.53",
    ],
    "士": [
        "M13.13,54.98c3.87,0.9,7.66,0.43,11.36,0.16c18.76-1.39,44.96-3.08,61.9-3.32"
        "c3.22-0.05,6.57,0.08,9.74,0.76",
        "M52.25,17.25C53.31,18.31,54,19.88,54,21.5c0,1.03,0.25,58.62,0.25,66",
        "M21.75,89.45c2.73,0.83,5.82,0.54,8.62,0.42c12.73-0.57,33.94-2.04,45.88-2.17"
        "c2.97-0.03,5.83,0.21,8.75,0.74",
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


@pytest.mark.parametrize(
    ("literal_drawn", "literal"),
    [("未", "末"), ("末", "未"), ("土", "士"), ("士", "土")],
)
def test_lengths_off_are_warnings_on_a_right_drawing(
    literal_drawn: str, literal: str
) -> None:
    # Twins that differ only in stroke lengths: nobody writes that exactly, so
    # the lengths are pointed out but the drawing counts.
    exact = StrokesAnswer(strokes=tuple(tuple(s) for s in strokes(literal_drawn)))

    result = grade_drawing(exact, [reference(literal)])

    assert result.verdict == "correct"
    assert {"too_long", "too_short"} <= {f.status for f in result.strokes}


def _off(kanji: list[Stroke], moves: dict[int, tuple[float, float]]) -> list[Stroke]:
    return [
        [(x + moves[i][0], y + moves[i][1]) for x, y in s] if i in moves else s
        for i, s in enumerate(kanji)
    ]


def test_imprecise_strokes_are_warnings_on_a_right_drawing() -> None:
    # Three of 本's five strokes out of place: still 本, with three warnings.
    kanji = _off(strokes("本"), {2: (12, 0), 3: (-12, 0), 4: (0, 10)})

    result = grade_drawing(drawn(kanji), [reference("本")])

    assert result.verdict == "correct"
    assert [f.status for f in result.strokes].count("imprecise") == 3


def test_a_drawing_too_far_from_the_kanji_isnt_correct() -> None:
    # Every stroke of 土 well off: the whole no longer looks like it.
    kanji = _off(strokes("土"), {0: (10, -10), 1: (-10, 5), 2: (0, -10)})

    assert grade_drawing(drawn(kanji), [reference("土")]).verdict == "wrong"


def test_a_stroke_well_out_of_place_still_pairs() -> None:
    # The vertical stroke 22 units to the right: imprecise, not extra + missing.
    kanji = _off(strokes("木"), {1: (22, 0)})

    result = grade_drawing(drawn(kanji), [reference("木")])

    assert result.verdict == "correct"
    statuses = [f.status for f in result.strokes]
    assert "extra" not in statuses
    assert "missing" not in statuses
    assert "imprecise" in statuses


def test_only_kanji_with_about_as_many_strokes_are_compared() -> None:
    # 二 has 2 strokes, so 本 (5) isn't compared; the asked kanji always is.
    result = grade_drawing(drawn(strokes("二")), [reference("本"), reference("木")])

    assert result.matched == "本"
    assert result.verdict == "wrong"
    two = grade_drawing(drawn(strokes("二")), [reference("木"), reference("二")])
    assert (two.matched, two.verdict) == ("二", "correct")


# Marks (dakuten, handakuten, dots) and telling kana apart, on KanjiVG's own
# strokes of the kana (`kanjivg_paths`).


def _grade(
    literal_drawn: str, literal: str, *, keep: list[int] | None = None
) -> HandwritingGrade:
    strokes = kanjivg_strokes(literal_drawn)
    if keep is not None:
        strokes = [strokes[i] for i in keep]
    return grade_drawing(
        StrokesAnswer(strokes=hand_drawn(strokes)), [kanjivg_reference(literal)]
    )


def test_dakuten_pair_by_place_in_any_order() -> None:
    assert _grade("べ", "べ").verdict == "correct"
    assert _grade("べ", "べ", keep=[0, 2, 1]).verdict == "correct"


def test_half_a_dakuten_is_close() -> None:
    grade = _grade("べ", "べ", keep=[0, 1])

    assert grade.verdict == "close"
    assert [f.status for f in grade.strokes] == ["ok", "ok", "missing"]


@pytest.mark.parametrize(
    ("literal_drawn", "literal"),
    [
        ("へ", "べ"),  # no dakuten
        ("ば", "は"),  # a dakuten that isn't there
        ("ぱ", "ば"),  # ゜ for ゛
        ("大", "犬"),  # no dot
        ("犬", "大"),  # a dot too many
    ],
)
def test_marks_missing_or_added_whole_are_another_character(
    literal_drawn: str, literal: str
) -> None:
    assert _grade(literal_drawn, literal).verdict == "wrong"


def test_a_dot_drawn_in_its_place_is_right() -> None:
    assert _grade("犬", "犬").verdict == "correct"


KANA = "へべばぱはるろれねきゃやいつった"


def _kana(
    literal_drawn: str, literal: str, keep: list[int] | None = None
) -> HandwritingGrade:
    strokes = kanjivg_strokes(literal_drawn)
    if keep is not None:
        strokes = [strokes[i] for i in keep]
    rivals = [kanjivg_reference(k) for k in KANA if k != literal]
    return grade_kana(
        StrokesAnswer(strokes=hand_drawn(strokes)), kanjivg_reference(literal), rivals
    )


@pytest.mark.parametrize(("literal_drawn", "literal"), [("ろ", "る"), ("ね", "れ")])
def test_a_kana_that_fits_another_better_is_wrong_and_named(
    literal_drawn: str, literal: str
) -> None:
    grade = _kana(literal_drawn, literal)

    assert (grade.verdict, grade.looks_like) == ("wrong", literal_drawn)


def test_a_kana_written_right_is_right() -> None:
    for literal in "るれきいつた":
        grade = _kana(literal, literal)
        assert (grade.verdict, grade.looks_like) == ("correct", None), literal


def test_a_slip_in_the_right_kana_is_close_not_wrong() -> None:
    # た has fewer than COUNT_TOLERANCE_FROM strokes: as a kanji, one missing
    # would make it another one.
    assert _grade("た", "た", keep=[0, 1, 2]).verdict == "wrong"
    assert _kana("た", "た", keep=[0, 1, 2]).verdict == "close"


def test_a_mark_drawn_the_other_way_is_reversed_but_its_angle_is_free() -> None:
    be = kanjivg_strokes("べ")
    rivals = [kanjivg_reference(k) for k in KANA if k != "べ"]

    def kana(strokes: list[tuple[Point, ...]]) -> HandwritingGrade:
        drawing = StrokesAnswer(strokes=hand_drawn(strokes))
        return grade_kana(drawing, kanjivg_reference("べ"), rivals)

    backwards = kana([be[0], be[1][::-1], be[2][::-1]])
    assert backwards.verdict == "close"
    assert [f.status for f in backwards.strokes] == ["ok", "reversed", "reversed"]
    assert kana([be[0], _turn(be[1], 60), _turn(be[2], 60)]).verdict == "correct"


def _turn(stroke: tuple[Point, ...], degrees: float) -> tuple[Point, ...]:
    """`stroke` turned about its centre."""
    cx = sum(x for x, _ in stroke) / len(stroke)
    cy = sum(y for _, y in stroke) / len(stroke)
    a = math.radians(degrees)
    return tuple(
        (
            cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a),
            cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a),
        )
        for x, y in stroke
    )


def test_short_strokes_of_a_dense_kanji_are_ordinary_strokes() -> None:
    # 曜 has 18 strokes: its short ones (the inner strokes of 日) aren't marks,
    # so their direction counts and one missing is a slip, not another kanji.
    yo = kanjivg_strokes("曜")
    backwards = [*yo[:1], yo[1][::-1], *yo[2:]]
    grade = grade_drawing(
        StrokesAnswer(strokes=hand_drawn(backwards)), [kanjivg_reference("曜")]
    )
    assert grade.verdict == "close"
    assert [f.status for f in grade.strokes if f.status != "ok"] == ["reversed"]

    missing = yo[:11] + yo[12:]
    assert (
        grade_drawing(
            StrokesAnswer(strokes=hand_drawn(missing)), [kanjivg_reference("曜")]
        ).verdict
        == "close"
    )
