# The computer science course

A study plan through this repository's **Computer science section only** —
the 128 per-technique pages plus their index — for someone with one basic
computer science course who wants the algorithms and engineering without the
archaeology. The excavation appears only as the worked example each
technique is grounded in.

This is the CS spine of [the full course](plan.md), reorganized: finer
units, fresh assessments, no workflow or archaeology phases. If you have
already done the full course's phases 6–8, the reading below will be
familiar; the [assessments](cs-assessments.md) are all new, so the exams
and projects still have value. If you are deciding between courses: take
this one to learn computer science using the repository as a textbook; take
the full course to learn the repository.

## The material

Everything lives in the **Computer science** section of the docs
([its index](../cs/index.md)), 128 pages in twenty clusters, each page the
same seven sections: *What it is · The picture · Where this project uses
it · Why this and not something else · What it costs · Where else you meet
it · Related pages*.

Two rules carry the whole course:

1. **Never skip "Why this and not something else."** The index says it
   plainly: that is where the engineering judgement lives. "What it is" you
   can find in any textbook; the alternatives-and-costs reasoning is what
   this catalogue does better than textbooks.
2. **Do every worked numeric example by hand.** The pages are written so
   that a reader with one CS course can follow the arithmetic. Following it
   with a pencil is what makes it stick; reading it is what makes it feel
   stuck when it isn't.

The [algorithm index](../architecture/algorithm-index.md) is the same
catalogue sorted by source module instead of by subject. You will use it in
Unit 9 to prove to yourself the techniques actually live somewhere.

## What you need

- Python 3.11+, a terminal, and the repository — Unit 0 sets up the
  virtual environment. You will write and run small experiments constantly;
  you will rarely need to run the web application itself.
- **Thirty minutes of project context**, once, in Unit 0: the pages assume
  you know what a trench drawing is being turned into. You do not need the
  archaeology; you need the pipeline's outline so "Where this project uses
  it" excerpts make sense.
- The two notes files from day one: a personal glossary in your own words,
  and a **confusables table** (erosion/opening, BFS/DFS, affine/similarity,
  validation/sanitisation — the catalogue is full of near-neighbour pairs).

## Size, honestly

About 149,000 words of technical prose — the CS section is three fifths of
the entire documentation. With the assessment pack, this is a full
university-course workload:

| Unit | Clusters | Pages | Hours (reading + assessments) |
|---|---|---|---|
| 0 — Orientation | index, context, setup | 2 + context | 4–6 |
| 1 — Pixels and enhancement | Images and pixels · Filtering and enhancement | 15 | 10–13 |
| 2 — Black and white | Thresholding and masks · Morphology | 10 | 8–10 |
| 3 — Edges, contours, shape | Edges, lines, and contours · Shape description · Candidate filtering | 20 | 12–15 |
| 4 — Vectors and transforms | Vectors and linear algebra · Transforms | 12 | 10–13 |
| 5 — Geometry and numbers | Computational geometry · Numerical methods and statistics | 16 | 11–14 |
| 6 — Graphs and structures | Graphs · Data structures | 16 | 11–14 |
| 7 — Bytes, threads, failure | Hashing, encoding, serialisation · Concurrency · Reliability | 18 | 11–14 |
| 8 — Boundaries and honesty | Validation · Architecture · Security · Scientific computing practice | 21 | 12–15 |
| 9 — Synthesis | algorithm index, pipeline mapping, capstone | — | 12–16 |
| **Total** | | **128** | **~100–130** |

At ~10 hours a week that is roughly **12 weeks** — a unit a week, with
Units 0 and 2 lighter and the capstone heavier. The honest trims: skip the
research papers (−20–25 h), or do only the unit finals plus the capstone.
Do not trim the programming assignments; as in the full course, they are
where the digestion happens.

## How to study it

- **Read a cluster in nav order** — the clusters are dependency chains
  (convolution before Gaussian blur before Sobel before Canny), and the
  units below never split a chain.
- **2–4 pages per sitting.** A page is ~1,150 words with arithmetic to do.
  Alternate reading days with assignment days.
- **Anchor in the assignments, not the app.** The full course anchors these
  pages to workflow steps; here, each unit's programming assignment is the
  anchor — read a few pages, build the piece that uses them, repeat.
- **Trust the excerpts.** Every page's "Where this project uses it" quotes
  the real module. When curious, open the file it names; the front matter
  lists the paths.
- Every assessment for every unit — pre-reading quiz, programming
  assignment, research paper, midterm, final — is in
  [the CS assessment pack](cs-assessments.md), same ground rules as the
  full course: keys in collapsed blocks, 80% pass bar, honor-system timing.

---

## The units

### Unit 0 — Orientation (2–3 h reading)

**Read:** the [quickstart](../start-here/quickstart.md) far enough to have
a working `.venv` at the repository root (you may skip launching the app);
[what this project does](../start-here/what-this-project-does.md) and the
pipeline diagram on the [home page](../index.md) — your thirty minutes of
context; then the [CS index](../cs/index.md) top to bottom, and a skim of
the [algorithm index](../architecture/algorithm-index.md) to learn what it
is.

**Do:** the Unit 0 assessments — the assignment builds the little
experiment harness the rest of the course reuses.

**Checkpoint:** recite the seven sections of a CS page and say which one
you are forbidden to skip; explain the difference between the CS index and
the algorithm index; name the seven pipeline boxes from the diagram,
labels only — that is all the archaeology this course requires.

### Unit 1 — Pixels and enhancement (15 pages, ~4–5 h reading)

**Read:** *Images and pixels* (6 pages: raster images, colour spaces,
grayscale, colour-channel arithmetic, bit depth, EXIF orientation), then
*Filtering and enhancement* (9: convolution through area-averaging
downsampling). Convolution is the most important page in the unit — the
one mechanism most of image processing is built from.

**Checkpoint:** hand-convolve a 3×3 neighbourhood; state the sum-to-1 /
sum-to-0 kernel rules; explain why CLAHE exists when histogram
equalisation already does; predict which resampling filter to use for
shrinking a photo versus enlarging line art.

### Unit 2 — Black and white (10 pages, ~3 h reading)

**Read:** *Thresholding and masks* (5: global, Otsu, adaptive, binary
masks and bitwise operations, connected-component labelling), then
*Morphology* (5: structuring elements, erosion, dilation, opening,
closing).

**Checkpoint:** choose global versus Otsu versus adaptive for three
described scans and defend each; erode and dilate a small grid by hand;
answer "specks or gaps?" with the right operation without thinking.

### Unit 3 — Edges, contours, and shape (20 pages, ~5–6 h reading)

**Read:** *Edges, lines, and contours* (7: gradients and Sobel, Canny,
edge thinning, hysteresis, Hough, contour tracing, contour hierarchy),
*Shape description* (9: area/perimeter through Ramer–Douglas–Peucker), and
*Candidate filtering* (4: IoU, non-maximum suppression, greedy algorithms,
multi-scale analysis). The biggest unit; take the full week.

**Checkpoint:** recite Canny's stages and defend the two thresholds;
compute area, perimeter, circularity, and solidity for a small polygon;
run one round of NMS by hand given boxes and scores.

### Unit 4 — Vectors and transforms (12 pages, ~4 h reading; the steepest math)

**Read:** *Vectors and linear algebra* (7: vectors and magnitude, unit
vectors, dot product, projection, cross product, plane normals,
orthonormal bases), then *Transforms* (5: translation/rotation/scaling,
similarity, affine, homogeneous coordinates, compass bearings versus
mathematical angles). Budget extra time; do every example twice.

**Checkpoint:** compute a dot product, a projection, and a 2D cross
product cold; rotate a point and explain rotate-then-translate versus
translate-then-rotate; convert compass 240° to a math angle without notes.

### Unit 5 — Geometry and numbers (16 pages, ~4–5 h reading)

**Read:** *Computational geometry* (9: signed area and orientation,
shoelace, segment intersection, polygon self-intersection, point in
polygon, polyline clipping, linear interpolation, piecewise-linear
functions, grid snapping), then *Numerical methods and statistics* (7:
floating point, epsilon comparison, mean and variance, coefficient of
variation, median and robust statistics, least squares, kriging).

**Checkpoint:** shoelace a quadrilateral; decide point-in-polygon by ray
casting including one edge case; explain why `0.1 + 0.2 != 0.3` and what
to do about it; say what kriging reports that linear interpolation cannot.

### Unit 6 — Graphs and the structures beneath (16 pages, ~4–5 h reading)

**Read:** *Graphs* (11: terminology, DAGs, adjacency representations,
DFS, BFS, cycle detection, topological sorting, transitive reduction,
Union-Find, connected components, layered drawing), then *Data
structures* (5: hash tables, sets, heaps, stacks and explicit recursion,
bounded caches).

**Checkpoint:** topologically sort a small DAG and say whether the order
is unique; find the redundant edge transitive reduction removes; explain
why the flood fill you will have written in Unit 2's assignment was
secretly BFS; pick hash table / heap / stack for three described jobs.

### Unit 7 — Bytes, threads, and things that fail (18 pages, ~5 h reading)

**Read:** *Hashing, encoding, and serialisation* (6: SHA-256,
content-addressed identifiers, endianness, binary serialisation, JSON and
schema design, regular expressions), *Concurrency and shared state* (5:
threads and the GIL, locks, race conditions, optimistic concurrency,
atomic file writes), then *Reliability* (7: idempotency, immutability,
determinism and stable sorting, exponential backoff, retry budgets,
fail-closed design, debouncing and throttling).

**Checkpoint:** decode two bytes as a 16-bit integer in both endiannesses;
narrate a lost-update race step by step; recite the atomic write pattern
and why the rename must stay on one filesystem; compute a backoff schedule
and say what jitter and a budget each protect.

### Unit 8 — Boundaries, blueprints, and honest computing (21 pages, ~5–6 h reading)

**Read:** *Validation and error handling* (4), *Architecture* (8: layered
architecture, dependency direction, application factory, blueprint
registries, late binding, closure capture, separation of concerns, pure
functions), *Security* (4: path traversal, input sanitisation,
decompression bombs, same-origin validation), and last — slowly —
*Scientific computing practice* (5: provenance, human-in-the-loop,
two-phase commit with review, fabrication detection, interpolation versus
measurement). That final cluster is the catalogue's worldview; by now you
will recognize every example in it.

**Checkpoint:** list three trust boundaries in any program you have
written this course; state which direction layered dependencies may point
and what a leaf module is; give the path-traversal attack string and two
independent fixes; explain in two sentences why a system must record
whether a value was measured or interpolated.

### Unit 9 — Synthesis (reading light; capstone heavy)

**Do:** reread the [CS index](../cs/index.md) — every line should now be a
face, not a name. Open the
[algorithm index](../architecture/algorithm-index.md), pick five modules,
and from each one's technique list say what the module does before reading
its description. Read [the pipeline](../architecture/pipeline.md) once,
mapping each stage to the units that explained it. Then the Unit 9
assessments: the integration midterm, the capstone build, and the course
final.

**Checkpoint:** the capstone runs on input you photographed yourself, and
you can narrate one pixel's journey through it naming a technique from
every unit.

---

## A calendar that works

| Week | Units | Milestone |
|---|---|---|
| 1 | 0 + start 1 | Harness built; convolution by hand |
| 2 | 1 | Darkroom assignment done |
| 3 | 2 | Whiteboard rescue done |
| 4–5 | 3 | Leaf field guide done |
| 6 | 4 | Flock simulation done |
| 7 | 5 | Gerrymander detector done |
| 8 | 6 | Spreadsheet engine done |
| 9 | 7 | Save-game vault done |
| 10 | 8 | Hardened notebook done |
| 11–12 | 9 | Capstone + course final |

Half pace: double every row.

## When you get stuck

- A term you half-know → the page's own **Related pages** footer, or the
  [CS index](../cs/index.md) — the clusters are small; the neighbour you
  need is adjacent.
- Arithmetic that won't come out → redo the page's worked example first;
  every exam question in the pack is a cousin of one.
- "Where would I ever use this?" → the page's **Where else you meet it**
  section, then its excerpt in the real module.
- Lost altogether → ask "which pipeline stage would use this?" and reread
  [the pipeline](../architecture/pipeline.md); the CS section is that page,
  expanded 128 times.
