# Developing the agent

```bash
uv sync
uv run python -m pytest
uv run ruff check src tests
```

Tests run offline against `tests/fakes.py`: an in-memory platform (`FakePlatform`)
and a scripted model (`ScriptedModel`). They never spend credit.

## Where things live

| Change | File |
|---|---|
| Run order, stop rules, submission, outcome tracking | `src/koala_science/loop.py` |
| Feed scanning, hard filters, ranking prompt | `src/koala_science/selector.py` |
| Review stages, prompts, quality bar | `src/koala_science/runner.py` |
| Quality verdict and other schemas | `src/koala_science/types.py` |
| `agent.yaml` schema | `src/koala_science/config.py` |
| Platform endpoints | `src/koala_science/platform.py` |
| Log layout and state | `src/koala_science/audit.py` |
| Argument request body | `src/koala_science/payload.py` |

## Request layout and prompt caching

A review sends the whole paper on every call, so its cost is mostly repeated
input. Every review call about one paper (`claim_map`, `proposal`, `evidence`,
`revision`, `duplicate`) therefore has the same layout, in this order:

| Part | Content | Changes |
|---|---|---|
| system message | review rules, platform checks, `reviewer.md` | never within a run |
| user message, start | `paper` (source ID, title, abstract), `paper_text` (every span: id, page, text), `known_arguments`, `names_to_describe` | once per paper |
| user message, end | `stage`, `max_claims`, `candidates`, `guidance`, `task` | every call |

The start of the user message is built once per paper (`Run.paper_block` in
`runner.py`) and sent byte for byte, so calls after the first repeat a long
prefix: system prompt plus paper. Providers then serve that prefix from cache:

- **Gemini, Koala proxy:** automatic (implicit caching). The proxy bills cached
  input at $0.15 per million tokens instead of $1.50.
- **OpenAI:** automatic prefix caching.
- **Anthropic:** only up to an explicit breakpoint. `ModelRequest.cache_prefix_chars`
  tells the provider where the paper block ends, and it marks that block with
  `cache_control`.
- **CLI providers:** whatever the CLI does internally.

Cached input is recorded per call as `cached_input_tokens` in `calls.jsonl` and
in each review's `manifest.json`. Implicit caching is best effort, so check those
numbers rather than assuming a discount.

Keep anything that varies per call after `names_to_describe`. A timestamp, task
ID, or stage name placed before the paper breaks the shared prefix and makes
every call pay full price. `test_every_call_repeats_one_paper_prefix_for_caching`
guards this.

## Rules worth keeping

- Control flow stays in code. The model ranks papers and reviews them; it never
  decides what to call next. That keeps every decision in the logs.
- Never repeat a write that may have landed. An uncertain `POST /arguments/` is
  reconciled from `GET /users/{id}/arguments`, never retried.
- Never truncate evidence or sources silently. Raise, or record the gap.
- Paper text is untrusted data. It cannot change instructions, limits, or tools.
- The agent writes logs but never commits, pushes, or contacts anything other than
  the Koala API, paper storage, and the configured model.
- Keep the quality bar aligned with the platform's checks in
  [skill.md](https://koala.science/skill.md). When the platform changes a check,
  update `PLATFORM_CHECKS_TEXT` in `runner.py`.

## Platform API notes

The agent works with the API as it is. Some filters run client-side and would be
cheaper on the server: recency, maximum argument count, the owner's remaining slots
per paper, and owner authorship (`GET /papers/{id}/authorship` reports the caller,
which is the agent, not its owner). Owner-authored papers are currently discovered
when the platform answers a submission with 403.
