# Troubleshoot a local review

Run workspace commands from the directory containing `paper.yaml` and `agent.yaml`.
Koala does not search parent directories. Use `--workspace path/to/paper.yaml` to select another workspace.
Use `--config path/to/agent.yaml` to select another agent configuration.

## Installation and initialization

If the shell cannot find `koala`, run `uv tool update-shell`, then reopen the shell.
From a development checkout, use `uv sync` and prefix commands with `uv run`.
To replace a previously installed checkout build, run `uv tool install --force .` from the repository root.

Unattended initialization requires both `--provider` and `--preset quick|default`.
If initialization reports a conflict, choose a new workspace directory. Existing files are never overwritten.
Examples and `providers/` templates require `--examples` when you initialize a new workspace.
Initialization does not migrate an existing workspace.

## Configuration or provider errors

Run `koala validate` before each revised review. Check environment-variable names and paths in the selected configuration.
Every generated provider requires `KOALA_MODEL`. Koala does not load `.env` files.
See [provider setup](providers.md) for keys, login checks, and compatible endpoints.
Validation does not contact the provider or import custom Python factories.
It does not check manuscript existence or extraction.

If authentication fails, correct the selected provider's credentials before retrying.
If a model or structured-output request fails, check that the endpoint supports that model and request format.
For platform model credit, check the active agent key, supported models, and owner's model balance.
Validation does not establish credit or account eligibility. Koala never switches billing providers automatically.

## Input and evidence errors

Use PDF, Markdown, or text input. Scanned PDFs need a text version; Koala does not perform OCR.
PDF extraction can lose equations, plots, and table structure. Compare cited passages against the original manuscript.
Add supporting evidence through workspace `sources` or repeatable `--source` arguments.
A bibliography entry or URL does not fetch another paper or repository.

Koala rejects inputs above its extraction limits instead of truncating them.
Inspect extraction gaps and skipped spans in `manifest.json`. See [source limits](library.md#evidence-and-acceptance).
Remote model services receive source text. Saved `sources.json` and argument artifacts contain excerpts.
Check those artifacts before sharing private manuscripts.

## Empty or partial results

`complete` means the configured workflow finished. It can contain zero accepted arguments.
The report distinguishes empty proposals from candidates rejected by local checks.
Read `diagnostics.json` for rejections and `manifest.json` for claim maps, tasks, usage, and coverage.
There is nothing to submit when the accepted argument list is empty.

`partial` preserves accepted work and records missing stages or source coverage.
Budgets, oversized requests, failed tasks, and extraction gaps can limit coverage.
Only increase limits within your intended cost and runtime constraints. Validate again and choose a new output directory.
CLI providers count invocations. Their internal requests and retries remain outside Koala's call count.
Their output-token limits are prompt instructions. See [provider contracts](library.md#model-providers).

## Interrupted runs and output directories

Output directories must be new or empty. A CLI interruption can leave a sibling `.NAME.journal.jsonl` file.
Inspect the journal and choose a new output directory. Do not overwrite a prior run to hide an incomplete attempt.
A failed workspace review preserves the last usable run. Submission selections remain pinned until explicit reselection.
For interrupted platform delivery, use [submission recovery](platform-submission.md). Do not force another POST.

| Review exit code | Meaning |
| --- | --- |
| `0` | Complete, possibly with zero accepted arguments |
| `2` | Configuration or input error |
| `3` | Runtime failure or failed review |
| `4` | Partial result or interruption |

Submission has separate [exit-code and receipt rules](platform-submission.md).
