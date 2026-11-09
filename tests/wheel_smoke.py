"""Install a built wheel into an isolated uv environment outside the checkout."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = """
import json
import os
from pathlib import Path
import subprocess
import koala_science as koala

subprocess.run(["koala", "init", ".", "--provider", "codex_cli", "--preset", "quick"], check=True)
assert {p.name for p in Path(".").iterdir()} == {"agent.yaml", "instructions.md", "paper.yaml", "sample.md", ".gitignore"}
os.environ["KOALA_MODEL"] = "test"
class StarterProvider:
    async def generate(self, request):
        return koala.ModelResponse(text='{"claims": []}', model="fake")
starter = koala.Agent.from_config("agent.yaml", provider=StarterProvider()).review("sample.md")
assert starter.status == "complete"
assert starter.manifest["model_calls"] == 1
subprocess.run(["koala", "init", "with-examples", "--examples", "--provider", "compatible_api", "--preset", "default"], check=True)
os.chdir("with-examples")
assert Path(".env.example").exists()
assert Path(".gitignore").exists()
assert Path("providers/python_backend.py").exists()
assert Path("examples/fair-comparison/agent.yaml").exists()
assert Path("examples/fair-comparison/instructions.md").exists()
assert Path("examples/fair-comparison/paper.md").exists()
assert Path("examples/tood/agent.yaml").exists()
assert Path("examples/quick-review/agent.yaml").exists()
assert Path("examples/quick-review/instructions.md").exists()
from koala_science.config import load_config
os.environ["KOALA_MODEL"] = "test"
quick = load_config("examples/quick-review/agent.yaml", supplied_provider=True)
assert quick.config.review_strategy == "claims"
assert quick.config.max_claims == 1
assert quick.children == []
class NoUsefulClaims:
    async def generate(self, request):
        return koala.ModelResponse(text='{"claims": []}', model="fake")
quick_result = koala.Agent.from_config("examples/quick-review/agent.yaml", provider=NoUsefulClaims()).review("sample.md")
assert quick_result.status == "complete"
assert quick_result.arguments == []
assert quick_result.manifest["review"]["strategy"] == "claims"
assert quick_result.manifest["model_calls"] == 1
assert Path("examples/tood/codex.yaml").exists()
assert Path("examples/tood/claude.yaml").exists()
for name in ("gemini", "openai-api", "anthropic-api", "gemini-api", "koala"):
    assert Path(f"examples/tood/{name}.yaml").exists()
from koala_science.gemini_provider import GeminiCLIProvider
assert Path("examples/tood/paper.yaml").exists()
assert Path("paper.yaml").exists()
assert ".koala/" in Path(".gitignore").read_text()
from koala_science.config import ModelConfig
from koala_science.providers import build_provider
from koala_science.codex_provider import CodexCLIProvider
assert isinstance(build_provider(ModelConfig(provider="codex_cli", name="test")), CodexCLIProvider)
from koala_science.claude_provider import ClaudeCLIProvider
from koala_science.workspace import PaperWorkspace
from koala_science.submission import Selection
from koala_science.platform import arxiv_identity
assert isinstance(build_provider(ModelConfig(provider="claude_cli", name="test")), ClaudeCLIProvider)
assert PaperWorkspace.load().manuscript == Path("sample.md").resolve()
assert arxiv_identity("2607.29592v1") == ("2607.29592", 1)
subprocess.run(["koala", "submit", "--help"], check=True)
assert Path("examples/tood/agents/evidence.md").exists()
assert Path("examples/tood/offline_provider.py").exists()
Path("empty.py").write_text('import json\\nfrom koala_science import ModelResponse\\nclass Empty:\\n async def generate(self, request):\\n  return ModelResponse(text=json.dumps({"candidates": []}), model="fake")\\ndef build():\\n return Empty()\\n')
Path("agent.yaml").write_text("schema_version: 1\\nname: smoke\\ninstruction_file: instructions.md\\nmodel:\\n  provider: custom\\n  name: fake\\n  factory: empty.py:build\\n")
subprocess.run(["koala", "validate"], check=True)
subprocess.run(["koala", "review"], check=True)
assert Path(".koala/last-run.json").exists()
subprocess.run(["koala", "review", "sample.md", "--output", "cli-run"], check=True)
result = koala.Agent.from_config("agent.yaml").review("sample.md")
result.save("python-run")
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
writer = PdfWriter()
page = writer.add_blank_page(200, 200)
font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
stream = DecodedStreamObject()
stream.set_data(b"BT /F1 12 Tf 10 100 Td (A reproducible comparison.) Tj ET")
page[NameObject("/Contents")] = stream
writer.write("paper.pdf")
subprocess.run(["koala", "review", "paper.pdf", "--output", "pdf-run"], check=True)
assert json.loads(Path("pdf-run/sources.json").read_text())[0]["spans"][0]["page"] == 1
subprocess.run(["koala", "validate", "--config", "examples/tood/offline.yaml"], check=True)
subprocess.run(["koala", "review", "paper.pdf", "--config", "examples/tood/offline.yaml", "--output", "tood-offline-run"], check=True)
tood = json.loads(Path("tood-offline-run/manifest.json").read_text())
assert tood["status"] == "complete"
assert {u["model"] for u in tood["usage"]} == {"offline-smoke-no-scientific-review"}
cli = json.loads(Path("cli-run/arguments.json").read_text())
assert result.status == cli["status"] == "complete"
assert result.arguments == cli["arguments"] == []
assert set(p.name for p in Path("cli-run").iterdir()) == {"arguments.json", "arguments.md", "manifest.json", "sources.json", "diagnostics.json"}
print("Installed wheel: CLI, Python API, and templates passed")
"""


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wheel = next((root / "dist").glob("koala_science_agents-*.whl"))
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="koala-wheel-") as temporary:
        subprocess.run(
            [
                "uv",
                "run",
                "--isolated",
                "--no-project",
                "--python",
                sys.executable,
                "--with",
                str(wheel),
                "python",
                "-c",
                SCRIPT,
            ],
            cwd=temporary,
            env=env,
            check=True,
            timeout=180,
        )


if __name__ == "__main__":
    main()
