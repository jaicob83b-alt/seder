"""Studies (add-on 08): import a course with topic names, index its lessons, find relevant ones.

Import copies, never moves: the original course folder stays as a backup.
The index is a markdown table built from folder names and the first heading
of each lesson's README, so a new project card can list the lessons that
match its name.
"""
import re
import shutil
from pathlib import Path

from .config import Config

HEAD = {
    "he": ("# אינדקס לימודים", "נבנה אוטומטית משמות התיקיות וכותרת ה-README של כל שיעור.", "| קורס | שיעור | קבצים | כותרת |"),
    "en": ("# Studies index", "Built automatically from folder names and each lesson's README heading.", "| course | lesson | files | title |"),
}
WORD = re.compile(r"\w{3,}", re.U)
TITLE = re.compile(r"^#\s+(.+?)\s*$", re.M)
HEBREW_PREFIXES = "והבלמשכ"


def branch(cfg: Config) -> dict:
    node = next((n for n in cfg.tree if n.get("id") == "studies"), None)
    if node is None:
        raise ValueError("no studies branch in brain.json (add-on 08)")
    return node


def _count(p: Path) -> tuple[int, int]:
    if p.is_file():
        return 1, p.stat().st_size
    files = [f for f in p.rglob("*") if f.is_file()]
    return len(files), sum(f.stat().st_size for f in files)


def import_course(cfg: Config, src: Path, course: str, rename: dict, dry_run: bool = True) -> list[dict]:
    """Plan (dry run) or copy every top-level item of `src` into <08>/<course>/<renamed>."""
    node = branch(cfg)
    src = Path(src)
    if not src.is_dir():
        raise ValueError(f"source folder does not exist: {src}")
    if not course or course.startswith((".", "_")):
        raise ValueError("course name is required")
    base = cfg.root / node["physical"] / course
    plan = []
    for entry in sorted(src.iterdir()):
        if entry.name.startswith((".", "~$")):
            continue
        files, size = _count(entry)
        plan.append({"from": str(entry), "to": str(base / (rename or {}).get(entry.name, entry.name)), "files": files, "bytes": size})
    if dry_run:
        return plan
    taken = [p["to"] for p in plan if Path(p["to"]).exists()]
    if taken:
        raise FileExistsError(f"target exists, nothing copied: {taken[0]}")
    base.mkdir(parents=True, exist_ok=True)
    for p in plan:
        f, t = Path(p["from"]), Path(p["to"])
        if f.is_dir():
            shutil.copytree(f, t)
        else:
            shutil.copy2(f, t)
    return plan


def _title(lesson: Path) -> str:
    candidates = sorted(lesson.glob("*.md"), key=lambda p: (p.name.lower() != "readme.md", p.name))
    for md in candidates:
        try:
            m = TITLE.search(md.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if m:
            return m.group(1).replace("|", "/")
    return ""


def lessons(cfg: Config) -> list[dict]:
    """Every lesson folder under every course: course, lesson, files, title."""
    base = cfg.root / branch(cfg)["physical"]
    out = []
    if not base.is_dir():
        return out
    for course in sorted(base.iterdir()):
        if not course.is_dir() or course.name.startswith(("_", ".")):
            continue
        for lesson in sorted(course.iterdir()):
            if not lesson.is_dir() or lesson.name.startswith(("_", ".")):
                continue
            files, _ = _count(lesson)
            out.append({"course": course.name, "lesson": lesson.name, "files": files, "title": _title(lesson)})
    return out


def build_index(cfg: Config) -> Path:
    head = HEAD.get(cfg.lang, HEAD["en"])
    lines = [head[0], "", head[1], "", head[2], "|---|---|---|---|"]
    for r in lessons(cfg):
        lines.append(f"| {r['course'].replace('|', '/')} | {r['lesson'].replace('|', '/')} | {r['files']} | {r['title']} |")
    out = cfg.path("studies_index")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def index_rows(cfg: Config) -> list[dict]:
    path = cfg.path("studies_index")
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[2].isdigit():
            continue
        rows.append({"course": cells[0], "lesson": cells[1], "files": int(cells[2]), "title": cells[3]})
    return rows


def _words(text: str) -> set[str]:
    out = set()
    for w in WORD.findall(text.lower()):
        out.add(w)
        if w[0] in HEBREW_PREFIXES and len(w) > 3:  # וסוכן -> סוכן, לדוח -> דוח
            out.add(w[1:])
    return out


def relevant(cfg: Config, query: str, limit: int = 5) -> list[dict]:
    """Lessons whose name or title share words with the query, best first."""
    q = _words(query)
    if not q:
        return []
    found = []
    for r in index_rows(cfg):
        score = len(q & _words(f"{r['lesson']} {r['title']}"))
        if score:
            found.append({"lesson": r["lesson"], "course": r["course"], "score": score, "label": f"{r['course']} / {r['lesson']}"})
    found.sort(key=lambda x: (-x["score"], x["course"], x["lesson"]))
    return found[:limit]
