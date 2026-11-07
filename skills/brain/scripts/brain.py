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

import datetime as dt  # noqa: E402
import json  # noqa: E402

import seder  # noqa: E402
from seder import config, emit, filing, index, ledger, pdf, sensitive  # noqa: E402

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

    ppdf = sub.add_parser("pdf", help="join images/PDFs into one PDF: pdf OUT PAGE... [--rotate 0,90,...]")
    ppdf.add_argument("out")
    ppdf.add_argument("pages", nargs="+")
    ppdf.add_argument("--rotate", default="", help="comma-separated clockwise degrees per page")

    pfile = sub.add_parser("file", help="move an approved document: file SRC FOLDER NAME --why TEXT")
    pfile.add_argument("src")
    pfile.add_argument("folder")
    pfile.add_argument("name")
    pfile.add_argument("--why", default="")
    pfile.add_argument("--mkdir", action="store_true", help="create the (approved) new folder")
    pfile.add_argument("--original", help="original file (xlsx/docx) for a hand-off branch")

    pidx = sub.add_parser("index", help="index: count rows, --rebuild, or --update REL")
    pidx.add_argument("--rebuild", action="store_true")
    pidx.add_argument("--update", metavar="REL")

    pnc = sub.add_parser("namecheck", help="is FOLDER/NAME taken, same as --src, and which name is free")
    pnc.add_argument("folder")
    pnc.add_argument("name")
    pnc.add_argument("--src")

    pled = sub.add_parser("ledger", help="the ledger: add, backfill, gaps, open, done")
    lsub = pled.add_subparsers(dest="sub", metavar="add|backfill|gaps|open|done")
    ladd = lsub.add_parser("add", help="add one row from JSON")
    ladd.add_argument("--json", required=True, help='{"path": ..., "type": ..., ...}')
    lsub.add_parser("backfill", help="a row for every indexed non-sensitive document without one")
    lgaps = lsub.add_parser("gaps", help="recurring documents with missing periods")
    lgaps.add_argument("--today", help="YYYY-MM-DD (default: today)")
    lopen = lsub.add_parser("open", help="open actions by due date")
    lopen.add_argument("--today", help="YYYY-MM-DD (default: today)")
    ldone = lsub.add_parser("done", help="mark the row of PATH as done")
    ldone.add_argument("path")
    ldone.add_argument("--when", help="YYYY-MM-DD (default: today)")
    return p


def _today(s: str | None) -> dt.date:
    return dt.date.fromisoformat(s) if s else dt.date.today()


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


def cmd_pdf(args) -> dict:
    rotations = [int(x) for x in args.rotate.split(",") if x.strip()] if args.rotate else []
    n = pdf.build_pdf([Path(p) for p in args.pages], rotations, Path(args.out))
    return {"ok": True, "out": str(Path(args.out)), "pages": n}


def cmd_file(args) -> dict:
    cfg = load_cfg(args)
    r = filing.file_doc(cfg, Path(args.src), args.folder, args.name, args.why,
                        mkdir=args.mkdir, original=Path(args.original) if args.original else None)
    return {"ok": True, **r}


def cmd_index(args) -> dict:
    cfg = load_cfg(args)
    if args.rebuild:
        return {"ok": True, "rows": index.rebuild(cfg)}
    if args.update:
        index.update_row(cfg, args.update)
        return {"ok": True, "updated": args.update}
    return {"ok": True, "rows": len(index.rows(cfg))}


def cmd_namecheck(args) -> dict:
    cfg = load_cfg(args)
    return {"ok": True, **filing.namecheck(cfg, args.folder, args.name, Path(args.src) if args.src else None)}


def cmd_ledger(args) -> dict:
    cfg = load_cfg(args)
    if args.sub == "add":
        ledger.append(cfg, json.loads(args.json))
        return {"ok": True, "added": 1}
    if args.sub == "backfill":
        return {"ok": True, "added": ledger.backfill_from_names(cfg)}
    if args.sub == "gaps":
        return {"ok": True, "gaps": ledger.recurring_gaps(cfg, _today(args.today))}
    if args.sub == "open":
        return {"ok": True, "items": ledger.open_items(cfg, _today(args.today))}
    if args.sub == "done":
        when = args.when or dt.date.today().isoformat()
        return {"ok": True, "done": ledger.mark_done(cfg, args.path, when)}
    raise CliError("ledger: add | backfill | gaps | open | done")


HANDLERS = {
    "version": cmd_version,
    "privacy": cmd_privacy,
    "pdf": cmd_pdf,
    "file": cmd_file,
    "index": cmd_index,
    "namecheck": cmd_namecheck,
    "ledger": cmd_ledger,
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
