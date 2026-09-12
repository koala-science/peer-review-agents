"""The harness must expose tools the platform actually has.

`agent_definition/harness/tools.py` offered `post_comment` and `post_verdict`
for five months after the platform replaced both with `post_argument`, and
offered no way to submit an argument at all — an agent built on it could browse
and never contribute. Nothing here noticed.

Modules are loaded by path rather than imported: `agent_definition.harness`'s
`__init__` pulls in `harness.py`, which imports `anthropic`, which is not a
declared dependency — importing the package aborts collection for the whole
suite under `uv sync --dev`. Same approach as `test_harness_koala.py`.

These are structural checks — that the surface matches — not proof the
descriptions are good advice.
"""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

HARNESS = Path(__file__).resolve().parents[1] / "agent_definition" / "harness"

# The platform's MCP surface, from `tools/list` on the live server. Tools the
# harness offers must come from here; it need not offer all of them.
#
# Copied rather than imported because the platform is not a dependency of this
# repo. The drift it cannot catch is a platform *rename*: the stale name stays
# in this set and the guard stays green. `test_offered_tools_exist_on_the_live_
# platform` covers that when the network is available.
PLATFORM_TOOLS = {
    "search_papers", "get_papers", "get_paper", "submit_paper",
    "get_arguments", "post_argument",
    "get_domains", "create_domain", "get_domain",
    "subscribe_to_domain", "unsubscribe_from_domain", "get_my_subscriptions",
    "get_my_profile", "update_my_profile",
    "get_actor_profile", "get_actor_papers", "get_actor_arguments",
    "get_notifications", "mark_notifications_read", "get_unread_count",
}

# Dispatched locally rather than sent to the platform.
LOCAL_TOOLS = {"run_code"}


PACKAGE = "_harness_under_test"


def _load(name: str):
    """Load one harness module without importing the package.

    `tools.py` imports `.koala` relatively, so the modules are loaded under a
    synthetic package whose `__path__` points at the harness directory. Going
    through `agent_definition.harness` instead would execute its `__init__`,
    which imports `anthropic` and aborts collection for the whole suite.
    """
    sys.modules.setdefault("httpx", MagicMock())
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(HARNESS)]
        sys.modules[PACKAGE] = package

    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", HARNESS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _offered() -> dict:
    tools = _load("tools")
    return {tool["name"]: tool for tool in tools.get_tools(has_gpu=True)}


def test_every_offered_tool_exists_on_the_platform():
    unknown = set(_offered()) - PLATFORM_TOOLS - LOCAL_TOOLS
    assert not unknown, (
        f"the harness offers {sorted(unknown)}, which the platform does not have — "
        f"an agent calling one gets an error it cannot act on"
    )


def test_the_agent_can_actually_contribute():
    """Everything else is browsing. Without this the harness is read-only."""
    assert "post_argument" in _offered()


def test_posting_an_argument_asks_for_what_the_platform_requires():
    """A missing field is a 422 the agent cannot diagnose from the schema."""
    required = set(_offered()["post_argument"]["input_schema"]["required"])
    assert required == {"paper_id", "claim", "position", "evidence"}


def test_position_is_constrained_to_what_the_platform_accepts():
    position = _offered()["post_argument"]["input_schema"]["properties"]["position"]
    assert set(position["enum"]) == {"positive", "negative"}


@pytest.mark.parametrize("retired", ["post_comment", "post_verdict", "get_comments"])
def test_retired_tools_are_gone(retired):
    assert retired not in _offered()


def test_the_client_sends_the_documented_header():
    """The bare key is the platform's documented form.

    (It also accepts `Bearer <key>`; sending the documented form is a matter of
    following the doc, not of avoiding a rejection.)
    """
    koala = _load("koala")
    client = koala.KoalaClient(api_key="cs_test_key")
    assert client.headers["Authorization"] == "cs_test_key"


# ---------------------------------------------------------------------------
# The parameter-level check the hardcoded set above cannot do: it asks the live
# server what it actually accepts, which is the only way to catch a renamed tool
# or a parameter that no longer exists.
#
# Opt-in — `pytest -m network`. Worth running whenever the harness or the
# platform changes, and worth a CI job of its own; not worth a 15-second
# timeout on every local run.
# ---------------------------------------------------------------------------


@pytest.mark.network
def test_offered_tools_exist_on_the_live_platform():
    import json
    import urllib.error
    import urllib.request

    sys.path.insert(0, str(HARNESS.parents[1] / "cli"))
    from reva.env import koala_base_url

    request = urllib.request.Request(
        f"{koala_base_url()}/mcp",
        data=json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        ).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"live platform unreachable: {exc}")

    live = {tool["name"]: tool for tool in payload["result"]["tools"]}
    assert live, "the platform returned no tools; this test cannot judge anything"

    # Every mismatch at once: reporting the first turns a multi-tool drift into
    # one round of fixing per tool.
    problems = []
    for name, schema in _offered().items():
        if name in LOCAL_TOOLS:
            continue
        if name not in live:
            problems.append(f"{name}: the platform no longer has this tool")
            continue
        declared = set(live[name].get("inputSchema", {}).get("properties", {}))
        unknown = set(schema["input_schema"].get("properties", {})) - declared
        if unknown:
            problems.append(
                f"{name}: offered with parameters the platform does not accept: "
                f"{sorted(unknown)}"
            )
    assert not problems, "\n".join(problems)
