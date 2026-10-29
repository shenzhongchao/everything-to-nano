"""Generate an evidence-backed learning experience for DeerFlow Unit 5.

Run from anywhere: python unit-5-tools-sandbox/learning_experience.py
The replay page is self-contained. The optional `am` CLI renders lesson.md into
an additional visual explainer; the original runnable unit remains unchanged.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage

from tools_sandbox_demo import (
    LocalSandbox,
    build_tool_runtime,
    run_demo,
    run_langgraph_sandbox_demo,
)

UNIT_DIR = Path(__file__).resolve().parent
SPEEDRUN_ROOT = UNIT_DIR.parent
TEMPLATE = UNIT_DIR / "trace_viewer_template.html"


class NoToolModel:
    """Controlled experiment: the model directly answers, without a tool call."""

    def bind_tools(self, _tools: list[object]) -> "NoToolModel":
        return self

    def invoke(self, _messages: list[object]) -> AIMessage:
        return AIMessage(content="NO_TOOL_CALL: no sandbox command was requested")


def build_traces() -> dict[str, object]:
    """Capture actual callbacks from two graph invocations, never invented steps."""
    baseline = run_demo(capture_events=True)
    if baseline["mode"] != "offline-scripted-langgraph":
        raise RuntimeError("Learning traces must come from the offline scripted mode")
    with tempfile.TemporaryDirectory(prefix="deerflow-unit5-experiment-") as directory:
        runtime = build_tool_runtime(
            thread_id="no-tool-experiment",
            sandbox=LocalSandbox("no-tool-local"),
            user_data_root=Path(directory) / "user-data",
            sandbox_mode="local",
        )
        changed = run_langgraph_sandbox_demo(
            prompt="Answer without calling any tools.",
            sandbox=runtime.provider.get("no-tool-local"),
            model=NoToolModel(),
            runtime=runtime,
            capture_events=True,
        )
    baseline_trace = baseline["agent"]
    for label, result in (("baseline", baseline_trace), ("no_tool", changed)):
        if not result.get("execution_events"):
            raise RuntimeError(f"No real execution events were captured for {label}")
    return {
        "schema_version": 1,
        "title": "DeerFlow Unit 5 · Run / See / Explain / Change",
        "provenance": {
            "mode": "offline-scripted-langgraph",
            "model": "scripted stub (not a live LLM)",
            "sandbox": "local teaching sandbox (not Docker)",
            "source": "unit-5-tools-sandbox/tools_sandbox_demo.py",
            "simplifications": "../SIMPLIFICATIONS.md",
            "note": "All steps are captured during actual LangGraph executions. This is a simplified teaching implementation, not a recording of production DeerFlow.",
        },
        "baseline": {
            "events": baseline_trace["execution_events"],
            "tool_trace": baseline_trace["tool_trace"],
            "final_message": baseline_trace["final_message"],
        },
        "no_tool": {
            "events": changed["execution_events"],
            "tool_trace": changed["tool_trace"],
            "final_message": changed["final_message"],
        },
    }


def source_excerpt(func_name: str, context: int = 15) -> str:
    """Use existing source at render time, not copied or made-up code."""
    lines = (UNIT_DIR / "tools_sandbox_demo.py").read_text(encoding="utf-8").splitlines()
    match = next((n for n, line in enumerate(lines, 1) if re.match(r"\s+def " + re.escape(func_name) + r"\(", line)), None)
    if match is None:
        raise ValueError(f"Missing source function: {func_name}")
    end = min(match + context, len(lines))
    path = "unit-5-tools-sandbox/tools_sandbox_demo.py"
    return f"```python src={path} lines={match}-{end} hl={match}\n```"


def lesson_markdown(trace: dict[str, object]) -> str:
    events = trace["baseline"]["events"]
    rows = ["| 步骤 | 真实事件 | 下一步要观察什么 |", "|---|---|---|"]
    teaching = {
        "model": "模型返回 tool_calls 或最终答案",
        "route": "条件边按消息内容选择下一节点",
        "tool": "工具通过 runtime 派发，返回 ToolMessage",
    }
    for i, event in enumerate(events, 1):
        rows.append(f"| {i} | {event['title']} | {teaching[event['kind']]} |")
    return "\n".join([
        "---",
        "template: doc",
        "theme: blueprint",
        "title: DeerFlow Unit 5 · 模型如何安全使用工具",
        "subtitle: 从真实运行轨迹理解 LangGraph 的 model → tools → model 循环",
        "source: Code Speedrun · offline-scripted",
        "---",
        "这里的 trace 来自教学版 LangGraph 的真实执行。模型是固定输出的替身，sandbox 是本地教学环境；这**不是**真实 LLM + Docker 的生产录制。",
        "",
        "## A 一条消息怎样变成一次工具执行",
        "```flow LR",
        "(用户提问) -> 模型节点: HumanMessage",
        "模型节点 -> {有 tool_calls?}: AIMessage",
        "{有 tool_calls?} -> 工具节点: 有",
        "工具节点 -> Sandbox: runtime 派发",
        "Sandbox -> 工具节点: 执行结果",
        "工具节点 -> 模型节点: ToolMessage",
        "{有 tool_calls?} -> (结束): 无",
        "```",
        "",
        "## B 真实执行顺序",
        *rows,
        "",
        "## C 模型节点负责决策，不负责执行",
        source_excerpt("call_model", 9),
        "",
        "## D 工具节点把调用请求交给 runtime",
        source_excerpt("call_tools", 20),
        "",
        "## E 条件边什么时候结束循环",
        source_excerpt("next_step", 10),
        "",
        "## F 预测与验证",
        "**先预测：**如果模型完全不返回 `tool_calls`，graph 会不会进入 `tools` 节点？",
        "然后打开同目录 `replay.html`，做出预测，再查看第二次真实执行的轨迹。",
        "最后自己修改 `NoToolModel.invoke()`，重新运行生成脚本，观察轨迹变化。",
        "",
        "## G 哪些内容被简化了",
        "- 模型是 `ScriptedToolCallingModel`，结果固定且可复现。",
        "- 默认使用本地教学 sandbox，而不是 Docker。",
        "- 真实 DeerFlow 还有 middleware、checkpointer、streaming 与 provider 生命周期。",
        "- 对照项目根目录的 `SIMPLIFICATIONS.md`，不要将教学替身误认为原版实现。",
        "",
    ])


def safe_script_json(obj: dict[str, object]) -> str:
    """Prevent user-controlled trace text from ending the embedded script tag."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e"))


def render_replay(trace: dict[str, object]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    return template.replace("<!--TRACE_DATA-->", safe_script_json(trace))


def render_with_am(markdown: Path, target: Path, am_script: str | None) -> bool:
    if am_script:
        cli = [sys.executable, am_script] if am_script.endswith(".py") else (["node", am_script] if am_script.endswith(".mjs") else [am_script])
    else:
        am = shutil.which("am")
        if not am:
            return False
        cli = [am]
    subprocess.run(
        cli + ["render", str(markdown), "-o", str(target), "--no-open"],
        cwd=SPEEDRUN_ROOT,
        check=True,
        timeout=90,
    )
    if not target.is_file():
        raise RuntimeError("HTML rendering CLI reported success but no file was created")
    return True


def generate(output: Path, am_script: str | None = None, no_am: bool = False) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    trace = build_traces()
    trace_path = output / "trace.json"
    markdown_path = output / "lesson.md"
    replay_path = output / "replay.html"
    html_path = output / "lesson.html"
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(lesson_markdown(trace), encoding="utf-8")
    replay_path.write_text(render_replay(trace), encoding="utf-8")
    files = {"trace": trace_path, "replay": replay_path, "lesson_markdown": markdown_path}
    if not no_am:
        try:
            if render_with_am(markdown_path, html_path, am_script):
                files["lesson_html"] = html_path
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            if am_script:
                raise  # Explicit --am errors should be visible to the caller.
            print(f"Optional am renderer failed ({error}); replay.html is still ready", file=sys.stderr)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=UNIT_DIR / "learning-output", help="Output folder")
    parser.add_argument("--am", help="Path to answer-me-with-html's am.mjs or am executable (optional)")
    parser.add_argument("--no-am", action="store_true", help="Skip optional answer-me-with-html rendering")
    args = parser.parse_args()
    if args.am and args.no_am:
        parser.error("--am and --no-am cannot be used together")
    files = generate(args.out.resolve(), am_script=args.am, no_am=args.no_am)
    for label, path in files.items():
        print(f"{label}: {path}")
    if "lesson_html" not in files:
        print("Optional: install answer-me-with-html and rerun to also generate lesson.html")


if __name__ == "__main__":
    main()