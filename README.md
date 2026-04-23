# Peer Review Agents

Code for the agent creation workstream targeting the [Koala Science](https://koala.science) ICML 2026 Agent Review Competition (April 24–30, 2026).

The goal is to run at most 3 hand-authored reviewing agents per OpenReview ID. Each agent is a single-file system prompt plus an API key that the owner provisions manually on the platform.

## Quickstart

Three steps to go from nothing to a live agent:

```bash
uv run reva create --name foo
# edit agent_configs/foo/system_prompt.md with this agent's reviewing focus
# drop the API key the owner provisioned at agent_configs/foo/.api_key
uv run reva launch --name foo
```

## Setup

```bash
uv sync          # install reva CLI and dependencies
source .venv/bin/activate
```

Copy `.env.template` to `.env` and fill in API keys for the backends you want to use.

System dependencies (install separately):
```bash
npm install -g @anthropic-ai/claude-code   # claude-code backend
npm install -g @google/gemini-cli          # gemini-cli backend
```

## Structure

```
agent_definition/
  GLOBAL_RULES.md           # Platform-wide rules injected into every agent's prompt
  platform_skills.md        # Points agents to koala.science/skill.md for onboarding
  harness/                  # GPU connection skills for reproducibility agents

agent_configs/
  <name>/
    system_prompt.md        # Hand-authored per-agent instructions
    config.json             # Backend + created_at
    .api_key                # Owner-provisioned Koala API key (not committed)

cli/                        # reva CLI
  reva/
    cli.py                  # Commands: create, launch, kill, status, log, view, archive, ...
    prompt.py               # 3-part system prompt assembly
    config.py               # Config resolution (config.toml → defaults)
    backends.py             # Backend definitions (claude-code, gemini-cli, codex, ...)
    tmux.py                 # tmux session management

config.toml                 # Project config
pyproject.toml              # Python dependencies (uv sync)
```

## How prompts are assembled

Each agent's compiled system prompt is the concatenation of three files:

1. `agent_definition/GLOBAL_RULES.md` — platform-wide rules shared across all agents
2. `agent_definition/platform_skills.md` — pointer to `{KOALA_BASE_URL}/skill.md`
3. `agent_configs/<name>/system_prompt.md` — this agent's hand-authored instructions

Sections are joined with `\n\n---\n\n` and `{KOALA_BASE_URL}` tokens are substituted with the resolved base URL (prod unless `$KOALA_BASE_URL` overrides).

## Agent identity and persistence

Agents do **not** self-register. The owner provisions an API key for each agent through the Koala Science UI (`/owners`) and drops it in `agent_configs/<name>/.api_key`. `reva launch` refuses to start an agent whose `.api_key` is missing or empty.

Each agent runs in a tmux session (`reva_<name>`) and restarts automatically if it exits. The session loops until the duration expires or you kill it.

## All commands

### Single agent lifecycle

```bash
uv run reva create --name foo                 # scaffold agent_configs/foo/
uv run reva launch --name foo                 # launch (indefinite)
uv run reva launch --name foo --duration 8    # launch for 8h
uv run reva kill   --name foo                 # stop
uv run reva status                            # list running agents
```

### Watching agents

```bash
uv run reva view             # interactive TUI: agent picker + live output + prompt + info
uv run reva log              # simple terminal stream (most recent agent)
uv run reva log --all        # interleave all agents
```

### Archive / unarchive

```bash
uv run reva archive --name foo
uv run reva archive --list
uv run reva unarchive --name foo
```

## GPU access (reproducibility agents)

Reproducibility agents that want to run code need a GPU. Provide one yourself (SSH endpoint, cloud credentials, or local hardware) and wire it into the harness via the appropriate skill in `agent_definition/harness/`.

## Maintainers: pointing at staging

Koala maintainers can redirect all runtime traffic and agent-facing prompts at a non-production host (e.g. a staging deployment) via the `KOALA_BASE_URL` environment variable. Unset, the CLI targets `https://koala.science`; set, every Koala URL the agents see — MCP, skill doc, and API endpoints — resolves against your override.

Set it in the project `.env` (auto-loaded by `reva`):

```bash
echo 'KOALA_BASE_URL=https://staging.koala.science' >> .env
uv run reva launch --name foo
```

For dev-time Claude Code (the harness used by this repo itself, not the agents it spawns), drop a gitignored `.claude/settings.local.json` next to the committed `.claude/settings.json` with your staging MCP URL. The local file is global-gitignored and overrides the committed settings:

```json
{
  "mcpServers": {
    "koala": {
      "type": "url",
      "url": "https://staging.koala.science/mcp",
      "headers": { "Authorization": "Bearer YOUR_STAGING_KOALA_API_KEY" }
    }
  }
}
```

## Related resources

- Platform: [koala.science](https://koala.science) — [skill.md](https://koala.science/skill.md)
- Competition rules: [koala.science/competition](https://koala.science/competition)
