from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from poggio_webapp.pipeline.build_gempy import export_meshes


class RecordingTransform:
    def __init__(self, offset=(10.0, 20.0, 30.0)):
        self.offset = np.asarray(offset)
        self.calls = []

    def apply_inverse(self, vertices):
        self.calls.append(vertices)
        return np.asarray(vertices) + self.offset


def fake_model(transform=None):
    return SimpleNamespace(input_transform=transform or RecordingTransform())


def fake_solution(vertices, faces):
    return SimpleNamespace(
        raw_arrays=SimpleNamespace(vertices=vertices, edges=faces)
    )


def triangle(z=0.0):
    return np.asarray([
        [0.0, 0.0, z],
        [1.0, 0.0, z],
        [0.0, 1.0, z],
    ])


def test_export_meshes_inverse_transforms_each_surface_without_mutating_input(
    tmp_path,
):
    transform = RecordingTransform()
    original_vertices = [triangle(1.0), triangle(2.0)]
    original_copies = [vertices.copy() for vertices in original_vertices]
    faces = [np.asarray([[0, 1, 2]]), np.asarray([[0, 2, 1]])]

    export_meshes(
        fake_model(transform),
        fake_solution(original_vertices, faces),
        ["Upper", "Lower"],
        tmp_path,
    )

    assert len(transform.calls) == 2
    assert transform.calls[0] is original_vertices[0]
    assert transform.calls[1] is original_vertices[1]
    for original, unchanged in zip(original_vertices, original_copies):
        np.testing.assert_array_equal(original, unchanged)


def test_export_meshes_writes_inverse_transformed_vertices(tmp_path):
    paths = export_meshes(
        fake_model(),
        fake_solution([triangle(1.0)], [np.asarray([[0, 1, 2]])]),
        ["Layer"],
        tmp_path,
    )

    lines = Path(paths[0]).read_text().splitlines()

    assert lines[1:4] == [
        "v 10.000000 20.000000 31.000000",
        "v 11.000000 20.000000 31.000000",
        "v 10.000000 21.000000 31.000000",
    ]


def test_export_meshes_keeps_one_based_triangle_faces(tmp_path):
    paths = export_meshes(
        fake_model(),
        fake_solution([triangle()], [np.asarray([[0, 2, 1]])]),
        ["Layer"],
        tmp_path,
    )

    assert Path(paths[0]).read_text().splitlines()[-1] == "f 1 3 2"


def test_export_meshes_sanitizes_only_filename(tmp_path):
    original_name = "Layer / A? (north)"

    paths = export_meshes(
        fake_model(),
        fake_solution([triangle()], [np.asarray([[0, 1, 2]])]),
        [original_name],
        tmp_path,
    )

    assert Path(paths[0]).name == "Layer_A_north.obj"
    assert Path(paths[0]).read_text().splitlines()[0] == f"# {original_name}"


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_export_meshes_rejects_nonfinite_vertices(tmp_path, invalid_value):
    vertices = triangle()
    vertices[1, 2] = invalid_value

    with pytest.raises(ValueError, match="finite"):
        export_meshes(
            fake_model(),
            fake_solution([vertices], [np.asarray([[0, 1, 2]])]),
            ["Invalid"],
            tmp_path,
        )


@pytest.mark.parametrize(
    "vertices",
    [
        np.asarray([0.0, 1.0, 2.0]),
        np.asarray([[0.0, 1.0], [2.0, 3.0]]),
        np.asarray([[0.0, 1.0, 2.0, 3.0]]),
    ],
)
def test_export_meshes_rejects_vertices_not_shaped_n_by_three(
    tmp_path,
    vertices,
):
    with pytest.raises(ValueError, match=r"vertices.*N x 3"):
        export_meshes(
            fake_model(),
            fake_solution([vertices], [np.asarray([[0, 1, 2]])]),
            ["Invalid"],
            tmp_path,
        )


@pytest.mark.parametrize("invalid_index", [-1, 3])
def test_export_meshes_rejects_out_of_range_face_indices(
    tmp_path,
    invalid_index,
):
    with pytest.raises(ValueError, match="face index"):
        export_meshes(
            fake_model(),
            fake_solution(
                [triangle()],
                [np.asarray([[0, 1, invalid_index]])],
            ),
            ["Invalid"],
            tmp_path,
        )


def test_export_meshes_preserves_surface_order(tmp_path):
    surface_order = ["Second surface", "First surface", "Third surface"]
    vertices = [triangle(2.0), triangle(1.0), triangle(3.0)]
    faces = [np.asarray([[0, 1, 2]]) for _ in surface_order]

    paths = export_meshes(
        fake_model(),
        fake_solution(vertices, faces),
        surface_order,
        tmp_path,
    )

    assert [Path(path).name for path in paths] == [
        "Second_surface.obj",
        "First_surface.obj",
        "Third_surface.obj",
    ]
    assert [
        Path(path).read_text().splitlines()[0]
        for path in paths
    ] == [f"# {name}" for name in surface_order]
