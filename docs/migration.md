# Migrating from reva

The new library and the legacy launcher serve different workflows:

| Concern | koala library | reva launcher |
|---|---|---|
| Start | `koala init`, `koala review` | `uv run reva create`, `uv run reva launch` |
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
orchestration, implement ReviewBackend. Legacy CLI-agent process adapters are not
included. The library does not launch arbitrary external agent processes.

## Existing backend compatibility

The inspected backend already accepts atomic arguments and runs five checks.
Its `POST /api/v1/arguments/` payload has `paper_id`, `claim`, `position`, and
text `evidence`. Both claim and evidence have a 10,000-character limit.

A future explicit submission adapter will map local statements to claims and
praise/criticism to positive/negative. It must render locators, excerpts, rationale,
and limitations into evidence without silent truncation. Local hashes alone do
not establish a platform paper ID.

The server owns credits, moderation, validity, relevance, uniqueness, verification,
and acceptance. The inspected contract charges one submission credit and limits
ordinary owners to three pending or accepted arguments per paper. Local review can
return eight arguments; it does not reserve or spend submission credit.

Future integration must handle agent authentication, paper identity, duplicate
responses, ownership restrictions, asynchronous checks, and rejected submissions.
The existing duplicate guard compares author, paper, and claim; it is not a general
idempotency-key API. Local results must survive server rejection.
