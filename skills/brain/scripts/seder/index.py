"""The index: one CSV row per document, built from names, sizes and hashes only.

Never opens document content. Column words follow the instance language;
the `path` column keeps the live archive's backslash form on every platform.
"""
import csv
import hashlib
import os
import re
from pathlib import Path

from . import names, sensitive
from .config import Config

SKIP_FILES = {"desktop.ini", "Thumbs.db"}
SKIP_DIR_PREFIXES = (".", "_", "~$")
SKIP_TOP_PREFIXES = ("My ",)  # Windows special folders inside Documents
SKIP_IN_HANDOFF = {"scripts", "data", "dashboard", "_snapshots", "_backup", "__pycache__", "financial-dashboard"}
DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?_")
SENSITIVE_MARK = {"he": "רפואי", "en": "sensitive"}


def sha_full(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha12(path: Path) -> str:
    return sha_full(path)[:12]


def _rel_parts(cfg: Config, path) -> tuple[str, ...]:
    """Root-relative parts of a path given relative (either separator) or absolute."""
    p = Path(str(path).replace("\\", "/"))
    if p.is_absolute():
        p = p.resolve().relative_to(cfg.root.resolve())
    return tuple(part for part in p.parts if part not in ("", "."))


def record(cfg: Config, path) -> dict:
    """The index record of one file (internal keys)."""
    parts = _rel_parts(cfg, path)
    full = cfg.root.joinpath(*parts)
    name = parts[-1]
    m = DATE_RE.match(name)
    date = (m.group(1) + ("-" + m.group(2) if m.group(2) else "")) if m else ""
    rel_posix = "/".join(parts)
    return {
        "path": "\\".join(parts),
        "topic": parts[0],
        "subfolder": "\\".join(parts[1:-1]),
        "name": name,
        "date": date,
        "ext": full.suffix.lower().lstrip("."),
        "kb": round(full.stat().st_size / 1024),
        "sensitive": SENSITIVE_MARK.get(cfg.lang, "sensitive") if sensitive.is_sensitive(cfg, rel_posix) else "",
        "sha12": sha12(full),
    }


def _handoff_tops(cfg: Config) -> set[str]:
    return {n.get("physical", "") for n in cfg.tree if n.get("handoff")}


def scan_files(cfg: Config):
    """Yield every document path under the root, with the live archive's skip rules."""
    root = cfg.root
    home = cfg.home.resolve()
    handoff_tops = _handoff_tops(cfg)
    for top in sorted(os.listdir(root)):
        tp = root / top
        if not tp.is_dir() or tp.resolve() == home or top.startswith(SKIP_DIR_PREFIXES + SKIP_TOP_PREFIXES):
            continue
        for dirpath, dirnames, filenames in os.walk(tp):
            keep = [d for d in dirnames if not d.startswith(SKIP_DIR_PREFIXES)]
            if top in handoff_tops:
                keep = [d for d in keep if d not in SKIP_IN_HANDOFF]
            dirnames[:] = sorted(keep)
            for f in sorted(filenames):
                if f in SKIP_FILES or f.endswith(".pyc") or f.startswith("~$"):
                    continue
                yield Path(dirpath) / f


def _write(cfg: Config, recs: list[dict]) -> None:
    path = cfg.path("index")
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(names.header("index", cfg.lang))
        for r in recs:
            w.writerow(names.to_row("index", cfg.lang, r))
    os.replace(tmp, path)


def rebuild(cfg: Config) -> int:
    recs = [record(cfg, p) for p in scan_files(cfg)]
    _write(cfg, recs)
    return len(recs)


def rows(cfg: Config) -> list[dict]:
    path = cfg.path("index")
    if not path.is_file():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [names.from_row("index", cfg.lang, row) for row in csv.DictReader(f)]


def _same(a: str, b: str) -> bool:
    return a.replace("/", "\\").strip("\\") == b.replace("/", "\\").strip("\\")


def update_row(cfg: Config, rel: str) -> None:
    """Replace or add the row of one file; drop it when the file is gone. Keeps order and header."""
    parts = _rel_parts(cfg, rel)
    key = "\\".join(parts)
    current = rows(cfg)
    exists = cfg.root.joinpath(*parts).is_file()
    new = record(cfg, rel) if exists else None
    out, replaced = [], False
    for r in current:
        if _same(r["path"], key):
            if new is not None and not replaced:
                out.append(new)
                replaced = True
            continue
        out.append(r)
    if new is not None and not replaced:
        out.append(new)
    _write(cfg, out)


def find_by_sha(cfg: Config, sha: str) -> list[str]:
    sha = (sha or "").lower()
    return [r["path"] for r in rows(cfg) if r["sha12"].lower() == sha] if sha else []
