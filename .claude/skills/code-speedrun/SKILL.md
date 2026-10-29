---
name: code-speedrun
description: >
  Speedrun any codebase by decomposing it into minimal, independently runnable units — run first,
  read later. Accepts GitHub URLs and local directories. Use when the user wants to: (1) quickly
  understand a codebase by running it instead of only reading it, (2) break down a complex project
  into small pieces they can execute and debug, (3) learn a codebase well enough to build a demo
  or reimplementation, (4) flatten the learning curve of a large or unfamiliar repository. Triggers
  on requests like "speedrun this codebase", "learn this repo", "teach me this codebase",
  "break down this project", "run to learn", or a repository URL.
---

# Code Speedrun

Decompose a codebase into self-contained, runnable learning units. The learner should be able to run each unit, inspect it with a debugger, and finish with enough understanding to rebuild a small working version.

Write all explanations, walkthroughs, and `// LEARN:` comments in Feynman style: plain language first, then technical precision. See [references/feynman-method.md](references/feynman-method.md).

Load bundled resources only when needed:

- Use [references/runtime-selection.md](references/runtime-selection.md) after identifying the runtime and toolchain.
- Use [references/unit-readme-template.md](references/unit-readme-template.md) when writing per-unit `README.md` files.
- Use [references/root-files-template.md](references/root-files-template.md) when writing the top-level `README.md` and `SIMPLIFICATIONS.md`.
- Use [references/debug-guide.md](references/debug-guide.md) when writing each unit's Debug Guide and the root `.vscode/launch.json`.
- Use [references/verification-checklist.md](references/verification-checklist.md) before handoff.
- **Always use** [references/visual-explanations.md](references/visual-explanations.md) when creating a new Speedrun: it defines the required Answer me with HTML explanation deliverables and content contract.
- Use `scripts/render_learning_pages.py` to render and validate the HTML learning pages after the runnable units have been verified.
- Use `scripts/scaffold_speedrun.py` to generate the directory skeleton when that saves time.
- Use `scripts/verify_speedrun.py` for structural verification before final manual checks.

## Workflow

### Phase 0: Source Acquisition

If the user provides a remote git URL:

1. Resolve the local target directory before cloning. Default target: `./<repo-name>`.
2. If the target directory already exists, do not overwrite it. Reuse it if it is the intended checkout, or pick a different sibling path.
3. Clone shallow by default:
   ```bash
   git clone --depth 1 <url> /path/to/<repo-name>
   ```
4. If clone requires network approval, credentials, submodules, or large-file support, surface that constraint and choose the narrowest workable fallback.
5. If the repo is very large or is a monorepo, scope the speedrun to the relevant subdirectory when possible instead of covering everything.
6. Record the source URL and clone date for the generated root `README.md`.

If the user provides a local directory, skip cloning and analyze that directory directly.

If acquisition fails:

- Prefer a local path the user already has.
- Prefer a scoped subdirectory over a full-repo walkthrough when the repository is too large.
- Do not keep retrying brittle clone/install flows when a local copy or narrower scope will unblock the task.

Create `speedrun-<repo-name>/` as a sibling of the source project, never inside it.

```text
parent-dir/
├── <repo-name>/                # Original project
└── speedrun-<repo-name>/       # Generated learning units
```

### Phase 0.5: Visual Explainer Preflight

Visual learning pages are a **default part of every new Speedrun artifact**,
not a separate optional command or an extra feature of one sample unit.

1. Read `references/visual-explanations.md`.
2. Check for the installed Answer me with HTML CLI (`am`, or the upstream
   `skills/answer-me-with-html/scripts/am.mjs` with Node.js 20+).
3. Do not auto-install, download, or update an external skill without permission.
   If unavailable, continue creating runnable units and visual Markdown drafts,
   but mark HTML rendering as **incomplete** and give the exact install/rerun action.
4. Do not make `am` or Node.js a runtime dependency of the resulting learning units.

### Phase 1: Codebase Analysis

1. Identify the runtime, framework, package manager, test runner, and debugger entry points.
2. Open [references/runtime-selection.md](references/runtime-selection.md) and pick only the section that matches the runtime.
3. Map entry points, core modules, data flow, and key dependencies.
4. Trace the main execution path first, then the most important secondary flows.
5. Mark external boundaries that will need mocks or stubs in learning units.
6. If this is a monorepo, explicitly choose the package or service being speedrun before decomposing units.

### Phase 2: Decomposition into Learning Units

Default to 4-8 units. Go below or above that range only when the codebase size or architecture justifies it, and state the reason in one sentence.

Rules:

- **Overall-first**: Unit 1 is the end-to-end main flow.
- **Real module boundaries**: Unit 1 imports and calls public APIs exported by Units 2+.
- **No fake orchestration**: Do not replace subsystem interactions with `print` or `console.log` narration.
- **Single concept**: Each Unit 2+ teaches one architectural idea.
- **Runnable**: Every unit has its own executable entry point.
- **Infra is woven in**: Config, types, logging, small helpers, and glue code belong inside the units that use them.
- **Exclude low-value areas by default**: Generated code, vendor directories, CI files, benchmarks, and tests do not become standalone units unless they are core to understanding the system.
- **Cross-reference**: READMEs and `// LEARN:` comments should point to related units.

Produce a unit list in this format:

```text
Unit 1: Overall — [Project Name]
  Motto:        [Short memorable phrase]
  Concept:      End-to-end main flow — imports and orchestrates Units 2+
  Teaches:      [What the learner will understand]
  Source files: [Key original files]
  Imports from: Unit 2 (router), Unit 3 (db), Unit 4 (auth)
  Runs as:      [Exact command]
  Prereqs:      None

Unit 2: [Title]
  Motto:        [Short memorable phrase]
  Concept:      [One-line core idea]
  Teaches:      [What the learner will understand]
  Source files: [Key original files]
  Exports:      [Public API imported by Unit 1]
  Runs as:      [Exact command]
  Prereqs:      [Units or None]
```

### Phase 2.5: Coverage Review

Before building units, cross-check the unit list against the source tree:

1. Re-scan top-level directories and key files. Mark each as covered, intentionally woven into another unit, or intentionally excluded.
2. Trace important secondary flows: error handling, jobs, migrations, webhooks, CLI subcommands, background workers, schedulers.
3. Check the dependency graph. If a heavily imported module is missing from the plan, decide whether to add a unit or explicitly weave it into an existing one.
4. Output a short coverage summary before proceeding.

If a meaningful gap remains, revise the unit list first.

### Phase 3: Build the Speedrun

If it helps, scaffold the directory first with `scripts/scaffold_speedrun.py`, then fill in the actual content.

Build Units 2+ first. Build Unit 1 last so it imports real public APIs from the other units.

For each unit:

1. Create `speedrun-<repo-name>/unit-N-<slug>/`.
2. Write `README.md` using [references/unit-readme-template.md](references/unit-readme-template.md).
3. Extract the minimum code needed to teach that concept.
4. Add `// LEARN:` comments only at non-obvious points.
5. Stub only external boundaries. Do not stub inter-unit dependencies.
6. Give the unit an entry point that runs in isolation with sample data.

For Unit 1 specifically:

- Import sibling units with real relative/module imports.
- Demonstrate real data flowing across units.
- Do not narrate subsystem behavior with placeholder logging.

At the speedrun root:

- Keep one shared dependency manifest for the whole speedrun.
- Keep one `.vscode/launch.json` with a named entry per unit plus a `Run Current File` entry.
- Keep unit directories as source plus `README.md`; do not add per-unit `.vscode/` or dependency manifests.
- Write the root `README.md` and `SIMPLIFICATIONS.md` using [references/root-files-template.md](references/root-files-template.md).

### Phase 4: Verification

Run `scripts/verify_speedrun.py <speedrun-dir>` first for structural checks.

Then apply the manual acceptance checklist in [references/verification-checklist.md](references/verification-checklist.md). Do not call the speedrun complete unless all of these are true:

- Every documented run command works from the stated directory.
- Unit 1 really imports and orchestrates Units 2+.
- The root debug configuration points at real unit entry points.
- `SIMPLIFICATIONS.md` lists all meaningful stubs and omissions.
- The generated explanations match the extracted code, not the original repo's complexity.

### Phase 5: Generate and Verify HTML Learning Explanations (Required)

Only do this **after** executing and validating the extracted runnable units.

1. Create `learning/overview.md`, plus `learning/unit-N-<slug>.md`
   for **every** unit in the generated Speedrun. These are authored educational
   narratives based on inspected source and observed unit output, NOT generated
   from a generic Markdown boilerplate. Follow
   `references/visual-explanations.md` for diagrams, annotated source,
   prediction/re-run exercises, and explicit teaching simplifications.
2. The overview is the entry point: what the original project does, a visual
   main flow, a learning-order map, and links back to runnable units. Each
   per-unit page explains the actual reduced code path and one experiment.
3. Add `[Visual learning overview](learning/overview.html)` to the generated
   **root** README; add `[Visual explanation](../learning/unit-N-<slug>.html)`
   to every generated **unit** README. Keep runnable commands alongside the links.
4. Run the bundled adapter (use the absolute path to this skill's script):

   ```bash
   python /path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-<repo-name>
   python /path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-<repo-name> --check
   ```

   Use `--am /absolute/path/to/scripts/am.mjs` if the renderer is not installed
   in the usual location. The adapter uses Answer me with HTML to generate
   self-contained `learning/*.html` and an integrity manifest. Do not hand-code
   HTML. Never let optional renderer failure break the already runnable code.
5. Check page accuracy against actual generated code: `src=` paths and line
   ranges exist, diagrams match real simplified control flow, expected outputs
   were observed, and mock/simulation boundaries are explicit.
6. Re-run `scripts/verify_speedrun.py --require-html <speedrun-dir>` to
   verify the full deliverable, including every HTML page and README link.
   A missing CLI, missing page, or stale Markdown is **not** a successful
   complete Speedrun. Report runnable-code success and HTML blocker separately.
7. In the final handoff link the generated **overview.html** and the original
   README; do not just print a filesystem path or say "HTML can be generated".
   Unless specifically asked for a video, do not generate one.

## Principles

- **Feynman-first**: Explain simply before being precise.
- **Runnable over readable**: Every unit must execute.
- **Overall then zoom-in**: Start with the full picture, then drill into subsystems.
- **Minimal extraction**: Copy the least code necessary to preserve the concept.
- **Real data shapes**: Mock realistic structures, not toy placeholders.
- **Debug-first**: The speedrun must be easier to inspect than the original codebase.
- **Terminology-rich**: Define domain-specific jargon before using it.
- **Explicit simplifications**: Every omission should be traceable in `SIMPLIFICATIONS.md`.
- **Runtime-aware**: Shape commands, debugger config, and file layout to the actual runtime, not a default Node.js mental model.
