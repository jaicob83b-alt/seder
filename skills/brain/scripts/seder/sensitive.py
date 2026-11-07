"""Privacy levels, secrets, deny rules and template names for documents the model never reads.

Three levels per folder: `open` (the model may read), `ask` (a question before
every file), `locked` (names only). They live in the instance's sensitive
file, whose format extends the live archive's `רגיש.json` so older tools
keep reading it.
"""
import fnmatch
import json
import os
import re
from datetime import datetime
from pathlib import Path

from .config import Config

ASSETS = Path(__file__).resolve().parents[2] / "assets"
LEVELS = ("open", "ask", "locked")
RANK = {"open": 0, "ask": 1, "locked": 2}
HEADLESS_TOOL_DENY = ["Write", "Edit", "Bash", "PowerShell", "WebFetch", "WebSearch", "NotebookEdit", "Agent"]
KIND = {"he": "רפואי", "en": "Medical"}
UNKNOWN = {"he": "לא ידוע", "en": "unknown"}


def defaults() -> dict:
    return json.loads((ASSETS / "sensitive.default.json").read_text(encoding="utf-8"))


def load(cfg: Config) -> dict:
    """Defaults merged with the instance file; a key in the instance file replaces the default."""
    d = defaults()
    p = cfg.path("sensitive")
    if p.is_file():
        try:
            user = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            user = {}
        for k, v in user.items():
            if not k.startswith("_"):
                d[k] = v
    if isinstance(d.get("folder_names"), list):  # tolerate the plain-list form
        d["folder_names"] = {n: "ask" for n in d["folder_names"]}
    return d


def _norm(rel: str) -> str:
    return str(rel).replace("\\", "/").strip("/")


def _rel(cfg: Config, path) -> str:
    """Path -> root-relative posix string (an absolute path inside the root is accepted)."""
    s = _norm(path)
    p = Path(s)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(cfg.root.resolve()).as_posix()
        except ValueError:
            return s
    return s


def _under(rel: str, folder: str) -> bool:
    f = _norm(folder)
    return bool(f) and (rel == f or rel.startswith(f + "/"))


def level(cfg: Config, rel: str) -> str:
    """Highest level that applies to the path: locked > ask > open."""
    g = load(cfg)
    r = _rel(cfg, rel)
    segs = [s for s in r.split("/") if s]
    best = "open"

    def bump(lv):
        nonlocal best
        if lv in RANK and RANK[lv] > RANK[best]:
            best = lv

    for folder, lv in (g.get("levels") or {}).items():
        if _under(r, folder):
            bump(lv)
    for folder in g.get("medical_folders") or []:
        if _under(r, folder):
            bump("ask")
    for folder in g.get("secret_folders") or []:
        if _under(r, folder):
            bump("locked")
    fn = g.get("folder_names") or {}
    for seg in segs:
        bump(fn.get(seg, "open"))
    if segs:
        from . import tree  # local import: tree depends on config only
        node = tree.find_node(cfg, segs[0])
        if node:
            bump(node.get("privacy", "open"))
    return best


def is_sensitive(cfg: Config, rel: str) -> bool:
    return level(cfg, rel) != "open"


def set_level(cfg: Config, rel: str, lv: str) -> dict:
    """Write a folder's level into the instance file (open = remove). Returns the levels map."""
    if lv not in LEVELS:
        raise ValueError(f"level must be one of {', '.join(LEVELS)}: {lv!r}")
    p = cfg.path("sensitive")
    user = {}
    if p.is_file():
        try:
            user = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            user = {}
    levels = dict(user.get("levels") or {})
    key = _rel(cfg, rel)
    if lv == "open":
        levels.pop(key, None)
    else:
        levels[key] = lv
    user["levels"] = levels
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(user, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return levels


def is_secret(path: str) -> bool:
    """True when the file name matches a secret pattern (.env, keys, passwords, tokens...)."""
    name = _norm(path).rsplit("/", 1)[-1].lower()
    if not name:
        return False
    for pat in defaults().get("secret_patterns", []):
        pat = pat[3:] if pat.startswith("**/") else pat
        if fnmatch.fnmatchcase(name, pat.lower()):
            return True
    return False


def looks_medical(cfg: Config, sender: str, names: list[str], text: str) -> bool:
    """Local check, no model: a medical sender, a medical word in a name, or two in the text."""
    g = load(cfg)
    low = (sender or "").lower()
    if any(s.lower() in low for s in g.get("medical_senders", [])):
        return True
    words = g.get("medical_words", [])
    if any(w.lower() in (n or "").lower() for n in names for w in words):
        return True
    t = (text or "").lower()
    return len({w for w in words if w.lower() in t}) >= 2


def _rule_path(p: Path) -> str:
    """Absolute path in the permission-rule spelling: //c/Users/... on Windows, /home/... elsewhere."""
    s = Path(p).resolve().as_posix()
    if re.match(r"^[A-Za-z]:/", s):
        return "//" + s[0].lower() + s[2:]
    return s


def _folders_with_levels(cfg: Config, g: dict) -> set[str]:
    out = {_norm(f) for f, lv in (g.get("levels") or {}).items() if lv in ("ask", "locked")}
    out |= {_norm(f) for f in g.get("medical_folders") or []}
    out |= {_norm(f) for f in g.get("secret_folders") or []}
    fn = {n for n, lv in (g.get("folder_names") or {}).items() if lv in ("ask", "locked")}
    root = cfg.root
    home = cfg.home.resolve()
    if fn and root.is_dir():
        for dirpath, dirnames, _ in os.walk(root):
            d = Path(dirpath)
            depth = len(d.relative_to(root).parts)
            if d.resolve() == home or depth >= 3:
                dirnames[:] = []
                continue
            for name in dirnames:
                if name in fn:
                    out.add((d / name).relative_to(root).as_posix())
    return {f for f in out if f}


def deny_rules(cfg: Config) -> list[str]:
    g = load(cfg)
    rules = [f"Read({_rule_path(cfg.root / f)}/**)" for f in sorted(_folders_with_levels(cfg, g))]
    rules += [f"Read({pat})" for pat in g.get("secret_patterns", [])]
    return rules


def allow_rules(cfg: Config) -> list[str]:
    return [f"Read({_rule_path(cfg.root)}/**)"]


def write_headless_settings(cfg: Config, out: Path) -> Path:
    """Settings file for unattended runs: read only inside the root, never sensitive folders or secrets."""
    out = Path(out)
    data = {"permissions": {"allow": allow_rules(cfg), "deny": deny_rules(cfg) + HEADLESS_TOOL_DENY}}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def _year_month(text: str) -> str | None:
    for m in re.finditer(r"\b(20\d\d)[-./](\d\d)\b", text or ""):
        if 1 <= int(m.group(2)) <= 12:
            return f"{m.group(1)}-{m.group(2)}"
    for m in re.finditer(r"\b\d\d[./](\d\d)[./](20\d\d)\b", text or ""):
        if 1 <= int(m.group(1)) <= 12:
            return f"{m.group(2)}-{m.group(1)}"
    return None


def template_name(cfg: Config, path: Path, whose: str = "", text: str = "") -> str:
    """`YYYY-MM_רפואי - של מי.pdf` for a document the model does not read."""
    ym = _year_month(text)
    if ym is None:
        ym = datetime.fromtimestamp(Path(path).stat().st_mtime).strftime("%Y-%m")
    who = whose or cfg.owner or UNKNOWN.get(cfg.lang, "unknown")
    return f"{ym}_{KIND.get(cfg.lang, 'Medical')} - {who}.pdf"
