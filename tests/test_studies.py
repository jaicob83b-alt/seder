import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from seder import config, studies, tree

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"
RENAME = {"שיעור 4": "04 - דוח בוקר וסוכן מחקר ב-n8n", "שיעור 8 - RAG SYSTEM": "08 - RAG, סוכן ידע עסקי"}


def make_course(tmp_path):
    src = tmp_path / "course_src"
    (src / "שיעור 4").mkdir(parents=True)
    (src / "שיעור 4" / "README.md").write_text("# דוח בוקר וסוכן מחקר ב-n8n\n\nטקסט.\n", encoding="utf-8")
    (src / "שיעור 4" / "notes.txt").write_text("x", encoding="utf-8")
    (src / "שיעור 5").mkdir()
    (src / "שיעור 5" / "slides.pdf").write_bytes(b"%PDF-1.4 fake")
    (src / "שיעור 8 - RAG SYSTEM" / "docs").mkdir(parents=True)
    (src / "שיעור 8 - RAG SYSTEM" / "README.md").write_text("intro line\n# RAG: סוכן ידע עסקי\n", encoding="utf-8")
    (src / "שיעור 8 - RAG SYSTEM" / "docs" / "deep.md").write_text("# nested\n", encoding="utf-8")
    (src / "syllabus.pdf").write_bytes(b"%PDF-1.4 syllabus")
    return src


def with_studies(home):
    cfg = config.Config.load(home)
    cfg.tree.append(next(a for a in tree.addons(cfg.lang) if a["id"] == "studies"))
    cfg.save()
    return config.Config.load(home)


def test_import_dry_run_lists_without_writing(home, tmp_path):
    cfg = with_studies(home)
    src = make_course(tmp_path)
    plan = studies.import_course(cfg, src, "AI Dev", RENAME, dry_run=True)
    by = {Path(p["from"]).name: p for p in plan}
    base = cfg.root / "08_לימודים" / "AI Dev"
    assert set(by) == {"שיעור 4", "שיעור 5", "שיעור 8 - RAG SYSTEM", "syllabus.pdf"}
    assert Path(by["שיעור 4"]["to"]) == base / "04 - דוח בוקר וסוכן מחקר ב-n8n" and by["שיעור 4"]["files"] == 2
    assert Path(by["שיעור 5"]["to"]) == base / "שיעור 5"  # not in the map: name kept
    assert Path(by["syllabus.pdf"]["to"]) == base / "syllabus.pdf" and by["syllabus.pdf"]["files"] == 1
    assert by["שיעור 8 - RAG SYSTEM"]["files"] == 2 and by["שיעור 8 - RAG SYSTEM"]["bytes"] > 0
    assert not (cfg.root / "08_לימודים").exists()


def test_import_copies_and_keeps_source(home, tmp_path):
    cfg = with_studies(home)
    src = make_course(tmp_path)
    done = studies.import_course(cfg, src, "AI Dev", RENAME, dry_run=False)
    base = cfg.root / "08_לימודים" / "AI Dev"
    assert len(done) == 4 and (base / "04 - דוח בוקר וסוכן מחקר ב-n8n" / "README.md").is_file()
    assert (base / "08 - RAG, סוכן ידע עסקי" / "docs" / "deep.md").is_file() and (base / "syllabus.pdf").is_file()
    assert (src / "שיעור 4" / "README.md").is_file()  # a copy, never a move
    with pytest.raises(FileExistsError):
        studies.import_course(cfg, src, "AI Dev", RENAME, dry_run=False)


def test_import_checks_all_targets_before_copying(home, tmp_path):
    cfg = with_studies(home)
    src = make_course(tmp_path)
    (cfg.root / "08_לימודים" / "AI Dev" / "שיעור 5").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        studies.import_course(cfg, src, "AI Dev", RENAME, dry_run=False)
    assert not (cfg.root / "08_לימודים" / "AI Dev" / "04 - דוח בוקר וסוכן מחקר ב-n8n").exists()


def test_import_needs_studies_branch(home, tmp_path):
    with pytest.raises(ValueError):
        studies.import_course(config.Config.load(home), make_course(tmp_path), "AI Dev", {}, dry_run=True)


def test_build_index_and_relevant(home, tmp_path):
    cfg = with_studies(home)
    studies.import_course(cfg, make_course(tmp_path), "AI Dev", RENAME, dry_run=False)
    out = studies.build_index(cfg)
    assert out == cfg.path("studies_index") and out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "04 - דוח בוקר וסוכן מחקר ב-n8n" in text and "דוח בוקר וסוכן מחקר ב-n8n" in text
    assert "RAG: סוכן ידע עסקי" in text and "שיעור 5" in text
    found = studies.relevant(cfg, "סוכן מחקר ב-n8n שמכין דוח בוקר")
    assert found[0]["lesson"] == "04 - דוח בוקר וסוכן מחקר ב-n8n" and found[0]["course"] == "AI Dev" and found[0]["score"] >= 3
    assert found[0]["label"].startswith("AI Dev / 04 - ")
    assert studies.relevant(cfg, "xyzzy") == []
    assert [f["lesson"] for f in studies.relevant(cfg, "סוכן")] == ["04 - דוח בוקר וסוכן מחקר ב-n8n", "08 - RAG, סוכן ידע עסקי"]


def test_relevant_without_index_returns_empty(home):
    assert studies.relevant(with_studies(home), "סוכן") == []


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_studies_cli(home, tmp_path):
    with_studies(home)
    src = make_course(tmp_path)
    rename = tmp_path / "names.json"
    rename.write_text(json.dumps(RENAME, ensure_ascii=False), encoding="utf-8")
    d = json.loads(run_cli(home, "studies", "import", "--src", str(src), "--course", "AI Dev", "--rename", str(rename)).stdout)
    assert d["ok"] and d["dry_run"] is True and len(d["plan"]) == 4 and not (home.parent / "08_לימודים").exists()
    d = json.loads(run_cli(home, "studies", "import", "--src", str(src), "--course", "AI Dev", "--rename", str(rename), "--go").stdout)
    assert d["ok"] and d["dry_run"] is False and (home.parent / "08_לימודים" / "AI Dev" / "syllabus.pdf").is_file()
    d = json.loads(run_cli(home, "studies", "index").stdout)
    assert d["ok"] and d["lessons"] == 3 and Path(d["file"]).is_file()
    d = json.loads(run_cli(home, "studies", "relevant", "RAG").stdout)
    assert d["ok"] and d["lessons"][0]["lesson"].startswith("08 - RAG")
