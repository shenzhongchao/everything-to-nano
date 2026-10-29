"""Regression tests for evidence-backed Unit 5 learning outputs."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


UNIT_DIR = Path(__file__).resolve().parents[1] / "unit-5-tools-sandbox"


def load_unit5():
    spec = importlib.util.spec_from_file_location("tools_sandbox_demo", UNIT_DIR / "tools_sandbox_demo.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_learning():
    load_unit5()
    spec = importlib.util.spec_from_file_location("learning_experience", UNIT_DIR / "learning_experience.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_graph_events_follow_real_model_route_tool_callbacks(tmp_path):
    module = load_unit5()
    sandbox = module.DockerSandbox(
        sandbox_id="teaching",
        user_data_root=tmp_path,
        runner=lambda command, **_: module.CompletedSandboxProcess(
            stdout="ACTUAL_TOOL_RESULT\n", stderr="", returncode=0
        ),
    )
    model = module.ScriptedToolCallingModel(
        tool_name="bash", tool_args={"command": "echo ACTUAL_TOOL_RESULT"}, final_text="DONE"
    )
    agent = module.run_langgraph_sandbox_demo(
        prompt="Run a command", sandbox=sandbox, model=model, capture_events=True
    )
    assert [event["kind"] for event in agent["execution_events"]] == [
        "model", "route", "tool", "model", "route"
    ]
    assert agent["execution_events"][2]["output"] == "ACTUAL_TOOL_RESULT"
    assert agent["tool_trace"][0]["output"] == "ACTUAL_TOOL_RESULT"
    assert agent["execution_events"][-1]["output"]["next_node"] == "END"
    assert agent["final_message"] == "DONE"


def test_original_default_api_has_no_extra_trace(tmp_path):
    module = load_unit5()
    sandbox = module.DockerSandbox(
        sandbox_id="teaching", user_data_root=tmp_path,
        runner=lambda *_args, **_kwargs: module.CompletedSandboxProcess("OK", "", 0),
    )
    model = module.ScriptedToolCallingModel("bash", {"command": "echo OK"}, "DONE")
    agent = module.run_langgraph_sandbox_demo(prompt="run", sandbox=sandbox, model=model)
    assert "execution_events" not in agent


def test_no_tool_experiment_skips_tool_node(tmp_path):
    module = load_learning()
    with module.tempfile.TemporaryDirectory() as folder:
        sandbox = module.LocalSandbox("no-tool")
        runtime = module.build_tool_runtime(
            thread_id="no-tool", sandbox=sandbox, user_data_root=folder, sandbox_mode="local"
        )
        result = module.run_langgraph_sandbox_demo(
            prompt="no tool", sandbox=sandbox, model=module.NoToolModel(),
            runtime=runtime, capture_events=True
        )
    assert [event["kind"] for event in result["execution_events"]] == ["model", "route"]
    assert result["tool_trace"] == []
    assert result["execution_events"][-1]["output"]["next_node"] == "END"


def test_generate_offline_learning_artifacts(tmp_path):
    module = load_learning()
    files = module.generate(tmp_path, no_am=True)
    assert set(files) == {"trace", "replay", "lesson_markdown"}
    doc = json.loads(files["trace"].read_text(encoding="utf-8"))
    assert doc["provenance"]["mode"] == "offline-scripted-langgraph"
    assert len(doc["baseline"]["tool_trace"]) == 1
    assert len(doc["no_tool"]["tool_trace"]) == 0
    assert [event["kind"] for event in doc["baseline"]["events"]] == ["model", "route", "tool", "model", "route"]
    page = files["replay"].read_text(encoding="utf-8")
    assert "<!--TRACE_DATA-->" not in page
    assert "ACTUAL_TOOL_RESULT" not in page
    assert "查看实际运行结果" in page
    assert "没有 tool_calls" in page
    md = files["lesson_markdown"].read_text(encoding="utf-8")
    assert "src=unit-5-tools-sandbox/tools_sandbox_demo.py" in md


def test_embedded_json_escapes_script_breakout():
    module = load_learning()
    result = module.safe_script_json({"value": "</script><script>alert(1)</script>"})
    assert "</script>" not in result
    assert json.loads(result)["value"] == "</script><script>alert(1)</script>"