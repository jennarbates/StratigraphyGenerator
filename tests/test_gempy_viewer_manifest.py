import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from poggio_webapp.pipeline.build_gempy import (
    run_build,
    write_viewer_manifest,
)


def write_test_manifest(
    tmp_path,
    *,
    extent=None,
    resolution=None,
    series_order=None,
    single_face_note=None,
    mesh_filenames=None,
):
    model_dir = tmp_path / "06_gempy_model"
    mesh_dir = model_dir / "trench_model_meshes"
    mesh_dir.mkdir(parents=True)
    manifest_path = model_dir / "trench_model_viewer.json"
    lith_block_path = model_dir / "trench_model_lith_block.npz"
    names = series_order or ["Topsoil", "Fill"]
    filenames = (
        mesh_filenames
        if mesh_filenames is not None
        else ["Topsoil.obj", "Fill.obj"]
    )
    mesh_paths = [mesh_dir / filename for filename in filenames]

    returned_path = write_viewer_manifest(
        manifest_path,
        extent=extent or [0, 10, 0, 5, 90, 100],
        resolution=resolution or [50, 50, 30],
        series_order=names,
        single_face_note=single_face_note,
        mesh_paths=mesh_paths,
        lith_block_path=lith_block_path,
    )

    assert Path(returned_path) == manifest_path
    return manifest_path, json.loads(manifest_path.read_text())


def test_manifest_has_version_one_and_required_kind(tmp_path):
    _, manifest = write_test_manifest(tmp_path)

    assert manifest["schema_version"] == 1
    assert manifest["kind"] == "gempy-surface-model"
    assert manifest["coordinate_system"] == {"units": "m", "up_axis": "Z"}


def test_manifest_serializes_numpy_scalars_as_json_numbers(tmp_path):
    extent = [
        np.int64(0),
        np.float64(10.5),
        np.int32(0),
        np.float32(5.25),
        np.int16(90),
        np.float64(100),
    ]

    _, manifest = write_test_manifest(tmp_path, extent=extent)

    assert all(type(value) in (int, float) for value in manifest["extent"])
    assert manifest["extent"] == [0, 10.5, 0, 5.25, 90, 100]


def test_manifest_resolution_values_are_json_integers(tmp_path):
    _, manifest = write_test_manifest(
        tmp_path,
        resolution=[np.int64(50), np.int32(40), np.uint16(30)],
    )

    assert manifest["resolution"] == [50, 40, 30]
    assert all(type(value) is int for value in manifest["resolution"])


def test_manifest_surface_names_and_order_match_series_order(tmp_path):
    series_order = ["Young layer", "Middle layer", "Old layer"]

    _, manifest = write_test_manifest(
        tmp_path,
        series_order=series_order,
        mesh_filenames=[
            "Young_layer.obj",
            "Middle_layer.obj",
            "Old_layer.obj",
        ],
    )

    assert [surface["name"] for surface in manifest["surfaces"]] == series_order


def test_manifest_paths_are_relative_portable_and_match_mesh_files(tmp_path):
    _, manifest = write_test_manifest(
        tmp_path,
        series_order=["Layer / A? (north)", "Layer B"],
        mesh_filenames=["Layer_A_north.obj", "Layer_B.obj"],
    )

    assert manifest["surfaces"] == [
        {
            "name": "Layer / A? (north)",
            "mesh_path": "trench_model_meshes/Layer_A_north.obj",
        },
        {
            "name": "Layer B",
            "mesh_path": "trench_model_meshes/Layer_B.obj",
        },
    ]
    assert (
        manifest["lith_block_path"]
        == "trench_model_lith_block.npz"
    )
    stored_paths = [
        surface["mesh_path"] for surface in manifest["surfaces"]
    ] + [manifest["lith_block_path"]]
    assert all(not Path(path).is_absolute() for path in stored_paths)
    assert all("\\" not in path for path in stored_paths)
    assert str(tmp_path) not in json.dumps(manifest)


@pytest.mark.parametrize(
    "single_face_note",
    [None, "Topsoil is interpolated from one face."],
)
def test_manifest_single_face_note_is_nullable_or_text(
    tmp_path,
    single_face_note,
):
    _, manifest = write_test_manifest(
        tmp_path,
        single_face_note=single_face_note,
    )

    assert manifest["single_face_note"] == single_face_note


def test_manifest_with_no_meshes_has_empty_surfaces(tmp_path):
    _, manifest = write_test_manifest(
        tmp_path,
        series_order=["Topsoil"],
        mesh_filenames=[],
    )

    assert manifest["series_order"] == ["Topsoil"]
    assert manifest["surfaces"] == []


class IdentityTransform:
    def apply_inverse(self, vertices):
        return np.asarray(vertices)


def fake_gempy():
    geo_model = SimpleNamespace(input_transform=IdentityTransform())
    solution = SimpleNamespace(
        raw_arrays=SimpleNamespace(
            vertices=[
                np.asarray([
                    [0.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                ])
            ],
            edges=[np.asarray([[0, 1, 2]])],
            lith_block=np.asarray([1, 1, 1, 1]),
        )
    )
    return SimpleNamespace(
        data=SimpleNamespace(
            ImporterHelper=lambda **kwargs: SimpleNamespace(**kwargs)
        ),
        create_geomodel=lambda **kwargs: geo_model,
        map_stack_to_surfaces=lambda *args, **kwargs: None,
        compute_model=lambda model: solution,
    )


@pytest.mark.parametrize("make_meshes", [True, False])
def test_builder_writes_absolute_manifest_output_with_known_artifacts(
    tmp_path,
    monkeypatch,
    make_meshes,
):
    surface_name = "Layer / A? (north)"
    points_path = tmp_path / "points.csv"
    points_path.write_text(
        "X,Y,Z,surface,face\n"
        f"0,0,0,{surface_name},north\n"
        f"1,1,1,{surface_name},north\n"
    )
    orientations_path = tmp_path / "orientations.csv"
    orientations_path.write_text("X,Y,Z,surface\n")
    model_dir = tmp_path / "06_gempy_model"
    model_dir.mkdir()
    out_prefix = model_dir / "trench_model"
    monkeypatch.setitem(sys.modules, "gempy", fake_gempy())

    result = run_build(
        points_path,
        orientations_path,
        out_prefix,
        resolution=(2, 2, 1),
        extent=[0, 1, 0, 1, 0, 1],
        series_order=[surface_name],
        make_plot=False,
        make_meshes=make_meshes,
        save_model=False,
    )

    manifest_path = Path(result["outputs"]["viewer_manifest"])
    manifest = json.loads(manifest_path.read_text())

    assert manifest_path.is_absolute()
    assert manifest_path == model_dir / "trench_model_viewer.json"
    assert manifest["lith_block_path"] == "trench_model_lith_block.npz"
    assert manifest["surfaces"] == (
        [
            {
                "name": surface_name,
                "mesh_path": (
                    "trench_model_meshes/Layer_A_north.obj"
                ),
            }
        ]
        if make_meshes
        else []
    )
    expected_output_keys = {"lith_block", "viewer_manifest"}
    if make_meshes:
        expected_output_keys.add("meshes")
    assert set(result["outputs"]) == expected_output_keys
