"""Regression tests for the Code Speedrun -> Answer me with HTML pipeline.

Tests use a fake CLI for deterministic orchestration. CI separately checks
the real upstream renderer against a small fixture.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODEX = ROOT / ".codex" / "skills" / "code-speedrun"
CLAUDE = ROOT / ".claude" / "skills" / "code-speedrun"


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def generated_speedrun(tmp_path: Path):
    root = tmp_path / "speedrun-example"
    root.mkdir()
    (root / ".vscode").mkdir()
    (root / ".vscode" / "launch.json").write_text(
        '{"configurations":[{"name":"Unit 1","type":"debugpy"}]}', encoding="utf-8"
    )
    unit_names = ["unit-1-overall", "unit-2-router"]
    (root / "README.md").write_text(
        "# Example\n\n[Visual learning overview](learning/overview.html)\n", encoding="utf-8"
    )
    (root / "SIMPLIFICATIONS.md").write_text(
        "# Simplifications\n\n## Unit 1: Overall\n\n## Unit 2: Router\n",
        encoding="utf-8",
    )
    (root / "learning").mkdir()
    (root / "learning" / "overview.md").write_text(
        "---\ntemplate: doc\ntitle: Example\n---\n## A One request\nA to B: request.\n",
        encoding="utf-8",
    )
    for name in unit_names:
        folder = root / name
        folder.mkdir()
        (folder / "main.py").write_text('print("success")\n', encoding="utf-8")
        (folder / "README.md").write_text(
            f"# {name}\n[Visual explanation](../learning/{name}.html)\n",
            encoding="utf-8",
        )
        (root / "learning" / f"{name}.md").write_text(
            f"---\ntitle: {name}\n---\n## A Run this unit\n"
            f"Run python {name}/main.py.\n\n"
            f"## B Read code\nThe real snippet is {name}/main.py line 1.\n",
            encoding="utf-8",
        )
    fake_am = tmp_path / "fake_am.py"
    fake_am.write_text(
        "import pathlib,sys\n"
        "args=sys.argv[1:]\n"
        "assert args[0]=='render' and '-o' in args and '--no-open' in args\n"
        "p=pathlib.Path(args[args.index('-o')+1])\n"
        "p.write_text('<!doctype html><html><body>'+('demo'*80)+'</body></html>',encoding='utf-8')\n",
        encoding="utf-8",
    )
    return root, fake_am


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_render_and_verify_all_units(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    module = load_script(skill / "scripts" / "render_learning_pages.py", skill.parent.name)
    expected = module.pages(root)
    assert len(expected) == 3
    module.render(root, expected, [sys.executable, str(fake_am)])
    module.check(root, expected)
    manifest = json.loads((root / "learning" / "manifest.json").read_text())
    assert len(manifest["pages"]) == 3
    assert all(row["sha256"] for row in manifest["pages"])

    result = subprocess.run(
        [sys.executable, str(skill / "scripts" / "verify_speedrun.py"),
         "--require-html", str(root)],
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_missing_and_stale_pages_fail(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    module = load_script(skill / "scripts" / "render_learning_pages.py", skill.parent.name)
    expected = module.pages(root)
    with pytest.raises(FileNotFoundError):
        module.check(root, expected)
    module.render(root, expected, [sys.executable, str(fake_am)])
    draft = root / "learning" / "unit-2-router.md"
    draft.write_text(draft.read_text() + "\nNew verified observation.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        module.check(root, expected)
    status = subprocess.run(
        [sys.executable, str(skill / "scripts" / "verify_speedrun.py"),
         "--require-html", str(root)],
        text=True, capture_output=True,
    )
    assert status.returncode != 0
    assert "stale" in status.stdout


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_bad_renderer_and_missing_draft(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    module = load_script(skill / "scripts" / "render_learning_pages.py", skill.parent.name)
    with pytest.raises(FileNotFoundError):
        module.command_for_am("/nonexistent/am.mjs")
    (root / "learning" / "unit-1-overall.md").unlink()
    with pytest.raises(FileNotFoundError):
        module.render(root, module.pages(root), [sys.executable, str(fake_am)])
    assert not (root / "learning" / "overview.html").exists()


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_missing_readme_link_is_rejected(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    module = load_script(skill / "scripts" / "render_learning_pages.py", skill.parent.name)
    module.render(root, module.pages(root), [sys.executable, str(fake_am)])
    (root / "unit-2-router" / "README.md").write_text("# Router\n", encoding="utf-8")
    checked = subprocess.run(
        [sys.executable, str(skill / "scripts" / "verify_speedrun.py"),
         "--require-html", str(root)],
        text=True, capture_output=True,
    )
    assert checked.returncode != 0
    assert "does not link" in checked.stdout


def test_codex_and_claude_share_identical_renderer():
    assert (CODEX / "scripts" / "render_learning_pages.py").read_bytes() == (
        CLAUDE / "scripts" / "render_learning_pages.py"
    ).read_bytes()


def prepare_real_evidence(skill: Path, root: Path) -> None:
    """Run actual fixture programs, then cite the captured source in each lesson."""
    module = load_script(skill / "scripts" / "unit_evidence.py", "evidence_" + skill.parent.name)
    for unit in ("unit-1-overall", "unit-2-router"):
        module.capture(
            root, unit=unit,
            command=[sys.executable, f"{unit}/main.py"],
            sources=[f"{unit}/main.py"],
            question="What will print if we replace success with changed?",
            change="Change the literal printed by main.py and recapture evidence.",
            observe="Compare the captured stdout from each actual run.",
        )
        draft = root / "learning" / f"{unit}.md"
        draft.write_text(
            draft.read_text(encoding="utf-8")
            + f"\n## C Execution evidence\n"
            + f"Verified run: learning/evidence/{unit}.json\n"
            + f"\n" + "```" + f"py src={unit}/main.py lines=1-1\n"
            + "```\n",
            encoding="utf-8",
        )


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_real_evidence_must_precede_html_and_tracks_source_changes(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    adapter = load_script(skill / "scripts" / "render_learning_pages.py", "renderer_ev_" + skill.parent.name)
    expected = adapter.pages(root)

    with pytest.raises(FileNotFoundError, match="Missing evidence"):
        adapter.render(root, expected, [sys.executable, str(fake_am)], require_evidence=True)

    prepare_real_evidence(skill, root)
    adapter.render(root, expected, [sys.executable, str(fake_am)], require_evidence=True)
    adapter.check(root, expected, require_evidence=True)
    manifest = json.loads((root / "learning" / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["evidence"]) == {"overview", "unit-1-overall", "unit-2-router"}
    assert "success" in json.loads((root / "learning/evidence/unit-1-overall.json").read_text())["execution"]["stdout"]
    result = subprocess.run(
        [sys.executable, str(skill / "scripts/verify_speedrun.py"), "--require-html",
         "--require-evidence", str(root)],
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # The old Markdown and HTML are untouched; a CODE change must still fail.
    (root / "unit-2-router/main.py").write_text('print("changed")\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Stale evidence"):
        adapter.check(root, expected, require_evidence=True)
    failed = subprocess.run(
        [sys.executable, str(skill / "scripts/verify_speedrun.py"),
         "--require-html", "--require-evidence", str(root)],
        text=True, capture_output=True,
    )
    assert failed.returncode != 0
    assert "Stale evidence" in failed.stdout


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_manifest_detects_changed_evidence_without_changed_markdown(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    prepare_real_evidence(skill, root)
    adapter = load_script(skill / "scripts" / "render_learning_pages.py", "renderer_manifest_" + skill.parent.name)
    expected = adapter.pages(root)
    adapter.render(root, expected, [sys.executable, str(fake_am)], require_evidence=True)
    path = root / "learning/evidence/unit-1-overall.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["experiment"]["prediction_question"] = "A different learning question"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        adapter.check(root, expected, require_evidence=True)


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_source_excerpt_must_be_in_evidence_and_have_real_lines(skill, generated_speedrun):
    root, fake_am = generated_speedrun
    prepare_real_evidence(skill, root)
    adapter = load_script(skill / "scripts" / "render_learning_pages.py", "renderer_excerpt_" + skill.parent.name)
    expected = adapter.pages(root)
    target = root / "learning/unit-1-overall.md"
    original = target.read_text(encoding="utf-8")
    target.write_text(original.replace("lines=1-1", "lines=1-9999"), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid source lines"):
        adapter.render(root, expected, [sys.executable, str(fake_am)], require_evidence=True)
    target.write_text(original.replace("unit-1-overall/main.py lines=", "unit-2-router/main.py lines="),
                      encoding="utf-8")
    with pytest.raises(ValueError, match="not included in Unit Evidence"):
        adapter.render(root, expected, [sys.executable, str(fake_am)], require_evidence=True)


@pytest.mark.parametrize("skill", [CODEX, CLAUDE])
def test_failing_run_and_escaping_paths_never_write_evidence(skill, generated_speedrun, tmp_path):
    root, _ = generated_speedrun
    evidence = load_script(skill / "scripts" / "unit_evidence.py", "evidence_fail_" + skill.parent.name)
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')\n", encoding="utf-8")
    args = dict(
        root=root, unit="unit-1-overall", command=[sys.executable, "unit-1-overall/main.py"],
        question="Predict output", change="Edit output", observe="Read stdout",
    )
    with pytest.raises(ValueError, match="escapes Speedrun root"):
        evidence.capture(**args, sources=["../outside.py"])
    assert not (root / "learning/evidence/unit-1-overall.json").exists()

    (root / "unit-1-overall/main.py").write_text("raise RuntimeError('expected failure')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence NOT recorded"):
        evidence.capture(**args, sources=["unit-1-overall/main.py"])
    assert not (root / "learning/evidence/unit-1-overall.json").exists()


def test_codex_and_claude_share_identical_evidence_capture():
    assert (CODEX / "scripts/unit_evidence.py").read_bytes() == (
        CLAUDE / "scripts/unit_evidence.py"
    ).read_bytes()
