"""Versioned persisted-data models for Harris Matrix workspaces."""

import heapq
import re
from collections import defaultdict
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

MatrixId = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{12}$"),
]
UnitId = Annotated[
    str,
    StringConstraints(pattern=r"^unit-[0-9a-f]{12}$"),
]
RelationId = Annotated[
    str,
    StringConstraints(pattern=r"^rel-[0-9a-f]{12}$"),
]
CorrelationId = Annotated[
    str,
    StringConstraints(pattern=r"^corr-[0-9a-f]{12}$"),
]
SuggestionId = Annotated[
    str,
    StringConstraints(pattern=r"^suggestion-[0-9a-f]{12}$"),
]
HumanText = Annotated[str, StringConstraints(strip_whitespace=True)]
UnitLabel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
NonNegativeInteger = Annotated[int, Field(strict=True, ge=0)]

UnitType = Literal[
    "deposit",
    "cut",
    "structure",
    "interface",
    "natural",
    "unknown",
]
RelationKind = Literal["above", "cuts", "fills", "precedes", "other"]
RelationSource = Literal["manual", "suggestion"]
SuggestionType = Literal["ordering", "correlation"]
SuggestionStatus = Literal["pending", "accepted", "rejected"]
SourceSchemaType = Literal["FieldWallProfile", "ArchaeologicalDiagram"]


class _HarrisModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(_HarrisModel):
    job_id: MatrixId
    schema_type: SourceSchemaType
    face: HumanText
    layer_index: NonNegativeInteger
    source_label: str | None


class HarrisUnit(_HarrisModel):
    id: UnitId
    label: UnitLabel
    unit_type: UnitType
    description: HumanText | None
    source_refs: list[SourceRef]


class HarrisRelation(_HarrisModel):
    id: RelationId
    younger_id: UnitId
    older_id: UnitId
    kind: RelationKind
    evidence: HumanText
    source: RelationSource
    notes: HumanText | None


class HarrisCorrelation(_HarrisModel):
    id: CorrelationId
    unit_ids: list[UnitId]
    notes: HumanText | None

    @model_validator(mode="after")
    def require_distinct_units(self):
        if len(set(self.unit_ids)) < 2:
            raise ValueError(
                "A correlation requires at least two distinct unit IDs."
            )
        return self


class HarrisSuggestion(_HarrisModel):
    id: SuggestionId
    suggestion_type: SuggestionType
    status: SuggestionStatus
    younger_id: UnitId | None
    older_id: UnitId | None
    relation_kind: RelationKind | None
    correlation_unit_ids: list[UnitId]
    reason: HumanText
    source_refs: list[SourceRef]

    @model_validator(mode="after")
    def enforce_suggestion_shape(self):
        if self.suggestion_type == "ordering":
            if (
                self.younger_id is None
                or self.older_id is None
                or self.relation_kind is None
            ):
                raise ValueError(
                    "An ordering suggestion requires younger_id, older_id, "
                    "and relation_kind."
                )
            if self.correlation_unit_ids:
                raise ValueError(
                    "An ordering suggestion must have no correlation unit IDs."
                )
            return self

        if (
            self.younger_id is not None
            or self.older_id is not None
            or self.relation_kind is not None
        ):
            raise ValueError(
                "A correlation suggestion must have null younger_id, "
                "older_id, and relation_kind."
            )
        if len(set(self.correlation_unit_ids)) < 2:
            raise ValueError(
                "A correlation suggestion requires at least two distinct "
                "unit IDs."
            )
        return self


class HarrisMatrix(_HarrisModel):
    schema_version: Literal[1]
    matrix_id: MatrixId
    revision: NonNegativeInteger
    title: HumanText
    site: HumanText
    trench: HumanText
    notes: HumanText
    source_job_ids: list[MatrixId]
    units: list[HarrisUnit]
    relations: list[HarrisRelation]
    correlations: list[HarrisCorrelation]
    suggestions: list[HarrisSuggestion]
    created_at: AwareDatetime
    updated_at: AwareDatetime


_GENERIC_LABEL = re.compile(r"Polygon\s+\d+", re.IGNORECASE)


def _issue(
    code: str,
    message: str,
    unit_ids=(),
    relation_ids=(),
) -> dict:
    return {
        "code": code,
        "message": message,
        "unit_ids": list(unit_ids),
        "relation_ids": list(relation_ids),
    }


def correlation_components(matrix: HarrisMatrix) -> dict[str, str]:
    """Map each stored unit to its deterministic correlation representative."""
    unit_ids = sorted({unit.id for unit in matrix.units})
    parent = {unit_id: unit_id for unit_id in unit_ids}

    def find(unit_id):
        while parent[unit_id] != unit_id:
            parent[unit_id] = parent[parent[unit_id]]
            unit_id = parent[unit_id]
        return unit_id

    def union(first_id, second_id):
        first_root = find(first_id)
        second_root = find(second_id)
        if first_root == second_root:
            return
        representative = min(first_root, second_root)
        other = max(first_root, second_root)
        parent[other] = representative

    for correlation in sorted(matrix.correlations, key=lambda item: item.id):
        members = sorted({
            unit_id
            for unit_id in correlation.unit_ids
            if unit_id in parent
        })
        for member in members[1:]:
            union(members[0], member)

    return {
        unit_id: find(unit_id)
        for unit_id in unit_ids
    }


def _collapsed_graph(matrix, components):
    unit_ids = set(components)
    nodes = set(components.values())
    relation_ids_by_edge = defaultdict(list)

    for relation in sorted(matrix.relations, key=lambda item: item.id):
        if (
            relation.younger_id not in unit_ids
            or relation.older_id not in unit_ids
            or relation.younger_id == relation.older_id
        ):
            continue
        younger = components[relation.younger_id]
        older = components[relation.older_id]
        if younger == older:
            continue
        relation_ids_by_edge[(younger, older)].append(relation.id)

    return nodes, {
        edge: sorted(relation_ids)
        for edge, relation_ids in relation_ids_by_edge.items()
    }


def _adjacency(nodes, edges):
    adjacent = {node: [] for node in nodes}
    for younger, older in sorted(edges):
        adjacent[younger].append(older)
    return adjacent


def _find_cycle(nodes, edges):
    adjacent = _adjacency(nodes, edges)
    state = {node: 0 for node in nodes}
    path = []
    path_indexes = {}

    def visit(node):
        state[node] = 1
        path_indexes[node] = len(path)
        path.append(node)

        for neighbor in adjacent[node]:
            if state[neighbor] == 0:
                cycle = visit(neighbor)
                if cycle is not None:
                    return cycle
            elif state[neighbor] == 1:
                return path[path_indexes[neighbor]:] + [neighbor]

        path.pop()
        path_indexes.pop(node)
        state[node] = 2
        return None

    for node in sorted(nodes):
        if state[node] == 0:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None


def _topological_sort(nodes, edges):
    adjacent = _adjacency(nodes, edges)
    indegree = {node: 0 for node in nodes}
    for _, older in edges:
        indegree[older] += 1

    ready = [
        node
        for node in nodes
        if indegree[node] == 0
    ]
    heapq.heapify(ready)
    order = []

    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for neighbor in adjacent[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    return order


def _path_exists(start, target, edges, excluded_edge):
    adjacent = _adjacency(
        {node for edge in edges for node in edge},
        edges - {excluded_edge},
    )
    pending = [start]
    visited = set()

    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        pending.extend(reversed(adjacent.get(node, [])))
    return False


def _transitive_reduction_edges(edges):
    return {
        edge
        for edge in edges
        if not _path_exists(edge[0], edge[1], edges, edge)
    }


def topological_order(matrix: HarrisMatrix) -> list[str]:
    """Return correlated display nodes in stable younger-to-older order."""
    components = correlation_components(matrix)
    nodes, relation_ids_by_edge = _collapsed_graph(matrix, components)
    edges = set(relation_ids_by_edge)
    cycle = _find_cycle(nodes, edges)
    if cycle is not None:
        raise ValueError(f"Cycle detected: {' -> '.join(cycle)}")
    return _topological_sort(nodes, edges)


def transitive_reduction(
    matrix: HarrisMatrix,
) -> list[tuple[str, str]]:
    """Return deterministic immediate display edges without changing relations."""
    components = correlation_components(matrix)
    nodes, relation_ids_by_edge = _collapsed_graph(matrix, components)
    edges = set(relation_ids_by_edge)
    cycle = _find_cycle(nodes, edges)
    if cycle is not None:
        raise ValueError(f"Cycle detected: {' -> '.join(cycle)}")
    return sorted(_transitive_reduction_edges(edges))


def _cycle_relation_ids(cycle, relation_ids_by_edge):
    relation_ids = set()
    for younger, older in zip(cycle, cycle[1:]):
        relation_ids.update(relation_ids_by_edge[(younger, older)])
    return sorted(relation_ids)


def validate_matrix_graph(matrix: HarrisMatrix) -> dict:
    """Validate and derive the deterministic display graph for a matrix."""
    errors = []
    warnings = []
    unit_ids = {unit.id for unit in matrix.units}
    components = correlation_components(matrix)

    for relation in sorted(matrix.relations, key=lambda item: item.id):
        missing_ids = sorted({
            unit_id
            for unit_id in (relation.younger_id, relation.older_id)
            if unit_id not in unit_ids
        })
        if missing_ids:
            errors.append(_issue(
                "missing-unit",
                f"Relation {relation.id} references missing unit(s): "
                f"{', '.join(missing_ids)}.",
                missing_ids,
                [relation.id],
            ))

    for correlation in sorted(matrix.correlations, key=lambda item: item.id):
        missing_ids = sorted(
            unit_id
            for unit_id in correlation.unit_ids
            if unit_id not in unit_ids
        )
        if missing_ids:
            errors.append(_issue(
                "missing-unit",
                f"Correlation {correlation.id} references missing unit(s): "
                f"{', '.join(missing_ids)}.",
                missing_ids,
            ))

    for relation in sorted(matrix.relations, key=lambda item: item.id):
        if relation.younger_id == relation.older_id:
            errors.append(_issue(
                "self-relation",
                f"Relation {relation.id} connects unit "
                f"{relation.younger_id} to itself.",
                [relation.younger_id],
                [relation.id],
            ))

    relations_by_pair = defaultdict(list)
    for relation in matrix.relations:
        relations_by_pair[
            (relation.younger_id, relation.older_id)
        ].append(relation.id)
    for (younger, older), relation_ids in sorted(relations_by_pair.items()):
        if len(relation_ids) > 1:
            errors.append(_issue(
                "duplicate-relation",
                f"Multiple relations assert {younger} -> {older}.",
                sorted({younger, older}),
                sorted(relation_ids),
            ))

    correlation_memberships = defaultdict(list)
    for correlation in matrix.correlations:
        for unit_id in set(correlation.unit_ids):
            correlation_memberships[unit_id].append(correlation.id)
    for unit_id, correlation_ids in sorted(correlation_memberships.items()):
        if len(correlation_ids) > 1:
            sorted_ids = sorted(correlation_ids)
            errors.append(_issue(
                "overlapping-correlation",
                f"Unit {unit_id} appears in overlapping correlation groups: "
                f"{', '.join(sorted_ids)}.",
                [unit_id],
            ))

    for relation in sorted(matrix.relations, key=lambda item: item.id):
        if (
            relation.younger_id in unit_ids
            and relation.older_id in unit_ids
            and relation.younger_id != relation.older_id
            and components[relation.younger_id]
            == components[relation.older_id]
        ):
            errors.append(_issue(
                "relation-within-correlation",
                f"Relation {relation.id} connects units in the same "
                "correlation component.",
                sorted({relation.younger_id, relation.older_id}),
                [relation.id],
            ))

    nodes, relation_ids_by_edge = _collapsed_graph(matrix, components)
    edges = set(relation_ids_by_edge)
    cycle = _find_cycle(nodes, edges)
    if cycle is not None:
        errors.append(_issue(
            "cycle",
            f"Chronological cycle detected: {' -> '.join(cycle)}.",
            cycle,
            _cycle_relation_ids(cycle, relation_ids_by_edge),
        ))
        order = []
        display_edges = []
    else:
        order = _topological_sort(nodes, edges)
        reduced_edges = _transitive_reduction_edges(edges)
        display_edges = sorted(reduced_edges)

        for edge in sorted(edges - reduced_edges):
            warnings.append(_issue(
                "redundant-relation",
                f"Saved relation {edge[0]} -> {edge[1]} is implied by "
                "a longer path and is omitted from display edges.",
                list(edge),
                relation_ids_by_edge[edge],
            ))

    connected_components = {
        component
        for edge in edges
        for component in edge
    }
    members_by_component = defaultdict(list)
    for unit_id, component in components.items():
        members_by_component[component].append(unit_id)
    for component in sorted(nodes - connected_components):
        members = sorted(members_by_component[component])
        warnings.append(_issue(
            "isolated-unit",
            f"Unit component {component} has no chronological relations.",
            members,
        ))

    for unit in sorted(matrix.units, key=lambda item: item.id):
        if _GENERIC_LABEL.fullmatch(unit.label):
            warnings.append(_issue(
                "generic-label",
                f"Unit {unit.id} still has generic label {unit.label!r}.",
                [unit.id],
            ))

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "topological_order": order,
        "display_edges": display_edges,
    }
