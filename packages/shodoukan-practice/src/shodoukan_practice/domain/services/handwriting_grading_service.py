"""Grade a drawn kanji against the KanjiVG strokes of the kanji it may be.

The drawing is compared with each accepted kanji, and graded by the closest.
Both are normalized (see `stroke_geometry_service`), so only the shape
counts, not where or how big it was drawn. Two things are compared:

- **The picture**: a chamfer distance between every point of both, blind to
  strokes and their order. It says whether it's the right kanji at all.
- **The strokes**: each drawn stroke is paired with the reference stroke it
  resembles most (both resampled to `STROKE_SAMPLES` points; drawn backwards
  counts as a match, flagged `reversed`). Pairs closer than `STROKE_MATCH`
  match; one further than `STROKE_OK` is `imprecise`. Matched strokes drawn
  out of order are the ones outside the longest run of reference strokes in
  writing order, so swapping two strokes is one mistake, not a cascade. A
  drawn stroke left unpaired is `extra`; a reference one, `missing`.
- **The lengths**: each paired stroke's share of the drawing's total length
  against its reference's share of the kanji's, so proportions count, not
  sizes. Off by more than `LENGTH_TOLERANCE` times, and by more than
  `LENGTH_MIN_SHARE_GAP` of the total, is `too_long` / `too_short`: 未 and 末
  differ only there. The gap keeps a short stroke's natural wobble from
  counting. Strokes shorter than `MIN_LENGTH_CHECKED` (dots) aren't checked.
- **The marks**: in characters of up to `MARK_MAX_STROKES` strokes, where a
  dot or a dakuten changes the character, reference strokes smaller than
  `MARK_EXTENT` (dakuten, handakuten, the dots of 犬 or 心) are too small for
  their shape to say much, so after the other strokes are paired they pair
  with what's left by **position** (their centres closer than `MARK_MATCH`;
  further than `MARK_OK` is `imprecise`), length unchecked; a circle (゜) only
  pairs with a circle. Their direction only counts when it's way off (more
  than `MARK_REVERSED_ANGLE` from the reference's: `reversed`). In denser
  characters short strokes are ordinary strokes (the inner ones of 曜). A run
  of marks (゛'s two strokes) may be drawn in any order. A run with none of its
  marks drawn, or marks drawn where the character has none (大 with a dot, は
  with ゛), make another character.

The verdict leans to the learner: nobody writes as exactly as KanjiVG draws,
so imprecise strokes and strokes of the wrong length are only warnings (see
docs/practice/technical/decisions.md). It depends on the picture, the
stroke order and direction, and the stroke count:

- `correct`: the picture is close (`SHAPE_OK`), and every stroke is there, in
  order and the right way;
- `close`: the picture is close enough (`SHAPE_CLOSE`), at most
  `ALLOWED_COUNT_ERRORS` strokes other than marks are extra or missing (none
  for kanji of fewer than `COUNT_TOLERANCE_FROM` strokes: 二 drawn as 三 is
  another kanji), no run of marks is missing or added whole, and at most
  `MISTAKE_CLOSE_SHARE` of the strokes are out of order, backwards, extra or
  missing;
- `wrong` otherwise.

`score` (0 to 100) mixes the picture and the strokes, for the user's eyes only;
the verdict doesn't depend on it. The thresholds are in units of the kanji's
size and were tuned on KanjiVG strokes drawn with noise; see
docs/practice/technical/exercises.md#handwriting.

`grade_kana` adds recognition for a kana: the drawing is also graded against
every other kana (`alphabet`), and one that fits clearly better
(`RECOGNITION_MARGIN`) makes it wrong, naming it (`looks_like`: ろ for る),
even when it passes for the expected one;
otherwise a recognisable kana (`SHAPE_CLOSE`) is at worst close, since a
stroke too many or too few in the right kana is a slip, not another kana.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from ..entities import (
    HandwritingGrade,
    Point,
    ReferenceKanji,
    StrokeFeedback,
    StrokesAnswer,
    StrokeStatus,
    Verdict,
)
from .stroke_geometry_service import Stroke, chamfer, mean_distance, normalize, resample

STROKE_SAMPLES = 16
# Mean distance between a drawn and a reference stroke (in kanji sizes).
STROKE_OK = 0.12
STROKE_MATCH = 0.28
# Picture distance (chamfer, in kanji sizes) mapped to a 0 to 1 likeness.
SHAPE_SCALE = 0.2
SHAPE_OK = 0.6
SHAPE_CLOSE = 0.4
ALLOWED_COUNT_ERRORS = 1
COUNT_TOLERANCE_FROM = 5
# A stroke's share of the total length may be this many times its reference's
# share, or this many times smaller.
LENGTH_TOLERANCE = 1.35
LENGTH_MIN_SHARE_GAP = 0.045
# Shorter reference strokes (in kanji sizes) aren't length-checked.
MIN_LENGTH_CHECKED = 0.1
# Share of the strokes a close drawing may have mistakes in.
MISTAKE_CLOSE_SHARE = 1 / 2

# Reference strokes smaller than this (in kanji sizes) are marks: dakuten,
# handakuten, dots. Marks pair by the distance between their centres.
MARK_EXTENT = 0.2
MARK_MATCH = 0.2
MARK_OK = 0.1
# Only characters this simple have marks: kana (ぼ has 6 strokes), 犬, 心.
MARK_MAX_STROKES = 6
# How far (in degrees) a mark's direction may turn from the reference's.
MARK_REVERSED_ANGLE = 120
# A stroke this many times longer than its extent, ending this close to its
# start (in extents), is a circle (゜).
CIRCLE_LENGTH = 2.0
CIRCLE_GAP = 0.5
# How much better (in score) another kana must fit to be what was written.
RECOGNITION_MARGIN = 10

# What keeps a drawing from being correct. Imprecise strokes and lengths are
# warnings only.
_MISTAKES = frozenset({"reversed", "out_of_order", "extra", "missing"})

_VERDICT_RANK: dict[Verdict, int] = {"correct": 2, "close": 1, "wrong": 0}


def grade_drawing(
    drawing: StrokesAnswer, references: Sequence[ReferenceKanji]
) -> HandwritingGrade:
    """The grade against the closest of `references` (at least one; the first
    is the kanji asked). Only references whose stroke count is within
    `ALLOWED_COUNT_ERRORS` of the drawing's are compared, since no other can be
    close; the first always is, so there's always a grade."""
    if not references:
        raise ValueError("a drawing is graded against at least one kanji")
    drawn = _prepare(drawing.strokes)
    candidates = [
        r
        for i, r in enumerate(references)
        if i == 0 or abs(len(r.strokes) - len(drawn)) <= ALLOWED_COUNT_ERRORS
    ]
    grades = [_grade_one(drawn, r).grade for r in candidates]
    return max(grades, key=lambda g: (_VERDICT_RANK[g.verdict], g.score))


def grade_kana(
    drawing: StrokesAnswer,
    expected: ReferenceKanji,
    alphabet: Sequence[ReferenceKanji],
) -> HandwritingGrade:
    """The grade of a drawn kana against `expected`, telling it apart from the
    other kana of `alphabet` (the caller leaves out those drawn the same: ヘ for
    へ, and the small or big twin, told apart by size elsewhere). See the
    module docs."""
    drawn = _prepare(drawing.strokes)
    own = _grade_one(drawn, expected)
    # Even a drawing that passes for `expected` may be a closer fit for
    # another kana (ろ passes for る: they differ only in the final loop).
    rivals = [
        _grade_one(drawn, other).grade
        for other in alphabet
        if other.literal != expected.literal
        and abs(len(other.strokes) - len(drawn)) <= ALLOWED_COUNT_ERRORS
    ]
    best = max(rivals, key=lambda g: (_VERDICT_RANK[g.verdict], g.score), default=None)
    if best is not None and (
        _VERDICT_RANK[best.verdict] > _VERDICT_RANK[own.grade.verdict]
        or best.score >= own.grade.score + RECOGNITION_MARGIN
    ):
        return own.grade.model_copy(
            update={"verdict": "wrong", "looks_like": best.matched}
        )
    if (
        own.grade.verdict == "wrong"
        and own.shape >= SHAPE_CLOSE
        and not own.identity_error
    ):
        return own.grade.model_copy(update={"verdict": "close"})
    return own.grade


@dataclass(frozen=True)
class _Pair:
    drawn: int
    reference: int
    distance: float
    reversed: bool
    mark: bool = False


@dataclass(frozen=True)
class _Graded:
    grade: HandwritingGrade
    # The picture's likeness, 0 to 1.
    shape: float
    # A run of marks missing or added whole: another character.
    identity_error: bool


def _prepare(strokes: Sequence[Sequence[Point]]) -> list[Stroke]:
    return [resample(s, STROKE_SAMPLES) for s in normalize([tuple(s) for s in strokes])]


def _grade_one(drawn: list[Stroke], reference: ReferenceKanji) -> _Graded:
    expected = _prepare([s.points for s in reference.strokes])
    shape = _likeness(
        chamfer([p for s in drawn for p in s], [p for s in expected for p in s]),
        SHAPE_SCALE,
    )
    marks = (
        [j for j, stroke in enumerate(expected) if _extent(stroke) < MARK_EXTENT]
        if len(expected) <= MARK_MAX_STROKES
        else []
    )
    strokes = [j for j in range(len(expected)) if j not in marks]
    pairs = _pair(drawn, expected, range(len(drawn)), strokes)
    left = [i for i in range(len(drawn)) if i not in {p.drawn for p in pairs}]
    pairs = sorted(
        pairs + _pair_marks(drawn, expected, left, marks), key=lambda p: p.drawn
    )
    runs = _mark_runs(marks)
    in_order = _longest_ordered_run(pairs, _ranks(len(expected), runs))
    drawn_lengths = [_length(s) for s in drawn]
    expected_lengths = [_length(s) for s in expected]
    drawn_total = sum(drawn_lengths) or 1.0
    expected_total = sum(expected_lengths) or 1.0

    feedback: list[StrokeFeedback] = []
    for pair in pairs:
        status: StrokeStatus = "ok"
        drawn_share = drawn_lengths[pair.drawn] / drawn_total
        expected_share = expected_lengths[pair.reference] / expected_total
        length_ratio = 1.0
        if (
            not pair.mark
            and expected_lengths[pair.reference] >= MIN_LENGTH_CHECKED
            and abs(drawn_share - expected_share) > LENGTH_MIN_SHARE_GAP
        ):
            length_ratio = drawn_share / expected_share
        if pair not in in_order:
            status = "out_of_order"
        elif pair.reversed:
            status = "reversed"
        elif length_ratio > LENGTH_TOLERANCE:
            status = "too_long"
        elif length_ratio < 1 / LENGTH_TOLERANCE:
            status = "too_short"
        elif pair.distance > (MARK_OK if pair.mark else STROKE_OK):
            status = "imprecise"
        feedback.append(
            StrokeFeedback(drawn=pair.drawn, reference=pair.reference, status=status)
        )
    paired_drawn = {p.drawn for p in pairs}
    paired_reference = {p.reference for p in pairs}
    extra = [i for i in range(len(drawn)) if i not in paired_drawn]
    missing = [j for j in range(len(expected)) if j not in paired_reference]
    feedback += [StrokeFeedback(drawn=i, reference=None, status="extra") for i in extra]
    feedback += [
        StrokeFeedback(drawn=None, reference=j, status="missing") for j in missing
    ]
    feedback.sort(key=_feedback_order)

    # Marks missing or added whole make another character (は for ば, 大 for 犬).
    extra_marks = [i for i in extra if _extent(drawn[i]) < MARK_EXTENT]
    identity_error = any(not set(run) & paired_reference for run in runs) or (
        bool(extra_marks) and not marks
    )
    count_errors = sum(1 for i in extra if i not in extra_marks) + sum(
        1 for j in missing if j not in marks
    )

    strokes_likeness = sum(
        _likeness(p.distance, MARK_MATCH if p.mark else STROKE_MATCH) for p in pairs
    ) / max(len(drawn), len(expected))
    score = round(100 * (shape + strokes_likeness) / 2)

    grade = HandwritingGrade(
        score=max(0, min(100, score)),
        verdict=_verdict(
            shape, feedback, count_errors, identity_error, len(drawn), len(expected)
        ),
        matched=reference.literal,
        strokes=tuple(feedback),
    )
    return _Graded(grade=grade, shape=shape, identity_error=identity_error)


def _pair(
    drawn: list[Stroke],
    expected: list[Stroke],
    drawn_indexes: Sequence[int],
    expected_indexes: Sequence[int],
) -> list[_Pair]:
    """Each drawn stroke with the reference stroke it resembles most, closest
    pairs first, each stroke used once; pairs over `STROKE_MATCH` are dropped."""
    candidates = []
    for i in drawn_indexes:
        d = drawn[i]
        backwards = tuple(reversed(d))
        for j in expected_indexes:
            e = expected[j]
            forward, backward = _distance(d, e), _distance(backwards, e)
            candidates.append(_Pair(i, j, min(forward, backward), backward < forward))
    return _take_closest(candidates, STROKE_MATCH)


def _pair_marks(
    drawn: list[Stroke],
    expected: list[Stroke],
    drawn_indexes: Sequence[int],
    marks: Sequence[int],
) -> list[_Pair]:
    """The drawn strokes left with the reference marks, by the distance
    between their centres; a circle only with a circle."""
    candidates = [
        _Pair(
            i,
            j,
            math.dist(_centre(drawn[i]), _centre(expected[j])),
            _turned(drawn[i], expected[j]),
            True,
        )
        for i in drawn_indexes
        for j in marks
        if _is_circle(drawn[i]) == _is_circle(expected[j])
    ]
    return _take_closest(candidates, MARK_MATCH)


def _turned(drawn: Stroke, expected: Stroke) -> bool:
    """Whether a mark was drawn the other way: its direction (start to end)
    more than `MARK_REVERSED_ANGLE` off the reference's. A circle, or a tap,
    has no direction."""
    if _is_circle(expected):
        return False
    (dx, dy), (ex, ey) = _direction(drawn), _direction(expected)
    if math.hypot(dx, dy) == 0 or math.hypot(ex, ey) == 0:
        return False
    turn = abs(math.degrees(math.atan2(dy, dx) - math.atan2(ey, ex))) % 360
    return min(turn, 360 - turn) > MARK_REVERSED_ANGLE


def _direction(stroke: Stroke) -> Point:
    return (stroke[-1][0] - stroke[0][0], stroke[-1][1] - stroke[0][1])


def _take_closest(candidates: list[_Pair], limit: float) -> list[_Pair]:
    """Closest pairs first, each stroke used once, none further than `limit`."""
    candidates.sort(key=lambda p: p.distance)
    pairs: list[_Pair] = []
    used_drawn: set[int] = set()
    used_reference: set[int] = set()
    for pair in candidates:
        if pair.distance > limit:
            break
        if pair.drawn in used_drawn or pair.reference in used_reference:
            continue
        pairs.append(pair)
        used_drawn.add(pair.drawn)
        used_reference.add(pair.reference)
    return pairs


def _distance(drawn: Stroke, expected: Stroke) -> float:
    """How far a drawn stroke is from a reference one: the mean distance
    between their points, and between their furthest-apart ends, so a stroke
    that's too short or too long counts even if it lies on the right line."""
    ends = max(math.dist(drawn[0], expected[0]), math.dist(drawn[-1], expected[-1]))
    return (mean_distance(drawn, expected) + ends) / 2


def _mark_runs(marks: Sequence[int]) -> list[list[int]]:
    """The marks in runs of consecutive strokes (゛'s two strokes are one)."""
    runs: list[list[int]] = []
    for j in marks:
        if runs and runs[-1][-1] == j - 1:
            runs[-1].append(j)
        else:
            runs.append([j])
    return runs


def _ranks(count: int, runs: list[list[int]]) -> list[int]:
    """Each reference stroke's place in writing order; the marks of a run
    share theirs, so they may be drawn in any order."""
    ranks = list(range(count))
    for run in runs:
        for j in run:
            ranks[j] = run[0]
    return ranks


def _longest_ordered_run(pairs: list[_Pair], ranks: list[int]) -> set[_Pair]:
    """The pairs (in drawn order) whose reference strokes form the longest
    increasing run: those were drawn in the right order relative to each
    other; the rest were drawn out of order. Strokes of the same rank (a run
    of marks) may come in any order."""
    if not pairs:
        return set()
    best = [1] * len(pairs)
    previous: list[int | None] = [None] * len(pairs)
    for k, pair in enumerate(pairs):
        for m in range(k):
            if (
                ranks[pairs[m].reference] <= ranks[pair.reference]
                and best[m] + 1 > best[k]
            ):
                best[k], previous[k] = best[m] + 1, m
    last: int | None = max(range(len(pairs)), key=lambda i: best[i])
    run: set[_Pair] = set()
    while last is not None:
        run.add(pairs[last])
        last = previous[last]
    return run


def _verdict(
    shape: float,
    feedback: list[StrokeFeedback],
    count_errors: int,
    identity_error: bool,
    drawn_strokes: int,
    reference_strokes: int,
) -> Verdict:
    """`count_errors` counts extra and missing strokes other than marks."""
    mistakes = sum(1 for f in feedback if f.status in _MISTAKES)
    if shape >= SHAPE_OK and mistakes == 0:
        return "correct"
    allowed = ALLOWED_COUNT_ERRORS if reference_strokes >= COUNT_TOLERANCE_FROM else 0
    if (
        shape >= SHAPE_CLOSE
        and not identity_error
        and count_errors <= allowed
        and mistakes <= MISTAKE_CLOSE_SHARE * max(drawn_strokes, reference_strokes)
    ):
        return "close"
    return "wrong"


def _length(stroke: Stroke) -> float:
    return sum(math.dist(a, b) for a, b in pairwise(stroke))


def _extent(stroke: Stroke) -> float:
    """The longer side of the stroke's bounding box."""
    xs = [x for x, _ in stroke]
    ys = [y for _, y in stroke]
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _centre(stroke: Stroke) -> Point:
    return (
        sum(x for x, _ in stroke) / len(stroke),
        sum(y for _, y in stroke) / len(stroke),
    )


def _is_circle(stroke: Stroke) -> bool:
    """A closed loop (゜): much longer than it's wide, ending near its start."""
    extent = _extent(stroke)
    return (
        extent > 0
        and _length(stroke) >= CIRCLE_LENGTH * extent
        and math.dist(stroke[0], stroke[-1]) <= CIRCLE_GAP * extent
    )


def _likeness(distance: float, scale: float) -> float:
    """1 for no distance, down to 0 at `scale`."""
    return max(0.0, 1 - distance / scale)


def _feedback_order(feedback: StrokeFeedback) -> tuple[int, int]:
    """In drawn order; missing strokes last, in writing order."""
    if feedback.drawn is not None:
        return (0, feedback.drawn)
    return (1, feedback.reference or 0)
