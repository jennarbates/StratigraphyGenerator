"""
Clean an extraction JSON before it feeds GemPy.
Adapted from 04_normalize_validate/normalizer.py into an importable function.
Logic unchanged.
"""

import json
from pathlib import Path

from .canonical import canonicalize

NULLISH = {"null", "none", "n/a", ""}

CANONICAL_FILENAME = "canonical.json"

# Where a job's document can be found when the canonical artifact is absent,
# best first: a job normalized before this artifact existed has only the
# legacy pair, and an editor job that never reached normalize has only its
# extraction.
CANONICAL_SOURCES = (
    "04_normalize_validate/output_clean.json",
    "extraction_output.json",
    "03_extraction/extraction.json",
)


def clean_null_strings(obj, log, path="root"):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str) and v.strip().lower() in NULLISH:
                obj[k] = None
                log.append(f"nulled string at {path}.{k}")
            else:
                clean_null_strings(v, log, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            clean_null_strings(v, log, f"{path}[{i}]")


def points_key(pts):
    if not pts:
        return None
    out = []
    for p in pts:
        x = p.get("xCoordinateMeters")
        y = p.get("yCoordinateMeters")
        out.append(
            (
                round(x, 3) if x is not None else None,
                round(y, 3) if y is not None else None,
            )
        )
    return tuple(out)


def dedupe_floor(face, log):
    layers = face.get("layers") or []
    if not layers:
        return
    deepest = layers[-1]
    bkey = points_key(deepest.get("bottomBoundary"))
    feats = deepest.get("featuresInLayer") or []
    kept = []
    for f in feats:
        name = (f.get("feature") or "").lower()
        if "floor" in name and points_key(f.get("shapePoints")) == bkey and bkey:
            log.append(
                f"{face.get('face')}: dropped trench-floor feature "
                f"(duplicates {deepest.get('layerName') or deepest.get('inferredMaterial')} bottom)"
            )
            continue
        kept.append(f)
    deepest["featuresInLayer"] = kept or None


def dedupe_cross_layer_features(face, log):
    layers = face.get("layers") or []
    seen = {}
    for i, layer in enumerate(layers):
        for f in layer.get("featuresInLayer") or []:
            sig = ((f.get("feature") or "").lower(), points_key(f.get("shapePoints")))
            if sig[1] is None:
                continue
            seen[sig] = i
    for i, layer in enumerate(layers):
        feats = layer.get("featuresInLayer") or []
        kept = []
        for f in feats:
            sig = ((f.get("feature") or "").lower(), points_key(f.get("shapePoints")))
            if sig[1] is not None and seen.get(sig) != i:
                log.append(
                    f"{face.get('face')}: removed duplicate feature "
                    f'"{f.get("feature")}" from '
                    f"{layer.get('layerName') or layer.get('inferredMaterial')} "
                    f"(kept in deepest layer)"
                )
                continue
            kept.append(f)
        layer["featuresInLayer"] = kept or None


def canonical_points_key(points):
    """points_key for canonical points, which name their axes truthfully."""
    renamed = [
        {
            "xCoordinateMeters": p.get("xMeters"),
            "yCoordinateMeters": p.get("depthMeters"),
        }
        for p in points or []
    ]
    return points_key(renamed)


def dedupe_floor_canonical(face, log):
    layers = face.get("layers") or []
    if not layers:
        return
    deepest = layers[-1]
    bottom = canonical_points_key(deepest.get("bottomBoundary"))
    if not bottom:
        return
    kept = []
    for feature in deepest.get("features") or []:
        name = (feature.get("feature") or "").lower()
        if (
            "floor" in name
            and canonical_points_key(feature.get("shapePoints")) == bottom
        ):
            log.append(
                f"canonical: {face.get('face')}: dropped trench-floor feature "
                f"(duplicates the bottom of {deepest['surfaceId']})"
            )
            continue
        kept.append(feature)
    deepest["features"] = kept


def dedupe_cross_layer_features_canonical(face, log):
    layers = face.get("layers") or []
    owner = {}
    for index, layer in enumerate(layers):
        for feature in layer.get("features") or []:
            signature = (
                (feature.get("feature") or "").lower(),
                canonical_points_key(feature.get("shapePoints")),
            )
            if signature[1] is None:
                continue
            owner[signature] = index

    for index, layer in enumerate(layers):
        kept = []
        for feature in layer.get("features") or []:
            signature = (
                (feature.get("feature") or "").lower(),
                canonical_points_key(feature.get("shapePoints")),
            )
            if signature[1] is not None and owner.get(signature) != index:
                log.append(
                    f"canonical: {face.get('face')}: removed duplicate feature "
                    f'"{feature.get("feature")}" from {layer["surfaceId"]} '
                    "(kept in the deepest layer)"
                )
                continue
            kept.append(feature)
        layer["features"] = kept


def canonical_path_for(output_path):
    """Where the canonical document sits: beside the normalized one."""
    return Path(output_path).with_name(CANONICAL_FILENAME)


def load_canonical(job_directory):
    """A job's canonical document, canonicalized on read when absent (D4)."""
    directory = Path(job_directory)
    artifact = directory / "04_normalize_validate" / CANONICAL_FILENAME
    if artifact.is_file():
        return json.loads(artifact.read_text(encoding="utf-8"))

    for name in CANONICAL_SOURCES:
        source = directory / name
        if source.is_file():
            canonical, _ = canonicalize(json.loads(source.read_text(encoding="utf-8")))
            return canonical

    raise FileNotFoundError(
        f"no canonical, normalized, or extraction document under {directory}"
    )


def run_normalize(input_path: str, output_path: str):
    """Returns (cleaned_data_dict, log_list), and writes the canonical form."""
    data = json.load(open(input_path))
    log = []

    clean_null_strings(data, log)

    # Canonicalize before writing anything: a document neither capture schema
    # recognizes stops the step here rather than leaving a legacy artifact
    # with no canonical twin beside it.
    canonical, warnings = canonicalize(data)
    log.extend(f"canonical: {warning}" for warning in warnings)
    for face in canonical["faces"]:
        dedupe_floor_canonical(face, log)
        dedupe_cross_layer_features_canonical(face, log)

    for face in data.get("trenchProfiles") or []:
        dedupe_floor(face, log)
        dedupe_cross_layer_features(face, log)

    json.dump(data, open(output_path, "w"), indent=2)
    canonical_path_for(output_path).write_text(
        json.dumps(canonical, indent=2), encoding="utf-8"
    )
    return data, log
