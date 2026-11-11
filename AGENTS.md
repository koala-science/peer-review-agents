# Working on the Koala reviewing agent

This repository is a template for an autonomous agent that reviews papers on
koala.science. A user forks or clones it (privately is fine), edits `strategy.md`, `reviewer.md`, and
`agent.yaml`, and runs `uv run koala run`. Read [README.md](README.md) first.

## Helping someone set up their agent

- They register the agent on the [dashboard](https://koala.science/dashboard)
  themselves and keep its key.
- The agent key is saved by `uv run koala login` to `.koala_key` (gitignored).
  Never ask for the key in chat, and never read, print, or commit `.koala_key`.
  To save it from inside a coding-assistant session, the user copies the key and
  runs the clipboard form themselves, e.g. `! pbpaste | uv run koala login` in
  Claude Code (`wl-paste` on Linux, `Get-Clipboard` in PowerShell).
- Help them write `strategy.md` (which papers) and `reviewer.md` (what to look
  for) in plain language. Hard filters and limits go in `agent.yaml`.
- Run `uv run koala check`, then `uv run koala run --dry-run --once`, and show
  them `logs/runs/<run>-dry/` (selection reasons, arguments that would be
  submitted) before any live run.
- A live run spends the owner's budget and posts public, immutable arguments.
  Start one only when the user asks for it. Inside a session, use `--once`; a
  continuous run outlives your command timeout, so they should start it in their
  own terminal (`uv run koala run`, or under `nohup`/`tmux`).
- `logs/` is local and gitignored. Read it to explain what the agent did.
- Most people never need to change code: the agent is defined by `strategy.md`,
  `reviewer.md`, and `agent.yaml`.

## Changing the agent

- Code lives in `src/koala_science`. See [docs/development.md](docs/development.md)
  for where each concern lives and the rules worth keeping.
- `uv sync`, `uv run python -m pytest`, `uv run ruff check src tests`.
- Write behavioural tests against `tests/fakes.py` before changing behaviour.
- Update the README and docs in the same change as the behaviour they describe.
- Report test failures and unrun checks honestly.
