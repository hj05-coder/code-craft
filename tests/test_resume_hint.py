import subprocess

from codecraft import cli


def test_resume_hint_uses_current_python_without_path_install(monkeypatch):
    monkeypatch.setattr(cli.sys, "executable", r"C:\Program Files\Python\python.exe")
    monkeypatch.setattr(cli.os, "name", "nt")
    expected = subprocess.list2cmdline([
        cli.sys.executable, "-m", "codecraft", "--resume", "session-123",
    ])
    assert cli.resume_command("session-123") == expected
