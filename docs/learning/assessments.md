# Assessments for the learning plan

A companion to [the learning plan](plan.md). Each of the ten phases gets
five assessments:

1. a **pre-reading quiz** — taken before opening any page of the phase;
2. a **programming assignment**;
3. a **research paper assignment**;
4. a **midterm exam** — taken partway through the phase, where noted;
5. a **final exam** — taken at the end, replacing or extending the plan's
   checkpoint.

## The design rule

Quizzes and exams face the documentation: they test what the docs teach,
using the project's own material. **Programming and research assignments face
away from it**: same subject, entirely different domain — cooking, fitness
tracking, photo libraries, orienteering, movie nights. That is deliberate.
If you can only apply an idea to trenches, you memorized the docs. If you can
apply it to a jogging route or a recipe box, you learned the idea. Transfer
is the test of digestion.

| Phase | Programming assignment (domain) | Research paper (domain) |
|---|---|---|
| 0 | Habit-tracker CLI (personal productivity) | The left-pad incident (software ecosystems) |
| 1 | Chat-log pipeline (text analytics) | Docs audit of an open-source project (technical writing) |
| 2 | Recipe box digitizer (cooking) | When paper becomes data (archives, another field) |
| 3 | The Trifle Inspector (dessert engineering) | Controlled vocabularies (medicine, libraries, aviation) |
| 4 | Essay forensics + treasure hunt (collaboration, orienteering) | Where is zero? (geodesy, aviation, construction) |
| 5 | Movie Night web app (entertainment) | Reference doc for a public API (open data) |
| 6 | Photo filters + candy census (photography) | One technique, another world (medicine, astronomy, forensics) |
| 7 | Run tracker + degree planner (fitness, academics) | The name in the method (history of science) |
| 8 | Photo twin finder + unbreakable journal (photo libraries, journaling) | Anatomy of a failure (safety engineering) |
| 9 | A digitizer for another record type (your choice) | Digitization in the wild (citizen science, archives) |

## Workload, honestly

The plan alone is 65–80 hours. These assessments add roughly **55–75 hours**
(most of it the programming assignments). The combined total, 120–155 hours,
is a university semester course. If that is more than you want, the natural
trims are: skip the research papers (−15 h), or do only the phase finals and
the capstone. Do not trim the programming assignments — they are where the
digestion happens.

## Ground rules

- **Self-graded.** Answer keys sit in collapsed blocks. Finish before you
  open them.
- **Pass bar is 80%** on every exam unless stated otherwise, all questions
  equal weight. Below the bar: reread the pages the missed questions cite,
  wait a day, retake.
- **Timing is honor system.** The times are calibrated; running long is
  information, not failure.
- **Criteria keys.** Essay questions get a list of what a good answer
  contains rather than a model answer. Grade yourself against the list.
- **Where a key says "verify against \<page\>",** that page is authoritative
  and this pack is not. The docs' own rule — the source wins — applies to
  this file too.
- Pre-reading quizzes are **diagnostic, not graded**. Wrong answers cost
  nothing; they tell you what to slow down for. Take them closed-book,
  before reading, then check.

---

## Phase 0 — Setup

*Subject: the command line, Python environments, dependency isolation,
running a local application.*

### Pre-reading quiz (10 minutes, before touching the terminal)

1. You run `cd docs`, then `cd ..`. What directory are you in now?
2. A file lives at `/Users/you/projects/app/data.json` and your terminal is
   "standing in" `/Users/you`. Write a relative path to the file.
3. What does `python3 --version` do — and why might `python` and `python3`
   behave differently on the same machine?
4. True or false: installing a Python package for project A can break
   project B.
5. What does it mean for a program to be "listening on port 5000"?
6. In one sentence: what is a dependency?
7. `make run` — what kind of tool is `make`?
8. What does Ctrl+C do in a terminal?
9. What is an environment variable, loosely?
10. A command prints `command not found`. Name two possible causes.

<details markdown="1">
<summary>Answer key</summary>

1. Back where you started — `..` means the parent directory.
2. `projects/app/data.json`.
3. Prints the interpreter's version; `python` and `python3` can point at two
   different installations (or `python` may not exist at all).
4. True — if both share one Python environment, their package versions can
   conflict. This is the whole reason virtual environments exist.
5. It has claimed that port number and accepts network connections to it;
   only one program can hold a port at a time.
6. Code your code needs but did not write — a library someone else maintains.
7. A task runner: it executes named recipes (like `run` or `test`) defined
   in a file called `Makefile`.
8. Interrupts the running program — how you stop a server.
9. A named value the operating system hands to programs, which they can read
   to change behavior (for example `PORT`).
10. The program isn't installed; or it's installed but not on the shell's
    search path (or you typo'd it).

**Scoring guidance:** 7+ correct, proceed. Below 6, spend an hour with any
introductory shell tutorial first — Phase 0 will go from frustrating to easy.

</details>

### Programming assignment — Habit Tracker CLI (3–5 hours)

Build a command-line habit tracker. Personal productivity, zero archaeology.

**Spec:**

- `python habits.py add "Stretch"` — register a habit.
- `python habits.py done "Stretch"` — record a completion for today.
- `python habits.py report` — print a table: habit, total completions,
  current daily streak.
- Data persists in a single `habits.json` between runs.
- Use one third-party package — `rich` is suggested for the table — so that
  the assignment forces a real dependency.

**The actual point** (worth more than the features):

- Create the project in a **fresh virtual environment** of its own.
- Write a `requirements.txt` with the dependency **pinned** to an exact
  version.
- Write a `Makefile` with `run` and `clean` targets that use the venv's
  Python explicitly.
- Write a `README.md` quickstart in the docs' workflow-page shape: *Before
  you start → Do this → Check your result → Common problems*. Your Common
  problems section must contain at least three entries you actually hit or
  can provoke.

**Rubric (100):** works as specced 40 · venv + pinned requirements +
Makefile 25 · README quickstart with honest Common problems 25 · code
readability 10.

### Research paper — The Day Eleven Lines Broke the Internet (1,000–1,500 words)

In March 2016, a developer unpublished a package called `left-pad` — eleven
lines of code — and build systems across the industry stopped working.
Research the incident and write it up for a reader who has never installed a
package.

**Must cover:** what happened and in what order; why thousands of unrelated
projects depended on eleven lines; what pinning, lockfiles, and vendoring
each do to prevent this; and one paragraph connecting back to why this
repository pins its requirements. **At least 4 sources**, including one
contemporaneous news account or postmortem.

**Rubric (100):** accurate sequence of events 30 · clear explanation of
transitive dependency risk 30 · the three mitigations correctly
distinguished 25 · sources cited 15.

### Midterm exam — terminal practical (20 minutes, open notes)

Do these in a scratch directory, not in the repository. Each item is
self-checking: the expected evidence is listed.

1. Print your current directory. *(Evidence: `pwd` output.)*
2. Count the Markdown files in the repository's `docs/cs/` directory using
   any command. *(Evidence: the number — it should be 129.)*
3. Create a virtual environment in the scratch directory, activate it, and
   prove activation. *(Evidence: `(venv)` prefix, or `which python` pointing
   into the venv.)*
4. Install `requests` inside it, and show it is **not** installed outside
   it. *(Evidence: `pip show requests` succeeds inside; after `deactivate`,
   the same command fails or shows a different location.)*
5. Run any command with a temporary environment variable set, e.g.
   `GREETING=hi python -c "import os; print(os.environ['GREETING'])"`.
   *(Evidence: it prints `hi`.)*
6. Deactivate and delete the venv. *(Evidence: prompt prefix gone, directory
   removed.)*

Pass: 5 of 6 without a search engine.

### Final exam — the broken-setup clinic (30 minutes, closed notes)

Six scenarios. For each: diagnose the cause in one sentence, then give one
command (or observation) that would confirm the diagnosis.

1. `make run` fails with `.venv/bin/python: No such file or directory`.
2. `python` reports `No module named flask`, though you installed the
   requirements an hour ago and it worked.
3. On macOS, the app starts but the browser at `localhost:5000` shows a
   different service entirely.
4. On a fresh laptop, `python3 --version` prints `command not found`.
5. You ran `pip install -r poggio_webapp/requirements.txt` **without** an
   active venv. It succeeded. Why is this still a problem?
6. You created the virtual environment inside `poggio_webapp/` instead of
   the repository root. `python` works fine there — but which things break,
   and why?

<details markdown="1">
<summary>Answer key</summary>

1. No venv at the repository root (wrong directory, or never created).
   Confirm: `ls Makefile .venv` from where you ran make.
2. The venv is not active in this terminal (each new terminal needs
   `source .venv/bin/activate`). Confirm: prompt lacks `(.venv)`, or
   `which python` points outside the repo.
3. Port 5000 is already held by another program — on macOS, commonly the
   AirPlay Receiver. Confirm/fix: `PORT=5001 make run` and browse to 5001.
4. Python isn't installed; install 3.11+ from python.org.
5. The packages went into the shared user/system environment: they can
   conflict with other projects, and the isolation that makes this project
   reproducible is gone.
6. Every `make` target looks for `.venv` at the repository root, so
   `make run`, `make test`, and `make docs` all fail to find their tools —
   the quickstart warns about exactly this. Fix: recreate it at the root.

Pass: 5 of 6.

</details>

---

## Phase 1 — Orientation

*Subject: what the system claims, how the documentation is organized,
pipelines as a way of thinking, capability status.*

### Pre-reading quiz (10 minutes)

1. A letter goes from a mailbox in one city to a doorstep in another. List
   the stages it passes through. (Any reasonable decomposition.)
2. What is the difference between "the software has feature X somewhere in
   its code" and "a user can reach feature X"?
3. You photograph a painting. Name two kinds of information the photograph
   loses.
4. A program's documentation says one thing; the running program does
   another. Which is "the truth," and what should be fixed?
5. What is JSON, loosely?
6. Why might a project deliberately label some of its example data as
   invented?
7. What is an API key, and why would software ask for one?
8. Try, from the name alone, to put these in order: *validate, trace,
   prepare, view, convert, build, normalize*. Don't worry about being wrong.

<details markdown="1">
<summary>Answer key</summary>

1. Collection → sorting → transport → local sorting → delivery, or similar.
   The point: multi-stage systems with hand-offs are everywhere.
2. Existence versus reachability — code can exist with no route to it from
   the interface. This project labels that state `backend-only`.
3. Texture/relief, true color under other light, scale, the back of the
   canvas... any two. Every representation loses something.
4. The behavior is the truth; either the docs get corrected or the behavior
   is a bug — but you debug against reality, not prose.
5. A plain-text format for structured data: nested objects (`{}`), lists
   (`[]`), strings, and numbers.
6. So no one ever mistakes practice data for real evidence — invented
   coordinates must never end up in a scientific record.
7. A secret string identifying/authorizing your access to an external
   service; the software asks because the service bills or rate-limits use.
8. Prepare → trace → normalize → validate → convert → build → view. You'll
   memorize this within the week.

</details>

### Programming assignment — The Group Chat Anthropologist (4–6 hours)

Build a five-stage text pipeline that turns a messy chat export (or any raw
text: meeting notes, a movie script) into a report — and, more importantly,
leaves an inspectable trail.

**Stages:** 1 strip timestamps/metadata → 2 normalize speaker names
("Sam", "sam_photos", "Samuel" → one canonical name, via a mapping you
write) → 3 drop noise lines (joins, reactions, empty) → 4 compute counts
(messages per person, top words) → 5 render `report.md`.

**Requirements:**

- Each stage is a function that **reads the previous stage's output file and
  writes its own** (`stage1.txt`, `stage2.txt`, ...). No stage reaches back
  to the raw input.
- A `manifest.json` accumulates one entry per stage: input file, output
  file, and a one-line description of what changed, with counts (lines in,
  lines out).
- `python pipeline.py run` executes all stages; `python pipeline.py inspect 3`
  prints stage 3's manifest entry and the first 10 lines of its artifact.

This is the shape of the project's job pipeline — staged artifacts you can
inspect between steps — applied to text analytics.

**Rubric (100):** stages correct and isolated 35 · artifacts + manifest 30 ·
`inspect` command 15 · README and code clarity 20.

### Research paper — Audit Someone Else's Documentation (1,200–1,800 words)

Pick an open-source project you actually use (a game emulator, a note-taking
app, a CLI tool). From its documentation, extract **five concrete claims**
("supports export to PDF", "works offline"). Test each one. Assign each a
status from this project's vocabulary — supported, experimental,
backend-only, broken/blocked, or stale — with your evidence.

**Deliverable:** a short paper containing a capability table (claim, status,
evidence) plus a discussion: where had the docs drifted from the software,
and what would have caught the drift?

**Rubric (100):** five genuinely testable claims 20 · evidence quality 40 ·
correct use of the status vocabulary 20 · discussion of drift 20.

### Midterm exam (30 minutes, closed docs)

1. Recite the seven pipeline boxes, in order.
2. Name the four ways to get drawing data into the application, and the
   capability status of each.
3. Which route(s) require an API key, and for which external service?
4. List the five capability status labels.
5. What exactly does the label *synthetic documentation example* promise,
   and what does it forbid?
6. The "How to read these docs" page issues two warnings. What are they?
7. A page and the code it describes disagree. Which wins, and what part of
   the page tells you where to look?
8. You need the exact format of an output file. Which of the nine sections
   do you open?
9. The glossary and the Archaeology reference both define terms. What is
   the difference in their job?
10. Which section does the how-to-read table say to consult "before
    trusting anything"?

<details markdown="1">
<summary>Answer key</summary>

1. Prepare image → trace/import/extract → normalize → validate → convert to
   site coordinates → build model → view and download.
2. Manual tracing (supported) · JSON import (supported) · AI-assisted
   extraction (experimental) · field-sheet marker workflow (backend-only, no
   browser entry point).
3. Only AI-assisted extraction; a Gemini key.
4. Supported, experimental, backend-only, blocked, historical.
5. Promises the data is invented and safe to copy while learning; forbids
   ever treating it as archaeological evidence.
6. Synthetic data is labelled; and a page can be current yet describe a
   capability you cannot click (implemented but not reachable in the UI).
7. The code wins; the front matter's `source_files` list says which files.
8. Reference.
9. Glossary: one paragraph per term, for while you work. Archaeology
   reference: one full page per term, in depth, including what it is *not*.
10. Project (capability status).

</details>

### Final exam (45 minutes, closed docs)

**Part A — routing scenarios.** For each person, name the right path and
one sentence of justification.

1. A student has a hand-drawn field sheet, no API key.
2. A colleague sends a JSON file this application produced last season.
3. A supervisor asks you to evaluate the automatic reading of a prepared
   image, and you have a Gemini key.
4. Someone wants the automated marker detection reviewed in the browser.

**Part B — navigation.** Name the specific section (and page, if you can)
you would open to answer:

5. "What field holds a boundary's points in the saved data?"
6. "Why does the app normalize geometry before validating it?"
7. "Is the 3D model build dependable enough to demo tomorrow?"

**Part C — comprehension.**

8. Name the five front-matter fields the docs' pages carry, and what the
   last two are for.
9. **Essay (5–8 sentences):** Explain to a museum curator what this
   application does, what it deliberately does not do, and why a successful
   validation still isn't a scientific conclusion.

<details markdown="1">
<summary>Answer key</summary>

1. Manual tracing — the supported path; field sheets are explicitly
   suited to it.
2. JSON import — but continue to the checking step; import verifies shape,
   not full validity.
3. AI-assisted extraction — experimental; output is a transcription to
   review against the drawing, not evidence.
4. No path — that workflow is backend-only with no UI entry point; the
   honest answer is "not currently possible in the browser," citing
   capability status.
5. Reference → data schemas.
6. Concepts → geometric normalization.
7. Project → capability status (model building is experimental; GemPy is
   optional and not installed by default).
8. `title`, `audience`, `status`, `source_files`, `verified_against` — the
   last two name the described source files and the commit the page was
   checked against, so disagreements can be resolved against the code.
9. Criteria: turns trench-wall drawings into structured, checkable data
   (and optionally a 3D model) · a person traces and reviews · it does not
   judge archaeological interpretation · validation catches detectable
   problems only · placeholder coordinates stay untrustworthy until real
   survey data replaces them · the drawing remains the evidence. 4+ of
   these = pass.

</details>

---

## Phase 2 — Hands-on: the pipeline

*Subject: staged workflows, structured data, normalization versus
validation, jobs and artifacts, provenance.*

### Pre-reading quiz (10 minutes)

Given this JSON:

```json
{"sheet": "north-wall", "layers": [{"name": "topsoil", "points": [[0, 0], [4, 0]]}]}
```

1. How many layers are recorded, and what is the first point of the first
   one?
2. Is `{'sheet': 'north-wall'}` valid JSON? Why or why not?
3. On a computer screen, where is the origin (0,0), and which way does y
   grow?
4. In your own words, guess the difference between *cleaning* data and
   *checking* data.
5. A program compares the strings `"2 m"` and `"200 cm"`. Equal?
6. A program is given a file it can only partly understand. What should it
   do: load the part it understood, or refuse with a clear message? Defend
   your choice.
7. What is a schema, loosely?
8. After tracing a drawing into data, why keep the original photograph?

<details markdown="1">
<summary>Answer key</summary>

1. One layer; `[0, 0]`.
2. No — JSON requires double quotes. (Python dictionaries accept single
   quotes, which is exactly why the confusion exists.)
3. Top-left, y grows downward — the opposite of graph paper. This will
   matter constantly.
4. Cleaning/normalizing *changes* data into a canonical form without
   changing meaning; checking/validating *detects* problems without
   changing anything. The docs hold this line strictly.
5. No — string comparison knows nothing about units. Something must
   normalize before anything can compare.
6. Refuse clearly (or load with loud warnings). Half-understood data that
   loads silently becomes trusted data. You'll meet this as "fail closed"
   in Phase 8.
7. A description of the shape data must have: which fields, which types,
   what's required.
8. The photograph is the evidence; the tracing is an interpretation of it.
   If a question arises later, you go back to the source. That is
   provenance, and it is this project's core value.

</details>

### Programming assignment — The Recipe Box Digitizer (6–8 hours)

The project's pipeline — capture → normalize → validate → convert — applied
to cooking.

**Input:** three real recipes you like, typed up as plain text exactly as
their sources wrote them (inconsistent units and all).

**Stage 1, capture:** parse each into JSON with this schema —
`{"name": str, "servings": int, "ingredients": [{"quantity": number,
"unit": str, "item": str}], "steps": [str]}`.

**Stage 2, normalize:** canonicalize without changing meaning: unit synonyms
(`T`, `tbsp`, `tablespoon` → `tbsp`), fractions to decimals (`1/2` → 0.5),
item names lowercased and singular. Keep a written table of every rule you
apply.

**Stage 3, validate:** at least six rules, each producing a message that
**names the location** ("recipe 2, ingredient 3: quantity must be positive").
Suggested rules: positive quantities; units from a known list; servings a
positive integer; no duplicate ingredients; no empty steps; every
ingredient mentioned by at least one step (report as a warning, not an
error — decide why the severities differ and write it down).

**Stage 4, convert:** rescale any recipe to a different serving count, and
emit one aggregated shopping list across all three recipes (same item +
same unit merge; incompatible units must *not* silently merge).

**Rubric (100):** parse 30 · normalize with rule table 20 · validation
messages that locate the problem 25 · conversion and honest aggregation 15 ·
README 10.

### Research paper — When Paper Becomes Data (1,500–2,500 words)

Pick one field that digitizes historical paper records — ship logbooks
(the Old Weather project), herbarium sheets, baseball scorecards,
19th-century weather registers, parish registers. Research how its records
go from paper to database and write for a reader from that field.

**Must cover:** what the paper record holds; what the digital schema keeps
and what it drops; who checks the transcription and how; and — the heart of
it — one concrete error type that would pass every automated check and
still be wrong. **At least 5 sources.**

**Rubric (100):** faithful description of the paper record 25 · schema
gains/losses analysis 30 · review process 20 · the validates-cleanly-but-
wrong example 25.

### Midterm exam (45 minutes, closed docs — take after workflow 05)

1. Name workflow steps 01 through 05, in order, from memory.
2. What is a *job*, where does it live on disk, and what happens to old
   jobs when you finish?
3. What is the prepare-image stage *for*? (Not what it does — what it's
   for.)
4. Importing a JSON file succeeded. Name the two things import actually
   verified, and the thing it did not do.
5. A traced boundary crosses itself. Which workflow step is designed to
   catch that?
6. Classify each as **marker**, **feature**, or **find** — or "none of the
   three": a bronze coin · a hearth · a drawn, numbered cross on the field
   sheet · a scatter of pottery fragments · a posthole · the sheet's north
   arrow.
7. You import a JSON file into a job where you had already traced manually.
   What does the choose-your-path page warn about this?
8. "Success means the application could read the data" — finish the
   sentence's warning, and give one concrete example.

<details markdown="1">
<summary>Answer key</summary>

1. Add a drawing → prepare the image → trace the layers → clean up the
   data → check for problems.
2. A local working directory holding one drawing's files and derived data,
   under `poggio_webapp/jobs/`; old job directories are **not** removed
   automatically.
3. To make the drawing legible for tracing/extraction — better contrast,
   corrected orientation, higher working resolution — so later stages act
   on the clearest possible source.
4. Verified: the file is JSON, and it matches one of the application's two
   top-level data shapes. Not done: full validation — you must still run
   the checking step.
5. Check for problems (05) — validation.
6. Find · feature · marker · find(s) · feature · none of the three (sheet
   furniture — it informs orientation, but it is not a marker/feature/find
   record). Verify the borderline cases against
   `concepts/markers-features-and-finds.md`.
7. Importing (or automatic reading) can **replace** manual data already in
   the job — choose one source deliberately.
8. "...not that the archaeological interpretation is correct." Example: a
   cleanly validated trace whose layer labels were transcribed onto the
   wrong boundaries — structurally perfect, archaeologically wrong.

</details>

### Final exam (60 minutes, closed docs + one practical)

**Part A — your job, box by box.** For each of the seven pipeline boxes,
state in one sentence what it concretely did to the data in the job you ran
during the tutorial. ("Normalize: straightened my tilted scan and rescaled
coordinates so the grid squares came out uniform" — your own sentences,
your own job.)

**Part B — the distinction that matters (5–8 sentences).** Normalize versus
validate: what each may and may not do, why the order matters, one example
of each from this application.

**Part C — failure triage.** Name the pipeline stage where each problem
belongs, and the doc page you'd open:

1. A PDF upload fails at the very first step.
2. Everything traced cleanly, but the model step reports GemPy is
   unavailable.
3. The trace looks perfect on screen, but placed on site the trench is ten
   times too wide.

**Part D — practical.** Rerun workflows 01–05 on a second synthetic
fixture, docs open, in under 30 minutes. Checklist: job created · ≥2 layers
traced · cleanup applied · validation passes · you can state where the job
directory is.

<details markdown="1">
<summary>Answer key</summary>

A. Graded on specificity: each sentence must name a real change in *your*
job (file, count, visual difference), not a definition. 6 of 7 specific =
pass.
B. Criteria: normalize edits toward canonical form and must not change
meaning · validate detects and reports but must not edit · normalize first,
so validation judges the canonical form · examples: unit/orientation
cleanup vs. self-intersection or missing-label errors.
C. 1: Prepare/add-drawing — PDF needs Poppler; quickstart's Common
problems. 2: Build model — GemPy optional/experimental; capability status.
3: Convert/place-on-site — scale registration; `archaeology/scale-and-dpi.md`
or workflow 06.
D. Pass = all checklist items.

</details>

---

## Phase 3 — The worked example and trench anatomy

*Subject: reading a case study critically, evidence versus interpretation,
the trench vocabulary and its is-not distinctions.*

### Pre-reading quiz (10 minutes)

1. A layer cake sits undisturbed. Which layer went on first?
2. What is a cross-section? Give an everyday example.
3. "There is a black, ashy layer here" versus "the town burned down in the
   war" — what kind of statement is each?
4. Why do archaeologists dig straight-sided, rectangular holes instead of
   just following the interesting bits?
5. Excavation removes soil permanently. What follows about record-keeping?
6. Can you put a layer back and re-excavate it more carefully next year?
7. *Locus* is Latin for "place." Guess what archaeologists might use the
   word for.
8. Why might the exact color of soil be worth recording?

<details markdown="1">
<summary>Answer key</summary>

1. The bottom one. You already believe the law of superposition; this phase
   names it.
2. A vertical slice showing internal layers — a cut cake, a road cutting, a
   sliced sandwich.
3. The first is evidence (observable now); the second is interpretation
   (an explanatory claim). Keeping them separate is the discipline's core
   habit, and this application's.
4. Straight walls give you readable vertical sections — the trench's own
   walls become the record of what you dug through. Control beats
   curiosity.
5. The records *are* the site afterward; excavation is destructive, so
   recording standards carry the entire burden of proof.
6. No. That is why the worked example keeps insisting on what the record
   can and cannot support.
7. A defined unit of excavation/recording — "that place in the trench."
   The precise project meaning arrives in this phase.
8. Color distinguishes deposits (ash, clay, topsoil) and is evidence for
   how they formed; standardized color (Munsell) makes two people's records
   comparable.

</details>

### Programming assignment — The Trifle Inspector (5–7 hours)

Stratigraphic modeling with a controlled vocabulary, applied to dessert.
(If dessert isn't your thing, the same brief works for a lasagna or the
sediment layers in a jar of muddy water.)

**Model, as JSON (schema yours to design, documented in the README):**

- A **glass** containing an ordered stack of **layers**, each with a type
  from a controlled vocabulary: `sponge`, `custard`, `jelly`, `cream`,
  `fruit-compote`.
- **Boundaries** between adjacent layers: `sharp` or `blended`.
- **Inclusions** — a whole raspberry, a chocolate shard — each belonging to
  exactly one layer.
- One **scoop event**: someone took a spoonful (a *cut* truncating one or
  more layers) and the hole was later refilled (a *fill* referencing that
  cut).

**Program:**

1. A **validator** enforcing at least six rules, with located messages:
   layer types from the vocabulary only · inclusions may not span layers ·
   a fill must reference an existing cut · a cut must truncate at least one
   layer · boundary count = layer count − 1 · stack may not be empty.
2. An **ASCII cross-section renderer**: layers as bands with a legend,
   inclusions marked, the scoop-and-fill visibly interrupting the bands.

**Deliver three fixture files:** one valid trifle, two with deliberately
planted category errors (e.g., a raspberry recorded as a layer; a fill with
no cut). Your validator must catch both plants.

**Rubric (100):** model and schema documentation 30 · validator and message
quality 30 · renderer 25 · fixtures and README 15.

### Research paper — Controlled Vocabularies Elsewhere (1,500–2,000 words)

Pick one: Linnaean taxonomy (biology), ICD codes (medicine), MARC or Dewey
(libraries), or standard phraseology (aviation). Write about it as a
controlled vocabulary: what confusions it exists to prevent, one documented
incident or cost of getting a term wrong, and how the field handles the
"what it is not" problem — the confusable near-neighbors.

**At least 4 sources.** Rubric (100): the vocabulary explained on its own
terms 30 · the incident, with evidence 30 · near-neighbor analysis 25 ·
writing for an outside reader 15.

### Midterm exam (40 minutes, closed docs — take after the worked example, before the anatomy cluster)

1. What did *registering* T905 establish, and why does everything after
   depend on it?
2. The sounding chapter treats the sounding "as measured geometry." What is
   that framing careful *not* to claim?
3. Give one specific claim the worked example says the record cannot
   support, and why.
4. Classify each as **evidence** or **interpretation**: "layer 3 is dark
   grayish brown" · "layer 3 is a destruction deposit" · "the boundary
   between layers 1 and 2 is gradual" · "the wall was built before layer 2
   accumulated" · "the site was abandoned suddenly" · "locus 5 contained
   three bronze fragments."
5. The workflows used synthetic fixtures; the worked example uses a real
   trench. What does the switch teach that fixtures cannot?

<details markdown="1">
<summary>Answer key (criteria)</summary>

1. Criteria: its position/orientation in the site coordinate system — the
   link between drawing measurements and real survey control. Everything
   downstream converts through it. Verify details against
   `worked-example/registration.md`.
2. Criteria: that measured geometry is not automatically archaeological
   truth — measurements carry uncertainty and the geometry supports only
   what was actually measured. Verify against `worked-example/the-sounding.md`.
3. Any specific limit the finds-and-limits page names, stated with its
   reason (e.g., a spatial precision the recording never captured). Verify
   against `worked-example/finds-and-limits.md`.
4. E · I · E · I (inferred from stratigraphic relations, however sound) ·
   I · E.
5. Criteria: real records have gaps, ambiguity, and limits; fixtures are
   clean by construction. The worked example teaches you to read what the
   record *cannot* say — the skill fixtures can't exercise.

</details>

### Final exam (60 minutes, closed docs)

**Part A — the sketch.** Draw a trench in cross-section from memory and
label: wall, baulk, face, three layers, one boundary, one cut, its fill,
and natural. (Ugly is fine; correct is required.)

**Part B — is-not drills.** One or two sentences each:

1. Locus vs. layer.
2. Cut vs. fill — and which is younger.
3. Wall vs. baulk vs. face.
4. Natural vs. just "the deepest layer we found."

**Part C — consequences.** A recorder logs a pit's fill as an ordinary
layer in the stack. What breaks downstream, and in which pipeline stage
would it surface, if at all?

**Part D — modeling.** Write a free-form JSON-ish record of this profile:
two layers; the upper one contains a stone; a pit cuts through the upper
layer into the lower; the pit contains a distinct fill. Grading is on the
distinctions, not the syntax.

<details markdown="1">
<summary>Answer key (criteria)</summary>

A. All eight labels placed plausibly; baulk/face distinguished from
generic "wall".
B1. A locus is the recording unit assigned by the excavator; a layer is a
depositional stratum. Every layer may be a locus; not every locus is a
layer (a cut can be a locus). Verify against `archaeology/locus.md`.
B2. A cut is the *event/surface* of removal; the fill is material deposited
into it afterward — the fill is younger than the cut, and the cut is
younger than everything it truncates.
B3. The wall is the trench's vertical side; a baulk is a deliberately
unexcavated partition left standing (to preserve a readable section); the
face is the specific drawn/recorded vertical surface.
B4. Natural is the undisturbed, pre-human deposit — a geological claim
about formation, not a statement about where digging stopped.
C. Criteria: the chronology inverts — a fill is younger than every layer
its cut truncates, but recorded as a plain layer it reads as older than
what's above it; relationship-based outputs (series order, Harris matrix)
silently inherit the error; validation may pass because the data is
structurally clean — the docs' "validates cleanly and means something
else."
D. Must show: layers ordered; stone as an inclusion/feature *within* a
layer, not a layer; the cut as its own entity truncating both layers...
(actually: upper cut fully, lower partially); fill referencing the cut.

</details>

---

## Phase 4 — Chronology and survey

*Subject: relative dating from relationships; reference frames, bearings,
elevations, and scale.*

### Pre-reading quiz (10 minutes)

1. Laundry has piled on a chair all week. Where is Tuesday's shirt relative
   to Thursday's — and what everyday event breaks that rule?
2. A pit is dug through a floor. Which is younger, pit or floor?
3. Trench A has a distinctive red-clay layer. Trench B, twenty meters away,
   has one too. Same layer?
4. What compass degree number is due east?
5. Does "sea level" mean the same height everywhere on Earth?
6. What is a benchmark, in the surveying sense — guess?
7. A ball released on a tilted table rolls in one particular direction.
   What's special about that direction relative to all others on the table?
8. Your map says "1:20." What does that mean?

<details markdown="1">
<summary>Answer key</summary>

1. Tuesday's is lower — unless someone rummaged (disturbed the pile). You
   just derived the law of superposition *and* its caveat.
2. The pit — a cut is younger than whatever it cuts through.
3. Maybe — asserting it is *correlation*, and it needs justification
   (physical continuity or strong matching evidence), not assumption.
4. 090.
5. No — it varies with tides, currents, gravity, and by how each country
   defines its vertical datum. Phase 4's paper is about exactly this.
6. A fixed physical point of precisely known elevation/position that other
   measurements reference.
7. It is the steepest direction — every other direction on the table is
   less steep. That is true dip; any other direction shows an apparent dip.
8. One unit on the map is twenty of the same unit in reality — 1 cm on
   paper is 20 cm of trench.

</details>

### Programming assignment — Essay Forensics & Treasure Hunt (6–8 hours)

Two small programs, two domains, no archaeology.

**Part A — Who edited when.** A shared essay was edited by many hands.
You receive observations, one per line: `Maya over Sam` ("Maya's edit sits
on top of Sam's"). Write a program that outputs:

- a chronological order of all editors consistent with every observation,
  or
- `CONTRADICTION`, listing the impossible loop it found (`Maya over Sam
  over Maya`), or
- the order plus an `AMBIGUOUS` list of pairs the observations cannot
  order.

Constraint: no graph libraries, no reading ahead — invent your own method.
(A hint you may use if stuck: repeatedly find someone no one claims to be
over.) In Phase 7 you will learn the formal name of what you invented, and
it will be a good day.

**Part B — Treasure hunt.** A walk log:

```
start 0 0
go bearing 045 distance 30
go bearing 150 distance 42
...
```

Compute each waypoint's coordinates and print the path plus the final
distance back to start ("closing error"). Use, with azimuth in degrees from
north, clockwise: `x += d·sin(az)`, `y += d·cos(az)` — and note in your
README *why* the sine and cosine look swapped compared with math class.
Add a datum feature: given a benchmark elevation (say 100.00 m) and a rod
reading below it at each waypoint, report absolute elevations.

**Rubric (100):** Part A correct on contradiction/ambiguity cases 45 ·
Part B waypoints and closing error correct 45 · README including the
swapped-trig explanation 10.

### Research paper — Where Is Zero? (1,500–2,500 words)

Every measuring field must define its zero. Pick one and go deep: vertical
datums in mapping (NGVD29 vs. NAVD88), GPS heights (ellipsoid vs. geoid),
altitude in aviation (QNH, QFE, flight levels), or floor levels in
construction. Explain how the zero is defined, who maintains it, and what
happens at the boundaries between systems.

**Required:** one real incident of datum confusion with consequences — the
Laufenburg bridge between Germany and Switzerland (a 54 cm surprise caused
by a sign error in reconciling two national sea levels) is a fine choice if
your field doesn't offer its own. **At least 5 sources.**

**Rubric (100):** the zero precisely explained 35 · maintenance and
conversion story 25 · the incident, accurately told 25 · sources 15.

### Midterm exam (45 minutes, closed docs — take after the chronology cluster)

Units in a sounding: L1 (topsoil) lies above L2; L2 lies above L3; a pit P
cuts L2; F fills P; L1 seals (lies above) both P and F. Elsewhere, in an
unconnected sounding, layer L4 was recorded, with no relation to any of
the above.

1. Draw the Harris matrix for L1, L2, L3, P, F.
2. Which unit is oldest? Which youngest?
3. Can F and L2 be ordered? If so, how does the reasoning run?
4. Can L4 and P be ordered? What would it take?
5. State the law of superposition *with* its precondition, and name two
   things that violate the precondition.
6. What justifies correlating "the same" layer across two trenches, and
   what does mere resemblance justify?
7. The archaeology reference deliberately omits one classic concept —
   grouping units into periods of activity. Name it, and say why it is
   absent from this application.
8. What does a Harris matrix show that a section drawing does not — and
   what does it throw away?

<details markdown="1">
<summary>Answer key</summary>

1. Top to bottom: L1 → F → P → L2 → L3 (F within P; P cuts L2; chains
   linear here).
2. Oldest L3; youngest L1.
3. Yes: P cuts L2, so P is later than L2; F fills P, so F is later than P;
   therefore F is later than L2.
4. No — no recorded relationship connects the soundings. It would take a
   stratigraphic link or a justified correlation.
5. In an *undisturbed* sequence, lower deposits are earlier. Violations:
   cuts (pits, ditches), burrowing animals/roots, collapse or dumping that
   inverts material — anything post-depositional.
6. Physical continuity (trace it through) or strong matching evidence
   argued explicitly; resemblance alone justifies only a hypothesis to
   test.
7. Phasing — it is a later interpretive step, and the application records
   relationships without performing interpretation.
8. Shows pure temporal/stratigraphic relations (topology); throws away
   geometry — thickness, shape, position. The drawing is the geometry; the
   matrix is the order.

</details>

### Final exam (60 minutes, closed docs, calculator allowed)

1. Convert: N30°E to azimuth · S45°W to azimuth · azimuth 300 to bearing.
2. True dip versus apparent dip: which can never be the larger, and when
   are they equal?
3. The site datum is 151.00 m. A point measures 1.37 m below it. Elevation?
   A second datum sits at 100.00 m and a point reads 0.85 below. Elevation?
4. A drawing is 1:20. A boundary segment is 5 cm on paper — real length?
   At 1:50, a 3 cm segment?
5. A sheet was scanned at 300 DPI. A feature is 150 pixels wide on the
   scan. How wide is it on paper, and — at 1:20 — in reality?
   (2.54 cm to the inch.)
6. Interpret `10YR 5/3`: name the three parts and what the notation buys
   two archaeologists on different continents.
7. Match to purpose, one line each: interface point · orientation seed ·
   grid tie point · survey point code.
8. Why does converting a drawing to site coordinates need *both* a scale
   and an orientation — what goes wrong with only one?

<details markdown="1">
<summary>Answer key</summary>

1. 030 · 225 · N60°W.
2. Apparent dip can never exceed true dip; equal when the section plane
   runs parallel to the true-dip direction.
3. 149.63 m · 99.15 m.
4. 1.00 m · 1.50 m.
5. 150 px ÷ 300 DPI = 0.5 in = 1.27 cm on paper; × 20 = 25.4 cm real.
6. Hue 10YR, value 5, chroma 3 — a standardized color reference (Munsell)
   so both record the *same* color name for the same soil, independent of
   light, screen, or vocabulary.
7. Criteria (verify against the four pages): interface point — a measured
   point on a boundary/interface between deposits; orientation seed — the
   initial orientation reference from which a face's direction is
   established; grid tie point — a point linking the local drawing/trench
   grid to the site grid; survey point code — the shorthand identifying
   what kind of thing a surveyed point records.
8. Scale without orientation places sizes correctly but rotates the trench
   arbitrarily; orientation without scale points it correctly at the wrong
   size. Placement is position + rotation + scale — a similarity
   transform, as Phase 7 will name it.

</details>

---

## Phase 5 — How the software is built

*Subject: client/server architecture, routes, background work, files as
interfaces, reading reference material.*

### Pre-reading quiz (10 minutes)

1. You type a URL and press Enter. Sketch what happens, in 3–5 steps.
2. Client versus server: which one is the browser?
3. When a web app "saves your work," where does the work usually go?
4. What is a *route* in a web application?
5. A user's click starts a computation that takes ten minutes. Why is doing
   it inside the click's request a bad idea, and what's the usual shape of
   the fix?
6. Two users write to the same file at nearly the same moment. What can go
   wrong?
7. One URL returns HTML, another returns JSON. Who is each for?
8. What are automated tests *for*, beyond "finding bugs"?

<details markdown="1">
<summary>Answer key</summary>

1. Browser resolves the name → sends an HTTP request → server routes it to
   a handler → handler computes/reads data → response returns → browser
   renders. Any faithful sketch passes.
2. The browser is the client; the server is the program listening on a
   port (here: Flask on 5000).
3. To the server's storage — files or a database on the machine running
   the app. (In this project: JSON files under a job directory.)
4. A URL pattern mapped to a handler function — `POST /vote` runs the
   vote-recording code.
5. The request (and the user's browser) hangs, times out, blocks other
   work. Fix shape: start background work, return a job id immediately,
   let the client poll status. This is exactly the project's async-task
   design.
6. Lost updates — the second write overwrites the first, or a reader sees
   a half-written file. Phase 8 makes this precise.
7. HTML pages are for humans in browsers; JSON endpoints are for programs
   (including the app's own frontend JavaScript).
8. Encoding expectations so they're checked forever — a safety net that
   lets you change code without re-verifying everything by hand.

</details>

### Programming assignment — Movie Night (6–8 hours)

A small Flask app for choosing a movie with friends. You installed Flask in
Phase 0's quickstart; now you write one.

**Routes:**

- `GET /` — an HTML page listing candidate movies and current votes (a
  bare-bones template is fine).
- `POST /vote` — accepts `{"title": ...}` as JSON, records one vote.
- `GET /results` — JSON standings, sorted by votes.
- `POST /poster/start` — begins "generating a poster" (fake it:
  a background thread that sleeps ~10 s), returns `{"job_id": ...}`.
- `GET /poster/status/<job_id>` — `{"status": "queued" | "working" |
  "done"}`.

**Requirements:**

- Votes persist to `votes.json` on every write, so a restart keeps
  standings.
- Poster jobs tracked in an in-memory dict keyed by id. Leave a
  `# TODO: what happens if two requests write votes.json at once?` where it
  belongs — Phase 8 comes back for it.
- **Three pytest tests** using Flask's test client: a vote is recorded ·
  results are sorted · a poster job eventually reaches `done`.
- README containing a **route reference table**: method, path, request
  body, response shape — written like a reference page, because next phase
  you'll write one for someone else's API.

**Rubric (100):** routes correct 35 · persistence survives restart 20 ·
job status lifecycle 20 · tests 15 · README route table 10.

### Research paper — A Reference for Someone Else's API (deliverable is a reference document, not an essay)

Pick a free public API — PokéAPI, Open-Meteo, your city's transit feed.
Using only real calls you make (browser or `curl`), write the reference
page its users deserve: base URL · at least five endpoints with method,
parameters, and response schema (as tables) · error behavior you *provoked*
(bad id, missing parameter) and what actually came back · anything you
found about versioning or rate limits.

Close with a 500-word reflection: what did the official docs omit that you
had to discover by experiment?

**Rubric (100):** accuracy of five endpoints 40 · provoked-error section
20 · schema tables usable by a stranger 25 · reflection 15.

### Midterm exam (45 minutes, closed docs — take after the architecture section)

1. Draw the system from memory: browser frontend, Flask backend, pipeline
   modules, job directories, background tasks — with arrows for who talks
   to whom.
2. Put a job's lifecycle in order, from upload to downloadable output.
3. Which part of the system: renders the tracing canvas? · decides that a
   polygon self-intersects? · owns the job directory layout? · runs the
   slow model build without freezing the browser?
4. Why do asynchronous tasks exist in this design — what breaks without
   them?
5. What kinds of files accumulate in a job directory over a run?
   (Categories, not exact names.)
6. The algorithm index and the CS section contain the same techniques.
   What is the difference between them, and when do you reach for the
   index?
7. Why does the plan (and the docs) insist you read capability status
   *before* changing code?

<details markdown="1">
<summary>Answer key</summary>

1. Criteria: frontend JS in the browser ↔ HTTP ↔ Flask routes; routes call
   pipeline code; pipeline reads/writes the job directory; slow work runs
   as background tasks the frontend polls. Verify against
   `architecture/system-overview.md`.
2. Criteria: job created on upload → source stored → prepared image →
   traced/imported data → normalized → validated → converted → model/output
   artifacts — each stage adding artifacts to the same job. Verify against
   `architecture/job-lifecycle.md`.
3. Frontend · pipeline (validation logic) · backend (job/file management) ·
   background tasks.
4. Long computations inside a request block the browser until timeout;
   async + status polling keeps the app responsive and the work observable.
5. Criteria: the uploaded source; derived/prepared images; structured data
   (traced/normalized); validation reports; converted coordinates; model
   and export outputs. Verify against `architecture/files-and-artifacts.md`.
6. Same content, two sort orders: CS section is by *subject* (textbook
   order); the index is by *source module* — reach for it when you're
   reading a file and want to know what's in it.
7. Because implemented-but-unreachable features exist; without checking,
   you can spend days building something that already exists backend-only.

</details>

### Final exam (60 minutes: Part A closed 30 min, Part B open-docs 30 min)

**Part A — closed.**

1. The backend and the pipeline are separate layers. What belongs in each,
   and name one benefit of keeping pipeline code importable without a
   running server.
2. `make test` — what does it run, and what must be true of your terminal
   for it to work?
3. Give one reason the frontend is organized as explicit stages/steps
   rather than one big page.
4. A request writes a file while a background task reads it. In one
   sentence, why is this design worth flagging for Phase 8?

**Part B — open-docs speed lookups.** Six questions, five minutes each.
Answer *and* cite the page you found it on. The skill under test is
navigation, so a right answer without its page is half credit.

5. The exact route (method + path) the frontend polls for a job's status.
6. The schema field that stores a boundary's point list.
7. The validation rule (name or message) that fires on a self-intersecting
   polygon.
8. The output file that contains site-converted coordinates.
9. How to run the app on a port other than 5000.
10. The troubleshooting entry for a PDF that fails to prepare.

<details markdown="1">
<summary>Answer key</summary>

1. Backend: HTTP routes, request handling, job/file management. Pipeline:
   the computation — image processing, normalization, validation,
   conversion. Benefit: pipeline functions can be tested (and reasoned
   about) directly, no server, no browser — pure inputs and outputs.
2. The pytest suite over `tests/`; the repo-root venv must exist with dev
   tools installed (and be the one `make` finds).
3. Criteria: each stage maps to a pipeline step with its own artifacts and
   checks; users can stop/resume; the UI mirrors the job lifecycle.
4. Concurrent access to shared files invites races and half-read states —
   deferred, deliberately, to Phase 8.
5–10. Graded by citation: the answers live in `reference/api-routes.md`,
`reference/data-schemas.md`, `reference/validation-rules.md`,
`reference/output-files.md`, `reference/configuration.md` (or the
quickstart's `PORT=5001 make run`), and `reference/troubleshooting.md`
(Poppler). Full credit = correct value + correct page within the time box.

</details>

---

## Phase 6 — Seeing like a computer

*Subject: image processing — pixels through shape description.*

### Pre-reading quiz (10 minutes)

1. What is a pixel, and what does one "contain" in a color photo?
2. Why does a photo go blocky when you zoom far enough in?
3. Red light plus green light makes what color?
4. What is a grayscale image, in terms of what each pixel stores?
5. True or false: you can blur an image by replacing each pixel with the
   average of its neighbors.
6. What is an "edge" in an image, in terms of pixel values?
7. A histogram of an image shows what?
8. You threshold a photographed page — every pixel darker than a cutoff
   becomes black, the rest white. One corner of the photo was in shadow.
   What happens, and what would you *want* instead?

<details markdown="1">
<summary>Answer key</summary>

1. The smallest square of the image grid; typically three numbers (red,
   green, blue intensities, 0–255 each).
2. You are seeing the individual grid squares — there is no more detail
   below one pixel.
3. Yellow — screens mix light (additive), not paint.
4. One number per pixel — brightness only.
5. True. That is a box blur, and it is where Phase 6 begins.
6. A sharp change in brightness between neighboring pixels.
7. How many pixels have each brightness value — the image's tonal
   distribution.
8. The shadowed corner falls entirely below the cutoff and goes solid
   black, text and paper alike. You'd want the cutoff to adapt to each
   neighborhood — which is exactly what adaptive thresholding and CLAHE
   exist for.

</details>

### Programming assignment — Filters & the Candy Census (10–14 hours; the biggest so far)

Implement the classics yourself, then use them to count candy. Rules:
**Pillow (or equivalent) for loading and saving only** — every operation on
pixels is your own loops. NumPy optional; if you use it, still no calls to
anyone else's filter/threshold/label functions. Work on images ≤ 500 px on
the long side, and don't worry about speed.

**Part A — the filter suite**, applied to a photo you took:

1. Grayscale (luminosity-weighted, not the plain average — say why in the
   README).
2. A general 3×3 **convolution engine**: takes any kernel, handles edges
   somehow (your choice, documented).
3. Through the engine: box blur, the Gaussian-ish kernel
   `[[1,2,1],[2,4,2],[1,2,1]]/16`, sharpen, and Sobel x and y — combined
   into a gradient-magnitude image.
4. Global threshold (fixed cutoff) producing a black/white image, plus
   invert. Stretch goal: implement Otsu to pick the cutoff automatically.
5. A contact sheet: original plus every result, labeled.

**Part B — the candy census.** Photograph 15–30 candies (or coins,
buttons) scattered on plain paper, no touching. Then, with your own code:
threshold to a binary mask → find connected components via flood fill
(iterative, with your own stack — recursion will overflow; this is
foreshadowing) → for each blob compute area, bounding box, centroid, and
circularity `4πA/P²` → report a count, grouped by color (mean RGB inside
each blob) and size bucket.

Then break it: push two candies together, rerun, and explain in the README
what happened and which Phase 6 technique (morphology) exists to help.

**Rubric (100):** engine + filters correct 40 · census pipeline works on
your photo 30 · the broken-case analysis 10 · contact sheet and README 10 ·
code clarity 10.

### Research paper — One Technique, Another World (1,500–2,500 words)

Pick one, research where it came from and who depends on it now:

- **CLAHE** — invented for medical imaging; how it reveals detail in
  X-rays without amplifying noise to lies.
- **JPEG** — why compression happens in 8×8 blocks, and why text scans
  ring and smear.
- **Image stacking in astronomy** — how averaging many bad photos makes one
  good one.
- **Fingerprint enhancement** — ridge cleanup as industrial-strength
  morphology.

**Mandatory:** one hand-worked 3×3 numeric example somewhere in the paper —
your own arithmetic, shown. **At least 5 sources**, one from the field that
uses the technique (not a programming tutorial).

**Rubric (100):** technique correct in your own words 30 · the field's need
explained on the field's terms 30 · the worked example 25 · sources 15.

### Midterm exam (60 minutes, closed docs, calculator allowed — take after the Morphology cluster)

1. Convolve the center pixel: neighborhood
   `[[10,10,10],[10,100,10],[10,10,10]]`, box-blur kernel (all ones, ÷9).
   Result? What just happened to the bright speck?
2. Same neighborhood, kernel `[[0,-1,0],[-1,5,-1],[0,-1,0]]`. Result
   (before clamping)? What is this kernel for?
3. State the two kernel-weight rules: what does a kernel whose weights sum
   to 1 do, versus one whose weights sum to 0?
4. Why does grayscale conversion weight green most and blue least?
5. Otsu's method, one sentence: how does it choose the threshold?
6. A binary image contains a solid 3×3 white square and one isolated white
   pixel. With a 3×3 square structuring element: what survives erosion?
   What does dilation of the *original* produce?
6b. Morphological opening versus closing: which removes small specks,
   which fills small gaps, and what is each composed of?
7. You must separate handwriting from graph-paper grid lines. Why is a
   global threshold on the raw scan likely to fail, and name two techniques
   from this phase that address the failure.

<details markdown="1">
<summary>Answer key</summary>

1. (8×10 + 100)/9 = 180/9 = **20**. The speck was averaged away toward its
   neighbors — blur suppresses isolated detail.
2. 5×100 − 4×10 = **460** (clamps to 255). Sharpen — it exaggerates the
   center's difference from its neighbors.
3. Sum 1: preserves overall brightness — a smoothing/blurring family.
   Sum 0: responds only to *change*, zero on flat regions — an edge/detail
   detector.
4. The eye's sensitivity: green contributes most to perceived brightness,
   blue least; equal weights would look wrong.
5. It tries every threshold and picks the one best separating the
   histogram into two populations (maximum between-class variance).
6. Erosion: the square shrinks to its single center pixel; the isolated
   pixel vanishes. Dilation: the square grows to 5×5; the isolated pixel
   becomes 3×3.
6b. Opening = erosion then dilation — removes specks smaller than the
   element while restoring surviving shapes. Closing = dilation then
   erosion — fills gaps/holes smaller than the element.
7. Illumination varies across the scan (shadow, curl), so one global
   cutoff can't be right everywhere; and faint grid lines sit close to
   paper tone. Address with adaptive thresholding, CLAHE or illumination
   flattening (homomorphic correction) — any two.

</details>

### Final exam (75 minutes, closed docs, calculator allowed)

1. Canny edge detection: name its four stages in order, and explain in one
   sentence why the last stage uses *two* thresholds.
2. An L-shaped region: a 4×4 pixel square with its top-right 2×2 corner
   missing. Area? Perimeter (edge-length walk)? Then circularity `4πA/P²`
   (two decimals) — and why is a circle exactly 1?
3. Two boxes: A spans (0,0)–(4,4), B spans (2,0)–(6,4). Compute IoU.
4. Non-maximum suppression, in the detection sense: what problem does it
   solve, and what does IoU have to do with it?
5. Ramer–Douglas–Peucker with ε = 0.5 on the polyline (0,0) → (2, 0.1) →
   (4,0) → (4,4): which points survive, and why — walk the recursion.
6. Why analyze a drawing at multiple scales rather than one?
7. Design question: microscope slide, dark roughly-circular cells on a
   bright background, some debris. Compose a counting pipeline from this
   phase's parts, in order, one line of justification per part.

<details markdown="1">
<summary>Answer key</summary>

1. Gaussian smoothing → gradient (Sobel) → non-maximum suppression
   (thinning) → hysteresis. Two thresholds so weak edges are kept only when
   connected to strong ones — one cutoff either drops real faint edges or
   keeps noise.
2. Area 12. Perimeter 16 (4 + 4 + 2 + 2 + 2 + 2). Circularity
   4π·12/16² = 150.8/256 ≈ **0.59**. A circle encloses the most area per
   perimeter — the formula is normalized so that optimum equals 1.
3. Intersection (2,0)–(4,4) = 8; union 16 + 16 − 8 = 24; IoU = **1/3**.
4. A detector fires many overlapping candidates for one object; NMS keeps
   the best-scoring one and suppresses neighbors that overlap it too much —
   "too much" measured by IoU.
5. Farthest point from chord (0,0)–(4,4) is (4,0), distance ≈ 2.83 > ε →
   keep, recurse. On (0,0)–(4,0): the point (2, 0.1) deviates 0.1 < ε →
   dropped. On (4,0)–(4,4): nothing between. Survivors: **(0,0), (4,0),
   (4,4)**.
6. Features live at different sizes (fine hatching vs. layer outlines);
   one scale's noise is another's signal — small-scale passes catch
   detail, coarse passes catch structure.
7. Criteria (order matters): grayscale → contrast/illumination fix if
   needed → blur (suppress debris noise) → threshold (Otsu or adaptive;
   dark-on-bright so invert as needed) → morphological opening (remove
   debris smaller than cells) → connected components → filter by area and
   circularity (cells are round; debris isn't) → count. 6+ sensible stages
   with reasons = pass.

</details>

---

## Phase 7 — Geometry, math, and graphs

*Subject: vectors, transforms, computational geometry, statistics, graph
algorithms.*

### Pre-reading quiz (10 minutes)

1. Plot (2,3): how far right, how far up?
2. Legs 3 and 4 — hypotenuse?
3. What two things define a vector, informally?
4. You can rotate the map, or turn yourself. Same result? What changed in
   each case?
5. Speeds from a GPS jog: {4, 5, 5, 6, 30} m/s. Mean? Median? Which
   describes the run — and what is the 30?
6. A subway map: what are the nodes and what are the edges?
7. Socks before shoes, shirt before jacket. What kind of problem is
   "getting dressed in a valid order"?
8. Straight-line distance versus walking distance in a city — why do they
   differ, and which is the vector one?

<details markdown="1">
<summary>Answer key</summary>

1. Right 2, up 3.
2. 5.
3. A length (magnitude) and a direction.
4. Same relative result — you rotated the *frame* or the *object*.
   Coordinate transforms are always one of these two, and confusing them
   is the classic bug.
5. Mean 10, median 5. The median describes the run; 30 is a glitch —
   your first robust statistic.
6. Stations; the track segments connecting them.
7. Ordering items under before/after constraints — you solved it by hand
   in Phase 4; this phase names it (topological sorting).
8. The straight line is the vector's magnitude; streets constrain the
   path — graph distance versus geometric distance.

</details>

### Programming assignment — Run Tracker & Degree Planner (10–14 hours)

Two programs. Formulas are supplied; the implementations are yours. No
libraries beyond `math` (and file I/O).

**Part A — Run tracker** (fitness domain). Input: a CSV of `t, x, y`
points from a jog — synthesize your own plausible loop of 200+ points, and
plant one GPS glitch (a point 500 m off the path).

Compute and report:

1. Total distance (sum of step-vector magnitudes) and per-step speeds.
2. Mean and median speed; show both and explain in the report why they
   disagree (the glitch).
3. A simplified route via your own Ramer–Douglas–Peucker (`ε` configurable);
   report points before/after.
4. Whether the run was a closed loop (end within ε of start), and if so
   its enclosed area via the shoelace formula.
5. Whether the path self-intersects, via segment-intersection tests.

Supplied formulas: `|v| = √(vx² + vy²)` · 2D cross for orientation
`(b−a)×(c−a) = (bx−ax)(cy−ay) − (by−ay)(cx−ax)` · segments AB, CD intersect
when orientations of (A,B,C)/(A,B,D) differ and (C,D,A)/(C,D,B) differ ·
shoelace `area = ½|Σ(xᵢyᵢ₊₁ − xᵢ₊₁yᵢ)|`.

**Part B — Degree planner** (academic domain). Input: a text file of
`COURSE requires COURSE` lines for a made-up major (≥ 12 courses, ≥ 1
diamond dependency; also produce a second input with a deliberate cycle).

1. Output a valid course order — and recognize aloud (in the README) that
   this is Phase 4's essay-forensics algorithm, now with its real name.
2. Detect the cycle in the second input and print the loop itself.
3. Minimum number of semesters if you can take unlimited parallel courses
   (longest chain / level assignment).
4. For each course, how many later courses it unlocks (reachability).

**Rubric (100):** A: distances/speeds 15, robust-stats explanation 10, RDP
10, shoelace + closed-loop 10, self-intersection 5 · B: topo order 15,
cycle named 10, semesters 10, unlocks 5 · README quality across both 10.

### Research paper — The Name in the Method (1,500–2,500 words)

These techniques carry their history in their names. Pick one origin story,
tell it properly, and end with one modern, non-obvious place it runs today:

- **Kriging** — Danie Krige, 1950s Witwatersrand gold mines: estimating ore
  between boreholes. (The project uses its descendants to interpolate
  geology between measured points — mention this in one sentence, then
  leave the project alone.)
- **Least squares** — Gauss, 1801, and the rediscovery of the asteroid
  Ceres from a handful of noisy observations.
- **Graph theory** — Euler, 1736, and the seven bridges of Königsberg.
- **Topological sorting** — how `make` (which you've used since Phase 0)
  decides what to build first.

**Mandatory:** a small worked toy example of the method, by hand, in the
paper. **At least 5 sources**, one primary or near-primary (Euler's paper
in translation, Krige's 1951 paper, a `make` manual...).

**Rubric (100):** the original problem, vividly and accurately 30 · the
idea explained to a classmate 30 · the worked example 25 · the modern
sighting 15.

### Midterm exam (60 minutes, closed docs, calculator allowed — take after the Computational geometry cluster)

1. u = (2,1), v = (1,3). Compute u·v. What does its sign tell you about
   the angle between them?
2. Normalize (3,4). Why does the pipeline care about unit vectors at all?
3. Project the point (2,3) onto the x-axis direction (1,0) — and state, in
   one sentence, what "projection" buys you when a measured point must be
   expressed *along a wall*.
4. Rotate (1,0) by 90° counterclockwise about the origin. Where does it
   land?
5. Why homogeneous coordinates — what does the extra 1 make possible?
6. Shoelace: area of the triangle (0,0), (4,0), (0,3)?
7. Signed area: what does its sign encode, and name one thing the pipeline
   can standardize with it.
8. Point-in-polygon by ray casting: state the rule, and the classic
   headache case.
9. Compass azimuth 060 → mathematical angle (counterclockwise from +x)?

<details markdown="1">
<summary>Answer key</summary>

1. 2·1 + 1·3 = **5**; positive → angle under 90° (they point broadly the
   same way).
2. (0.6, 0.8) — divide by the magnitude, 5. Unit vectors carry pure
   direction, so scaling and projecting stay honest (dot with a unit
   vector = length along it).
3. (2,0) — the dot product with the unit direction gives the distance
   *along* it. That is exactly how "how far along the wall is this point"
   becomes a number.
4. (0,1).
5. Adding the 1 lets translation join rotation and scaling as matrix
   multiplication, so a whole transform chain composes into one matrix.
6. ½|0(0−3) + 4(3−0) + 0(0−0)| = **6**.
7. Traversal orientation: counterclockwise positive, clockwise negative.
   Standardizing polygon winding (so all boundaries run the same way) —
   and the orientation test underlies intersection checks.
8. Cast a ray from the point; odd crossings = inside. Headache: the ray
   grazing a vertex or running along an edge — implementations must break
   ties carefully.
9. 90 − 60 = **30°**. (Two conventions: compass measures clockwise from
   north; math counterclockwise from east. The pipeline converts;
   confusing them rotates your trench.)

</details>

### Final exam (75 minutes, closed docs, calculator allowed)

1. Data {1, 3, 3, 5}: mean, population variance, standard deviation, and
   coefficient of variation (two decimals). What is CV *for* — why divide?
2. Same data with an outlier appended: {1, 3, 3, 5, 40}. Mean and median
   now? One sentence: why the pipeline prefers medians when scans contain
   glitches.
3. Ordinary least squares in one sentence — what exactly is minimized?
   And its known weakness, connecting to question 2.
4. Kriging versus straight linear interpolation between measured points:
   what does kriging weight by, and what does it report that plain
   interpolation cannot?
5. Edges: A→B, A→C, B→D, C→D, A→D. Is this a DAG? Give two valid
   topological orders. Is a unique order guaranteed in general — when is
   it?
6. Same graph: which edge does transitive reduction delete, and why is the
   result "the same" ordering information?
7. How does DFS detect a cycle — what's the tell?
8. Union-Find: the two operations, and one sentence on what it computes
   fast that repeated searching computes slowly.
9. BFS versus DFS: which finds fewest-hop connections, and why does the
   candy-census flood fill from Phase 6 secretly belong to this family?
10. In a layered drawing of a DAG (the Harris matrix's style), what does a
    row/layer mean?

<details markdown="1">
<summary>Answer key</summary>

1. Mean 3; variance (4+0+0+4)/4 = **2**; σ = √2 ≈ **1.41**; CV ≈ **0.47**.
   Dividing by the mean makes spread unitless/relative, so you can compare
   variability across quantities of different size.
2. Mean 10.4, median 3. One wild point drags the mean anywhere; the median
   barely moves — robustness under glitches.
3. It minimizes the sum of squared vertical residuals between points and
   the fitted line. Squaring makes outliers dominate — the same fragility
   as the mean.
4. Weights by spatial correlation (near, correlated points count more, per
   a fitted model of how similarity decays with distance) and reports an
   uncertainty estimate alongside each value.
5. Yes — no cycles. A,B,C,D and A,C,B,D. Not unique in general; unique
   only when at every step exactly one vertex has no remaining
   prerequisites (a full chain forces the order).
6. A→D — it is implied by A→B→D (and A→C→D). Reduction deletes only edges
   whose ordering constraint survives via longer paths, so reachability is
   unchanged; the Harris matrix is drawn this way to show only direct
   relationships.
7. Reaching a vertex that is still on the current exploration path (a
   back edge) — you've walked into your own ancestry.
8. `find` (which group?) and `union` (merge groups). It maintains
   connected groupings incrementally in near-constant amortized time —
   answering "same component?" without re-walking the graph each time.
9. BFS — it explores in rings of increasing distance. Flood fill visits
   everything reachable within a region; with a queue it *is* BFS (with a
   stack, DFS) over the pixel-adjacency graph.
10. A rank of relative age/order: everything in a row is later than the
    rows above it connect to — position encodes the partial order, which
    is the matrix's whole message.

</details>

---

## Phase 8 — Engineering the system

*Subject: data structures in anger, hashing, concurrency, reliability,
validation, security, and scientific computing practice.*

### Pre-reading quiz (10 minutes)

1. Two people edit the same shared document offline, then both sync. What
   are the possible outcomes?
2. Why did computers ever ask you to "safely eject" a USB drive before
   pulling it?
3. What is a hash, to whatever extent you've met one?
4. An app fails to reach its server. Retrying instantly, forever, is bad
   for two different parties. Who, and why?
5. Why do sites store something derived from your password instead of the
   password?
6. A downloaded file is named `../../important.cfg`. Why should software be
   suspicious of that name?
7. In Python: `a = [1,2]; b = a; b.append(3)`. What is `a`, and what does
   that reveal?
8. A program crashes halfway through saving. What states can the file be
   in, and which is worst?

<details markdown="1">
<summary>Answer key</summary>

1. One wins and the other's work is lost; or a merge (clean or
   conflicted); or duplicates. "Last write wins" silently is the scary
   one — that's a lost update.
2. Writes are buffered; ejecting flushes them. Pull early and the file is
   half-written — the exact problem atomic writes solve.
3. A fixed-size fingerprint computed from data; same data, same
   fingerprint.
4. Bad for you (battery, blocked UI) and worse for the struggling server —
   a stampede of retries can keep it down. Hence backing off, with a
   budget.
5. So a database breach doesn't reveal passwords: a good hash runs one
   way.
6. `..` climbs directories — a filename that *navigates* can escape the
   folder you meant to confine it to (path traversal).
7. `[1,2,3]` — `b` is another name for the same list, not a copy. Shared
   mutable state in one line; Phase 8 is about what it does at scale.
8. Missing, complete, or half-written. Half-written is worst: it exists,
   parses as damaged, and can be trusted by the next reader.

</details>

### Programming assignment — Twin Finder & the Unbreakable Journal (8–12 hours)

Two tools, two domains.

**Part A — Photo Twin Finder** (photo-library domain). Point it at a folder
tree of images (seed one with deliberate duplicates under different names
and subfolders).

1. Walk the tree; compute each file's SHA-256 (`hashlib`, reading in
   chunks — note in the README why not `f.read()` the whole file).
2. Group by digest in a dict; report every duplicate set and the bytes
   reclaimable.
3. **The tool never deletes.** It writes `report.json` and prints a
   summary. Write one README paragraph on why a *reporting* tool is the
   right default for other people's photos — you are practicing fail-safe
   design, not just politeness.
4. Stretch: copy unique files into a content-addressed store —
   `store/ab/cdef123...` named by digest — and observe that duplicates
   collapse by construction. (You have just reinvented the trick Git and
   this project's artifact naming both use.)

**Part B — The Unbreakable Journal** (journaling domain). A CLI diary that
refuses to lose data.

1. Entries in one JSON file with a top-level `schema_version`.
2. **Atomic saves**: write to a temp file in the same directory, flush,
   then `os.replace` onto the real file. Prove it: add a `--crash`
   flag that kills the process mid-save, and show the journal survives.
3. **Migration**: v1 entries lack `tags`; on load, migrate v1 → v2 (adding
   `"tags": []`), bump the version, and keep a `.bak` of the pre-migration
   file.
4. **Validation on load**: a corrupted file (truncate one by hand) is
   rejected with a clear message naming the problem — never a stack trace,
   never a silent empty journal.
5. **Flaky sync**: a provided-by-you stub `cloud_sync(entry)` raises a
   `TemporaryError` 60% of the time. Sync with exponential backoff plus
   jitter, a retry budget of 5, and idempotency — entries carry stable
   ids, and the stub, which you also write, must dedupe by id so that a
   retry after a "failure" that actually succeeded doesn't double-post.

**Rubric (100):** A: hashing/grouping 25, report + never-deletes rationale
10, stretch 5 · B: atomic + crash test 20, migration 10, validation-on-load
10, backoff/budget/idempotent sync 15 · README 5.

### Research paper — Anatomy of a Failure (1,800–2,500 words)

Pick one famous software failure and explain it through this phase's
vocabulary:

- **Therac-25** (1985–87) — radiation therapy machine; race conditions and
  the removal of hardware interlocks.
- **Knight Capital** (2012) — $440M in 45 minutes; deployment, dead code,
  and configuration reuse.
- **Northeast blackout** (2003) — a race condition in an alarm system, and
  55 million people in the dark.
- **Ariane 5, flight 501** (1996) — reused code, an unvalidated
  conversion, and an exploding rocket.

**Required:** narrate the failure accurately; explain it using **at least
three named concepts from this phase** (race condition, validation at trust
boundaries, fail-closed design, idempotency, schema/interface versioning,
...); identify the practice that would most plausibly have prevented it;
**at least 5 sources including one primary/official report** (Leveson &
Turner for Therac-25; the SEC order for Knight; the NERC/US-Canada task
force report for the blackout; the Lions inquiry report for Ariane).

**Rubric (100):** accurate narrative 30 · correct use of three concepts
35 · the prevention argument 20 · sources incl. primary 15.

### Midterm exam (45 minutes, closed docs — take after the Reliability cluster)

1. Membership test in a list versus a set: how does each scale as the
   collection grows, and what makes the set fast?
2. Name three properties of SHA-256 that make it fit for fingerprinting
   files.
3. Content-addressed naming: what does "the name is the hash of the
   content" buy? Two distinct benefits.
4. Define a race condition, and describe the one you left as a TODO in
   Movie Night (Phase 5) — what interleaving loses a vote?
5. Python has the GIL — one thread runs Python bytecode at a time. Why do
   race conditions happen anyway?
6. The atomic write pattern: list its steps, and state why the rename must
   stay on the same filesystem.
7. Idempotency: define it, and explain why retries are dangerous without
   it.
8. Backoff starting at 0.5 s and doubling: how long is the wait before the
   4th retry? What does jitter add, and what does a retry *budget* protect?
9. A bounded cache is full. What does LRU eviction discard, and on what
   assumption?

<details markdown="1">
<summary>Answer key</summary>

1. List: scan everything — cost grows with length (O(n)). Set: hash the
   item, jump to its bucket — roughly constant on average. The hash
   function is what buys the shortcut.
2. Any three: deterministic; fixed-size output; tiny input change flips
   the output completely (avalanche); infeasible to invert; collisions
   infeasible to construct.
3. Identical content gets identical names — deduplication is automatic;
   and the name verifies the content — corruption or tampering is
   detectable by rehashing. (Also: safe caching.)
4. Two operations interleave on shared state so the outcome depends on
   timing. Movie Night: two requests both read `votes.json` (n), both
   write n+1 — one vote evaporates. Read-modify-write without exclusion.
5. The GIL serializes bytecodes, not logical operations — threads can
   still interleave *between* the read and the write, and I/O releases the
   GIL constantly.
6. Write to a temp file in the same directory → flush (and fsync if you
   mean it) → `os.replace` over the target. Rename is atomic only within
   a filesystem; across devices it becomes copy-then-delete — a window.
7. Doing it twice equals doing it once. Without it, a retry after a
   timeout whose request actually succeeded performs the action twice
   (double vote, double charge).
8. Waits 0.5, 1, 2, 4 → **4 s** before the 4th retry. Jitter staggers
   many clients so they don't stampede in sync. The budget caps total
   attempts so a dead service fails fast instead of hanging forever.
9. The least-recently-used entry — assuming recent use predicts future
   use.

</details>

### Final exam (60 minutes, closed docs)

1. "Validation at trust boundaries": name three distinct trust boundaries
   in any application you've built this course, and what crosses each.
2. What is an error taxonomy for? Give the split you'd offer a user versus
   a developer.
3. Why must a file format carry a schema version from day one, and in
   which direction do migrations run?
4. Code review: a route builds `open(os.path.join(JOBS_DIR,
   request.args["name"]))`. Give the attack input, the harm, and two
   independent fixes.
5. What is a decompression bomb, and what does a defense look like?
6. Layered architecture: which direction may dependencies point, what is a
   leaf module, and why does the pipeline being a leaf make it testable?
7. Two-phase commit with review, as this project uses it: what are the two
   phases, what sits between them, and why is that the right design for AI
   extraction specifically?
8. Interpolation versus measurement (short essay, 5–8 sentences): why must
   a scientific system record which one produced each value, what goes
   wrong when the flag is lost, and how does this echo the synthetic-data
   rule from Phase 1?

<details markdown="1">
<summary>Answer key</summary>

1. Any three genuine boundaries: user form/CLI input · files read from
   disk · network/API responses · imported data files · environment
   variables. What crosses: untrusted bytes that must be validated before
   becoming trusted state.
2. Sorting failures so responses can differ: user-fixable input problems
   (clear message, no stack trace) vs. bugs (log loudly, fail) vs.
   environment/transient (retry or degrade). Users get actionable
   messages; developers get diagnostics.
3. Old files outlive the code that wrote them; the version field lets a
   newer reader recognize and migrate old data (old → new, on load, with a
   backup) instead of misparsing it silently.
4. `name=../../../../etc/passwd` (or any `..` path) escapes the jobs
   directory — read/overwrite of arbitrary files. Fixes (any two):
   resolve the joined path and require it to start with the jobs dir's
   resolved path; reject separators/`..` outright; use a generated id →
   path lookup instead of user-supplied names.
5. A tiny compressed input that expands enormously (a 10 KB PNG describing
   a 100-megapixel image), exhausting memory/disk. Defense: cap declared
   dimensions/decoded size *before* decoding, and fail closed.
6. Downward/inward only — UI depends on application logic, which depends
   on core modules; a leaf imports no application layer above it. The
   pipeline-as-leaf runs with plain inputs and outputs — no server, no
   browser — so tests call it directly.
7. Phase one: stage the extraction as a *proposal* artifact; between:
   a human compares it against the drawing; phase two: commit into the
   job's real data only on approval. Right for AI extraction because its
   failure mode is plausible fabrication — invented geometry that only a
   human comparing against the source can catch.
8. Criteria: measured values inherit evidence; interpolated values inherit
   assumptions · downstream users can't weigh a value without knowing
   which it is · once merged, false precision propagates and cannot be
   un-merged · the flag is provenance, exactly like the synthetic label:
   both keep "what we know" separate from "what we made up" · losing it
   turns a model into an artifact that *looks* like data. 4+ = pass.

</details>

---

## Phase 9 — Synthesis

*Subject: everything, at once, on purpose.*

### Pre-reading quiz — calibration inventory (15 minutes)

Rate your confidence 1–5 in each area, *then* take the five spot checks.

Areas: terminal & environments · the seven pipeline boxes · JSON, schemas,
validation · trench anatomy · chronology & the Harris matrix · survey math
(bearings, datums, scale) · system architecture · image processing ·
geometry & graphs · engineering practices.

Spot checks (closed book): recite the seven boxes → two sentences on locus
vs. layer → N45°E as azimuth → Canny's four stages in order → the atomic
write pattern.

<details markdown="1">
<summary>Answer key</summary>

Azimuth: 045. The rest you can now self-verify against Phases 1, 3, 4, 6,
and 8 above. The real result is the *calibration*: any area you rated 4+
whose spot check you missed goes on your review list before the capstone —
misplaced confidence, not ignorance, is what this quiz hunts.

</details>

### Programming assignment — capstone: A Digitizer for Something Else Entirely (15–20 hours)

Build a miniature end-to-end digitizer for a paper record type with **no
connection to archaeology**. Pick one: knitting charts · baseball
scorecards · a garden bed plan · a vintage weather logbook page · sheet
music (simplified) · board-game score sheets.

Your pipeline must include, each requirement naming the phase that taught
it:

1. **Image preparation** of a photo/scan of the record, using your Phase 6
   filter suite (grayscale, contrast, threshold — whatever the source
   needs).
2. **Guided manual capture** (Phase 2): a CLI or simple form that walks a
   person through transcribing the record into structured JSON — you are
   the tracing stage.
3. **A documented schema** with `schema_version` (Phases 2, 8).
4. **Normalization** rules, written down (Phase 2).
5. **Validation**: ≥ 5 rules with located messages *and* a severity split —
   errors versus warnings (Phases 2, 8).
6. **One real unit/frame conversion** (Phases 4, 7): knitting gauge
   (stitches → centimeters), scorecard innings → a game timeline, garden
   grid → planting coordinates in meters.
7. **Provenance** (Phase 8): every derived file records its source file,
   its tool/step name, and the source's SHA-256.
8. **Atomic writes** for all outputs (Phase 8).
9. **A report or visualization** a person from the domain would recognize
   (text rendering fine; Phase 6 skills welcome).
10. **A README** with a quickstart in the workflow-page shape *and* an
    honest capability table — supported / experimental / not-implemented —
    for your own tool (Phases 0, 1).

**Rubric (100):** pipeline completeness end to end 30 · schema +
validation quality 20 · provenance + atomicity + honest capability table
20 · conversion correctness 10 · report/visualization 10 · README 10.

This is the proof of digestion the whole pack aims at: the project's
architecture, rebuilt from understanding, pointed at a different world.

### Research paper — Digitization in the Wild (2,000–3,000 words)

Pick a real, large digitization effort: **Old Weather** (citizen
transcription of ship logbooks for climate science) · **Google Books /
Ngrams** (OCR at library scale) · a museum collection you can research ·
**FamilySearch/genealogy indexing**. Evaluate it against six principles you
now own, with evidence for each: provenance (can a datum be traced to its
page?) · human-in-the-loop (who reviews, how sampled?) · validation (what's
checked, what slips through?) · honesty about capability (what does the
project claim vs. deliver?) · interpolation vs. measurement (are gaps
filled, and are fills flagged?) · synthetic/real separation (test data ever
near real data?).

Close with a verdict: what should this effort adopt from the principles,
and — seriously considered — what should the principles learn from the
effort's scale? **At least 6 sources.**

**Rubric (100):** the effort described accurately 25 · all six principles
applied with evidence 45 · the two-way verdict 20 · sources 10.

### Midterm exam — the integration matrix (60 minutes, closed docs)

**Part A.** Draw a table: seven rows (the pipeline boxes), four columns —
workflow page · concept page · one CS technique · one archaeology term.
Fill all 28 cells from memory. Any defensible entry counts; a cell you can
argue is a cell you own.

**Part B — confusable pairs, rapid fire.** One distinguishing sentence
each: marker/feature · feature/find · locus/layer · apparent/true dip ·
normalize/validate · wall/baulk · cut/fill · measured/interpolated.

**Part C — navigation, rapid fire.** Name the section (page if you can)
for: a schema field's type · whether model building is dependable · what
erosion does · what a baulk is · why the app stages AI output for review ·
the exact validation message wording.

<details markdown="1">
<summary>Answer key</summary>

A. Sample defensible row set (yours may differ): Prepare — workflow 02 /
source drawing types / CLAHE / scale and DPI · Trace — workflow 03 / layers
and boundaries / contour tracing / boundary · Normalize — workflow 04 /
geometric normalization / similarity transforms / orientation seed ·
Validate — workflow 05 / accuracy and provenance / polygon
self-intersection / stratigraphic relationships · Convert — workflow 06 /
coordinate spaces / affine transforms / datum · Build — workflow 07 / from
archaeology to 3D / spatial interpolation & kriging / true dip · View —
workflow 08 / jobs, sheets, and trenches / JSON & schema design /
provenance links. Pass: ≥ 24 defensible cells.
B. Pass: 7 of 8 crisp. (Every pair appears in Phases 2–8 keys above;
measured/interpolated is Phase 8's essay.)
C. Reference (data schemas) · Project (capability status) · CS
(morphology/erosion) · Archaeology (wall-and-baulk) · CS (two-phase commit
with review) or Concepts (accuracy and provenance) · Reference (validation
rules). Pass: 5 of 6.

</details>

### Final exam — the course final (three parts; ~3 hours total, sittings may be split)

**Part A — comprehensive written (90 minutes, closed docs, calculator
allowed).** Twenty-five questions; pass ≥ 20.

1. The seven pipeline boxes, in order.
2. The four input routes and each one's capability status.
3. A doc page and its source file disagree — which wins, and which
   front-matter field points where?
4. The synthetic-data rule, in one sentence.
5. Define locus so it doesn't just mean "layer."
6. Why leave a baulk standing?
7. Relations: topsoil above pit-fill; the pit cuts floor; floor above
   bedding. Order all four, oldest first.
8. S30°E as azimuth?
9. Datum 204.10 m; a surface lies 2.45 m below. Elevation?
10. A 1:20 drawing scanned at 300 DPI: how many pixels represent one real
    meter?
11. `7.5YR 6/4` — name the parts.
12. Which architectural component decides a trace is invalid, and which
    component told the browser about it?
13. Why does the slow model build run as a background task?
14. Convolve: neighborhood `[[0,0,0],[0,9,0],[0,0,0]]`, box kernel ÷9.
    Result, and the general lesson about lone bright pixels?
15. Otsu, one sentence.
16. Specks versus gaps: which morphological operation for each?
17. Canny's stages, in order.
18. Boxes (0,0)–(2,2) and (1,1)–(3,3): IoU?
19. Normalize (5,12).
20. Shoelace: area of (0,0), (6,0), (6,2), (0,2)?
21. Edges A→B, B→C, A→C: valid topological order(s), and which edge does
    transitive reduction remove?
22. Two files, one SHA-256 digest: conclude what, with what confidence?
23. The atomic write pattern, three steps.
24. Why must retried operations be idempotent — one concrete disaster if
    not?
25. Two-phase commit with review: why is the human between the phases not
    optional for AI-extracted geometry?

**Part B — essays (45 minutes, closed docs; both).**

1. *What this application refuses to do, and why that is its best
   feature.* Cover: interpretation, placeholder coordinates, fabrication
   risk, provenance, and the capability-status habit. (10–15 sentences.)
2. *Trace a raindrop.* One pixel of a scanned drawing, from upload to a
   coordinate inside a 3D model: name every transformation it undergoes,
   every stage that could reject it, and every artifact it appears in
   along the way. (10–15 sentences.)

**Part C — practical (45 minutes, docs closed until you're stuck).**
A fresh synthetic fixture, the full pipeline, alone. Checklist: job
created · image prepared · ≥ 2 layers + 1 feature captured · cleanup run ·
validation clean · placed with (synthetic) coordinates · model built or
its absence correctly explained via capability status · outputs located on
disk and their provenance stated.

<details markdown="1">
<summary>Answer key — Part A</summary>

1. Prepare → trace/import/extract → normalize → validate → convert →
   build → view. 2. Manual/supported · import/supported · AI/experimental ·
   marker workflow/backend-only. 3. The code; `source_files` (with
   `verified_against`). 4. Labeled-synthetic data is invented, safe for
   practice, never evidence. 5. The excavator's defined recording unit —
   which may be a deposit, a cut, or another unit of observation, not only
   a stratum. 6. To preserve standing sections (readable stratigraphy) and
   access/control while digging. 7. Bedding → floor → pit (cut) →
   pit-fill → topsoil — oldest first: bedding, floor, pit, fill, topsoil.
   8. 150. 9. 201.65 m. 10. 1 m real = 5 cm paper = 5/2.54 in × 300 ≈
   **591 px**. 11. Hue 7.5YR, value 6, chroma 4. 12. The pipeline decides;
   the backend (routes/status) told the browser. 13. So the request
   returns immediately and the browser polls status instead of hanging.
   14. 9/9 = **1** — isolated pixels are annihilated by averaging; blur is
   noise suppression. 15. Picks the threshold maximizing between-class
   variance of the histogram. 16. Specks: opening. Gaps: closing.
   17. Smooth (Gaussian) → gradient (Sobel) → non-max suppression →
   hysteresis. 18. Intersection 1; union 4+4−1=7; **1/7**. 19. (5/13,
   12/13). 20. **12**. 21. Only A,B,C; remove A→C. 22. Same content —
   for practical purposes certain (engineered collisions infeasible,
   accidental ones astronomically unlikely). 23. Temp file, same
   directory → write + flush → atomic rename over target. 24. A retry
   after a success-that-looked-like-failure repeats the action — the
   double-charged card, the double-posted entry. 25. Because extraction
   can fabricate plausible geometry; only comparison against the source
   drawing catches it, so commit must wait on that comparison.

**Part B criteria.** Essay 1: names ≥ 4 refusals and argues *why* each
protects the science (scope humility = trustworthiness). Essay 2: touches
≥ 8 distinct stations (upload artifact → EXIF/orientation → enhancement →
trace/extract coordinate → normalization transform → validation gates →
similarity/affine to site frame → interpolation into the model → exported
artifact with provenance) without inventing capabilities the docs don't
claim.

**Part C.** Pass = every checklist item, unaided. Any item that required
opening the docs: note it, review that page, redo just that item another
day.

</details>

---

## After the final

Passing Part A at 20/25 with both essays meeting criteria and a clean
Part C run means the plan's goal — *learn, understand, and digest all of
the information in the documentation* — is met, with receipts: ten
programs, ten papers, and a capstone that rebuilt the project's ideas in a
world of your choosing.

Where you fell short, the pattern repeats at every scale: find the page,
reread it, wait a day, retest. The docs have no dead ends, and now neither
does your understanding of them.

<!-- Local-only enhancement: a "Copy for feedback" button on every quiz and
     exam. It copies the section's questions, its answer key, and a grading
     brief, ready to paste into Claude (or any assistant) for marking. The
     script lives inside this draft page, so it is served locally and never
     reaches the published site. Inside Claude Code, the grade-assessment
     skill is the better loop: it reads this file itself. -->
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
    return "the learning course";
  }
  function buildPrompt(heading) {
    var section = collect(heading);
    return [
      "I am self-studying the Poggio Civitate trench-digitization documentation with its learning course, and I want you to grade one assessment.",
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



