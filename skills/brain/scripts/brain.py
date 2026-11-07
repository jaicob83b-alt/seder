"""Seder command line: `python -I -X utf8 brain.py <command> [args]`.

Contract: every run prints exactly one JSON object to stdout,
`{"ok": true, ...}` or `{"ok": false, "error": "..."}`, and exits 0 or 1.
Commands register themselves in `HANDLERS`; each handler takes the parsed
arguments and returns the dict to print.
"""
import argparse
import sys
from pathlib import Path

# `-I` (isolated mode) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import seder  # noqa: E402
from seder import emit  # noqa: E402


class CliError(Exception):
    """A user-facing error: printed as {"ok": false, "error": ...}, exit 1."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse would print usage and exit 2
        raise CliError(message)


def build_parser() -> _Parser:
    p = _Parser(prog="brain.py", description="Seder: private document archive engine.")
    sub = p.add_subparsers(dest="cmd", metavar="command")
    sub.add_parser("version", help="print the engine version")
    return p


def cmd_version(args) -> dict:
    return {"ok": True, "version": seder.__version__}


HANDLERS = {
    "version": cmd_version,
}


def main(argv: list[str]) -> int:
    try:
        args = build_parser().parse_args(argv)
        if not args.cmd:
            raise CliError("missing command (try: version)")
        result = HANDLERS[args.cmd](args)
        emit(result)
        return 0 if result.get("ok", True) else 1
    except SystemExit:
        raise
    except Exception as e:  # every failure is still one JSON object
        emit({"ok": False, "error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
