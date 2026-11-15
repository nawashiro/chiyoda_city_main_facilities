"""Local maintainer environment values loaded from the repository .env file."""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(root: str | Path) -> None:
    """Fill missing environment variables from .env in the repository root.

    Values already present in the environment, such as workflow secrets, win.
    """
    path = Path(root) / ".env"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
