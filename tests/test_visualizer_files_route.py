import json
from pathlib import Path

import pytest

import storage
from app import app
from pipeline.canonical import canonicalize

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    app.config.update(TESTING=True)
    return app.test_client()


def _manual_calibration():
    return {
        "kind": "manual",
        "origin_px": [100.25, 200.5],
        "ref_px": [200.25, 200.5],
        "lowest_px": [100.25, 300.5],
        "ref_meters": 1.0,
        "px_per_m": 100.0,
    }


def _marker_calibration():
    return {
        "kind": "manual",
        "origin_px": [100, 200],
        "ref_px": [500, 195],
        "lowest_px": [100, 650.0],
        "ref_meters": 4.0,
        "px_per_m": 100.5,
    }


def _write_meta(job_dir, meta):
    (job_dir / "meta.json").write_text(json.dumps(meta))


def _viewer_manifest(*, surfaces=None, schema_version=1):
    return {
        "schema_version": schema_version,
        "kind": "gempy-surface-model",
        "coordinate_system": {
            "units": "m",
            "up_axis": "Z",
        },
        "extent": [0, 10, 0, 5, 90, 100],
        "resolution": [50, 50, 30],
        "series_order": [
            surface["name"]
            for surface in (
                surfaces
                if surfaces is not None
                else [
                    {
                        "name": "Topsoil",
                        "mesh_path": ("trench_model_meshes/Topsoil.obj"),
                    }
                ]
            )
        ],
        "single_face_note": None,
        "surfaces": (
            surfaces
            if surfaces is not None
            else [
                {
                    "name": "Topsoil",
                    "mesh_path": "trench_model_meshes/Topsoil.obj",
                }
            ]
        ),
        "lith_block_path": "trench_model_lith_block.npz",
    }


def _volume_manifest(**overrides):
    volume = {
        "schema_version": 1,
        "format": "raw",
        "dtype": "uint16-le",
        "layout": "C",
        "axes": ["x", "y", "z"],
        "shape": [50, 50, 30],
        "path": "trench_model_lith_block.bin",
        "lithologies": [
            {
                "id": 1,
                "name": "Lithology 1",
            },
            {
                "id": 2,
                "name": "Lithology 2",
            },
        ],
    }
    volume.update(overrides)
    return volume


def _write_manifest(job_dir, payload, relative_path=None):
    relative_path = relative_path or Path("06_gempy_model") / "trench_model_viewer.json"
    manifest_path = job_dir / relative_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload))
    return manifest_path


def _write_model_file(job_dir, relative_path):
    path = job_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"model artifact")
    return path


def test_manual_calibration_surfaced_under_calibration_key(client):
    job_id = "manual-calibration"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    image_path = job_dir / "manual.png"
    image_path.write_bytes(b"image")
    calibration = _manual_calibration()
    _write_meta(
        job_dir,
        {
            "manual_calibration": calibration,
            "manual_image_path": str(image_path),
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["calibration"] == calibration
    assert "marker_calib" not in payload
    assert payload["image_url"] == f"/api/jobs/{job_id}/file?path=manual.png"


def test_manual_calibration_omitted_without_matching_image(client):
    job_id = "missing-manual-image"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_meta(
        job_dir,
        {
            "manual_calibration": _manual_calibration(),
            "manual_image_path": str(job_dir / "missing.png"),
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert "calibration" not in payload
    assert "image_url" not in payload


def test_no_calibration_at_all_still_serves_image(client):
    job_id = "scan-without-calibration"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    _write_meta(job_dir, {"scan_path": str(scan_path)})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["image_url"] == f"/api/jobs/{job_id}/file?path=scan.png"
    assert "calibration" not in payload


def test_marker_calib_surfaced_under_calibration_key(client):
    job_id = "marker-calibration"
    job_dir = storage.JOBS_DIR / job_id
    extraction_dir = job_dir / "03_extraction"
    extraction_dir.mkdir(parents=True)
    rotated_path = extraction_dir / "marker_source_rotated.png"
    rotated_path.write_bytes(b"image")
    calibration = _marker_calibration()
    _write_meta(job_dir, {"marker_calib": calibration})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["calibration"] == calibration
    assert "marker_calib" not in payload
    assert (
        payload["image_url"] == f"/api/jobs/{job_id}/file?"
        "path=03_extraction/marker_source_rotated.png"
    )


def test_marker_calib_ignored_without_rotated_image(client):
    job_id = "marker-calibration-without-rotated-image"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = job_dir / "scan.png"
    scan_path.write_bytes(b"scan")
    _write_meta(
        job_dir,
        {
            "marker_calib": _marker_calibration(),
            "scan_path": str(scan_path),
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["image_url"] == f"/api/jobs/{job_id}/file?path=scan.png"
    assert "calibration" not in payload
    assert "marker_calib" not in payload


def test_no_model_keeps_existing_visualizer_payload_unchanged(client):
    job_id = "existing-two-dimensional-payload"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    scan_path = _write_model_file(job_dir, "scan.png")
    normalized_path = _write_model_file(job_dir, "normalized.json")
    extraction_path = _write_model_file(job_dir, "extraction.json")
    _write_meta(
        job_dir,
        {
            "sheet_type": "fieldwall",
            "scan_path": str(scan_path),
            "normalized_path": str(normalized_path),
            "extraction_path": str(extraction_path),
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json() == {
        "sheet_type": "fieldwall",
        "jsons": [
            {
                "label": "normalized",
                "url": (f"/api/jobs/{job_id}/file?path=normalized.json"),
            },
            {
                "label": "raw extraction",
                "url": (f"/api/jobs/{job_id}/file?path=extraction.json"),
            },
        ],
        "image_url": f"/api/jobs/{job_id}/file?path=scan.png",
    }


def _field_capture():
    return json.loads((FIXTURES / "t907-parity-fieldwall.json").read_text())


def test_canonical_is_listed_first_when_a_conventional_source_exists(client):
    """The visualizer auto-loads jsons[0], so listing the canonical form
    first is what retires the served-raw workaround: the client sees one
    shape for both mediums, and the legacy entries stay behind it for A/B
    compare."""
    job_id = "canonical-listing"
    job_dir = storage.JOBS_DIR / job_id
    normalize_dir = job_dir / "04_normalize_validate"
    normalize_dir.mkdir(parents=True)
    normalized_path = normalize_dir / "output_clean.json"
    normalized_path.write_text(json.dumps(_field_capture()))
    _write_meta(job_dir, {"normalized_path": str(normalized_path)})

    payload = client.get(f"/api/jobs/{job_id}/visualizer-files").get_json()

    assert [entry["label"] for entry in payload["jsons"]] == [
        "canonical",
        "normalized",
    ]
    assert payload["jsons"][0]["url"] == f"/api/jobs/{job_id}/canonical"


def test_canonical_endpoint_serves_the_artifact_when_present(client):
    """canonical.json carries the normalize step's dedupe passes, so the
    endpoint must serve it rather than re-canonicalize the legacy file."""
    job_id = "canonical-artifact"
    job_dir = storage.JOBS_DIR / job_id
    normalize_dir = job_dir / "04_normalize_validate"
    normalize_dir.mkdir(parents=True)
    (normalize_dir / "output_clean.json").write_text(json.dumps(_field_capture()))
    marked = _field_capture()
    marked["trenchLabel"] = "T-artifact"
    artifact, _warnings = canonicalize(marked)
    (normalize_dir / "canonical.json").write_text(json.dumps(artifact))
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/canonical")

    assert response.status_code == 200
    assert response.get_json() == artifact


def test_canonical_endpoint_canonicalizes_legacy_jobs_on_read(client):
    job_id = "canonical-on-read"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    (job_dir / "extraction_output.json").write_text(json.dumps(_field_capture()))
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/canonical")

    expected, _warnings = canonicalize(_field_capture())
    assert response.status_code == 200
    assert response.get_json() == expected


def test_canonical_endpoint_404s_with_nothing_to_serve(client):
    job_id = "canonical-empty"
    (storage.JOBS_DIR / job_id).mkdir()

    assert client.get(f"/api/jobs/{job_id}/canonical").status_code == 404
    assert client.get("/api/jobs/no-such-job/canonical").status_code == 404


def test_metadata_manifest_returns_model3d_with_job_file_urls(client):
    job_id = "metadata-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest_path = _write_manifest(
        job_dir,
        _viewer_manifest(),
        Path("custom_model") / "viewer.json",
    )
    _write_model_file(
        job_dir,
        "custom_model/trench_model_meshes/Topsoil.obj",
    )
    _write_model_file(
        job_dir,
        "custom_model/trench_model_lith_block.npz",
    )
    _write_meta(
        job_dir,
        {
            "model_outputs": {
                "viewer_manifest": str(manifest_path),
            },
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json()["model3d"] == {
        "schema_version": 1,
        "kind": "gempy-surface-model",
        "coordinate_system": {
            "units": "m",
            "up_axis": "Z",
        },
        "extent": [0, 10, 0, 5, 90, 100],
        "resolution": [50, 50, 30],
        "series_order": ["Topsoil"],
        "single_face_note": None,
        "surfaces": [
            {
                "name": "Topsoil",
                "url": (
                    f"/api/jobs/{job_id}/file?"
                    "path=custom_model/trench_model_meshes/Topsoil.obj"
                ),
            }
        ],
        "lith_block_url": (
            f"/api/jobs/{job_id}/file?path=custom_model/trench_model_lith_block.npz"
        ),
        "warnings": [],
    }


def test_conventional_manifest_survives_without_model_outputs(client):
    job_id = "conventional-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_manifest(job_dir, _viewer_manifest())
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_lith_block.npz",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json()["model3d"]["surfaces"][0]["url"] == (
        f"/api/jobs/{job_id}/file?path=06_gempy_model/trench_model_meshes/Topsoil.obj"
    )


def test_metadata_manifest_is_preferred_over_conventional_manifest(client):
    job_id = "preferred-metadata-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Conventional",
                    "mesh_path": "trench_model_meshes/Conventional.obj",
                }
            ]
        ),
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Conventional.obj",
    )
    metadata_manifest = _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Preferred",
                    "mesh_path": "meshes/Preferred.obj",
                }
            ]
        ),
        Path("preferred") / "viewer.json",
    )
    _write_model_file(job_dir, "preferred/meshes/Preferred.obj")
    _write_meta(
        job_dir,
        {
            "model_outputs": {
                "viewer_manifest": str(metadata_manifest),
            },
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json()["model3d"]["surfaces"] == [
        {
            "name": "Preferred",
            "url": (f"/api/jobs/{job_id}/file?path=preferred/meshes/Preferred.obj"),
        }
    ]


def test_missing_mesh_is_omitted_with_surface_warning(client):
    job_id = "partially-missing-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Present",
                    "mesh_path": "trench_model_meshes/Present.obj",
                },
                {
                    "name": "Missing",
                    "mesh_path": "trench_model_meshes/Missing.obj",
                },
            ]
        ),
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Present.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    model = response.get_json()["model3d"]
    assert [surface["name"] for surface in model["surfaces"]] == ["Present"]
    assert any("Missing" in warning for warning in model["warnings"])
    assert "mesh_path" not in json.dumps(model)


def test_manifest_with_no_existing_surfaces_omits_model3d(client):
    job_id = "model-without-surfaces"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Missing",
                    "mesh_path": "trench_model_meshes/Missing.obj",
                }
            ]
        ),
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert "model3d" not in response.get_json()


def test_missing_lith_block_keeps_surface_without_lith_url(client):
    job_id = "model-without-lith-block"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    _write_manifest(job_dir, _viewer_manifest())
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    model = response.get_json()["model3d"]
    assert len(model["surfaces"]) == 1
    assert "lith_block_url" not in model
    assert any("lithology" in warning.lower() for warning in model["warnings"])


def test_valid_volume_replaces_manifest_path_with_job_file_url(client):
    job_id = "model-with-volume"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest = _viewer_manifest()
    manifest["volume"] = _volume_manifest()
    _write_manifest(job_dir, manifest)
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_lith_block.bin",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    model = response.get_json()["model3d"]
    assert model["volume"] == {
        "schema_version": 1,
        "format": "raw",
        "dtype": "uint16-le",
        "layout": "C",
        "axes": ["x", "y", "z"],
        "shape": [50, 50, 30],
        "url": (
            f"/api/jobs/{job_id}/file?path=06_gempy_model/trench_model_lith_block.bin"
        ),
        "lithologies": [
            {
                "id": 1,
                "name": "Lithology 1",
            },
            {
                "id": 2,
                "name": "Lithology 2",
            },
        ],
    }
    assert '"path"' not in json.dumps(model["volume"])
    assert str(job_dir) not in response.get_data(as_text=True)


def test_missing_volume_binary_omits_volume_but_preserves_surfaces(client):
    job_id = "model-with-missing-volume"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest = _viewer_manifest()
    manifest["volume"] = _volume_manifest()
    _write_manifest(job_dir, manifest)
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    model = response.get_json()["model3d"]
    assert [surface["name"] for surface in model["surfaces"]] == ["Topsoil"]
    assert "volume" not in model


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("schema_version", 2),
        ("format", "npz"),
        ("dtype", "float32-le"),
        ("layout", "F"),
        ("axes", ["z", "y", "x"]),
        ("shape", [50, 50]),
        ("lithologies", [{"id": 1, "name": ""}]),
    ],
)
def test_malformed_or_unsupported_volume_is_omitted_safely(
    client,
    field,
    invalid_value,
):
    job_id = f"model-with-invalid-volume-{field}"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest = _viewer_manifest()
    manifest["volume"] = _volume_manifest(**{field: invalid_value})
    _write_manifest(job_dir, manifest)
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_lith_block.bin",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    model = response.get_json()["model3d"]
    assert [surface["name"] for surface in model["surfaces"]] == ["Topsoil"]
    assert "volume" not in model


def test_volume_path_traversal_is_rejected_without_exposing_a_path(
    client,
    tmp_path,
):
    job_id = "model-with-traversal-volume"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    outside_volume = tmp_path / "outside-volume.bin"
    outside_volume.write_bytes(b"\x01\x00")
    manifest = _viewer_manifest()
    manifest["volume"] = _volume_manifest(
        path="../../../outside-volume.bin",
    )
    _write_manifest(job_dir, manifest)
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    model = response.get_json()["model3d"]
    assert [surface["name"] for surface in model["surfaces"]] == ["Topsoil"]
    assert "volume" not in model
    assert str(outside_volume) not in body
    assert "outside-volume.bin" not in body


def test_malformed_manifest_does_not_break_two_dimensional_payload(client):
    job_id = "malformed-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest_path = job_dir / "06_gempy_model" / "trench_model_viewer.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text("{not valid json")
    scan_path = _write_model_file(job_dir, "scan.png")
    _write_meta(job_dir, {"scan_path": str(scan_path)})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json() == {
        "sheet_type": None,
        "jsons": [],
        "image_url": f"/api/jobs/{job_id}/file?path=scan.png",
    }


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("schema_version", 2),
        ("extent", "0,10,0,5,90,100"),
        ("resolution", [50, 50, 0]),
        ("coordinate_system", "Z-up metres"),
        ("series_order", "Topsoil"),
        ("surfaces", "Topsoil.obj"),
    ],
)
def test_unsupported_or_malformed_manifest_is_ignored(
    client,
    field,
    invalid_value,
):
    job_id = f"invalid-model-{field}"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    manifest = _viewer_manifest()
    manifest[field] = invalid_value
    _write_manifest(job_dir, manifest)
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Topsoil.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert "model3d" not in response.get_json()


def test_manifest_traversal_cannot_create_url_or_read_outside_job(
    client,
    tmp_path,
):
    job_id = "traversal-model"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    outside_mesh = tmp_path / "outside.obj"
    outside_mesh.write_text("v 0 0 0")
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Escaped",
                    "mesh_path": "../../../outside.obj",
                }
            ]
        ),
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "model3d" not in response.get_json()
    assert str(outside_mesh) not in body
    assert "outside.obj" not in body


def test_outside_metadata_manifest_is_ignored_for_conventional_fallback(
    client,
    tmp_path,
):
    job_id = "outside-metadata-manifest"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    outside_manifest = tmp_path / "outside-viewer.json"
    outside_manifest.write_text(json.dumps(_viewer_manifest()))
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": "Safe",
                    "mesh_path": "trench_model_meshes/Safe.obj",
                }
            ]
        ),
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/Safe.obj",
    )
    _write_meta(
        job_dir,
        {
            "model_outputs": {
                "viewer_manifest": str(outside_manifest),
            },
        },
    )

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.get_json()["model3d"]["surfaces"][0]["name"] == "Safe"


def test_surface_name_is_returned_only_as_json_data(client):
    job_id = "hostile-surface-name"
    job_dir = storage.JOBS_DIR / job_id
    job_dir.mkdir()
    surface_name = '<img src=x onerror="alert(1)">'
    _write_manifest(
        job_dir,
        _viewer_manifest(
            surfaces=[
                {
                    "name": surface_name,
                    "mesh_path": "trench_model_meshes/safe.obj",
                }
            ]
        ),
    )
    _write_model_file(
        job_dir,
        "06_gempy_model/trench_model_meshes/safe.obj",
    )
    _write_meta(job_dir, {})

    response = client.get(f"/api/jobs/{job_id}/visualizer-files")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json()["model3d"]["surfaces"][0]["name"] == surface_name
