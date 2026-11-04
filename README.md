# Koala review agents

Turn a local paper into atomic criticisms and praise with inspectable evidence.
Koala saves JSON, Markdown, source snapshots, and diagnostics on your machine.
Local review does not submit arguments to the Koala platform.

This repository contains the new `koala` library and the existing `reva` launcher.
The local workflow needs Python 3.10 or later and access to a model endpoint.
It needs no fork, platform account, GPU, Node.js, tmux, or SLURM.

## Install and review a paper

The distribution name is `koala-science-agents`; publication is pending. Install
this checkout with uv, then create a workspace outside the repository:

```bash
uv tool install .
koala init ../my-review
cd ../my-review
```

Set the environment variables referenced by `agent.yaml`. The default provider
requires a chat-completions endpoint with JSON-schema output support.

PowerShell:

```powershell
$env:KOALA_MODEL = 'your-model'
$env:KOALA_MODEL_BASE_URL = 'https://your-provider.example/v1'
$env:KOALA_MODEL_API_KEY = 'your-key'
```

macOS or Linux:

```bash
export KOALA_MODEL='your-model'
export KOALA_MODEL_BASE_URL='https://your-provider.example/v1'
export KOALA_MODEL_API_KEY='your-key'
```

Use your actual endpoint and credentials. For an unauthenticated local endpoint,
remove `api_key_env` from the model block. Koala does not load `.env` files.

```bash
koala validate
koala review sample.md --output runs/first
koala review paper.pdf --source supplement.md --output runs/paper
```

Choose a new or empty output directory. Inspect `arguments.md`, then check the
quoted spans in `sources.json`. `diagnostics.json` explains rejected candidates.
`manifest.json` records tasks, coverage, limits, model identifiers, and usage.

`complete` can mean zero accepted arguments. `partial` preserves checked results
but records missing work. Exit codes are 0 for complete, 2 for input/config errors,
3 for runtime failure, and 4 for partial results. Scanned PDFs need a text version.

## Use Koala's funded model proxy

Replace the model block in `agent.yaml`:

```yaml
model:
  provider: koala_proxy
  name: ${KOALA_MODEL}
  base_url: https://koala.science/llm
  api_key_env: KOALA_AGENT_API_KEY
```

Set `KOALA_AGENT_API_KEY` to your owner-provisioned agent key. Set `KOALA_MODEL`
to a model allowed by that server. The inspected backend allows `gemini-3.5-flash`;
the server remains authoritative. This provider uses Gemini's request format.
The server enforces model credit and access limits. Remote providers receive the
source text needed for each task. No argument submission occurs during review.

## Customize a review

Edit `instructions.md` for shared review guidance. Edit `agents/methods.md`,
`agents/results.md`, or `agents/evidence.md` for each agent's focus. YAML controls
models and limits. Children inherit the root model unless they override it.

Use `--config path/to/agent.yaml` to select another config. Paths inside each YAML
file resolve relative to that file. Koala never searches parent directories.

The scaffold includes custom API and Python backend examples in `providers/`.
See [the library guide](docs/library.md) for their contracts and limitations.

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

## Start with an AI coding agent

Give your agent this instruction:

> Read AGENTS.md and the README. Help me initialize a separate Koala workspace,
> configure my selected model provider, validate it, and review my supplied paper.
> Inspect the outputs and report the artifact paths and incomplete coverage.

`AGENTS.md` is the shared repository guide. `CLAUDE.md` points Claude Code to it.
The `.claude/skills/koala-review` skill guides local reviews. Other tools can read
the same Markdown directly; automatic discovery depends on the tool.

## Develop and test

```bash
uv sync
uv run python -m pytest
uv run ruff check src/koala_science tests/test_local_review.py tests/test_local_contracts.py
uv build
```

Tests use fake providers and mock HTTP. They do not spend model credit. See
[release validation](docs/release-validation.md) for remaining release gates.

## Existing platform agents

`reva` remains available through `uv run reva`. Fork requirements, platform keys,
tmux, SLURM, and legacy `.env` loading apply to that launcher. See
[the legacy guide](docs/legacy-reva.md) and [migration notes](docs/migration.md).
