# Release validation

The distribution is not published by this change. Package-name ownership, license
obligations, live model compatibility, and scientific quality remain release gates.

Run the offline suite with `uv run python -m pytest`. Tests use deterministic
providers and HTTP mocks. Build a wheel with `uv build` and install it outside the
checkout. CI exercises Python 3.10 and 3.14 on Windows, macOS, and Linux.

Legacy shell and permission tests require a working POSIX environment. They do
not establish Windows support for tmux or SLURM. The local library is portable.

## Live proxy smoke test

Use a designated test account and endpoint. Set `KOALA_SMOKE_BASE_URL` to the
proxy base ending in `/llm`, `KOALA_SMOKE_MODEL` to an allowed model, and
`KOALA_SMOKE_API_KEY` to its agent key. Then run:

```bash
uv run python -m pytest -m network tests/test_local_contracts.py -k live_proxy
```

This test spends model credit. Mock tests prove the client wire contract only;
they do not prove deployed credentials, model support, Redis, PostgreSQL, or credit
settlement. The backend's own integration suite remains a separate check.

## Human evaluation

Before a public quality claim, assemble 20 licensed papers across research areas.
Two reviewers independently label accepted arguments for atomicity, source accuracy,
support, duplication, and usefulness. Record disagreements and adjudication.

Targets are 100% valid locators, 95% atomic arguments, and 90% supported arguments.
Report sample counts and uncertainty, useful-argument yield, coverage, usage, and
elapsed time. Require a supported argument on 80% of fixtures known to contain one.
These are targets, not measured results. The bundled CC0 sample is synthetic and
does not replace a scientific evaluation set.
