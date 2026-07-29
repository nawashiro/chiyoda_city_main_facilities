from __future__ import annotations

from typing import Any


def read_limited_response(response: Any, maximum_bytes: int, label: str) -> bytes:
    """Read an HTTP response without allowing an unbounded allocation."""
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as error:
            raise ValueError(f"invalid {label} Content-Length") from error
        if declared < 0 or declared > maximum_bytes:
            raise ValueError(f"{label} response is too large")
    payload = response.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError(f"{label} response is too large")
    return payload
