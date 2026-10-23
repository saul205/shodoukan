import math
from itertools import pairwise

import pytest

from shodoukan.utils.svg_path import path_points


def _gaps(points):
    return [math.dist(a, b) for a, b in pairwise(points)]


def test_straight_cubic_is_evenly_spaced():
    points = path_points("M20,30c10,0,20,0,30,0", spacing=5)

    assert points == [(20 + 5 * i, 30) for i in range(7)]


def test_curve_keeps_both_ends_and_spacing():
    points = path_points("M54,10c0,5-20,20-40,25", spacing=2)

    assert points[0] == (54, 10)
    assert points[-1] == (14, 35)
    assert all(g == pytest.approx(2, abs=0.05) for g in _gaps(points)[:-1])


def test_real_kanjivg_stroke_with_unseparated_numbers():
    # 食's first stroke, as KanjiVG writes it.
    d = "M52.75,10.5c0.11,0.98-0.19,2.67-0.97,3.93C45,25.34,31.75,41.19,14,51.5"

    points = path_points(d)

    assert points[0] == (52.75, 10.5)
    assert points[-1] == (14, 51.5)
    assert len(points) > 40


def test_smooth_curve_reflects_the_previous_control_point():
    # The `s` segment mirrors the `c` one: a symmetric arch around x = 20.
    points = path_points("M0,0c0,10,10,10,10,10s10,0,10,-10", spacing=0.5)

    top = max(points, key=lambda p: p[1])
    assert top[0] == pytest.approx(10, abs=0.5)
    assert points[-1] == (20, 0)


def test_lines_and_close():
    points = path_points("M0,0h3v4z", spacing=1)

    assert points[0] == (0, 0)
    assert points[-1] == (0, 0)
    assert len(points) == 13  # 3 + 4 + 5 units of perimeter


def test_short_path_yields_its_ends():
    assert path_points("M0,0L0.5,0", spacing=2) == [(0, 0), (0.5, 0)]
    assert path_points("M3,4") == [(3, 4)]


@pytest.mark.parametrize("d", ["M0,0A5,5,0,0,1,10,10", "0,0L1,1", "M0"])
def test_unsupported_path_data(d):
    with pytest.raises(ValueError):
        path_points(d)
