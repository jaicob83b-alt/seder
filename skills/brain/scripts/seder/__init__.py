"""Seder engine: the scripted half of the `brain` skill.

Every CLI command prints exactly one JSON object to stdout (see `emit`), so the
only thing that reaches the conversation is a short, predictable result.
"""
import json
import sys

__version__ = "0.2.0"


def emit(obj: dict) -> None:
    """Print one JSON object (UTF-8, not ASCII-escaped) and flush."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()
