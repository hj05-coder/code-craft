from types import SimpleNamespace

import pytest

from codecraft.core.session_store import SessionStore
from codecraft.cli import _format_history


def test_history_preview_is_short_single_line_and_turns_are_not_messages(tmp_path):
    store = SessionStore(tmp_path)
    store.save({"id": "one", "history": [
        {"role": "user", "content": "question"},
        {"role": "tool", "content": "observation"},
        {"role": "user", "kind": "protocol_correction", "content": "fix format"},
        {"role": "user", "content": "<task-notification>done</task-notification>"},
        {"role": "assistant", "content": "# Title\n\n**bold** `code`\n" + "x" * 200},
    ]})
    row = store.list_sessions()[0]
    assert row["history_count"] == 5
    assert row["turn_count"] == 1
    assert "\n" not in row["last_final_answer"]
    assert len(row["last_final_answer"]) <= 80
    assert "truncated" not in row["last_final_answer"]
    output = _format_history(SimpleNamespace(session_store=store))
    assert len(output.splitlines()) == 1
    assert "turns=1" in output


@pytest.mark.asyncio
async def test_tui_history_is_literal_not_markdown(tmp_path):
    from codecraft import Codecraft, WorkspaceContext
    from codecraft.testing import ScriptedModelClient
    from codecraft.tui.app import CodecraftTuiApp
    from codecraft.tui.widgets import AssistantMessage
    from textual.widgets import Markdown

    store = SessionStore(tmp_path / ".codecraft/sessions")
    agent = Codecraft(model_client=ScriptedModelClient([]),
                     workspace=WorkspaceContext.build(tmp_path), session_store=store,
                     auto_dream=False)
    store.save({"id": "example", "history": [
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "**bold** `path` [text] # Title"},
    ]})
    app = CodecraftTuiApp(agent)
    async with app.run_test() as pilot:
        app._handle_command("/history")
        await pilot.pause()
        message = list(app.query(AssistantMessage))[-1]
        assert not list(message.query(Markdown))
        assert "**bold** `path`" in message.content
        assert len(message.content.splitlines()) == 2
