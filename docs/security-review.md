# Review of the local agent library

Reviewed commit range: `ed13542..deebc71` (the four template-update commits).
Review date: 2026-11-03.

The original changes needed fixes before further release testing. The review found
security, correctness, and auditability issues that the initial test suite missed.
The fixes below are covered by regression tests in `tests/test_review_hardening.py`.

## Findings and fixes

| Priority | Finding | Fix |
|---|---|---|
| P1 | Model statements and source quotes could insert active HTML and remote images into permissive Markdown renderers. | Escape all untrusted report fields. Preserve original text in JSON. |
| P1 | A custom provider's exception message could copy an API key into diagnostics and the manifest. | Persist controlled error categories and HTTP status descriptions, not custom exception text. |
| P1 | PDF extraction ran before the deadline started. HTTP responses and extracted text had insufficient size bounds. | Include extraction in the deadline; terminate PDF workers on timeout/cancellation; cap inputs, extracted text, spans, pages, and responses. Reject compressed HTTP responses before decoding. |
| P1 | The installed environment contained packages with published advisories. | Raise security floors and update AnyIO, IDNA, Starlette, and the lockfile. Keep the PDF parser floor at the audited version. |
| P2 | A repair attempt reset the transient retry counter, allowing more than two retries per task. | Share the retry allowance across the initial and repair attempts. |
| P2 | An external backend could return no work while the coordinator claimed it inspected every source span. | Require explicit coverage through BackendResult. Old results have unknown coverage; unknown span IDs fail. Copy source data before handoff. |
| P2 | PDF hashing and extraction reopened the path separately, so changed bytes could receive the wrong hash. | Parse the same byte snapshot that was hashed. |
| P2 | Duplicate YAML fields silently overrode values; recursive aliases crashed expansion; booleans and infinite values could pass numeric validation. | Reject duplicate fields, recursive aliases, excessive nesting, coercions, and non-finite limits. Validate provider URLs before requests. |
| P2 | An invalid paper path left a journal that blocked a corrected rerun. Journal creation also had a check-then-write race. | Create journals exclusively; remove an untouched journal after an input failure. Preserve journals containing task diagnostics. |
| P2 | Custom provider modules using dataclasses and postponed annotations failed to import. | Register modules during import and restore the module registry on failure. |
| P2 | A successful repair retained the original prompt's digest. Backend provenance also claimed a digest the coordinator could not know. | Record the actual repaired prompt digest; mark unavailable external provenance as unknown. |

The review also confirmed that default review tasks do not execute commands from
papers, publish arguments, browse the web, or open model-invented source paths.
Model output cannot increase the coordinator's task or call limits.

## Dependency audit

The initial audit reported advisories in AnyIO 4.13.0, IDNA 3.13, and Starlette 1.0.0.
Relevant upstream advisories cover [AnyIO TLS hostname handling](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6),
[IDNA resource exhaustion](https://github.com/kjd/idna/security/advisories/GHSA-65pc-fj4g-8rjx),
and [Starlette request handling](https://github.com/Kludex/starlette/security/advisories).

The installed versions are now AnyIO 4.16.0, IDNA 3.20, and Starlette 1.10.0.
The repeat audit reported no known vulnerabilities in the scanned third-party
packages. Editable local packages were excluded from the advisory lookup; their
code was reviewed and tested separately. An advisory lookup does not prove absence
of undisclosed vulnerabilities.

Reproduce the environment audit with:

```bash
uv run --with pip-audit python -m pip_audit --path .venv/Lib/site-packages --skip-editable
```

That path is for Windows. On POSIX, use the environment's Python-version-specific
`site-packages` directory. The audit queries public package advisory services.

## Validation

- Full offline suite: **271 passed**, 10 POSIX-only tests skipped on Windows, two network tests excluded.
- The review added 27 regression and boundary cases, including actual PDF extraction and worker termination.
- Ruff passed for the library and local-review test files.
- The wheel and source distribution built successfully.
- An isolated wheel installation outside the checkout passed CLI, Python, template, and text-PDF checks.
- The dependency audit reported no known vulnerabilities after the updates.

## Remaining boundaries and release gates

Custom Python providers and backends are trusted extensions. They can access the
host process and bypass cooperative budgets deliberately. Only load code you trust.

The PDF worker is time-bounded and its output is limited. It is not an OS sandbox
and has no hard memory quota. Public hosting of arbitrary uploaded PDFs needs
additional isolation and operating-system resource limits.

Local model judgments can still be wrong or influenced by malicious paper text.
Exact quote matching proves a quote exists, not that its conclusion is sound.

Live proxy authentication, funded credit settlement, and model-specific structured
output remain untested here. Remote OS/Python CI and human scientific evaluation
are still release gates. No platform submissions or paid model calls were made.
