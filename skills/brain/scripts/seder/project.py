"""Project cards: one folder per project with a short card, decisions and documents.

The code and the large files stay where they are; the card links to them.
Archiving (moving a quiet project into the branch's archive folder) is proposed
by the weekly review and runs only after the person says yes.
"""
import datetime as dt
import re
import shutil
from datetime import date
from pathlib import Path

from .config import Config

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "project_template"
NAMES = {
    "he": {"card": "כרטיס.md", "decisions": "החלטות.md", "docs": "מסמכים", "archive": "_ארכיון"},
    "en": {"card": "card.md", "decisions": "decisions.md", "docs": "Documents", "archive": "_archive"},
}
BRANCH_IDS = ("dev_projects", "projects")
FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
NONE = "—"


def _names(cfg: Config) -> dict:
    return NAMES.get(cfg.lang, NAMES["en"])


def branches(cfg: Config) -> list[dict]:
    """The project branches present in this instance, 07 first when it exists."""
    found = [n for bid in BRANCH_IDS for n in cfg.tree if n.get("id") == bid]
    if not found:
        raise ValueError("no project branch in brain.json (add-on 07 dev_projects or 06 projects)")
    return found


def _check_name(name: str) -> str:
    n = str(name or "")
    if not n or FORBIDDEN.search(n) or n[0] in "_. " or n[-1] in ". " or len(n) > 120:
        raise ValueError(f"bad project name: {name!r}")
    return n


def _template(kind: str, lang: str) -> str:
    return (ASSETS / f"{kind}.{lang}.md").read_text(encoding="utf-8")


def _relevant_lessons(cfg: Config, name: str) -> str:
    try:
        from . import studies  # add-on 08; absent until Task 12
    except ImportError:
        return NONE
    try:
        found = studies.relevant(cfg, name)
    except Exception:
        return NONE
    return "\n".join(f"- {x['label']}" for x in found) if found else NONE


def new_project(cfg: Config, name: str, code_path: str | None, today: date, branch_id: str | None = None) -> Path:
    """Create `<branch>/<name>/` with a card, a decisions file and a documents folder. Never overwrites."""
    name = _check_name(name)
    node = next((n for n in branches(cfg) if branch_id is None or n.get("id") == branch_id), None)
    if node is None:
        raise ValueError(f"no branch {branch_id!r} in brain.json")
    base = cfg.root / node["physical"]
    p = base / name
    if p.exists():
        raise FileExistsError(f"project already exists: {p}")
    n = _names(cfg)
    (p / n["docs"]).mkdir(parents=True)
    values = {"name": name, "code_path": code_path or NONE, "created": today.isoformat(),
              "relevant_lessons": _relevant_lessons(cfg, name)}
    for kind, fname in (("card", n["card"]), ("decisions", n["decisions"])):
        text = _template(kind, cfg.lang)
        for k, v in values.items():
            text = text.replace("{" + k + "}", v)
        (p / fname).write_text(text, encoding="utf-8")
    return p


def _last_modified(p: Path) -> date:
    stamps = [p.stat().st_mtime] + [f.stat().st_mtime for f in p.rglob("*")]
    return dt.datetime.fromtimestamp(max(stamps)).date()


def _created(p: Path, card: Path) -> str:
    if card.is_file():
        m = DATE_RE.search(card.read_text(encoding="utf-8", errors="ignore"))
        if m:
            return m.group(1)
    return dt.datetime.fromtimestamp(p.stat().st_ctime).date().isoformat()


def list_projects(cfg: Config) -> list[dict]:
    n = _names(cfg)
    out = []
    for node in branches(cfg):
        base = cfg.root / node["physical"]
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if not p.is_dir() or p.name.startswith(("_", ".")):
                continue
            card = p / n["card"]
            out.append({"name": p.name, "created": _created(p, card), "last_modified": _last_modified(p).isoformat(),
                        "card": str(card) if card.is_file() else "", "path": str(p)})
    return out


def archive_candidates(cfg: Config, today: date, days: int = 90) -> list[dict]:
    """Projects with no file changed in the last `days` days (and not yet archived)."""
    out = []
    for p in list_projects(cfg):
        last = date.fromisoformat(p["last_modified"])
        if (today - last).days > days:
            out.append({"name": p["name"], "last_modified": p["last_modified"], "path": p["path"]})
    return out


def archive(cfg: Config, name: str) -> Path:
    """Move a project into its branch's archive folder. Call only after the person said yes."""
    name = _check_name(name)
    n = _names(cfg)
    for node in branches(cfg):
        src = cfg.root / node["physical"] / name
        if src.is_dir():
            dest = cfg.root / node["physical"] / n["archive"] / name
            if dest.exists():
                raise FileExistsError(f"already in the archive: {dest}")
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dest))
            return dest
    raise FileNotFoundError(f"no project named {name!r}")
