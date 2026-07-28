import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from poggio_webapp.pipeline.build_gempy import (
    run_build,
    write_lithology_binary,
)


def test_write_lithology_binary_rejects_wrong_element_count(tmp_path):
    output_path = tmp_path / "lithology.bin"

    with pytest.raises(ValueError, match=r"element count.*24"):
        write_lithology_binary(
            np.arange(23),
            [2, 3, 4],
            output_path,
        )

    assert not output_path.exists()


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ([0, 1, np.nan, 3], "finite"),
        ([0, 1, np.inf, 3], "finite"),
        ([0, 1, -1, 3], "non-negative"),
        ([0, 1, 1.5, 3], "integers"),
    ],
)
def test_write_lithology_binary_rejects_invalid_values(
    tmp_path,
    values,
    message,
):
    output_path = tmp_path / "lithology.bin"

    with pytest.raises(ValueError, match=message):
        write_lithology_binary(values, [2, 2, 1], output_path)

    assert not output_path.exists()


def test_write_lithology_binary_rejects_values_above_uint16(tmp_path):
    output_path = tmp_path / "lithology.bin"

    with pytest.raises(ValueError, match="65535"):
        write_lithology_binary([0, 1, 65535, 65536], [2, 2, 1], output_path)

    assert not output_path.exists()


def test_write_lithology_binary_writes_exact_little_endian_uint16(tmp_path):
    output_path = tmp_path / "lithology.bin"

    write_lithology_binary(
        np.asarray([0, 1, 256, 65535], dtype=np.int64),
        [2, 2, 1],
        output_path,
    )

    assert output_path.read_bytes() == (
        b"\x00\x00"
        b"\x01\x00"
        b"\x00\x01"
        b"\xff\xff"
    )


def test_write_lithology_binary_returns_sorted_lithology_metadata(tmp_path):
    output_path = tmp_path / "lithology.bin"

    lithologies = write_lithology_binary(
        [7, 2, 7, 4],
        [2, 2, 1],
        output_path,
        lithology_names={
            2: "Fill",
            7: "Basement",
        },
    )

    assert lithologies == [
        {"id": 2, "name": "Fill"},
        {"id": 4, "name": "Lithology 4"},
        {"id": 7, "name": "Basement"},
    ]


def test_write_lithology_binary_preserves_c_order_for_non_cubic_grid(
    tmp_path,
):
    output_path = tmp_path / "lithology.bin"
    shape = (2, 3, 4)
    values = np.arange(np.prod(shape)).reshape(shape, order="C")

    write_lithology_binary(values, shape, output_path)

    decoded = np.frombuffer(output_path.read_bytes(), dtype="<u2").reshape(
        shape,
        order="C",
    )
    for x, y, z in np.ndindex(shape):
        expected = (x * shape[1] + y) * shape[2] + z
        assert decoded[x, y, z] == expected


class IdentityTransform:
    def apply_inverse(self, vertices):
        return np.asarray(vertices)


def fake_gempy():
    geo_model = SimpleNamespace(
        input_transform=IdentityTransform(),
        structural_frame=SimpleNamespace(
            volume_elements_enumerator=np.asarray([1, 2]),
            volume_elements_names=["Topsoil", "Basement"],
        ),
    )
    solution = SimpleNamespace(
        raw_arrays=SimpleNamespace(
            vertices=[],
            edges=[],
            lith_block=np.asarray([2, 1, 2, 1], dtype=np.int8),
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


def test_run_build_preserves_npz_and_adds_binary_and_manifest_metadata(
    tmp_path,
    monkeypatch,
):
    points_path = tmp_path / "points.csv"
    points_path.write_text(
        "X,Y,Z,surface,face\n"
        "0,0,0,Topsoil,north\n"
        "1,1,1,Topsoil,north\n"
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
        series_order=["Topsoil"],
        make_plot=False,
        make_meshes=False,
        save_model=False,
    )

    npz_path = Path(result["outputs"]["lith_block"])
    with np.load(npz_path, allow_pickle=False) as archive:
        assert archive.files == ["lith_block", "resolution", "extent"]
        np.testing.assert_array_equal(
            archive["lith_block"],
            np.asarray([2, 1, 2, 1], dtype=np.int8),
        )
        np.testing.assert_array_equal(
            archive["resolution"],
            np.asarray([2, 2, 1]),
        )
        np.testing.assert_array_equal(
            archive["extent"],
            np.asarray([0, 1, 0, 1, 0, 1]),
        )

    binary_path = Path(result["outputs"]["lith_block_binary"])
    assert binary_path == model_dir / "trench_model_lith_block.bin"
    assert np.frombuffer(binary_path.read_bytes(), dtype="<u2").tolist() == [
        2,
        1,
        2,
        1,
    ]

    manifest = json.loads(
        Path(result["outputs"]["viewer_manifest"]).read_text()
    )
    assert manifest["volume"] == {
        "schema_version": 1,
        "format": "raw",
        "dtype": "uint16-le",
        "layout": "C",
        "axes": ["x", "y", "z"],
        "shape": [2, 2, 1],
        "path": "trench_model_lith_block.bin",
        "lithologies": [
            {"id": 1, "name": "Topsoil"},
            {"id": 2, "name": "Basement"},
        ],
    }
