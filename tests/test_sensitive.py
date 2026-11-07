import json
import os
import subprocess
import sys
from pathlib import Path

from seder import config, sensitive

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def test_sensitive_by_folder_name_and_lock(home):
    cfg = config.Config.load(home)
    assert sensitive.is_sensitive(cfg, "03_משפחה/דנה/בריאות/2026-01_סיכום.pdf")
    assert not sensitive.is_sensitive(cfg, "01_כספים/בנק/2026-01_דף.pdf")
    assert sensitive.is_sensitive(cfg, str(home.parent / "03_משפחה" / "דנה" / "בריאות" / "x.pdf"))  # absolute inside root
    assert sensitive.is_sensitive(cfg, "03_משפחה\\דנה\\בריאות\\x.pdf")  # backslashes


def test_secret_patterns():
    assert sensitive.is_secret(".env") and sensitive.is_secret("id_rsa") and sensitive.is_secret("סיסמאות.txt")
    assert sensitive.is_secret("C:/x/.env.local") and sensitive.is_secret("my-TOKEN.json")
    assert not sensitive.is_secret("2026-01_תלוש - דנה.pdf")


def test_looks_medical(home):
    cfg = config.Config.load(home)
    assert sensitive.looks_medical(cfg, "noreply@clalit.co.il", ["x.pdf"], "")
    assert sensitive.looks_medical(cfg, "a@b.com", ["סיכום מיון.pdf"], "")
    assert sensitive.looks_medical(cfg, "a@b.com", ["x.pdf"], "בדיקות דם ... רנטגן")
    assert not sensitive.looks_medical(cfg, "a@b.com", ["x.pdf"], "בדיקות דם")


def test_deny_rules_shape(home):
    cfg = config.Config.load(home)
    rules = sensitive.deny_rules(cfg)
    assert any(r.startswith("Read(//") and r.endswith("/בריאות/**)") for r in rules)
    assert "Read(**/.env)" in rules
    allow = sensitive.allow_rules(cfg)
    assert len(allow) == 1 and allow[0].startswith("Read(//") and allow[0].endswith("/root/**)")


def test_write_headless_settings(home, tmp_path):
    out = sensitive.write_headless_settings(config.Config.load(home), tmp_path / "s.json")
    d = json.loads(out.read_text(encoding="utf-8"))
    assert set(d["permissions"]) == {"allow", "deny"} and "Read(**/.env)" in d["permissions"]["deny"]


def test_level_set_and_default(home):
    cfg = config.Config.load(home)
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/a.pdf") == "locked"   # health is locked by default
    sensitive.set_level(cfg, "03_משפחה/דנה/בריאות", "ask")
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/a.pdf") == "ask"
    sensitive.set_level(cfg, "03_משפחה/דנה/בריאות", "open")
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/a.pdf") == "locked"   # default by folder name returns
    assert sensitive.level(cfg, "01_כספים/בנק/a.pdf") == "open"


def test_explicit_ask_relaxes_the_health_lock(home):
    cfg = config.Config.load(home)
    sensitive.set_level(cfg, "03_משפחה/דנה/בריאות", "ask")
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/a.pdf") == "ask"
    assert sensitive.level(cfg, "03_משפחה/יוסי/בריאות/a.pdf") == "locked"   # only that folder


def test_deeper_name_default_beats_a_shallower_explicit_level(home):
    cfg = config.Config.load(home)
    sensitive.set_level(cfg, "03_משפחה", "ask")
    assert sensitive.level(cfg, "03_משפחה/דנה/a.pdf") == "ask"
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/a.pdf") == "locked"


def test_branch_privacy_in_tree(home):
    cfg = config.Config.load(home)
    cfg.tree[2]["privacy"] = "ask"
    cfg.save()
    assert sensitive.level(config.Config.load(home), "02_בית/x.pdf") == "ask"


def test_live_format_is_read(home):
    (home / "רגיש.json").write_text(json.dumps({"medical_folders": ["01_כספים/בנק"], "secret_folders": ["02_בית"]}, ensure_ascii=False), encoding="utf-8")
    cfg = config.Config.load(home)
    assert sensitive.level(cfg, "01_כספים/בנק/x.pdf") == "ask" and sensitive.level(cfg, "02_בית/x.pdf") == "locked"
    assert sensitive.level(cfg, "03_משפחה/דנה/בריאות/x.pdf") == "locked"   # defaults still apply


def test_template_name(home, tmp_path):
    cfg = config.Config.load(home)
    cfg.owner = "דנה"
    f = tmp_path / "x.pdf"
    f.write_bytes(b"x")
    assert sensitive.template_name(cfg, f, text="ביקור ב-03.09.2026") == "2026-09_רפואי - דנה.pdf"
    assert sensitive.template_name(cfg, f, text="period 2025-11 to 2026-01") == "2025-11_רפואי - דנה.pdf"
    assert sensitive.template_name(cfg, f, whose="יוסי", text="").endswith("_רפואי - יוסי.pdf")


def test_template_name_en(home_en, tmp_path):
    cfg = config.Config.load(home_en)
    cfg.owner = "Dana"
    f = tmp_path / "x.jpg"
    f.write_bytes(b"x")
    assert sensitive.template_name(cfg, f, text="2026-02") == "2026-02_Medical - Dana.pdf"


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_privacy_cli(home):
    r = run_cli(home, "privacy", "set", "01_כספים/בנק", "locked")
    assert r.returncode == 0 and json.loads(r.stdout)["levels"] == {"01_כספים/בנק": "locked"}
    r = run_cli(home, "privacy", "list")
    d = json.loads(r.stdout)
    assert d["ok"] and d["levels"]["01_כספים/בנק"] == "locked" and d["folder_names"]["בריאות"] == "locked"
    r = run_cli(home, "privacy", "set", "01_כספים/בנק", "secret")
    assert r.returncode == 1 and json.loads(r.stdout)["ok"] is False
