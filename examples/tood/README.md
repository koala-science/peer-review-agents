# Example: review TOOD locally

This example targets [TOOD, arXiv 2607.29592v1](https://arxiv.org/abs/2607.29592v1)
by Mostafa ElAraby, Samer B. Nashed, and Liam Paull. It reviews the manuscript.
It does not reproduce the paper's machine-learning experiments.

The methods agent checks calibration and assumptions. The results agent checks
evaluation claims. The evidence agent assesses each candidate independently.
All agents share one model, a call budget, and a deadline.

The example is runnable from the repository root or a workspace created by `koala init`.
In this checkout, prefix the `koala` commands below with `uv run`.

## Get the paper

From an initialized Koala workspace, download the pinned PDF:

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

## Inspect the review

Read `arguments.md`, then compare its quotations against `sources.json` and the PDF.
Read `diagnostics.json` for rejected candidates and `manifest.json` for incomplete work.
Equations and plots can lose information during text extraction. Inspect them in the
PDF before accepting a numerical or mathematical conclusion.

Add a local supplement with `--source path/to/supplement.md`. A bibliography entry
or a link does not give the reviewer access to another paper or a code repository.
Reviewing never submits arguments to the Koala platform.
