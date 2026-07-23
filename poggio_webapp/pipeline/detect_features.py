"""Computer-vision proposals for discrete features in trench drawings.

This detector intentionally does not claim that every closed contour is a
stone. It proposes compact, closed shapes that may represent stones, cuts,
lenses, voids, or other discrete features. A person approves, rejects, and
labels each proposal before extraction. The confirmed list is then treated as
the feature inventory for the extraction prompt.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np


MAX_ANALYSIS_DIM = 2200
MAX_CANDIDATES = 250


def _read_image(image_path: str) -> np.ndarray:
    """Read an image from disk and raise a useful error if it fails."""
    img = cv2.imread(
        image_path,
        cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_COLOR,
    )

    if img is None:
        raise RuntimeError(f"Could not read image: {image_path}")

    return img


def _analysis_copy(img: np.ndarray) -> tuple[np.ndarray, float]:
    """Return a resized analysis image and its scale relative to the original."""
    height, width = img.shape[:2]
    longest_side = max(width, height)

    if longest_side <= MAX_ANALYSIS_DIM:
        return img.copy(), 1.0

    scale = MAX_ANALYSIS_DIM / longest_side

    resized = cv2.resize(
        img,
        (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        ),
        interpolation=cv2.INTER_AREA,
    )

    return resized, scale


def _iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Calculate intersection-over-union for two feature bounding boxes."""
    ax1 = float(a["x"])
    ay1 = float(a["y"])
    ax2 = ax1 + float(a["width"])
    ay2 = ay1 + float(a["height"])

    bx1 = float(b["x"])
    by1 = float(b["y"])
    bx2 = bx1 + float(b["width"])
    by2 = by1 + float(b["height"])

    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)

    intersection_width = max(0.0, intersection_x2 - intersection_x1)
    intersection_height = max(0.0, intersection_y2 - intersection_y1)
    intersection = intersection_width * intersection_height

    if intersection <= 0:
        return 0.0

    area_a = float(a["width"]) * float(a["height"])
    area_b = float(b["width"]) * float(b["height"])
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Suppress nested or overlapping contours representing the same object."""
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            float(candidate["score"]),
            float(candidate["area_px"]),
        ),
        reverse=True,
    )

    kept: list[dict[str, Any]] = []

    for candidate in ordered:
        candidate_center_x = (
            float(candidate["x"]) + float(candidate["width"]) / 2
        )
        candidate_center_y = (
            float(candidate["y"]) + float(candidate["height"]) / 2
        )

        duplicate = False

        for existing in kept:
            existing_center_x = (
                float(existing["x"]) + float(existing["width"]) / 2
            )
            existing_center_y = (
                float(existing["y"]) + float(existing["height"]) / 2
            )

            center_distance = math.hypot(
                candidate_center_x - existing_center_x,
                candidate_center_y - existing_center_y,
            )

            center_threshold = 0.18 * min(
                float(candidate["width"]) + float(candidate["height"]),
                float(existing["width"]) + float(existing["height"]),
            )

            overlap = _iou(candidate, existing)
            close_centers = center_distance < center_threshold

            if overlap >= 0.68 or (close_centers and overlap >= 0.35):
                duplicate = True
                break

        if not duplicate:
            kept.append(candidate)

        if len(kept) >= MAX_CANDIDATES:
            break

    return kept


def run_detect(
    image_path: str,
    out_dir: str,
    min_area_fraction: float = 0.000018,
    max_area_fraction: float = 0.035,
) -> dict[str, Any]:
    """Propose compact closed contours as reviewable feature candidates."""
    os.makedirs(out_dir, exist_ok=True)

    original = _read_image(image_path)
    analysis, scale = _analysis_copy(original)

    analysis_height, analysis_width = analysis.shape[:2]
    image_area = float(analysis_width * analysis_height)

    gray = cv2.cvtColor(analysis, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # Canny identifies ink boundaries while avoiding most paper-background
    # variation. Closing repairs small gaps in hand-drawn feature outlines.
    median_intensity = float(np.median(gray))
    lower_threshold = int(max(20, 0.55 * median_intensity))
    upper_threshold = int(
        min(
            255,
            max(lower_threshold + 30, 1.25 * median_intensity),
        )
    )

    edges = cv2.Canny(
        gray,
        lower_threshold,
        upper_threshold,
    )

    closing_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3),
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        closing_kernel,
        iterations=1,
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    min_area = max(
        55.0,
        image_area * float(min_area_fraction),
    )
    max_area = image_area * float(max_area_fraction)

    raw_candidates: list[dict[str, Any]] = []

    for contour in contours:
        area = abs(float(cv2.contourArea(contour)))
        perimeter = float(cv2.arcLength(contour, True))

        if area < min_area or area > max_area or perimeter <= 0:
            continue

        x, y, width, height = cv2.boundingRect(contour)

        if width < 10 or height < 10:
            continue

        if width > 0.34 * analysis_width:
            continue

        if height > 0.34 * analysis_height:
            continue

        if (
            x <= 2
            or y <= 2
            or x + width >= analysis_width - 2
            or y + height >= analysis_height - 2
        ):
            continue

        aspect_ratio = width / height

        if aspect_ratio < 0.16 or aspect_ratio > 6.2:
            continue

        convex_hull = cv2.convexHull(contour)
        hull_area = abs(float(cv2.contourArea(convex_hull)))

        solidity = area / hull_area if hull_area > 0 else 0.0
        extent = area / float(width * height)
        circularity = (
            4.0 * math.pi * area / (perimeter * perimeter)
        )

        # Layer boundaries and grid lines generally have low extent or
        # solidity. Small text loops are mostly removed by size limits.
        if solidity < 0.34 or extent < 0.09:
            continue

        compactness = min(
            1.0,
            max(0.0, circularity),
        )

        score = (
            0.45 * compactness
            + 0.35 * min(1.0, solidity)
            + 0.20 * min(1.0, extent)
        )

        if score < 0.28:
            continue

        epsilon = 0.012 * perimeter
        approximated_contour = cv2.approxPolyDP(
            contour,
            epsilon,
            True,
        )

        inverse_scale = 1.0 / scale

        points = [
            [
                round(float(point[0][0]) * inverse_scale, 1),
                round(float(point[0][1]) * inverse_scale, 1),
            ]
            for point in approximated_contour[:80]
        ]

        suggested_type = (
            "rock/stone"
            if compactness >= 0.24 and 0.35 <= aspect_ratio <= 2.8
            else "other feature"
        )

        raw_candidates.append(
            {
                "x": round(x * inverse_scale, 1),
                "y": round(y * inverse_scale, 1),
                "width": round(width * inverse_scale, 1),
                "height": round(height * inverse_scale, 1),
                "area_px": round(
                    area * inverse_scale * inverse_scale,
                    1,
                ),
                "circularity": round(circularity, 3),
                "solidity": round(solidity, 3),
                "score": round(score, 3),
                "points": points,
                "suggested_type": suggested_type,
                "feature_type": suggested_type,
                "status": "pending",
                "source": "cv",
            }
        )

    candidates = _dedupe(raw_candidates)
    candidates.sort(
        key=lambda candidate: (
            float(candidate["y"]),
            float(candidate["x"]),
        )
    )

    for index, candidate in enumerate(candidates):
        candidate["id"] = index
        candidate["display_id"] = index + 1

    debug_image = original.copy()

    for candidate in candidates:
        x = int(round(float(candidate["x"])))
        y = int(round(float(candidate["y"])))
        width = int(round(float(candidate["width"])))
        height = int(round(float(candidate["height"])))

        cv2.rectangle(
            debug_image,
            (x, y),
            (x + width, y + height),
            (0, 180, 255),
            3,
        )

        cv2.putText(
            debug_image,
            str(candidate["display_id"]),
            (x, max(18, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 100, 220),
            2,
            cv2.LINE_AA,
        )

    debug_path = str(
        Path(out_dir) / "feature_candidates.png"
    )

    if not cv2.imwrite(debug_path, debug_image):
        raise RuntimeError(
            f"Could not write feature debug image: {debug_path}"
        )

    return {
        "features": candidates,
        "debug_image": debug_path,
        "image_width": int(original.shape[1]),
        "image_height": int(original.shape[0]),
        "candidate_count": len(candidates),
    }


def write_review_overlay(
    image_path: str,
    features: list[dict[str, Any]],
    out_path: str,
) -> str:
    """Write numbered boxes for the human-confirmed feature inventory."""
    image = _read_image(image_path)

    output_parent = Path(out_path).parent
    output_parent.mkdir(parents=True, exist_ok=True)

    for index, feature in enumerate(features):
        status = str(feature.get("status", "approved")).lower()

        if status == "rejected":
            continue

        x = int(round(float(feature["x"])))
        y = int(round(float(feature["y"])))
        width = int(round(float(feature["width"])))
        height = int(round(float(feature["height"])))

        feature_type = str(
            feature.get("feature_type")
            or feature.get("suggested_type")
            or "feature"
        )

        cv2.rectangle(
            image,
            (x, y),
            (x + width, y + height),
            (50, 150, 50),
            4,
        )

        label = f"F{index + 1}: {feature_type}"

        cv2.putText(
            image,
            label,
            (x, max(24, y - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (35, 105, 35),
            2,
            cv2.LINE_AA,
        )

    if not cv2.imwrite(out_path, image):
        raise RuntimeError(
            f"Could not write reviewed feature overlay: {out_path}"
        )

    return out_path