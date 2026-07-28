"""Conservative, reviewable suggestions for Harris Matrix workspaces."""

import hashlib
import math
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .harris_import import load_source_document
from .harris_matrix import (
    HarrisCorrelation,
    HarrisMatrix,
    HarrisRelation,
    HarrisSuggestion,
    SourceRef,
    correlation_components,
    validate_matrix_graph,
)


_GENERIC_LABEL = re.compile(
    r"(?:Polygon|Unlabeled layer)\s+\d+",
    re.IGNORECASE,
)
_ORDERING_REASON = (
    "Consecutive source layers share a recorded boundary."
)
_CORRELATION_REASON = (
    "Matching normalized labels appear in different jobs or faces."
)


class HarrisSuggestionError(ValueError):
    """Raised when a suggestion cannot be generated or reviewed safely."""


def _hash_suffix(*parts: str) -> str:
    identity = "|".join(parts)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def _suggestion_id(suggestion_type: str, *unit_ids: str) -> str:
    return (
        "suggestion-"
        f"{_hash_suffix(suggestion_type, *unit_ids)}"
    )


def _relation_id(suggestion_id: str) -> str:
    return f"rel-{_hash_suffix('suggestion', suggestion_id)}"


def _correlation_id(unit_ids: list[str]) -> str:
    return f"corr-{_hash_suffix('correlation', *sorted(unit_ids))}"


def _source_ref_key(source_ref: SourceRef) -> tuple:
    return (
        source_ref.job_id,
        source_ref.schema_type,
        source_ref.face,
        source_ref.layer_index,
        source_ref.source_label is None,
        source_ref.source_label or "",
    )


def _unique_source_refs(source_refs) -> list[SourceRef]:
    refs_by_key = {
        _source_ref_key(source_ref): source_ref
        for source_ref in source_refs
    }
    return [
        refs_by_key[key].model_copy(deep=True)
        for key in sorted(refs_by_key)
    ]


def _clean_face(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _layer_for_ref(document: dict, source_ref: SourceRef) -> dict | None:
    if source_ref.schema_type == "FieldWallProfile":
        if _clean_face(document.get("faceLabel")) != source_ref.face:
            return None
        layers = document.get("layers")
        if not isinstance(layers, list):
            return None
        if source_ref.layer_index >= len(layers):
            return None
        layer = layers[source_ref.layer_index]
        return layer if isinstance(layer, dict) else None

    profiles = document.get("trenchProfiles")
    if not isinstance(profiles, list):
        return None
    for profile in profiles:
        if (
            not isinstance(profile, dict)
            or _clean_face(profile.get("face")) != source_ref.face
        ):
            continue
        layers = profile.get("layers")
        if (
            not isinstance(layers, list)
            or source_ref.layer_index >= len(layers)
        ):
            continue
        layer = layers[source_ref.layer_index]
        if isinstance(layer, dict):
            return layer
    return None


def _finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _point_coordinates(point) -> tuple[float, float] | None:
    if not isinstance(point, dict):
        return None
    for x_key, y_key in (
        ("xMeters", "depthMeters"),
        ("xCoordinateMeters", "yCoordinateMeters"),
    ):
        x = point.get(x_key)
        y = point.get(y_key)
        if _finite_number(x) and _finite_number(y):
            return float(x), float(y)
    return None


def _boundary_coordinates(boundary) -> list[tuple[float, float]] | None:
    if not isinstance(boundary, list) or len(boundary) < 2:
        return None
    coordinates = []
    for point in boundary:
        coordinate = _point_coordinates(point)
        if coordinate is None:
            return None
        coordinates.append(coordinate)
    return sorted(coordinates)


def _boundaries_match(upper_boundary, lower_boundary, tolerance_m) -> bool:
    upper_points = _boundary_coordinates(upper_boundary)
    lower_points = _boundary_coordinates(lower_boundary)
    if (
        upper_points is None
        or lower_points is None
        or len(upper_points) != len(lower_points)
    ):
        return False
    return all(
        abs(upper_x - lower_x) <= tolerance_m
        and abs(upper_y - lower_y) <= tolerance_m
        for (upper_x, upper_y), (lower_x, lower_y) in zip(
            upper_points,
            lower_points,
        )
    )


def _ordering_suggestions(
    matrix: HarrisMatrix,
    jobs_dir: Path,
    tolerance_m: float,
) -> list[HarrisSuggestion]:
    units_by_occurrence = defaultdict(list)
    for unit in matrix.units:
        for source_ref in unit.source_refs:
            occurrence = (
                source_ref.job_id,
                source_ref.schema_type,
                source_ref.face,
                source_ref.layer_index,
            )
            units_by_occurrence[occurrence].append((unit, source_ref))

    documents = {}
    suggestions_by_id = {}
    for occurrence in sorted(units_by_occurrence):
        job_id, schema_type, face, layer_index = occurrence
        lower_occurrence = (
            job_id,
            schema_type,
            face,
            layer_index + 1,
        )
        if lower_occurrence not in units_by_occurrence:
            continue

        document = documents.get(job_id)
        if document is None:
            document, _path = load_source_document(job_id, jobs_dir)
            documents[job_id] = document

        for upper_unit, upper_ref in sorted(
            units_by_occurrence[occurrence],
            key=lambda item: item[0].id,
        ):
            upper_layer = _layer_for_ref(document, upper_ref)
            if upper_layer is None:
                continue
            for lower_unit, lower_ref in sorted(
                units_by_occurrence[lower_occurrence],
                key=lambda item: item[0].id,
            ):
                if upper_unit.id == lower_unit.id:
                    continue
                lower_layer = _layer_for_ref(document, lower_ref)
                if lower_layer is None or not _boundaries_match(
                    upper_layer.get("bottomBoundary"),
                    lower_layer.get("topBoundary"),
                    tolerance_m,
                ):
                    continue

                suggestion_id = _suggestion_id(
                    "ordering",
                    upper_unit.id,
                    lower_unit.id,
                )
                existing = suggestions_by_id.get(suggestion_id)
                source_refs = [upper_ref, lower_ref]
                if existing is not None:
                    source_refs.extend(existing.source_refs)
                suggestions_by_id[suggestion_id] = HarrisSuggestion(
                    id=suggestion_id,
                    suggestion_type="ordering",
                    status="pending",
                    younger_id=upper_unit.id,
                    older_id=lower_unit.id,
                    relation_kind="above",
                    correlation_unit_ids=[],
                    reason=_ORDERING_REASON,
                    source_refs=_unique_source_refs(source_refs),
                )

    return list(suggestions_by_id.values())


def _normalized_label(label: str) -> str | None:
    normalized = label.strip()
    if not normalized or _GENERIC_LABEL.fullmatch(normalized):
        return None
    return normalized.casefold()


def _different_jobs_or_faces(first, second) -> bool:
    return any(
        (
            first_ref.job_id != second_ref.job_id
            or first_ref.face != second_ref.face
        )
        for first_ref in first.source_refs
        for second_ref in second.source_refs
    )


def _correlation_suggestions(
    matrix: HarrisMatrix,
) -> list[HarrisSuggestion]:
    units_by_label = defaultdict(list)
    for unit in matrix.units:
        normalized_label = _normalized_label(unit.label)
        if normalized_label is not None:
            units_by_label[normalized_label].append(unit)

    components = correlation_components(matrix)
    suggestions = []
    for normalized_label in sorted(units_by_label):
        units = sorted(
            units_by_label[normalized_label],
            key=lambda unit: unit.id,
        )
        for first, second in combinations(units, 2):
            if (
                not _different_jobs_or_faces(first, second)
                or components.get(first.id) == components.get(second.id)
            ):
                continue
            unit_ids = sorted([first.id, second.id])
            suggestions.append(
                HarrisSuggestion(
                    id=_suggestion_id("correlation", *unit_ids),
                    suggestion_type="correlation",
                    status="pending",
                    younger_id=None,
                    older_id=None,
                    relation_kind=None,
                    correlation_unit_ids=unit_ids,
                    reason=_CORRELATION_REASON,
                    source_refs=_unique_source_refs(
                        first.source_refs + second.source_refs
                    ),
                )
            )
    return suggestions


def _validate_tolerance(tolerance_m) -> float:
    if not _finite_number(tolerance_m) or tolerance_m < 0:
        raise HarrisSuggestionError(
            "Boundary tolerance must be a finite, non-negative number."
        )
    return float(tolerance_m)


def generate_suggestions(
    matrix: HarrisMatrix,
    jobs_dir: Path,
    tolerance_m: float = 0.02,
) -> HarrisMatrix:
    """Return a copy containing deterministic, unaccepted suggestions."""
    tolerance_m = _validate_tolerance(tolerance_m)
    generated = _ordering_suggestions(matrix, jobs_dir, tolerance_m)
    generated.extend(_correlation_suggestions(matrix))

    existing_by_id = {
        suggestion.id: suggestion
        for suggestion in matrix.suggestions
    }
    suggestions_by_id = {
        suggestion.id: suggestion.model_copy(deep=True)
        for suggestion in matrix.suggestions
    }
    for suggestion in generated:
        previous = existing_by_id.get(suggestion.id)
        if previous is not None:
            suggestion.status = previous.status
        suggestions_by_id[suggestion.id] = suggestion

    result = matrix.model_copy(deep=True)
    result.suggestions = [
        suggestions_by_id[suggestion_id]
        for suggestion_id in sorted(suggestions_by_id)
    ]
    return result


def _accept_ordering(
    matrix: HarrisMatrix,
    suggestion: HarrisSuggestion,
) -> None:
    relation = HarrisRelation(
        id=_relation_id(suggestion.id),
        younger_id=suggestion.younger_id,
        older_id=suggestion.older_id,
        kind=suggestion.relation_kind,
        evidence=suggestion.reason,
        source="suggestion",
        notes=None,
    )
    existing = next(
        (
            item
            for item in matrix.relations
            if item.id == relation.id
        ),
        None,
    )
    if existing is None:
        matrix.relations.append(relation)
    elif existing != relation:
        raise HarrisSuggestionError(
            f"Cannot accept suggestion {suggestion.id}: generated "
            f"relation ID {relation.id} is already in use."
        )


def _accept_correlation(
    matrix: HarrisMatrix,
    suggestion: HarrisSuggestion,
) -> None:
    target_ids = set(suggestion.correlation_unit_ids)
    matched = [
        correlation
        for correlation in matrix.correlations
        if target_ids.intersection(correlation.unit_ids)
    ]
    merged_ids = set(target_ids)
    for correlation in matched:
        merged_ids.update(correlation.unit_ids)

    if matched:
        retained = min(matched, key=lambda correlation: correlation.id)
        retained.unit_ids = sorted(merged_ids)
        matched_ids = {
            correlation.id
            for correlation in matched
            if correlation.id != retained.id
        }
        matrix.correlations = [
            correlation
            for correlation in matrix.correlations
            if correlation.id not in matched_ids
        ]
        return

    correlation = HarrisCorrelation(
        id=_correlation_id(suggestion.correlation_unit_ids),
        unit_ids=sorted(merged_ids),
        notes=None,
    )
    existing = next(
        (
            item
            for item in matrix.correlations
            if item.id == correlation.id
        ),
        None,
    )
    if existing is None:
        matrix.correlations.append(correlation)
    elif existing != correlation:
        raise HarrisSuggestionError(
            f"Cannot accept suggestion {suggestion.id}: generated "
            f"correlation ID {correlation.id} is already in use."
        )


def _acceptance_error(
    suggestion: HarrisSuggestion,
    report: dict,
) -> HarrisSuggestionError:
    details = "; ".join(
        f"{issue['code']}: {issue['message']}"
        for issue in report["errors"]
    )
    return HarrisSuggestionError(
        f"Cannot accept suggestion {suggestion.id}: {details}"
    )


def review_suggestion(
    matrix: HarrisMatrix,
    suggestion_id: str,
    action: str,
) -> HarrisMatrix:
    """Accept or reject one suggestion without mutating the input matrix."""
    if (
        not isinstance(action, str)
        or action not in {"accept", "reject"}
    ):
        raise HarrisSuggestionError(
            "Suggestion action must be exactly 'accept' or 'reject'."
        )

    suggestion_index = next(
        (
            index
            for index, suggestion in enumerate(matrix.suggestions)
            if suggestion.id == suggestion_id
        ),
        None,
    )
    if suggestion_index is None:
        raise HarrisSuggestionError(
            f"Unknown suggestion ID: {suggestion_id}."
        )

    reviewed = matrix.model_copy(deep=True)
    suggestion = reviewed.suggestions[suggestion_index]

    if action == "reject":
        if suggestion.status == "accepted":
            raise HarrisSuggestionError(
                f"Suggestion {suggestion.id} is already accepted and "
                "cannot be rejected."
            )
        suggestion.status = "rejected"
        return reviewed

    if suggestion.status == "accepted":
        return reviewed

    if suggestion.suggestion_type == "ordering":
        _accept_ordering(reviewed, suggestion)
    else:
        _accept_correlation(reviewed, suggestion)
    suggestion.status = "accepted"

    report = validate_matrix_graph(reviewed)
    if not report["ok"]:
        raise _acceptance_error(suggestion, report)
    return reviewed
