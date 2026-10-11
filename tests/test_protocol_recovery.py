import json

from codecraft import Codecraft, SessionStore, WorkspaceContext
from codecraft.testing import ScriptedModelClient
from codecraft.core.model_output import retry_notice


def test_malformed_output_stops_early_and_preserves_evidence(tmp_path):
    client = ScriptedModelClient(["untagged response"] * 60)
    agent = Codecraft(model_client=client, workspace=WorkspaceContext.build(tmp_path),
                     session_store=SessionStore(tmp_path / ".codecraft/sessions"),
                     max_steps=50, auto_dream=False)
    events = list(agent.engine.run_turn("explain the memory system"))
    assert len(client.prompts) == 3
    assert events[-1]["stop_reason"] == "retry_limit_reached"
    assert "输出格式" in events[-2]["content"]
    artifacts = list((agent.current_run_dir / "artifacts").glob("malformed-model-*.txt"))
    assert len(artifacts) == 3
    assert artifacts[0].read_text(encoding="utf-8") == "untagged response"
    report = json.loads((agent.current_run_dir / "report.json").read_text(encoding="utf-8"))
    assert report["task_state"]["stop_reason"] == "retry_limit_reached"
    corrections = [m for m in agent.session["history"] if m.get("kind") == "protocol_correction"]
    assert corrections and all(m["role"] == "user" for m in corrections)


def test_retry_notice_keeps_tags_visible_in_markdown():
    notice = retry_notice("missing <tool> or <final> tag")
    assert "`<tool>`" in notice and "`<final>`" in notice


def test_protocol_errors_reset_after_valid_tool_and_recover(tmp_path):
    client = ScriptedModelClient([
        "bad one", "bad two",
        '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
        "bad three", "bad four", "<final>Recovered.</final>",
    ])
    agent = Codecraft(model_client=client, workspace=WorkspaceContext.build(tmp_path),
                     session_store=SessionStore(tmp_path / ".codecraft/sessions"),
                     max_steps=10, auto_dream=False)
    assert agent.ask("inspect") == "Recovered."
    assert len(client.prompts) == 6
    assert "bad one" not in client.prompts[1]
    assert "Your previous response could not be executed" in client.prompts[1]


def test_failed_protocol_evidence_redacts_environment_and_client_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret-from-environment")
    client = ScriptedModelClient(["secret-from-environment secret-from-client"] * 3)
    client.api_key = "secret-from-client"
    agent = Codecraft(model_client=client, workspace=WorkspaceContext.build(tmp_path),
                     session_store=SessionStore(tmp_path / ".codecraft/sessions"),
                     max_steps=50, auto_dream=False)
    agent.ask("inspect")
    for artifact in (agent.current_run_dir / "artifacts").glob("malformed-model-*.txt"):
        content = artifact.read_text(encoding="utf-8")
        assert "secret-from-environment" not in content
        assert "secret-from-client" not in content
        assert "<redacted>" in content
