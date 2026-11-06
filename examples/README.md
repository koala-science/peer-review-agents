# Review examples

Each example keeps its configuration, instructions, and supporting files together.
These directories are the source for the examples included by `koala init`.

| Example | Purpose | Start here |
| --- | --- | --- |
| [TOOD](tood/README.md) | Review a real continual OOD detection paper with methods, results, and evidence agents. | [agent.yaml](tood/agent.yaml) or [offline.yaml](tood/offline.yaml) |
| [Fair comparison](fair-comparison/README.md) | Inspect a small reviewer with a fictional paper and a confounded comparison. | [agent.yaml](fair-comparison/agent.yaml) |

## Inspect TOOD

```text
examples/tood/
  agent.yaml             Local-model configuration
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
```

Follow the [TOOD guide](tood/README.md) to download the paper and run a review.
When working in this checkout, prefix its `koala` commands with `uv run`.
Store downloaded papers in `inputs/` and results in `runs/`. Both directories are ignored by Git.

The offline provider checks extraction and export. It does not make scientific judgments.
The model configuration in `agent.yaml` is used for an actual review.

## Packaging

Edit these root examples directly. The wheel maps them into
`koala_science/templates/examples/`, and editable installs read this directory.
Generated workspaces keep the same `examples/tood/` and `examples/fair-comparison/` paths.
