"""Filing: move an approved document into its folder, with a hash check, a log row and an undo command.

Never overwrites, never deletes. A branch with a hand-off sends the document
(the original format, when asked) to another engine's inbox instead.
"""
import csv
import datetime as dt
import os
import re
import shutil
from pathlib import Path

from . import index, names, tree
from .config import Config

FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
MAX_NAME = 180
APPROVED = {"he": "כן", "en": "yes"}


def clean_name(name: str, ext: str | None = None) -> str:
    """Validate a file name; add `ext` when the name has no extension. Raises ValueError."""
    n = str(name)
    if not n:
        raise ValueError("empty name")
    if FORBIDDEN.search(n):
        raise ValueError(f"forbidden character in name: {n!r}")
    if len(n) > MAX_NAME:
        raise ValueError(f"name longer than {MAX_NAME} characters")
    if n[0] in ". ":
        raise ValueError(f"name starts with a dot or space: {n!r}")
    if n[-1] in ". ":
        raise ValueError(f"name ends with a dot or space: {n!r}")
    if ext and not Path(n).suffix:
        n += ext
    stem = Path(n).stem
    if stem and stem[-1] in ". ":
        raise ValueError(f"name ends with a dot or space before the extension: {n!r}")
    return n


def free_name(target_dir: Path, name: str) -> str:
    """`name` if unused in `target_dir`, else `stem (2).ext`, `stem (3).ext`, ..."""
    target_dir = Path(target_dir)
    if not (target_dir / name).exists():
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 2
    while (target_dir / f"{stem} ({n}){suffix}").exists():
        n += 1
    return f"{stem} ({n}){suffix}"


def _log(cfg: Config, rec: dict) -> None:
    path = cfg.path("log")
    new = not path.exists()
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(names.header("log", cfg.lang))
        w.writerow(names.to_row("log", cfg.lang, rec))


def file_doc(cfg: Config, src: Path, folder: str, name: str, why: str,
             mkdir: bool = False, original: Path | None = None) -> dict:
    """Move `src` (or `original`, for a hand-off branch that wants originals) into `folder` as `name`."""
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"source missing: {src}")
    name = clean_name(name)
    target_dir = tree.check_target(cfg, folder)
    handoff = tree.handoff_for(cfg, folder)
    moving = src
    is_handoff = False
    if handoff:
        is_handoff = True
        target_dir = handoff["inbox"]
        if handoff["originals"] and original is not None and Path(original).is_file():
            moving = Path(original)
            name = Path(name).stem + moving.suffix.lower()
        if not target_dir.is_dir() and target_dir.parent.is_dir():
            target_dir.mkdir()
    if not target_dir.is_dir():
        if not mkdir:
            raise ValueError(f"folder does not exist (a new folder needs approval and mkdir): {target_dir}")
        if not target_dir.parent.is_dir():
            raise ValueError(f"parent folder does not exist: {target_dir.parent}")
        target_dir.mkdir()
    dest = target_dir / name
    if dest.exists():
        raise FileExistsError(f"target exists, not overwriting: {dest}")
    before = index.sha12(moving)
    shutil.move(str(moving), str(dest))
    after = index.sha12(dest)
    if before != after:
        raise RuntimeError(f"sha changed {before} -> {after}; the file is at {dest}")
    undo = f'Move-Item -LiteralPath "{dest}" -Destination "{moving}"'
    _log(cfg, {
        "when": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "orig": moving.name, "new": name, "folder": str(target_dir), "why": why,
        "approved": APPROVED.get(cfg.lang, "yes"), "sha12": after, "undo": undo,
    })
    if not is_handoff:
        index.update_row(cfg, dest)
    return {"dest": str(dest), "sha12": after, "undo": undo, "handoff": is_handoff}


def namecheck(cfg: Config, folder: str, name: str, src: Path | None = None) -> dict:
    """Does `folder/name` exist, is it the same file as `src`, and which name is free."""
    name = clean_name(name)
    target_dir = tree.check_target(cfg, folder)
    dest = target_dir / name
    exists = dest.exists()
    same = None
    if exists and src is not None and Path(src).is_file():
        same = index.sha12(Path(src)) == index.sha12(dest)
    return {"exists": exists, "same": same, "free": free_name(target_dir, name) if target_dir.is_dir() else name}
