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
from seder import pull, site, tree  # noqa: E402
from seder import config, discover, doctor, emit, filing, inbox, index, init, ledger, names, pdf, project, prune, sensitive, studies  # noqa: E402

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

    sub.add_parser("doctor", help="environment checks and where the instance is")

    pinit = sub.add_parser("init", help="create a new instance: init --home DIR --root DIR --lang he|en --owner NAME")
    pinit.add_argument("--home", default=argparse.SUPPRESS, help="the brain folder to create")
    pinit.add_argument("--root", required=True)
    pinit.add_argument("--lang", default="he", choices=list(names.LANGS))
    pinit.add_argument("--owner", default="")
    pinit.add_argument("--entities", default="", help="comma-separated people and businesses")
    pinit.add_argument("--addons", default="", help="comma-separated addon ids, e.g. dev_projects,studies")
    pinit.add_argument("--plan", help="JSON file: the tailored tree the person approved (see tree-preview)")
    pinit.add_argument("--name", default="", help="what the person calls the archive")

    padopt = sub.add_parser("adopt", help="register an existing archive: adopt --home DIR --root DIR")
    padopt.add_argument("--home", default=argparse.SUPPRESS, help="the existing brain folder")
    padopt.add_argument("--root", required=True)
    padopt.add_argument("--addons", default="", help="comma-separated addon ids to register, e.g. dev_projects,studies")
    padopt.add_argument("--name", default="", help="what the person calls the archive")

    pdisc = sub.add_parser("discover", help="before an archive exists, with a yes: where documents live and which topics, names only")
    pdisc.add_argument("--roots", nargs="*", help="folders to look in (default: Documents, Downloads, Desktop, cloud-sync folders)")
    pdisc.add_argument("--lang", default="he", choices=list(names.LANGS))
    pdisc.add_argument("--max-depth", type=int, default=discover.DEFAULT_MAX_DEPTH)

    pprev = sub.add_parser("tree-preview", help="the tree init would create, from add-ons and a plan; writes nothing")
    pprev.add_argument("--lang", default="he", choices=list(names.LANGS))
    pprev.add_argument("--addons", default="")
    pprev.add_argument("--plan", help="JSON file with the tailored tree")

    psite = sub.add_parser("site", help="the phone site: approve, snap a photo, search; listens on Tailscale or 127.0.0.1 only")
    psite.add_argument("--port", type=int, default=site.DEFAULT_PORT)
    psite.add_argument("--bind", help="100.x (Tailscale) or 127.0.0.1; default: the Tailscale address, else 127.0.0.1")
    psite.add_argument("--check", action="store_true", help="is Tailscale up, which address to open on the phone; starts nothing")
    psite.add_argument("--wait-tailscale", type=int, default=0, help="seconds to wait for Tailscale at startup")
    psite.add_argument("--autostart", choices=["install", "remove", "status"], help="start the site with Windows (after a yes)")

    sub.add_parser("pull", help="copy new documents from the watched folders into the inbox")
    psrc = sub.add_parser("sources", help="watched folders: list, add PATH --label L, remove PATH")
    srcsub = psrc.add_subparsers(dest="src_cmd", metavar="action")
    srcsub.add_parser("list")
    sadd = srcsub.add_parser("add")
    sadd.add_argument("path")
    sadd.add_argument("--label", default="")
    srem = srcsub.add_parser("remove")
    srem.add_argument("path")

    pren = sub.add_parser("rename", help="change the archive's name; --folder also renames the brain folder")
    pren.add_argument("name")
    pren.add_argument("--folder", action="store_true")

    sub.add_parser("scan", help="folders up to depth 2 with file counts, names only")

    sub.add_parser("inbox", help="what is waiting in the inbox: duplicates, quarantine, suggested names")

    papp = sub.add_parser("intake-apply", help="file the approved documents of _proposal.json (1-based numbers)")
    papp.add_argument("--approve", required=True, help="comma-separated document numbers, e.g. 1,3")
    papp.add_argument("--name", action="append", default=[], metavar="N=NAME", help="corrected name for document N")
    papp.add_argument("--folder", action="append", default=[], metavar="N=FOLDER", help="corrected folder for document N")
    papp.add_argument("--mkdir", default="", help="comma-separated document numbers whose new folder was approved")
    papp.add_argument("--proposal", help="path of the proposal file (default: <inbox>/_proposal.json)")

    pproj = sub.add_parser("project", help="project cards: new, list, archive-candidates, archive")
    jsub = pproj.add_subparsers(dest="sub", metavar="new|list|archive-candidates|archive")
    jnew = jsub.add_parser("new", help="create a project folder with a card")
    jnew.add_argument("name")
    jnew.add_argument("--code", help="where the code lives (path or URL)")
    jnew.add_argument("--branch", help="dev_projects (07) or projects (06); default: the first present")
    jsub.add_parser("list", help="projects with created / last modified dates")
    jcand = jsub.add_parser("archive-candidates", help="projects quiet for more than --days days")
    jcand.add_argument("--days", type=int, default=90)
    jcand.add_argument("--today", help="YYYY-MM-DD (default: today)")
    jarch = jsub.add_parser("archive", help="move a project into the branch's archive folder (after a yes)")
    jarch.add_argument("name")

    pst = sub.add_parser("studies", help="add-on 08: import a course (copy), index lessons, find relevant lessons")
    ssub = pst.add_subparsers(dest="sub", metavar="import|index|relevant")
    simp = ssub.add_parser("import", help="copy a course folder into 08 with topic names; dry run unless --go")
    simp.add_argument("--src", required=True, help="the course folder to copy from")
    simp.add_argument("--course", required=True, help="course name inside 08")
    simp.add_argument("--rename", help="JSON file: {\"old folder name\": \"new name\", ...}")
    simp.add_argument("--go", action="store_true", help="actually copy (default: list the plan only)")
    ssub.add_parser("index", help="rebuild the studies index")
    srel = ssub.add_parser("relevant", help="lessons related to a text, best first")
    srel.add_argument("query")
    srel.add_argument("--limit", type=int, default=5)

    ppr = sub.add_parser("prune-transcripts", help="list (or with --go move) old intake transcripts out of ~/.claude/projects")
    ppr.add_argument("--older-days", type=int, default=7)
    ppr.add_argument("--projects", help="the Claude Code projects folder (default: ~/.claude/projects)")
    ppr.add_argument("--go", action="store_true", help="move them into <home>/<transcripts archive>; nothing is deleted")

    pset2 = sub.add_parser("settings", help="write the permission settings for unattended runs: settings --headless OUT")
    pset2.add_argument("--headless", metavar="OUT", required=True)

    pptr = sub.add_parser("pointer", help="the ~/.seder/home pointer the hook uses to find the instance")
    pptr.add_argument("--write", action="store_true", help="write the current instance's path into it")
    pptr.add_argument("--file", help="pointer file (default: ~/.seder/home)")
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


def _split_list(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def cmd_doctor(args) -> dict:
    home = config.find_home(explicit=Path(args.home) if args.home else None)
    return {"ok": True, "home": str(home) if home else None, "checks": doctor.checks()}


def cmd_init(args) -> dict:
    if not args.home:
        raise CliError("init needs --home DIR (the brain folder to create)")
    cfg = init.create(Path(args.home), Path(args.root), args.lang, args.owner, _split_list(args.entities),
                      _split_list(args.addons), plan=_read_plan(args.plan), name=args.name)
    return {"ok": True, "home": str(cfg.home), "root": str(cfg.root), "lang": cfg.lang, "name": cfg.data.get("name"),
            "tree": [{"num": n["num"], "name": n["name"], "physical": n["physical"]} for n in cfg.tree]}


def cmd_adopt(args) -> dict:
    if not args.home:
        raise CliError("adopt needs --home DIR (the existing brain folder)")
    cfg = init.adopt(Path(args.home), Path(args.root), _split_list(args.addons), name=args.name)
    return {"ok": True, "home": str(cfg.home), "root": str(cfg.root), "lang": cfg.lang,
            "tree": [{"num": n["num"], "name": n["name"], "physical": n["physical"], "handoff": n["handoff"]} for n in cfg.tree],
            "proposed_tree": str(cfg.path("proposed_tree"))}


def _read_plan(path: str | None) -> dict | None:
    if not path:
        return None
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise CliError(f"cannot read plan {path}: {e}")
    if not isinstance(plan, dict):
        raise CliError("the plan must be a JSON object")
    return plan


def cmd_discover(args) -> dict:
    roots = [Path(r) for r in args.roots] if args.roots else None
    return {"ok": True, **discover.discover(roots, max_depth=args.max_depth, lang=args.lang)}


def cmd_tree_preview(args) -> dict:
    branches = tree.build(args.lang, _split_list(args.addons), _read_plan(args.plan))
    return {"ok": True, "tree": [{"num": n["num"], "name": n["name"], "physical": n["physical"],
                                  "subfolders": n.get("subfolders", []), "items": n.get("items", []),
                                  "per_item": n.get("per_item", False)} for n in branches]}


def cmd_site(args) -> dict:
    if args.check:
        return {"ok": True, **site.check(args.port)}
    cfg = load_cfg(args)
    if args.autostart:
        return {"ok": True, **site.autostart(cfg, args.autostart, Path(__file__).resolve(), sys.executable)}
    site.serve(cfg, bind=args.bind, port=args.port, wait_for_tailscale=args.wait_tailscale)
    return {"ok": True, "stopped": True}


def cmd_pull(args) -> dict:
    return {"ok": True, **pull.pull(load_cfg(args))}


def cmd_sources(args) -> dict:
    cfg = load_cfg(args)
    if args.src_cmd == "add":
        return {"ok": True, "added": pull.add(cfg, Path(args.path), args.label)}
    if args.src_cmd == "remove":
        return {"ok": True, "removed": pull.remove(cfg, Path(args.path))}
    return {"ok": True, **pull.status(cfg)}


def cmd_rename(args) -> dict:
    return {"ok": True, **init.rename(load_cfg(args), args.name, move_folder=args.folder)}


def cmd_scan(args) -> dict:
    return {"ok": True, **init.scan(load_cfg(args))}


def cmd_inbox(args) -> dict:
    return {"ok": True, "files": inbox.list_inbox(load_cfg(args))}


def _numbered(pairs: list[str]) -> dict:
    out = {}
    for s in pairs:
        n, _, value = s.partition("=")
        if not n.strip().isdigit() or not value:
            raise CliError(f"expected N=value, got {s!r}")
        out[int(n) - 1] = value
    return out


def cmd_intake_apply(args) -> dict:
    cfg = load_cfg(args)
    path = Path(args.proposal) if args.proposal else cfg.path("inbox") / inbox.PROPOSAL
    if not path.is_file():
        raise CliError(f"proposal file not found: {path}")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    approved = [int(x) - 1 for x in _split_list(args.approve)]
    mk = {int(x) - 1 for x in _split_list(args.mkdir)}
    results = inbox.apply(cfg, proposal, approved, names=_numbered(args.name), folders=_numbered(args.folder), mkdir=mk)
    for r in results:
        r["i"] = r["i"] + 1
    return {"ok": all(r.get("ok") for r in results), "results": results}


def cmd_project(args) -> dict:
    cfg = load_cfg(args)
    if args.sub == "new":
        p = project.new_project(cfg, args.name, args.code, dt.date.today(), args.branch)
        return {"ok": True, "path": str(p), "card": str(p / project.NAMES.get(cfg.lang, project.NAMES["en"])["card"])}
    if args.sub == "list":
        return {"ok": True, "projects": project.list_projects(cfg)}
    if args.sub == "archive-candidates":
        return {"ok": True, "candidates": project.archive_candidates(cfg, _today(args.today), args.days)}
    if args.sub == "archive":
        return {"ok": True, "dest": str(project.archive(cfg, args.name))}
    raise CliError("project: new | list | archive-candidates | archive")


def cmd_studies(args) -> dict:
    cfg = load_cfg(args)
    if args.sub == "import":
        rename = json.loads(Path(args.rename).read_text(encoding="utf-8")) if args.rename else {}
        plan = studies.import_course(cfg, Path(args.src), args.course, rename, dry_run=not args.go)
        return {"ok": True, "dry_run": not args.go, "plan": plan}
    if args.sub == "index":
        out = studies.build_index(cfg)
        return {"ok": True, "file": str(out), "lessons": len(studies.index_rows(cfg))}
    if args.sub == "relevant":
        return {"ok": True, "lessons": studies.relevant(cfg, args.query, args.limit)}
    raise CliError("studies: import | index | relevant")


def cmd_prune(args) -> dict:
    cfg = load_cfg(args)
    projects = Path(args.projects) if args.projects else prune.default_projects_dir()
    dest = cfg.path("transcripts")
    items = prune.scan(projects, args.older_days)
    out = {"ok": True, "go": bool(args.go), "projects": str(projects), "dest": str(dest), "transcripts": items}
    if args.go:
        out["moved"] = prune.move(items, dest)
    return out


def cmd_settings(args) -> dict:
    cfg = load_cfg(args)
    out = sensitive.write_headless_settings(cfg, Path(args.headless))
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"ok": True, "file": str(out), "allow": data["permissions"]["allow"], "deny": len(data["permissions"]["deny"])}


def cmd_pointer(args) -> dict:
    pointer = Path(args.file) if args.file else config.HOME_POINTER
    if args.write:
        cfg = load_cfg(args)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(str(cfg.home) + "\n", encoding="utf-8")
    current = None
    if pointer.is_file():
        line = pointer.read_text(encoding="utf-8").strip().splitlines()
        current = line[0].strip() if line else None
    return {"ok": True, "file": str(pointer), "home": current}


HANDLERS = {
    "version": cmd_version,
    "privacy": cmd_privacy,
    "pdf": cmd_pdf,
    "file": cmd_file,
    "index": cmd_index,
    "namecheck": cmd_namecheck,
    "ledger": cmd_ledger,
    "doctor": cmd_doctor,
    "init": cmd_init,
    "adopt": cmd_adopt,
    "scan": cmd_scan,
    "discover": cmd_discover,
    "tree-preview": cmd_tree_preview,
    "rename": cmd_rename,
    "site": cmd_site,
    "pull": cmd_pull,
    "sources": cmd_sources,
    "inbox": cmd_inbox,
    "intake-apply": cmd_intake_apply,
    "project": cmd_project,
    "studies": cmd_studies,
    "prune-transcripts": cmd_prune,
    "settings": cmd_settings,
    "pointer": cmd_pointer,
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
