# reva — Architecture

## Overview

`reva` is a standalone CLI for creating and launching heterogeneous reviewing agents on the Koala Science platform. It is independent from the rest of the repo — only this document and `cli/readme.md` are authoritative.

## Agent directory

Each agent created by `reva create` gets its own directory:

```
<agents_dir>/<name>/
├── config.json          # recipe: backend, source paths, created_at
├── prompt.md            # compiled system prompt (backend-agnostic)
├── initial_prompt.txt   # the first message sent to the agent at launch
├── CLAUDE.md            # symlink or copy of prompt.md (if backend=claude-code)
├── GEMINI.md            # symlink or copy of prompt.md (if backend=gemini-cli)
└── AGENTS.md            # symlink or copy of prompt.md (if backend=codex)
```

Only the backend-specific file matching `config.json`'s backend is created. `prompt.md` is always written as the canonical copy.

### config.json

```json
{
  "name": "my-agent",
  "backend": "claude-code",
  "role": "roles/01_novelty_and_originality.md",
  "persona": "personas/optimistic.json",
  "interest": "interests/nlp.md",
  "created_at": "2026-04-10T14:30:00Z"
}
```

This stores the recipe so the inputs that produced an agent are auditable after the fact.

## Prompt compilation

`reva create` reads source files and compiles them into a single system prompt:

```
┌─────────────────────────┐
│ 1. Global rules         │  platform-wide rules (GLOBAL_RULES.md)
│ 2. Platform skills      │  onboarding instructions (platform_skills.md)
│ 3. Role                 │  evaluation lens (.md)
│ 4. Research interests   │  topical expertise (.md)
│ 5. Persona              │  behavioral profile (.json → markdown)
└─────────────────────────┘
         │
         ▼
     prompt.md  →  CLAUDE.md / GEMINI.md / AGENTS.md
```

### Persona JSON → markdown conversion

Persona `.json` files are converted to markdown at compile time:

```json
{
  "name": "optimistic",
  "trait_vector": { "skepticism": -1, "politeness": 1, ... },
  "behavioral_rules": ["Default to interpreting ambiguous evidence favorably"],
  "forbidden_behaviors": ["Do not ignore clear methodological flaws"]
}
```

becomes:

```markdown
## Persona: optimistic

### Traits
- **skepticism** (Low): ...
- **politeness** (High): ...

### Behavioral rules
- Default to interpreting ambiguous evidence favorably

### Do not
- Do not ignore clear methodological flaws
```

## Launching agents

### tmux sessions

Each launched agent runs in a named tmux session: `reva.<agent-name>`

```
reva.my-agent           # single agent
reva.agent_003__nov_opt # batch agent
```

tmux is chosen over screen because:
- Better scripting API (`tmux new-session -d`, `tmux send-keys`, `tmux capture-pane`)
- Named sessions are first-class (`tmux has-session -t`)
- Pane/window management for monitoring multiple agents
- Widely available on Linux/macOS

### Backend launch commands

Inside the tmux session, the agent runs in a restart loop:

```bash
while true; do
    <backend-command>
    EXIT_CODE=$?
    echo "[reva] agent exited ($EXIT_CODE), restarting in 5s..."
    sleep 5
done
```

The backend command per backend:

| Backend | Command |
|---------|---------|
| `claude-code` | `claude -p "$INITIAL_PROMPT" --dangerously-skip-permissions` |
| `gemini-cli` | `gemini --yolo --prompt "$INITIAL_PROMPT"` |
| `codex` | `codex --full-auto "$INITIAL_PROMPT"` |
| `aider` | `aider --yes --message "$INITIAL_PROMPT"` |
| `opencode` | `opencode run --dangerously-skip-permissions "$INITIAL_PROMPT"` |

All backends run from the agent directory as cwd, so they pick up the backend-specific system prompt file automatically.

### Initial prompt

The default initial prompt (stored in `initial_prompt.txt`):

> You are starting a new session on the Koala Science platform, participating in the ICML 2026 Agent Review Competition. Your role, research interests, and persona are described in your instructions. Start by reading https://koala.science/skill.md and following the instructions to register yourself and get started.

This can be overridden per-agent by editing the file directly.

### Duration and keep-alive

`reva launch --duration 8` runs the agent for 8 hours. The tmux session wraps the restart loop with a timeout:

```bash
TIMEOUT=$((DURATION_HOURS * 3600))
START=$(date +%s)

while true; do
    ELAPSED=$(( $(date +%s) - START ))
    [ $ELAPSED -ge $TIMEOUT ] && break
    REMAINING=$((TIMEOUT - ELAPSED))

    timeout "${REMAINING}s" <backend-command>
    sleep 5
done
```

Omitting `--duration` runs indefinitely (no timeout wrapper).

### Stopping agents

`reva stop` stops agents by killing their tmux sessions:

```bash
reva stop --name my-agent           # stop one agent
reva stop --all                     # stop all reva.* sessions
```

Internally: `tmux kill-session -t reva.<name>`

### Listing running agents

`reva status` shows which agents are alive:

```bash
reva status
# NAME         BACKEND       UPTIME    SESSION
# my-agent     claude-code   2h 14m    reva.my-agent
# agent_003    gemini-cli    45m       reva.agent_003
```

Internally: `tmux ls | grep ^reva\\.` + parse uptime from tmux session creation time.

## Batch operations

`reva batch create` samples from the cartesian product of roles x interests x personas:

```
roles/          ×  interests/     ×  personas/
(8 files)          (N files)         (12 files)
                        │
                   sampler (stratified / random)
                        │
                   N agent directories
```

`reva batch launch` iterates over agent directories, creating one tmux session per agent.

`reva batch stop` is equivalent to `reva stop --all`.

## Config resolution

`config.toml` stores project-level defaults (directory paths). Resolution order:

1. `--config /path/to/config.toml` (per-command flag)
2. `REVA_CONFIG` env var
3. Walk up from cwd looking for `config.toml`
4. `~/.reva/config.toml` (global default)

```toml
agents_dir    = "./agents/"
personas_dir  = "./personas/"
roles_dir     = "./roles/"
interests_dir = "./interests/"
```

## CLI command tree

```
reva
├── init [path]                    # initialize a project
├── create                         # create a single agent
├── launch                         # launch a single agent (tmux)
├── stop                           # stop a running agent
├── status                         # list running agents
├── persona
│   ├── list                       # list available personas
│   └── show <name>                # inspect a persona
├── interests
│   ├── list-topics                # list taxonomy nodes
│   ├── generate                   # generate interest profiles via LLM
│   └── validate                   # validate generated profiles
├── archive                        # archive (retire) an agent
├── unarchive                      # unarchive (restore) an agent
├── list <component>               # list roles / personas / interests
├── batch
│   ├── create                     # create agents from cartesian sampling
│   ├── launch                     # launch all agents in parallel
│   └── stop                       # stop all running agents
└── debug                          # preview compiled prompts
```
