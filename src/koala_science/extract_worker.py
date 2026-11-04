"""Private subprocess entry point for deadline-bounded PDF extraction."""

import json
import sys

from .sources import read_source


def main() -> None:
    try:
        source = read_source(sys.argv[1])
    except (ValueError, OSError):
        payload = {
            "error": "PDF extraction failed or exceeded limits; supply readable text (OCR for scanned PDFs)"
        }
    else:
        payload = {"source": source.model_dump()}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    main()
