"""Geometry of strokes: polylines of points, compared after normalizing.

A drawing and a reference kanji are each normalized on their own (centred on
their bounding box, scaled by its longer side), so where and how big the
user drew on the canvas doesn't count, only the shape. Distances are then in
units of the character's size: 0.1 is a tenth of the kanji.
"""

import math
from collections.abc import Sequence
from itertools import pairwise

from ..entities import Point

Stroke = tuple[Point, ...]

# A bounding box side below this is a dot: it isn't scaled up.
_MIN_SIDE = 1e-6


def normalize(strokes: Sequence[Stroke]) -> list[Stroke]:
    """The strokes centred on their joint bounding box and scaled so its
    longer side is 1."""
    points = [p for stroke in strokes for p in stroke]
    if not points:
        return []
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    side = max(max(xs) - min(xs), max(ys) - min(ys), _MIN_SIDE)
    return [
        tuple(((x - cx) / side, (y - cy) / side) for x, y in stroke)
        for stroke in strokes
    ]


def resample(stroke: Stroke, n: int) -> Stroke:
    """`n` points evenly spaced along the stroke, its ends included. A stroke
    with no length (a tap) is its point `n` times."""
    if n < 2:
        raise ValueError("resample to at least 2 points")
    lengths = [math.dist(a, b) for a, b in pairwise(stroke)]
    total = sum(lengths)
    if total == 0:
        return (stroke[0],) * n
    result = [stroke[0]]
    segment, walked = 0, 0.0  # current segment, length before it
    for k in range(1, n - 1):
        target = total * k / (n - 1)
        while walked + lengths[segment] < target and segment < len(lengths) - 1:
            walked += lengths[segment]
            segment += 1
        length = lengths[segment]
        t = min((target - walked) / length, 1.0) if length else 0.0
        (x0, y0), (x1, y1) = stroke[segment], stroke[segment + 1]
        result.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    result.append(stroke[-1])
    return tuple(result)


def mean_distance(a: Stroke, b: Stroke) -> float:
    """Mean distance between the points of two strokes of the same length,
    pairwise (so direction counts)."""
    if len(a) != len(b):
        raise ValueError("strokes must have the same number of points")
    return sum(math.dist(p, q) for p, q in zip(a, b, strict=True)) / len(a)


def chamfer(a: Sequence[Point], b: Sequence[Point]) -> float:
    """Symmetric chamfer distance: the mean distance from each point to the
    closest point of the other set, both ways. Order and strokes don't count:
    it compares the two drawings as pictures."""
    if not a or not b:
        raise ValueError("chamfer needs points on both sides")

    def one_way(src: Sequence[Point], dst: Sequence[Point]) -> float:
        return sum(min(math.dist(p, q) for q in dst) for p in src) / len(src)

    return (one_way(a, b) + one_way(b, a)) / 2
