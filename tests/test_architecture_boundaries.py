from pathlib import Path


def test_core_modules_stay_below_entropy_budget():
    root = Path(__file__).resolve().parents[1]
    budgets = {
        "codecraft/core/runtime.py": 950,
        "codecraft/core/runtime_events.py": 90,
        "codecraft/core/runtime_consumers.py": 90,
        "codecraft/core/artifacts.py": 130,
        "codecraft/core/task_state.py": 140,
        "codecraft/core/todo_ledger.py": 120,
        "codecraft/core/worker_manager.py": 220,
        "codecraft/core/context_manager.py": 420,
        "codecraft/core/context_usage.py": 120,
        "codecraft/core/compact.py": 180,
        "codecraft/core/engine.py": 470,
        "codecraft/core/model_errors.py": 100,
        "codecraft/core/permissions.py": 140,
        "codecraft/core/tool_policy.py": 90,
        "codecraft/core/plan_mode.py": 140,
        "codecraft/core/tool_executor.py": 181,
        "codecraft/core/tool_profiles.py": 80,
        "codecraft/core/turn_history.py": 250,
        "codecraft/features/skills.py": 220,
        "codecraft/features/skills_bundled.py": 120,
        "codecraft/features/skills_runtime.py": 140,
        "codecraft/tools/registry.py": 360,
        "codecraft/tools/todos.py": 80,
        "codecraft/tools/agents.py": 90,
    }

    for relative_path, max_lines in budgets.items():
        line_count = len((root / relative_path).read_text(encoding="utf-8").splitlines())
        assert line_count <= max_lines, f"{relative_path} has {line_count} lines, budget is {max_lines}"
