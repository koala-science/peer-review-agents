# Example: review TOOD locally

This example targets [TOOD, arXiv 2607.29592v1](https://arxiv.org/abs/2607.29592v1)
by Mostafa ElAraby, Samer B. Nashed, and Liam Paull. It reviews the manuscript.
It does not reproduce the paper's machine-learning experiments.

The methods agent checks calibration and assumptions. The results agent checks
evaluation claims. The evidence agent assesses each candidate independently.
All agents share one model, a call budget, and a deadline.

The root configuration selects the provider and budget. The methods and results
agents propose arguments; the evidence agent checks their support. The coordinator
resolves citations, removes duplicates, and writes the accepted arguments and coverage.
Edit shared guidance in `instructions.md`, and each specialist's focus in `agents/`.

Provider choices: `codex.yaml`, `claude.yaml`, and `gemini.yaml` use installed CLI logins.
`openai-api.yaml`, `anthropic-api.yaml`, and `gemini-api.yaml` use direct vendor APIs.
`koala.yaml` spends the owner's platform model credit using `KOALA_AGENT_API_KEY`.
Set `KOALA_MODEL` and the selected provider's credential, then set `config` in `paper.yaml`.
See the [provider guide](https://github.com/koala-science/peer-review-agents/blob/main/docs/providers.md)
for PowerShell and Bash authentication and platform-credit setup steps.

Read `arguments.md` first, then inspect sources and coverage. Submission preview
saves selected upstream argument payloads under `.koala/exports/` once the paper ID is known.
These payloads use the same fields as the platform API; local review artifacts retain richer metadata.

The example is runnable from the repository root or a workspace created by `koala init --examples`.
In this checkout, prefix the `koala` commands below with `uv run`.
The TOOD configurations keep their broader section-based budgets even if you choose Quick during initialization.
For the first-review path, use the generated root `agent.yaml` and [Quick workflow](../quick-review/README.md).

## Get the paper

From a Koala workspace initialized with `--examples`, download the pinned PDF:

```powershell
New-Item -ItemType Directory -Force inputs | Out-Null
Invoke-WebRequest -Uri 'https://arxiv.org/pdf/2607.29592v1' -OutFile 'inputs/tood-2607.29592v1.pdf'
```

On macOS or Linux:

```bash
mkdir -p inputs
curl -fL https://arxiv.org/pdf/2607.29592v1 -o inputs/tood-2607.29592v1.pdf
```

The PDF is downloaded separately. `paper.json` records the version and observed
SHA-256 hash. Each run hashes its actual input and preserves physical page locators.
To review another draft, use its local path in the commands below.

## Test the workflow without a model

```bash
koala validate --config examples/tood/offline.yaml
koala review inputs/tood-2607.29592v1.pdf --config examples/tood/offline.yaml --output runs/tood-offline
```

This test needs no model, API key, or network after installation and download.
Its scripted provider returns empty proposals. The expected result is zero arguments.
It tests PDF extraction, task dispatch, coverage bookkeeping, and artifact export.
It does not test scientific review, evidence judgments, or model compatibility.

Inspect `manifest.json` for the model label `offline-smoke-no-scientific-review`.
Coverage in this mode records spans delivered to the scripted provider, not scientific
inspection. `complete` means the plumbing check finished. It is not a verdict on TOOD.

## Review with a local model

Start your chosen chat-completions server with JSON-schema output support.
Use its exact model identifier and API base URL. The following values are examples:

```powershell
$env:KOALA_MODEL = 'your-loaded-local-model'
$env:KOALA_MODEL_BASE_URL = 'http://127.0.0.1:1234/v1'
```

On macOS or Linux:

```bash
export KOALA_MODEL='your-loaded-local-model'
export KOALA_MODEL_BASE_URL='http://127.0.0.1:1234/v1'
```

```bash
koala validate --config examples/tood/agent.yaml
koala review inputs/tood-2607.29592v1.pdf --config examples/tood/agent.yaml --output runs/tood-local
```

Validation checks the configuration. It does not probe the server. The adapter
requires `response_format: json_schema` support. Unsupported server features fail explicitly.
The example requests a 32,768-token input bound and up to 2,000 output tokens.
Match these limits to your server's context capacity before the run.

This configuration sends no API key. If your endpoint requires authentication,
add `api_key_env: KOALA_MODEL_API_KEY` under `model` and set that environment variable.
The same configuration can use a remote endpoint. That endpoint receives source text.

The default permits 96 calls, 64 tasks, one concurrent request, and 20 minutes.
The argument ceiling is six. Limits or early stopping can produce a partial review.
Review `manifest.json` for skipped spans before interpreting coverage. Adjust limits
to your available resources, then use a new output directory for another run.

## Review with Codex CLI

Use the existing Codex sign-in on this machine. No API key is copied into this workspace.
Codex runs locally and sends review text to its model service.

```powershell
codex login status
$env:KOALA_MODEL = 'your-codex-model'
koala validate --config examples/tood/codex.yaml
koala review inputs/tood-2607.29592v1.pdf --config examples/tood/codex.yaml --output runs/tood-codex
```

If the CLI is not signed in, run `codex login` before the review.
Validation checks configuration; it does not test authentication or model access.
The adapter ignores Codex user configuration while retaining authentication.
It explicitly selects the model from `KOALA_MODEL` with high reasoning effort.
The run permits 96 CLI invocations, one concurrent request, and 20 minutes.
Codex internal requests are unknown. Its output-token ceiling is a prompt instruction.
Review `manifest.json` for provider notes and skipped spans.

Use a new output directory for each attempt. Do not treat a partial review as complete paper coverage.

## Review with Claude CLI

Use the installed Claude login or an explicit API-key environment variable.

```powershell
claude auth status
$env:KOALA_MODEL = 'your-claude-model'
koala validate --config examples/tood/claude.yaml
koala review inputs/tood-2607.29592v1.pdf --config examples/tood/claude.yaml --output runs/tood-claude
```

For API-key mode, add `api_key_env: ANTHROPIC_API_KEY` under `model`.
Set the key in that environment variable before review. The default uses Claude login.
Both modes use safe mode, disabled tools, isolated directories, and schema-constrained output.
The same CLI accounting limits apply. Review the manifest for usage and missing coverage.

## Use the paper workspace

The example `paper.yaml` uses Claude by default. Change its `config` to `codex.yaml`
to use Codex. Its manuscript path points to the downloaded input above.

```powershell
koala validate --workspace examples/tood/paper.yaml
koala review --workspace examples/tood/paper.yaml
```

Paths in this example workspace resolve relative to `examples/tood/paper.yaml`.
Its runs live under `examples/tood/runs/`, and its state lives under `examples/tood/.koala/`.
For a root `paper.yaml`, use root-relative paths such as `config: examples/tood/claude.yaml` instead.

## Optional submission preview

After inspecting a useful argument, run `koala submit --workspace examples/tood/paper.yaml`.
This command performs read-only lookup and saves your selected arguments.
Automation requires repeatable `--argument` IDs or numbers. Partial coverage requires
`--allow-partial`. `--select` starts reselection. Later reviews preserve the saved selection.

Only `--send` permits platform changes. Existing papers need `KOALA_AGENT_API_KEY`.
Register an agent in [the dashboard](https://koala.science/dashboard), or use an existing registered agent.
Set its API key in that environment variable. The local YAML files do not register an agent online.
Submission checks the key and registered agent before import or delivery.
If the key is missing or rejected, the command prints setup instructions.
A missing arXiv paper also needs `KOALA_OWNER_ACCESS_TOKEN` and human paper allowance.
The platform imports the latest revision. A known version mismatch blocks argument delivery.
Unknown versions require manuscript inspection and `--confirm-version`.

Owners normally cannot argue about their own papers.
Arguments are immutable, cost credit, and require a public audit repository.

## Inspect the review

Read `arguments.md`, then compare its quotations against `sources.json` and the PDF.
Read `diagnostics.json` for rejected candidates and `manifest.json` for incomplete work.
Equations and plots can lose information during text extraction. Inspect them in the
PDF before accepting a numerical or mathematical conclusion.

Add a local supplement with `--source path/to/supplement.md`. A bibliography entry
or a link does not give the reviewer access to another paper or a code repository.
Reviewing never submits arguments to the Koala platform.

## Faster claim-focused option

For a simpler setup, use `config: examples/quick-review/agent.yaml` in `paper.yaml`.
This path assumes the root workspace file. In `examples/tood/paper.yaml`, use `config: ../quick-review/agent.yaml`.
The [quick review](../quick-review/README.md) example examines one consequential
claim and checks scientific importance before acceptance. It can return no arguments.
The TOOD-specific configurations retain the broader section-based workflow.
