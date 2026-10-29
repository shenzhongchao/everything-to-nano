# Verification Checklist

Apply this checklist after structural verification and before handoff.

## Execution

- Every unit runs from the command written in its `README.md`.
- The root quick-start commands run from the documented working directory.
- Stubbed services or fixtures produce deterministic output.

## Architecture Integrity

- Unit 1 imports and orchestrates Units 2+ through real public APIs.
- Unit 1 does not fake subsystem flow with narration-only logging.
- Unit boundaries match the promised concepts in the learning-path table.

## Documentation Integrity

- The root `README.md` explains what the original project is before describing the speedrun scope.
- Each unit `README.md` explains the extracted code, not the original codebase at full complexity.
- Every unit includes Key Terminology, runnable commands, expected output, exercises, and a Debug Guide.
- Cross-references between related units are accurate.

## Code Learnability

- Each unit's source includes clear inline teaching comments at the important non-obvious boundaries, state changes, or design decisions.
- Inline comments explain the extracted code in plain language first, then technical precision.
- If a unit omits inline teaching comments because the code is truly straightforward, the unit `README.md` says so explicitly instead of leaving the absence unexplained.

## Visual Explanations (Answer me with HTML)

- `learning/overview.md` and `learning/overview.html` exist for the project-level learning map.
- Every Unit has a corresponding `learning/unit-N-<slug>.md/.html` pair.
- Each Unit has evidence from actual offline execution: argv, return code, observed outputs, source SHA-256 and prediction/change/rerun exercise.
- `scripts/unit_evidence.py check` validates every source fingerprint after extraction.
- `scripts/render_learning_pages.py --check --require-evidence` succeeds and shows no stale evidence, source code, drafts or missing artifacts.
- Root README and every unit README link to their actual rendered HTML page.
- Every explanation uses real generated code and validated runtime observations; source excerpts have valid paths and line numbers.
- Each unit explanation includes a prediction/change/re-run exercise and explicit simplification boundaries.
- If `am` is unavailable, report HTML as blocked, **not passed**. Run-only completion must be distinguished from full Speedrun delivery.

## Debugging

- `.vscode/launch.json` or the runtime-equivalent debug config points at real unit entry points.
- The debug instructions mention concrete files, commands, or breakpoints the learner can use.

## Simplifications

- `SIMPLIFICATIONS.md` covers every important stub, omitted dependency, removed layer, or simplified branch.
- Each simplification points back to the real implementation path in the original repo.

## Scope

- The chosen unit count is justified if it falls outside the default 4-8 range.
- Monorepo or partial-repo scope is stated explicitly in the root README.
