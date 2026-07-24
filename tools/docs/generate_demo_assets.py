"""Generate small, sanitized documentation fixtures and source images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


SYNTHETIC_LABEL = "Synthetic documentation example"
IMAGE_SIZE = (960, 640)
PLOT_BOUNDS = (84, 112, 912, 558)
LOCAL_X_MAX_METERS = 5.0
LOCAL_DEPTH_MAX_METERS = 2.0
TITLE_FONT = ImageFont.load_default(size=20)
BODY_FONT = ImageFont.load_default(size=15)
SMALL_FONT = ImageFont.load_default(size=13)


def build_fieldwall_fixture() -> dict:
    """Return a synthetic fixture matching the current FieldWallProfile."""
    shared_boundary = [
        {"xMeters": 0.0, "depthMeters": 0.62, "confidence": "synthetic"},
        {"xMeters": 0.47, "depthMeters": 0.58, "confidence": "synthetic"},
        {"xMeters": 1.36, "depthMeters": 0.72, "confidence": "synthetic"},
        {"xMeters": 2.14, "depthMeters": 0.67, "confidence": "synthetic"},
        {"xMeters": 3.29, "depthMeters": 0.81, "confidence": "synthetic"},
        {"xMeters": 3.91, "depthMeters": 0.76, "confidence": "synthetic"},
        {"xMeters": 4.8, "depthMeters": 0.86, "confidence": "synthetic"},
    ]
    return {
        "trenchLabel": "DEMO-ASTER",
        "faceLabel": "Practice Face Zephyr",
        "illustrators": [],
        "date": "2000-01-01",
        "northArrowPresent": False,
        "gridSquareCm": 20.0,
        "gridTiePoints": [
            {"rawText": "DEMO-ORIGIN-A", "approxXMeters": 0.0},
            {"rawText": "DEMO-END-B", "approxXMeters": 4.8},
        ],
        "loci": [
            {
                "locusNumber": "DEMO-L1",
                "munsell": {
                    "raw": "10YR 5/4",
                    "colorName": "illustrative ochre",
                },
                "description": "Invented upper practice layer.",
                "confidence": "synthetic",
            },
            {
                "locusNumber": "DEMO-L2",
                "munsell": {
                    "raw": "7.5YR 4/3",
                    "colorName": "illustrative umber",
                },
                "description": "Invented lower practice layer.",
                "confidence": "synthetic",
            },
        ],
        "layers": [
            {
                "locusNumber": "DEMO-L1",
                "topBoundary": [
                    {
                        "xMeters": 0.0,
                        "depthMeters": 0.18,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 0.52,
                        "depthMeters": 0.14,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 1.41,
                        "depthMeters": 0.2,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 2.18,
                        "depthMeters": 0.17,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 3.36,
                        "depthMeters": 0.23,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 4.02,
                        "depthMeters": 0.19,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 4.8,
                        "depthMeters": 0.24,
                        "confidence": "synthetic",
                    },
                ],
                "bottomBoundary": shared_boundary,
                "featuresInLayer": [
                    {
                        "feature": "Synthetic rounded inclusion",
                        "description": (
                            "Invented internal feature for documentation only."
                        ),
                        "shapePoints": None,
                        "approxXMeters": 2.62,
                        "approxDepthMeters": 0.47,
                        "approxWidthMeters": 0.44,
                        "approxHeightMeters": 0.18,
                        "confidence": "synthetic",
                    }
                ],
            },
            {
                "locusNumber": "DEMO-L2",
                "topBoundary": shared_boundary,
                "bottomBoundary": [
                    {
                        "xMeters": 0.0,
                        "depthMeters": 1.3,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 0.71,
                        "depthMeters": 1.38,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 1.18,
                        "depthMeters": 1.31,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 2.37,
                        "depthMeters": 1.48,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 3.08,
                        "depthMeters": 1.4,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 4.21,
                        "depthMeters": 1.53,
                        "confidence": "synthetic",
                    },
                    {
                        "xMeters": 4.8,
                        "depthMeters": 1.46,
                        "confidence": "synthetic",
                    },
                ],
                "featuresInLayer": [],
            },
        ],
        "marginalia": [
            SYNTHETIC_LABEL,
            "All labels and local measurements on this sheet are invented.",
        ],
        "source": "manual_editor",
        "finds": [],
    }


def build_illustrator_fixture() -> dict:
    """Return a synthetic fixture matching the current ArchaeologicalDiagram."""
    shared_boundary = [
        {
            "xCoordinateMeters": 0.0,
            "yCoordinateMeters": 0.7,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 0.63,
            "yCoordinateMeters": 0.77,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 1.57,
            "yCoordinateMeters": 0.68,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 2.21,
            "yCoordinateMeters": 0.82,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 3.43,
            "yCoordinateMeters": 0.75,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 4.06,
            "yCoordinateMeters": 0.88,
            "confidence": "synthetic",
        },
        {
            "xCoordinateMeters": 4.8,
            "yCoordinateMeters": 0.8,
            "confidence": "synthetic",
        },
    ]
    return {
        "metadata": {
            "currentFilePath": "synthetic://docs/demo-illustrator.png",
            "suggestedFilename": "synthetic_demo_cobalt",
            "trenchLabel": "DEMO-COBALT",
            "scale": {
                "unit": "m",
                "valuesMarked": [0, 1, 2, 3, 4, 5],
                "metricConversionAssumption": None,
                "confidence": "synthetic metric scale",
            },
            "credits": {"attributions": [], "year": None},
            "marginalia": [
                SYNTHETIC_LABEL,
                "Invented labels and face-local coordinates only.",
            ],
        },
        "trenchProfiles": [
            {
                "face": "Practice Face Nimbus",
                "gridLabels": ["DEMO-A", "DEMO-C", "DEMO-F"],
                "gridLabelXMeters": [0.0, 2.08, 4.8],
                "layers": [
                    {
                        "layerName": "Demo Layer Cobalt",
                        "inferredMaterial": "synthetic stipple",
                        "description": "Invented upper band.",
                        "visualPattern": "sparse dots",
                        "featuresInLayer": [
                            {
                                "feature": "Synthetic lens",
                                "description": (
                                    "Invented internal outline for documentation."
                                ),
                                "shapePoints": [
                                    {
                                        "xCoordinateMeters": 2.58,
                                        "yCoordinateMeters": 0.48,
                                        "confidence": "synthetic",
                                    },
                                    {
                                        "xCoordinateMeters": 2.82,
                                        "yCoordinateMeters": 0.43,
                                        "confidence": "synthetic",
                                    },
                                    {
                                        "xCoordinateMeters": 3.13,
                                        "yCoordinateMeters": 0.5,
                                        "confidence": "synthetic",
                                    },
                                    {
                                        "xCoordinateMeters": 2.87,
                                        "yCoordinateMeters": 0.59,
                                        "confidence": "synthetic",
                                    },
                                ],
                                "approxXMeters": None,
                                "approxYMeters": None,
                                "approxWidthMeters": None,
                                "approxHeightMeters": None,
                                "confidence": "synthetic",
                            }
                        ],
                        "topBoundary": [
                            {
                                "xCoordinateMeters": 0.0,
                                "yCoordinateMeters": 0.15,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 0.54,
                                "yCoordinateMeters": 0.19,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 1.48,
                                "yCoordinateMeters": 0.13,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 2.33,
                                "yCoordinateMeters": 0.22,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 3.51,
                                "yCoordinateMeters": 0.17,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 4.17,
                                "yCoordinateMeters": 0.25,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 4.8,
                                "yCoordinateMeters": 0.2,
                                "confidence": "synthetic",
                            },
                        ],
                        "bottomBoundary": shared_boundary,
                    },
                    {
                        "layerName": "Demo Layer Saffron",
                        "inferredMaterial": "synthetic diagonal hatch",
                        "description": "Invented lower band.",
                        "visualPattern": "diagonal hatch",
                        "featuresInLayer": [],
                        "topBoundary": shared_boundary,
                        "bottomBoundary": [
                            {
                                "xCoordinateMeters": 0.0,
                                "yCoordinateMeters": 1.38,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 0.76,
                                "yCoordinateMeters": 1.3,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 1.26,
                                "yCoordinateMeters": 1.45,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 2.42,
                                "yCoordinateMeters": 1.36,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 3.14,
                                "yCoordinateMeters": 1.53,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 4.29,
                                "yCoordinateMeters": 1.42,
                                "confidence": "synthetic",
                            },
                            {
                                "xCoordinateMeters": 4.8,
                                "yCoordinateMeters": 1.5,
                                "confidence": "synthetic",
                            },
                        ],
                    },
                ],
            }
        ],
        "legend": [
            {"visualPattern": "sparse dots", "material": "Demo Layer Cobalt"},
            {
                "visualPattern": "diagonal hatch",
                "material": "Demo Layer Saffron",
            },
        ],
        "inferred_notes": [
            SYNTHETIC_LABEL,
            "Geometry is illustrative and has no archaeological interpretation.",
        ],
        "rawTranscription": (
            f"{SYNTHETIC_LABEL}. Two invented layers and one invented internal "
            "feature are shown."
        ),
        "source": "manual_editor",
        "finds": [],
    }


def _plot_point(x: float, depth: float) -> tuple[int, int]:
    left, top, right, bottom = PLOT_BOUNDS
    px = left + (x / LOCAL_X_MAX_METERS) * (right - left)
    py = top + (depth / LOCAL_DEPTH_MAX_METERS) * (bottom - top)
    return round(px), round(py)


def _fieldwall_points(points: list[dict] | None) -> list[tuple[int, int]]:
    return [
        _plot_point(point["xMeters"], point["depthMeters"])
        for point in (points or [])
        if point.get("xMeters") is not None
        and point.get("depthMeters") is not None
    ]


def _illustrator_points(points: list[dict] | None) -> list[tuple[int, int]]:
    return [
        _plot_point(
            point["xCoordinateMeters"],
            point["yCoordinateMeters"],
        )
        for point in (points or [])
        if point.get("xCoordinateMeters") is not None
        and point.get("yCoordinateMeters") is not None
    ]


def _new_image(subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", IMAGE_SIZE, "#fffdf7")
    draw = ImageDraw.Draw(image)
    draw.text((32, 20), SYNTHETIC_LABEL, fill="#1d3557", font=TITLE_FONT)
    draw.text((32, 50), subtitle, fill="#374151", font=BODY_FONT)
    draw.text(
        (32, 73),
        "Invented face-local coordinates (metres); not a site survey.",
        fill="#6b4f3a",
        font=SMALL_FONT,
    )

    left, top, right, bottom = PLOT_BOUNDS
    draw.rectangle(PLOT_BOUNDS, outline="#374151", width=2)
    for meter in range(6):
        x, _ = _plot_point(float(meter), 0.0)
        draw.line((x, bottom, x, bottom + 7), fill="#374151", width=1)
        draw.text(
            (x - 4, bottom + 12),
            str(meter),
            fill="#374151",
            font=SMALL_FONT,
        )
    for depth in (0.0, 0.5, 1.0, 1.5, 2.0):
        _, y = _plot_point(0.0, depth)
        draw.line((left - 7, y, left, y), fill="#374151", width=1)
        draw.text((42, y - 7), f"{depth:g}", fill="#374151", font=SMALL_FONT)
    draw.text((448, 598), "local x (m)", fill="#374151", font=SMALL_FONT)
    draw.text((10, 324), "depth", fill="#374151", font=SMALL_FONT)
    return image, draw


def _draw_boundaries(
    draw: ImageDraw.ImageDraw,
    layers: list[dict],
    point_reader,
    fills: tuple[str, ...],
) -> None:
    for index, layer in enumerate(layers):
        top = point_reader(layer.get("topBoundary"))
        bottom = point_reader(layer.get("bottomBoundary"))
        if top and bottom:
            draw.polygon(top + list(reversed(bottom)), fill=fills[index % len(fills)])
        if top:
            draw.line(top, fill="#263238", width=3)
            for point in top:
                draw.ellipse(
                    (point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3),
                    fill="#fffdf7",
                    outline="#263238",
                    width=1,
                )
        if bottom:
            draw.line(bottom, fill="#263238", width=3)
            for point in bottom:
                draw.ellipse(
                    (point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3),
                    fill="#fffdf7",
                    outline="#263238",
                    width=1,
                )


def _save_png(image: Image.Image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", compress_level=9, optimize=False)


def render_fieldwall_image(data: dict, output_path: Path) -> None:
    """Render a deterministic source image for a FieldWallProfile fixture."""
    image, draw = _new_image(
        f"{data['trenchLabel']} | {data['faceLabel']} | synthetic field wall"
    )
    layers = data.get("layers") or []
    _draw_boundaries(
        draw,
        layers,
        _fieldwall_points,
        ("#d9c7a3", "#c9b18b"),
    )

    for index, layer in enumerate(layers):
        draw.text(
            _plot_point(0.18, 0.39 + index * 0.72),
            str(layer.get("locusNumber") or f"layer {index + 1}"),
            fill="#1f2937",
            font=BODY_FONT,
        )
        for feature in layer.get("featuresInLayer") or []:
            x = feature.get("approxXMeters")
            y = feature.get("approxDepthMeters")
            width = feature.get("approxWidthMeters")
            height = feature.get("approxHeightMeters")
            if None not in (x, y, width, height):
                x0, y0 = _plot_point(x - width / 2, y - height / 2)
                x1, y1 = _plot_point(x + width / 2, y + height / 2)
                draw.ellipse(
                    (x0, y0, x1, y1),
                    fill="#f8f1df",
                    outline="#9c3d2e",
                    width=3,
                )
                draw.text(
                    (x1 + 7, y0),
                    "synthetic feature",
                    fill="#7f1d1d",
                    font=SMALL_FONT,
                )

    _save_png(image, output_path)


def render_illustrator_image(data: dict, output_path: Path) -> None:
    """Render a deterministic source image for an ArchaeologicalDiagram."""
    metadata = data.get("metadata") or {}
    profiles = data.get("trenchProfiles") or []
    profile = profiles[0] if profiles else {}
    image, draw = _new_image(
        f"{metadata.get('trenchLabel')} | {profile.get('face')} | synthetic diagram"
    )
    layers = profile.get("layers") or []
    _draw_boundaries(
        draw,
        layers,
        _illustrator_points,
        ("#c7dbe6", "#e5c891"),
    )

    for index, layer in enumerate(layers):
        draw.text(
            _plot_point(0.18, 0.42 + index * 0.7),
            str(layer.get("layerName") or f"layer {index + 1}"),
            fill="#1f2937",
            font=BODY_FONT,
        )
        for feature in layer.get("featuresInLayer") or []:
            points = _illustrator_points(feature.get("shapePoints"))
            if len(points) >= 3:
                draw.polygon(
                    points,
                    fill="#fff7cc",
                    outline="#9c3d2e",
                    width=3,
                )
                draw.text(
                    (min(x for x, _ in points), max(y for _, y in points) + 8),
                    "synthetic feature",
                    fill="#7f1d1d",
                    font=SMALL_FONT,
                )

    _save_png(image, output_path)


def _write_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_demo_assets(output_root: Path) -> list[Path]:
    """Write the four generated assets below a repository-like output root."""
    output_root = Path(output_root)
    fieldwall_data = build_fieldwall_fixture()
    illustrator_data = build_illustrator_fixture()
    paths = [
        output_root / "docs" / "fixtures" / "demo-fieldwall.json",
        output_root / "docs" / "fixtures" / "demo-illustrator.json",
        output_root / "docs" / "assets" / "source" / "demo-fieldwall.png",
        output_root / "docs" / "assets" / "source" / "demo-illustrator.png",
    ]
    _write_json(fieldwall_data, paths[0])
    _write_json(illustrator_data, paths[1])
    render_fieldwall_image(fieldwall_data, paths[2])
    render_illustrator_image(illustrator_data, paths[3])
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    """Generate assets at the repository root or an explicit output root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository-like root below which docs/ assets are written.",
    )
    args = parser.parse_args(argv)
    for path in write_demo_assets(args.output_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
