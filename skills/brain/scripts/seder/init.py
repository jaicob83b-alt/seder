"""Creating a new instance, adopting an existing archive, and scanning names.

`create` builds the brain folder from templates and the standard tree. It
creates nothing in the root itself: branch folders appear with the first
document that is filed into them, after approval.

`adopt` registers an existing archive as it is: every top-level folder
becomes a branch whose physical name is the existing name, so new documents
keep going where they go today. The suggested standard mapping is written
to a proposal file, never applied.
"""
import csv
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

from . import names, sensitive, tree
from . import config as _config
from .config import BRAIN_FILE, Config

ASSETS = Path(__file__).resolve().parents[2] / "assets"
TEMPLATES = ASSETS / "templates"
SKIP_TOP_PREFIXES = (".", "_", "~$", "My ")
NUM_RE = re.compile(r"^(\d{2})[_ -]?(.*)$")
DEFAULT_NAME = {"he": "סדר", "en": "Seder"}

# keyword -> standard branch id, for the adoption proposal (first match wins)
PROPOSAL_KEYWORDS = [
    ("finance", ["כספ", "money", "finance", "bank", "בנק"]),
    ("home", ["בית", "נדל", "דירה", "home", "house", "estate"]),
    ("family", ["ילד", "משפח", "אישי", "family", "personal", "kids"]),
    ("vehicles", ["רכב", "car", "vehicle"]),
    ("business", ["עסק", "חברה", "בע\"מ", "ltd", "co", "business", "company"]),
    ("projects", ["פרויקט", "project", "אירוע", "event"]),
    ("studies", ["לימוד", "קורס", "study", "course"]),
    ("media", ["מדיה", "media", "תמונ", "photo"]),
    ("archive", ["ארכיון", "archive", "ישן", "old"]),
]
PROPOSAL_LABELS = {
    "he": {"title": "# עץ מוצע", "intro": "הצעה בלבד, שום דבר לא זז. לכל תיקייה קיימת: לאן היא הייתה הולכת בעץ הסטנדרטי. \"?\" = צריך להחליט.",
           "cols": "| תיקייה קיימת | קבצים | ענף סטנדרטי מוצע |", "generated": "נוצר"},
    "en": {"title": "# Proposed tree", "intro": "A proposal only; nothing moves. For every existing folder: where it would go in the standard tree. \"?\" = needs a decision.",
           "cols": "| existing folder | files | proposed standard branch |", "generated": "generated"},
}


def _write_csv_header(path: Path, kind: str, lang: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(names.header(kind, lang))


def _routing_table(cfg: Config) -> str:
    """Markdown rows: branch -> physical folder, with its allowed subfolders."""
    rows = []
    for n in cfg.tree:
        if n.get("id") == "brain":
            continue
        subs = " · ".join(n.get("subfolders", []))
        rule = n.get("rule", "")
        rows.append(f"| {n['num']} {n['name']} | `{n['physical']}` | {subs} | {rule} |")
    return "\n".join(rows)


def _fill(template: str, cfg: Config) -> str:
    vals = {
        "owner": cfg.owner or ("?" if cfg.lang == "en" else "?"),
        "entities": ", ".join(cfg.entities) if cfg.entities else cfg.owner,
        "root": str(cfg.root),
        "home": str(cfg.home),
        "brain_folder": cfg.home.name,
        "inbox": names.FILES[cfg.lang]["inbox"],
        "index": names.FILES[cfg.lang]["index"],
        "ledger": names.FILES[cfg.lang]["ledger"],
        "log": names.FILES[cfg.lang]["log"],
        "sensitive_file": names.FILES[cfg.lang]["sensitive"],
        "routing_table": _routing_table(cfg),
        "date": date.today().isoformat(),
    }
    out = template
    for k, v in vals.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _template(kind: str, lang: str) -> str:
    return (TEMPLATES / f"{kind}.{lang}.md").read_text(encoding="utf-8")


def create(home: Path, root: Path, lang: str, owner: str, entities: list[str], addons: list[str] = (),
           plan: dict | None = None, name: str = "") -> Config:
    """A new instance in `home` for the documents under `root`. Creates no branch folders.

    `plan` tailors the standard tree (see tree.build); `name` is what the person calls
    the archive ("Seder", "Dana's cabinet"), shown in answers and on the review page."""
    home, root = Path(home), Path(root)
    if lang not in names.LANGS:
        raise ValueError(f"unsupported lang: {lang}")
    if (home / BRAIN_FILE).exists():
        raise FileExistsError(f"an instance already exists: {home / BRAIN_FILE}")
    root.mkdir(parents=True, exist_ok=True)
    branches = tree.build(lang, list(addons or []), plan)
    branches[0]["physical"] = home.name  # the brain folder is wherever the person put it
    if name:
        branches[0]["name"] = tree._check_name(name)
    home.mkdir(parents=True, exist_ok=True)
    cfg = Config(home=home, root=root, lang=lang, owner=owner, entities=list(entities),
                 tree=branches,
                 sources={"inbox": True, "gmail": False, "whatsapp": False, "downloads": False, "site": False},
                 data={"version": 1, "remote_warning": True, "name": name or DEFAULT_NAME[lang]})
    cfg.save()
    cfg.path("inbox").mkdir(exist_ok=True)
    for kind in ("index", "ledger", "log"):
        if not cfg.path(kind).exists():
            _write_csv_header(cfg.path(kind), kind, lang)
    if not cfg.path("sensitive").exists():
        shutil.copyfile(ASSETS / "sensitive.default.json", cfg.path("sensitive"))
    for kind, key in (("naming", "naming"), ("profile", "profile")):
        if not cfg.path(key).exists():
            cfg.path(key).write_text(_fill(_template(kind, lang), cfg), encoding="utf-8")
    return cfg


def _detect_lang(home: Path) -> str:
    if (home / names.FILES["he"]["index"]).exists() or (home / names.FILES["he"]["inbox"]).exists():
        return "he"
    if (home / names.FILES["en"]["index"]).exists() or (home / names.FILES["en"]["inbox"]).exists():
        return "en"
    return "he"


def _branch_from_folder(root: Path, home: Path, name: str, lang: str) -> dict:
    m = NUM_RE.match(name)
    num, label = (m.group(1), m.group(2) or name) if m else ("", name)
    node = {"id": re.sub(r"\W+", "_", label).strip("_").lower() or name, "num": num, "name": label,
            "physical": name, "privacy": "open", "handoff": None, "subfolders": [], "locked_subfolders": [],
            "per_item": False}
    if (root / name / "_inbox").is_dir():
        node["handoff"] = {"inbox": f"{name}/_inbox", "originals": True}
    return node


def _count_files(folder: Path) -> int:
    n = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "_", "~$"))]
        n += sum(1 for f in filenames if f not in ("desktop.ini", "Thumbs.db"))
    return n


def _propose(name: str) -> str | None:
    low = name.lower()
    for branch_id, words in PROPOSAL_KEYWORDS:
        if any(w in low for w in words):
            return branch_id
    return None


def _write_proposal(cfg: Config, counts: dict[str, int]) -> None:
    lang = cfg.lang
    std = {n["id"]: n for n in tree.default_tree(lang) + tree.addons(lang)}
    L = PROPOSAL_LABELS[lang]
    lines = [L["title"], "", L["intro"], "", L["cols"], "|---|---|---|"]
    for n in cfg.tree:
        if n["id"] == "brain" or n["physical"] == cfg.home.name:
            continue
        pid = _propose(n["physical"])
        target = f"{std[pid]['num']} {std[pid]['name']}" if pid and pid in std else "?"
        lines.append(f"| {n['physical']} | {counts.get(n['physical'], 0)} | {target} |")
    lines += ["", f"_{L['generated']} {date.today().isoformat()}_", ""]
    cfg.path("proposed_tree").write_text("\n".join(lines), encoding="utf-8")


def adopt(home: Path, root: Path, addons: list[str] = (), name: str = "") -> Config:
    """Register an existing archive as the instance, touching none of its files.

    `addons` (e.g. dev_projects, studies) are appended as new branches with their
    standard physical names; their folders are created with the first document."""
    home, root = Path(home), Path(root)
    if (home / BRAIN_FILE).exists():
        raise FileExistsError(f"an instance already exists: {home / BRAIN_FILE}")
    if not home.is_dir() or not root.is_dir():
        raise ValueError("home and root must exist")
    lang = _detect_lang(home)
    known = {a["id"]: a for a in tree.addons(lang)}
    unknown = [a for a in (addons or []) if a not in known]
    if unknown:
        raise ValueError(f"unknown add-on(s): {', '.join(unknown)}; choose from {', '.join(known)}")
    brain_node = dict(tree.default_tree(lang)[0])
    brain_node["physical"] = home.name
    branches = [brain_node]
    counts = {}
    for entry in sorted(os.listdir(root)):
        p = root / entry
        if not p.is_dir() or p.resolve() == home.resolve() or entry.startswith(SKIP_TOP_PREFIXES):
            continue
        branches.append(_branch_from_folder(root, home, entry, lang))
        counts[entry] = _count_files(p)
    taken = {n["physical"] for n in branches}
    for aid in addons or []:
        node = dict(known[aid])
        if node["physical"] not in taken:
            branches.append(node)
    cfg = Config(home=home, root=root, lang=lang, owner="", entities=[], tree=branches,
                 sources={"inbox": True, "gmail": False, "whatsapp": False, "downloads": False, "site": False},
                 data={"version": 1, "remote_warning": True, "adopted": date.today().isoformat(),
                       "name": name or DEFAULT_NAME[lang]})
    cfg.save()
    if not cfg.path("inbox").exists():
        cfg.path("inbox").mkdir()
    for kind in ("index", "ledger", "log"):
        if not cfg.path(kind).exists():
            _write_csv_header(cfg.path(kind), kind, lang)
    if not cfg.path("sensitive").exists():
        shutil.copyfile(ASSETS / "sensitive.default.json", cfg.path("sensitive"))
    _mark_medical_named_folders(cfg)
    _write_proposal(cfg, counts)
    return cfg


def _mark_medical_named_folders(cfg: Config) -> None:
    """Folders (depth <= 3) whose name contains a sensitive folder word get level ask, unless already covered."""
    g = sensitive.load(cfg)
    words = [w for w, lv in (g.get("folder_names") or {}).items() if lv in ("ask", "locked")]
    root = cfg.root
    for dirpath, dirnames, _ in os.walk(root):
        d = Path(dirpath)
        depth = len(d.relative_to(root).parts)
        if d.resolve() == cfg.home.resolve() or depth >= 3:
            dirnames[:] = []
            continue
        dirnames[:] = [x for x in dirnames if not x.startswith((".", "_", "~$"))]
        for name in dirnames:
            if any(w in name for w in words):
                rel = (d / name).relative_to(root).as_posix()
                if sensitive.level(cfg, rel) == "open":
                    sensitive.set_level(cfg, rel, "locked")


def scan(cfg: Config) -> dict:
    """Folders up to depth 2 (direct file counts, sensitivity) and the total file count. Names only."""
    root = cfg.root
    home = cfg.home.resolve()
    folders = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        rel = d.relative_to(root)
        depth = len(rel.parts)
        if d.resolve() == home or (depth and rel.parts[0].startswith(SKIP_TOP_PREFIXES)):
            dirnames[:] = []
            continue
        dirnames[:] = sorted(x for x in dirnames if not x.startswith((".", "_", "~$")))
        files = [f for f in filenames if f not in ("desktop.ini", "Thumbs.db")]
        if depth:
            total += len(files)
        if 1 <= depth <= 2:
            folders.append({"path": rel.as_posix(), "files": len(files), "sensitive": sensitive.is_sensitive(cfg, rel.as_posix())})
    return {"folders": folders, "total": total}


def rename(cfg: Config, new_name: str, move_folder: bool = False) -> dict:
    """Change what the person calls the archive. With `move_folder`, the brain folder follows the name.

    The display name lives in brain.json. Moving the folder renames only the brain folder
    (documents stay where they are, their paths are relative to the root), rewrites the
    ~/.seder/home pointer when it pointed here, and updates the path in the naming and
    profile files. Refuses when the new folder already exists."""
    new_name = tree._check_name(new_name)
    old_home = cfg.home
    out = {"name": new_name, "home": str(old_home), "moved": False, "pointer_updated": False, "warnings": []}
    cfg.data["name"] = new_name
    brain = next((n for n in cfg.tree if n.get("id") == "brain"), None)
    if brain is not None:
        brain["name"] = new_name
    if move_folder:
        prefix = "00_" if old_home.name.startswith("00") else ""
        new_home = old_home.parent / (prefix + new_name.replace(" ", "_"))
        if new_home.resolve() != old_home.resolve():
            if new_home.exists():
                raise FileExistsError(f"already exists: {new_home}")
            os.rename(old_home, new_home)
            cfg.home = new_home
            if brain is not None:
                brain["physical"] = new_home.name
            for key in ("naming", "profile"):
                p = cfg.path(key)
                if p.is_file():
                    text = p.read_text(encoding="utf-8")
                    text = text.replace(str(old_home), str(new_home)).replace(old_home.name, new_home.name)
                    p.write_text(text, encoding="utf-8")
            ptr = _config.HOME_POINTER
            try:
                if ptr.is_file() and Path(ptr.read_text(encoding="utf-8").strip().splitlines()[0].strip()) == old_home:
                    ptr.write_text(str(new_home) + "\n", encoding="utf-8")
                    out["pointer_updated"] = True
            except (OSError, IndexError):
                out["warnings"].append("could not read or update the ~/.seder/home pointer")
            if os.environ.get(_config.ENV_VAR) and Path(os.environ[_config.ENV_VAR]) == old_home:
                out["warnings"].append(f"{_config.ENV_VAR} still points at the old folder; update it")
            out.update(moved=True, home=str(new_home))
    cfg.save()
    return out
