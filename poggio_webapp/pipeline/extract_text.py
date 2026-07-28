"""Text-only extraction and review contracts for field-wall sheets."""

import json
import re
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewStatus(str, Enum):
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    UNREADABLE = "unreadable"


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_bbox_order(bbox: list[int]) -> list[int]:
    x_min, y_min, x_max, y_max = bbox
    if x_min >= x_max:
        raise ValueError("bbox xMin must be less than xMax")
    if y_min >= y_max:
        raise ValueError("bbox yMin must be less than yMax")
    return bbox


BoundingBox = Annotated[
    list[Annotated[int, Field(strict=True, ge=0, le=1000)]],
    Field(min_length=4, max_length=4),
    AfterValidator(_validate_bbox_order),
]


class TextCandidate(_ContractModel):
    raw: str
    proposed: str | None = None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None = None
    notes: str | None = None


class NumberCandidate(_ContractModel):
    raw: str
    proposed: float | None = None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None = None
    notes: str | None = None


class BooleanCandidate(_ContractModel):
    raw: str
    proposed: bool | None = None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None = None
    notes: str | None = None


class LocusTextCandidate(_ContractModel):
    locusNumber: TextCandidate | None = None
    munsellRaw: TextCandidate | None = None
    description: TextCandidate | None = None


class DocumentTextCandidates(_ContractModel):
    trenchLabel: TextCandidate | None = None
    faceLabel: TextCandidate | None = None
    date: TextCandidate | None = None
    gridSquareCm: NumberCandidate | None = None
    northArrowPresent: BooleanCandidate | None = None
    illustrators: list[TextCandidate] = Field(default_factory=list)
    gridTiePoints: list[TextCandidate] = Field(default_factory=list)
    marginalia: list[TextCandidate] = Field(default_factory=list)
    otherText: list[TextCandidate] = Field(default_factory=list)


class FieldWallTextCandidates(_ContractModel):
    # google-genai rejects numeric Literal values while translating a
    # Pydantic response schema. Strict bounds preserve the exact same
    # contract (only the integer 1 is valid) without emitting a numeric const.
    schemaVersion: Annotated[int, Field(strict=True, ge=1, le=1)] = 1
    sheetType: Literal["fieldwall"] = "fieldwall"
    document: DocumentTextCandidates = Field(default_factory=DocumentTextCandidates)
    loci: list[LocusTextCandidate] = Field(default_factory=list)


class VerifiedDocumentText(_ContractModel):
    trenchLabel: str | None = None
    faceLabel: str | None = None
    date: str | None = None
    gridSquareCm: float | None = None
    northArrowPresent: bool | None = None
    illustrators: list[str] = Field(default_factory=list)
    gridTiePoints: list[str] = Field(default_factory=list)
    marginalia: list[str] = Field(default_factory=list)
    otherText: list[str] = Field(default_factory=list)


class VerifiedLocusText(_ContractModel):
    locusNumber: str | None = None
    munsellRaw: str | None = None
    description: str | None = None


class AuditEntry(_ContractModel):
    fieldPath: str
    raw: str | None
    proposed: str | float | bool | None
    final: str | float | bool | None
    status: ReviewStatus
    confidence: ConfidenceLevel
    bbox: BoundingBox | None


class VerifiedFieldWallText(_ContractModel):
    schemaVersion: Literal[1] = 1
    sheetType: Literal["fieldwall"] = "fieldwall"
    reviewCompleted: Literal[True] = True
    document: VerifiedDocumentText = Field(default_factory=VerifiedDocumentText)
    loci: list[VerifiedLocusText] = Field(default_factory=list)
    audit: list[AuditEntry] = Field(default_factory=list)


_HUE_PREFIX = re.compile(
    r"^(?P<number>\d+(?:\.\d+)?)\s*"
    r"(?P<hue>YR|GY|BG|PB|RP|R|Y|G|B|P)(?=\s)",
    re.IGNORECASE,
)
_MUNSELL_STRUCTURE = re.compile(
    r"^(?:2\.5|5|7\.5|10)(?:YR|GY|BG|PB|RP|R|Y|G|B|P) "
    r"(?:10|[0-9](?:\.\d+)?)/[0-9]+(?:\.\d+)?$"
)


def normalize_munsell(raw: str | None) -> tuple[str | None, bool]:
    """Apply safe formatting only and report whether the result has Munsell form."""
    if raw is None:
        return None, False

    proposed = " ".join(raw.strip().split())
    proposed = re.sub(r"\s*/\s*", "/", proposed)
    proposed = _HUE_PREFIX.sub(
        lambda match: f"{match.group('number')}{match.group('hue').upper()}",
        proposed,
    )
    return proposed, _MUNSELL_STRUCTURE.fullmatch(proposed) is not None


def _confidence_level(value: object) -> ConfidenceLevel:
    """Map the original extractor's free-text confidence conservatively."""
    text = str(value or "").strip().lower()
    if text in {level.value for level in ConfidenceLevel}:
        return ConfidenceLevel(text)
    if any(word in text for word in ("uncertain", "ambiguous", "faded", "illegible")):
        return ConfidenceLevel.LOW
    if any(word in text for word in ("certain", "clear", "confident")):
        return ConfidenceLevel.HIGH
    return ConfidenceLevel.MEDIUM


def _text_candidate(
    value: object,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> TextCandidate | None:
    if value is None:
        return None
    raw = str(value)
    if not raw.strip():
        return None
    return TextCandidate(
        raw=raw,
        proposed=raw,
        confidence=confidence,
        bbox=None,
    )


_DOCUMENT_SINGLE_CANDIDATES = (
    "trenchLabel",
    "faceLabel",
    "date",
    "gridSquareCm",
    "northArrowPresent",
)
_DOCUMENT_CANDIDATE_LISTS = (
    "illustrators",
    "gridTiePoints",
    "marginalia",
    "otherText",
)
_LOCUS_CANDIDATES = ("locusNumber", "munsellRaw", "description")


def _candidate_dicts(payload: dict):
    document = payload.get("document")
    if isinstance(document, dict):
        for field_name in _DOCUMENT_SINGLE_CANDIDATES:
            candidate = document.get(field_name)
            if isinstance(candidate, dict):
                yield candidate
        for field_name in _DOCUMENT_CANDIDATE_LISTS:
            candidates = document.get(field_name)
            if isinstance(candidates, list):
                for candidate in candidates:
                    if isinstance(candidate, dict):
                        yield candidate

    for locus in payload.get("loci") or []:
        if not isinstance(locus, dict):
            continue
        for field_name in _LOCUS_CANDIDATES:
            candidate = locus.get(field_name)
            if isinstance(candidate, dict):
                yield candidate


def _valid_bbox(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if any(type(coordinate) is not int for coordinate in value):
        return False
    if any(coordinate < 0 or coordinate > 1000 for coordinate in value):
        return False
    x_min, y_min, x_max, y_max = value
    return x_min < x_max and y_min < y_max


def _embedded_candidates(payload: dict) -> dict | None:
    embedded = payload.get("textCandidates")
    if not isinstance(embedded, dict):
        return None

    embedded = deepcopy(embedded)
    for candidate in _candidate_dicts(embedded):
        bbox = candidate.get("bbox")
        if bbox is not None and not _valid_bbox(bbox):
            candidate["bbox"] = None
    return FieldWallTextCandidates.model_validate(embedded).model_dump(mode="json")


def candidates_from_fieldwall_extraction(
    extraction: str | dict,
    output_path: str | None = None,
) -> dict:
    """Adapt the existing Gemini field-wall result for human text review.

    This performs no provider call. The established ``extract_fieldwall``
    pipeline remains the single Gemini integration; this function only shapes
    the text already present in its JSON into the review contract.
    """
    payload = json.loads(extraction) if isinstance(extraction, str) else extraction
    if not isinstance(payload, dict):
        raise ValueError("field-wall extraction must be a JSON object")

    embedded = _embedded_candidates(payload)
    if embedded is not None:
        result = embedded
        if output_path:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return result

    grid_ties = []
    for tie in payload.get("gridTiePoints") or []:
        raw_text = tie.get("rawText") if isinstance(tie, dict) else tie
        candidate = _text_candidate(raw_text)
        if candidate is not None:
            grid_ties.append(candidate)

    loci = []
    for locus in payload.get("loci") or []:
        if not isinstance(locus, dict):
            continue
        confidence = _confidence_level(locus.get("confidence"))
        munsell = locus.get("munsell")
        munsell_raw = munsell.get("raw") if isinstance(munsell, dict) else None
        loci.append(
            LocusTextCandidate(
                locusNumber=_text_candidate(locus.get("locusNumber"), confidence),
                munsellRaw=_text_candidate(munsell_raw, confidence),
                description=_text_candidate(locus.get("description"), confidence),
            )
        )

    grid_square = payload.get("gridSquareCm")
    grid_candidate = None
    if isinstance(grid_square, (int, float)) and not isinstance(grid_square, bool):
        grid_candidate = NumberCandidate(
            raw=f"{grid_square:g}",
            proposed=float(grid_square),
            confidence=ConfidenceLevel.HIGH,
            bbox=None,
        )

    north_arrow = payload.get("northArrowPresent")
    north_candidate = None
    if isinstance(north_arrow, bool):
        north_candidate = BooleanCandidate(
            raw="present" if north_arrow else "not present",
            proposed=north_arrow,
            confidence=ConfidenceLevel.MEDIUM,
            bbox=None,
        )

    def text_list(values):
        candidates = []
        for value in values or []:
            candidate = _text_candidate(value)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    candidates = FieldWallTextCandidates(
        document=DocumentTextCandidates(
            trenchLabel=_text_candidate(payload.get("trenchLabel")),
            faceLabel=_text_candidate(payload.get("faceLabel")),
            date=_text_candidate(payload.get("date")),
            gridSquareCm=grid_candidate,
            northArrowPresent=north_candidate,
            illustrators=text_list(payload.get("illustrators")),
            gridTiePoints=grid_ties,
            marginalia=text_list(payload.get("marginalia")),
            otherText=[],
        ),
        loci=loci,
    )
    result = candidates.model_dump(mode="json")

    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return result
