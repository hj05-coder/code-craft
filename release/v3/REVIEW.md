# Codecraft v3 review pack

## Project pitch

Codecraft is a small local coding agent that turns one user request into a bounded
repository session: it builds context from the workspace, calls a provider,
executes approved tools, and persists the session locally.

## Architecture map

- `Codecraft` owns session state, memory, tools, and workspace safety.
- `Engine` drives the model/tool/final-answer loop.
- `SessionEventBus` writes the durable session timeline.
- `RunStore` keeps per-run traces, task state, and reports.
- `WorkerManager` keeps subagent task ids, continuation state, notifications,
  and write-scope boundaries.
- Provider clients live behind one `complete()` contract.

## Harness boundaries

The v3 harness turns one user request into a verifiable local session. Every
turn gets a run id, task id, attempt count, tool step count, stop reason, and
final answer. That task state is written beside the run trace so failures can
be inspected after the process exits.

The stable boundaries are:

- Engine: owns the model/tool/final-answer loop.
- Provider: exposes a single text completion contract.
- Tools: enforce workspace paths, approval policy, and write safety.
- Session event bus: records the user-visible session timeline.
- Plan mode: constrains planning turns to the active plan artifact.
- Worker manager: owns bounded subagent lifecycle and write scopes.

## Benchmark evidence

Use the test suite as the current acceptance floor. Real-session behavior should
be validated through persisted `.codecraft/sessions/*.json` and
`.codecraft/sessions/*.events.jsonl` artifacts before treating a runtime change as
done.

## Sample run artifact list

- `.codecraft/sessions/<session_id>.json`
- `.codecraft/sessions/<session_id>.events.jsonl`
- `.codecraft/runs/<run_id>/task_state.json`
- `.codecraft/runs/<run_id>/trace.jsonl`
- `.codecraft/runs/<run_id>/report.json`
