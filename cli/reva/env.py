"""Environment accessors for reva."""

import os

DEFAULT_KOALA_BASE_URL = "https://koala.science"


def koala_base_url() -> str:
    """Koala base URL. Honors $KOALA_BASE_URL (empty → default), strips trailing slashes."""
    value = os.environ.get("KOALA_BASE_URL") or DEFAULT_KOALA_BASE_URL
    return value.rstrip("/")
