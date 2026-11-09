# Customize and inspect a review

## Keep a review fast and useful

Choose **Quick** during `koala init`, or pass your chosen `--provider` with `--preset quick`.
Use the generated root `agent.yaml` and set an explicit `KOALA_MODEL`.
The optional `examples/quick-review/agent.yaml` has the same review limits and uses Codex.
Example files are included only with `--examples`.

```powershell
koala validate
koala review                     # Local sources only
```

The workflow maps consequential claims to evidence across sections before proposing
arguments. A separate skeptical check must explain the scientific contribution and
address the strongest author defense. A correct quotation or routine design choice
does not suffice. Returning zero arguments is a valid outcome.

Quick examines one claim with a limit of six model calls and four minutes.
One mapping request, one proposal, and one verification normally use three calls. Larger papers,
additional evidence reads, and output repairs require more. These limits bound work.
They do not guarantee runtime, scientific quality, or platform acceptance.

Default examines two claims with ten calls and six minutes. Both presets use the
same evidence and quality checks. `arguments.md` reports elapsed time and call count.
For an empty result, it distinguishes no proposed candidates from candidates that
failed local checks. Inspect `manifest.json` and `diagnostics.json` before another run.
There is nothing to submit when the accepted argument list is empty.

For an optional novelty check, use `koala review --platform-context` instead.
`--platform-context` requires an arXiv workspace, the claims strategy, and an existing platform paper. It reads
public arguments only, creates no platform records, and saves the snapshot in the
manifest. Lookup failures stop the review. Without it, platform novelty is explicitly
`not_checked`. The server checks current uniqueness again after submission.

Old configurations retain the section-based workflow. Opt in with
`review_strategy: claims` and `max_claims: 2`. Read the [workflow contract](library.md#claim-focused-review)
for coverage, budgets, and quality checks. Existing workspaces are not overwritten.


## Examples and review instructions

Try the included [fair comparison agent](../examples/fair-comparison/README.md).
`koala init --examples` copies it into `examples/fair-comparison/` in your workspace. It has
focused instructions, bounded model calls, and a fictional paper with a confounded comparison.

```bash
koala validate --config examples/fair-comparison/agent.yaml
koala review examples/fair-comparison/paper.md --config examples/fair-comparison/agent.yaml --output runs/fair-comparison
```

These commands require the compatible API environment variables from the [provider guide](providers.md#credentials-and-endpoints).

For a real manuscript, use the [TOOD example](../examples/tood/README.md).
It includes methods, results, and evidence agents for continual OOD detection.
Run its offline smoke test without a model, then use a local model for scientific review.
The paper downloads separately. `koala init --examples` includes the example under `examples/tood/`.

In the TOOD example directory, edit `instructions.md` for shared review guidance.
Edit `agents/methods.md`, `agents/results.md`, or `agents/evidence.md` for each agent's focus. YAML controls
models and limits. Children inherit the root model unless they override it.

Use `--config path/to/agent.yaml` to select another config. Paths inside each YAML
file resolve relative to that file. Koala never searches parent directories.

With `--examples`, the scaffold includes custom API and Python backend examples in `providers/`.
See [the library guide](library.md) for their contracts and limitations.

## Inspect and share artifacts

Read `arguments.md`, then compare its quotations with `sources.json` and the manuscript.
`arguments.json` preserves full local records. `diagnostics.json` explains rejected candidates.
`manifest.json` records tasks, coverage, limits, model identifiers, and available usage.
Source snapshots contain manuscript text. Review artifacts before sharing private source material.
See [troubleshooting](troubleshooting.md#empty-or-partial-results) for empty and partial results.
Platform exports and optional publication are covered in [submission](platform-submission.md).
