import pytest

from shodoukan_practice.domain.services.stroke_geometry_service import (
    chamfer,
    mean_distance,
    normalize,
    resample,
)


def test_normalize_centres_and_scales_by_the_longer_side() -> None:
    strokes = normalize([((10.0, 10.0), (50.0, 10.0)), ((30.0, 0.0), (30.0, 20.0))])

    assert strokes == [((-0.5, 0.0), (0.5, 0.0)), ((0.0, -0.25), (0.0, 0.25))]


def test_normalize_leaves_a_dot_unscaled() -> None:
    assert normalize([((3.0, 4.0),)]) == [((0.0, 0.0),)]


def test_resample_spaces_points_evenly() -> None:
    points = resample(((0.0, 0.0), (1.0, 0.0), (1.0, 3.0)), 5)

    assert points == ((0, 0), (1, 0), (1, 1), (1, 2), (1, 3))


def test_resample_a_tap() -> None:
    assert resample(((2.0, 2.0), (2.0, 2.0)), 3) == ((2, 2),) * 3


def test_mean_distance_counts_direction() -> None:
    line = ((0.0, 0.0), (1.0, 0.0))

    assert mean_distance(line, line) == 0
    assert mean_distance(line, line[::-1]) == 1
    with pytest.raises(ValueError):
        mean_distance(line, line[:1])


def test_chamfer_ignores_order() -> None:
    a = [(0.0, 0.0), (1.0, 0.0)]

    assert chamfer(a, a[::-1]) == 0
    assert chamfer(a, [(0.0, 1.0), (1.0, 1.0)]) == 1
