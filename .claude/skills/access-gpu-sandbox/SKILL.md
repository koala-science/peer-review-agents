---
name: access-gpu-sandbox
description: Access an authorized McGill-NLP GPU sandbox for explicitly requested infrastructure work. Not required for local Koala reviews. Never use the shared sandbox account.
---

# GPU Sandbox

API + docs: https://gpu-sandbox-keys-upload.mcgill-nlp.org/api/docs

## ⚠️ Never SSH as `sandbox`

`sandbox` is the Docker host's internal account. Every agent must provision its own named user via the API. If you find yourself typing `ssh sandbox@...` — stop.

## Local state

All state lives in `${CLAUDE_SKILL_DIR}` and is gitignored:
- `.ssh/id_rsa`, `.ssh/id_rsa.pub` — SSH key pair
- `.username` — provisioned username

## Workflow

**If `.username` and `.ssh/id_rsa` both exist**, read the username and SSH in.

**Otherwise**, obtain authorization for sandbox provisioning before following these steps:
1. `ssh-keygen -t rsa -b 4096 -N "" -f ${CLAUDE_SKILL_DIR}/.ssh/id_rsa`
2. Pick a unique lowercase username (e.g. from the repo/session name, not hardcoded).
3. `POST /api/keys` with the username + public key (see `/api/docs` for the exact fields).
4. Write the username to `${CLAUDE_SKILL_DIR}/.username`.

## Connecting

Get SSH host/port from `GET /api/info`, then:

```bash
USER=$(cat ${CLAUDE_SKILL_DIR}/.username)
ssh -p <port> $USER@<host> -i ${CLAUDE_SKILL_DIR}/.ssh/id_rsa
```
