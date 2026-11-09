# Example: fair comparison reviewer

This agent checks whether a reported comparison supports its stated conclusion.
It uses one configured model for separate proposal and evidence tasks. No child
agents are required. The coordinator still applies the same acceptance checks.

The example is runnable from the repository root or a workspace created by `koala init --examples`.
In this checkout, prefix the `koala` commands below with `uv run`.

## Run it

From the workspace root, set `KOALA_MODEL`, `KOALA_MODEL_BASE_URL`, and
`KOALA_MODEL_API_KEY` for your compatible API. Then run:

```bash
koala validate --config examples/fair-comparison/agent.yaml
koala review examples/fair-comparison/paper.md --config examples/fair-comparison/agent.yaml --output runs/fair-comparison
```

Model requests can incur provider charges. For an unauthenticated local endpoint,
remove `api_key_env` from this example's model block. For Koala's funded proxy,
replace that block using the [provider guide](https://github.com/koala-science/peer-review-agents/blob/main/docs/providers.md#use-koalas-funded-model-proxy).
That guide also shows PowerShell and Bash commands for credential entry.
Remote providers receive the supplied source text.

The paper is a small fictional fixture. It describes different training durations,
then attributes the accuracy difference to architecture alone. One useful criticism
would explain why this comparison does not isolate architecture from training duration.
That observation does not establish which model would win under equal conditions.

Inspect `runs/fair-comparison/arguments.md` and its cited text in `sources.json`.
Read diagnostics and coverage before drawing conclusions. Actual output varies
with the model; this is a workflow example, not a quality benchmark.

## Use your own paper

```bash
koala review path/to/paper.pdf --config examples/fair-comparison/agent.yaml --output runs/my-comparison
```

Edit `instructions.md` to change the review focus. Edit `agent.yaml` to change the
model or budget. Use a new output directory for each run.

The same example works from Python:

```python
from koala_science import Agent

agent = Agent.from_config("examples/fair-comparison/agent.yaml")
result = agent.review("examples/fair-comparison/paper.md")
result.save("runs/fair-comparison-python")
```
