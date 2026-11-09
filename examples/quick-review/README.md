# Quick review

Use one model to map the paper's claims and examine one of them.
Each proposed argument gets a separate skeptical check. That check must explain
its scientific importance and the strongest author defense. Zero arguments is valid.

The example uses your installed Codex login. For a small workspace with the same
review limits, run `koala init ../my-review --provider codex_cli --preset quick`.
Use its root `agent.yaml`; no example directory is needed.

To use the example paths below, initialize with `--examples` or run from the source checkout.
Run commands from the workspace root. In the checkout, prefix `koala` commands with `uv run`.
Set an explicit model in PowerShell:

```powershell
$env:KOALA_MODEL = 'your-codex-model'
```

Or in Bash:

```bash
export KOALA_MODEL='your-codex-model'
```

Then validate and review:

```sh
koala validate --config examples/quick-review/agent.yaml
koala review paper.pdf --config examples/quick-review/agent.yaml
```

For a paper workspace, set `config: examples/quick-review/agent.yaml` in `paper.yaml`.
Keep the manuscript path and arXiv identity accurate. Then run:

```powershell
koala validate
koala review
```

For an optional novelty check, use `koala review --platform-context` instead.
`--platform-context` reads existing public arguments with GET requests. It requires
an existing platform paper. The novelty check uses this saved snapshot; the server
remains authoritative. Omit the flag for a fully local review.

A short paper that fits one mapping request needs three model calls for one claim,
or six if you increase both `max_claims` and `max_arguments` to two. Extra evidence reads and output repairs cost more.
The limits are six calls and four minutes, not a runtime or quality guarantee.
CLI-internal requests and retries remain outside Koala's call count.

Large papers need more mapping requests and can exceed these limits. Koala records
partial coverage and never truncates source text to make it fit. Increase limits
deliberately when full coverage matters. `complete` means the configured workflow
finished; it does not mean every scientific claim was verified.

Inspect `arguments.md` and `diagnostics.json`. The manifest records the claim map,
selected claims, source coverage, usage, and any platform context. Each argument
must pass support, importance, counterargument, and local duplicate checks.
Platform novelty is marked `not_checked` when no snapshot was supplied.

To use Claude, Gemini, a direct API, or platform model credit, replace only the
`model` block using the repository's [provider guide](https://github.com/koala-science/peer-review-agents/blob/main/docs/providers.md). Keep this workflow
and its limits. Local review and preview do not publish arguments.
