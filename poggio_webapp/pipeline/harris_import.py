"""Read-only discovery and unit import for Harris Matrix source jobs."""

import hashlib
import json
import re
from pathlib import Path

from .harris_matrix import HarrisMatrix, HarrisUnit, SourceRef

_JOB_ID = re.compile(r"[0-9a-f]{12}")
_GENERIC_LABEL = re.compile(r"Polygon\s+\d+", re.IGNORECASE)
_FIELD_WALL_FIELDS = frozenset(
    {
        "faceLabel",
        "gridSquareCm",
        "loci",
        "trenchLabel",
    }
)


class HarrisImportError(ValueError):
    """Raised for an expected source discovery or import failure."""


def _validate_job_id(job_id: str) -> str:
    if not isinstance(job_id, str) or _JOB_ID.fullmatch(job_id) is None:
        raise HarrisImportError(
            "Job ID must be exactly 12 lowercase hexadecimal characters."
        )
    return job_id


def _is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def _read_metadata(job_directory: Path) -> dict:
    metadata_path = job_directory / "meta.json"
    if not metadata_path.is_file():
        return {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _metadata_candidate(
    job_directory: Path,
    metadata: dict,
    field: str,
) -> Path | None:
    raw_path = metadata.get(field)
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = job_directory / candidate
    try:
        candidate = candidate.resolve()
    except OSError:
        return None

    if not _is_within(candidate, job_directory) or not candidate.is_file():
        return None
    return candidate


def _schema_type(document: dict) -> str:
    if isinstance(document.get("trenchProfiles"), list):
        return "ArchaeologicalDiagram"
    if isinstance(document.get("layers"), list) and _FIELD_WALL_FIELDS.intersection(
        document
    ):
        return "FieldWallProfile"
    raise HarrisImportError("Source document has an unsupported extraction schema.")


def _read_source_json(job_id: str, path: Path) -> dict:
    try:
        serialized = path.read_text(encoding="utf-8")
        document = json.loads(serialized)
    except json.JSONDecodeError as error:
        raise HarrisImportError(
            f"Source document for job {job_id} contains malformed JSON."
        ) from error
    except UnicodeDecodeError as error:
        raise HarrisImportError(
            f"Source document for job {job_id} is not valid UTF-8 JSON."
        ) from error
    except OSError as error:
        raise HarrisImportError(
            f"Source document for job {job_id} could not be read."
        ) from error

    if not isinstance(document, dict):
        raise HarrisImportError(
            f"Source document for job {job_id} has an unsupported top-level shape."
        )
    _schema_type(document)
    return document


def load_source_document(
    job_id: str,
    jobs_dir: Path,
) -> tuple[dict, Path]:
    """Load the highest-priority usable artifact inside one source job."""
    job_id = _validate_job_id(job_id)
    job_directory = (Path(jobs_dir) / job_id).resolve()
    if not job_directory.is_dir():
        raise HarrisImportError(f"Source job {job_id} was not found.")

    metadata = _read_metadata(job_directory)
    candidates = [
        _metadata_candidate(
            job_directory,
            metadata,
            "normalized_path",
        ),
        (job_directory / "04_normalize_validate" / "output_clean.json").resolve(),
        _metadata_candidate(
            job_directory,
            metadata,
            "extraction_path",
        ),
        (job_directory / "extraction_output.json").resolve(),
    ]

    for candidate in candidates:
        if (
            candidate is not None
            and _is_within(candidate, job_directory)
            and candidate.is_file()
        ):
            return _read_source_json(job_id, candidate), candidate

    raise HarrisImportError(f"Source job {job_id} has no usable extraction output.")


def _clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _source_label(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _munsell_text(locus: dict) -> str | None:
    munsell = locus.get("munsell")
    if isinstance(munsell, str):
        return _clean_text(munsell)
    if isinstance(munsell, dict):
        parts = [
            _clean_text(munsell.get("raw")),
            _clean_text(munsell.get("colorName")),
        ]
        return " ".join(part for part in parts if part) or None
    return _clean_text(locus.get("munsellRaw"))


def _unit_id(
    job_id: str,
    schema_type: str,
    face: str,
    layer_index: int,
) -> str:
    identity = f"{job_id}|{schema_type}|{face}|{layer_index}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"unit-{suffix}"


def _warning(
    code: str,
    message: str,
    job_id: str,
    unit: HarrisUnit,
) -> dict:
    return {
        "code": code,
        "message": message,
        "job_id": job_id,
        "unit_id": unit.id,
    }


def _make_unit(
    *,
    job_id: str,
    schema_type: str,
    face,
    layer_index: int,
    raw_label,
    description,
) -> tuple[HarrisUnit, dict | None]:
    clean_face = _clean_text(face) or ""
    preserved_label = _source_label(raw_label)
    clean_label = _clean_text(preserved_label)
    warning_code = None
    if clean_label is None:
        clean_label = f"Unlabeled layer {layer_index + 1}"
        warning_code = "unlabeled-source-unit"
    elif _GENERIC_LABEL.fullmatch(clean_label):
        warning_code = "generic-source-label"

    unit = HarrisUnit(
        id=_unit_id(
            job_id,
            schema_type,
            clean_face,
            layer_index,
        ),
        label=clean_label,
        unit_type="deposit",
        description=_clean_text(description),
        source_refs=[
            SourceRef(
                job_id=job_id,
                schema_type=schema_type,
                face=clean_face,
                layer_index=layer_index,
                source_label=preserved_label,
            )
        ],
    )

    if warning_code == "unlabeled-source-unit":
        return unit, _warning(
            warning_code,
            (
                f"Job {job_id}, face {clean_face or '(unrecorded)'}, "
                f"layer {layer_index + 1} has no source label."
            ),
            job_id,
            unit,
        )
    if warning_code == "generic-source-label":
        return unit, _warning(
            warning_code,
            (
                f"Job {job_id}, face {clean_face or '(unrecorded)'}, "
                f"layer {layer_index + 1} uses generic label "
                f"{clean_label!r}."
            ),
            job_id,
            unit,
        )
    return unit, None


def _field_wall_units(
    job_id: str,
    document: dict,
) -> tuple[list[HarrisUnit], list[dict]]:
    face = document.get("faceLabel")
    loci_by_label = {}
    loci = document.get("loci")
    if isinstance(loci, list):
        for locus in loci:
            if not isinstance(locus, dict):
                continue
            label = _clean_text(_source_label(locus.get("locusNumber")))
            if label is not None and label not in loci_by_label:
                loci_by_label[label] = locus

    units = []
    warnings = []
    for layer_index, layer in enumerate(document["layers"]):
        if not isinstance(layer, dict):
            continue
        raw_label = layer.get("locusNumber")
        clean_label = _clean_text(_source_label(raw_label))
        locus = loci_by_label.get(clean_label, {})
        description = _clean_text(locus.get("description"))
        if description is None:
            description = _munsell_text(locus)
        unit, warning = _make_unit(
            job_id=job_id,
            schema_type="FieldWallProfile",
            face=face,
            layer_index=layer_index,
            raw_label=raw_label,
            description=description,
        )
        units.append(unit)
        if warning is not None:
            warnings.append(warning)
    return units, warnings


def _illustrator_units(
    job_id: str,
    document: dict,
) -> tuple[list[HarrisUnit], list[dict]]:
    units = []
    warnings = []
    for profile in document["trenchProfiles"]:
        if not isinstance(profile, dict):
            continue
        layers = profile.get("layers")
        if not isinstance(layers, list):
            continue
        for layer_index, layer in enumerate(layers):
            if not isinstance(layer, dict):
                continue
            description = _clean_text(layer.get("description"))
            if description is None:
                description = _clean_text(layer.get("inferredMaterial"))
            unit, warning = _make_unit(
                job_id=job_id,
                schema_type="ArchaeologicalDiagram",
                face=profile.get("face"),
                layer_index=layer_index,
                raw_label=layer.get("layerName"),
                description=description,
            )
            units.append(unit)
            if warning is not None:
                warnings.append(warning)
    return units, warnings


def _extract_with_warnings(
    job_id: str,
    document: dict,
) -> tuple[list[HarrisUnit], list[dict]]:
    job_id = _validate_job_id(job_id)
    if not isinstance(document, dict):
        raise HarrisImportError("Source document has an unsupported top-level shape.")

    schema_type = _schema_type(document)
    if schema_type == "FieldWallProfile":
        return _field_wall_units(job_id, document)
    return _illustrator_units(job_id, document)


def extract_source_units(
    job_id: str,
    document: dict,
) -> list[HarrisUnit]:
    """Convert one supported source document into independent matrix units."""
    units, _warnings = _extract_with_warnings(job_id, document)
    return units


def _trench_label(document: dict, schema_type: str) -> str:
    if schema_type == "FieldWallProfile":
        return _clean_text(document.get("trenchLabel")) or ""
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    return _clean_text(metadata.get("trenchLabel")) or ""


def _faces(units: list[HarrisUnit]) -> list[str]:
    faces = {
        source_ref.face
        for unit in units
        for source_ref in unit.source_refs
        if source_ref.face
    }
    return sorted(faces)


def discover_source_jobs(jobs_dir: Path) -> list[dict]:
    """Summarize valid source artifacts without exposing server paths."""
    jobs_directory = Path(jobs_dir)
    if not jobs_directory.is_dir():
        return []

    summaries = []
    for candidate in sorted(
        jobs_directory.iterdir(),
        key=lambda path: path.name,
    ):
        job_id = candidate.name
        if not candidate.is_dir() or _JOB_ID.fullmatch(job_id) is None:
            continue
        try:
            document, _path = load_source_document(job_id, jobs_directory)
            units = extract_source_units(job_id, document)
        except HarrisImportError:
            continue
        schema_type = _schema_type(document)
        summaries.append(
            {
                "job_id": job_id,
                "schema_type": schema_type,
                "trench": _trench_label(document, schema_type),
                "faces": _faces(units),
                "unit_count": len(units),
            }
        )
    return summaries


def import_source_jobs(
    matrix: HarrisMatrix,
    job_ids: list[str],
    jobs_dir: Path,
) -> tuple[HarrisMatrix, list[dict]]:
    """Return a matrix copy with source units merged idempotently."""
    imported_matrix = matrix.model_copy(deep=True)
    units_by_id = {unit.id: unit for unit in imported_matrix.units}
    warnings = []
    imported_job_ids = set(imported_matrix.source_job_ids)
    requested_job_ids = set()

    for job_id in job_ids:
        job_id = _validate_job_id(job_id)
        if job_id in requested_job_ids:
            continue
        requested_job_ids.add(job_id)

        document, _path = load_source_document(job_id, jobs_dir)
        imported_units, job_warnings = _extract_with_warnings(
            job_id,
            document,
        )
        warnings.extend(job_warnings)

        for imported_unit in imported_units:
            existing_unit = units_by_id.get(imported_unit.id)
            if existing_unit is None:
                imported_matrix.units.append(imported_unit)
                units_by_id[imported_unit.id] = imported_unit
                continue
            for source_ref in imported_unit.source_refs:
                if source_ref not in existing_unit.source_refs:
                    existing_unit.source_refs.append(source_ref)

        if job_id not in imported_job_ids:
            imported_matrix.source_job_ids.append(job_id)
            imported_job_ids.add(job_id)

    return imported_matrix, warnings
