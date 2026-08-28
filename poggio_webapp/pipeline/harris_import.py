"""Read-only discovery and unit import for Harris Matrix source jobs.

Sources are read in their canonical form: the canonical artifact when the
job has one, else the legacy artifact chain canonicalized on read (D4). One
unit builder serves both mediums, and the unit identity inputs
``job_id|schema_type|face|layer_index`` are the ones this module hashed
before the canonical form existed, so re-importing an old matrix finds its
units instead of forking them.
"""

import hashlib
import json
import re
from pathlib import Path

from . import canonical
from .harris_matrix import HarrisMatrix, HarrisUnit, SourceRef

_JOB_ID = re.compile(r"[0-9a-f]{12}")
_GENERIC_LABEL = re.compile(r"Polygon\s+\d+", re.IGNORECASE)


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


def _canonical_document(job_id: str, document: dict) -> dict:
    """The canonical form of a source document, canonicalized on read."""
    if not isinstance(document, dict):
        raise HarrisImportError(
            f"Source document for job {job_id} has an unsupported top-level shape."
        )
    if canonical.is_canonical(document):
        return document
    try:
        converted, _warnings = canonical.canonicalize(document)
    except (ValueError, AttributeError, TypeError) as error:
        raise HarrisImportError(
            "Source document has an unsupported extraction schema."
        ) from error
    return converted


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

    return _canonical_document(job_id, document)


def load_source_document(
    job_id: str,
    jobs_dir: Path,
) -> tuple[dict, Path]:
    """Load the highest-priority usable artifact inside one source job.

    Returns (canonical document, path of the file actually read)."""
    job_id = _validate_job_id(job_id)
    job_directory = (Path(jobs_dir) / job_id).resolve()
    if not job_directory.is_dir():
        raise HarrisImportError(f"Source job {job_id} was not found.")

    metadata = _read_metadata(job_directory)
    candidates = [
        _metadata_candidate(
            job_directory,
            metadata,
            "canonical_path",
        ),
        (job_directory / "04_normalize_validate" / "canonical.json").resolve(),
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


def _composed_description(layer: dict) -> str | None:
    """Prose plus the medium's observation, neither displacing the other (E6)."""
    prose = _clean_text(layer.get("description"))
    observation = _clean_text(
        canonical._munsell_text(layer.get("munsell"))
    ) or _clean_text(layer.get("material"))
    if prose and observation and observation != prose:
        return f"{prose} ({observation})"
    return prose or observation


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


def _extract_with_warnings(
    job_id: str,
    document: dict,
) -> tuple[list[HarrisUnit], list[dict]]:
    """One unit builder for both mediums, over the canonical faces."""
    job_id = _validate_job_id(job_id)
    document = _canonical_document(job_id, document)
    schema_type = document["sourceSchema"]

    units = []
    warnings = []
    for face in document.get("faces") or []:
        for layer_index, layer in enumerate(face.get("layers") or []):
            provenance = layer.get("provenance") or {}
            unit, warning = _make_unit(
                job_id=job_id,
                schema_type=schema_type,
                face=face.get("face"),
                layer_index=layer_index,
                raw_label=provenance.get("sourceLabel", layer.get("label")),
                description=_composed_description(layer),
            )
            units.append(unit)
            if warning is not None:
                warnings.append(warning)
    return units, warnings


def extract_source_units(
    job_id: str,
    document: dict,
) -> list[HarrisUnit]:
    """Convert one supported source document into independent matrix units."""
    units, _warnings = _extract_with_warnings(job_id, document)
    return units


def _trench_label(document: dict) -> str:
    return _clean_text((document.get("document") or {}).get("trenchLabel")) or ""


def _faces(units: list[HarrisUnit]) -> list[str]:
    faces = {
        source_ref.face
        for unit in units
        for source_ref in unit.source_refs
        if source_ref.face
    }
    return sorted(faces)


def discover_source_jobs(jobs_dir: Path) -> list[dict]:
    """Summarize source artifacts without exposing server paths.

    A job directory that cannot be imported is listed with the reason
    rather than silently skipped, so the operator can see why a drawing is
    missing from the picker. Directories that are not job IDs stay out.
    """
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
        except HarrisImportError as error:
            summaries.append(
                {
                    "job_id": job_id,
                    "usable": False,
                    "reason": str(error),
                }
            )
            continue
        summaries.append(
            {
                "job_id": job_id,
                "usable": True,
                "schema_type": document["sourceSchema"],
                "trench": _trench_label(document),
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
