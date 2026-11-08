"""Folder sources: copy new documents from watched folders into the inbox.

A watched folder is any folder on this computer: the PC's Downloads, or a folder
that Syncthing fills from the phone (its Download folder, WhatsApp Documents).
`pull` copies what is new there into the inbox and stops; filing still goes
through a proposal and a yes. Originals are never moved or deleted.

Rules: top level only; documents only (by extension); files older than the day
the folder was added are ignored, so adding Downloads does not flood the inbox
with years of history; a file is copied once (by content hash), even if it is
renamed or the same file arrives in two folders. State lives in the inbox as
`_sources_state.json`, which the inbox listing never shows as a document.
"""
import json
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

from . import filing, index
from .config import Config
from .discover import DOC_EXTS

STATE = "_sources_state.json"
PARTIAL = (".tmp", ".part", ".crdownload", ".download", ".partial")
MIN_BYTES = 1024
MAX_BYTES = 60 * 1024 * 1024


def folders(cfg: Config) -> list[dict]:
    return list((cfg.sources or {}).get("folders") or [])


def add(cfg: Config, path: Path, label: str = "") -> dict:
    p = Path(path).expanduser()
    if not p.is_dir():
        raise ValueError(f"not a folder: {p}")
    rp = p.resolve()
    if rp == cfg.home.resolve() or rp.is_relative_to(cfg.home.resolve()):
        raise ValueError("a folder inside the brain folder cannot be a source")
    cur = folders(cfg)
    if any(Path(f["path"]).resolve() == rp for f in cur):
        raise ValueError(f"already watched: {p}")
    entry = {"path": str(p), "label": label or p.name, "since": date.today().isoformat()}
    cfg.sources = dict(cfg.sources or {})
    cfg.sources["folders"] = cur + [entry]
    cfg.save()
    return entry


def remove(cfg: Config, path: Path) -> bool:
    rp = Path(path).expanduser().resolve()
    cur = folders(cfg)
    keep = [f for f in cur if Path(f["path"]).resolve() != rp]
    if len(keep) == len(cur):
        return False
    cfg.sources = dict(cfg.sources or {})
    cfg.sources["folders"] = keep
    cfg.save()
    return True


def _state(box: Path) -> dict:
    try:
        return json.loads((box / STATE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(box: Path, st: dict) -> None:
    tmp = box / (STATE + ".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, box / STATE)


def _candidate(p: Path, since_ts: float) -> bool:
    name = p.name
    if name.startswith((".", "~$", ".syncthing.")) or name.lower().endswith(PARTIAL):
        return False
    if p.suffix.lower() not in DOC_EXTS:
        return False
    try:
        st = p.stat()
    except OSError:
        return False
    if not (MIN_BYTES <= st.st_size <= MAX_BYTES):
        return False
    if st.st_mtime < since_ts:
        return False
    return time.time() - st.st_mtime > 5  # still being written


def pull(cfg: Config) -> dict:
    """Copy new documents from every watched folder into the inbox. Returns what happened per folder."""
    box = cfg.path("inbox")
    box.mkdir(exist_ok=True)
    st = _state(box)
    seen = set(st.get("seen", []))
    report = []
    for f in folders(cfg):
        src = Path(f["path"])
        row = {"path": str(src), "label": f.get("label", ""), "copied": [], "error": ""}
        if not src.is_dir():
            row["error"] = "folder not found"
            report.append(row)
            continue
        since_ts = datetime.fromisoformat(f.get("since") or "1970-01-01").timestamp()
        try:
            entries = sorted(src.iterdir())
        except OSError as e:
            row["error"] = f"{e.__class__.__name__}"
            report.append(row)
            continue
        for p in entries:
            if not p.is_file() or not _candidate(p, since_ts):
                continue
            try:
                sha = index.sha12(p)
                if sha in seen:
                    continue
                dest = box / filing.free_name(box, p.name)
                shutil.copy2(p, dest)
                seen.add(sha)
                row["copied"].append(dest.name)
            except OSError as e:
                row["error"] = f"{p.name}: {e.__class__.__name__}"
        report.append(row)
    st["seen"] = sorted(seen)
    st["last_run"] = datetime.now().isoformat(timespec="seconds")
    st["last_report"] = [{"label": r["label"], "copied": len(r["copied"]), "error": r["error"]} for r in report]
    _save_state(box, st)
    return {"folders": report, "copied": sum(len(r["copied"]) for r in report), "last_run": st["last_run"]}


def status(cfg: Config) -> dict:
    st = _state(cfg.path("inbox"))
    return {"folders": folders(cfg), "last_run": st.get("last_run"), "last_report": st.get("last_report", [])}
