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
from seder import config, emit, sensitive  # noqa: E402

NO_HOME = "לא נמצאה תיקיית מוח / no archive found: run init, or set SEDER_HOME"


class CliError(Exception):
    """A user-facing error: printed as {"ok": false, "error": ...}, exit 1."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse would print usage and exit 2
        raise CliError(message)


def build_parser() -> _Parser:
    p = _Parser(prog="brain.py", description="Seder: private document archive engine.")
    p.add_argument("--home", help="instance folder (the one holding brain.json)")
    sub = p.add_subparsers(dest="cmd", metavar="command")
    sub.add_parser("version", help="print the engine version")

    priv = sub.add_parser("privacy", help="per-folder privacy levels: open, ask, locked")
    psub = priv.add_subparsers(dest="sub", metavar="list|set")
    psub.add_parser("list", help="show levels and folder-name defaults")
    pset = psub.add_parser("set", help="set a folder's level")
    pset.add_argument("folder")
    pset.add_argument("level", choices=sensitive.LEVELS)
    return p


def load_cfg(args) -> config.Config:
    home = config.find_home(explicit=Path(args.home) if args.home else None)
    if home is None:
        raise CliError(NO_HOME)
    return config.Config.load(home)


def cmd_version(args) -> dict:
    return {"ok": True, "version": seder.__version__}


def cmd_privacy(args) -> dict:
    cfg = load_cfg(args)
    if args.sub == "set":
        return {"ok": True, "levels": sensitive.set_level(cfg, args.folder, args.level)}
    g = sensitive.load(cfg)
    return {"ok": True, "levels": g.get("levels") or {}, "folder_names": g.get("folder_names") or {},
            "medical_folders": g.get("medical_folders") or [], "secret_folders": g.get("secret_folders") or []}


HANDLERS = {
    "version": cmd_version,
    "privacy": cmd_privacy,
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
