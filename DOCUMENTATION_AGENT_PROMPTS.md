# Copy/Paste Prompts for Documentation Chunks

Each section below contains one complete prompt to paste into a new chat.
The agent is expected to have access to this repository. Do not paste more than
one chunk into the same chat.

The detailed contracts remain in
[`DOCUMENTATION_AGENT_WORKPLAN.md`](DOCUMENTATION_AGENT_WORKPLAN.md). Every
prompt explicitly requires the agent to read the global contract and its
assigned chunk before acting.

After a chunk finishes:

1. Review its changed files and test results.
2. Resolve or record any blockers.
3. Merge or otherwise accept the chunk.
4. Complete the required human review gate, when applicable.
5. Only then open a new chat with the next prompt.

## Chunk 0 — Establish the baseline

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 0 — Establish the baseline, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 0 — Establish the baseline” section.
4. Follow both sections exactly.

Scope rules:
- Do not implement any other chunk.
- Chunk 0 allows no file edits.
- Do not install packages, fix tests, stage, commit, push, or deploy.
- If anything is ambiguous, stop and report it instead of guessing.

Run every preflight and baseline command required by Chunk 0. Return the exact
“Required final report” from the global contract, including PASS, FAIL, and
NOT RUN results. Then stop. Do not continue to Chunk 1.
```

## Chunk 1 — Create the documentation site scaffold

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 1 — Create the documentation site scaffold,
from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 1 — Create the documentation site scaffold”
   section.
4. Verify that Chunk 0 was completed and record the current preflight state.

Scope rules:
- Do not implement any other chunk.
- Edit only the files in Chunk 1’s “Files you may edit” allow-list.
- Treat every other file as read-only.
- Preserve all pre-existing user changes.
- Do not migrate old docs, rewrite README.md, add screenshots, or change the
  application.
- Do not stage, commit, push, deploy, or change repository settings.
- If a needed file is outside the allow-list, stop and report the blocker.

Complete every Chunk 1 deliverable and run every validation command available
at this point. Return the exact “Required final report” from the global
contract. Then stop. Do not continue to Chunk 2.
```

## Chunk 2 — Add documentation validation tooling and unit tests

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 2 — Add documentation validation tooling and
unit tests, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 2 — Add documentation validation tooling and unit
   tests” section.
4. Verify that Chunks 0–1 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the exact Chunk 2 allow-list.
- Do not edit documentation pages merely to hide checker failures.
- Do not modify, weaken, or delete existing application tests.
- Write every specifically listed unit test; “representative coverage” is not
  sufficient.
- Use no network requests and do not build a general Markdown parser.
- Do not stage, commit, push, deploy, or change repository settings.
- Stop rather than expanding scope.

Implement the exact public Python interfaces and CLI behavior in Chunk 2.
Run the new unit tests, the complete Python test suite, the checker, and the
strict docs build. Return the required final report. Then stop. Do not
continue to Chunk 3.
```

## Chunk 3 — Create the current capability audit

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 3 — Create the current capability audit, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 3 — Create the current capability audit” section.
4. Verify Chunks 0–2 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 3 allow-list.
- Application code and existing docs are evidence only; do not edit them.
- Use code, passing tests, and reachable UI as the sources of truth.
- Never label a backend-only route as a supported UI feature.
- Do not fix bugs or stale README statements in this chunk.
- Do not stage, commit, push, deploy, or change repository settings.
- If a status cannot be proven, stop and report the evidence gap.

Complete the full capability table and source map specified by Chunk 3. Run
all available validation commands and return the required final report. Flag
that Human Review Gate A’s status review is required before Chunk 4. Then
stop.
```

## Chunk 4 — Migrate and repair the existing public documentation

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 4 — Migrate and repair the existing public
documentation, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 4 — Migrate and repair the existing public
   documentation” section.
4. Confirm Chunks 0–3 are complete and the Chunk 3 status audit was approved.
5. Run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the exact Chunk 4 allow-list.
- Do not edit or publish 00_docs/CLAUDE.md.
- Preserve useful existing content and file history where practical.
- Update only status claims already resolved by the approved capability audit.
- Do not add new visuals or change pipeline/application code.
- Do not stage, commit, push, deploy, or change repository settings.
- Stop if a move would overwrite an existing user file.

Complete all migrations, compatibility stubs, front matter, and repaired
links required by Chunk 4. Run the full available validation suite and return
the required final report. State that Human Review Gate A must approve the
migration before Chunk 5. Then stop.
```

## Chunk 5 — Create sanitized, deterministic documentation fixtures

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 5 — Create sanitized, deterministic
documentation fixtures, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 5 — Create sanitized, deterministic documentation
   fixtures” section.
4. Confirm Chunks 0–4 and Review Gate A are complete.
5. Run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 5 allow-list.
- Do not copy, crop, or modify real archaeological scans.
- Use invented labels and non-site coordinates only.
- Do not weaken schemas or validators to make fixtures pass.
- Write every listed fixture and determinism unit test.
- Do not generate GemPy outputs or screenshots.
- Do not stage, commit, push, deploy, or change repository settings.

Implement the exact Python interfaces, deterministic assets, schema-valid
fixtures, README, and tests required by Chunk 5. Run the generator twice and
prove byte-identical output. Run the complete validation suite and return the
required final report. Then stop. Do not continue to Chunk 6.
```

## Chunk 6 — Write the beginner entry path

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 6 — Write the beginner entry path, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 6 — Write the beginner entry path” section.
4. Confirm Chunks 0–5 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 6 allow-list.
- Write for a reader with little codebase experience.
- Do not write detailed stage tutorials, route reference, or architecture.
- Do not require an API key for the primary beginner path.
- Do not promise unsupported platforms or install optional GemPy by default.
- Treat current capability status as authoritative.
- Do not stage, commit, push, deploy, or change repository settings.

Complete the homepage, reader-path chooser, quickstart, project explanation,
and full required glossary. Follow the standard page contract. Run all
available validation commands and return the required final report. Then
stop. Do not continue to Chunk 7.
```

## Chunk 7 — Document upload, preprocessing, and manual tracing

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 7 — Document upload, preprocessing, and manual
tracing, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 7 — Document upload, preprocessing, and manual
   tracing” section.
4. Confirm Chunks 0–6 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 7 allow-list.
- Do not capture screenshots; use the exact non-breaking screenshot-comment
  format from the chunk.
- Do not document AI, marker, registration, or GemPy details here.
- Do not change application copy or behavior.
- Use the synthetic fixtures for examples.
- Follow the exact workflow-page section order.
- Do not stage, commit, push, deploy, or change repository settings.

Write the workflow overview and the three primary-path pages with exact
inputs, actions, artifacts, success checks, common problems, and source links.
Run all available validation commands and return the required final report.
Then stop. Do not continue to Chunk 8.
```

## Chunk 8 — Document alternative extraction, cleanup, and validation

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 8 — Document alternative extraction, cleanup,
and validation, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 8 — Document alternative extraction, cleanup, and
   validation” section.
4. Confirm Chunks 0–7 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 8 allow-list.
- Keep optional paths visibly secondary to manual tracing.
- Distinguish supported UI, experimental UI, backend-only, and blocked paths.
- Never present AI-derived geometry as verified.
- Use no real API keys or real job data.
- Do not change validation rules, thresholds, application code, or tests.
- Do not stage, commit, push, deploy, or change repository settings.

Write all four required workflow pages. For every warning, state its trigger,
blocking behavior, and user inspection step. Use sanitized JSON examples.
Run all available validation commands and return the required final report.
Then stop. Do not continue to Chunk 9.
```

## Chunk 9 — Document registration, model creation, visualization, and finds

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 9 — Document registration, model creation,
visualization, and finds, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 9 — Document registration, model creation,
   visualization, and finds” section.
4. Confirm Chunks 0–8 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 9 allow-list.
- Never invent surveyed registration values.
- Never represent a smoke-test model as a scientific result.
- Do not generate or commit a real scientific model.
- Do not interpret archaeology or add batch features.
- Use the repository’s exact coordinate formulas and bearing convention.
- Do not stage, commit, push, deploy, or change repository settings.

Complete the four workflow pages and the linked first-model tutorial using the
synthetic example. Identify every output artifact and make placeholder-data
warnings prominent. Run all available validation commands and return the
required final report. State that Human Review Gate B is required before
Chunk 10. Then stop.
```

## Chunk 10 — Write the conceptual learning layer

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 10 — Write the conceptual learning layer, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 10 — Write the conceptual learning layer” section.
4. Confirm Chunks 0–9 and Review Gate B are complete.
5. Run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 10 allow-list.
- Explain concepts without requiring source-code knowledge.
- Do not repeat full UI instructions or write API reference.
- Do not add speculative archaeological interpretation.
- Separate manual, imported, CV, AI, placeholder, and surveyed provenance.
- Do not stage, commit, push, deploy, or change repository settings.

Write all five concept pages using the exact concept-page contract. Link each
concept to the workflow where it is used and keep accuracy claims cautious.
Run all available validation commands and return the required final report.
Then stop. Do not continue to Chunk 11.
```

## Chunk 11 — Document system architecture

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 11 — Document system architecture, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 11 — Document system architecture” section.
4. Confirm Chunks 0–10 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 11 allow-list.
- Application source and tests are read-only.
- Describe current architecture, including awkward or legacy paths, neutrally.
- Do not refactor duplicate routes, task persistence, or job storage.
- Do not copy entire source files into documentation.
- Keep user-facing availability separate from backend capability.
- Do not stage, commit, push, deploy, or change repository settings.

Write every required architecture page with responsibilities, inputs, outputs,
source files, failure boundaries, tests, and workflow links. Run all available
validation commands and return the required final report. Then stop. Do not
continue to Chunk 12.
```

## Chunk 12 — Write the developer reference

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 12 — Write the developer reference, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 12 — Write the developer reference” section.
4. Confirm Chunks 0–11 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 12 allow-list.
- Verify every signature, default, route, and validation level against source.
- Do not generate reference pages through runtime introspection.
- Do not change dependencies, add a license, fix bugs, or modify code.
- Keep current limitations separate from roadmap ideas.
- Do not add dates or owners to roadmap items.
- Do not stage, commit, push, deploy, or change repository settings.

Write all specified reference, contributor, limitation, roadmap, and
scientific-assumption pages. Run all available validation commands and return
the required final report. Then stop. Do not continue to Chunk 13.
```

## Chunk 13 — Add deterministic diagrams and the visual inventory

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 13 — Add deterministic diagrams and the visual
inventory, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 13 — Add deterministic diagrams and the visual
   inventory” section.
4. Confirm Chunks 0–12 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 13 allow-list.
- Do not capture live screenshots.
- Do not use image generation for precise technical diagrams.
- Do not use unapproved real scans or decorative visuals.
- Do not change application styling.
- Every visual must have a teaching purpose, source, alt text, and caption.
- Do not stage, commit, push, deploy, or change repository settings.

Create the full visual manifest, the five deterministic SVGs, and the three
Mermaid diagrams. Embed only completed diagrams in relevant pages. Validate
accessibility and implementation accuracy, run all available validation
commands, and return the required final report. Then stop. Do not continue to
Chunk 14.
```

## Chunk 14 — Add screenshot capture tooling and approved screenshots

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 14 — Add screenshot capture tooling and
approved screenshots, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 14 — Add screenshot capture tooling and approved
   screenshots” section.
4. Confirm Chunks 0–13 are complete.
5. Confirm a human explicitly approved that the UI redesign is stable and the
   listed assets are safe to publish.
6. Run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 14 allow-list.
- Use only synthetic fixtures and manifest-approved UI states.
- Do not display API keys, real survey values, real user jobs, or unstable ids.
- Do not edit application code to add selectors or change appearance.
- Do not keep stale screenshots when capture fails.
- Write every listed visual-manifest unit test.
- Do not stage, commit, push, deploy, or change repository settings.
- Stop if UI stability or publication approval is missing.

Implement the exact Python manifest interfaces, deterministic capture command,
approved screenshots, and placeholder replacements specified in Chunk 14.
Run all new and existing validation commands. Return the required final
report and state that Human Review Gate C is required before Chunk 15. Then
stop.
```

## Chunk 15 — Add small interactive documentation components

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 15 — Add small interactive documentation
components, from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 15 — Add small interactive documentation
   components” section.
4. Confirm Chunks 0–14 and Review Gate C are complete.
5. Run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 15 allow-list.
- Implement only the coordinate calculator and before/after comparison.
- Use plain JavaScript with no framework, bundler, analytics, or live app
  embedding.
- Keep pure logic separate from DOM initialization.
- Preserve useful content when JavaScript is disabled.
- Write every listed Node unit test.
- Do not stage, commit, push, deploy, or change repository settings.

Implement the exact JavaScript interfaces and error contract specified in
Chunk 15. Run Node tests plus the full Python/docs validation suite. Return
the required final report. Then stop. Do not continue to Chunk 16.
```

## Chunk 16 — Rewrite the root README as the front door

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 16 — Rewrite the root README as the front door,
from DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 16 — Rewrite the root README as the front door”
   section.
4. Confirm Chunks 0–15 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only README.md.
- Preserve deep historical/technical value by linking to its new location.
- Do not turn README.md back into a full manual.
- Do not edit poggio_webapp/README.md.
- Do not add badges for workflows that do not exist.
- Check every status-sensitive claim against the capability audit.
- Do not stage, commit, push, deploy, or change repository settings.

Write the README in the exact required order from Chunk 16. Ensure all links
work as GitHub-relative links and the launch command is visible immediately.
Run all available validation commands and return the required final report.
Then stop. Do not continue to Chunk 17.
```

## Chunk 17 — Add CI and prepare deployment

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 17 — Add CI and prepare deployment, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 17 — Add CI and prepare deployment” section.
4. Confirm Chunks 0–16 are complete and run the required preflight.

Scope rules:
- Do not implement any other chunk.
- Edit only the Chunk 17 allow-list.
- Pull requests must never deploy.
- Do not change GitHub settings, publish Pages, add secrets, or rewrite
  application CI.
- Pin test dependencies in the allowed requirements file.
- Make CI commands match commands already proven locally.
- Do not stage, commit, push, or deploy.
- Stop if deployment safety cannot be guaranteed.

Create the CI workflow, PR checklist, test requirements, and documentation
updates required by Chunk 17. Run every workflow command locally where
possible and report any command that cannot be run as NOT RUN. Return the
required final report. Then stop. Do not continue to Chunk 18.
```

## Chunk 18 — Final audit and novice test packet

Copy everything inside this block:

```text
You are working in the PoggioCivitate repository.

Your only assignment is Chunk 18 — Final audit and novice test packet, from
DOCUMENTATION_AGENT_WORKPLAN.md.

Before taking any action:
1. Open DOCUMENTATION_AGENT_WORKPLAN.md.
2. Read the entire “Global task contract.”
3. Read the entire “Chunk 18 — Final audit and novice test packet” section.
4. Confirm Chunks 0–17 are complete and run the required preflight.

Scope rules:
- Do not implement any other work.
- Edit only the Chunk 18 allow-list.
- Do not change application features or documentation for stylistic preference.
- Do not claim novice testing occurred unless real participants completed it.
- Do not publish or deploy.
- Update status/limitations only when the audit proves an error.
- Report failures honestly; do not remove pages, checks, or assets to make the
  audit pass.
- Do not stage, commit, push, deploy, or change repository settings.

Complete the final audit, novice test script, and results template. Run every
exact final command listed in Chunk 18. Return the required final report and
state that Human Review Gate D is required. Then stop. The project is not
complete until that human review is approved.
```

