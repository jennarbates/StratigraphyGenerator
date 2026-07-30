---
title: How to read these docs
audience: beginner
status: current
source_files:
  - mkdocs.yml
  - docs/_meta/page-template.md
  - tools/docs/check_docs.py
verified_against: d23b842
---

# How to read these docs

There are five sections and four sensible ways through them. You do not need to
read everything, and reading in nav order is rarely the fastest route.

## Four paths

### 1. I want to understand what this is

[What this project does](what-this-project-does.md) →
[from archaeology to 3D](../concepts/archaeology-to-3d.md) →
[glossary](glossary.md)

About fifteen minutes. No installation. Start here if the words *trench*,
*locus*, and *stratigraphy* are new, or if you know the archaeology but not
what the software claims to do.

### 2. I want to use it

[Quickstart](quickstart.md) → [first model tutorial](first-model.md) →
[workflow overview](../workflows/overview.md) → the numbered workflows

The numbered workflows are the pipeline in order, 01 through 09. Each one is a
single step, and each links to the next, so you can follow them straight
through without returning here.

[Choose your path](choose-your-path.md) is worth reading before you start: it
tells you which route suits your drawing, and which steps need an API key.

### 3. I want to understand why it works this way

The **Concepts** section. These pages are not sequential — read the one you
need.

Every workflow page has an **Under the hood** section linking to the concept
behind it. That is usually the better way in: hit the step, then follow the
link, rather than reading concepts cold.

### 4. I want to change the code

**Architecture** for how the system fits together, then **Reference** for exact
schemas, routes, and file formats.

Start with [capability status](../project/capability-status.md) regardless of
what you plan to change. It records what is actually wired up versus what
merely exists, and it will save you from implementing something that is already
there but unreachable.

## What each section is for

| Section | Answers | Read it |
|---|---|---|
| Start here | What is this, and how do I run it? | First, once |
| Workflows | How do I do this step? | In order, while working |
| Concepts | Why does it work this way? | On demand |
| Architecture | How is the system built? | Before changing code |
| Reference | What exactly is the format? | As a lookup |
| Project | What is the state of this? | Before trusting anything |

## Reading a page

Every page follows one of two shapes, defined in `docs/_meta/page-template.md`.

**Workflow pages** run: Before you start → Do this → What the application
creates → Check your result → Common problems → Under the hood → Next.

**Concept pages** run: definition → Why it matters here → Example → How the
repository represents it → Related concepts.

Two conventions worth knowing:

- **Every page ends with a `Next` or `Related` section.** There are no dead
  ends; if you have finished a page, the links at the bottom are the intended
  continuations.
- **Every page's front matter names the source files it describes** and the
  commit it was verified against. If a page and the code disagree, the source
  file wins — and the front matter tells you exactly where to look.

## Two warnings

**Synthetic data is labelled.** Examples marked *synthetic documentation
example* are invented, including all coordinates and Munsell readings. They are
safe to copy while learning and must never be treated as archaeological
evidence. See [synthetic fixtures](../fixtures/README.md).

**A page can be current and still describe something you cannot click.** Some
capabilities are implemented behind routes but absent from the browser
interface. Those pages say so at the top.
[Capability status](../project/capability-status.md) is the authoritative list.

## Next

- [What this project does](what-this-project-does.md) if you are new.
- [Quickstart](quickstart.md) if you want it running now.
- [Capability status](../project/capability-status.md) if you are evaluating
  whether it does what you need.
