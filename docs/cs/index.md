---
title: Computer science concepts
audience: developer
status: current
source_files:
  - poggio_webapp/pipeline/preprocess.py
  - poggio_webapp/pipeline/detect_markers.py
  - poggio_webapp/pipeline/detect_features.py
  - poggio_webapp/pipeline/convert_coords.py
  - poggio_webapp/pipeline/true_dip.py
  - poggio_webapp/pipeline/merge_walls.py
  - poggio_webapp/pipeline/harris_matrix.py
  - poggio_webapp/backend/tasks.py
  - poggio_webapp/backend/jobs.py
verified_against: ae2fc1d
---

# Computer science concepts

Every algorithm, data structure, and engineering principle this repository
uses, one page each.

These pages are written for someone who knows the archaeology and not the
computer science. Each one starts from the idea in plain language, shows the
exact place this project uses it, and — the part that is usually missing —
explains **why that technique rather than the obvious alternative**. A
technique chosen for a reason is a technique a future maintainer can change
safely.

## How to read a concept page

Every page has the same seven sections.

| Section | Answers |
|---|---|
| **What it is** | The idea, in plain language, with no code |
| **The picture** | A diagram or a worked example with real numbers |
| **Where this project uses it** | The actual file and function, with the real excerpt |
| **Why this and not something else** | The alternatives that were available, and what each would have cost |
| **What it costs** | Time and memory complexity, and whether that matters at this scale |
| **Where else you meet it** | The same idea in other software you have used |
| **Related pages** | Neighbouring concepts and the workflow steps that depend on this one |

If you only read one section, read **Why this and not something else**. That is
where the engineering judgement lives.

## Two views of the same material

- This page groups concepts **by subject**, the way a textbook would.
- The [algorithm index](../architecture/algorithm-index.md) groups them **by
  source module**, so you can start from a file you are reading and find out
  what is in it.

## The catalogue

One hundred and twenty-eight pages. This list is the contract: it is what
"every concept this repository uses" means, and a technique missing from it is
a gap rather than a decision.

### Images and pixels

- [Raster images and pixels](raster-images-and-pixels.md) · [Colour spaces and channels](colour-spaces-and-channels.md) · [Grayscale conversion](grayscale-conversion.md)
- [Colour-channel arithmetic](colour-channel-arithmetic.md) · [Bit depth and dynamic range](bit-depth-and-dynamic-range.md) · [EXIF orientation](exif-orientation.md)

### Filtering and enhancement

- [Convolution](convolution.md) · [Gaussian blur](gaussian-blur.md) · [Homomorphic illumination correction](homomorphic-illumination-correction.md)
- [Histogram equalisation](histogram-equalisation.md) · [CLAHE](clahe.md) · [Unsharp masking](unsharp-masking.md)
- [Bilinear and bicubic interpolation](bilinear-and-bicubic-interpolation.md) · [Lanczos resampling](lanczos-resampling.md) · [Area-averaging downsampling](area-averaging-downsampling.md)

### Thresholding and masks

- [Global thresholding](global-thresholding.md) · [Otsu's method](otsu-thresholding.md) · [Adaptive thresholding](adaptive-thresholding.md)
- [Binary masks and bitwise operations](binary-masks-and-bitwise-operations.md) · [Connected-component labelling](connected-component-labelling.md)

### Morphology

- [Structuring elements](structuring-elements.md) · [Erosion](erosion.md) · [Dilation](dilation.md)
- [Morphological opening](morphological-opening.md) · [Morphological closing](morphological-closing.md)

### Edges, lines, and contours

- [Image gradients and Sobel](image-gradients-and-sobel.md) · [Canny edge detection](canny-edge-detection.md)
- [Edge thinning (non-maximum suppression)](edge-thinning-non-maximum-suppression.md) · [Hysteresis thresholding](hysteresis-thresholding.md)
- [Hough line transform](hough-line-transform.md) · [Contour tracing](contour-tracing.md) · [Contour hierarchy](contour-hierarchy.md)

### Shape description

- [Contour area and perimeter](contour-area-and-perimeter.md) · [Bounding boxes](bounding-boxes.md) · [Minimum enclosing circle](minimum-enclosing-circle.md)
- [Convex hull](convex-hull.md) · [Circularity](circularity.md) · [Solidity](solidity.md)
- [Extent and fill ratio](extent-and-fill-ratio.md) · [Aspect ratio](aspect-ratio.md) · [Ramer–Douglas–Peucker simplification](ramer-douglas-peucker.md)

### Candidate filtering

- [Intersection over union](intersection-over-union.md) · [Non-maximum suppression](non-maximum-suppression.md)
- [Greedy algorithms](greedy-algorithms.md) · [Multi-scale analysis](multi-scale-analysis.md)

### Vectors and linear algebra

- [Vectors and magnitude](vectors-and-magnitude.md) · [Unit vectors and normalisation](unit-vectors-and-normalisation.md)
- [Dot product](dot-product.md) · [Vector projection](vector-projection.md)
- [Cross product](cross-product.md) · [Plane normals](plane-normals.md) · [Orthonormal bases](orthonormal-bases.md)

### Transforms

- [Translation, rotation, and scaling](translation-rotation-scaling.md) · [Similarity transforms](similarity-transforms.md) · [Affine transforms](affine-transforms.md)
- [Homogeneous coordinates](homogeneous-coordinates.md) · [Compass bearings versus mathematical angles](compass-bearings-vs-mathematical-angles.md)

### Computational geometry

- [Signed area and the orientation test](signed-area-and-orientation-test.md) · [Shoelace formula](shoelace-formula.md)
- [Line segment intersection](line-segment-intersection.md) · [Polygon self-intersection](polygon-self-intersection.md) · [Point in polygon](point-in-polygon.md)
- [Polyline clipping](polyline-clipping.md) · [Linear interpolation](linear-interpolation.md) · [Piecewise-linear functions](piecewise-linear-functions.md)
- [Grid snapping and quantisation](grid-snapping-and-quantisation.md)

### Numerical methods and statistics

- [Floating-point representation](floating-point-representation.md) · [Epsilon comparison](epsilon-comparison.md)
- [Mean and variance](mean-and-variance.md) · [Coefficient of variation](coefficient-of-variation.md) · [Median and robust statistics](median-and-robust-statistics.md)
- [Ordinary least squares](ordinary-least-squares.md) · [Spatial interpolation and kriging](spatial-interpolation-and-kriging.md)

### Graphs

- [Graphs and terminology](graphs-and-terminology.md) · [Directed acyclic graphs](directed-acyclic-graphs.md) · [Adjacency representations](adjacency-representations.md)
- [Depth-first search](depth-first-search.md) · [Breadth-first search](breadth-first-search.md) · [Cycle detection](cycle-detection.md)
- [Topological sorting](topological-sorting.md) · [Transitive reduction](transitive-reduction.md)
- [Union-Find (disjoint sets)](union-find.md) · [Connected components](connected-components.md) · [Layered graph drawing](layered-graph-drawing.md)

### Data structures

- [Hash tables](hash-tables.md) · [Sets and membership](sets-and-membership.md) · [Heaps and priority queues](heaps-and-priority-queues.md)
- [Stacks and explicit recursion](stacks-and-explicit-recursion.md) · [Bounded caches and eviction](bounded-caches-and-eviction.md)

### Hashing, encoding, and serialisation

- [Hash functions and SHA-256](hash-functions-and-sha256.md) · [Content-addressed identifiers](content-addressed-identifiers.md)
- [Endianness](endianness.md) · [Binary serialisation](binary-serialisation.md) · [JSON and schema design](json-schema-design.md) · [Regular expressions](regular-expressions.md)

### Concurrency and shared state

- [Threads and the GIL](threads-and-the-gil.md) · [Locks and critical sections](locks-and-critical-sections.md) · [Race conditions](race-conditions.md)
- [Optimistic concurrency control](optimistic-concurrency-control.md) · [Atomic file writes](atomic-file-writes.md)

### Reliability

- [Idempotency](idempotency.md) · [Immutability and defensive copying](immutability-and-defensive-copying.md) · [Determinism and stable sorting](determinism-and-stable-sorting.md)
- [Exponential backoff](exponential-backoff.md) · [Retry budgets](retry-budgets.md) · [Fail-closed design](fail-closed-design.md)
- [Debouncing and throttling](debouncing-and-throttling.md)

### Validation and error handling

- [Validation at trust boundaries](validation-at-trust-boundaries.md) · [Error taxonomies](error-taxonomies.md)
- [Schema versioning](schema-versioning.md) · [Structural versus schema validation](structural-vs-schema-validation.md)

### Architecture

- [Layered architecture](layered-architecture.md) · [Dependency direction and leaf modules](dependency-direction-and-leaf-modules.md)
- [Application factory](application-factory.md) · [Blueprint and plugin registries](blueprint-and-plugin-registries.md)
- [Late binding versus import-time binding](late-binding-vs-import-time-binding.md) · [Closure late-binding capture](closure-late-binding-capture.md)
- [Separation of concerns](separation-of-concerns.md) · [Pure functions and testability](pure-functions-and-testability.md)

### Security

- [Path traversal and containment](path-traversal-and-containment.md) · [Input sanitisation](input-sanitisation.md)
- [Decompression bombs](decompression-bombs.md) · [Same-origin URL validation](same-origin-url-validation.md)

### Scientific computing practice

- [Provenance and data lineage](provenance-and-data-lineage.md) · [Human-in-the-loop review](human-in-the-loop-review.md)
- [Two-phase commit with review](two-phase-commit-with-review.md) · [Fabrication detection](fabrication-detection.md)
- [Interpolation versus measurement](interpolation-vs-measurement.md)

## Related concepts

- [Algorithm index](../architecture/algorithm-index.md) lists the same
  techniques by the module that uses them.
- [Pipeline architecture](../architecture/pipeline.md) describes the stages
  these techniques are arranged into.
- [Archaeology reference](../archaeology/index.md) does the same job in the
  other direction, for readers who know the code and not the excavation.
