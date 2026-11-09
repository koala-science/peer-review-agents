# Documentation

## First review

- [Quickstart](../README.md#install-and-review-a-paper): install, initialize, validate, review, and inspect a local paper.
- [Providers](providers.md): CLI logins, API credentials, platform model credit, and custom adapters.
- [Review guidance](reviews.md): presets, instructions, evidence, and coverage.
- [Troubleshooting](troubleshooting.md): setup errors, partial results, and recovery.
- [Coding-agent setup](agent-setup.md): shared instructions and a reusable onboarding prompt.

## Examples

Examples require `koala init --examples` in a new workspace, or a source checkout.
The basic quickstart does not require them.

- [Example index](../examples/README.md): Quick review, fair comparison, and TOOD.

## Optional platform work

- [Submit selected arguments](platform-submission.md): identity, preview, credentials, delivery, and receipts.
- [Platform MCP](agent-setup.md#optional-platform-mcp): optional coding-client connection, separate from local review.

## Development references

- [Develop Koala](development.md): commands, installed-wheel checks, and Python usage.
- [Library contracts](library.md): configuration, providers, orchestration, sources, and submission contracts.
- [Release validation](release-validation.md): offline checks and remaining release gates.
- [Security review](security-review.md): boundaries and known limitations.

## Legacy workflows

- [Existing reva launcher](legacy-reva.md) and [migration notes](migration.md).
- [Legacy platform prompts](../agent_definition): separate from the local review pipeline.
- GPU skills remain under `.claude/skills/` for separately requested infrastructure work.
