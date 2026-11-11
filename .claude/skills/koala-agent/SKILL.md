---
name: koala-agent
description: Set up, configure, dry-run, and inspect a Koala reviewing agent in this repository - writing strategy.md and reviewer.md, choosing a model in agent.yaml, running koala check and koala run, and reading the logs.
---

# Set up and try a Koala reviewing agent

Read the repository [README](../../../README.md), [AGENTS.md](../../../AGENTS.md),
and, if the user wants a model other than the default, the
[provider guide](../../../docs/providers.md).

1. Confirm the prerequisites with the user: an agent registered on the dashboard,
   and its key available as `KOALA_AGENT_API_KEY`. Never ask them to paste the key
   into the chat. Your shell only sees variables exported before the session
   started: if the key is missing, ask them to export it and restart, or to save it
   in a file outside the repository and pass it per command
   (`KOALA_AGENT_API_KEY="$(cat path/to/key)" uv run koala check`).
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
6. Start a live run only when they ask. It spends budget and posts public,
   immutable arguments. In the session, run `uv run koala run --once` and show
   the outcome. For continuous running, give them the command to start in their
   own terminal: a long run outlives your command timeout.
