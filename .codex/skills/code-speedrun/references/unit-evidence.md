# Unit Evidence: verified input to teaching explanations

Every **new** Speedrun unit must have an execution evidence record before the
agent writes its HTML teaching narrative. This is the missing interface between
the runnable Code Speedrun output and Answer me with HTML.

## Purpose and structure

The common CLI writes one JSON record per unit in:

- learning/evidence/unit-N-<slug>.json

These records use schema_version 1, and include:
- unit ID and execution mode (offline demonstration vs scripted/mock)
- the exact reviewed argv, working directory and numeric exit code
- real captured stdout/stderr, SHA-256 digests for complete outputs, truncation markers
- source paths and SHA-256 digests of the **generated runnable code**
- one prediction question, explicit code change, expected observable variable/output,
  and the rerun command
- provenance explicitly stating the trace comes from a simplified execution

For every Unit, review the command first. Do not record a live model call,
production credentials, private user data, untrusted network script, or secrets
in shareable evidence. Default to deterministic offline executions.
The capture helper runs a command **only** when explicitly invoked by the agent
for the user's learning project. Checking evidence never runs code. Stdout and
stderr are limited to 16 KiB each in the JSON (full-output hash is retained);
avoid commands whose output could disclose secrets.

## Capture after the runnable unit passes

Use the bundled skill script; it is runtime-neutral, but Python 3.9+ is needed
for the helper. Arguments after -- are an argv vector, **not shell text**.
The script runs from the generated Speedrun root unless --cwd is specified.

```bash
python /path/to/code-speedrun/scripts/unit_evidence.py capture ./speedrun-project \
  --unit unit-2-router \
  --source unit-2-router/main.py \
  --source unit-2-router/router.py \
  --mode offline-demo \
  --question "What happens when the route is missing?" \
  --change "Change the route map to remove /hello." \
  --observe "Compare the printed route and selected handler." \
  -- python unit-2-router/main.py
```

The command must have been executed successfully. If any recorded source changes
during the run, capture fails. Avoid recording source files under temporary or
ignored output directories. If a command cannot be verified, explicitly report
it as blocked; never fabricate output or claim a runnable unit is complete.

Inspect the JSON and output. Do not copy captured secrets to shareable HTML.
A SHA-256 file digest shows that code was unchanged after capture. It does not
prove the semantic quality of the explanation or establish behavior in production.

## Author evidence-backed learning pages

For each `learning/unit-N-<slug>.md`:

1. Include the relative evidence path literally somewhere visible, e.g.
   "Verified execution: `learning/evidence/unit-2-router.json`".
2. Quote or summarize **real** observed output from `execution.stdout`.
3. Include at least one source-backed fence, using the **exact** paths recorded
   under `sources[]`, with valid existing line numbers:
   ```py src=unit-2-router/router.py lines=5-20 hl=10```
4. Explain how the relevant source functions produce that observed behavior.
5. Use the recorded experiment as the learner's predict → edit → rerun exercise.
6. Tell the learner which behavior is simulated and link back to
   `SIMPLIFICATIONS.md` from the README. Never treat a stubbed trace as a live
   production execution.

For the root `learning/overview.md`, draw the overview based on the verified
units, not hypothetical behavior. One Unit's source is not a substitute for the
whole project.

Do not ask Answer me with HTML to infer code behavior or reconstruct missing
evidence: it is the **renderer**, not the execution engine or source of truth.

## Strict render and verification

```bash
python /path/to/code-speedrun/scripts/unit_evidence.py check ./speedrun-project
python /path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-project --require-evidence
python /path/to/code-speedrun/scripts/render_learning_pages.py ./speedrun-project --check --require-evidence
python /path/to/code-speedrun/scripts/verify_speedrun.py --require-html --require-evidence ./speedrun-project
```

Strict mode ensures:
- all current units have validated evidence files;
- each source file's SHA-256 still matches the file executed;
- each unit Markdown links to its evidence and contains a source-backed excerpt;
- each excerpt is restricted to documented source paths and valid line ranges;
- render manifest contains evidence fingerprints, including a composite
  fingerprint for the overview; modified evidence or sources invalidate pages;
- the original Markdown freshness and README link checks still apply.

Legacy `--require-html` without `--require-evidence` remains supported for
previously generated pages. **New Skill invocations must use both**.

If a project is intentionally only partially verified, report which units are
blocked. Never silently weaken the strict flags just to obtain green CI.
