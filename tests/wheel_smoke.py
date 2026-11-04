"""Install a built wheel into an isolated uv environment outside the checkout."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = """
import json
from pathlib import Path
import subprocess
import koala_science as koala

subprocess.run(["koala", "init", "."], check=True)
assert Path(".env.example").exists()
assert Path(".gitignore").exists()
assert Path("providers/python_backend.py").exists()
assert Path("examples/fair-comparison/agent.yaml").exists()
assert Path("examples/fair-comparison/instructions.md").exists()
assert Path("examples/fair-comparison/paper.md").exists()
Path("empty.py").write_text('import json\\nfrom koala_science import ModelResponse\\nclass Empty:\\n async def generate(self, request):\\n  return ModelResponse(text=json.dumps({"candidates": []}), model="fake")\\ndef build():\\n return Empty()\\n')
Path("agent.yaml").write_text("schema_version: 1\\nname: smoke\\ninstruction_file: instructions.md\\nmodel:\\n  provider: custom\\n  name: fake\\n  factory: empty.py:build\\n")
subprocess.run(["koala", "validate"], check=True)
subprocess.run(["koala", "review", "sample.md", "--output", "cli-run"], check=True)
result = koala.Agent.from_config("agent.yaml").review("sample.md")
result.save("python-run")
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
