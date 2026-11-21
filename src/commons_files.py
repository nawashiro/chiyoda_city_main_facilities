"""Normalize Wikimedia Commons file references."""
from __future__ import annotations

import re
from urllib.parse import quote, unquote, urlsplit


COMMONS_FILE_PAGE = "https://commons.wikimedia.org/wiki/"
_FILE_PREFIX = "File:"
_FORBIDDEN_TITLE = re.compile(r"[#?\[\]{}|<>]")


def commons_file_title(value: str) -> str:
    """Return a canonical File: title from a title or a Commons file page URL."""
    if not isinstance(value, str):
        raise ValueError("Commons file must be a string")
    text = value.strip()
    if not text:
        raise ValueError("Commons file is empty")
    if "://" in text:
        parsed = urlsplit(text)
        if parsed.scheme != "https" or parsed.netloc != "commons.wikimedia.org" or not parsed.path.startswith("/wiki/"):
            raise ValueError("only Wikimedia Commons file pages are supported")
        title = unquote(parsed.path[len("/wiki/"):])
    else:
        title = text
    if title.lower().startswith("category:"):
        raise ValueError("Category: is not a file")
    if title.lower().startswith(_FILE_PREFIX.lower()):
        title = title[len(_FILE_PREFIX):]
    elif ":" in title:
        raise ValueError("only File: titles are supported")
    title = re.sub(r"\s+", " ", title.replace("_", " ")).strip()
    if not title:
        raise ValueError("Commons file title is empty")
    if _FORBIDDEN_TITLE.search(title):
        raise ValueError("Commons file title contains unsupported characters")
    return f"{_FILE_PREFIX}{title}"


def commons_file_page(value: str) -> str:
    """Return the canonical Commons file page URL for a title or URL."""
    title = commons_file_title(value)
    return COMMONS_FILE_PAGE + quote(title.replace(" ", "_"), safe="/:()!$&'*,;=@~")


def is_commons_file_page(value: str) -> bool:
    """Return whether value is an absolute Commons file page URL."""
    if not isinstance(value, str) or any(character.isspace() for character in value):
        return False
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.netloc != "commons.wikimedia.org":
        return False
    if not parsed.path.startswith(f"/wiki/{_FILE_PREFIX}") or parsed.query or parsed.fragment:
        return False
    try:
        commons_file_title(value)
    except ValueError:
        return False
    return True
