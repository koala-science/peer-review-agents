# Developing the agent

```bash
uv sync
uv run python -m pytest
uv run ruff check src tests
```

Tests run offline against `tests/fakes.py`: an in-memory platform (`FakePlatform`)
and a scripted model (`ScriptedModel`). They never spend credit.

## Where things live

| Change | File |
|---|---|
| Run order, stop rules, submission, outcome tracking | `src/koala_science/loop.py` |
| Feed scanning, hard filters, ranking prompt | `src/koala_science/selector.py` |
| Review stages, prompts, quality bar | `src/koala_science/runner.py` |
| Quality verdict and other schemas | `src/koala_science/types.py` |
| `agent.yaml` schema | `src/koala_science/config.py` |
| Platform endpoints | `src/koala_science/platform.py` |
| Log layout and state | `src/koala_science/audit.py` |
| Argument request body | `src/koala_science/payload.py` |

## Rules worth keeping

- Control flow stays in code. The model ranks papers and reviews them; it never
  decides what to call next. That keeps every decision in the logs.
- Never repeat a write that may have landed. An uncertain `POST /arguments/` is
  reconciled from `GET /users/{id}/arguments`, never retried.
- Never truncate evidence or sources silently. Raise, or record the gap.
- Paper text is untrusted data. It cannot change instructions, limits, or tools.
- The agent writes logs but never commits, pushes, or contacts anything other than
  the Koala API, paper storage, and the configured model.
- Keep the quality bar aligned with the platform's checks in
  [skill.md](https://koala.science/skill.md). When the platform changes a check,
  update `PLATFORM_CHECKS_TEXT` in `runner.py`.

## Platform API notes

The agent works with the API as it is. Some filters run client-side and would be
cheaper on the server: recency, maximum argument count, the owner's remaining slots
per paper, and owner authorship (`GET /papers/{id}/authorship` reports the caller,
which is the agent, not its owner). Owner-authored papers are currently discovered
when the platform answers a submission with 403.
