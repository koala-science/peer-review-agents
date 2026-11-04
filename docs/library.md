# Library contracts

## Configuration

`schema_version: 1` is required. Unknown fields fail validation. The CLI reads
`./agent.yaml` unless `--config` selects another file. Paths resolve relative to
the YAML file that contains them. `${NAME}` reads the process environment; missing
values fail validation. Keys remain environment references. `.env` is not loaded.

Children have `role: proposer` or `role: verifier`. They inherit shared limits and
the root model. A complete child model block overrides its provider. Nested
delegation and duplicate names are rejected. Custom Python runs only during review.

`Agent.from_config(path, provider=instance)` replaces root and inherited provider
construction. Explicit child model overrides retain their configured providers.

## Model providers

A provider implements `async generate(ModelRequest) -> ModelResponse`. The request
contains messages, model name, JSON schema, output limit, and timeout. The response
contains text, actual model identifier, and optional usage counts. Koala validates
every response, including native structured output.

`compatible_api` appends `/chat/completions` to `base_url`. It requires JSON-schema
output support and does not silently fall back to unstructured requests.
`koala_proxy` appends `/v1beta/models/{model}:generateContent` to a base ending in
`/llm`. It sends an agent key as a bearer credential. It excludes thought parts
from returned text and includes reported thinking tokens in output usage.

For a custom service:

```yaml
model:
  provider: custom
  name: ${KOALA_MODEL}
  factory: providers/custom_api.py:build_provider
  parameters:
    endpoint: ${CUSTOM_MODEL_ENDPOINT}
    api_key_env: CUSTOM_MODEL_API_KEY
```

Adapt the generated example's request and response fields to your service.
Custom providers are trusted Python code. They must respect request timeouts.
Raise `koala_science.providers.ProviderError` with `retryable=True` for transient
service failures. Never put credentials or raw response bodies in error messages.

## Existing orchestration

Use `Agent.from_backend(backend, config="agent.yaml", provider=verifier_provider)`.
The backend implements `async propose(context, limits, budget) -> Proposals` and
declares `supports_budget = True`. See `providers/python_backend.py` in a workspace.

Before each model request, await `budget.reserve_call()`. Report its response with
`budget.report_usage(response)`. Return at most `max_candidates_per_task` candidates.
The coordinator applies its deadline, then performs evidence and duplicate checks.
Python extensions are trusted code; cooperative callbacks cannot sandbox deliberate
budget bypasses. A declaration is an interface contract, not proof of isolation.

## Evidence and acceptance

Each source stores a SHA-256 hash and a content-derived ID. PDF locators use
physical pages starting at one. Text and Markdown locators use one-based line
ranges. Spans preserve extracted text; very long lines/pages have multiple spans.
Whitespace normalization collapses Unicode whitespace to single spaces. It does
not change case, punctuation, spelling, or PDF extraction errors.

Quotes must occur in their cited span and have matching source and locator fields.
Only spans supplied to a proposal can support its initial candidate. The verifier
receives that context and a source index. It can request one additional set of spans
through `requested_span_ids`. The coordinator supplies those spans in another bounded
evidence task. Unresolved context stays uncertain. Revisions can cite the added spans.

The reader groups Markdown sections and PDF pages into bounded tasks. It records
unread spans and blank PDF pages. Semantic interpretation happens in proposal and
verification calls; headings alone do not establish scientific claims or coverage.
Scanned PDFs fail when they contain no usable text. Inputs above 100 MiB fail
before extraction. OCR, automatic search, and experiment execution are out of scope.

Schema and source checks are mechanical. Atomicity, support, absence scope, and
semantic duplicates involve model judgments. They can be wrong. A revision gets
another evidence decision. Exact duplicate statements are removed mechanically;
other accepted conclusions receive a model comparison. Distinct or conflicting
conclusions can share evidence.

## Budgets and results

All tasks share a call budget and monotonic deadline. Each transient failure has
at most two retries. Malformed output has one repair attempt. Every attempt uses
a call slot. Authentication and credit errors are not retried. New proposals leave
capacity for first-pass evidence review; retries and revisions can still exhaust it.

Input size uses a conservative UTF-8 byte bound rather than a provider tokenizer.
This can produce partial coverage sooner than the nominal token limit suggests.
No text is silently truncated. Reduce task instructions or increase limits when
appropriate. Output size is requested from the provider and truncated responses fail.

Complete runs may contain no arguments. Partial runs preserve accepted work and
record missing stages or coverage. Failed runs have no accepted arguments.
`result.save(path)` stages all five artifacts before replacing a new or empty
directory. CLI runs keep a sibling `.NAME.journal.jsonl` until export succeeds.
After an interruption, inspect the journal and choose a new output destination.
The Python API returns diagnostics with the result; durable journaling is a CLI feature.

Run manifests contain limits, tasks, source hashes, prompt digests, model identifiers,
and available usage. They do not contain provider credentials or pricing estimates.
Source snapshots and rationale remain public review explanations, not private reasoning.
