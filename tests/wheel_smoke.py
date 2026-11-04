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
