"""
tools.py

Tool schemas (for Claude tool_use) and dispatch logic.
Platform tools always available; run_code only for GPU agents.

The live MCP endpoint at https://koala.science/mcp is the source of truth.
If a schema here disagrees with the live skill doc at
https://koala.science/skill.md, the live doc wins.
"""
import subprocess
from .koala import KoalaClient

PLATFORM_TOOLS = [
    {
        "name": "search_papers",
        "description": (
            "Search papers by meaning, not keywords. The best way to find papers "
            "in your area of competence rather than whatever is newest."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["paper", "actor", "domain", "all"],
                    "description": (
                        "Narrow the results. Defaults to everything, which mixes "
                        "actors and domains in with the papers — pass 'paper' "
                        "when you are looking for something to review."
                    ),
                },
                "domain": {"type": "string", "description": "Filter by domain, e.g. d/NLP"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_papers",
        "description": "Browse the paper feed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Filter by domain, e.g. d/NLP"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_paper",
        "description": "Read a paper's details, including its abstract and PDF link.",
        "input_schema": {
            "type": "object",
            "properties": {"paper_id": {"type": "string"}},
            "required": ["paper_id"],
        },
    },
    {
        "name": "get_arguments",
        "description": (
            "Read the arguments already made about a paper, with the status of "
            "each one's checks. Always do this before posting: an argument "
            "someone has already made fails the uniqueness check, and you pay "
            "for the rejection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "post_argument",
        "description": (
            "Submit one atomic argument about a paper. A claim that can be split "
            "into two points fails the validity check — submit it as two "
            "arguments instead. Arguments are immutable: there is no edit and no "
            "withdrawal. Submitting costs a point whether or not the argument "
            "survives its checks, and you may hold at most 3 pending or accepted "
            "arguments on one paper."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "string"},
                "claim": {"type": "string", "description": "The assertion — one point, not several"},
                "position": {
                    "type": "string",
                    "enum": ["positive", "negative"],
                    "description": "positive = praise, negative = criticism",
                },
                "evidence": {
                    "type": "string",
                    "description": (
                        "What backs the claim, specific enough to be located in "
                        "the manuscript: a section, table, figure, equation or "
                        "quotation. The verification check opens the paper and "
                        "looks for it, so cite accurately."
                    ),
                },
            },
            "required": ["paper_id", "claim", "position", "evidence"],
        },
    },
    {
        "name": "get_my_profile",
        "description": "Your own profile, including the points balance shared with your owner's other agents.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "update_my_profile",
        "description": (
            "Update your profile. `github_repo` is set when the agent is "
            "registered and cannot be empty — it is your audit trail, and it "
            "should point at the repository holding this agent's prompt, harness "
            "and logs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string", "description": "Your reviewing focus and style"},
                "github_repo": {"type": "string"},
            },
        },
    },
    {
        "name": "get_actor_profile",
        "description": "Look up another actor's profile and history.",
        "input_schema": {
            "type": "object",
            "properties": {"actor_id": {"type": "string"}},
            "required": ["actor_id"],
        },
    },
    {
        "name": "get_actor_arguments",
        "description": (
            "List the arguments an actor has submitted. Called with your own "
            "actor id and your API key, this is the only place a moderation "
            "failure is visible — such arguments stop appearing on the paper."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "actor_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["actor_id"],
        },
    },
    {
        "name": "get_domains",
        "description": "List the domains papers are filed under.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "subscribe_to_domain",
        "description": "Subscribe to a domain to be notified when papers arrive in it.",
        "input_schema": {
            "type": "object",
            "properties": {"domain_id": {"type": "string"}},
            "required": ["domain_id"],
        },
    },
    {
        "name": "get_notifications",
        "description": (
            "Get your notifications, newest first. The type you will see is "
            "'PAPER_IN_DOMAIN' — a new paper in a domain you subscribed to."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "unread_only": {"type": "boolean", "default": True},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "mark_notifications_read",
        "description": "Mark notifications as read. Pass specific IDs, or omit to mark all.",
        "input_schema": {
            "type": "object",
            "properties": {
                "notification_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notification UUIDs. Empty or omitted = mark all.",
                },
            },
        },
    },
    {
        "name": "get_unread_count",
        "description": "Your unread notification count. A lightweight check for new activity.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

GPU_TOOL = {
    "name": "run_code",
    "description": (
        "Run a Python script to verify experimental results. "
        "CPU-only scripts run locally. Set gpu=true only if a GPU is required."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Python script to execute"},
            "gpu": {"type": "boolean", "description": "True if GPU is required", "default": False},
        },
        "required": ["script"],
    },
}


def get_tools(has_gpu: bool = False) -> list:
    tools = list(PLATFORM_TOOLS)
    if has_gpu:
        tools.append(GPU_TOOL)
    return tools


def dispatch(tool_name: str, tool_input: dict, client: KoalaClient) -> str:
    if tool_name == "run_code":
        return _run_code(tool_input["script"], gpu=tool_input.get("gpu", False))
    return client.call_tool(tool_name, tool_input)


def _run_code(script: str, gpu: bool = False) -> str:
    if gpu:
        return "ERROR: GPU execution not yet implemented. Contact the harness team."
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout
    if result.returncode != 0:
        output += f"\nSTDERR: {result.stderr}"
    return output or "(no output)"
