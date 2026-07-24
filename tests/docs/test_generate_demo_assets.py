from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "poggio_webapp"))

from pipeline import validator
from pipeline.extract_fieldwall import FieldWallProfile
from pipeline.extract_illustrator import ArchaeologicalDiagram
from tools.docs.generate_demo_assets import (
    SYNTHETIC_LABEL,
    build_fieldwall_fixture,
    build_illustrator_fixture,
    main,
    write_demo_assets,
)


BUILDERS = (build_fieldwall_fixture, build_illustrator_fixture)


def _features(data: dict) -> list[dict]:
    if "trenchProfiles" in data:
        layers = [
            layer
            for profile in data["trenchProfiles"]
            for layer in (profile.get("layers") or [])
        ]
    else:
        layers = data.get("layers") or []
    return [
        feature
        for layer in layers
        for feature in (layer.get("featuresInLayer") or [])
    ]


def _boundaries(data: dict) -> list[list[dict]]:
    if "trenchProfiles" in data:
        layers = [
            layer
            for profile in data["trenchProfiles"]
            for layer in (profile.get("layers") or [])
        ]
    else:
        layers = data.get("layers") or []
    return [
        points
        for layer in layers
        for key in ("topBoundary", "bottomBoundary")
        if (points := layer.get(key))
    ]


def _normalized_real_trench_names() -> set[str]:
    names = set()
    for path in (REPO_ROOT / "01_scans").iterdir():
        for match in re.finditer(
            r"(?:trench[\W_]*\d+|t\d{2,})",
            path.stem,
            flags=re.IGNORECASE,
        ):
            names.add(re.sub(r"[^a-z0-9]", "", match.group(0).lower()))
    return names


def test_fieldwall_fixture_validates_against_current_model() -> None:
    fixture = build_fieldwall_fixture()

    assert FieldWallProfile.model_validate(fixture).model_dump() == fixture


def test_illustrator_fixture_validates_against_current_model() -> None:
    fixture = build_illustrator_fixture()

    assert ArchaeologicalDiagram.model_validate(fixture).model_dump() == fixture


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_produces_zero_validator_errors(builder) -> None:
    report = validator.validate(builder())

    assert report.errors == []
    assert report.warnings == []


def test_fieldwall_fixture_has_two_loci_and_two_layers() -> None:
    fixture = build_fieldwall_fixture()

    assert len(fixture["loci"]) >= 2
    assert len(fixture["layers"]) >= 2


def test_illustrator_fixture_has_two_layers() -> None:
    fixture = build_illustrator_fixture()
    layers = [
        layer
        for profile in fixture["trenchProfiles"]
        for layer in profile["layers"]
    ]

    assert len(layers) >= 2


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_has_an_internal_feature(builder) -> None:
    assert _features(builder())


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_boundary_spacing_is_irregular(builder) -> None:
    for points in _boundaries(builder()):
        x_key = "xMeters" if "xMeters" in points[0] else "xCoordinateMeters"
        deltas = [
            round(right[x_key] - left[x_key], 3)
            for left, right in zip(points, points[1:])
        ]
        assert len(set(deltas)) >= 3


def test_generator_output_is_byte_identical_across_directories(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first_paths = write_demo_assets(first_root)
    second_paths = write_demo_assets(second_root)
    first_bytes = {
        path.relative_to(first_root): path.read_bytes() for path in first_paths
    }
    second_bytes = {
        path.relative_to(second_root): path.read_bytes() for path in second_paths
    }

    assert first_bytes == second_bytes


@pytest.mark.parametrize(
    "relative_path",
    (
        Path("docs/assets/source/demo-fieldwall.png"),
        Path("docs/assets/source/demo-illustrator.png"),
    ),
)
def test_generated_images_are_nonempty_png_files(
    tmp_path: Path,
    relative_path: Path,
) -> None:
    write_demo_assets(tmp_path)
    image_path = tmp_path / relative_path

    assert image_path.stat().st_size > 0
    with Image.open(image_path) as image:
        assert image.format == "PNG"
        assert image.width > 0
        assert image.height > 0
        image.verify()


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_text_contains_synthetic_example_label(builder) -> None:
    assert SYNTHETIC_LABEL in json.dumps(builder(), sort_keys=True)


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_values_exclude_known_real_trench_names(builder) -> None:
    known_names = _normalized_real_trench_names()
    fixture_text = re.sub(
        r"[^a-z0-9]",
        "",
        json.dumps(builder(), sort_keys=True).lower(),
    )

    assert known_names
    assert all(name not in fixture_text for name in known_names)


@pytest.mark.parametrize("builder", BUILDERS)
def test_fixture_coordinates_are_small_and_face_local(builder) -> None:
    coordinate_keys = {
        "xMeters",
        "depthMeters",
        "xCoordinateMeters",
        "yCoordinateMeters",
        "approxXMeters",
        "approxDepthMeters",
        "approxYMeters",
        "gridLabelXMeters",
    }
    values = []

    def collect(value, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                collect(child_value, child_key)
        elif isinstance(value, list):
            for child in value:
                collect(child, key)
        elif key in coordinate_keys and isinstance(value, (int, float)):
            values.append(value)

    collect(builder())

    assert values
    assert all(0.0 <= value <= 5.0 for value in values)


def test_main_writes_all_four_assets(tmp_path: Path) -> None:
    assert main(["--output-root", str(tmp_path)]) == 0
    assert {
        path.relative_to(tmp_path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    } == {
        Path("docs/fixtures/demo-fieldwall.json"),
        Path("docs/fixtures/demo-illustrator.json"),
        Path("docs/assets/source/demo-fieldwall.png"),
        Path("docs/assets/source/demo-illustrator.png"),
    }


def test_checked_in_assets_match_generator(tmp_path: Path) -> None:
    generated_paths = write_demo_assets(tmp_path)

    for generated_path in generated_paths:
        relative_path = generated_path.relative_to(tmp_path)
        assert generated_path.read_bytes() == (REPO_ROOT / relative_path).read_bytes()
