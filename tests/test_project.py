import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest

from seder import config, project, tree

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def add_dev_branch(home):
    cfg = config.Config.load(home)
    cfg.tree.append(next(a for a in tree.addons(cfg.lang) if a["id"] == "dev_projects"))
    cfg.save()
    return config.Config.load(home)


def test_new_project_creates_card_decisions_docs(home):
    cfg = add_dev_branch(home)
    p = project.new_project(cfg, "Seder", "C:/dev/seder", date(2026, 11, 7))
    assert p == cfg.root / "07_פרויקטי_פיתוח" / "Seder"
    assert (p / "כרטיס.md").is_file() and (p / "החלטות.md").is_file() and (p / "מסמכים").is_dir()
    card = (p / "כרטיס.md").read_text(encoding="utf-8")
    assert "# Seder" in card and "C:/dev/seder" in card and "2026-11-07" in card and "{" not in card
    assert "—" in card  # no studies index yet: relevant lessons placeholder
    with pytest.raises(FileExistsError):
        project.new_project(cfg, "Seder", None, date(2026, 11, 7))


def test_new_project_falls_back_to_06_and_rejects_bad_names(home):
    cfg = config.Config.load(home)
    cfg.tree.append(next(n for n in tree.default_tree("he") if n["id"] == "projects"))
    cfg.save()
    cfg = config.Config.load(home)
    p = project.new_project(cfg, "חתונה 2027", None, date(2026, 11, 7))
    assert p == cfg.root / "06_פרויקטים_ואירועים" / "חתונה 2027" and (p / "כרטיס.md").is_file()
    for bad in ("", "a/b", "x.", "_ארכיון", "con:"):
        with pytest.raises(ValueError):
            project.new_project(cfg, bad, None, date(2026, 11, 7))


def test_new_project_english_template(home_en):
    cfg = config.Config.load(home_en)
    cfg.tree.append(next(a for a in tree.addons("en") if a["id"] == "dev_projects"))
    cfg.save()
    p = project.new_project(config.Config.load(home_en), "Seder", None, date(2026, 11, 7))
    assert (p / "card.md").is_file() and (p / "decisions.md").is_file() and (p / "Documents").is_dir()


def test_list_and_archive_candidates(home):
    cfg = add_dev_branch(home)
    old = project.new_project(cfg, "Old", None, date(2026, 1, 1))
    new = project.new_project(cfg, "New", None, date(2026, 11, 1))
    past = time.time() - 120 * 86400
    for p in old.rglob("*"):
        os.utime(p, (past, past))
    os.utime(old, (past, past))
    listed = {p["name"]: p for p in project.list_projects(cfg)}
    assert set(listed) == {"Old", "New"} and listed["Old"]["card"].endswith("כרטיס.md")
    assert set(listed["Old"]) == {"name", "created", "last_modified", "card", "path"}
    cands = project.archive_candidates(cfg, date(2026, 11, 7))
    assert [c["name"] for c in cands] == ["Old"] and cands[0]["last_modified"] < "2026-09"
    assert project.archive_candidates(cfg, date(2026, 11, 7), days=400) == []


def test_archive_moves_and_is_not_a_candidate_again(home):
    cfg = add_dev_branch(home)
    old = project.new_project(cfg, "Old", None, date(2026, 1, 1))
    past = time.time() - 120 * 86400
    os.utime(old / "כרטיס.md", (past, past))
    dest = project.archive(cfg, "Old")
    assert dest == cfg.root / "07_פרויקטי_פיתוח" / "_ארכיון" / "Old" and (dest / "כרטיס.md").is_file() and not old.exists()
    assert project.archive_candidates(cfg, date(2026, 11, 7)) == [] and [p["name"] for p in project.list_projects(cfg)] == []
    with pytest.raises(FileNotFoundError):
        project.archive(cfg, "Old")


def test_archive_never_overwrites(home):
    cfg = add_dev_branch(home)
    project.new_project(cfg, "Dup", None, date(2026, 1, 1))
    (cfg.root / "07_פרויקטי_פיתוח" / "_ארכיון" / "Dup").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        project.archive(cfg, "Dup")


def test_no_project_branch_is_an_error(home):
    with pytest.raises(ValueError):
        project.new_project(config.Config.load(home), "x", None, date(2026, 11, 7))


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_project_cli(home):
    add_dev_branch(home)
    r = run_cli(home, "project", "new", "Seder", "--code", "C:/dev/seder")
    d = json.loads(r.stdout)
    assert r.returncode == 0 and d["ok"] and d["path"].endswith("Seder") and d["card"].endswith("כרטיס.md")
    d = json.loads(run_cli(home, "project", "list").stdout)
    assert [p["name"] for p in d["projects"]] == ["Seder"]
    d = json.loads(run_cli(home, "project", "archive-candidates", "--days", "0").stdout)
    assert d["ok"] and isinstance(d["candidates"], list)
    r = run_cli(home, "project", "archive", "Seder")
    assert json.loads(r.stdout)["ok"] and (home.parent / "07_פרויקטי_פיתוח" / "_ארכיון" / "Seder").is_dir()
