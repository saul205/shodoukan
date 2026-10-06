"""Flattens SVG path data into evenly spaced points.

KanjiVG draws each stroke as the centre line of a pen stroke, with `M`, `C` and
`S` commands (absolute and relative). Lines (`L`, `H`, `V`) and `Z` are read too,
so any simple open path works. Arcs and quadratic curves aren't supported.
"""

import math
import re
from itertools import pairwise

Point = tuple[float, float]

# A command letter, or a number (KanjiVG writes "2.67-0.97" and ".5.5" without
# separators).
_TOKEN = re.compile(r"[MmCcSsLlHhVvZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
# Samples per cubic segment before resampling: plenty for strokes of a 109 square.
_CURVE_SAMPLES = 24


def path_points(d: str, spacing: float = 1.0) -> list[Point]:
    """The points of path `d`, `spacing` apart along it (in the path's units).

    The first and last points of the path are always kept, so a path shorter
    than `spacing` yields its two ends. Raises `ValueError` for path data it
    can't read.
    """
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    polyline = _polyline(d)
    if not polyline:
        return []
    return [(round(x, 2), round(y, 2)) for x, y in _resample(polyline, spacing)]


def _polyline(d: str) -> list[Point]:
    """The path as a dense polyline: curves sampled, lines as they are."""
    tokens = _TOKEN.findall(d)
    if "".join(tokens).replace(" ", "") != re.sub(r"[\s,]", "", d):
        raise ValueError(f"unsupported path data: {d!r}")
    points: list[Point] = []
    current: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    # The second control point of the last cubic, reflected by `S`.
    last_control: Point | None = None
    command = ""
    i = 0

    def numbers(count: int) -> list[float]:
        nonlocal i
        values = tokens[i : i + count]
        if len(values) < count or any(v.isalpha() for v in values):
            raise ValueError(f"missing coordinates in path data: {d!r}")
        i += count
        return [float(v) for v in values]

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        elif not command:
            raise ValueError(f"path data must start with a command: {d!r}")
        relative = command.islower()
        ox, oy = current if relative else (0.0, 0.0)
        kind = command.upper()

        if kind == "M":
            x, y = numbers(2)
            current = start = (ox + x, oy + y)
            points.append(current)
            last_control = None
            # Further pairs after a move are implicit line-tos.
            command = "l" if relative else "L"
        elif kind == "L":
            x, y = numbers(2)
            current = (ox + x, oy + y)
            points.append(current)
            last_control = None
        elif kind == "H":
            (x,) = numbers(1)
            current = (ox + x, current[1])
            points.append(current)
            last_control = None
        elif kind == "V":
            (y,) = numbers(1)
            current = (current[0], oy + y)
            points.append(current)
            last_control = None
        elif kind in ("C", "S"):
            if kind == "C":
                x1, y1, x2, y2, x, y = numbers(6)
                c1 = (ox + x1, oy + y1)
            else:
                x2, y2, x, y = numbers(4)
                c1 = (
                    (2 * current[0] - last_control[0], 2 * current[1] - last_control[1])
                    if last_control
                    else current
                )
            c2 = (ox + x2, oy + y2)
            end = (ox + x, oy + y)
            points.extend(_cubic(current, c1, c2, end))
            current, last_control = end, c2
        elif kind == "Z":
            current = start
            points.append(current)
            last_control = None
            command = ""
        else:  # pragma: no cover - _TOKEN only matches the commands above
            raise ValueError(f"unsupported path command {command!r}")
    return points


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point) -> list[Point]:
    """Points along a cubic Bézier, without its start (already in the line)."""
    result = []
    for step in range(1, _CURVE_SAMPLES + 1):
        t = step / _CURVE_SAMPLES
        u = 1 - t
        a, b, c, e = u**3, 3 * u * u * t, 3 * u * t * t, t**3
        result.append(
            (
                a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0],
                a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1],
            )
        )
    return result


def _resample(polyline: list[Point], spacing: float) -> list[Point]:
    """Points `spacing` apart along the polyline, plus its last point."""
    result = [polyline[0]]
    carried = 0.0  # length walked since the last emitted point
    for (x0, y0), (x1, y1) in pairwise(polyline):
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            continue
        walked = spacing - carried
        while walked <= length:
            t = walked / length
            result.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            walked += spacing
        carried = length - (walked - spacing)
    if result[-1] != polyline[-1] and (len(result) == 1 or carried > 1e-9):
        result.append(polyline[-1])
    return result
