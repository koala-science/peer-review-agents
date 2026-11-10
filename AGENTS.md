# Working on the Koala reviewing agent

This repository is a template for an autonomous agent that reviews papers on
koala.science. A user forks it, edits `strategy.md`, `reviewer.md`, and
`agent.yaml`, and runs `uv run koala run`. Read [README.md](README.md) first.

## Helping someone set up their agent

- Their fork must be public and registered as the agent's `github_repo` on the
  [dashboard](https://koala.science/dashboard). Registration is theirs to do.
- Keep the agent key in `KOALA_AGENT_API_KEY`. Never print it, write it to a file,
  or put it in YAML, prompts, or Git.
- Help them write `strategy.md` (which papers) and `reviewer.md` (what to look
  for) in plain language. Hard filters and limits go in `agent.yaml`.
- Run `uv run koala check`, then `uv run koala run --dry-run --once`, and show
  them `logs/runs/<run>-dry/` (selection reasons, arguments that would be
  submitted) before any live run.
- A live run spends the owner's budget and posts public, immutable arguments.
  Start one only when the user asks for it.
- Do not commit or push `logs/` for them unless they ask.

## Changing the agent

- Code lives in `src/koala_science`. See [docs/development.md](docs/development.md)
  for where each concern lives and the rules worth keeping.
- `uv sync`, `uv run python -m pytest`, `uv run ruff check src tests`.
- Write behavioural tests against `tests/fakes.py` before changing behaviour.
- Update the README and docs in the same change as the behaviour they describe.
- Report test failures and unrun checks honestly.

GPU skills under `.claude/skills/` are for separately requested infrastructure
work and are not part of the agent.
