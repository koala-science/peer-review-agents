# Prompt for platform-side Claude Code: simplify comment URL requirement

Copy-paste the block below into a Claude Code session running in the **Koala Science platform repo** (not this one). It's self-contained and briefs a fresh agent from zero.

---

I need you to simplify how comments capture their reasoning URL on the Koala Science platform.

**Current behavior (to be changed):** Every comment posted via the API must include a `github_file_url` field. The platform validates that this URL points at a file that has already been committed and pushed to a GitHub repo — agents have to write a reasoning file, commit it, push it, then reference the resulting raw/blob URL in the comment body. This commit-then-cite dance is too much friction for what should be a lightweight "here's a link to my reasoning" field.

**Desired behavior:**
- Keep the field. Comments still carry `paper_id`, `content_markdown`, and a URL. The URL field name can stay `github_file_url` (for backwards compatibility) or be renamed to `url` — your call based on what's least disruptive to existing callers.
- Validate only that the URL is a well-formed GitHub URL — i.e., `https://github.com/<anything>`. Reject obvious non-GitHub URLs, malformed URLs, and empty strings.
- Drop all of the following validations (they are the "too much"):
  - Whether the file exists at that URL.
  - Whether the commit SHA in the URL has been pushed.
  - Whether the URL resolves to a raw/blob file vs. a tree/page/issue/PR.
  - Whether the URL lives in a repo the agent owns or has pushed to.
- Preserve the requirement that the field is present and non-empty — comments without any URL should still be rejected. The change is about *what counts as valid*, not about making it optional.

**What to do:**
1. Explore the repo to find where comments are created/validated. Start with a grep for `github_file_url`, then trace the validation path.
2. Identify every check that currently enforces "the URL resolves / the file has been committed / the URL is a raw blob / the repo is owned by the caller" etc. These are the ones to remove.
3. Replace them with a single check: is this a well-formed GitHub URL (`github.com` host, HTTPS scheme)? Use the platform's existing URL-parsing utilities if any; otherwise `urllib.parse` in Python or the equivalent in whatever language the platform is written in.
4. Update tests: any test that exercises the dropped validations either deletes with the validation or is rewritten to test the new format-only rule. Add tests for: valid github URL accepted; non-github URL rejected; empty rejected; malformed URL rejected.
5. Update any API docs, OpenAPI schema, or `skill.md` entry on the platform that describes the comment payload so it reflects the new rule.

**Constraints:**
- Do not change the `paper_id` or `content_markdown` fields.
- Do not make the URL optional — it's still required, just validated differently.
- Do not break existing comment payloads that were written against the old API — if you rename the field, keep the old name as an accepted alias.

**When you're done:** run the platform's full test suite, confirm all tests pass, and summarize the diff. Do not deploy — that's the operator's call.
