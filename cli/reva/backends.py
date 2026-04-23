"""Backend definitions: command templates and system-prompt filenames per backend."""

from dataclasses import dataclass

# Paper Lantern MCP server config, inlined into the claude-code command template.
# The JSON is wrapped in single quotes at the shell level so its internal double
# quotes pass through unchanged; `\'` escapes the single quotes inside the Python
# string. Braces are doubled ({{ / }}) so that reva's str.format() call in
# cli.py (which substitutes {prompt} for other backends) does not interpret them
# as format fields — the doubling collapses back to single braces at format time.
_PAPER_LANTERN_MCP_CONFIG = (
    '\'{{"mcpServers":{{"paperlantern":'
    '{{"type":"http","url":"https://mcp.paperlantern.ai/chat/mcp?key=pl_cd1099cd5b35f6c193f9"}}'
    '}}}}\''
)

_CODEX_KOALA_MCP_CONFIG = (
    '-c \'mcp_servers.koala.url="https://koala.science/mcp"\''
    ' -c \'mcp_servers.koala.bearer_token_env_var="COALESCENCE_API_KEY"\''
)


@dataclass(frozen=True)
class Backend:
    name: str
    prompt_filename: str  # backend-specific system prompt file (e.g. CLAUDE.md)
    command_template: str  # shell command; {prompt} is replaced with initial prompt
    resume_command_template: str | None = None  # command to resume last session
    # Shell command run after each invocation whose stdout is written to
    # last_session_id. Only used when resume_command_template contains
    # $SESSION_ID. When None and $SESSION_ID is present, the session ID is
    # parsed from the stream-json agent.log (claude-code default).
    session_id_extractor: str | None = None


BACKENDS: dict[str, Backend] = {
    "claude-code": Backend(
        name="claude-code",
        prompt_filename="CLAUDE.md",
        command_template=(
            'claude -p "$(cat initial_prompt.txt)"'
            " --dangerously-skip-permissions"
            " --output-format stream-json --verbose"
            f" --mcp-config {_PAPER_LANTERN_MCP_CONFIG}"
            " 2>&1 | tee -a agent.log"
        ),
        # session_id parsed from stream-json log by tmux.py (_EXTRACT_SESSION_ID_FROM_LOG)
        resume_command_template='claude --resume "$SESSION_ID" --dangerously-skip-permissions --output-format stream-json --verbose 2>&1 | tee -a agent.log',
    ),
    "gemini-cli": Backend(
        name="gemini-cli",
        prompt_filename="GEMINI.md",
        # Use $(cat) to safely handle multiline prompts; no resume since
        # headless sessions don't persist a resumable state.
        command_template='gemini --yolo -p "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
    ),
    "codex": Backend(
        name="codex",
        prompt_filename="AGENTS.md",
        command_template=(
            "codex exec"
            f" {_CODEX_KOALA_MCP_CONFIG}"
            " --skip-git-repo-check"
            ' --dangerously-bypass-approvals-and-sandbox "$(cat initial_prompt.txt)"'
            " 2>&1 | tee -a agent.log"
        ),
        # --last resumes the most recent session in the current working directory.
        # Re-send the initial work loop prompt so non-interactive resume has a task
        # to perform instead of falling back to interactive behavior.
        resume_command_template=(
            "codex exec resume"
            f" {_CODEX_KOALA_MCP_CONFIG}"
            " --last --skip-git-repo-check"
            ' --dangerously-bypass-approvals-and-sandbox "$(cat initial_prompt.txt)"'
            " 2>&1 | tee -a agent.log"
        ),
    ),
    "aider": Backend(
        name="aider",
        prompt_filename="AIDER.md",
        # aider auto-persists chat history in .aider.chat.history.md; no
        # explicit resume needed — context is available on every restart.
        command_template='aider --yes --message "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
    ),
    "opencode": Backend(
        name="opencode",
        prompt_filename="OPENCODE.md",
        command_template='opencode run --dangerously-skip-permissions "$(cat initial_prompt.txt)" 2>&1 | tee -a agent.log',
        resume_command_template='opencode run --session "$SESSION_ID" --dangerously-skip-permissions 2>&1 | tee -a agent.log',
        session_id_extractor=(
            'opencode session list --format json -n 1 2>/dev/null'
            ' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0][\'id\'] if d else \'\')"'
        ),
    ),
}

BACKEND_CHOICES = list(BACKENDS.keys())


def get_backend(name: str) -> Backend:
    if name not in BACKENDS:
        raise ValueError(f"Unknown backend: {name!r}. Choose from: {BACKEND_CHOICES}")
    return BACKENDS[name]
