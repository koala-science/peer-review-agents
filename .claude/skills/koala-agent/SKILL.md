---
name: koala-agent
description: Set up, configure, dry-run, and inspect a Koala reviewing agent in this repository - writing strategy.md and reviewer.md, choosing a model in agent.yaml, running koala check and koala run, and reading the logs.
---

# Set up and try a Koala reviewing agent

Read the repository [README](../../../README.md), [AGENTS.md](../../../AGENTS.md),
and, if the user wants a model other than the default, the
[provider guide](../../../docs/providers.md).

1. Confirm they have registered an agent on the dashboard. Then ask them to copy
   its key and save it by typing `! pbpaste | uv run koala login` here (Linux:
   `wl-paste`, Windows PowerShell: `Get-Clipboard`), or `uv run koala login` in their
   own terminal. It prints the agent's name when the key works. Never ask for the
   key in chat, and never read or print `.koala_key`.
2. Tell them the default: the agent reviews the least-reviewed papers first, in any
   field. Ask whether they want to change that (fields, kinds of papers, recency)
   and what they care about in a review. Leave `strategy.md` as it is if they keep
   the default; otherwise write it, and `reviewer.md`, from their answers in plain
   language. Put hard
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
