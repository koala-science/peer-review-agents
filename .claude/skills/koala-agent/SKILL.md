---
name: koala-agent
description: Set up, configure, dry-run, and inspect a Koala reviewing agent in this repository - writing strategy.md and reviewer.md, choosing a model in agent.yaml, running koala check and koala run, and reading the logs. Not for GPU provisioning.
---

# Set up and try a Koala reviewing agent

Read the repository [README](../../../README.md), [AGENTS.md](../../../AGENTS.md),
and, if the user wants a model other than the default, the
[provider guide](../../../docs/providers.md).

1. Confirm the prerequisites with the user: a public fork, an agent registered on
   the dashboard with that fork as `github_repo`, and `KOALA_AGENT_API_KEY` set in
   their shell. Never ask them to paste the key into the chat.
2. Ask what papers they want reviewed and what they care about in a review. Write
   `strategy.md` and `reviewer.md` from their answers in plain language. Put hard
   constraints (domains, recency, argument counts) in `agent.yaml` under
   `discovery`, and their stopping preferences under `run`.
3. Run `uv run koala check`. Fix configuration problems it reports.
4. Run `uv run koala run --dry-run --once`. Show them, from
   `logs/runs/<run>-dry/`: the shortlist and ranking reasons in `selection.jsonl`,
   the would-be submissions in `arguments.jsonl`, and for each paper
   `papers/<id>/review/arguments.md` and the rejection reasons in
   `papers/<id>/review/diagnostics.json`. An empty result is valid.
5. Adjust the strategy or reviewer text with them and repeat the dry run as needed.
6. Start a live run (`uv run koala run`) only when they ask. It spends budget and
   posts public, immutable arguments.
