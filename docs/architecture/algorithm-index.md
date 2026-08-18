---
title: Algorithm index
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/preprocess.py
  - poggio_webapp/pipeline/detect_markers.py
  - poggio_webapp/pipeline/detect_features.py
  - poggio_webapp/pipeline/manual_extraction.py
  - poggio_webapp/pipeline/normalizer.py
  - poggio_webapp/pipeline/validator.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/true_dip.py
  - poggio_webapp/pipeline/merge_walls.py
  - poggio_webapp/pipeline/build_gempy.py
  - poggio_webapp/pipeline/harris_matrix.py
  - poggio_webapp/pipeline/harris_suggestions.py
  - poggio_webapp/pipeline/harris_render.py
  - poggio_webapp/pipeline/editor/geometry.py
  - poggio_webapp/backend/harris_store.py
  - poggio_webapp/backend/tasks.py
  - poggio_webapp/backend/jobs.py
  - poggio_webapp/pipeline/site_vocab.py
  - poggio_webapp/pipeline/series_order.py
  - poggio_webapp/pipeline/provenance.py
  - poggio_webapp/pipeline/geospatial_sheet.py
  - poggio_webapp/pipeline/locus_import.py
  - poggio_webapp/naming.py
verified_against: ae2fc1d
---

# Algorithm index

What is in each module, so you can start from a file you are reading rather
than from a concept you already know the name of.

The [computer science concepts](../cs/index.md) catalogue is the same material
organised the other way, by subject, with one page per technique. The
[archaeology reference](../archaeology/index.md) does the same for the domain
terms these modules operate on.

## Image processing

| Module | Techniques |
|---|---|
| `pipeline/preprocess.py` | [Gaussian blur](../cs/gaussian-blur.md) · homomorphic illumination correction · [Canny edge detection](../cs/canny-edge-detection.md) · [Hough line transform](../cs/hough-line-transform.md) · median as a robust estimator · affine rotation · [Lanczos resampling](../cs/lanczos-resampling.md) · [CLAHE](../cs/clahe.md) · unsharp masking · adaptive thresholding |
| `pipeline/detect_markers.py` | [Adaptive thresholding](../cs/adaptive-thresholding.md) · colour-channel arithmetic · morphological opening · structuring elements · contour tracing · minimum enclosing circle · convex hull · circularity · solidity · fill ratio · greedy non-maximum suppression · [EXIF orientation](../cs/exif-orientation.md) control |
| `pipeline/detect_features.py` | [Multi-scale analysis](../cs/multi-scale-analysis.md) · area-averaging downsampling · Gaussian blur · median-adaptive Canny thresholds · morphological closing · contour tracing · bounding boxes · convex hull · circularity · solidity · extent · aspect ratio · Ramer–Douglas–Peucker · intersection-over-union · greedy non-maximum suppression |

## Geometry and coordinates

| Module | Techniques |
|---|---|
| `pipeline/manual_extraction.py` | Unit vectors · dot product · vector projection · orthonormal bases · 2D similarity transforms · piecewise-linear interpolation |
| `pipeline/convert_coords.py` | [Ordinary least squares](../cs/ordinary-least-squares.md) · compass bearings vs mathematical angles · rigid transforms · arctangent for dip |
| `pipeline/true_dip.py` | [Vector projection](../cs/vector-projection.md) · cross product · plane normals · ordinary least squares · `atan2` for compass azimuth |
| `pipeline/editor/geometry.py` | [Signed area and the orientation test](../cs/signed-area-and-orientation-test.md) · line-segment intersection · polygon self-intersection |
| `static/visualizer/layer-fill.mjs` | Vector projection · polyline clipping · linear interpolation · shoelace formula · polygon self-intersection |
| `static/canvas/grid.mjs` | [Grid snapping and quantisation](../cs/grid-snapping-and-quantisation.md) · orientation test · segment intersection · debouncing |

## Statistics and validation

| Module | Techniques |
|---|---|
| `pipeline/validator.py` | [Coefficient of variation](../cs/coefficient-of-variation.md) · mean and variance · piecewise-linear interpolation · epsilon comparison · error taxonomies · fabrication detection |
| `pipeline/normalizer.py` | Recursive tree traversal · composite keys for deduplication |

## Graphs

| Module | Techniques |
|---|---|
| `pipeline/harris_matrix.py` | [Directed acyclic graphs](../cs/directed-acyclic-graphs.md) · adjacency representations · depth-first search · three-colour cycle detection · Kahn's topological sort · heaps and priority queues · transitive reduction · [union-find](../cs/union-find.md) · connected components · graph quotients |
| `pipeline/merge_walls.py` | Kahn's topological sort · heaps · [union-find](../cs/union-find.md) · connected components · cycle isolation by peeling |
| `pipeline/series_order.py` | [Topological sorting](../cs/topological-sorting.md) (via `harris_matrix`) · reachability by [explicit-stack](../cs/stacks-and-explicit-recursion.md) traversal · [provenance labelling](../cs/provenance-and-data-lineage.md) of the order's source |
| `pipeline/harris_render.py` | Longest-path layering · layered graph drawing · deterministic ordering |

## Data, storage, and concurrency

| Module | Techniques |
|---|---|
| `backend/harris_store.py` | Optimistic concurrency control · atomic file writes · schema versioning · regular expressions for identifier validation |
| `backend/tasks.py` | Threads · locks and critical sections · bounded caches and eviction · runtime introspection |
| `backend/jobs.py` | Path traversal containment · tolerant versus strict reads |
| `pipeline/harris_suggestions.py` | SHA-256 hashing · content-addressed identifiers · idempotency · immutability and defensive copying · combinations |
| `pipeline/site_vocab.py` | Controlled vocabularies · [regular expressions](../cs/regular-expressions.md) for identifier parsing · frozen value objects · canonical construction with permissive parsing (see [find identifiers](../archaeology/find-identifiers.md) and [survey point codes](../archaeology/survey-point-codes.md)) |
| `pipeline/provenance.py` | [Regular expressions](../cs/regular-expressions.md) for link shapes · [input sanitisation](../cs/input-sanitisation.md) of operator-supplied identifiers, validated by shape and never fetched (see [provenance and data lineage](../cs/provenance-and-data-lineage.md)) |
| `pipeline/geospatial_sheet.py` | [Regular expressions](../cs/regular-expressions.md) for corner and trench-id labels · [error taxonomies](../cs/error-taxonomies.md) (per-trench refusals versus notes) |
| `pipeline/locus_import.py` | [Fail-closed design](../cs/fail-closed-design.md): explicit column maps, refusing an unrecognised export with its observed headers listed · [validation at trust boundaries](../cs/validation-at-trust-boundaries.md) |
| `naming.py` | Regular expressions · canonicalisation that declines to mangle what it does not recognise (see [trench](../archaeology/trench.md)) |
| `pipeline/build_gempy.py` | Endianness and binary serialisation · spatial interpolation (via GemPy) · mesh validation · schema versioning |
| `static/visualizer/volume3d-core.mjs` | Endianness-safe decoding · C-order indexing · golden-angle colour assignment |

## Related concepts

- [Computer science concepts](../cs/index.md): one page per technique.
- [Pipeline architecture](pipeline.md): the stages these modules form.
- [Backend architecture](backend.md): how routes, services, and pipeline relate.
