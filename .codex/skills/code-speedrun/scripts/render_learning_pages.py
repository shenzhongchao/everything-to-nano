#!/usr/bin/env python3
"""Render/verify Code Speedrun explanation drafts with Answer me with HTML.

The agent authors learning/*.md from verified code; this script only renders it.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_RE = re.compile(r"unit-\d+-.+")
VERSION = 1


def pages(root: Path) -> list[tuple[Path, Path]]:
    units = sorted(
        (p for p in root.iterdir() if p.is_dir() and UNIT_RE.fullmatch(p.name)),
        key=lambda p: (int(p.name.split("-")[1]), p.name),
    )
    if not units:
        raise ValueError("No unit-N-slug directories found")
    learning = root / "learning"
    return [(learning / "overview.md", learning / "overview.html")] + [
        (learning / f"{unit.name}.md", learning / f"{unit.name}.html")
        for unit in units
    ]


def command_for_am(value: str | None) -> list[str]:
    """Use an installed renderer. No implicit download, package install or auto-update."""
    candidate = value or os.environ.get("SPEEDRUN_AM")
    if candidate:
        path = Path(candidate).expanduser()
        if path.suffix == ".mjs":
            if not path.is_file():
                raise FileNotFoundError(f"Missing Answer me with HTML script: {path}")
            node = shutil.which("node")
            if not node:
                raise RuntimeError("Node.js 20+ is required for am.mjs")
            return [node, str(path.resolve())]
        found = shutil.which(candidate)
        if found:
            return [found]
        if path.is_file():
            return [str(path.resolve())]
        raise FileNotFoundError(f"Cannot find Answer me with HTML CLI: {candidate}")
    for name in ("am", "answer-me-with-html"):
        found = shutil.which(name)
        if found:
            return [found]
    for base in (Path.home() / ".codex", Path.home() / ".claude"):
        script = base / "skills" / "answer-me-with-html" / "scripts" / "am.mjs"
        if script.is_file():
            return command_for_am(str(script))
    raise FileNotFoundError(
        "Answer me with HTML is not installed. Install the upstream skill "
        "(https://github.com/QingYunA/answer-me-with-html) and retry, "
        "or pass --am /absolute/path/to/scripts/am.mjs. "
        "Markdown drafts remain available but HTML generation is NOT complete."
    )


def validate_draft(source: Path) -> bytes:
    if not source.is_file():
        raise FileNotFoundError(f"Missing agent-authored explanation: {source}")
    data = source.read_bytes()
    content = data.decode("utf-8")
    if not content.startswith("---\n") or "title:" not in content or "\n## " not in content:
        raise ValueError(f"Missing frontmatter, title or explanation panels: {source}")
    return data


def evidence_snapshot(root: Path, expected: list[tuple[Path, Path]]) -> dict[str, str]:
    """Validate all Unit evidence and actual source excerpts before HTML rendering."""
    evidence_script = Path(__file__).with_name("unit_evidence.py")
    spec = importlib.util.spec_from_file_location("code_speedrun_unit_evidence", evidence_script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load evidence validator: {evidence_script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fingerprints = module.fingerprints(root)
    snapshot = {
        "overview": hashlib.sha256(
            json.dumps(fingerprints, sort_keys=True).encode("utf-8")
        ).hexdigest()
    }
    for source, _ in expected:
        if source.name == "overview.md":
            continue
        unit = source.stem
        record = module.validate(root, unit)
        expected_ref = f"learning/evidence/{unit}.json"
        markdown = source.read_text(encoding="utf-8")
        if expected_ref not in markdown:
            raise ValueError(f"{source}: must cite {expected_ref}")
        snippets = list(re.finditer(
            r"```[^\n]*\bsrc=([^\s`]+)[^\n]*\blines=(\d+)-(\d+)",
            markdown,
        ))
        if not snippets:
            raise ValueError(f"{source}: missing source-backed fenced code excerpt")
        permitted = {item["path"] for item in record["sources"]}
        for match in snippets:
            path, first, last = match.group(1), int(match.group(2)), int(match.group(3))
            if path not in permitted:
                raise ValueError(f"{source}: source excerpt {path} not included in Unit Evidence")
            source_path = module.inside(root, path)
            count = len(source_path.read_text(encoding="utf-8").splitlines())
            if first < 1 or last < first or last > count:
                raise ValueError(f"{source}: invalid source lines {path}:{first}-{last} (file has {count})")
        snapshot[unit] = fingerprints[unit]
    return snapshot


def check(
    root: Path,
    expected: list[tuple[Path, Path]],
    require_evidence: bool = False,
) -> None:
    manifest_path = root / "learning" / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing render manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != VERSION:
        raise ValueError("Unsupported or missing learning manifest schema")
    evidence = evidence_snapshot(root, expected) if require_evidence else None
    if require_evidence and manifest.get("evidence") != evidence:
        raise ValueError("Rendered HTML is stale: Unit Evidence or source changed; rerun renderer")
    recorded = {row["source"]: row for row in manifest["pages"]}
    if set(recorded) != {s.relative_to(root).as_posix() for s, _ in expected}:
        raise ValueError("Learning manifest does not cover every current Unit")
    for source, output in expected:
        data = validate_draft(source)
        key = source.relative_to(root).as_posix()
        item = recorded[key]
        if item["sha256"] != hashlib.sha256(data).hexdigest():
            raise ValueError(f"HTML is stale for {key}; rerun the renderer")
        if item["html"] != output.relative_to(root).as_posix():
            raise ValueError(f"Wrong HTML destination for {key}")
        if not output.is_file() or output.stat().st_size < 100:
            raise ValueError(f"Missing or empty rendered HTML: {output}")
        opening = output.read_text(encoding="utf-8", errors="replace")[:1200].lower()
        if "<html" not in opening and "<!doctype html" not in opening:
            raise ValueError(f"Invalid HTML output: {output}")
    print(f"Verified {len(expected)} learning pages: {manifest_path}")


def render(
    root: Path,
    expected: list[tuple[Path, Path]],
    cli: list[str],
    require_evidence: bool = False,
) -> None:
    # Validate the full set before invoking the renderer.
    inputs = [(src, out, validate_draft(src)) for src, out in expected]
    evidence = evidence_snapshot(root, expected) if require_evidence else None
    for src, out, _ in inputs:
        cmd = [
            *cli, "render", src.relative_to(root).as_posix(),
            "-o", out.relative_to(root).as_posix(), "--no-open",
        ]
        # CWD=root makes src=unit-N-.../file.py code excerpts resolvable.
        result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=120)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[-1600:]
            raise RuntimeError(f"Failed rendering {src.name}: {detail}")
        if not out.is_file() or out.stat().st_size < 100:
            raise RuntimeError(f"Renderer did not create {out}")
        print(f"Rendered {out.relative_to(root)}")
    manifest = {
        "schema_version": VERSION,
        "renderer": "answer-me-with-html",
        **({"evidence": evidence} if evidence is not None else {}),
        "pages": [
            {
                "source": src.relative_to(root).as_posix(),
                "html": out.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for src, out, data in inputs
        ],
    }
    path = root / "learning" / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check(root, expected, require_evidence=require_evidence)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Speedrun explanations using am.")
    parser.add_argument("speedrun_dir", type=Path, help="Generated speedrun project root")
    parser.add_argument("--am", help="Installed am command or absolute scripts/am.mjs path")
    parser.add_argument("--check", action="store_true", help="Verify pages and detect stale HTML")
    parser.add_argument(
        "--require-evidence", action="store_true",
        help="Require fresh execution evidence, its source hashes and source-backed excerpts",
    )
    args = parser.parse_args()
    try:
        root = args.speedrun_dir.expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Speedrun directory does not exist: {root}")
        expected = pages(root)
        if args.check:
            check(root, expected, require_evidence=args.require_evidence)
        else:
            render(root, expected, command_for_am(args.am), require_evidence=args.require_evidence)
    except (ValueError, FileNotFoundError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
