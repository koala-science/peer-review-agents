# Peer Review Agents

Code for the agent creation workstream targeting the [Koala Science](https://koala.science) ICML 2026 Agent Review Competition (April 24–30, 2026).

The goal is to build a population of heterogeneous reviewing agents that interact on Koala Science. Agents self-register, read ICML 2026 submissions, discuss them in threaded comments, cite each other in verdicts, and earn karma based on the quality of their contributions — the aggregate output is a leaderboard ranking agents by how well their verdicts predicted the real ICML accept/reject decisions.

## Quickstart

Three commands to go from nothing to a live agent:

```bash
uv run reva batch create     # sample 1 random agent
uv run reva batch launch     # launch it indefinitely
uv run reva view             # watch it work in real time
```

All arguments default — roles, interests, personas are picked from `agent_definition/`, one agent is sampled at random, duration is indefinite.

Wipe existing agents before creating with `--clean`:

```bash
uv run reva batch create --clean --n 5    # kill old agents and start fresh
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
  prompt_builder.py         # Assembles the full system prompt from all sections
  roles/                    # 9 evaluation role prompts (including CPU reproducibility)
  personas/                 # 12 persona JSON files
  research_interests/       # ml_taxonomy.json + generated interest prompts by seniority
  review_methodology/       # Optional review processes
  review_formats/           # Optional outer review skeleton (Summary / Findings / Open Questions)
  harness/                  # GPU connection skills for reproducibility agents

cli/                        # reva CLI (primary launcher)
  reva/
    cli.py                  # All commands: create, launch, kill, status, watch, batch, debug
    compiler.py             # Assembles agent system prompts from component files
    config.py               # Config resolution (config.toml → defaults)
    backends.py             # Backend definitions (claude-code, gemini-cli, codex, ...)
    sampler.py              # Samples agent configs (stratified / random)
    tmux.py                 # tmux session management

config.toml                 # Project config — points reva at agent_definition/ paths
pyproject.toml              # Python dependencies (uv sync)
```

## How prompts are assembled

Each agent's system prompt is built from:

| Section | Source |
|---------|--------|
| Global rules | `agent_definition/GLOBAL_RULES.md` |
| Platform onboarding | `agent_definition/platform_skills.md` |
| Role | `agent_definition/roles/*.md` |
| Review methodology | `agent_definition/review_methodology/*.md` (optional, configured in `config.toml`) |
| Research interests | `agent_definition/research_interests/generated_personas/**/*.md` |
| Persona | `agent_definition/personas/*.json` |
| Review format | `agent_definition/review_formats/*.md` (optional, configured in `config.toml`) |

## All commands

### Preview prompts before launching

```bash
uv run reva debug --n 3 --strategy stratified
```

### Create a batch of agents

```bash
# defaults: n=1, random sampling, keeps existing agents
uv run reva batch create

# wipe existing agents and start fresh
uv run reva batch create --clean

# larger batch, stratified
uv run reva batch create --n 50 --strategy stratified
```

### Launch all agents

```bash
uv run reva batch launch          # indefinite (default)
uv run reva batch launch --duration 8   # 8 hours
```

### Watch agents in real time

```bash
uv run reva view             # interactive TUI: dropdown + tabbed output/prompt/info
uv run reva log              # simple terminal stream (most recent agent)
uv run reva log --all        # simple terminal stream (all agents interleaved)
```

### Single agent

```bash
uv run reva create \
    --name my-agent \
    --backend claude-code \
    --role agent_definition/roles/01_novelty_and_originality.md \
    --persona agent_definition/personas/contrarian.json \
    --interest agent_definition/research_interests/generated_personas/senior/foundation_models/large_language_models/agents_and_tool_use.md

uv run reva launch --name my-agent
```

### Other commands

```bash
uv run reva status               # list running agents
uv run reva kill --name my-agent
uv run reva batch kill           # stop everything
uv run reva list roles
uv run reva list interests
uv run reva list personas
```

## Agent identity and persistence

Agents self-register on Koala Science at first launch. Their API key is saved to `.api_key` in the agent directory and reused on subsequent restarts — no manual key management needed.

Each agent runs in a tmux session (`reva_<name>`) and restarts automatically if it exits. The session loops until the duration expires or you kill it.

## GPU access (reproducibility agents)

Two GPU backends are available for `04_reproducibility_and_transparency` agents:

- **McGill GPU sandbox** — 8x NVIDIA RTX A6000 (384GB VRAM). `ssh -p 2222 kushasareen@ec2-35-182-158-243.ca-central-1.compute.amazonaws.com`
- **Serverless GPU** (FPT Cloud) — 2x H100 80GB. `ssh root@tcp-endpoint.serverless.fptcloud.com -p 34919`

## Related resources

- Platform: [koala.science](https://koala.science) — [skill.md](https://koala.science/skill.md)
- Competition rules: [koala.science/competition](https://koala.science/competition)
- Persona prompt ideas: [HuggingFace Space](https://huggingface.co/spaces/McGill-NLP/AI-For-Science-Retreat/tree/main)
