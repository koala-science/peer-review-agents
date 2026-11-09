# Develop Koala

Run development commands from the repository root.

## Develop and test

```bash
uv sync
uv run python -m pytest
uv run ruff check src/koala_science examples tests/test_local_review.py tests/test_local_contracts.py tests/test_review_hardening.py
uv build
uv run python tests/wheel_smoke.py
```

Tests use fake providers and mock HTTP. They do not spend model credit. See
[release validation](release-validation.md) for remaining release gates.

Run one heavy test or build process at a time. The wheel smoke check installs the
built wheel into an isolated environment outside the checkout and exercises its imports and templates.
Legacy shell and permission tests require POSIX facilities. Report unsupported Windows checks explicitly.
Read [AGENTS.md](../AGENTS.md) before edits and [library contracts](library.md) before changing runtime behavior.
Edit examples in the root `examples/` directory. The wheel packages them as template resources.

## Python API

Install the checkout in your Python project with `uv add /path/to/peer-review-agents`.

```python
import koala_science as koala

agent = koala.Agent.from_config("agent.yaml")
result = agent.review("paper.pdf", sources=["supplement.md"])
result.save("runs/first")
for argument in result.arguments:
    print(argument.statement)
```

Inside notebooks or another event loop, use `await agent.areview("paper.pdf")`.
