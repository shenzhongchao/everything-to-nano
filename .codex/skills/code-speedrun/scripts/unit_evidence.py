#!/usr/bin/env python3
"""Capture and validate evidence from real, deterministic Speedrun unit executions.

No LLM-generated trace or command execution is inferred. The operator supplies
a reviewed offline command and sources; the helper runs it once and records facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = 1
UNIT_RE = re.compile(r"unit-\d+-.+")
MAX_CAPTURE = 16000


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside(root: Path, path: str, *, must_exist: bool = True) -> Path:
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Evidence path escapes Speedrun root: {path}")
    if must_exist and not target.is_file():
        raise FileNotFoundError(f"Missing evidence source file: {path}")
    return target


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root.resolve()).as_posix()


def units(root: Path) -> list[str]:
    return sorted(
        (p.name for p in root.iterdir() if p.is_dir() and UNIT_RE.fullmatch(p.name)),
        key=lambda name: (int(name.split("-")[1]), name),
    )


def evidence_path(root: Path, unit: str) -> Path:
    if unit not in units(root):
        raise ValueError(f"Unknown unit: {unit}")
    return root / "learning" / "evidence" / f"{unit}.json"


def capture(
    root: Path,
    *,
    unit: str,
    command: list[str],
    sources: list[str],
    question: str,
    change: str,
    observe: str,
    cwd: str = ".",
    timeout: int = 90,
    mode: str = "offline-demo",
) -> Path:
    """Execute an explicit trusted command; never run a command from an evidence JSON."""
    root = root.resolve()
    path = evidence_path(root, unit)
    if not command or not command[0]:
        raise ValueError("Supply a reviewed executable command after --")
    if not sources:
        raise ValueError("At least one actual source file is required")
    if not all(s.strip() for s in (question, change, observe, mode)):
        raise ValueError("Experiment question/change/observation and mode are required")
    workdir = (root / cwd).resolve()
    if not workdir.is_relative_to(root) or not workdir.is_dir():
        raise ValueError("Working directory must exist inside the Speedrun root")
    if timeout < 1 or timeout > 600:
        raise ValueError("Timeout must be between 1 and 600 seconds")
    # Record byte digests of all referenced code, before running the example.
    source_rows = []
    for value in dict.fromkeys(sources):
        file = inside(root, value)
        if not file.is_file():
            raise ValueError(f"Not a file: {value}")
        source_rows.append({"path": relative(root, file), "sha256": digest(file.read_bytes())})
    process = subprocess.run(
        command, cwd=workdir, capture_output=True, timeout=timeout, check=False,
    )
    if process.returncode != 0:
        stderr = process.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"Unit command exited {process.returncode}; evidence NOT recorded: {stderr[-1200:]}")
    # Refuse recording a run which edited the purported evidence sources.
    for row in source_rows:
        if digest(inside(root, row["path"]).read_bytes()) != row["sha256"]:
            raise ValueError(f"Unit changed its own source while running: {row['path']}")
    row = {
        "schema_version": SCHEMA,
        "unit": unit,
        "execution": {
            "mode": mode,
            "cwd": relative(root, workdir) or ".",
            "argv": command,
            "exit_code": process.returncode,
            "stdout": process.stdout[:MAX_CAPTURE].decode("utf-8", "replace"),
            "stderr": process.stderr[:MAX_CAPTURE].decode("utf-8", "replace"),
            "stdout_sha256": digest(process.stdout),
            "stderr_sha256": digest(process.stderr),
            "stdout_truncated": len(process.stdout) > MAX_CAPTURE,
            "stderr_truncated": len(process.stderr) > MAX_CAPTURE,
        },
        "sources": source_rows,
        "experiment": {
            "prediction_question": question,
            "change_instruction": change,
            "observe": observe,
            "rerun_argv": command,
        },
        "provenance": (
            "Captured from one actual subprocess run of the simplified Speedrun unit. "
            "Not proof of production system behavior."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate(root, unit)
    return path


def validate(root: Path, unit: str) -> dict:
    """Do not execute code here. Verify schema, source hashes and teaching fields."""
    root = root.resolve()
    path = evidence_path(root, unit)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing evidence: {path}") from None
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA or data.get("unit") != unit:
        raise ValueError(f"Invalid evidence schema or unit: {path}")
    execution = data.get("execution")
    if not isinstance(execution, dict) or execution.get("exit_code") != 0:
        raise ValueError(f"Unit did not complete successfully: {unit}")
    if not isinstance(execution.get("argv"), list) or not execution["argv"]:
        raise ValueError(f"Missing recorded command for {unit}")
    if not isinstance(execution.get("mode"), str) or not execution["mode"]:
        raise ValueError(f"Missing execution mode for {unit}")
    if not isinstance(execution.get("stdout"), str) or not isinstance(execution.get("stderr"), str):
        raise ValueError(f"Missing captured output for {unit}")
    for name in ("stdout_sha256", "stderr_sha256"):
        if not isinstance(execution.get(name), str) or not re.fullmatch(r"[0-9a-f]{64}", execution[name]):
            raise ValueError(f"Missing full output digest: {name}")
    experiment = data.get("experiment")
    if not isinstance(experiment, dict) or not all(
        isinstance(experiment.get(key), str) and experiment[key].strip()
        for key in ("prediction_question", "change_instruction", "observe")
    ):
        raise ValueError(f"Missing prediction/change/observe task in {unit}")
    if not isinstance(data.get("sources"), list) or not data["sources"]:
        raise ValueError(f"Missing source fingerprints in {unit}")
    for source in data["sources"]:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise ValueError(f"Invalid source entry in {unit}")
        file = inside(root, source["path"])
        actual = digest(file.read_bytes())
        if source.get("sha256") != actual:
            raise ValueError(
                f"Stale evidence for {unit}: {source['path']} changed after capture; rerun the unit."
            )
    return data


def fingerprints(root: Path, *, only: list[str] | None = None) -> dict[str, str]:
    """Hash validated evidence bytes, keyed by unit; stale code causes an error."""
    output = {}
    for unit in only if only is not None else units(root):
        validate(root, unit)
        output[unit] = digest(evidence_path(root, unit).read_bytes())
    if not output:
        raise ValueError("No unit evidence found")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    do = sub.add_parser("capture", help="Execute a reviewed offline command and capture evidence")
    do.add_argument("speedrun_dir", type=Path)
    do.add_argument("--unit", required=True)
    do.add_argument("--source", action="append", required=True, dest="sources")
    do.add_argument("--question", required=True)
    do.add_argument("--change", required=True)
    do.add_argument("--observe", required=True)
    do.add_argument("--cwd", default=".")
    do.add_argument("--mode", default="offline-demo")
    do.add_argument("--timeout", type=int, default=90)
    do.add_argument("command", nargs=argparse.REMAINDER)
    check = sub.add_parser("check", help="Check source fingerprints without running commands")
    check.add_argument("speedrun_dir", type=Path)
    check.add_argument("--unit", help="Check one unit, otherwise all units")
    args = parser.parse_args()
    try:
        root = args.speedrun_dir.expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"No such Speedrun root: {root}")
        if args.action == "capture":
            command = args.command[1:] if args.command and args.command[0] == "--" else args.command
            output = capture(
                root, unit=args.unit, command=command, sources=args.sources,
                question=args.question, change=args.change, observe=args.observe,
                cwd=args.cwd, mode=args.mode, timeout=args.timeout,
            )
            print(f"Captured real execution: {output}")
        else:
            rows = fingerprints(root, only=[args.unit] if args.unit else None)
            print(f"Validated {len(rows)} Unit Evidence record(s)")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
