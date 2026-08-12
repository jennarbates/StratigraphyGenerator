"""Plane-geometry primitives for polygon validation.

Nothing here knows about editors, faces or jobs -- these are orientation,
segment intersection and self-intersection on lists of points.
"""

import math


def _point_coordinates(point: dict) -> tuple[float, float] | None:
    x_coordinate = point.get("x")
    y_coordinate = point.get("y")
    if (
        not isinstance(x_coordinate, (int, float))
        or isinstance(x_coordinate, bool)
        or not math.isfinite(x_coordinate)
        or not isinstance(y_coordinate, (int, float))
        or isinstance(y_coordinate, bool)
        or not math.isfinite(y_coordinate)
    ):
        return None
    return float(x_coordinate), float(y_coordinate)


def _direction(start, end, point):
    return (end[0] - start[0]) * (point[1] - start[1]) - (end[1] - start[1]) * (
        point[0] - start[0]
    )


def _point_on_segment(point, start, end):
    return (
        _direction(start, end, point) == 0
        and min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def _segments_intersect(first_start, first_end, second_start, second_end):
    first_direction = _direction(first_start, first_end, second_start)
    second_direction = _direction(first_start, first_end, second_end)
    third_direction = _direction(second_start, second_end, first_start)
    fourth_direction = _direction(second_start, second_end, first_end)

    if (
        first_direction > 0 > second_direction or first_direction < 0 < second_direction
    ) and (
        third_direction > 0 > fourth_direction or third_direction < 0 < fourth_direction
    ):
        return True

    return (
        first_direction == 0
        and _point_on_segment(second_start, first_start, first_end)
        or second_direction == 0
        and _point_on_segment(second_end, first_start, first_end)
        or third_direction == 0
        and _point_on_segment(first_start, second_start, second_end)
        or fourth_direction == 0
        and _point_on_segment(first_end, second_start, second_end)
    )


def _polygon_self_intersects(vertices: list[dict]) -> bool:
    points = [_point_coordinates(vertex) for vertex in vertices]
    if any(point is None for point in points):
        return False
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 4:
        return False

    for first_edge in range(len(points)):
        first_edge_end = (first_edge + 1) % len(points)
        for second_edge in range(first_edge + 1, len(points)):
            second_edge_end = (second_edge + 1) % len(points)
            edges_are_adjacent = (
                first_edge_end == second_edge or second_edge_end == first_edge
            )
            if edges_are_adjacent:
                continue
            if _segments_intersect(
                points[first_edge],
                points[first_edge_end],
                points[second_edge],
                points[second_edge_end],
            ):
                return True

    return False
