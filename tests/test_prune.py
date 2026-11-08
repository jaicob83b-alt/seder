import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from seder import prune

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"
TODAY = date(2026, 11, 7)


def _age(p: Path, days: int):
    t = time.time() - days * 86400 - 3600  # an hour of slack: mtime rounding must not turn 20 days into 19
    os.utime(p, (t, t))


def make_projects(tmp_path):
    """A fake ~/.claude/projects: two project folders, transcripts with and without the intake marker, old and new."""
    proj = tmp_path / "projects"
    a = proj / "C--Users-x-Documents"
    a.mkdir(parents=True)
    (a / "old.jsonl").write_text('{"type":"user","text":"wrote _proposal.json for 3 docs"}\n', encoding="utf-8")
    (a / "old").mkdir()
    (a / "old" / "tool-result.txt").write_text("x", encoding="utf-8")
    _age(a / "old.jsonl", 20)
    (a / "plain.jsonl").write_text('{"type":"user","text":"unrelated chat"}\n', encoding="utf-8")
    _age(a / "plain.jsonl", 20)
    (a / "new.jsonl").write_text('{"type":"user","text":"SEDER_INTAKE today"}\n', encoding="utf-8")
    _age(a / "new.jsonl", 1)
    b = proj / "c--"
    b.mkdir()
    (b / "x.jsonl").write_text('SEDER_INTAKE\n', encoding="utf-8")
    _age(b / "x.jsonl", 40)
    return proj


def test_scan_finds_only_marked_and_old(tmp_path):
    proj = make_projects(tmp_path)
    items = prune.scan(proj, older_days=7)
    assert {(i["project"], Path(i["file"]).name) for i in items} == {("C--Users-x-Documents", "old.jsonl"), ("c--", "x.jsonl")}
    assert all(set(i) == {"file", "project", "kb", "age_days", "sidecar"} for i in items)
    old = next(i for i in items if i["project"] == "C--Users-x-Documents")
    assert old["age_days"] >= 20 and old["sidecar"].endswith("old")
    assert prune.scan(proj, older_days=60) == []
    assert prune.scan(tmp_path / "nope", older_days=0) == []


def test_move_keeps_files_and_sidecar(tmp_path):
    proj = make_projects(tmp_path)
    dest = tmp_path / "archive"
    before = sum(1 for p in proj.rglob("*") if p.is_file())
    moved = prune.move(prune.scan(proj, older_days=7), dest)
    assert len(moved) == 2 and (dest / "C--Users-x-Documents__old.jsonl").is_file() and (dest / "C--Users-x-Documents__old" / "tool-result.txt").is_file()
    assert (dest / "c--__x.jsonl").is_file() and not (proj / "C--Users-x-Documents" / "old.jsonl").exists()
    assert (proj / "C--Users-x-Documents" / "plain.jsonl").exists() and (proj / "C--Users-x-Documents" / "new.jsonl").exists()
    after = sum(1 for p in proj.rglob("*") if p.is_file()) + sum(1 for p in dest.rglob("*") if p.is_file())
    assert after == before  # nothing deleted
    moved2 = prune.move(prune.scan(proj, older_days=7), dest)
    assert moved2 == []


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_cli_prune_dry_then_go(home, tmp_path):
    proj = make_projects(tmp_path)
    d = json.loads(run_cli(home, "prune-transcripts", "--older-days", "7", "--projects", str(proj)).stdout)
    assert d["ok"] and d["go"] is False and len(d["transcripts"]) == 2 and (proj / "c--" / "x.jsonl").exists()
    assert Path(d["dest"]).name == "_ארכיון_תמלילים"
    d = json.loads(run_cli(home, "prune-transcripts", "--older-days", "7", "--projects", str(proj), "--go").stdout)
    assert d["ok"] and d["go"] is True and len(d["moved"]) == 2 and (home / "_ארכיון_תמלילים" / "c--__x.jsonl").is_file()


def test_cli_settings_headless(home, tmp_path):
    out = tmp_path / "headless.json"
    d = json.loads(run_cli(home, "settings", "--headless", str(out)).stdout)
    s = json.loads(out.read_text(encoding="utf-8"))
    assert d["ok"] and Path(d["file"]) == out and "Read(**/.env)" in s["permissions"]["deny"] and "Bash" in s["permissions"]["deny"]
    assert len(s["permissions"]["allow"]) == 1 and d["deny"] == len(s["permissions"]["deny"])


def test_cli_pointer(home, tmp_path):
    f = tmp_path / ".seder" / "home"
    d = json.loads(run_cli(home, "pointer", "--file", str(f)).stdout)
    assert d == {"ok": True, "file": str(f), "home": None}
    d = json.loads(run_cli(home, "pointer", "--write", "--file", str(f)).stdout)
    assert d["ok"] and d["home"] == str(home) and f.read_text(encoding="utf-8").strip() == str(home)
    d = json.loads(run_cli(home, "pointer", "--file", str(f)).stdout)
    assert d["home"] == str(home)
