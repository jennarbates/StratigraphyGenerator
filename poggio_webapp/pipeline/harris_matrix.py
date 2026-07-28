"""Versioned persisted-data models for Harris Matrix workspaces."""

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
