---
title: Learning plan
audience: beginner
status: current
source_files:
  - mkdocs.yml
  - poggio_webapp/app.py
verified_against: de07c37
---

# Learning plan: the Poggio Civitate documentation

A study plan for someone who has never seen this repository and has taken one
basic computer science course. Followed end to end, it covers every page of
the documentation: what order to read in, what to do alongside the reading,
and how to check you actually understood each stage before moving on.

A companion assessment pack (a pre-reading quiz, programming assignment,
research paper, midterm, and final exam for every phase below) is in
[the assessment pack](assessments.md). The phase checkpoints in this file
are the minimum; the assessment pack is the full course.

Only here for the algorithms? [The computer science course](cs-plan.md)
covers the CS section alone (ten units over the same 128 technique pages,
with its own all-new assessments) and skips the archaeology entirely.

## Who this assumes you are

- You can open a terminal, change directories, and run commands, even if you
  have to look up the syntax.
- You have written small programs in some language. You know what a variable,
  a loop, a function, and a list are.
- You do not know image processing, linear algebra beyond high-school math,
  graph theory, web development, or archaeology. The docs teach all of these
  from zero; this plan sequences them so nothing is needed before it is taught.

You also need: a computer with Python 3.11 or newer, and on Windows either
WSL or Git Bash (the commands assume a Unix-style shell).

## What you are looking at

The project turns a drawing of an excavated trench wall into structured,
checkable data and, optionally, a 3D geological model. One diagram on the
docs home page shows the whole thing:

**Drawing → Prepare image → Trace/import/extract → Normalize → Validate →
Convert to site coordinates → Build model → View and download**

Memorize those boxes early. Every one of the ~225 documentation pages expands
one of them. When you feel lost, ask "which box am I in?" and you usually
won't be lost anymore.

### What counts as "the documentation"

Everything under `docs/` (published as an MkDocs site), plus the two READMEs:

| Section | Pages | Words (approx.) | What it is |
|---|---|---|---|
| Home + Start here | 8 | 6,600 | Orientation, quickstart, demo, tutorial, glossary |
| Workflows | 14 | 10,900 | The pipeline as numbered how-to steps, 01–09 plus extras |
| Worked example | 5 | 6,400 | One real trench (T905) followed end to end |
| Concepts | 8 | 6,000 | Why the system works the way it does |
| Project | 4 | 4,500 | Capability status, roadmap, history |
| Architecture | 10 | 8,600 | How the software is built |
| Computer science | 129 | 148,900 | Every technique the code uses, one page each |
| Archaeology | 39 | 41,500 | Every site term the project uses, one page each |
| Reference | 9 | 15,500 | Exact schemas, routes, formats, troubleshooting |
| **Total** | **~225** | **~249,000** | |

### What to skip

- `site/`: the generated HTML build of `docs/`. Never read it; read `docs/`.
- `docs/_meta/`: internal templates for people writing docs, excluded from
  the published site.
- `local/`: personal working notes, not documentation.
- The root-level `*_PLAN.md` and `*_CONTRACT.md` files: internal engineering
  task contracts from past development pushes. The parts that matter to a
  reader were distilled into `docs/project/history.md`, which you will read.

## How big the job is, honestly

About 249,000 words of technical prose, roughly a dense textbook. Budget
**65–80 hours** of reading, hands-on work, and self-testing.

- At ~10 hours/week: about **8 weeks**.
- At ~5 hours/week: about **15–16 weeks**.

The plan below is written as ten phases with hour estimates rather than
calendar dates, so either pace works. The one scheduling rule that matters:
**never read more than about five reference pages in one sitting**, and
alternate reading with doing. The catalogue sections (CS and Archaeology) are
excellent pages, but 129 of anything in a row stops sticking.

## Four rules the docs play by

Learn these before phase 1; the docs rely on them everywhere.

1. No dead ends. Every page ends with a `Next` or `Related` section. If
   you finish a page and wonder where to go, the answer is at the bottom of it.
2. Synthetic means invented. Anything labelled *synthetic documentation
   example* (coordinates, Munsell readings, whole trenches) is made up so
   you can practice safely. It is never archaeological evidence.
3. Capability status is the truth. Some pages describe things that exist
   in the code but cannot be clicked in the browser.
   `docs/project/capability-status.md` is the authoritative list of what is
   supported, experimental, backend-only, blocked, or historical. When a
   button you expected is missing, check there before assuming you broke
   something.
4. Pages cite their sources. Every page's front matter names the source
   files it describes and the commit it was verified against. If a page and
   the code disagree, the code wins, and the front matter tells you where to
   look.

## How to study these particular docs

**The pages have fixed shapes, so use them.** Workflow pages always run: Before
you start → Do this → What the application creates → Check your result →
Common problems → Under the hood → Next. The two big catalogues each use a
fixed seven-section shape too. Once you notice the shape, you can navigate
any page in seconds.

**On computer science pages, the section that matters most is "Why this and
not something else."** The CS index says so itself. "What it is" teaches the
idea; "Why this and not something else" teaches the judgment. On a first
pass it is fine to skim "What it costs" when the complexity math gets heavy;
come back to it.

**On archaeology pages, the section that matters most is "What it is not."**
The application makes distinctions a drawing doesn't: a marker is not a
feature, a feature is not a find, a layer is not always a locus, an apparent
dip is not a true dip. Confusing them produces data that validates cleanly
and means the wrong thing.

**Keep two running notes files** from day one:

- *Personal glossary*: every term, one line in your own words. Rewriting the
  definition is the digestion.
- *Confusion pairs*: a two-column table of easily-confused terms and the
  one-sentence difference. Both catalogues hand these to you explicitly;
  collect them.

**Follow "Under the hood" links when they appear.** Workflow pages link to
the concept behind each step. Reading the concept right after doing the step
beats reading concepts cold. The docs recommend this themselves.

---

## The plan

Each phase lists what to read, what to do, and a checkpoint. Do not move on
until the checkpoint feels easy; the later phases assume the earlier ones.

### Phase 0: Setup (2–3 hours)

**Do:**

- Read the root `README.md` once, fast. Don't stop at unfamiliar words.
- Follow `docs/start-here/quickstart.md` exactly: check `python3 --version`,
  create the `.venv` **at the repository root**, install
  `poggio_webapp/requirements.txt`, run `make run`, and see the app at
  `http://localhost:5000`.
- Do **not** install GemPy, do not enter any API key. The supported beginner
  path needs neither.
- Create your two notes files.

**Checkpoint:** the browser shows **Add your trench drawing**, and you can
stop the server with Ctrl+C and start it again.

### Phase 1. Orientation: what is this thing? (3–4 hours)

**Read, in order:**

1. `docs/index.md`: the home page and the seven-box pipeline diagram.
2. `docs/start-here/what-this-project-does.md`
3. `docs/start-here/how-to-read-these-docs.md`, the docs explaining
   themselves: four reading paths, the page shapes, the two warnings.
4. `docs/start-here/choose-your-path.md`: the four input routes and their
   statuses.
5. `docs/concepts/archaeology-to-3d.md`: the bridge page.
6. `docs/start-here/glossary.md`: **skim only.** One pass so you know what
   lives there. You will return constantly; do not memorize it now.
7. `docs/project/capability-status.md`: skim the table; learn the five
   status labels.

**Checkpoint:** without looking, (a) explain in three sentences what the
application does and does not claim to do; (b) name the four ways to get
drawing data in, and which is supported, which needs an API key, and which
has no browser entry point; (c) recite the seven pipeline boxes.

### Phase 2. Hands-on: run the whole pipeline once (6–8 hours)

The single most important phase. Everything after it is depth on things you
will have already done.

**Do and read, interleaved:**

1. `docs/start-here/demo.md`: run the demo.
2. `docs/start-here/first-model.md`: the guided tutorial, using a synthetic
   fixture from `docs/fixtures/` (read `fixtures/README.md`, it's one page).
3. `docs/workflows/overview.md`, then workflows **01 through 09 in order**,
   performing each step in the app as you read it: add a drawing, prepare
   the image, trace the layers, markers and features, clean up, check for
   problems, place on site, create the model, view and download.
4. As you finish each workflow page, follow its **Under the hood** link and
   read that Concepts page. Across the nine steps this covers the whole
   Concepts section (source drawing types; jobs, sheets, and trenches;
   layers and boundaries; coordinate spaces; accuracy and provenance;
   geometric normalization; markers, features, and finds).
5. Finish with the two extra workflows: `workflows/harris-matrix.md` and
   `workflows/logging-finds.md`, and skim
   `workflows/03-alternative-import-and-ai.md` so you know what the
   experimental path is. You are not expected to run it.

If the model-building step reports GemPy is unavailable, that is expected,
because it is optional and experimental. Reaching that step counts as
completing it.

**Checkpoint:** you produced (or reached the build step of) a model from a
synthetic drawing, and for each of the seven pipeline boxes you can say what
it did *to your data*, not in general, but in the job you just ran.

### Phase 3. Consolidate: one real trench, and the anatomy vocabulary (5–6 hours)

**Read:**

1. The entire **Worked example** section, in order (5 pages): the T905
   trench end to end. Registration, stratigraphy, the sounding, and
   `finds-and-limits.md`, which shows what the record *cannot* support.
   This is phase 2 again, but with real archaeological reasoning attached.
2. Archaeology cluster 1, **The trench and its anatomy** (10 pages): trench,
   trench profile, wall and baulk, face, locus, layer, boundary, cut, fill,
   natural. Read "What it is" and "What it is not" first on every page.

**Checkpoint:** sketch a trench from memory and label wall, baulk, face,
layers, a cut and its fill, and natural. Explain the locus/layer distinction
in two sentences. Your confusion-pairs table should have at least five rows.

### Phase 4: Archaeology, the rest (8–10 hours)

**Read, a few pages per sitting:**

1. Cluster 2, **Stratigraphy and chronology** (12 pages), which pairs directly
   with the Harris matrix workflow you ran in phase 2. Core run:
   stratigraphy → law of superposition → stratigraphic relationships →
   Harris Matrix → correlation, then the rest.
2. Cluster 3, **Survey, measurement, and recording** (13 pages), which pairs with
   the "place on site" workflow. Core run: datum → elevation → site
   coordinates → grid registration → bearing and azimuth → apparent and true
   dip, then the rest.
3. **Records beyond this application** (3 pages): Geospatial Spreadsheet,
   Kobo locus import, provenance links.

**Checkpoint:** on the sample recording sheet (`archaeology/recording-sheet.md`),
point at the datum reference, an elevation, a Munsell reading, and a locus
number. Explain apparent versus true dip in one sentence each. Explain what a
Harris matrix shows that a section drawing doesn't.

### Phase 5: How the software is built (6–8 hours)

Now the machinery. You know what it does; this is how.

**Read:**

1. The rest of **Project** (roadmap, history, contributing-docs; you
   already know capability-status).
2. All of **Architecture**, in nav order (10 pages): system overview, job
   lifecycle, frontend, backend, pipeline, asynchronous tasks, files and
   artifacts, pipeline walkthrough, codebase review, algorithm index. Note
   what the **algorithm index** is: the CS catalogue re-sorted by source
   file. It is your map for phases 6–8.
3. **Reference**, calibrated: read `drawing-guidelines.md` and
   `troubleshooting.md` fully; *skim* data schemas, validation rules, API
   routes, output files, and configuration (the goal is knowing what each
   contains, not retaining it); and follow `running-the-tests.md` once,
   actually running `make test`.

**Checkpoint:** trace one uploaded image through the job lifecycle, naming
what appears on disk under `poggio_webapp/jobs/` and which part of the system
(frontend, backend, pipeline, async task) touches it at each stage. Then,
using only the Reference section, find the definition of any schema field in
under two minutes.

### Phases 6–8: The computer science catalogue (128 pages, ~35 hours total)

Three fifths of the documentation by volume. The pages are written for
readers with *less* CS than you: plain language first, one worked numeric
example each, then the real code that uses it. Two strategies make the
catalogue tractable:

- Read in cluster order, not alphabetically. The clusters are a
  dependency chain; each phase below groups them so nothing appears before
  its prerequisite.
- Anchor every cluster to something you already did. Before each group,
  re-open the workflow or architecture page it explains; after it, open the
  algorithm index entry for one module and recognize the techniques by name.

Pace: 2–4 pages a day is sustainable; a page is ~1,100 words.

#### Phase 6: Seeing like a computer (45 pages, 10–12 hours)

How a photograph of a drawing becomes clean geometry. Anchor: re-run
workflow 02 (prepare the image) first, and skim the AI-extraction page.
These clusters *are* that code.

Clusters, in order: **Images and pixels** (6) → **Filtering and
enhancement** (9) → **Thresholding and masks** (5) → **Morphology** (5) →
**Edges, lines, and contours** (7) → **Shape description** (9) →
**Candidate filtering** (4).

The chain is real: convolution → Gaussian blur → gradients → Canny;
thresholding → masks → morphology → contours → shape measures. Do not
reorder.

**Checkpoint:** explain, box by box, what happens to your uploaded photo
during "prepare the image," and for any three techniques, give the
one-line answer to "why this and not the obvious alternative?"

#### Phase 7: Geometry, math, and graphs (39 pages, 10–12 hours)

How traced pixels become site coordinates, and how loci become a matrix.
This is the steepest math for a basic-CS reader; the worked numeric examples
carry you. Do them by hand.

Clusters, in order: **Vectors and linear algebra** (7) → **Transforms** (5)
→ **Computational geometry** (9) → **Numerical methods and statistics** (7)
→ **Graphs** (11).

Anchors: vectors/transforms/geometry explain workflows 04 (clean up) and 06
(place on site), so reread those two pages first. Graphs explain the Harris
matrix workflow: DAG → cycle detection → topological sort → transitive
reduction → layered drawing is literally how the matrix is built and drawn.

**Checkpoint:** starting from a point on the drawing, narrate its journey to
site coordinates naming the transforms applied. Explain why the Harris
matrix build must reject cycles, and what transitive reduction removes.

#### Phase 8: Engineering the system (44 pages, 10–12 hours)

Why the backend is built the way it is. Anchor: skim the Architecture
section (phase 5) again first; these pages are its footnotes.

Clusters, in order: **Data structures** (5) → **Hashing, encoding, and
serialisation** (6) → **Concurrency and shared state** (5) →
**Reliability** (7) → **Validation and error handling** (4) →
**Architecture** (8) → **Security** (4) → **Scientific computing
practice** (5).

Read **Scientific computing practice last, and read it slowly.** Provenance,
human-in-the-loop review, fabrication detection, interpolation versus
measurement: this cluster is the ideology of the entire project, and by now
you will recognize every example it uses.

**Checkpoint:** answer in your own words: why are job writes atomic? Why is
validation repeated at trust boundaries even for data the app itself wrote?
Why does the AI-extraction path force human review before commit? What is
the difference between a measured point and an interpolated one, and where
does the data record it?

### Phase 9. Synthesis: prove it stuck (4–6 hours)

1. Reread `docs/index.md`. The seven-box diagram should now decompress: for
   every box you can name the workflow step, the concepts, the algorithms,
   and the archaeology terms inside it.
2. Do the glossary as a flashcard pass: cover each definition, recite your
   own. Anything shaky, follow into its full catalogue page.
3. Quiz yourself from your confusion-pairs table: marker/feature/find,
   locus/layer, apparent/true dip, normalize/validate, measured/interpolated.
4. Open `architecture/algorithm-index.md`, pick five modules at random, and
   say from the name of each listed technique what the module does.
5. The final exam: run the entire workflow on a fresh synthetic fixture
   **without opening the docs**, then write a one-page summary of the
   project in your own words: what it does, what it refuses to do, and why.

If step 5 works, you have not just read the documentation; you have digested
it.

---

## Suggested calendar at ~10 hours/week

| Week | Phases | Milestone |
|---|---|---|
| 1 | 0, 1, start 2 | App running; orientation pages done |
| 2 | 2, start 3 | Full pipeline run on a synthetic drawing |
| 3 | 3, 4 | Worked example + all 38 archaeology terms |
| 4 | 5 | Architecture and reference mapped |
| 5 | 6 | Image-processing clusters (45 pages) |
| 6 | 7 | Geometry, math, and graph clusters (39 pages) |
| 7 | 8 | Engineering clusters (44 pages) |
| 8 | 9 | Synthesis, self-tests, final run |

At 5 hours/week, double every row.

## When you get stuck

- Unfamiliar word → glossary → that term's full page. One paragraph or one
  page deep, your choice.
- Lost in a workflow → its **Common problems** section, then
  `reference/troubleshooting.md`.
- A described button doesn't exist → `project/capability-status.md`, rule 3.
- Totally disoriented → ask "which of the seven boxes am I in?", reread that
  workflow page, and follow its links outward.
- A page seems wrong → check its front matter for the source files and
  verified commit; the code wins.
