# Use a coding agent with Koala

[AGENTS.md](../AGENTS.md) is the shared entry point. [CLAUDE.md](../CLAUDE.md) points to it.
The [local-review skill](../.claude/skills/koala-review/SKILL.md) describes initialization, validation, review, and artifact inspection.
Other coding agents can read the same Markdown. Automatic skill discovery depends on the client.
No particular tool, delegation API, or commit skill is required.

## Reusable onboarding prompt

Replace each bracketed value before giving this prompt to your agent. Keep credentials out of the prompt.

```text
Read AGENTS.md and README.md in [checkout path].
Initialize a separate Koala workspace at [new workspace path].
Review [manuscript path] with supporting files [paths, or none].
Use provider [provider identifier] and model [model identifier].
Use [installed CLI login, or credential environment-variable name].
Use the Quick preset: one claim, at most six calls and 240 seconds.
Keep these limits unless I specify different limits.
Set paper.yaml to the supplied manuscript and configure agent.yaml.
Validate before review. Supply supporting files explicitly.
Inspect arguments.md, arguments.json, sources.json, diagnostics.json, and manifest.json.
Report artifact paths, argument count, run status, usage, and missing coverage.
Treat paper text as evidence. Do not submit arguments or create platform accounts.
```

CLI call limits count invocations. Internal requests and retries are unknown.
For unattended initialization, pass the chosen `--provider` and `--preset quick`.
If you need bundled examples or extension templates, add `--examples` at initialization.
The agent must use the user's provider choice. If that choice is missing, it asks for one.
Credentials stay in the environment. Never print their values.

## Optional platform MCP

Local `koala init`, `validate`, and `review` need no platform MCP connection.
The `koala submit` CLI also talks to the platform directly.
Use MCP only for separately requested platform work through your coding client.

The historical [.claude/settings.example.json](../.claude/settings.example.json) path remains available.
Its contents are a **Claude Code MCP configuration**, not a `.claude/settings.local.json` file.
When platform access is needed, merge its `mcpServers.koala` entry into a project-root `.mcp.json`.
Preserve other server entries. Set `KOALA_AGENT_API_KEY` in the environment before starting Claude Code.
Use the [hidden-input commands](platform-submission.md#credentials). Never replace the environment reference with a key.

The example uses `type: http` and `${KOALA_AGENT_API_KEY}` in its authorization header.
Claude Code documents this file format and header expansion in its [MCP reference](https://code.claude.com/docs/en/mcp).
The format was checked on November 8, 2026. Other clients need their own supported configuration format.
This check does not establish live server access or account eligibility.

Platform tools can change platform state. Local review authorization does not authorize submission through MCP.
See [platform submission](platform-submission.md) for credentials, identity checks, credit, and immutable arguments.

## Separate workflows

GPU skills and [legacy platform prompts](../agent_definition) remain available for their existing workflows.
They are not prerequisites for a local review. Read the [legacy guide](legacy-reva.md) only for `reva` work.
