---
title: CS assessments
audience: beginner
status: current
source_files:
  - mkdocs.yml
  - poggio_webapp/pipeline/convert_coords.py
verified_against: de07c37
---

# Assessments for the computer science course

A companion to [the CS study plan](cs-plan.md). Each of the ten units gets
five assessments: a **pre-reading quiz** before opening the unit's pages, a
**programming assignment**, a **research paper**, a **midterm** partway
through, and a **final** at the end.

Same design rule as the full course: quizzes and exams face the
documentation; **programming and research assignments face away from it** —
same subject, different world. If a technique only works for you inside
trench drawings, you memorized a page; if it works on a whiteboard photo, a
voting map, or a save file, you learned the technique. All assignments and
papers here are new — none are shared with the full course, so both packs
can be taken by the same person.

| Unit | Programming assignment (domain) | Research paper (domain) |
|---|---|---|
| 0 | Experiment harness (benchmarking) | Docs-as-code (technical writing) |
| 1 | The Digital Darkroom (photography) | The Bayer filter (camera engineering) |
| 2 | Whiteboard Rescue (office life) | Morphology's mining-school origin (history of science) |
| 3 | The Leaf Field Guide (botany) | Reading the mail: postal OCR (automation history) |
| 4 | Flock + Kaleidoscope (simulation, art) | How GPS finds you (navigation) |
| 5 | The Gerrymander Detector (civics) | The Challenger data (engineering statistics) |
| 6 | A Tiny Spreadsheet + maze solver (office tools, games) | Choose: PageRank, critical paths, or package managers |
| 7 | The Save-Game Vault + race lab (games, systems) | Idempotency keys in payments (fintech) |
| 8 | The Hardened Lab Notebook (science tooling) | The reproducibility crisis (research practice) |
| 9 | The Meter Reader capstone (home telemetry) | One real pipeline, mapped (your choice of field) |

## Ground rules

Identical to the full course's pack: self-graded; answer keys in collapsed
blocks you open only when finished; **pass bar 80%**, equal question weight
unless a key states otherwise; timing on the honor system; criteria keys
list what a good answer contains; where a key defers to a docs page, the
page wins. Pre-reading quizzes are ungraded diagnostics.

Inside Claude Code, the `grade-assessment` skill grades any quiz or exam
here against its key — say which unit and which assessment. Each quiz and
exam also has a **Copy for feedback** button when this page is served
locally.

---

## Unit 0 — Orientation

*Subject: the environment, reading this catalogue, and enough project
context to parse the excerpts.*

### Pre-reading quiz (10 minutes)

1. What is an algorithm, in one sentence of your own?
2. `python3 -m venv .venv` — what do the two dots-and-names at the end
   each mean?
3. You must look up how one function works, fifty times over a semester.
   What decides whether that is fine or a problem?
4. A cookbook can be organized by ingredient or by occasion. Why might a
   technique catalogue need two orderings too?
5. True or false: to understand code that processes drawings of trenches,
   you must first understand trenches.
6. Estimate: how many times longer does it take to *check* whether an item
   is in an unsorted list of a million things versus a list of ten things?
7. What is a pipeline, and why do builders of software like them?
8. When a textbook shows a worked numeric example, what is the difference
   between reading it and doing it?

<details markdown="1">
<summary>Answer key</summary>

1. A finite, unambiguous recipe: steps that take input to output. Any
   faithful phrasing passes.
2. `venv` is the module being run; `.venv` is the folder the new
   environment is created in.
3. Whether looking up is cheap and reliable — which is why this course
   trains navigation (index, algorithm index, Related pages) before
   content.
4. Different questions arrive: "teach me thresholding" wants by-subject;
   "what is this file doing" wants by-module. This repository ships both.
5. False — and this course is the proof it intends to construct. You need
   the pipeline's outline, not the discipline.
6. About 100,000× — scanning scales with length. Unit 6 gives you the
   structure that makes it roughly constant instead.
7. Stages, each consuming the previous stage's output, each inspectable.
   Builders like them because problems localize to a stage.
8. Reading rents the understanding; doing buys it. This course's rule is
   pencil first.

</details>

### Programming assignment — The Experiment Harness (3–4 hours)

Build the little lab you will reuse all course. Benchmarking domain, no
archaeology, no images yet.

**Spec:**

- A fresh `.venv` at the repository root if Unit 0's reading did not
  already create one, and a `lab/` folder (gitignored or outside the repo —
  your choice, note it in the README).
- `lab/harness.py` exposing two helpers: `timeit_ms(fn, *args)` returning
  median milliseconds over repeated runs, and `table(rows)` printing
  aligned columns.
- Two experiments using them, each a small script with a one-paragraph
  written conclusion:
  1. **Membership**: build a list and a set of N random integers for
     N = 1,000 / 100,000 / 1,000,000; time `x in list` versus `x in set`
     for hits and misses. State the shape of the growth you observe. (You
     will meet the explanation in Unit 6; write the observation now.)
  2. **Copy versus alias**: time copying a million-element list versus
     aliasing it, and demonstrate with a two-line example why the fast one
     is dangerous.
- A README in the workflow-page shape (*Before you start → Do this →
  Check your result → Common problems*).

**Rubric (100):** harness helpers correct 30 · membership experiment with
honest conclusion 30 · copy/alias experiment with the danger demo 25 ·
README 15.

### Research paper — Docs-as-Code (800–1,200 words)

This repository's documentation is Markdown in git, built by MkDocs,
checked by scripts in CI. That is a philosophy with a history. Trace it:
man pages → wikis → docs-as-code. What problems did each stage fix, what
did it break, and which of this repository's four documentation checkers
would have been impossible in a wiki? **At least 3 sources.**

**Rubric (100):** the three eras fairly described 40 · the tradeoff
analysis 35 · the checker connection 25.

### Midterm exam — navigation practical (25 minutes, open docs — that is the point)

Timed lookups. Answer and cite the page you found it on; a right answer
without its page is half credit.

1. Which cluster holds the page on Otsu's method, and what are its two
   neighbouring pages in nav order?
2. Find the technique page whose subject is choosing *which overlapping
   detection to keep*. Name it.
3. Using the algorithm index only: name one technique listed for the
   module that builds the Harris matrix.
4. On any CS page you choose: quote its "Why this and not something else"
   heading's first alternative considered.
5. Which cluster would explain why two floating-point numbers that should
   be equal are not?
6. A page's front matter names `source_files`. What are you entitled to
   conclude if the page and that file disagree?

<details markdown="1">
<summary>Answer key</summary>

1. Thresholding and masks; between Global thresholding and Adaptive
   thresholding.
2. Non-maximum suppression (Candidate filtering cluster).
3. Any technique the index lists for `pipeline/harris_matrix.py` — e.g.
   cycle detection, topological sorting, transitive reduction (verify
   against the index).
4. Graded on the citation being real.
5. Numerical methods and statistics (floating-point representation,
   epsilon comparison).
6. The file wins; the page is due a fix. Front matter tells you where to
   look.

</details>

### Final exam (30 minutes, closed docs)

1. Name the seven sections of a CS page, in order.
2. Which section is the one this course forbids skipping, and what is in
   it that a textbook usually lacks?
3. The CS index and the algorithm index: same content, different what?
   When do you reach for each?
4. Recite the seven pipeline boxes (labels only), and state which single
   box Units 1–3 of this course live inside.
5. What does the label *synthetic documentation example* promise, and why
   does even a CS-only reader need to honor it?
6. Your `.venv` is at the repository root. Why there and not inside some
   subfolder?
7. From the quiz's membership experiment: what did you observe, and which
   unit owes you the explanation?

<details markdown="1">
<summary>Answer key</summary>

1. What it is · The picture · Where this project uses it · Why this and
   not something else · What it costs · Where else you meet it · Related
   pages.
2. "Why this and not something else" — the alternatives that were
   available and what each would have cost: the judgement, not the recipe.
3. Different sort order: by subject versus by source module. Subject when
   learning a topic; module when reading a file.
4. Prepare → trace/import/extract → normalize → validate → convert →
   build → view. Units 1–3 live in *prepare* (and the extraction side of
   the trace box).
5. The data is invented and safe to copy, never evidence. Copying an
   invented coordinate into anything real-looking poisons it — the same
   discipline applies to benchmark numbers you made up.
6. Every `make` target resolves tools from the root `.venv`; elsewhere,
   `make run`, `make test`, and `make docs` all fail to find them.
7. Set membership stayed roughly flat while list membership grew with N;
   Unit 6 (hash tables, sets and membership) explains why.

</details>

---

## Unit 1 — Pixels and enhancement

*Subject: images as numbers; convolution and the enhancement family.*

### Pre-reading quiz (10 minutes)

1. A "12-megapixel" photo — twelve million of what, each holding what?
2. Why do photos taken at night look grainy?
3. Screens mix red, green, and blue light; printers mix cyan, magenta,
   and yellow ink. Why are the two sets different?
4. Guess: to store "how bright," how many distinct levels does an
   ordinary photo use per channel — 16, 256, or 65,536?
5. Your phone photographs a receipt in dim warm light. Name two distinct
   things "fixing" that image might mean.
6. What would happen if you replaced every pixel with the average of the
   nine pixels around it?
7. Shrinking a 4000-pixel-wide photo to 400 wide throws away 99% of the
   pixels. Why does the result usually still look right?
8. Sideways phone photos: where might a camera hide the fact that the
   photo was taken rotated?

<details markdown="1">
<summary>Answer key</summary>

1. Pixels; each holds three intensity numbers (red, green, blue).
2. Little light means the sensor's measurement noise is large relative to
   the signal — grain is noise made visible.
3. Screens emit light (additive: sum toward white); ink absorbs it
   (subtractive: sum toward black). Same colours, opposite arithmetic.
4. 256 — 8 bits per channel. The bit-depth page is about when that is
   not enough.
5. Brightening/contrast (tonal), colour correction (white balance),
   sharpening, denoising — any two distinct ones.
6. A blur: detail averages away. You have just invented the box filter.
7. Neighbouring pixels are highly redundant; good downsampling averages
   areas rather than picking survivors — which is exactly the
   area-averaging page.
8. In metadata — an EXIF orientation tag — which software must read and
   apply, or the pixels arrive sideways.

</details>

### Programming assignment — The Digital Darkroom (7–9 hours)

Tonal and colour work on your own photographs — the clusters' arithmetic,
none of the project's subject matter. Pillow (or equivalent) for load and
save only; every pixel operation is your own loops over pixel data.
Work at ≤ 800 px on the long side.

**Build, as one CLI (`python darkroom.py <op> in.jpg out.jpg`):**

1. `grayscale` — luminosity weights, and a README sentence on why not the
   plain average.
2. `brightness ±n` and `contrast k` — channel arithmetic with clamping;
   show in the README one example where clamping visibly destroys detail
   (bit depth in action).
3. `whitebalance` — scale channels so a user-chosen "should be neutral"
   pixel becomes gray.
4. `sepia` — a 3×3 channel-mixing matrix.
5. `vignette` — darken with distance from centre (a radial mask you
   compute).
6. `grain n` — add noise; then rescue it with `blur` (box, via your own
   3×3 convolution loop) and describe the tradeoff you see.
7. `equalize` — global histogram equalisation on the grayscale image;
   include a before/after where it helps and one where it overdoes it
   (your CLAHE motivation, observed firsthand).
8. `resize` — nearest-neighbour and bilinear, side by side, on a photo
   and on a screenshot of text; two README sentences on which wins where
   and why.
9. A contact sheet of every operation applied to one photo of yours.

**Rubric (100):** operations correct 45 · the four asked-for README
analyses (clamping, grain/blur, equalize limits, resize comparison) 30 ·
contact sheet 10 · code clarity 15.

### Research paper — One Sensor, Three Colours: the Bayer Filter (1,500–2,000 words)

A camera sensor measures one number per site, yet produces three per
pixel. Research the Bayer mosaic and demosaicing: what the pattern is, why
green gets half the sites, how interpolation fills the missing channels,
and one artifact (moiré, zippering) that betrays the process. Include a
hand-worked 2×2 or 3×3 demosaic example with numbers you invent. **At
least 4 sources**, one from photography or sensor engineering rather than
a programming tutorial.

**Rubric (100):** mosaic and rationale 30 · demosaicing explained via
your worked example 40 · the artifact, honestly connected to
interpolation 20 · sources 10.

### Midterm exam (40 minutes, closed docs, calculator allowed — take after the *Images and pixels* cluster)

1. A pixel is (200, 100, 50). Compute its luminosity grayscale with
   weights 0.299 R + 0.587 G + 0.114 B (nearest integer).
2. Same pixel: what colour family is it, and what would (50, 100, 200)
   be? What single operation swaps warm for cool here?
3. Two images are subtracted channel-by-channel. What do large values in
   the result mean, and name one use for that.
4. 8 bits per channel: how many distinct values? You brighten a dark
   image by multiplying by 4 — what happens at both ends of the range,
   and what is the visible artifact called when smooth gradients turn to
   stripes?
5. Your program ignores EXIF orientation. Describe the bug report you
   will receive.
6. Why does grayscale weight green highest?

<details markdown="1">
<summary>Answer key</summary>

1. 0.299·200 + 0.587·100 + 0.114·50 = 59.8 + 58.7 + 5.7 = 124.2 → **124**.
2. Orange/brown (warm); the swap is blue-ish (cool); exchanging the R and
   B channels — pure channel arithmetic.
3. The images differ there — change detection (movement, before/after,
   flattening illumination by subtracting background).
4. 256. Values clip at 255 (blown highlights) and dark values quantize
   coarsely; the striping is **banding** (posterization).
5. "Photos from my phone import sideways" — portrait shots stored rotated
   with an orientation tag your program never applied.
6. The eye is most sensitive to green; equal weights would make greens
   too dark and blues too bright relative to perception.

</details>

### Final exam (60 minutes, closed docs, calculator allowed)

1. Convolve the centre pixel: neighbourhood
   `[[40,40,40],[40,130,40],[40,40,40]]`, box kernel (all ones ÷ 9).
   Result? What happened to the bright spot?
2. Same neighbourhood, kernel `[[0,-1,0],[-1,5,-1],[0,-1,0]]` — result
   before clamping, and the operation's name.
3. State the two kernel-weight rules (sum 1 versus sum 0) and give one
   kernel of each kind by heart.
4. Gaussian blur versus box blur: what does the Gaussian's weighting buy?
5. Histogram equalisation helped a murky scan but wrecked a portrait's
   sky. Why — and what does CLAHE change, in two clauses (the A and the
   L)?
6. Unsharp masking sharpens by way of a *blur*. Explain the trick in two
   sentences.
7. Choose the resampler and defend in one line each: (a) shrinking a
   6000-px photo to a 300-px thumbnail; (b) enlarging a crisp line
   drawing 4×; (c) high-quality photographic downsample where ringing is
   unacceptable.
8. Homomorphic illumination correction exists because some lighting
   problems are *multiplicative*. What does that mean, and why does
   subtraction fail on them?

<details markdown="1">
<summary>Answer key</summary>

1. (8·40 + 130)/9 = 450/9 = **50**. Averaged toward its neighbours —
   isolated bright detail is suppressed.
2. 5·130 − 4·40 = 650 − 160 = **490** → clamps to 255. Sharpen.
3. Sum 1: brightness-preserving smoothing (e.g. box ÷9, Gaussian ÷16).
   Sum 0: responds to change, zero on flat regions (e.g. Sobel).
4. Nearby pixels count more than distant ones — smoothing without the
   box's blocky artifacts; repeated small Gaussians compose sensibly.
5. Global equalisation spreads the *whole* histogram, so a dominant
   region (sky) drags everything; CLAHE equalises **locally** (per tile,
   A = adaptive) and **caps the boost** (L = limited) so noise is not
   amplified into false detail.
6. Blur the image, subtract the blur from the original to isolate fine
   detail, add a scaled copy of that detail back. The blur defines what
   counts as "detail."
7. (a) area-averaging — many-to-one shrink wants averaging, not picking;
   (b) nearest-neighbour — it keeps hard edges hard and invents no new
   colours; (c) bilinear/bicubic over Lanczos — Lanczos is sharper but
   can ring; when ringing is unacceptable you trade sharpness (accept
   bicubic; criteria answer).
8. Uneven lighting *multiplies* the underlying surface brightness
   (shadow = ×0.5, not −50). Subtracting a constant cannot undo a
   multiplication; the homomorphic trick works in log space, where
   multiplication becomes addition and can be removed.

</details>

---

## Unit 2 — Black and white

*Subject: thresholding, masks, components, and morphology.*

### Pre-reading quiz (10 minutes)

1. You photocopy a pencil note. The machine must decide, for every spot:
   ink or paper. What single number is it choosing, and what goes wrong
   with one bad choice?
2. The same note photographed with a shadow across it: why does one
   cutoff now fail somewhere no matter where you set it?
3. What is a mask, in the stencil sense, and what might a digital one be
   made of?
4. Two blobs of black touch at one corner pixel. One object or two? Who
   decides?
5. A scanned page has pepper specks smaller than any letter stroke.
   Invent an operation to remove them without erasing letters.
6. A letter "e" has a tiny gap where the loop nearly closes. Invent the
   opposite operation.
7. Counting coins in a photo: after ink-or-paper, what is the next
   question you must answer to report "seven coins"?
8. Why might software prefer white-on-black to black-on-white internally?

<details markdown="1">
<summary>Answer key</summary>

1. A threshold. Too low: faint strokes vanish; too high: paper texture
   becomes ink.
2. The shadowed paper is darker than the lit ink — no single global value
   separates them everywhere. (Unit answer: adapt the threshold locally.)
3. A shape that selects where an operation applies; digitally, a binary
   image used to keep/discard pixels — bitwise AND with the stencil.
4. A convention: 4-connectivity says two, 8-connectivity says one. You
   must pick and say so.
5. Shrink everything until specks vanish, then grow back — you invented
   opening.
6. Grow until gaps close, then shrink back — closing.
7. Which foreground pixels belong together — connected-component
   labelling, then count the components.
8. Convention: many operations treat nonzero as "thing"; a consistent
   foreground makes masks, counts, and morphology read the same way
   everywhere.

</details>

### Programming assignment — Whiteboard Rescue (6–8 hours)

Photograph a real whiteboard (or chalkboard) with writing, at an angle,
with glare if you can manage it. Turn it into a clean, legible, shareable
black-on-white image — the office-life version of this unit. Own loops
only; Pillow for I/O.

**Build:**

1. Grayscale, then **global threshold** with a slider/flag; save the best
   you can achieve and keep it for comparison.
2. **Otsu**: implement it (histogram → pick the cutoff maximizing
   between-class variance); report the value chosen and compare with your
   hand-tuned one.
3. **Adaptive threshold**: mean of each pixel's neighbourhood minus a
   constant; show it beating both globals on the glare/shadow regions.
4. **Morphological cleanup**: your own erosion and dilation with a 3×3
   square element, composed into opening (kill marker speckle) and
   closing (heal broken strokes). Pick the order and justify it in the
   README.
5. **Connected components** (flood fill with an explicit stack — no
   recursion; you will thank yourself in Unit 6): remove any component
   smaller than N pixels as residual noise, and report how many
   components the final board has.
6. A four-panel strip: original → best global → adaptive → cleaned, with
   one caption each.

**Rubric (100):** Otsu correct 20 · adaptive beats global where it should
20 · morphology composed and justified 25 · component cleanup with stack
flood fill 20 · strip and README 15.

### Research paper — Morphology Was Born in a Mining School (1,500–2,000 words)

Mathematical morphology — erosion, dilation, and their algebra — was
invented in the 1960s by Georges Matheron and Jean Serra at the École des
Mines, to answer questions about ore and porous rock from images of thin
sections. Tell that story: the industrial question, why "probe the image
with a shape" answered it, and how the same idea now cleans text scans and
medical slides. Include one hand-worked erosion on a grid you draw. **At
least 4 sources**; Serra or Matheron in translation counts as primary.
(You may notice the same school and era produced kriging. One sentence on
that coincidence is welcome; no more.)

**Rubric (100):** the industrial origin, accurately told 35 · the idea
explained through the probe metaphor 30 · worked example 20 · sources 15.

### Midterm exam (40 minutes, closed docs — take after the *Thresholding and masks* cluster)

1. Otsu in one sentence: what does it maximize, over what?
2. For each scan, pick global-fixed, Otsu, or adaptive and defend in one
   line: (a) evenly lit microfilm with known exposure, batch of 10,000;
   (b) a well-lit page you have never seen before; (c) a page with a
   coffee-ring shadow.
3. Binary masks: A is a page mask, B is a "regions with handwriting"
   mask. Write the bitwise expression for "handwriting on the page" and
   for "page with handwriting removed."
4. This 6×6 grid (`#` = foreground): how many objects under
   4-connectivity, and under 8-connectivity?

   ```
   # # . . . .
   # # . . # .
   . . . # . .
   . . . # # .
   . # . . . .
   # # . . . .
   ```

5. Connected-component labelling gives each blob an id. Name two per-blob
   facts that become computable the moment ids exist.

<details markdown="1">
<summary>Answer key</summary>

1. The threshold that maximizes between-class variance (equivalently,
   minimizes within-class variance) between the two histogram
   populations.
2. (a) global-fixed — exposure is controlled, a constant is cheap and
   deterministic across the batch; (b) Otsu — one clean bimodal page,
   let the histogram choose; (c) adaptive — illumination varies across
   the page, so the cutoff must too.
3. `A AND B`; `A AND (NOT B)`.
4. 4-connectivity: **4** — the top-left 2×2 block; the lone `#` at row
   2, column 5; the group at rows 3–4, columns 4–5; the bottom-left
   group at rows 5–6. 8-connectivity: **3** — the lone `#` at (2,5)
   touches the rows-3–4 group diagonally and merges with it; the other
   two groups are unchanged.
5. Area (pixel count), bounding box, centroid, perimeter — any two;
   per-object measurement is the door CCL opens.

</details>

### Final exam (50 minutes, closed docs)

1. A solid 3×3 square and one isolated pixel, 3×3 square structuring
   element: what does erosion leave? What does dilation of the original
   produce?
2. Opening and closing: give the composition of each, and match to the
   job: pepper specks · pinholes inside strokes · rejoining a dashed
   line · slimming glare-bloated strokes. (One operation can serve twice.)
3. Why does the structuring element's *size* matter more than its shape
   for speck removal? Give the rule of thumb.
4. Design, stage by stage: photographed crossword grid → count the black
   squares. Name each technique and one reason it is there.
5. Erosion then dilation is not the identity, even with the same element.
   What is permanently lost, and why is that the point?
6. Your Whiteboard Rescue used an explicit stack for flood fill. What
   goes wrong with the recursive version on a large blob, and why does an
   explicit stack not have that problem?

<details markdown="1">
<summary>Answer key</summary>

1. Erosion: the square collapses to its single centre pixel; the isolated
   pixel vanishes. Dilation: the square grows to 5×5; the pixel becomes
   a 3×3 square.
2. Opening = erosion∘dilation (erode first); closing = dilation∘erosion.
   Specks: opening. Pinholes: closing. Dashed line: closing. Glare-fat
   strokes: erosion (or opening).
3. Anything smaller than the element cannot survive erosion; choose the
   element just larger than the biggest speck and just smaller than the
   thinnest stroke you must keep.
4. Criteria: grayscale → threshold (Otsu or adaptive if unevenly lit) →
   opening (kill dust) → maybe closing (heal printing gaps) → connected
   components → filter by roughly-square bounding boxes/area → count.
   Six sensible stages with reasons = pass.
5. Everything smaller than the element is gone forever, and surviving
   shapes return smoothed. Morphology is a deliberate forgetting of
   detail below a chosen scale — that selectivity is its use.
6. Recursion depth equals blob size in the worst case — a big region
   overflows the call stack. An explicit stack lives on the heap, grows
   as needed, and makes the traversal order visible and controllable.

</details>

---

## Unit 3 — Edges, contours, and shape

*Subject: finding outlines, describing them, and choosing among competing
detections.*

### Pre-reading quiz (10 minutes)

1. Describe the difference between a picture of a coin and the *outline*
   of a coin. Which is less data, and what did it cost?
2. You must explain a shape to someone over the phone, no images. Name
   three numbers you could quote that would let them tell a coin from a
   key.
3. Where, in terms of pixel values, is the "edge" of a dark letter on
   light paper?
4. A pencil line is three pixels wide. An edge detector fires on all
   three. Why is that a problem, and what would you want instead?
5. A detector proposes twelve slightly-different boxes around the same
   face. What should the final answer be, and what rule produces it?
6. What does "the outline of the hole in a donut" have that the outline
   of a pancake lacks?
7. Simplifying a wiggly GPS trace to fewer points: which points would you
   fight to keep?
8. Why might software look at the same photo shrunk, medium, and full
   size?

<details markdown="1">
<summary>Answer key</summary>

1. The outline is a list of boundary points — far less data; it costs
   everything interior (color, texture, fill).
2. Area, perimeter, circularity, aspect ratio, solidity — any three;
   this unit turns each into a formula.
3. Between them — a steep brightness *change*, which is why edge
   detection is gradient detection.
4. Three parallel responses for one true edge; you want the single
   strongest — thinning (non-maximum suppression).
5. One box — keep the best-scoring, suppress near-duplicates that
   overlap it too much. That rule is NMS, and "too much" is IoU.
6. A parent — the hole's contour is *inside* another contour. Contour
   hierarchy is that family tree.
7. The corners — points whose removal changes the path most. That
   instinct is Ramer–Douglas–Peucker.
8. Features live at different scales: fine texture at full size,
   structure when small. One scale's noise is another's signal.

</details>

### Programming assignment — The Leaf Field Guide (8–10 hours)

Collect and photograph 10–15 leaves of 3–4 distinct kinds on plain paper.
Build the guide that tells them apart by shape alone. Own loops; Pillow
for I/O; your Unit 2 code is the front half.

**Build:**

1. Reuse Whiteboard Rescue's pipeline to a clean binary mask per photo
   (threshold → morphology → components; keep components above a size
   floor).
2. **Boundary tracing**: for each leaf component, walk its outline into
   an ordered point list (Moore neighborhood tracing or your own
   scheme — document it).
3. **Descriptors** per leaf: area, perimeter, circularity `4πA/P²`,
   bounding-box extent, aspect ratio, and solidity (area ÷ convex-hull
   area — implement the hull with the gift-wrapping method; the pages
   give you the orientation test it needs).
4. **RDP-simplify** each outline with configurable ε; report point
   counts before and after; render simplified outlines as an SVG or
   ASCII contact sheet.
5. **Classify**: from your own measurements, hand-write threshold rules
   ("circularity > 0.6 and aspect < 1.4 → oak-ish") and report the
   guide's accuracy on your photos, including the failures.
6. **Candidate filtering finale**: photograph two overlapping leaves,
   run detection, and apply your own NMS over the component bounding
   boxes with IoU to keep the dominant one. Report the IoU it decided
   with.

**Rubric (100):** tracing correct 20 · descriptors correct (spot-checked
by hand on one leaf) 30 · RDP + rendering 15 · honest classification
report 20 · NMS finale 15.

### Research paper — Reading the Mail (1,500–2,000 words)

By the 1980s, machines read most US addresses. Research postal OCR: how
envelopes were segmented into lines and characters (connected components
at industrial scale), what shape features early digit readers used, why
handwritten digits resisted, and what changed. Include one hand-worked
example: pick a digit, draw it on a grid, and compute two shape
descriptors that distinguish it from another digit. **At least 4
sources**, one contemporary to the era.

**Rubric (100):** the system, accurately described 35 · segmentation and
features explained with your worked example 40 · the handwriting
difficulty, honestly analyzed 15 · sources 10.

### Midterm exam (50 minutes, closed docs, calculator allowed — take after the *Edges, lines, and contours* cluster)

1. Sobel kernels: Gx `[[-1,0,1],[-2,0,2],[-1,0,1]]`, Gy
   `[[-1,-2,-1],[0,0,0],[1,2,1]]`. For the neighbourhood
   `[[10,10,10],[10,10,10],[90,90,90]]` compute Gx and Gy at the centre.
   What is the edge's orientation, and how do the numbers say so?
2. Canny's four stages, in order, one clause each.
3. Edge thinning (non-maximum suppression along the gradient): what
   question does it ask of each pixel, and what survives?
4. Hysteresis uses two thresholds. Walk the fate of: a strong pixel, a
   weak pixel touching a strong chain, a weak pixel alone.
5. The Hough transform finds lines by voting. What votes, for what, and
   why do collinear points win?
6. Contour tracing versus edge detection: both produce "outlines." What
   does tracing guarantee that a Canny edge map does not?
7. A binary image of the letter **O**: how many contours, and what does
   the hierarchy record about them?

<details markdown="1">
<summary>Answer key</summary>

1. Gx = 0 (columns identical); Gy = (90·1 + 90·2 + 90·1) − (10·1 + 10·2
   + 10·1) = 360 − 40 = **320**. Gradient points down the image
   (brightening downward), so the *edge is horizontal* — all change is
   vertical, none horizontal.
2. Gaussian smooth (denoise) → Sobel gradients (strength + direction) →
   non-maximum suppression (thin to one-pixel ridges) → hysteresis
   (two-threshold linking).
3. "Am I the strongest along my own gradient direction, versus my two
   neighbours?" Only local maxima survive — one-pixel-wide edges.
4. Strong: kept. Weak-touching-strong: kept — it extends a real edge.
   Weak-alone: discarded as noise.
5. Each edge pixel votes for every line that could pass through it (all
   its (angle, offset) pairs); collinear pixels' votes pile onto the
   same cell, and peaks in the accumulator are lines.
6. An *ordered, closed* boundary of a specific component — connectivity
   and ownership. Canny yields unordered edge pixels belonging to
   nobody in particular.
7. Two — the outer boundary and the hole; the hierarchy records the
   hole's contour as a child of the outer one.

</details>

### Final exam (70 minutes, closed docs, calculator allowed)

1. A filled 4×4 square: area, perimeter (edge walk), circularity
   `4πA/P²` to two decimals. Why is even a square well short of 1?
2. The L-shape (a 4×4 square missing its top-right 2×2): area 12,
   perimeter 16, and its convex hull has vertices
   (0,0), (4,0), (4,2), (2,4), (0,4) with area 14. Compute solidity and
   extent (bounding box 4×4), and say in words what each measures.
3. Boxes A = (0,0)–(3,3) and B = (1,1)–(4,4): compute IoU.
4. Detections: X score 0.9; Y score 0.8, IoU(X,Y) = 0.5; Z score 0.7,
   IoU(X,Z) = 0.1, IoU(Y,Z) = 0.05. Run NMS with threshold 0.4 — what
   survives, in what order of decisions?
5. NMS is called a *greedy* algorithm. What does greedy mean here, and
   what is the standard risk greedy strategies accept?
6. RDP with ε = 0.5 on (0,0) → (2, 2.3) → (4,4): result and reasoning.
   Same polyline with ε = 0.1?
7. Multi-scale analysis: give one concrete reason a drawing-reading
   pipeline runs detection at more than one scale, and the cost it
   accepts.
8. Design: photographed page of scattered pressed flowers → "count the
   petals on each flower." Compose the pipeline from Units 1–3, naming
   each stage's technique and purpose.

<details markdown="1">
<summary>Answer key</summary>

1. Area 16, perimeter 16, circularity 4π·16/256 = π/4 ≈ **0.79**. The
   circle is the maximum-area-per-perimeter shape; corners spend
   perimeter without buying area.
2. Solidity 12/14 ≈ **0.86** — how convex the shape is (dents and bays
   lower it). Extent 12/16 = **0.75** — how much of its bounding box it
   fills (protrusions and diagonal poses lower it).
3. Intersection (1,1)–(3,3) = 4; union 9 + 9 − 4 = 14; IoU = **2/7 ≈
   0.29**.
4. Keep X (best). Y overlaps X at 0.5 ≥ 0.4 → suppressed. Z overlaps X
   at 0.1 < 0.4 → kept. Survivors: **X and Z**.
5. Take the best-scoring remaining candidate, commit, discard what
   conflicts with it, repeat — no lookahead. Risk: a locally-best
   commitment can force a globally worse outcome (two adjacent true
   objects, one suppressed).
6. ε = 0.5: the middle point deviates |2.3 − 2|/√2 ≈ 0.21 < ε from the
   chord (0,0)–(4,4) → dropped; result is the straight segment. ε =
   0.1: 0.21 > ε → kept; all three points survive.
7. Criteria: thin hatching and fine labels need full resolution while
   large structure is steadier when small (noise suppressed); accepted
   cost is running the pipeline several times plus reconciling
   detections across scales (IoU/NMS again).
8. Criteria, in order: grayscale → illumination fix/CLAHE if needed →
   blur → threshold (adaptive if shadowed) → opening for dust →
   connected components = flowers → per-flower contour trace →
   hierarchy or convexity analysis for petal lobes (e.g. count boundary
   convexity runs or child contours) → report per component. Eight
   sensible stages with reasons = pass; the petal-counting step may be
   any defensible shape-based idea.

</details>

---

## Unit 4 — Vectors and transforms

*Subject: direction, projection, rotation, and the algebra of moving
things.*

### Pre-reading quiz (10 minutes)

1. "Walk 30 meters northeast" contains two pieces of information. Name
   them.
2. Two people push a crate, one due east, one due north, equally hard.
   Which way does it go?
3. Your shadow at noon versus late afternoon: what does its length on
   the ground have to do with *you*?
4. A clock's hands and a protractor's degrees both measure angles — but
   from different zeros, turning different ways. Name a real mixup this
   causes.
5. Rotate a photo 90° then slide it right 100 px. Slide first, then
   rotate. Same result?
6. What is special about the number pair (0.6, 0.8) compared with
   (3, 4), as directions?
7. A map app must turn "the screen's pixels" into "the world's meters"
   constantly. Guess the three ingredients of that conversion.
8. Why do 3D graphics people carry a fourth number alongside x, y, z?

<details markdown="1">
<summary>Answer key</summary>

1. A magnitude (30 m) and a direction (northeast) — a vector.
2. Northeast — vector addition of the two pushes.
3. It is your projection onto the ground along the light's direction —
   the same operation as the dot product's shadow.
4. Compass bearings run clockwise from north; math angles
   counterclockwise from east. Mixing them rotates everything by a
   wrong, consistent amount — this repository has a page precisely
   because of it.
5. No — rotate-then-slide is not slide-then-rotate. Order matters;
   that is the day's most important fact.
6. Same direction, unit length — (3,4) normalized by its magnitude 5.
   Unit vectors carry direction with no size attached.
7. A scale, a rotation, and an offset (translation) — precisely the
   similarity transform.
8. So translation becomes matrix multiplication like everything else —
   homogeneous coordinates; chains of moves collapse into one matrix.

</details>

### Programming assignment — The Flock and the Kaleidoscope (8–10 hours)

Two halves, one vector library. Plain Python plus `math`; render to SVG
(text you write yourself) or a simple canvas — your choice.

**Part 0 — vectors.py** (used by both halves): magnitude, normalize,
add/subtract/scale, dot, 2D cross, angle-between, rotate-by-θ,
project-a-onto-b. Unit-test each against hand-computed cases (include
(3,4)·(4,3) = 24 and rotate (2,0) by 90° → (0,2) among them).

**Part A — Boids** (simulation domain): 40 birds with position and
velocity in a 2D box.

- Each frame, every bird steers by three rules over neighbours within
  radius r: separation (away from too-close), alignment (match average
  heading — normalize!), cohesion (toward local centroid).
- **Field of view**: a bird only sees neighbours within ±120° of its
  heading — implement with the dot product against its unit heading.
- Cap speed by clamping velocity magnitude. Emit every 10th frame as an
  SVG frame or dump positions to CSV and describe the motion.
- README: which rule uses which vector operation, one line each.

**Part B — Kaleidoscope** (art domain): take a short polyline "doodle"
you define (10–20 points).

- Build 3×3 homogeneous matrices for translate, rotate, scale; a
  `compose(...)` that multiplies them; and `apply(matrix, points)`.
- Render the doodle repeated N = 8 ways around the centre (rotation
  matrices), then a second ring scaled 0.5 and offset — **one composed
  matrix per copy**, no per-point ad-hoc math.
- Demonstrate order-matters: render translate∘rotate and rotate∘translate
  of the same doodle in different colors, and caption which is which.

**Rubric (100):** vector library with passing hand-checked tests 25 ·
boids rules via the named operations (dot-product view cone included)
35 · kaleidoscope with genuinely composed matrices 25 · order-matters
demo and README 15.

### Research paper — How GPS Finds You (1,500–2,500 words)

A receiver knows its distance to several satellites and computes where
you are. Explain trilateration: distances from time-of-flight, spheres
intersecting, why three satellites are not quite enough (the clock —
the fourth unknown), and where vectors live in the solution. Include a
2D toy worked by hand: three known points, three distances, your
position recovered (pick numbers that come out clean). One paragraph at
the end: what the *dilution of precision* warning shares with this
course's theme of honest uncertainty. **At least 4 sources.**

**Rubric (100):** trilateration correct and clear 35 · the clock/fourth
unknown explained 25 · the 2D worked example 30 · sources 10.

### Midterm exam (45 minutes, closed docs, calculator allowed — take after the *Vectors and linear algebra* cluster)

1. u = (3,4), v = (4,3). Compute u·v, |u|, |v|, and cos θ. Are they
   nearly parallel or nearly perpendicular?
2. Normalize (5,12).
3. Project (3,4) onto the direction (1,0). What single sentence says
   what projection *is*?
4. 2D cross product of (3,4) and (4,3): value and sign — and what does
   the sign tell you about the turn from the first to the second?
5. u = (1,0,0), v = (0,1,0). Compute u × v and say what the result is
   *for*, geometrically.
6. What two properties make a set of vectors an orthonormal basis, and
   what cheap operations does having one buy?
7. A bird's unit heading is h; a neighbour sits at offset d. Write the
   test for "within ±90° of my heading" using one dot product.

<details markdown="1">
<summary>Answer key</summary>

1. u·v = 12 + 12 = **24**; |u| = |v| = 5; cos θ = 24/25 = **0.96** —
   nearly parallel (θ ≈ 16°).
2. Magnitude 13 → **(5/13, 12/13)** ≈ (0.385, 0.923).
3. (3,4)·(1,0) = 3 → the point (3,0). Projection is the shadow: how
   much of one vector lies along another's direction.
4. 3·3 − 4·4 = **−7**; negative → the turn from u to v is clockwise
   (v lies to u's right).
5. (0,0,1) — a vector perpendicular to both: the plane normal, which
   is how a face's orientation becomes one vector.
6. Unit length, mutually perpendicular. Coordinates in that basis come
   from plain dot products, and lengths/angles survive the change of
   frame.
7. `dot(h, normalize(d)) > 0` (or `dot(h, d) > 0`, since only the sign
   matters for ±90°).

</details>

### Final exam (60 minutes, closed docs, calculator allowed)

1. Rotate the point (2,0) by 90° counterclockwise about the origin.
   Give the 2×2 matrix you used.
2. p = (1,0). Apply translate-by-(3,0)-then-rotate-90°, and
   rotate-90°-then-translate-by-(3,0). Compute both results. Moral, in
   one sentence.
3. Why homogeneous coordinates: what specifically becomes possible when
   points carry a trailing 1, and what does a chain of five transforms
   collapse into?
4. Similarity versus affine transforms: what does each preserve, and
   give one distortion affine allows that similarity forbids.
5. A similarity transform has how many degrees of freedom in 2D, and
   what real-world calibration acts (scale, rotate, offset) do they
   correspond to?
6. Convert compass azimuth 240° to a mathematical angle
   (counterclockwise from +x), showing the rule.
7. Screen y grows downward; graph y grows upward. A naive port of
   rotation code between the two conventions produces what symptom, and
   why?

<details markdown="1">
<summary>Answer key</summary>

1. (0,2), via `[[0,−1],[1,0]]`.
2. Translate-then-rotate: (1,0) → (4,0) → **(0,4)**.
   Rotate-then-translate: (1,0) → (0,1) → **(3,1)**. Transform
   composition is order-sensitive because each step acts on the
   previous step's output.
3. Translation becomes a matrix multiply like rotation and scale, so
   transforms compose by multiplication — five transforms collapse
   into one 3×3 matrix applied once per point.
4. Similarity preserves shape: angles and length *ratios* (rotation +
   uniform scale + translation). Affine preserves parallelism and
   ratios along lines but allows shear and non-uniform scale — a
   square may become a parallelogram.
5. Four: one scale, one rotation angle, two translation components —
   exactly "how big, which way around, where."
6. math = 90° − azimuth (mod 360) = 90 − 240 = −150 ≡ **210°**.
7. Rotations appear to run the wrong way (and vertical flips creep
   in): flipping the y-axis reverses orientation, so clockwise and
   counterclockwise trade places unless the code accounts for the
   handedness change.

</details>

---

## Unit 5 — Geometry and numbers

*Subject: polygon truths, and arithmetic you can trust.*

### Pre-reading quiz (10 minutes)

1. Without a formula: how might you estimate the area of a
   weird-shaped county on a gridded map?
2. Three towns on a map. Driving A → B → C, how would a passenger
   describe "we turned left" as geometry?
3. Two straight roads each connect two towns. Without drawing, what
   would convince you the roads must cross?
4. You are "inside the fairgrounds" — invent a test using only a walk
   to the horizon.
5. A hiking trail's elevation is measured every kilometre. What is the
   honest way to state the elevation at 2.5 km?
6. Type `0.1 + 0.2 == 0.3` into Python. Predict the output and take a
   guess at the reason.
7. Average test score 71, median 84. What happened?
8. A miner has ore samples from ten boreholes and must estimate the
   grade between them. Why is "average of the two nearest" not quite
   enough?

<details markdown="1">
<summary>Answer key</summary>

1. Count grid squares (and part-squares) it covers — quantized area,
   the intuition the shoelace formula makes exact.
2. The signed direction of the turn at B — the orientation test's
   left/right, the unit's most reused primitive.
3. Each road's endpoints lie on opposite sides of the other road —
   exactly the two-orientation-tests criterion.
4. Walk straight out; count fence crossings; odd = inside. Ray
   casting.
5. About halfway between the 2 km and 3 km readings — *and saying* it
   is an interpolation, not a measurement.
6. `False`; neither 0.1 nor 0.2 is exactly representable in binary
   floating point, and the errors do not cancel.
7. A tail of very low scores dragged the mean below most students —
   the median resisted. Robustness.
8. Nearer samples should count more, correlated directions matter, and
   you want an uncertainty attached — the road to kriging.

</details>

### Programming assignment — The Gerrymander Detector (8–10 hours)

Civics, not trenches: measure the shapes of voting districts. Invent a
small rectangular "state," define 4–6 districts as coordinate polygons
(make two deliberately ugly — long tentacles, near-pinches), and place
30–50 "addresses" as points.

**Part A — geometry engine (own code, formulas from the pages):**

1. Signed area / orientation test as one shared primitive.
2. **Shoelace area** and perimeter per district; normalize all polygon
   windings to counterclockwise using the signed area, and say so in
   the README.
3. **Compactness** = 4πA/P² per district (in civics this is
   Polsby–Popper — one README sentence on the coincidence that it is
   Unit 3's circularity); rank districts, ugliest first.
4. **Point-in-polygon** by ray casting: assign every address to its
   district; include one address that lands on a shared edge and
   document your tie rule.
5. **Validation**: segment-intersection test over every polygon —
   reject self-intersecting district boundaries with a message naming
   the two offending edges.
6. Report: table of districts (area, perimeter, compactness, address
   count) plus verdicts.

**Part B — the outlier lab (stats, ~2 h):** fabricate a CSV of
(study-hours, exam-score) for 20 students, one wild outlier included.
Compute mean, median, variance, CV of scores; fit ordinary least
squares by the closed form (slope = Σ(x−x̄)(y−ȳ) / Σ(x−x̄)²); fit
again without the outlier; plot or tabulate both lines' predictions at
x = 0 and x = 10 and write three sentences on what the outlier did to
the fit versus to the median.

**Rubric (100):** shared orientation primitive reused throughout 10 ·
shoelace + winding normalization 15 · compactness ranking 15 ·
point-in-polygon with documented tie rule 20 · self-intersection
validation with located message 15 · outlier lab computations and
writeup 25.

### Research paper — The Night Before Challenger (1,800–2,500 words)

On 27 January 1986, engineers argued about O-rings and cold using a
data display that omitted the flights with no incidents. Tell the
story quantitatively: what the full dataset showed versus the partial
one, what an honest regression or even a scatter plot at 31 °F would
have implied about extrapolating far outside observed data, and what
Tufte and the Rogers Commission each concluded about the display of
evidence. Close with the connection to this unit: outliers,
extrapolation, and what "the data you left out" does to a fit. **At
least 5 sources, one primary** (Commission report or hearing
transcript).

**Rubric (100):** the data story, told straight 35 · the statistical
argument (omitted data, extrapolation) 35 · the evidence-display
analysis 20 · sources 10.

### Midterm exam (50 minutes, closed docs, calculator allowed — take after the *Computational geometry* cluster)

1. Orientation test on A = (0,0), B = (4,1), C = (2,5): compute
   (B−A) × (C−A) and interpret the sign.
2. Shoelace: area of the quadrilateral (0,0), (5,0), (6,3), (1,4).
3. Do segments (0,0)–(4,4) and (0,4)–(4,0) intersect? Argue with
   orientations, not a sketch. Then the same for (0,0)–(2,2) and
   (3,0)–(5,2).
4. Ray casting: point (2,2), square (0,0)/(4,0)/(4,4)/(0,4) — count
   crossings for a +x ray and conclude. Name the classic degenerate
   case and one standard way implementations defuse it.
5. Linear interpolation: elevations 104 m at km 2 and 112 m at km 3 —
   the lerp value at km 2.25? And what *must* a scientific system
   record alongside that number?
6. Polyline clipping to a window: a segment enters and exits a
   rectangular window. What does clipping output, and why do
   pipelines clip before measuring?
7. Grid snapping quantizes coordinates to a lattice. One benefit, one
   danger, one sentence each.

<details markdown="1">
<summary>Answer key</summary>

1. (4,1) × (2,5) = 4·5 − 1·2 = **18** > 0 → counterclockwise; C lies
   left of ray AB.
2. ½|0·0−5·0 + 5·3−6·0 + 6·4−1·3 + 1·0−0·4| = ½(0 + 15 + 21 + 0) =
   **18**.
3. First pair: C and D lie on opposite sides of AB *and* A and B on
   opposite sides of CD (orientation signs differ in both tests) →
   intersect (at (2,2)). Second pair: both endpoints of one segment
   lie on the same side of the other's line (same orientation signs)
   → no intersection.
4. One crossing (the right edge) → odd → inside. Degenerate: the ray
   grazing a vertex or running along an edge; defused by consistent
   half-open edge rules (count an edge only if one endpoint is
   strictly above the ray) or by nudging the ray angle.
5. 104 + 0.25·(112 − 104) = **106 m**; that the value is interpolated,
   not measured — provenance of the number.
6. The portion of the segment inside the window, with new endpoints
   computed at the window's edges; measuring after clipping keeps
   out-of-frame geometry from polluting lengths, areas, and
   intersections.
7. Benefit: nearby-but-unequal coordinates unify, so equality,
   deduplication, and hashing behave. Danger: distinct close points
   collapse — resolution is permanently spent.

</details>

### Final exam (60 minutes, closed docs, calculator allowed)

1. Why is `0.1 + 0.2 == 0.3` false in binary floating point, and what
   is the printed sum's tail? What comparison policy replaces `==`,
   and why does it need *both* an absolute and a relative part?
2. Data {2, 4, 6, 8}: mean, population variance, standard deviation,
   coefficient of variation (two decimals each). What question does
   CV answer that σ alone does not?
3. Append the outlier 40: new mean and median. One sentence on which
   estimator a glitch-prone pipeline should prefer and why.
4. Ordinary least squares: what exactly is minimized, and why does
   squaring hand outliers so much power? Name the family of
   alternatives the docs' robust-statistics page reaches for.
5. Kriging versus linear interpolation between measured points: two
   things kriging uses that lerp ignores, and the one output kriging
   provides that lerp cannot.
6. Piecewise-linear functions: why does a pipeline prefer a polyline
   of measured points over a fitted smooth curve for a boundary?
7. An epsilon of 1e−9 works in unit tests but comparisons fail on
   real survey coordinates in the millions. Diagnose.

<details markdown="1">
<summary>Answer key</summary>

1. Neither operand is representable exactly in base-2; the rounding
   errors accumulate to 0.30000000000000004. Use
   |a−b| ≤ max(abs_tol, rel_tol·max(|a|,|b|)): absolute for numbers
   near zero (relative degenerates), relative for large numbers
   (fixed epsilon becomes meaninglessly small).
2. Mean **5**; variance (9+1+1+9)/4 = **5**; σ = √5 ≈ **2.24**; CV =
   2.24/5 ≈ **0.45**. CV asks "large spread *relative to the size of
   the thing measured*?" — comparable across scales and units.
3. Mean 12, median 6 (was 5). The median: one wild value moved it one
   step; the mean it dragged by 7 — robust statistics for data with
   glitches.
4. The sum of *squared* vertical residuals; squaring makes one large
   residual outweigh many small ones, so the line chases the outlier.
   Median-based / robust estimators (e.g. median absolute deviation).
5. Distance-dependent correlation (near points weigh more, per a
   fitted variogram) and directional structure; the extra output is a
   per-estimate uncertainty.
6. The polyline *is* the measurements plus honest straight-line
   interpolation between them; a fitted curve invents smoothness the
   evidence never claimed — interpolation versus measurement again.
7. The epsilon is absolute; at coordinate magnitude ~10⁶,
   representable spacing (ULP) exceeds 1e−9, so no two computed
   values ever compare equal. The relative term exists precisely for
   this.

</details>

---

## Unit 6 — Graphs and the structures beneath

*Subject: relationships as data, and the containers that make them fast.*

### Pre-reading quiz (10 minutes)

1. A subway map versus a satellite photo of the same city: what did the
   map throw away, and why is it better for planning a route?
2. "Socks before shoes, shirt before jacket" — getting dressed is a set
   of before/after constraints. Is there always a valid order? When is
   there not?
3. Spreadsheet cell C1 is `=A1+B1`, and someone makes A1 `=C1*2`. What
   happens, and what should?
4. Why does your phone find a contact instantly among thousands, while
   you would scan a paper list top to bottom?
5. The undo button: what shape of container does it need, and why that
   one?
6. "Fewest transfers" on a transit app: does the first route found by
   just wandering qualify? What search discipline does fewest-anything
   need?
7. Merging two friend groups when one person joins both: what question
   becomes annoying to answer repeatedly, at scale?
8. A cache can hold 100 items and is full. Something must go. Propose a
   rule and defend it in one sentence.

<details markdown="1">
<summary>Answer key</summary>

1. Geometry — distances, curves, true positions. Only connectivity
   remains, which is exactly what routing needs: a graph.
2. Yes, if the constraints have no cycle; a cycle ("A before B before
   A") makes any order impossible — this unit names both facts.
3. A circular reference: C1 needs A1 needs C1. The spreadsheet should
   detect the cycle and refuse with an error, not loop.
4. Contacts are hashed/indexed for direct jumps; the paper list is a
   linear scan. Hash tables are the difference.
5. A stack — last action undone first. LIFO is the semantics of
   "undo."
6. No — wandering (depth-first) finds *a* route; fewest-hops requires
   exploring in rings: breadth-first.
7. "Are these two in the same group yet?" — asked repeatedly under
   merges: the Union-Find problem.
8. Any defensible rule; the classic is least-recently-used, betting
   that recent past predicts near future.

</details>

### Programming assignment — A Tiny Spreadsheet, and a Maze (9–11 hours)

Two builds, one toolbox. Plain Python.

**Part A — the spreadsheet engine** (office-tools domain):

1. A sheet is a dict mapping cell names (`A1`) to either a number or a
   formula string like `=A1+B2*2` (numbers, cell refs, `+ - *`,
   parentheses optional — keep the grammar tiny and document it).
2. Extract each formula's references (a small regex is fine — you will
   formalize regexes in Unit 7), building the dependency graph.
3. **Evaluate the sheet in topological order**; report a valid order.
4. **Cycle detection**: on a circular sheet, print the actual loop
   (`C1 → A1 → C1`), refuse to evaluate, and exit nonzero.
5. **Levels**: report which cells could be computed in parallel
   (BFS-style level assignment — the "semesters" of the sheet).
6. **Impact analysis**: for a given cell, list every cell that
   transitively depends on it (reachability).
7. Include two demo sheets: one 12+ cells with a diamond dependency,
   one with a deliberate cycle.

**Part B — the maze** (games domain): a text-file maze (`#` walls,
`.` floors, `S` start, `E` exit).

1. **BFS** for the shortest path (render the path on the maze);
   report its length and the number of cells explored.
2. **DFS with an explicit stack** on the same maze; report *its* path
   length and cells explored. Two README sentences comparing them.
3. **Connected components** over floor cells: how many isolated
   regions the maze has (reuse your Unit 2 flood-fill thinking — say
   so in a comment).
4. Stretch: weight some floor as mud (cost 3) and find the cheapest
   path with a priority queue (`heapq`).

**Rubric (100):** dependency extraction and topo evaluation 25 · cycle
named and refused 15 · levels + impact analysis 15 · BFS shortest path
correct 20 · DFS comparison honest 10 · components 5 · README and demo
files 10.

### Research paper — Choose One: Ranked Pages, Critical Paths, or Package Managers (1,500–2,500 words)

One graph algorithm, told through its habitat:

- **PageRank** — the web as a graph; why counting links beat counting
  words, and what the random surfer actually computes.
- **The critical path method** — 1950s construction and missile
  programs discovered the longest path through a task DAG *is* the
  schedule; slack, and why crashing a non-critical task buys nothing.
- **Package managers** — how `apt`/`npm` turn "install this" into a
  dependency graph problem: topological install order, version
  conflicts, and why resolution can genuinely be hard.

**Mandatory:** one small worked example by hand (a 6-node rank
iteration, a 7-task critical path, or an install-order trace). **At
least 4 sources.**

**Rubric (100):** the algorithm in its habitat 35 · the worked
example 35 · what breaks or is hard, honestly 20 · sources 10.

### Midterm exam (50 minutes, closed docs — take after the *Graphs* cluster)

1. Edges: A→B, A→C, B→D, C→D, A→D. Is it a DAG? List every valid
   topological order.
2. Same graph: which edge does transitive reduction remove, and what
   exact property is preserved after removal?
3. Add D→A. Trace any cycle-detection idea until it names the loop.
4. BFS from A (same DAG): list the layers. What scheduling fact do
   the layers encode?
5. Adjacency matrix versus adjacency list for a 10,000-page site
   with ~30 links per page: memory shape of each, which wins here,
   and one query the matrix answers faster.
6. Union-Find over {1..6}: union(1,2), union(3,4), union(2,3). How
   many groups remain, and what does find(4) = find(1) return?
   What per-operation cost does Union-Find achieve that re-scanning
   cannot?
7. Why is the flood fill you wrote in Unit 2 "secretly BFS or DFS,"
   and which one does the container you used decide?

<details markdown="1">
<summary>Answer key</summary>

1. Yes — no cycles. Orders: **A,B,C,D** and **A,C,B,D**.
2. A→D — implied by A→B→D (and A→C→D); reachability is unchanged:
   every ordering constraint the edge stated still holds via longer
   paths.
3. E.g. DFS from A: A→B→D→A — reaching a vertex still on the current
   path (a back edge) names the loop A,B,D. (Equivalently: repeated
   zero-indegree removal stalls with {A,B,C,D} left.)
4. {A}, {B,C}, {D}. Everything in a layer can be done in parallel
   once earlier layers finish — the "minimum semesters" structure.
5. Matrix: V² cells ≈ 10⁸ — mostly zeros; list: V + E ≈ 310,000
   entries. List wins. The matrix answers "is there an edge u→v?" in
   O(1).
6. Groups: {1,2,3,4}, {5}, {6} → **3**; find(4) = find(1) is true.
   Near-constant amortized find/union versus rescanning the whole
   structure per question.
7. It explores everything reachable over the pixel-adjacency graph;
   a queue makes it BFS, your explicit stack made it DFS.

</details>

### Final exam (60 minutes, closed docs)

1. A cell store maps `"A1" → value` in a hash table. Why is lookup
   roughly constant time, what is a collision, and name one standard
   way tables survive collisions.
2. `x in my_list` versus `x in my_set` — you measured this in Unit
   0's harness. State the observed shapes and, now, the reason.
3. Give one job in this unit's assignment for each: a stack, a
   queue, a heap. One line each.
4. An LRU cache holds 3 items. Access sequence: A, B, C, A, D. What
   is evicted, and what is the cache after? What bet does LRU make?
5. Topological order is not always unique. State the exact condition
   under which it is.
6. Your spreadsheet's "impact analysis" is reachability. Why is
   precomputing full reachability for every cell a memory tradeoff,
   and what does the transitive *reduction* page say the Harris
   matrix chose instead?
7. Layered graph drawing: what does a row mean, and why is that the
   right picture for both course prerequisites and stratigraphy?
8. Heaps promise O(log n) insert and pop-min. Sketch why: what shape
   is maintained, and what walks up or down?

<details markdown="1">
<summary>Answer key</summary>

1. The key hashes straight to a bucket index — no scan. A collision:
   two keys, one bucket; survived by chaining (lists per bucket) or
   open addressing (probe onward).
2. List membership grew linearly with N; set stayed near-flat.
   Hashing jumps to the candidate bucket instead of scanning.
3. Stack: DFS frontier (explicit recursion). Queue: BFS frontier.
   Heap: cheapest-path frontier in the mud-maze stretch (always pop
   the lowest-cost cell).
4. After A,B,C the LRU is A; accessing A refreshes it, making B
   least recent; D evicts **B**; cache = {C, A, D}. The bet:
   recently used predicts soon used.
5. Unique iff at every step exactly one vertex has no remaining
   prerequisites — equivalently the order forms a single forced
   chain (a Hamiltonian path through the DAG).
6. Full reachability stores up to V² pairs — the transitive
   *closure*; the matrix keeps only direct relations (the closure's
   information at minimum edge cost) and recomputes reach on
   demand.
7. A row is a rank in the partial order — everything below depends
   on (or is later than) things above. Both domains are DAGs whose
   only message is relative order, so position-as-order is the
   honest rendering.
8. A complete binary tree with the parent ≤ children invariant
   (min-heap); insert bubbles a leaf up, pop-min moves the last
   leaf to the root and sinks it down — both walk one root-to-leaf
   path: log n.

</details>

---

## Unit 7 — Bytes, threads, and things that fail

*Subject: data at rest, work in parallel, and surviving both.*

### Pre-reading quiz (10 minutes)

1. Two copies of a 4 GB file may or may not be identical. Propose a
   check that does not read them side by side forever.
2. Why does a `.zip` of a text file shrink it, while a `.zip` of a
   `.jpg` barely does?
3. The number 258 must be stored in two bytes. Invent two defensible
   ways to order those bytes.
4. Two clerks share one paper ledger. Both read "balance: 100," both
   add 50, both write. What does the ledger say, and what was lost?
5. Your download died at 80%. What must the server and client agree
   on so resuming is not restarting?
6. An app retries a failed request instantly, forever. Name two
   parties this hurts.
7. Pulling a USB stick "too early" used to corrupt files. What was
   actually half-done?
8. "Doing it twice is the same as doing it once." Name one everyday
   action with this property and one without.

<details markdown="1">
<summary>Answer key</summary>

1. Fingerprint both with a hash and compare the digests — the
   unit's opening move.
2. Text is redundant (patterns compress); JPEG is already
   compressed, so little redundancy remains. Compression is
   redundancy spending.
3. Big end first (0x01 0x02) or little end first (0x02 0x01) —
   endianness, and both camps shipped hardware.
4. 150 — one clerk's 50 vanished: a lost update from unsynchronized
   read-modify-write.
5. Where the file stands (offset/chunk index) and that re-sending a
   chunk is harmless — resumability is idempotency plus position.
6. The user (battery, blocked UI) and the struggling server (a
   retry stampede keeps it down); hence backoff, jitter, budgets.
7. Buffered writes not yet flushed — the file existed part-written:
   the atomic-write problem.
8. Idempotent: pressing an elevator call button. Not: pressing
   "send payment."

</details>

### Programming assignment — The Save-Game Vault and the Race Lab (9–11 hours)

Games and systems, no archaeology.

**Part A — the vault.** A tiny text adventure needs bulletproof saves.
Model a game state (player name, position, inventory list, play
seconds).

1. **Two serializers**: JSON, and your own binary format via
   `struct` — magic bytes, a format version, then fields with
   explicit little-endian encoding. A README table: bytes on disk
   for each, and one advantage per side.
2. **Checksummed**: append the SHA-256 of the payload; on load,
   verify before parsing. Truncate a save by hand and show the
   clean refusal (message, nonzero exit — never a stack trace).
3. **Atomic saves**: temp file, flush, `os.replace`. Add `--crash`
   to kill mid-write and demonstrate the old save surviving.
4. **Versioned**: v2 adds an `achievements` list. Loading a v1 save
   migrates it (empty list), writes a `.bak` first, and reports the
   migration.
5. **Content-addressed snapshots** (stretch): `snapshot` copies the
   save into `vault/<first-2-hex>/<digest>`; identical states
   dedupe by construction.

**Part B — the race lab.**

1. Two threads each increment a shared counter 100,000 times, no
   lock. Report expected versus observed across five runs. Explain
   the loss in terms of read-modify-write interleaving — and why
   the GIL did not save you.
2. Fix it with a `threading.Lock`; show the clean 200,000.
3. **Flaky downloader**: a stub `fetch_chunk(i)` fails 40% of the
   time (seed your random generator for reproducibility — that is
   determinism practiced, note it). Download 20 chunks with
   exponential backoff plus jitter, a retry budget of 5 per chunk,
   and resume-from-manifest so a rerun refetches nothing already
   verified (chunk hashes in the manifest — idempotency by
   content).

**Rubric (100):** binary format with explicit endianness 20 ·
checksum + refusal 15 · atomic + crash demo 15 · migration with
backup 10 · race demonstrated, explained, fixed 20 · downloader
(backoff, jitter, budget, resumable manifest) 20.

### Research paper — Why Your Card Was Not Charged Twice (1,500–2,000 words)

Payment APIs let a client retry a charge safely by attaching an
idempotency key. Research how this works (Stripe's design is well
documented): what the key identifies, what the server stores, what
happens when a retry races the original, and what expiry policies
trade away. Connect to the unit: which failure the pattern exists
for (the success that looked like a failure), and why "at
least once plus idempotency" is the industry's answer to "exactly
once." **At least 4 sources, one primary** (API docs or an
engineering post from a payments company).

**Rubric (100):** the mechanism, precisely described 40 · the
race/retry analysis 30 · the exactly-once discussion 20 · sources 10.

### Midterm exam (45 minutes, closed docs, calculator allowed — take after the *Hashing, encoding, and serialisation* cluster)

1. Name three properties of SHA-256 that make it a trustworthy file
   fingerprint, and the one thing equal digests do *not* prove in the
   presence of a malicious actor with unlimited power (answer per the
   docs' practical stance).
2. Content-addressed storage: two distinct benefits of naming a file
   by its hash, one sentence each.
3. Bytes `0x01 0x02` as one 16-bit integer: value read big-endian?
   Little-endian? Which mistake do these numbers let you diagnose in
   the wild?
4. Your binary save format begins with magic bytes and a version.
   What failure does each of the two headers convert into a clean
   error?
5. JSON versus your binary format: one axis where each wins,
   grounded in your vault measurements.
6. Regex `\d{4}-\d{2}-\d{2}` under *search* semantics: which of
   these contain a match — `2026-08-14` · `2026-8-14` ·
   `date:2026-08-14end` · `20260814`? What changes under
   *fullmatch*?

<details markdown="1">
<summary>Answer key</summary>

1. Deterministic; fixed-size output; avalanche (tiny change, wholly
   different digest); one-way; collision-resistant — any three.
   Equal digests prove identical content only against accident and
   present-day capability; the docs treat engineered collisions as
   infeasible, not impossible in principle.
2. Deduplication is automatic (same bytes, same name); integrity is
   verifiable by rehashing (the name certifies the content). Also
   acceptable: caches never serve stale content under a
   content-derived name.
3. Big: 0x0102 = **258**. Little: 0x0201 = **513**. Numbers that
   arrive wildly wrong but pattern-like (258 ↔ 513) betray an
   endianness mismatch between writer and reader.
4. Magic bytes: "this is not even a save file" (wrong file fed in)
   → refuse before parsing garbage. Version: "a save from a
   different era" → migrate or refuse knowingly, instead of
   misparsing silently.
5. JSON: human-readable, self-describing, toolable — debugging and
   interop. Binary: smaller and faster to parse, with explicit
   layout — but opaque and fragile without its spec. (Your byte
   counts justify the size claim.)
6. Search: matches in `2026-08-14` and `date:2026-08-14end`; not in
   `2026-8-14` (two-digit month required) or `20260814` (no
   hyphens). Fullmatch: only the bare `2026-08-14` — the entire
   string must match.

</details>

### Final exam (60 minutes, closed docs, calculator allowed)

1. The GIL runs one thread's bytecode at a time. Reconcile: your
   race lab still lost updates. Where exactly does the interleaving
   sneak in?
2. Optimistic concurrency with version numbers: A reads v3, B reads
   v3, B writes first. Narrate both writes' fates and what A must
   do. When is this scheme better than a lock, and when worse?
3. The atomic write pattern: the three steps, why the temp file
   must live on the same filesystem as the target, and what a
   reader can observe mid-operation.
4. Backoff starting at 0.25 s, doubling per failure: the wait after
   the 4th failure, and total sleep across all four. What does
   jitter add, and what does the retry *budget* protect that
   backoff alone does not?
5. Your downloader is safely rerunnable. Name the two properties
   that make it so, and which artifact encodes each.
6. Debouncing versus throttling: define each in one clause and
   assign the right one to (a) live-search-as-you-type, (b) a
   progress bar updating from a firehose of events.
7. Determinism and stable sorting: what does a stable sort preserve,
   and why do reproducible pipelines insist on deterministic
   ordering even when any order would be "correct"?
8. Fail-closed design: what does the vault do with a save whose
   checksum fails, and why is the tempting alternative worse?

<details markdown="1">
<summary>Answer key</summary>

1. The GIL serializes *bytecodes*, not logical operations;
   `counter += 1` is several bytecodes (load, add, store), and the
   interpreter can switch threads between them — two loads of the
   same value, two stores, one update lost.
2. B's write succeeds, bumping to v4; A's write presents expected
   v3 against current v4 → rejected; A rereads and redoes. Better
   under low contention (no one waits); worse under high contention
   (endless retry work a lock would have serialized).
3. Write to a temp file in the target's directory → flush (fsync if
   promised durable) → `os.replace` over the target. Rename is
   atomic only within a filesystem — across devices it degrades to
   copy-then-delete, which has a half-state. A reader sees either
   the whole old file or the whole new one, never a mix.
4. Waits 0.25, 0.5, 1, 2 → after the 4th failure the wait is
   **2 s**; total sleep **3.75 s**. Jitter staggers many clients so
   they stop synchronizing their retries; the budget bounds total
   attempts so a dead dependency fails fast instead of consuming
   forever.
5. Idempotency (re-fetching a chunk is harmless; verified chunks
   are skipped) — encoded in the manifest with per-chunk hashes;
   and determinism of what remains (the manifest says exactly which
   chunks are outstanding). Rerun = converge, not repeat.
6. Debounce: act once after the input goes quiet — (a). Throttle:
   act at most once per interval while input continues — (b).
7. The relative order of equal keys. Deterministic ordering makes
   runs comparable — diffs mean changes in *data*, not in
   iteration whim — which is what makes outputs reviewable and
   cacheable by content.
8. Refuse to load, say why, point at the backup — fail closed. The
   alternative — "salvage what parses" — silently promotes corrupt
   state to trusted state, and the player finds out much later,
   with less evidence.

</details>

---

## Unit 8 — Boundaries, blueprints, and honest computing

*Subject: keeping bad data out, structure that survives change, and the
ethics of computed numbers.*

### Pre-reading quiz (10 minutes)

1. A nightclub checks IDs at the door, not at every table. A program
   receives data from outside. Where is its "door," and what happens
   if checks live at the tables instead?
2. Name two "outsides" a program receives data from besides its
   human user.
3. `filename = "../../secrets.txt"` — what is the filename trying to
   do, and to what?
4. A 40 KB file claims, in its own header, to be a 100-megapixel
   image. What should a careful program do before decoding, and why?
5. Why do big programs get organized into layers at all — what goes
   wrong with an "everything calls everything" design?
6. A function that reads a global config, writes a log, and returns
   a value — what makes it awkward to test compared with one that
   takes inputs and returns outputs?
7. An instrument measured 4.1 and 4.5; software reports 4.3 for the
   point between. What is the one honest thing the report must
   carry?
8. A machine transcribes a stack of handwritten forms. Before the
   transcript becomes the record, what should stand between? Why
   there and not later?

<details markdown="1">
<summary>Answer key</summary>

1. The door is where outside data enters (parse/ingest points) —
   the trust boundary. Checks scattered at tables get forgotten,
   duplicated, and disagree; bad data is already inside.
2. Files on disk, network responses, environment variables, other
   programs' output — any two.
3. Climb out of the directory it was supposed to stay in — path
   traversal against the program's file store.
4. Refuse or cap using the *declared* size before decoding — the
   expansion happens at decode time; after is too late. A
   decompression bomb.
5. Every change ripples everywhere; nothing is testable alone;
   dependencies point every direction. Layers give change a
   direction to flow.
6. Its behavior depends on hidden state and it leaves footprints —
   you must stage the world to test it. Pure functions need only
   arguments and assertions.
7. That 4.3 is interpolated, not measured — provenance of the
   number.
8. A human review of the transcription against the source, at the
   point of *commitment* — later, the transcript has already been
   trusted, cited, and copied.

</details>

### Programming assignment — The Hardened Lab Notebook (9–12 hours)

A command-line notebook for any hobby that generates observations —
sourdough bakes, telescope nights, marathon training. The point is not
the notebook; it is that every page of Unit 8 shows up in one small
tool.

**Architecture (drawn in the README):** three modules with one legal
dependency direction — `storage.py` (leaf: file I/O, atomic writes,
no imports from the others), `logic.py` (validation, provenance,
queries; imports storage only), `cli.py` (argument parsing and
printing; imports logic only). One sentence in the README on what
this buys, citing the leaf-module idea.

**Features:**

1. `add` — an entry with fields (date, title, notes, numeric
   measurement with unit). **Validation at the boundary**: every
   field checked at parse time; errors carry an **error taxonomy**:
   user-fixable (exit 2, friendly message), internal bug (exit 70,
   asks for a report), environment (exit 69, e.g. disk full) — the
   README maps the classes.
2. `attach <file>` — copies a file into the notebook's store under
   a **content-addressed name**; the requested filename is used
   only as a display label, and any path from the user is resolved
   and **contained** (two independent traversal defenses, tested by
   an attack you script).
3. A size cap on attachments enforced **before** reading the whole
   file (bomb thinking; document the limit).
4. `import-csv` — bulk observations land in a **staging area**, not
   the notebook; `review` shows staged entries with validation
   verdicts; `approve <id>` commits them — two-phase commit with a
   human between. Approved entries record `source: imported+reviewed`;
   hand-typed ones `source: manual` (provenance).
5. Every entry stores the schema version; ship a v1→v2 migration
   (adds `tags`) with a `.bak`, reusing your Unit 7 pattern.
6. **Pure core**: validation and query functions are pure; pytest
   tests cover them without touching the filesystem. Listing output
   is deterministically ordered (stable sort by date then title) —
   a README sentence on why.

**Rubric (100):** layering with legal imports (checked by reading)
15 · taxonomy-coded validation 20 · containment + content addressing
with scripted attack test 20 · staged import with review gate 20 ·
migration 10 · pure core with tests + deterministic listing 15.

### Research paper — The Reproducibility Crisis, for Programmers (1,800–2,500 words)

Large swaths of published computational results cannot be
regenerated from what was published. Research the crisis as it
applies to *code*: missing environments, unseeded randomness,
nondeterministic ordering, absent provenance, data cleaning by hand.
Pick one documented case study (any field), tell what failed to
reproduce and why, then map each cause onto a practice from this
course's pages (determinism, provenance and lineage, schema
versioning, validation, human review). End with the strongest
counterargument you can construct — what reproducibility costs — and
answer it. **At least 5 sources, one primary** (the case's paper,
retraction, or postmortem).

**Rubric (100):** the crisis and case, accurately told 35 · causes
mapped to named practices 35 · the counterargument taken seriously
20 · sources 10.

### Midterm exam (45 minutes, closed docs — take after the *Validation* and *Architecture* clusters)

1. Sort these eight failures into user-fixable / internal bug /
   environment: malformed date in an added entry · `KeyError` in
   your own query code · disk full during save · attachment over
   the size cap · network timeout fetching a URL the user gave ·
   an assertion failing on an invariant you maintain · unsupported
   image format attached · permission denied on the store
   directory.
2. Validation versus sanitisation: define each; which does a trust
   boundary prefer, and why is the other's silence dangerous?
3. Why must a file format carry a schema version *from its first
   release*, and which direction do migrations run?
4. Structural versus schema validation: what does each catch?
   Give one record that passes structurally and fails the schema.
5. Layered architecture: which direction may imports point? Judge
   each: `storage` imports `cli` · `cli` imports `logic` · `logic`
   imports `storage` · `storage` imports `logic`.
6. What is an application factory, and name the concrete testing
   problem it solves compared with a module-level global app.
7. The classic closure bug: three buttons wired in a loop all
   fire the last button's action. Diagnose in one sentence and
   give the standard fix.
8. Pure functions and testability: what two properties define
   purity, and what does each remove from a test's setup?

<details markdown="1">
<summary>Answer key</summary>

1. User: malformed date, oversize attachment, unsupported format.
   Bug: `KeyError` in own code, failed invariant assertion.
   Environment: disk full, network timeout, permission denied.
2. Validation inspects and *rejects* nonconforming input;
   sanitisation *transforms* input toward safety. Boundaries prefer
   validate-and-refuse: sanitisation silently changes meaning, and
   what slipped through was never inspected against intent.
3. Old files outlive the code that wrote them; without a version
   the reader cannot even know migration is needed. Migrations run
   old → new, on load, with a backup.
4. Structural: is it well-formed at all (parses, right shapes)?
   Schema: does it have the required fields with the required
   types/ranges? `{"date": "yesterday"}` in valid JSON parses
   (structurally fine) and fails the schema's date rule.
5. Downward only, toward leaves. `storage→cli` illegal (leaf
   importing up), `cli→logic` legal, `logic→storage` legal,
   `storage→logic` illegal.
6. A function that builds and returns a configured application
   instance; tests can create a fresh, differently-configured app
   per test instead of sharing one import-time global whose state
   leaks between tests.
7. The loop's closures captured the *variable*, not its value, so
   all see its final value; bind at definition time (default
   argument `i=i` or a factory function).
8. Same inputs → same output; no side effects. The first removes
   hidden state from setup; the second removes teardown and
   world-staging — the test is a call and an assertion.

</details>

### Final exam (60 minutes, closed docs)

1. A route opens `os.path.join(STORE, request.args["name"])`. Give
   the attack value, the harm, and two *independent* fixes.
2. A decompression bomb in one sentence, and the defense's timing
   in one more.
3. Same-origin URL validation: the notebook fetches a URL the user
   supplies for an attachment. What check belongs before the fetch,
   and what class of mischief does it block?
4. Input sanitisation has a place despite Q-midterm's preference:
   give one legitimate sanitisation at an *output* boundary and why
   there.
5. Provenance and data lineage: list the fields a derived
   artifact's record should carry, and the question each answers a
   year later.
6. Human-in-the-loop review: why does the import gate sit at
   *commit* time rather than report time, and what does sampling
   review trade against full review?
7. Two-phase commit with review: the two phases, what lives
   between, and the failure mode the design accepts to gain
   safety.
8. Fabrication detection: three signals that a "measurement" in a
   dataset was invented, and the honest limitation of any such
   detector.
9. Interpolation versus measurement (short essay, 5–8 sentences):
   why the flag must travel with the value, what dies downstream
   when it is dropped, and the parallel rule from Unit 0's reading
   about synthetic examples.

<details markdown="1">
<summary>Answer key</summary>

1. `name=../../../../etc/passwd` (any `..` chain): reads or
   overwrites files outside the store. Fixes (any two,
   independent): resolve the joined path and require the store's
   resolved path as prefix; reject path separators and `..`
   outright (or use basename); look up server-generated ids
   instead of accepting names at all.
2. A tiny input that decodes into an enormous allocation
   (compressed pixels, nested archives). The defense acts on
   *declared* size before decoding — afterward the memory is
   already spent.
3. Scheme and host validation against an allowlist (and no
   redirects off it) — blocks the notebook being used as a proxy
   to fetch internal/other-origin resources it should never touch.
4. Escaping text for display (HTML/shell) — at output, the goal is
   representing data safely in a context, not judging it;
   rejecting is meaningless there.
5. Source identifier and its content hash · tool/step name and
   parameters · timestamp · schema version. They answer: derived
   from what, exactly? by what, configured how? when? readable by
   what?
6. Commit is the last moment before the data becomes trusted and
   copied onward; reporting-time review is advisory and skippable.
   Sampling trades certainty for cost — acceptable when errors are
   independent, ruinous when one systematic error repeats across
   every record.
7. Stage the automated result as a proposal; a human compares it
   against the source; only approval commits. Accepted cost:
   throughput — the pipeline is only as fast as the reviewer.
8. E.g.: precision beyond the instrument (4.73218 from a tape
   measure) · values too regular (identical deltas, reused
   digits) · impossible ranges or unit mismatches · perfect
   agreement between supposedly independent sources. Limitation: a
   detector flags *suspicion*, not proof — plausible fabrication
   passes every statistical sniff.
9. Criteria: measured values inherit evidence, interpolated ones
   inherit assumptions · downstream consumers cannot weigh what
   they cannot distinguish · once merged, false precision
   propagates irreversibly · the flag is provenance in miniature ·
   synthetic-data labeling is the same contract: keep what we know
   separate from what we made up. 4+ = pass.

</details>

---

## Unit 9 — Synthesis

*Subject: all of it, at once, on a photograph you take yourself.*

### Pre-reading quiz — calibration inventory (15 minutes)

Rate your confidence 1–5 per unit (0 through 8), then take the five spot
checks closed-book. The product is the *calibration*: any unit rated 4+
whose spot check fails goes on the review list before the capstone.

Spot checks:

1. Box-convolve the centre of `[[20,20,20],[20,110,20],[20,20,20]]`.
2. Boxes (0,0)–(2,2) and (1,0)–(3,2): IoU.
3. Edges P→Q, Q→R, P→R: one valid topological order, and the edge
   transitive reduction removes.
4. Name three properties of SHA-256.
5. The atomic write pattern, three steps.

<details markdown="1">
<summary>Answer key</summary>

1. (8·20 + 110)/9 = 270/9 = **30**.
2. Intersection (1,0)–(2,2) = 2; union 4 + 4 − 2 = 6; IoU = **1/3**.
3. P, Q, R; remove **P→R**.
4. Any three: deterministic, fixed-size, avalanche, one-way,
   collision-resistant.
5. Temp file in the same directory → write and flush → `os.replace`
   over the target.

</details>

### Programming assignment — capstone: The Meter Reader (12–16 hours)

Seven-segment displays are everywhere: microwave clocks, ovens, bathroom
scales, utility meters. Photograph one daily for a week and build the
tool that reads it — image in, trusted number out, every unit of this
course on duty. Own loops; Pillow for I/O.

**Requirements, each naming its unit:**

1. **Prepare** (U1): grayscale, contrast or equalisation as your photos
   need, optional blur; keep the prepared image as an artifact.
2. **Binarize and clean** (U2): threshold (adaptive if your photos have
   glare), opening/closing as needed.
3. **Find the digits** (U2–U3): connected components; filter candidates
   by size, aspect ratio, and extent; sort surviving boxes left to
   right. If overlapping candidates survive, resolve with IoU/NMS.
4. **Sample the segments** (U4–U5): within each digit's box, define the
   seven segment zones in *normalized* coordinates (so any digit size
   works — that is a scale transform), and decide lit/unlit by the ink
   ratio in each zone.
5. **Decode** (U6): a hash table from seven-bit segment patterns to
   digits; unknown patterns are reported as unreadable, never guessed
   (fail closed, U7/U8).
6. **Validate** (U8): range and format rules for your instrument
   ("scale reads 30.0–150.0 kg, one decimal"); violations produce
   taxonomy-coded errors.
7. **Log** (U7–U8): append accepted readings to a JSON log with schema
   version, and provenance per reading: source photo path *and its
   SHA-256*, tool name, parameters, timestamp. Atomic writes. Rerunning
   on an already-logged photo must not duplicate (idempotency by photo
   hash).
8. **Report** (U5): across the week's readings — count, mean, median,
   and a one-line trend statement; note explicitly that days you missed
   are gaps, not interpolations, unless you choose to interpolate *and
   flag it*.
9. **README** (U0): quickstart in the workflow-page shape, and an
   honest capability table for your own tool (supported / experimental /
   not-implemented — glare handling and decimal points are where
   honesty gets exercised).

**Rubric (100):** segmentation robust on your real photos 20 · segment
sampling via normalized zones 15 · fail-closed decoding 10 ·
taxonomy-coded validation 10 · provenance + atomic, idempotent log 20 ·
stats report with the interpolation stance 10 · README with honest
capability table 15.

This is the digestion proof: the course's whole arc — photograph to
validated, provenanced number — rebuilt by you, on your own kitchen
counter.

### Research paper — One Real Pipeline, Mapped (2,000–3,000 words)

Choose a documented, real image-to-data pipeline from any field:
astronomical survey photometry (e.g. a sky-survey's difference-imaging
pipeline), digital pathology slide analysis, archive-scale OCR, or a
self-driving perception stack. From published descriptions, map its
stages onto **at least ten techniques from at least six units** of this
course — name the technique, the stage, and the evidence. Then evaluate
its honesty practices against Unit 8: what provenance is kept, where
humans review, what happens to low-confidence output. Close with the
one thing the pipeline does that this course did not teach, as your
next thing to learn. **At least 6 sources.**

**Rubric (100):** the pipeline, accurately described 25 · the ten
mappings, specific and defensible 40 · the honesty evaluation 25 ·
sources 10.

### Midterm exam — the integration matrix (60 minutes: Part A closed, Part B open-docs)

**Part A (closed).** For each unit 1–8, from memory: name one technique
from that unit *and* one sentence of its "why this and not the obvious
alternative" reasoning. Sixteen sentences total.

**Part B (open the algorithm index only).** For five of those eight
techniques, find via the [algorithm index](../architecture/algorithm-index.md)
one repository module that uses it. Cite module paths.

**Part C (closed) — confusables, rapid fire.** One distinguishing
sentence each: erosion/opening · Otsu/adaptive · BFS/DFS ·
similarity/affine · mean/median · validation/sanitisation ·
checksum/schema-version · debounce/throttle.

<details markdown="1">
<summary>Answer key</summary>

A. Graded on the second half: the alternative must be real and the
cost stated (e.g. "Gaussian over box: smoothing without blocky
artifacts, at slightly more arithmetic"). 13+ of 16 sentences
defensible = pass.
B. Graded by citation matching the index. 4 of 5 = pass.
C. Pass: 7 of 8 crisp. All eight pairs appear in Units 1–8 keys
above.

</details>

### Final exam — the course final (three parts, ~2.5–3 hours; sittings may split)

**Part A — comprehensive (75 minutes, closed docs, calculator
allowed).** Twenty-five questions; pass ≥ 20.

1. The seven sections of a CS page, in order.
2. Luminosity grayscale of (120, 200, 40) with weights
   0.299/0.587/0.114 (nearest integer).
3. Box-convolve the centre of `[[20,20,20],[20,110,20],[20,20,20]]`.
4. The two kernel-weight rules, one clause each.
5. Otsu's method in one sentence.
6. Dust specks smaller than every stroke: which morphological
   operation, composed how?
7. Two blobs touch only at a corner. One object or two, and what
   decides?
8. Canny's four stages, in order.
9. Circularity of a 2×8 rectangle (area 16, perimeter 20), two
   decimals.
10. Boxes A (0,0)–(2,2), B (1,0)–(3,2): IoU.
11. In RDP, which points are guaranteed to survive, and why?
12. Normalize (8,6).
13. (1,2)·(2,−1) — value, and the geometric conclusion.
14. Rotate (0,3) by 90° counterclockwise.
15. Why does transform order matter? One sentence.
16. Compass azimuth 135° as a math angle.
17. Shoelace: area of the triangle (0,0), (6,0), (0,4).
18. The ray-casting rule for point-in-polygon, one sentence.
19. Why is `0.1 + 0.2 == 0.3` false, and the comparison policy that
    replaces `==`?
20. Data {3, 5, 7, 9, 41}: mean and median, and which to report for
    glitchy data.
21. Edges P→Q, Q→R, P→R: a valid topological order, and transitive
    reduction's move.
22. From your Unit 0 harness: how did `in list` and `in set` scale,
    and why?
23. Bytes `0x00 0x10` as a 16-bit integer, big- and little-endian.
24. Two threads, `n += 1` each, no lock, from n = 0: worst-case final
    value and the mechanism.
25. The atomic write pattern — and in one sentence, why automated
    transcription commits only after human review (two-phase commit's
    reason).

**Part B — essays (45 minutes, closed docs; both).**

1. *One mechanism, many operations.* Convolution is the unit thesis of
   image processing: show it by tracing the same mechanism from box
   blur through Gaussian, sharpening, Sobel, and into Canny's first
   two stages — what changes each time, and what never does.
   (10–15 sentences.)
2. *From photons to a number you can defend.* Trace one pixel of your
   Meter Reader's photograph to a logged, validated reading: name
   every transformation, every decision that could reject it, and
   every artifact that records what happened — at least one technique
   from every unit, 1 through 8. (10–15 sentences.)

**Part C — practical (45 minutes, docs closed until stuck).** A fresh
photo of your display, through your capstone, unaided. Checklist:
prepared artifact saved · digits found (or failures honestly reported) ·
reading decoded or refused with a named reason · validation verdict ·
log entry with provenance and intact hash · stats updated · rerun on
the same photo does not duplicate.

<details markdown="1">
<summary>Answer key — Part A</summary>

1. What it is · The picture · Where this project uses it · Why this
   and not something else · What it costs · Where else you meet it ·
   Related pages.
2. 35.88 + 117.4 + 4.56 = 157.84 → **158**.
3. 270/9 = **30**.
4. Sum 1: brightness-preserving smoothing. Sum 0: change detector,
   zero on flat regions.
5. The threshold maximizing between-class variance of the histogram's
   two populations.
6. Opening — erosion then dilation.
7. Convention: 4-connectivity two, 8-connectivity one; you must
   choose and document.
8. Gaussian smooth → Sobel gradient → non-maximum suppression →
   hysteresis.
9. 4π·16/400 ≈ **0.50**.
10. 2/(4+4−2) = **1/3**.
11. The endpoints, and recursively every point farther than ε from
    the current chord — the farthest-deviation points are exactly
    what the algorithm keeps.
12. Magnitude 10 → **(0.8, 0.6)**.
13. 2 − 2 = **0** → perpendicular.
14. **(−3, 0)**.
15. Each transform acts on the previous one's output, so composition
    is multiplication, and matrix multiplication does not commute.
16. 90 − 135 = −45 ≡ **315°**.
17. ½·6·4 = **12** (shoelace confirms).
18. Cast a ray; odd crossings inside — with a consistent tie rule at
    vertices and edges.
19. 0.1 and 0.2 are not exactly representable in binary; use
    |a−b| ≤ max(abs_tol, rel_tol·max(|a|,|b|)).
20. Mean **13**, median **7**; the median, because one glitch moved
    the mean by six.
21. P, Q, R; remove P→R.
22. List grew linearly, set stayed near-flat; hashing jumps to a
    bucket instead of scanning.
23. Big: **16**; little: **4096**.
24. **1** — both read 0 before either writes: lost update via
    interleaved read-modify-write.
25. Temp file, same directory → write and flush → atomic rename.
    Because automated transcription's failure mode is plausible
    fabrication, and only a human comparing against the source can
    catch it before it becomes trusted data.

**Part B criteria.** Essay 1: the kernel is the only thing that
changes; sliding weighted sums never do — and Canny is shown to open
with two convolutions (Gaussian, Sobel). Essay 2: touches ≥ 8 units
with concrete stations (prepare → threshold/morphology → components/
shape filter → normalized-zone sampling → hash decode → validation →
provenanced atomic log → stats), and treats at least one rejection
path honestly.

**Part C.** Pass = every checklist item unaided; anything that
required the docs goes on a reread list and is redone another day.

</details>

---

## After the final

Passing Part A at 20/25 with both essays meeting criteria and a clean
capstone run means you have digested the computer science this
repository uses — with receipts: nine programs, a capstone that reads a
real instrument, and answer-key-verified exams across every cluster.

Two natural continuations: the [full course](plan.md), whose phases 1–5
teach what the archaeologists are doing with these techniques; or the
codebase itself, entered through the
[algorithm index](../architecture/algorithm-index.md) — you now speak
its language.

<!-- Local-only enhancement: a "Copy for feedback" button on every quiz
     and exam, duplicated from assessments.md so each draft page stays
     self-contained. It copies the section's questions, answer key, and
     a grading brief for pasting into Claude. Inside Claude Code, the
     grade-assessment skill is the better loop: it reads this file
     itself. -->
<style>
.assessment-copy { margin: 0 0 1em; }
.assessment-copy button {
  font: inherit; font-size: 0.72rem; padding: 0.3em 0.9em; cursor: pointer;
  border: 1px solid var(--md-default-fg-color--lightest, #ccc);
  border-radius: 0.25em;
  background: var(--md-code-bg-color, #f5f5f5);
  color: var(--md-default-fg-color--light, #444);
}
.assessment-copy button:hover {
  border-color: var(--md-accent-fg-color, #536878);
  color: var(--md-accent-fg-color, #536878);
}
</style>
<script>
(function () {
  "use strict";
  // Quizzes and exams get a button; assignments get feedback conversationally.
  var GRADEABLE = /^(Pre-reading quiz|Midterm exam|Final exam)/;
  function headingText(heading) {
    var clone = heading.cloneNode(true);
    var links = clone.querySelectorAll(".headerlink");
    for (var i = 0; i < links.length; i++) { links[i].remove(); }
    return clone.textContent.trim();
  }
  // textContent-based rendering: list markers are reconstructed by hand
  // because closed <details> content has no layout for innerText to read.
  function render(node) {
    var tag = node.tagName;
    if (tag === "OL" || tag === "UL") {
      var start = tag === "OL" ? parseInt(node.getAttribute("start") || "1", 10) : 0;
      var lines = [];
      for (var i = 0; i < node.children.length; i++) {
        var item = node.children[i];
        if (item.tagName !== "LI") { continue; }
        var marker = tag === "OL" ? String(start + i) + ". " : "- ";
        lines.push(marker + item.textContent.trim().replace(/\n[ \t]*/g, "\n   "));
      }
      return lines.join("\n");
    }
    if (tag === "PRE") { return node.textContent.replace(/\s+$/, ""); }
    if (tag === "DETAILS" || tag === "SUMMARY") { return ""; }
    return (node.innerText || node.textContent).trim();
  }
  function collect(heading) {
    var questions = [];
    var key = [];
    var el = heading.nextElementSibling;
    while (el && !/^H[123]$|^HR$/.test(el.tagName)) {
      if (el.classList && el.classList.contains("assessment-copy")) {
        el = el.nextElementSibling;
        continue;
      }
      if (el.tagName === "DETAILS") {
        for (var i = 0; i < el.children.length; i++) {
          if (el.children[i].tagName === "SUMMARY") { continue; }
          var part = render(el.children[i]);
          if (part) { key.push(part); }
        }
      } else {
        var text = render(el);
        if (text) { questions.push(text); }
      }
      el = el.nextElementSibling;
    }
    return { questions: questions.join("\n\n"), key: key.join("\n\n") };
  }
  function phaseTitle(heading) {
    var el = heading.previousElementSibling;
    while (el) {
      if (el.tagName === "H2") { return headingText(el); }
      el = el.previousElementSibling;
    }
    return "the CS course";
  }
  function buildPrompt(heading) {
    var section = collect(heading);
    return [
      "I am self-studying the computer-science course built on the Poggio Civitate documentation, and I want you to grade one assessment.",
      "",
      "ASSESSMENT: " + phaseTitle(heading) + " / " + headingText(heading),
      "",
      "QUESTIONS",
      section.questions,
      "",
      "ANSWER KEY - grade against this. Numeric keys: allow equivalent forms. 'Criteria' keys: judge substance against the listed criteria, not wording.",
      section.key || "This assessment is self-checking: grade against the evidence and checklist stated in the questions themselves.",
      "",
      "HOW TO GRADE",
      "- My answers are at the end of this message. If the MY ANSWERS section is empty, ask me for them and wait.",
      "- Score every answered question; the pass bar is 80% unless the key states its own.",
      "- For each miss: say what was missing, quote the relevant key line, and name the documentation page to reread.",
      "- Leave unanswered questions ungraded and do not reveal their answers, so I can retry.",
      "- Finish with: score, pass or fail, and the three most valuable things to review.",
      "",
      "MY ANSWERS",
      ""
    ].join("\n");
  }
  function addButton(heading) {
    var wrapper = document.createElement("div");
    wrapper.className = "assessment-copy";
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Copy for feedback";
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(buildPrompt(heading)).then(function () {
        button.textContent = "Copied - paste into Claude, add answers";
        setTimeout(function () { button.textContent = "Copy for feedback"; }, 3000);
      }, function () {
        button.textContent = "Copy failed - select the section by hand";
      });
    });
    wrapper.appendChild(button);
    heading.insertAdjacentElement("afterend", wrapper);
  }
  function init() {
    var headings = document.querySelectorAll("h3");
    for (var i = 0; i < headings.length; i++) {
      if (GRADEABLE.test(headingText(headings[i]))) { addButton(headings[i]); }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>
