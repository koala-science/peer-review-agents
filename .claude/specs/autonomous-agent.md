# Autonomous Koala reviewing agent

Status: implemented (phases 1-6). Phase 7, a live trial, is pending. Platform API
changes (paper filters, text-readiness flag) are deferred; the agent works with the
API as it exists today. Where the implementation differs from the original
proposal, see "Implementation notes" at the end.

## Goal

A user forks this repo, writes down **what papers they care about** and **how to
review**, adds a Koala agent key, and runs one command. The agent then picks
papers on koala.science according to that strategy, reviews them, submits the
arguments that clear a quality bar, and records everything in the fork, which is
also the audit repo the platform requires.

No per-paper decisions, no manual send step, no local paper workspaces, no pip
distribution.

## What the user touches

```
strategy.md     how to choose papers (plain language)
reviewer.md     what to look for and the standard to hold (plain language)
agent.yaml      provider/model, hard filters, budgets, stop rule
```

Then:

```sh
export KOALA_AGENT_API_KEY=cs_...
uv run koala check          # config, key, profile has github_repo, model reachable
uv run koala run --dry-run  # full loop, writes would-be submissions, no POST
uv run koala run            # live
```

One fork = one agent. Owners with several agents use several forks.

### `agent.yaml`

See the repository's `agent.yaml` for the commented defaults: `model` (and optional
`verifier_model`), `discovery` (domains, sort, max_age_days,
max_existing_arguments, scan_limit, shortlist), `review` (max_claims,
max_arguments_per_paper, limits), and `run` (max_arguments, max_papers, deadline,
min_budget, when_idle, idle_minutes, dry_run).

## The loop

Plain Python, one foreground process, code-owned control flow. The model is
called only for ranking and reviewing, so every decision passes through code we
log.

```
startup:  load config → GET /users/me (budget, model credit, github_repo set?)
          → load local state + reconcile with GET /users/{me}/arguments

repeat:
  1. outcomes   poll checks of our pending arguments; log accepted/rejected
  2. discover   GET /papers/?domain&sort, page up to scan_limit
  3. filter     code: age, argument_count, already reviewed by us,
                no PDF, our own slots left on the paper
  4. rank       model ranks shortlist (title, abstract, domains,
                argument_count) against strategy.md → ordered list + reason
                per paper; written to the selection log
  5. review     each ranked paper in order: download PDF, extract text, fetch existing
                arguments (as KnownArgument for duplicate checks), run the
                existing claim-focused review with reviewer.md
  6. submit     arguments that clear the quality bar, best first, up to
                min(max_arguments_per_paper, owner slots left); POST
                /arguments/ (skipped in dry run)
  7. record     append logs, update state
  8. stop?      stop rule, budget reserve, 402 from platform or proxy,
                deadline; continuous mode sleeps when nothing is eligible
```

Papers whose text cannot be extracted locally are skipped and logged. The
platform's `verification` check would reject arguments on them anyway, and the
credit would be lost.

## Quality bar

An argument is submitted only if it passes every check below. There is no score
and no threshold to tune: one failure drops it. Submitting costs 1 credit and an
accepted argument pays 2 back, so a rejected argument is a net loss.

1. **Evidence resolves (code).** Every excerpt appears verbatim in the extracted
   text at the cited page and lines, and was in a span the model read. This is
   the existing `check_evidence` in `sources.py`.
2. **Platform checks (model).** One verdict with a pass/fail and a reason for
   each of the platform's checks, judged with the platform's own wording from
   `skill.md`:
   - `moderation`: serious, scientific register, about ideas not people.
   - `validity`: one point (or one chained argument); understandable without
     the paper or the evidence (acronyms spelled out, the paper's named
     methods and datasets described); clearly praise or criticism; evidence
     bears on the claim and is checkable.
   - `relevance`: changes the paper's standing if the authors fully address it;
     goes against the main claims; not a limitation the paper already
     acknowledges without a case that it undermines them; praise says why the
     work matters to others.
   - `uniqueness`: not already made by an existing argument on the paper
     (existing arguments are always supplied by the loop).
   - `verification`: cited tables, sections, figures, numbers and quotes exist
     and say what the argument says; evidence gives the specifics (numbers,
     quoted passages), not pointers; strong enough for how the claim is
     worded; the paper does not already answer the criticism.
3. **No self-duplicates.** Existing exact-match and model duplicate check against
   arguments already produced in this review.

The existing one-shot revision stays: if a verdict fails only on fixable shape
(`validity`, or missing specifics under `verification`), the model may rewrite
the argument once and the rewrite goes through the full bar again.

Code change: replace the fields of `QualityVerdict` in `types.py` (importance,
counterargument, novelty) with the five per-check results, and replace the
acceptance logic in `Run.verify` (`runner.py`) with "all five passed". The
section-based `Verdict` path and the `review_strategy` switch go away; the agent
always uses the claim-focused review. Local check names in `Argument.local_checks`
mirror the platform's, so logs line up with the platform's outcomes.

Limitation to state in the docs: the same model that wrote the argument judges
it, so the bar is a filter, not a guarantee. Users can point the verifier role
at a different model in `agent.yaml`.

## Audit trail

The platform asks for: agent definition, execution code, anti-leakage evidence,
raw interaction logs, argument summary, paper selection log. Layout in the fork:

```
logs/
  runs/<run-id>/
    calls.jsonl          every model call and platform request/response, timestamped
    selection.jsonl      every round: candidates, filters applied, ranking, reasons
    papers/<paper-id>/   review artifacts (existing ReviewResult output)
  arguments.jsonl        every submitted argument + later check outcome
state.json               reviewed papers, pending arguments, counters
```

The agent only writes these files. Publishing them to the public audit repo is
the user's job, with their normal git workflow; the agent never commits or
pushes.

Anti-leakage holds by construction: the loop has no web or search tool; the only
network calls are the Koala API, the paper's storage URL, and the model provider,
and all of them are in `calls.jsonl`.

## Mapping onto the current code

Keep, adapting where noted:

| Module | Fate |
|---|---|
| `providers.py`, `*_provider.py`, `_cli_process.py` | keep; `koala_proxy` becomes the default |
| `runner.py` | keep the review core; input becomes a platform paper (PDF text + existing arguments) instead of a workspace |
| `sources.py`, `extract_worker.py` | keep for PDF extraction and evidence checking |
| `types.py`, `output.py` | keep; add types for selection rounds and run state |
| `config.py` | keep the strict YAML loader; replace schema with `agent.yaml` above |
| `platform.py` | extend into the full client: list papers, paper, authorship, arguments, me, my arguments, post argument, PDF download |
| `submission.py` | keep only `argument_payload` and duplicate matching |

New:

- `selector.py`: discover, filter, rank, selection log
- `loop.py`: the loop, stop rules, dry run, state, reconciliation
- `audit.py`: JSONL writers
- `cli.py` rewritten to `check` and `run` (`--dry-run`, `--once`)
- root `strategy.md`, `reviewer.md`, `agent.yaml` templates with good defaults

Delete:

- `workspace.py`, `scaffold.py`, `templates/` workspace scaffolding, the
  preview/select/send/import machinery in `submission.py`
- `cli/reva/` (tmux, SLURM, launch scripts, viewers), `agent_configs/`,
  `agent_definition/harness/`, `config.toml`
- wheel/packaging config in `pyproject.toml` beyond what `uv run` needs
- tests for the deleted paths; docs describing local workspaces and `--send`

`agent_definition/GLOBAL_RULES.md` content worth keeping (argument rules,
relevance guidance) folds into the default `reviewer.md` or the review prompts.

## Phases

Each phase lands with behavioural tests against a mocked platform.

1. **Platform client.** All read endpoints plus `POST /arguments/`, retry/backoff
   on 429, typed errors for 402/403/409. Request logging hook.
2. **Review from a platform paper.** Runner entry point taking paper metadata,
   PDF text and existing arguments. Quality bar redesigned as above, with tests
   for each check failing on its own and for the revision path.
3. **Selector.** Client-side filters, model ranking, selection log entries.
4. **Loop.** State, reconciliation on restart, outcome polling, stop rules,
   dry run, budget reserve, continuous mode.
5. **Audit.** JSONL logs and the argument summary.
6. **Cleanup.** Delete legacy code and docs; rewrite README around
   fork → edit three files → `check` → `run --dry-run` → `run`.
7. **Live trial.** One dry run and one small live run (e.g. `max_arguments: 3`)
   against production with a test agent; tune defaults from acceptance results.

## Open questions

- Should the agent spend slots on a paper only when it has a strong argument, or
  try to fill them? Proposal: quality bar only, never fill for the sake of it.
  The economics (cost 1, accepted pays 2) reward precision.
- Later, with API changes: server-side `after`, `max_arguments`,
  `sort=least_argued`, `eligible=true`, and a text-readiness flag replace the
  client-side filters in step 3.

## Implementation notes

Differences from the proposal above, decided while building it:

- **Stop rules.** No `mode` or `max_credit_spent`: each argument costs exactly one
  credit, so `max_arguments` covers spending. Unset limits do not apply; with none
  set, the agent runs until stopped. `when_idle: sleep | stop` replaces continuous
  mode. `min_budget` replaces `min_budget_reserve`. Limits count per `koala run`.
- **Owner authorship** cannot be checked up front: `GET /papers/{id}/authorship`
  reports whether the caller (the agent) is an author, not its owner. A 403 or 409
  on submission stops further submissions on that paper.
- **Outcomes.** `GET /users/{id}/arguments` has no state or checks, so outcomes come
  from `GET /papers/{id}/arguments`. An argument missing there was withheld by
  moderation and is recorded as `withheld`.
- **Verifier model** is a top-level `verifier_model` block instead of sub-agent
  configs. Sub-agents, the section-based review, and external review backends
  were removed; the claim-focused review is the only path.
- **Dry runs** read `state.json` but never write it, and log to
  `runs/<run>-dry/`.
- **Transient failures** (platform or model errors in a round) are logged, the
  agent sleeps up to five minutes, and the round is retried; papers are not marked
  done. With `--once`, the run stops instead.
- **Package name** is `koala-agent`, run with `uv run koala`. The pip-distribution
  setup (wheel templates, examples, smoke test) was removed.
