# Spec: `KOALA_BASE_URL` env variable

## Goal
Introduce a `KOALA_BASE_URL` environment variable so Koala maintainers can point agents at a non-prod host (e.g. `https://staging.koala.science`) without leaking the staging URL into the public repo or affecting contestants — the shipped default must remain `https://koala.science`.

## Context
The repo currently hardcodes `koala.science` in 13 places across three layers:
- **Runtime clients** that talk to Koala: `agent_definition/harness/koala.py`, `cli/reva/backends.py` (codex MCP config), `cli/reva/config.py` (agent's self-registration initial prompt).
- **Agent-facing prompt content** that gets compiled into each agent's system prompt: `agent_definition/GLOBAL_RULES.md`, `agent_definition/platform_skills.md`, `agent_definition/harness/tools.py` (docstrings).
- **Human-facing docs / dev-time config**: `README.md`, `cli/architecture.md`, `.claude/settings.json`, `tests/test_config.py`.

`reva` (the CLI) spawns agents in tmux sessions. Agent processes inherit the parent environment, so env vars set in `reva`'s shell reach each agent. `.env` is not currently auto-loaded — `python-dotenv` is not a dependency.

Agent-facing prompt content is assembled by `cli/reva/compiler.py::compile_prompt` from raw file reads (`_read(global_rules_path)` etc.) with no templating — so URL substitution must happen either (a) at compile time by running `.format()` or `.replace()` on the text, or (b) by putting a placeholder token in the source files.

## Requirements

1. **Env var + default.** Introduce `KOALA_BASE_URL`, default `https://koala.science` (no trailing slash). Central accessor: `reva.env.koala_base_url() -> str` that reads the env once and returns it. All code that needs the URL imports this accessor. Skill/MCP paths concatenate: `f"{base}/skill.md"`, `f"{base}/mcp"`, `f"{base}/api/v1/..."`.

2. **`.env` auto-loading.** Add `python-dotenv>=1.0` to `cli/pyproject.toml`. In `reva/cli.py` (before any subcommand runs), load `.env` from the project root via `find_config`'s resolved `project_root` — so `KOALA_BASE_URL` in `.env` is picked up automatically. Document in `.env.template`.

3. **Runtime client swaps.**
   - `agent_definition/harness/koala.py`: replace the module-level `MCP_URL` constant with a call to the accessor; `KoalaClient` reads it lazily at construction.
   - `cli/reva/backends.py`: compute `_CODEX_KOALA_MCP_CONFIG` from the accessor at module import time is fine (env is set before import in CLI flow), OR build it inside `get_backend()`. Pick whichever avoids import-order bugs.
   - `cli/reva/config.py`: `DEFAULT_INITIAL_PROMPT` becomes a template with `{koala_base_url}` placeholder; `RevaConfig` gains `koala_base_url: str` populated from the accessor; the rendering code in `cli.py` passes it into `.format(...)` alongside existing fields.

4. **Agent-facing prompt content.**
   - `agent_definition/GLOBAL_RULES.md` and `agent_definition/platform_skills.md`: replace literal URLs with the token `{KOALA_BASE_URL}` (curly-braced so it survives markdown rendering). `compile_prompt` substitutes the token after reading each file.
   - `agent_definition/harness/tools.py`: same token substitution on docstrings is overkill — leave as literal prod URLs since these docstrings are for human reading, not the agent's prompt. (Verify this file is not included in any compiled prompt.)

5. **Human-facing docs NOT templated.**
   - `README.md` and `cli/architecture.md`: leave as literal `https://koala.science` — these are for contestants who will always use prod. The README should gain a short "Maintainers: staging" note pointing at `KOALA_BASE_URL`.

6. **`.claude/settings.json`** — static JSON, cannot read env vars. Keep the prod URL committed; document in README that maintainers can drop a gitignored `.claude/settings.local.json` with the staging MCP URL for their own dev-time Claude Code sessions. `.gitignore` already ignores the whole `.claude/settings.local.json` (verify).

7. **Tests.**
   - `tests/test_config.py::test_default_initial_prompt_contains_koala_science` — update to assert that the prompt contains `{koala_base_url}` unformatted, and that after formatting with `KOALA_BASE_URL` it contains the resolved host.
   - New `tests/test_env.py`: `test_koala_base_url_default()` asserts `https://koala.science` when env unset; `test_koala_base_url_override()` asserts override when env set; `test_koala_base_url_no_trailing_slash()` asserts trailing-slash stripping if we choose to normalize (see open question below).
   - New `tests/test_compiler.py` (or extend existing): `test_compile_prompt_substitutes_koala_base_url` asserts `{KOALA_BASE_URL}` in source files is replaced in the compiled prompt.

## Constraints
- **Shipped default must be `https://koala.science`.** No staging URL appears in any committed file.
- **No new hard requirement on contestants.** An unset `KOALA_BASE_URL` must behave identically to today.
- **No breaking CLI changes.** Existing `reva` commands keep working.
- **No refactor sprawl.** Touch only the files named above. Don't rename `COALESCENCE_API_KEY` (separate cleanup).
- **Backwards compat for `.env`.** Existing `.env` files without `KOALA_BASE_URL` must still work.

## Test Plan
Files to write/modify:
- `tests/test_env.py` (new): default + override behavior of `koala_base_url()`.
- `tests/test_config.py`: update `koala.science` assertion to use the new templated form.
- `tests/test_compiler.py` (new or extended): token substitution in compiled prompt.

Mocks: `monkeypatch.setenv("KOALA_BASE_URL", ...)`; no network calls required.

Key assertions:
- `koala_base_url()` returns `https://koala.science` with env unset.
- `koala_base_url()` returns overridden value with env set; trailing slash stripped if present.
- Compiled prompt has no `{KOALA_BASE_URL}` placeholder left after compilation.
- `DEFAULT_INITIAL_PROMPT` contains `{koala_base_url}` before formatting, and the resolved URL after.

## Acceptance Criteria

- [ ] `KOALA_BASE_URL` env var is read in exactly one place (`reva/env.py`) and every runtime URL is derived from that accessor.
- [ ] `uv run pytest` passes with env unset, and with `KOALA_BASE_URL=https://staging.koala.science` set.
- [ ] `grep -rn "https://koala.science" agent_definition/ cli/reva/` returns zero hits (all runtime + prompt-content files go through the accessor or `{KOALA_BASE_URL}` token).
- [ ] `grep -rn "staging" .` returns only doc mentions — no committed `staging.koala.science` URL anywhere.
- [ ] Launching an agent with `KOALA_BASE_URL=https://staging.koala.science reva create --name t1 && reva launch --name t1` produces an `initial_prompt.txt` containing `staging.koala.science` and no bare `koala.science`.
- [ ] With env unset, the same launch produces an `initial_prompt.txt` containing `https://koala.science` exactly as today.
- [ ] `.env.template` documents `KOALA_BASE_URL` with default value and a warning to leave it unless you're a maintainer.
- [ ] README has a short "Maintainers: pointing at staging" note covering the env var + the `.claude/settings.local.json` override for dev-time Claude Code.

## Open questions (resolve before implementation)

1. **Normalization.** Strip trailing slash on read, or document "no trailing slash"? Recommendation: strip it — cheap and eliminates a class of bugs.
2. **`agent_definition/harness/tools.py` docstrings.** Template them, or leave as prod literals? Recommendation: leave — they're not in any compiled prompt.
3. **`.claude/settings.local.json` override approach** — acceptable, or do you want a script that generates `.claude/settings.json` from a template?
