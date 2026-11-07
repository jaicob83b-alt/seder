import json

from seder import config, names


def test_hebrew_headers_match_live_files():
    assert names.header("index", "he") == ["נתיב", "נושא", "תת_תיקייה", "שם", "תאריך", "סוג_קובץ", "KB", "רגיש", "sha12"]
    assert names.header("log", "he") == ["תאריך", "שם_מקורי", "שם_חדש", "תיקייה", "למה", "אישור", "sha12", "ביטול"]
    assert names.FILES["he"]["index"] == "אינדקס.csv" and names.FILES["en"]["index"] == "index.csv"


def test_english_headers_are_the_internal_keys():
    assert names.header("ledger", "en") == names.KEYS["ledger"]
    assert names.FILES["en"]["inbox"] == "_inbox" and names.FILES["he"]["inbox"] == "_נכנס"


def test_row_roundtrip():
    rec = dict(zip(names.KEYS["ledger"], ["a/b.pdf", "חשבון", "חברת החשמל", "דנה", "2026-09", "412.30", "ILS", "", "", "חודשי", "", "name"]))
    row = dict(zip(names.header("ledger", "he"), names.to_row("ledger", "he", rec)))
    assert names.from_row("ledger", "he", row) == rec


def test_load_save_and_paths(home):
    cfg = config.Config.load(home)
    assert cfg.lang == "he" and cfg.path("index").name == "אינדקס.csv" and cfg.path("inbox").name == "_נכנס"
    assert cfg.root == home.parent and cfg.tree[1]["physical"] == "01_כספים"
    cfg.owner = "דנה"
    cfg.save()
    assert json.loads((home / "brain.json").read_text(encoding="utf-8"))["owner"] == "דנה"
    assert cfg.t("no_home").startswith("לא נמצאה")


def test_english_instance(home_en):
    cfg = config.Config.load(home_en)
    assert cfg.lang == "en" and cfg.path("index").name == "index.csv" and cfg.path("log").name == "intake_log.csv"
    assert cfg.t("no_home").startswith("No archive")


def test_find_home_order(home, tmp_path, monkeypatch):
    monkeypatch.delenv("SEDER_HOME", raising=False)
    monkeypatch.setattr(config, "HOME_POINTER", tmp_path / "nowhere" / "home")
    assert config.find_home(cwd=home.parent) == home           # child of cwd
    assert config.find_home(cwd=home / "_נכנס") == home         # parent of cwd
    assert config.find_home(cwd=tmp_path) is None               # nothing around
    env_home = tmp_path / "env_home"
    env_home.mkdir()
    (env_home / "brain.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SEDER_HOME", str(env_home))
    assert config.find_home(cwd=home) == env_home               # env wins over search
    assert config.find_home(explicit=home, cwd=env_home) == home  # explicit wins over env


def test_find_home_pointer_file(home, tmp_path, monkeypatch):
    monkeypatch.delenv("SEDER_HOME", raising=False)
    pointer = tmp_path / ".seder" / "home"
    pointer.parent.mkdir()
    pointer.write_text(str(home) + "\n", encoding="utf-8")
    monkeypatch.setattr(config, "HOME_POINTER", pointer)
    assert config.find_home(cwd=tmp_path) == home
