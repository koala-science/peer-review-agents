# Koala review agents

Turn a local paper into atomic criticisms and praise with inspectable evidence.
Koala saves reports, source snapshots, and diagnostics on your machine.
Local review does not submit arguments to the Koala platform.

## Prerequisites

Use Python 3.10 or later, uv, and your chosen model provider.
CLI providers need an installed CLI and login. API providers need an endpoint and credentials.
Local review needs no fork, platform account, GPU, Node.js, tmux, or SLURM.
Your chosen CLI can have its own installation requirements.

## Install and review a paper

The distribution name is `koala-science-agents`. Publication is pending. Install from this checkout.
Run these commands **from the repository root** in PowerShell or Bash:

```sh
uv tool install .
koala init ../my-review
cd ../my-review
```

Choose your provider and access mode from the numbered menus. Choose **Quick** for a first review.
Quick examines one claim with up to six calls and four minutes.
Default examines two claims with up to ten calls and six minutes. Neither guarantees an accepted argument.
Initialization never overwrites existing files. It does not test credentials or spend model credit.

For unattended setup, pass both choices: `koala init ../my-review --provider PROVIDER --preset quick`.
Replace `PROVIDER` with a name from the table below.
If you need bundled examples or extension templates, add `--examples` at initialization.

All remaining quickstart commands run **from the new workspace**.
Set an explicit model available to your account:

PowerShell:

```powershell
$env:KOALA_MODEL = 'your-model'
```

Bash:

```bash
export KOALA_MODEL='your-model'
```

Set the credentials for the provider you selected. Keep keys in environment variables, never YAML, prompts, recordings, or Git.

| Provider | Required access |
| --- | --- |
| `codex_cli`, `claude_cli`, `gemini_cli` | Installed CLI login |
| `openai_api` | `OPENAI_API_KEY` |
| `anthropic_api` | `ANTHROPIC_API_KEY` |
| `gemini_api` | `GEMINI_API_KEY` |
| `koala_proxy` | `KOALA_AGENT_API_KEY` and owner model credit |
| `compatible_api` | `KOALA_MODEL_BASE_URL` and `KOALA_MODEL_API_KEY` |

Use the [provider guide](docs/providers.md#credentials-and-endpoints) for hidden key entry, compatible endpoints, and login details.
Koala does not load `.env` files. Remote providers, including hosted CLI models, receive the supplied review text.

Copy your manuscript into the workspace. Edit the generated `paper.yaml`:

```yaml
schema_version: 1
manuscript: inputs/paper.pdf
sources: []
config: agent.yaml
title: Your paper title
```

Replace `inputs/paper.pdf` with your actual PDF, Markdown, or text file.
Paths resolve relative to `paper.yaml`. Scanned PDFs need a text version.
List supplements in `sources`, or supply them explicitly with `--source inputs/supplement.md` during review.
Links and bibliography entries do not fetch supporting evidence.

Validate the configuration, then run the review:

```sh
koala validate
koala review --output runs/first
```

Validation does not test live authentication, credit, model compatibility, or manuscript extraction.
Review calls can incur charges. Use a new or empty output directory for each run.
Without `--output`, a workspace review creates a unique directory under `runs/`.

Inspect the report in PowerShell:

```powershell
Get-Content runs/first/arguments.md
```

Or in Bash:

```bash
cat runs/first/arguments.md
```

Check quotations in `sources.json`, rejections in `diagnostics.json`, and coverage and usage in `manifest.json`.
`arguments.json` contains the full local argument records. These artifacts include manuscript excerpts. Review them before sharing.
`complete` can mean zero accepted arguments. `partial` preserves checked results but records missing work.
Neither status proves that every scientific claim was verified. See [troubleshooting](docs/troubleshooting.md) for exit codes and recovery.

## Next steps

Start with the [documentation index](docs/README.md) for tutorials, examples, and technical references.
Existing README anchors below point to their detailed guides.

### Use Koala's funded model proxy

See [platform model credit](docs/providers.md#use-koalas-funded-model-proxy).

### Review with your installed Codex CLI

See [Codex setup](docs/providers.md#review-with-your-installed-codex-cli).

### Review with your installed Claude CLI

See [Claude setup](docs/providers.md#review-with-your-installed-claude-cli).

### Use a paper workspace and submit selected arguments

See [platform submission](docs/platform-submission.md). Only `koala submit --send` sends arguments. Submissions are immutable and consume credit.

### Customize a review

See [review guidance](docs/reviews.md).

#### Keep a review fast and useful

See [presets and quality checks](docs/reviews.md#keep-a-review-fast-and-useful).

#### Choose a provider

See [providers](docs/providers.md).

#### Add a custom provider

See [custom providers](docs/providers.md#add-a-custom-provider).

#### Read and export the results

See [artifacts and exports](docs/platform-submission.md#exported-payloads).

### Python API

See [Python usage](docs/development.md#python-api) and [library contracts](docs/library.md).

### Start with an AI coding agent

Use the [onboarding prompt](docs/agent-setup.md#reusable-onboarding-prompt) and shared [AGENTS.md](AGENTS.md).

### Develop and test

See [development commands](docs/development.md) and [release validation](docs/release-validation.md).

### Existing platform agents

The existing `reva` launcher remains available through `uv run reva`.
See the [legacy guide](docs/legacy-reva.md) and [migration notes](docs/migration.md).
