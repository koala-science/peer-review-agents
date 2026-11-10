---
name: access-fpt-cloud
description: Manage an existing user-provided FPT GPU environment when the user explicitly requests FPT infrastructure work. Not required for Koala local paper review.
---

# Optional FPT infrastructure

Use only for a requested GPU task. Establish the existing account, target environment,
budget, and stopping condition before provisioning billable resources.
Reuse authorized credentials from private state. Do not create accounts,
claim promotional credits, or run `fpt_signup.py` as part of onboarding.

Inspect `fpt_manage.py` before using its commands. Use `uv run` for Python tools.
Keep state files and SSH keys private. Delete only authorized task resources.
Report remaining billable resources.

Legacy signup helpers remain for historical compatibility. The local review
library never invokes them. This skill does not grant permission to use them.
