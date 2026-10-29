# Visual Teaching Pages (Answer me with HTML)

This reference is part of the **normal Code Speedrun output workflow**.
The visual pages complement the runnable code. They are not decorative summaries
or a separate optional demo bolted onto a particular repository.

## Output contract

For each newly generated \`speedrun-<repo>/\`, produce:

- \`learning/overview.md\` → \`learning/overview.html\`
- \`learning/unit-1-<slug>.md\` → \`learning/unit-1-<slug>.html\`
- One matching Markdown/HTML pair for every other unit
- \`learning/manifest.json\`, written by the renderer
- Root README link to \`learning/overview.html\`
- Every Unit README link to its matching \`../learning/unit-N-<slug>.html\`

Use \`learning/\` as the only home for visual explanations. The unit folders still
contain executable code and README, not generated HTML bundles. Rendered HTML is a
self-contained artifact that learners can open without a dev server.

The **agent** writes truthful Markdown drafts. \`answer-me-with-html\` handles
rendering, diagram layout, CSS, and style linting. Never hand-write full HTML or
fork the upstream renderer to fabricate a learning page.

## Preconditions and renderer discovery

1. Verify the runnable unit, its actual output, and the exact source locations.
2. Use an installed \`am\` executable, or the upstream
   \`skills/answer-me-with-html/scripts/am.mjs\` with Node.js 20+.
3. Never run \`npm install\`, \`npx -y\`, or download/update a skill without user
   approval. If the renderer is unavailable, still author all \`learning/*.md\`
   drafts and report HTML generation as **pending**, not as completed.
4. Do not force this dependency on normal execution of the learner's code.
   \`am\` is a build-time dependency only.

Render from the generated speedrun root, not the source repository. The bundled
adapter resolves installed renderers and gives clear errors:

\`\`\`bash
python /absolute/path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-project
python /absolute/path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-project --check
\`\`\`

For a nonstandard location, provide
\`--am /absolute/path/to/answer-me-with-html/skills/answer-me-with-html/scripts/am.mjs\`.
The adapter uses \`am render learning/<draft>.md -o learning/<draft>.html --no-open\`.
Do not open browsers automatically or publish generated pages externally.

## What the agent must write (not the renderer)

A useful page explains **one reasoning path with evidence**, not a wall of prose
formatted into cards. Start with the behavior someone can run, then explain
how code produces it. Every unit page should contain:

1. **Plain-language question and goal:** what can learners predict after the unit?
2. **System relationship:** use \`flow\`, \`sequence\`, or \`tree\` to show the
   observed main path. Use \`er\` only for true data-model relations.
3. **Trace from code to behavior:** real entry point, one or two key functions,
   the input, **verified** output, and why this boundary matters.
4. **Source excerpt:** reference real generated unit source with
   \`\`\`py src=unit-5-tools-sandbox/tools_sandbox_demo.py lines=270-305 hl=283\`\`\`
   style fences (language is file-appropriate). Paths are **relative to the
   speedrun root**, because the CLI runs from there. Check file existence and
   line numbers before rendering.
5. **Learner action:** one concrete change, a prediction *before* running, the
   exact command to rerun, and which output or debugger variable to inspect.
6. **Truth boundary:** tell users which parts are stubbed, scripted, simulated
   or omitted, linking to root \`SIMPLIFICATIONS.md\` in the surrounding README.
   Do not present teaching mocks as production behavior.
7. **Navigation:** the root HTML is a map of the unit order; the root README
   retains the canonical full path. Unit pages need enough context to stand alone.

Write **4–6 panels per unit** by default; a concise overview may use 3–6 panels.
Prefer one diagram that explains the core mechanism over several generic charts.
Do not invent performance numbers or observational traces. If execution cannot
be verified, label the illustration as hypothetical and report the blocker.

The upstream \`am\` CLI supports descriptive diagrams, highlighted source
references, maths, structured comparisons, and \`ask\` for explicit choices.
Its \`ask\` is a reader response feature, **not** code execution. Do not claim
that rendered pages run or debug the learner's project. If real replay is
needed, implement that as a separate task and keep it distinguishable from
the static HTML explainer.

## Minimal authored Markdown example (adapt all names to actual source)

\`\`\`\`markdown
---
template: doc
title: Unit 2 — Routing one request
subtitle: Watch the request move between two verified functions
---
## A What happens first?
Run \`python unit-2-router/main.py\` from the speedrun root.
The observed output is \`route: /hello\`.

## B The execution path
\`\`\`flow LR
(Request) -> Router: inspect path
Router -> Handler: select matching route
Handler -> (Response): render greeting
\`\`\`

## C Find it in the runnable code
\`\`\`py src=unit-2-router/main.py lines=8-24 hl=12
\`\`\`

## D Change one thing
Before editing the route name, predict which branch will be chosen.
Edit \`main.py\`, rerun the command above and compare your prediction.

## E Where the teaching version stops
This example replaces the production route registry with a hard-coded map;
consult \`SIMPLIFICATIONS.md\` for the original implementation path.
\`\`\`\`

The example is **illustrative only**. Never reuse its claims, paths or observed
output without matching the generated source and executing that actual unit.

## Acceptance criteria

- Every existing unit has a non-placeholder \`learning/unit-*.md\` and HTML page.
- Overview page and README links are present and lead to actual files.
- For each unit, code snippets point at real files and valid line ranges.
- Every diagram matches the generated code, **not a more complex original**.
- At least one prediction/change/re-run prompt per unit.
- Verify \`learning/manifest.json\` using \`--check\`. If Markdown later changes,
  re-render; the check detects stale drafts using SHA-256.
- The original run commands and debug configurations remain functional.
- State clearly if \`am\` is not installed and HTML could not be rendered.
