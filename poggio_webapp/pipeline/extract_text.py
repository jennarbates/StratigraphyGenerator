"""Text-only extraction and review contracts for field-wall sheets."""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from google import genai
from google.genai import types
from PIL import Image
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

from ._extract_common import check_response, generate_with_retry


# Preprocessed scans may be intentionally large, but Gemini does not need the
# full working resolution. Keep this aligned with the existing extractors.
Image.MAX_IMAGE_PIXELS = None
MAX_SEND_DIMENSION = 3072


def _cap_for_sending(img: Image.Image, max_dim: int = MAX_SEND_DIMENSION) -> Image.Image:
    """Shrink an image to ``max_dim`` on its longest side without enlarging it."""
    width, height = img.size
    if max(width, height) <= max_dim:
        return img

    scale = max_dim / max(width, height)
    return img.resize(
        (int(width * scale), int(height * scale)),
        Image.Resampling.LANCZOS,
    )


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
    proposed: str | None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None
    notes: str | None = None


class NumberCandidate(_ContractModel):
    raw: str
    proposed: float | None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None
    notes: str | None = None


class BooleanCandidate(_ContractModel):
    raw: str
    proposed: bool | None
    confidence: ConfidenceLevel
    bbox: BoundingBox | None
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
    schemaVersion: Literal[1] = 1
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


def build_prompt() -> str:
    """Return the instructions for text-only field-wall transcription."""
    return """
You are extracting text from a modern archaeological field-wall recording
sheet into the provided FieldWallTextCandidates JSON schema.

TEXT ONLY
- Transcribe visible text only.
- Do not trace boundaries.
- Do not return layer coordinates.
- Do not identify marker positions.
- Do not classify features.
- Do not estimate geometry.
- Do not interpret archaeological chronology.

TRANSCRIPTION RULES
- Do not complete partially visible text.
- Use null when text is unreadable or uncertain. A null is better than a guess.
- Preserve raw transcription. Store it exactly as it appears in each
  candidate's raw field, including spelling, spacing, capitalization, and
  punctuation.
- Put standardized text only in proposed; never silently standardize raw.
- Associate a Munsell value with a locus only when the association is visually
  clear. Otherwise leave the association null.
- Record unrelated readable text under otherText (`document.otherText`).

BOUNDING BOXES
- Return bounding boxes normalized to the inclusive 0-1000 coordinate range.
- The required bounding-box order is [xMin, yMin, xMax, yMax].
- A bounding box locates text only; it must never describe a boundary, layer,
  feature, marker, or other geometry.
- Use null for a bounding box when its position cannot be located reliably.

Return only JSON that conforms to FieldWallTextCandidates.
""".strip()


def run_text_extraction(
    image_path: str,
    api_key: str,
    output_path: str,
    progress_cb=None,
) -> dict:
    """Extract, validate, persist, and return text candidates from an image."""
    source_path = Path(image_path)
    if not source_path.is_file():
        raise RuntimeError(f"file not found: {image_path}")

    if progress_cb:
        progress_cb("transcribing visible text only...")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=240_000),
    )

    with Image.open(source_path) as source_image:
        original_size = source_image.size
        image = _cap_for_sending(source_image)
        if image.size != original_size and progress_cb:
            progress_cb(
                f"resized {original_size[0]}x{original_size[1]} -> "
                f"{image.size[0]}x{image.size[1]} before sending to Gemini"
            )

        response = generate_with_retry(
            client,
            progress_cb=progress_cb,
            model="gemini-2.5-flash",
            contents=[image, build_prompt()],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FieldWallTextCandidates,
                temperature=0.1,
                max_output_tokens=65_536,
                thinking_config=types.ThinkingConfig(thinking_budget=1024),
            ),
        )

    raw_json = response.text
    warning = check_response(response, raw_json)
    if warning:
        raise ValueError(
            "Invalid structured output for FieldWallTextCandidates: "
            f"{warning}"
        )

    try:
        candidates = FieldWallTextCandidates.model_validate_json(raw_json)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid structured output for FieldWallTextCandidates: "
            f"{exc}"
        ) from exc

    result = candidates.model_dump(mode="json")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if progress_cb:
        progress_cb(f"wrote {output_path}")

    return result
