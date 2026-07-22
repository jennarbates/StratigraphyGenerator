"""
normalizer.py — clean an extraction JSON before it feeds GemPy.

Usage:
    python normalizer.py input.json [output.json]
    (default output: <input>_clean.json)

Idempotent and non-destructive: reads input, writes a cleaned copy, prints a
change log.

Fixes applied:
  1. Convert literal "null"/"none"/"n/a" strings to real null.
  2. Drop a trench-floor FEATURE when its points duplicate the deepest layer's
     bottomBoundary (keep the boundary, remove the redundant feature).
  3. De-duplicate a feature that was copied into more than one layer: keep it in
     the single deepest layer it appears in, remove the copies. (Features that
     "span layers" should live once, on their primary layer.)
  4. Report — but do NOT alter — geometry, so you always see what changed.
"""

import json
import sys


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
    """Hashable signature of a shapePoints/boundary list for comparison."""
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
    """Remove a trench-floor feature that just repeats the deepest layer bottom."""
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
    """If the same feature (by name+points) appears in multiple layers, keep it
    only in the deepest occurrence."""
    layers = face.get("layers") or []
    seen = {}   # signature -> index of deepest layer holding it
    # first pass: find the deepest layer index per signature
    for i, layer in enumerate(layers):
        for f in (layer.get("featuresInLayer") or []):
            sig = ((f.get("feature") or "").lower(), points_key(f.get("shapePoints")))
            if sig[1] is None:
                continue  # discrete objects (approx*) aren't cross-layer dupes
            seen[sig] = i   # later i overwrites -> deepest wins
    # second pass: drop copies not in the deepest layer
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


def main():
    if len(sys.argv) < 2:
        print("usage: python normalize.py input.json [output.json]")
        sys.exit(2)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit(".", 1)[0] + "_clean.json"

    data = json.load(open(inp))
    log = []

    clean_null_strings(data, log)
    for face in data.get("trenchProfiles") or []:
        dedupe_floor(face, log)
        dedupe_cross_layer_features(face, log)

    json.dump(data, open(out, "w"), indent=2)

    if log:
        print("Changes:")
        for line in log:
            print("  -", line)
    else:
        print("No changes needed.")
    print(f"\nWrote {out} ({len(log)} change(s)).")


if __name__ == "__main__":
    main()