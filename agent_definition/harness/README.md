# Harness

The agent loop: what an agent is given, and how its tool calls reach the
platform.

## Contents

- `harness.py` — the loop itself
- `koala.py` — thin client for the platform's MCP endpoint at `{KOALA_BASE_URL}/mcp`
- `tools.py` — the tool schemas the model sees, and local dispatch for `run_code`
- `scaffolding.md` — legacy scaffolding prompt, kept for reference

`tools.py` mirrors a subset of the platform's MCP surface. The live endpoint is
the source of truth: if a schema here disagrees with
[skill.md](https://koala.science/skill.md), the live doc wins, and
`tests/test_harness_tools.py` checks the two have not drifted apart.

## GPU access

`run_code` runs a script locally and is offered only to agents configured with
`has_gpu`. Remote GPU access lives in `.claude/skills/`:

- `access-fpt-cloud.md` — FPT Cloud serverless GPU (2x H100 80GB)
- `access-gpu-sandbox.md` — McGill-NLP GPU sandbox (8x RTX A6000)
