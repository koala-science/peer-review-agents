# Spec: simplify agent model — drop self-registration, batch, and persona/role/interest composition

## Goal
Collapse the repo from "sample many agents from role × persona × interest axes and self-register them on the platform" to "hand-author at most 3 agents as single-file system prompts; the owner provisions API keys manually." Remove every abstraction that only makes sense at scale.

## Context
Today:
- `DEFAULT_INITIAL_PROMPT` in `cli/reva/config.py` walks the agent through POSTing to `/api/v1/auth/agents/register` with `owner_email`/`owner_name`/`owner_password`.
- `cli/reva/compiler.py` stitches system prompts from 7 component files (`GLOBAL_RULES` + `platform_skills` + role + methodology + interests + persona + format).
- `cli/reva/sampler.py` + `cli/reva/cli.py` sample combinations for batch creation.
- `reva batch create/launch/kill` operate on N agents at once.
- `agent_definition/` holds large subtrees of roles, personas, research interests, review methodologies, review formats — these existed to feed the compiler.
- The new reality: at most 3 agents per OpenReview ID, each hand-authored, API keys provisioned manually by the owner via the platform UI.

## Requirements

1. **Delete the composition machinery.**
   - Delete `cli/reva/compiler.py` and `cli/reva/sampler.py`.
   - Delete `agent_definition/roles/`, `agent_definition/personas/`, `agent_definition/research_interests/`, `agent_definition/review_methodology/`, `agent_definition/review_formats/`.
   - Delete `tests/test_compiler.py` and `tests/test_sampler.py`.
   - Keep `agent_definition/GLOBAL_RULES.md` and `agent_definition/platform_skills.md` — these remain shared bootstrap.
   - Keep `agent_definition/harness/` untouched — it's runtime code, not a composition axis.

2. **New single-file per-agent prompt model.**
   - Each agent directory (`agent_configs/<name>/`) contains a hand-authored `system_prompt.md`.
   - `reva create --name foo` creates `agent_configs/foo/` with a starter `system_prompt.md` scaffold (e.g. "# Agent: foo\n\nDescribe this agent's reviewing focus and style here.") and a `config.json`. It no longer takes `--role`, `--persona`, `--interest`, `--review-methodology`, `--review-format` — the backend is the only remaining knob, defaulting to `claude-code`.
   - The compiled prompt is the concatenation of: `GLOBAL_RULES.md` + `platform_skills.md` + `agent_configs/<name>/system_prompt.md`, in that order, with the existing `SECTION_SEPARATOR` between sections and `{KOALA_BASE_URL}` substitution applied. The substitution + assembly lives in a small helper (≤20 LoC) in `cli/reva/cli.py` or a new one-function `cli/reva/prompt.py`.

3. **Drop batch commands.**
   - Remove the `batch` subcommand group entirely from `cli/reva/cli.py` (create, launch, kill).
   - Remove the `list` subcommand group (`reva list roles|interests|personas`) — it's meaningless without the directories.
   - Remove `reva debug` (was a preview of compiled-from-N-sources prompts).
   - `reva create`, `reva launch`, `reva kill`, `reva status`, `reva view`, `reva log`, `reva archive`, `reva unarchive` remain.

4. **Drop self-registration from the initial prompt.**
   - `DEFAULT_INITIAL_PROMPT` loses the 30-line auth/registration block. Replace with one paragraph:
     > Your API key is at `.api_key` in this directory — the owner provisioned it. Use it as `Authorization: Bearer <key>` on every Koala Science request. If `.api_key` is missing, stop: the owner has not provisioned you yet.
   - Keep the transparency workflow, comments/verdicts, notifications, work-loop sections.

5. **Config cleanup.**
   - `cli/reva/config.py::DEFAULT_CONFIG`: remove `owner_email`, `owner_name`, `owner_password`, `personas_dir`, `roles_dir`, `interests_dir`, `review_methodology_dir`, `review_format_dir`, `review_methodology`, `review_format`.
   - `cli/reva/config.py::RevaConfig`: drop the same fields (and the optional-path / weights infrastructure that only served them).
   - `config.toml`: reduce to `agents_dir`, `global_rules`, `platform_skills`, `github_repo`.

6. **Launch-time `.api_key` gate.**
   - Before `reva launch` actually spawns the backend for an agent, verify `agent_configs/<name>/.api_key` exists and is non-empty. If not, abort with `.api_key missing — ask the owner to provision it at <KOALA_BASE_URL>/owners and drop the key at <path>` and exit non-zero.

7. **GLOBAL_RULES.md trim.**
   - Keep the OpenReview-ID + profile-description guidance — it's still true. Remove or rewrite any sentence that implies programmatic registration.

8. **README rewrite.**
   - Quickstart becomes three commands (single agent): `reva create --name foo`, edit `agent_configs/foo/system_prompt.md`, drop `.api_key` in the dir, `reva launch --name foo`.
   - "Structure" section drops references to the deleted directories and files.
   - "How prompts are assembled" section simplifies to the 3-part concatenation.
   - "Agent identity and persistence" describes owner-provisioned keys.
   - "All commands" section prunes `batch`, `list`, `debug`.

9. **Tests.**
   - Delete `tests/test_compiler.py`, `tests/test_sampler.py`.
   - `tests/test_config.py`: strip assertions about the deleted fields + directories.
   - `tests/test_cli.py`: remove tests for `batch`, `list`, `debug` commands; add tests for (a) `reva launch` fails when `.api_key` missing, (b) `reva create --name foo` generates `system_prompt.md` + `config.json`, (c) the new 3-part prompt assembly.
   - `tests/test_backends.py`: unaffected.
   - `tests/test_tmux.py`: audit for references to deleted commands.
   - `tests/test_env.py`, `tests/test_harness_koala.py`: unaffected.

## Constraints
- Do not change harness code (`agent_definition/harness/`).
- Do not change `KOALA_BASE_URL` behavior, `.env` loading, or the env accessor added in the prior commit.
- Do not add feature flags or legacy-compat shims. Hard break: anyone with an old agent directory created by the sampler needs to re-create by hand. Existing entries in `agent_configs/` can be archived or deleted by the operator; the code doesn't need to migrate them.
- Keep `.agent_name` behavior if it exists (check `tests/test_tmux.py`); don't accidentally break it.

## Acceptance Criteria

- [ ] `grep -rn "owner_password\|owner_email\|owner_name\|auth/agents/register" cli/ agent_definition/ config.toml README.md` returns zero hits.
- [ ] `ls agent_definition/` shows only `GLOBAL_RULES.md`, `platform_skills.md`, and `harness/`.
- [ ] `cli/reva/compiler.py` and `cli/reva/sampler.py` do not exist.
- [ ] `reva --help` does not list `batch`, `list`, or `debug`.
- [ ] `reva create --help` does not mention `--role`, `--persona`, `--interest`, `--review-methodology`, `--review-format`.
- [ ] `reva create --name foo` creates `agent_configs/foo/` with at least `system_prompt.md` and `config.json`.
- [ ] `reva launch --name foo` exits non-zero with a message mentioning `.api_key` when the file is missing.
- [ ] The rendered initial prompt for a launched agent contains `.api_key` and does NOT contain `register` or `owner_password`.
- [ ] `uv run pytest` passes with env unset AND with `KOALA_BASE_URL=https://staging.koala.science` set.
- [ ] README Quickstart uses the new single-agent flow — no `batch` commands appear.
- [ ] `config.toml` contains only: `agents_dir`, `global_rules`, `platform_skills`, `github_repo`.
- [ ] The compiled prompt for an agent is exactly `GLOBAL_RULES.md` + `SECTION_SEPARATOR` + `platform_skills.md` + `SECTION_SEPARATOR` + `agent_configs/<name>/system_prompt.md`, with `{KOALA_BASE_URL}` substituted.
