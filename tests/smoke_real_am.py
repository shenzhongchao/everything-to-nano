"""Smoke test for the real, pinned Answer me with HTML CLI.

Usage: python tests/smoke_real_am.py /path/to/answer-me-with-html/skills/answer-me-with-html/scripts/am.mjs
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADAPTER = REPO / ".codex/skills/code-speedrun/scripts/render_learning_pages.py"


def main() -> None:
    am = Path(sys.argv[1]).resolve()
    if not am.is_file():
        raise SystemExit(f"Missing upstream am.mjs: {am}")
    with tempfile.TemporaryDirectory(prefix="speedrun-am-smoke-") as workspace:
        root = Path(workspace) / "speedrun-hello"
        unit = root / "unit-1-overall"
        learning = root / "learning"
        unit.mkdir(parents=True)
        learning.mkdir()
        (unit / "main.py").write_text(
            "def say_hello():\n"
            "    return 'HELLO'\n\n"
            "print(say_hello())\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "# Example\n\n[Visual overview](learning/overview.html)\n", encoding="utf-8"
        )
        (root / "SIMPLIFICATIONS.md").write_text(
            "# Simplifications\n\n## Unit 1: Overall\n- No external services.\n",
            encoding="utf-8",
        )
        (unit / "README.md").write_text(
            "[Visual explanation](../learning/unit-1-overall.html)\n", encoding="utf-8"
        )
        (root / ".vscode").mkdir()
        (root / ".vscode" / "launch.json").write_text(
            '{"configurations":[{"name":"Unit 1","type":"debugpy"}]}', encoding="utf-8"
        )
        (learning / "overview.md").write_text(
            "---\n"
            "template: doc\n"
            "title: Speedrun Hello\n"
            "subtitle: A minimal runnable function\n"
            "---\n"
            "## A Start with the observed output\n"
            "Run python unit-1-overall/main.py; it prints HELLO.\n"
            "## B One-call architecture\n"
            "```flow LR\n"
            "(Entry) -> Function: say_hello\n"
            "Function -> (Output): HELLO\n"
            "```\n",
            encoding="utf-8",
        )
        (learning / "unit-1-overall.md").write_text(
            "---\n"
            "template: doc\n"
            "title: Unit 1 — Return a value\n"
            "---\n"
            "## A Predict and run\n"
            "Predict what happens if return is changed. Run python unit-1-overall/main.py.\n"
            "## B Find the function in code\n"
            "```py src=unit-1-overall/main.py lines=1-4 hl=2\n"
            "```\n"
            "## C Simplification boundary\n"
            "This unit intentionally uses no external services.\n",
            encoding="utf-8",
        )
        subprocess.run(
            [sys.executable, str(unit / "main.py")], cwd=root, check=True,
        )
        subprocess.run(
            [sys.executable, str(ADAPTER), str(root), "--am", str(am)],
            cwd=root, check=True,
        )
        subprocess.run(
            [sys.executable, str(ADAPTER), str(root), "--check"],
            cwd=root, check=True,
        )
        subprocess.run(
            [sys.executable, str(REPO / ".codex/skills/code-speedrun/scripts/verify_speedrun.py"),
             "--require-html", str(root)], cwd=root, check=True,
        )
        for name in ("overview", "unit-1-overall"):
            html = learning / f"{name}.html"
            assert "<html" in html.read_text(encoding="utf-8").lower()
        print("Real Answer me with HTML CLI integration passed")


if __name__ == "__main__":
    main()
