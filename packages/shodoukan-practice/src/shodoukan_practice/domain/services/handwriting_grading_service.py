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

The verdict:

- `correct`: every stroke matches, in order and direction, and the picture is
  close (`SHAPE_OK`);
- `close`: the picture is close enough (`SHAPE_CLOSE`), and at most
  `ALLOWED_COUNT_ERRORS` strokes are extra or missing (none for kanji of fewer
  than `COUNT_TOLERANCE_FROM` strokes: 二 drawn as 三 is another kanji);
- `wrong` otherwise.

`score` (0 to 100) mixes the picture and the strokes, for the user's eyes only;
the verdict doesn't depend on it. The thresholds are in units of the kanji's
size and were tuned on KanjiVG strokes drawn with noise; see
docs/practice/technical/exercises.md#handwriting.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

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
STROKE_MATCH = 0.25
# Picture distance (chamfer, in kanji sizes) mapped to a 0 to 1 likeness.
SHAPE_SCALE = 0.2
SHAPE_OK = 0.6
SHAPE_CLOSE = 0.4
ALLOWED_COUNT_ERRORS = 1
COUNT_TOLERANCE_FROM = 5

_VERDICT_RANK: dict[Verdict, int] = {"correct": 2, "close": 1, "wrong": 0}


def grade_drawing(
    drawing: StrokesAnswer, references: Sequence[ReferenceKanji]
) -> HandwritingGrade:
    """The grade against the closest of `references` (at least one)."""
    if not references:
        raise ValueError("a drawing is graded against at least one kanji")
    drawn = _prepare(drawing.strokes)
    grades = [_grade_one(drawn, r) for r in references]
    return max(grades, key=lambda g: (_VERDICT_RANK[g.verdict], g.score))


@dataclass(frozen=True)
class _Pair:
    drawn: int
    reference: int
    distance: float
    reversed: bool


def _prepare(strokes: Sequence[Sequence[Point]]) -> list[Stroke]:
    return [resample(s, STROKE_SAMPLES) for s in normalize([tuple(s) for s in strokes])]


def _grade_one(drawn: list[Stroke], reference: ReferenceKanji) -> HandwritingGrade:
    expected = _prepare([s.points for s in reference.strokes])
    shape = _likeness(
        chamfer([p for s in drawn for p in s], [p for s in expected for p in s]),
        SHAPE_SCALE,
    )
    pairs = _pair(drawn, expected)
    in_order = _longest_ordered_run(pairs)

    feedback: list[StrokeFeedback] = []
    for pair in pairs:
        status: StrokeStatus = "ok"
        if pair not in in_order:
            status = "out_of_order"
        elif pair.reversed:
            status = "reversed"
        elif pair.distance > STROKE_OK:
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

    strokes_likeness = sum(_likeness(p.distance, STROKE_MATCH) for p in pairs) / max(
        len(drawn), len(expected)
    )
    score = round(100 * (shape + strokes_likeness) / 2)

    return HandwritingGrade(
        score=max(0, min(100, score)),
        verdict=_verdict(shape, feedback, len(expected)),
        matched=reference.literal,
        strokes=tuple(feedback),
    )


def _pair(drawn: list[Stroke], expected: list[Stroke]) -> list[_Pair]:
    """Each drawn stroke with the reference stroke it resembles most, closest
    pairs first, each stroke used once; pairs over `STROKE_MATCH` are dropped."""
    candidates = []
    for i, d in enumerate(drawn):
        backwards = tuple(reversed(d))
        for j, e in enumerate(expected):
            forward, backward = _distance(d, e), _distance(backwards, e)
            candidates.append(_Pair(i, j, min(forward, backward), backward < forward))
    candidates.sort(key=lambda p: p.distance)
    pairs: list[_Pair] = []
    used_drawn: set[int] = set()
    used_reference: set[int] = set()
    for pair in candidates:
        if pair.distance > STROKE_MATCH:
            break
        if pair.drawn in used_drawn or pair.reference in used_reference:
            continue
        pairs.append(pair)
        used_drawn.add(pair.drawn)
        used_reference.add(pair.reference)
    return sorted(pairs, key=lambda p: p.drawn)


def _distance(drawn: Stroke, expected: Stroke) -> float:
    """How far a drawn stroke is from a reference one: the mean distance
    between their points, and between their furthest-apart ends, so a stroke
    that's too short or too long counts even if it lies on the right line."""
    ends = max(math.dist(drawn[0], expected[0]), math.dist(drawn[-1], expected[-1]))
    return (mean_distance(drawn, expected) + ends) / 2


def _longest_ordered_run(pairs: list[_Pair]) -> set[_Pair]:
    """The pairs (in drawn order) whose reference strokes form the longest
    increasing run: those were drawn in the right order relative to each
    other; the rest were drawn out of order."""
    if not pairs:
        return set()
    best = [1] * len(pairs)
    previous: list[int | None] = [None] * len(pairs)
    for k, pair in enumerate(pairs):
        for m in range(k):
            if pairs[m].reference < pair.reference and best[m] + 1 > best[k]:
                best[k], previous[k] = best[m] + 1, m
    last: int | None = max(range(len(pairs)), key=lambda i: best[i])
    run: set[_Pair] = set()
    while last is not None:
        run.add(pairs[last])
        last = previous[last]
    return run


def _verdict(
    shape: float, feedback: list[StrokeFeedback], reference_strokes: int
) -> Verdict:
    count_errors = sum(1 for f in feedback if f.status in ("extra", "missing"))
    if shape >= SHAPE_OK and all(f.status == "ok" for f in feedback):
        return "correct"
    allowed = ALLOWED_COUNT_ERRORS if reference_strokes >= COUNT_TOLERANCE_FROM else 0
    if shape >= SHAPE_CLOSE and count_errors <= allowed:
        return "close"
    return "wrong"


def _likeness(distance: float, scale: float) -> float:
    """1 for no distance, down to 0 at `scale`."""
    return max(0.0, 1 - distance / scale)


def _feedback_order(feedback: StrokeFeedback) -> tuple[int, int]:
    """In drawn order; missing strokes last, in writing order."""
    if feedback.drawn is not None:
        return (0, feedback.drawn)
    return (1, feedback.reference or 0)
