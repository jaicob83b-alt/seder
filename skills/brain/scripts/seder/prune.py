"""Intake transcripts: find the old ones and move them out of the active projects folder.

Claude Code keeps every conversation as a `.jsonl` under `~/.claude/projects/<cwd>/`.
An intake conversation holds document content, so the person may want it off the
active folder. Moves only, never deletes.
"""
import datetime as dt
import shutil
from pathlib import Path

MARKERS = ("SEDER_INTAKE", "_proposal.json")


def default_projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def _has_marker(path: Path, markers) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read()
    except OSError:
        return False
    return any(m.encode("utf-8") in chunk for m in markers)


def scan(projects: Path, older_days: int, markers=MARKERS, now: float | None = None) -> list[dict]:
    """Intake transcripts older than `older_days` days, with their sidecar folder when one exists."""
    projects = Path(projects)
    if not projects.is_dir():
        return []
    now = dt.datetime.now().timestamp() if now is None else now
    out = []
    for proj in sorted(p for p in projects.iterdir() if p.is_dir()):
        for f in sorted(proj.glob("*.jsonl")):
            age = (now - f.stat().st_mtime) / 86400
            if age <= older_days or not _has_marker(f, markers):
                continue
            sidecar = f.with_suffix("")
            out.append({"file": str(f), "project": proj.name, "kb": round(f.stat().st_size / 1024),
                        "age_days": int(age), "sidecar": str(sidecar) if sidecar.is_dir() else ""})
    return out


def move(items: list[dict], dest: Path) -> list[dict]:
    """Move the listed transcripts (and sidecars) into `dest`, prefixed by their project folder name."""
    dest = Path(dest)
    moved = []
    for it in items:
        src = Path(it["file"])
        if not src.is_file():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / f"{it['project']}__{src.name}"
        if target.exists():
            continue
        shutil.move(str(src), str(target))
        rec = {"from": str(src), "to": str(target)}
        if it.get("sidecar") and Path(it["sidecar"]).is_dir():
            side_target = dest / f"{it['project']}__{Path(it['sidecar']).name}"
            if not side_target.exists():
                shutil.move(it["sidecar"], str(side_target))
                rec["sidecar_to"] = str(side_target)
        moved.append(rec)
    return moved
