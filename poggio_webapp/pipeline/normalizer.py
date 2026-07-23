"""
normalizer.py — clean an extraction JSON before it feeds GemPy.
Adapted from 04_normalize_validate/normalizer.py into an importable function.
Logic unchanged.
"""

import json

NULLISH = {"null", "none", "n/a", ""}


def clean_null_strings(obj, log, path="root"):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str) and v.strip().lower() in NULLISH:
                obj[k] = None
                log.append(f'nulled string at {path}.{k}')
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
        out.append((round(x, 3) if x is not None else None,
                    round(y, 3) if y is not None else None))
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
            log.append(f'{face.get("face")}: dropped trench-floor feature '
                       f'(duplicates {deepest.get("layerName") or deepest.get("inferredMaterial")} bottom)')
            continue
        kept.append(f)
    deepest["featuresInLayer"] = kept or None


def dedupe_cross_layer_features(face, log):
    layers = face.get("layers") or []
    seen = {}
    for i, layer in enumerate(layers):
        for f in (layer.get("featuresInLayer") or []):
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
                log.append(f'{face.get("face")}: removed duplicate feature '
                           f'"{f.get("feature")}" from '
                           f'{layer.get("layerName") or layer.get("inferredMaterial")} '
                           f'(kept in deepest layer)')
                continue
            kept.append(f)
        layer["featuresInLayer"] = kept or None


def run_normalize(input_path: str, output_path: str):
    """Returns (cleaned_data_dict, log_list)."""
    data = json.load(open(input_path))
    log = []

    clean_null_strings(data, log)
    for face in data.get("trenchProfiles") or []:
        dedupe_floor(face, log)
        dedupe_cross_layer_features(face, log)

    json.dump(data, open(output_path, "w"), indent=2)
    return data, log
