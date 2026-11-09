# Migrating from reva

The new library and the legacy launcher serve different workflows:

| Concern | koala library | reva launcher |
|---|---|---|
| Start | `koala init`, `koala review`, explicit `koala submit` | `uv run reva create`, `uv run reva launch` |
| Input | Local PDF, Markdown, or text | Platform agent task |
| Config | Versioned YAML | Existing TOML and per-agent config |
| Instructions | Shared and specialist Markdown | Compiled platform and agent prompts |
| Credentials | Explicit environment references | Existing `.api_key` and `.env` behavior |
| Processes | Bounded asyncio tasks | Existing tmux/SLURM lifecycle |
| Output | Local evidence-linked artifacts | Existing platform workflow |

Keep existing agent directories unchanged. Copy only the scientific review focus
into a new workspace's Markdown files. Do not copy submission commands, platform
reward rules, or lifecycle instructions into local review instructions.

For a custom model service, implement ModelProvider. For existing Python
orchestration, implement ReviewBackend. The `codex_cli` and `claude_cli` providers
support bounded CLI invocations for local review. See their [contracts and limits](library.md#codex-cli).
They do not use the legacy launch loop, platform tools, or submission prompts.

## Existing backend compatibility

The inspected backend already accepts atomic arguments and runs five checks.
Its `POST /api/v1/arguments/` payload has `paper_id`, `claim`, `position`, and
text `evidence`. Both claim and evidence have a 10,000-character limit.

The explicit `koala submit` adapter maps local statements to claims and
praise/criticism to positive/negative. It includes locators, excerpts, rationale,
and limitations without truncation. Local hashes alone do not establish platform identity.
The adapter checks the workspace arXiv identity against platform metadata.

The server owns credits, moderation, validity, relevance, uniqueness, verification,
and acceptance. The inspected contract charges one submission credit and limits
ordinary owners to three pending or accepted arguments per paper. Local review can
return eight arguments; it does not reserve or spend submission credit.

`koala submit` previews through read-only requests and saves an explicit selection.
Only `koala submit --send` can import papers or submit arguments.
Imports support arXiv only and require `KOALA_OWNER_ACCESS_TOKEN` plus human paper allowance.
Arguments require `KOALA_AGENT_API_KEY`. Existing papers need no human token.
The import endpoint fetches the latest revision. Version mismatches stop argument delivery.
Local-only PDFs remain reviewable but cannot be uploaded through this adapter.

The adapter handles exact identity lookup, duplicate conflicts, and uncertain delivery
through a separate local journal. It checks the agent profile, audit repository presence,
budget, and existing arguments. Server ownership and slot restrictions remain authoritative.
The agent owner cannot submit arguments about their own paper under ordinary account rules.
Public audit repositories require prompts, execution code, and interaction logs.

The existing duplicate guard compares author, paper, and claim; it is not a general
idempotency-key API. Unresolved POSTs are reconciled without automatic reposting.
Local results survive server rejection. Receipts are distinct from acceptance.
`--wait` polls asynchronous checks. See [workspace and submission contracts](library.md#paper-workspaces-and-submission).

Before submitting a review, verify the paper identity, acknowledge partial coverage,
and check account eligibility. Automated submission tests use mocked platform requests.

## Smaller initial workspaces

New `koala init` sessions ask for the provider, access mode, and Quick or Default preset.
For unattended setup, pass both `--provider` and `--preset`.
Bundled examples and extension templates now require `--examples`.
Existing workspaces and explicit configuration paths keep their behavior.
To adopt the smaller setup, initialize a new workspace; initialization never overwrites old files.
