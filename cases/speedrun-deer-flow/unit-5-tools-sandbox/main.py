from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools_sandbox_demo import run_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use a real OpenAI-compatible LLM and Docker sandbox.",
    )
    parser.add_argument(
        "--learn",
        action="store_true",
        help="Generate real execution traces, replay.html and an optional am-rendered guide.",
    )
    args = parser.parse_args()
    if args.learn:
        if args.live:
            parser.error("--learn only supports the deterministic offline teaching mode")
        from learning_experience import generate
        artifacts = generate(Path(__file__).resolve().parent / "learning-output")
        for label, path in artifacts.items():
            print(f"{label}: {path}")
        if "lesson_html" not in artifacts:
            print("Tip: install answer-me-with-html's am CLI to render lesson.html too")
    else:
        print(json.dumps(run_demo(live=args.live), indent=2))
