"""Actual DeerFlow Unit 5 -> Unit Evidence -> HTML smoke test.

Creates an isolated one-unit Speedrun from the existing runnable unit; the
other nine units are deliberately NOT claimed as already migrated.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CASE = Path(__file__).resolve().parents[1]
REPO = CASE.parents[1]
UNIT = "unit-5-tools-sandbox"
EVIDENCE = REPO / ".codex/skills/code-speedrun/scripts/unit_evidence.py"
RENDER = REPO / ".codex/skills/code-speedrun/scripts/render_learning_pages.py"
VERIFY = REPO / ".codex/skills/code-speedrun/scripts/verify_speedrun.py"


def checked(*argv: str, cwd: Path) -> None:
    subprocess.run([sys.executable, *map(str, argv)], cwd=cwd, check=True)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Pass the absolute path to upstream am.mjs")
    am = Path(sys.argv[1]).resolve()
    if not am.is_file():
        raise SystemExit(f"Missing upstream am.mjs: {am}")
    sys.path.insert(0, str(CASE / UNIT))
    from learning_experience import build_traces, lesson_markdown

    with tempfile.TemporaryDirectory(prefix="speedrun-deerflow-real-evidence-") as temp:
        root = Path(temp) / "speedrun-deerflow-unit5"
        shutil.copytree(
            CASE / UNIT, root / UNIT,
            ignore=shutil.ignore_patterns("_demo_data", "learning-output", "__pycache__", "*.pyc"),
        )
        learning = root / "learning"
        learning.mkdir()
        (root / ".vscode").mkdir()
        (root / ".vscode/launch.json").write_text(
            '{"configurations":[{"name":"Unit 5","type":"debugpy"}]}\n', encoding="utf-8"
        )
        (root / "README.md").write_text(
            "# DeerFlow Unit 5\n[Visual learning overview](learning/overview.html)\n",
            encoding="utf-8",
        )
        (root / UNIT / "README.md").write_text(
            f"# Unit 5\n[Visual explanation](../learning/{UNIT}.html)\n", encoding="utf-8"
        )
        (root / "SIMPLIFICATIONS.md").write_text(
            (CASE / "SIMPLIFICATIONS.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        checked(
            EVIDENCE, "capture", root, "--unit", UNIT,
            "--source", f"{UNIT}/main.py",
            "--source", f"{UNIT}/tools_sandbox_demo.py",
            "--mode", "offline-scripted-langgraph",
            "--question", "Does a model without tool_calls execute the tools node?",
            "--change", "Make ScriptedToolCallingModel return a final answer immediately.",
            "--observe", "Compare the tool_trace in stdout.",
            "--", sys.executable, f"{UNIT}/main.py",
            cwd=root,
        )
        captured = json.loads((learning / f"evidence/{UNIT}.json").read_text(encoding="utf-8"))
        assert captured["execution"]["exit_code"] == 0
        stdout = json.loads(captured["execution"]["stdout"])
        assert stdout["mode"] == "offline-scripted-langgraph"
        assert stdout["agent"]["tool_trace"]

        trace = build_traces()
        evidence_path = f"learning/evidence/{UNIT}.json"
        lesson = lesson_markdown(trace)
        lesson += (
            "\n## H Evidence provenance\n"
            + "Verified offline execution: " + chr(96) + evidence_path + chr(96) + ".\n"
            + "This is a scripted teaching model, not production DeerFlow.\n"
        )
        (learning / f"{UNIT}.md").write_text(lesson, encoding="utf-8")
        fence = chr(96) * 3
        (learning / "overview.md").write_text(
            "---\ntemplate: doc\ntitle: DeerFlow Unit 5 evidence pilot\n"
            "subtitle: Verified offline LangGraph teaching unit\n---\n"
            "## A Actual observed flow\n"
            "The scripted model calls bash, reads ToolMessage and returns a final message.\n"
            "## B A visual learning map\n"
            + fence + "flow LR\n"
            "(User) -> Model: prompt\n"
            "Model -> Tools: tool_calls\n"
            "Tools -> Model: ToolMessage\n"
            "Model -> (End): answer\n"
            + fence + "\n",
            encoding="utf-8",
        )
        checked(RENDER, root, "--require-evidence", "--am", am, cwd=root)
        checked(RENDER, root, "--check", "--require-evidence", cwd=root)
        checked(VERIFY, "--require-html", "--require-evidence", root, cwd=root)
        for name in ("overview", UNIT):
            assert (learning / f"{name}.html").stat().st_size > 1000
        print("PASS: real DeerFlow Unit 5 evidence -> actual am HTML -> strict checks")


if __name__ == "__main__":
    main()
