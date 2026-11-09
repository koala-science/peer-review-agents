# Review examples

Each example keeps its configuration, instructions, and supporting files together.
These directories are the source for the examples included by `koala init --examples`.
For a first review, initialize a basic workspace and choose Quick in the menu.
Examples are optional and keep their own providers and budgets, independent of the root `agent.yaml`.

From the checkout, create an example workspace with `koala init ../example-review --examples`.
Then run `cd ../example-review`. For unattended setup, also pass your `--provider` and `--preset` choices.
Use the repository's [provider guide](https://github.com/koala-science/peer-review-agents/blob/main/docs/providers.md)
for authentication. Repository documentation is not copied into generated workspaces.

| Example | Purpose | Start here |
| --- | --- | --- |
| [Quick review](quick-review/README.md) | Examine one consequential claim with a skeptical quality check. | [agent.yaml](quick-review/agent.yaml) |
| [TOOD](tood/README.md) | Review a real continual OOD detection paper with methods, results, and evidence agents. | [agent.yaml](tood/agent.yaml) or [offline.yaml](tood/offline.yaml) |
| [Fair comparison](fair-comparison/README.md) | Inspect a small reviewer with a fictional paper and a confounded comparison. | [agent.yaml](fair-comparison/agent.yaml) |

## Inspect TOOD

```text
examples/tood/
  agent.yaml             Local-model configuration
  codex.yaml             Installed Codex CLI configuration
  claude.yaml            Installed Claude CLI configuration
  gemini.yaml            Installed Gemini CLI configuration
  openai-api.yaml        Direct OpenAI API configuration
  anthropic-api.yaml     Direct Anthropic API configuration
  gemini-api.yaml        Direct Gemini API configuration
  koala.yaml             Platform model-credit configuration
  paper.yaml             arXiv identity and workspace paths
  instructions.md        Shared review instructions
  agents/
    methods.yaml / .md    Calibration and assumptions
    results.yaml / .md    Evaluation and conclusions
    evidence.yaml / .md   Independent evidence review
  offline.yaml           No-model workflow check
  offline_provider.py    Scripted empty proposals
  paper.json             Pinned paper metadata
```

From the repository root, validate the offline example:

```bash
uv run koala validate --config examples/tood/offline.yaml
uv run koala review examples/fair-comparison/paper.md --config examples/tood/offline.yaml --output runs/offline-check
```

Follow the [TOOD guide](tood/README.md) to download the paper and run a review.
When working in this checkout, prefix its `koala` commands with `uv run`.
Store downloaded papers in `inputs/` and results in `runs/`. Both directories are ignored by Git.

This no-download check uses the bundled fictional paper and returns zero arguments.
Inspect `runs/offline-check/arguments.md`, `sources.json`, `diagnostics.json`, and `manifest.json`.
The offline provider checks extraction and export. It does not make scientific judgments.
The model configuration in `agent.yaml` is used for an actual review.

## Packaging

Edit these root examples directly. The wheel maps them into
`koala_science/templates/examples/`, and editable installs read this directory.
Workspaces initialized with `--examples` keep the same `examples/tood/` and `examples/fair-comparison/` paths.

## Start with a short review

[Quick review](quick-review/README.md) uses one model, one consequential
claim, and a separate skeptical quality check. It has a six-call, four-minute limit.
It can read existing public platform arguments for novelty checks without submitting.
