from pathlib import Path

import pytest

from codecraft.core.model_output import parse
from codecraft import Codecraft, SessionStore, WorkspaceContext
from codecraft.testing import ScriptedModelClient


FIXTURES = Path(__file__).parent / "fixtures" / "dsml"


@pytest.mark.parametrize("name,count", [("search.txt", 1), ("batch.txt", 2), ("wrapped.txt", 1)])
def test_replay_captured_dsml(name, count):
    kind, payload = parse((FIXTURES / name).read_text(encoding="utf-8"))
    assert kind == ("tool" if count == 1 else "tools")
    tools = [payload] if kind == "tool" else payload
    assert len(tools) == count
    assert all(isinstance(t["args"], dict) for t in tools)
    if name == "wrapped.txt":
        assert tools[0]["name"] == "search"
        assert tools[0]["args"]["path"] == "codecraft"
        assert "args" not in tools[0]["args"]


def test_captured_dsml_runs_through_engine(tmp_path):
    (tmp_path / "codecraft").mkdir()
    client = ScriptedModelClient([
        (FIXTURES / "search.txt").read_text(encoding="utf-8"),
        "<final>Memory explained.</final>",
    ])
    agent = Codecraft(model_client=client, workspace=WorkspaceContext.build(tmp_path),
                     session_store=SessionStore(tmp_path / ".codecraft/sessions"),
                     auto_dream=False)
    assert agent.ask("explain memory") == "Memory explained."
    assert agent.current_task_state.tool_steps == 1
    assert any(m.get("name") == "search" for m in agent.session["history"])
    assert not list((agent.current_run_dir / "artifacts").glob("malformed-model-*.txt"))


MARKER = "\uff5c\uff5cDSML\uff5c\uff5c"


def dsml_call(name, parameters):
    return (f'<{MARKER} calls><{MARKER} invoke name="{name}">'
            + parameters + f'</{MARKER} invoke></{MARKER} calls>')


def param(name, value, string="true"):
    return f'<{MARKER} parameter name="{name}" string="{string}">{value}</{MARKER} parameter>'


def test_dsml_preserves_string_and_typed_json_values():
    raw = dsml_call("read_file", param("path", "源码/a&b.py")
                    + param("start", "2", "false") + param("end", "8", "false"))
    assert parse(raw) == ("tool", {"name": "read_file", "args": {
        "path": "源码/a&b.py", "start": 2, "end": 8}})


@pytest.mark.parametrize("raw", [
    dsml_call("search", param("pattern", "memory"))[:-5],
    dsml_call("search", param("args", "{broken}", "false")),
    dsml_call("search", param("path", "a") + param("path", "b")),
    dsml_call("search", param("path", "a", "unknown")),
    dsml_call("search", param("name", "write_file") + param("args", "{}", "false")),
    dsml_call("search", param("args", "[]", "false")),
    dsml_call("search", param("pattern", "memory")) + "unexpected trailing content",
    f'<{MARKER} calls></{MARKER} calls>',
    # A valid first tool must not execute if the rest of the batch is broken.
    dsml_call("list_files", "").replace(f'</{MARKER} calls>',
        f'<{MARKER} invoke name="search">broken</{MARKER} calls>'),
])
def test_malformed_dsml_is_rejected_as_a_whole(raw):
    assert parse(raw)[0] == "retry"


@pytest.mark.parametrize("name,args,code", [
    ("write_file", param("path", "outside.txt") + param("content", "no"), "write_scope_mismatch"),
    ("run_shell", param("command", "echo must-not-run"), "tool_not_allowed"),
    ("unknown_tool", "", "unknown_tool"),
    ("read_file", param("path", "../outside.txt"), "invalid_arguments"),
])
def test_dsml_uses_existing_worker_guardrails(tmp_path, name, args, code):
    agent = Codecraft(model_client=ScriptedModelClient([]),
                     workspace=WorkspaceContext.build(tmp_path),
                     session_store=SessionStore(tmp_path / ".codecraft/sessions"),
                     write_scope=["allowed"], auto_dream=False)
    agent.set_tool_profile("worker")
    kind, payload = parse(dsml_call(name, args))
    assert kind == "tool"
    agent.run_tool(payload["name"], payload["args"])
    assert agent._last_tool_result_metadata["tool_error_code"] == code
    assert not (tmp_path / "outside.txt").exists()


def test_final_can_describe_dsml_without_executing_it():
    answer = "Example: " + dsml_call("run_shell", param("command", "echo no"))
    assert parse("<final>" + answer + "</final>") == ("final", answer)


@pytest.mark.parametrize("name", ["read_file", "list_files"])
def test_mixed_tool_opening_and_dsml_closing_is_rejected(name):
    raw = ('<tool>{"name":"' + name + '","args":{"path":"README.md"}}'
           + f'</{MARKER} parameter>\n</{MARKER} invoke>\n</{MARKER} calls>')
    assert parse(raw)[0] == "retry"
    assert "matching opening and closing tags" in parse(raw)[1]
