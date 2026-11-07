import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import make_pdf
from seder import config, doctor, init, names, sensitive

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def _lines(path):
    return path.read_text(encoding="utf-8-sig").splitlines()


def test_create_makes_skeleton_without_tree_dirs(tmp_path):
    root = tmp_path / "root"
    (root / "01_כספים").mkdir(parents=True)  # one branch already exists
    home = root / "00_המוח"
    cfg = init.create(home, root, "he", "דנה", ["דנה", "יוסי"], addons=["dev_projects"])
    for key in ("sensitive", "naming", "profile"):
        assert cfg.path(key).is_file(), key
    assert cfg.path("inbox").is_dir() and (home / "brain.json").is_file()
    for key in ("index", "ledger", "log"):
        assert _lines(cfg.path(key)) == [",".join(names.header(key, "he"))], key
    naming = cfg.path("naming").read_text(encoding="utf-8")
    assert "01_כספים" in naming and "03_משפחה" in naming and "דנה" in naming and "{" not in naming
    profile = cfg.path("profile").read_text(encoding="utf-8")
    assert "דנה" in profile and "יוסי" in profile and "{" not in profile
    assert {p.name for p in root.iterdir()} == {"00_המוח", "01_כספים"}  # nothing else created in the root
    assert [n["num"] for n in cfg.tree] == ["00", "01", "02", "03", "04", "05", "06", "07", "99"]
    assert cfg.tree[0]["physical"] == "00_המוח" and cfg.owner == "דנה" and cfg.entities == ["דנה", "יוסי"]
    assert cfg.root == root and cfg.sources["inbox"] is True
    g = json.loads(cfg.path("sensitive").read_text(encoding="utf-8"))
    assert g["folder_names"]["בריאות"] == "locked" and g["levels"] == {}


def test_create_refuses_existing_instance(tmp_path):
    root = tmp_path / "root"
    init.create(root / "00_המוח", root, "he", "דנה", [])
    with pytest.raises(FileExistsError):
        init.create(root / "00_המוח", root, "he", "דנה", [])


def test_create_rejects_bad_lang(tmp_path):
    with pytest.raises(ValueError):
        init.create(tmp_path / "x", tmp_path, "fr", "a", [])


def test_create_en_names(tmp_path):
    root = tmp_path / "root"
    cfg = init.create(root / "00_Brain", root, "en", "Dana", ["Dana"])
    assert (root / "00_Brain" / "index.csv").is_file() and (root / "00_Brain" / "naming.md").is_file()
    assert (root / "00_Brain" / "about_me.md").is_file() and (root / "00_Brain" / "sensitive.json").is_file()
    assert "01_Finance" in cfg.path("naming").read_text(encoding="utf-8")
    assert _lines(cfg.path("index")) == [",".join(names.KEYS["index"])]


def make_legacy(tmp_path):
    """A pre-Seder archive: numbered folders with their own names, a Hebrew index, no brain.json."""
    root = tmp_path / "Documents"
    for rel in ["01_Acme_Ltd", "02_כספי_הבית/_inbox", "02_כספי_הבית/scripts", "03_בית", "09_אישי/רפואי_דנה", "09_אישי/רכב", "My Music"]:
        (root / rel).mkdir(parents=True)
    make_pdf(root / "01_Acme_Ltd" / "2022-07_חוזה - Acme.pdf", "a")
    make_pdf(root / "02_כספי_הבית" / "2026-01_דף חשבון - דנה.pdf", "b")
    make_pdf(root / "09_אישי" / "רפואי_דנה" / "2026-02_סיכום - דנה.pdf", "c")
    home = root / "00_מוח"
    (home / "_נכנס").mkdir(parents=True)
    with open(home / "אינדקס.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(names.header("index", "he"))
        w.writerow(["01_Acme_Ltd\\2022-07_חוזה - Acme.pdf", "01_Acme_Ltd", "", "2022-07_חוזה - Acme.pdf", "2022-07", "pdf", "1", "", "aaaaaaaaaaaa"])
    with open(home / "יומן_קליטה.csv", "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(names.header("log", "he"))
    (home / "נוהל_שמות.md").write_text("# נוהל קיים\n", encoding="utf-8")
    (home / "מי_אני.md").write_text("# מי אני\n", encoding="utf-8")
    (home / "רגיש.json").write_text(json.dumps({"medical_folders": ["09_אישי/רפואי_דנה"], "secret_folders": [], "secret_patterns": ["**/.env"], "medical_senders": [], "medical_words": []}, ensure_ascii=False), encoding="utf-8")
    return root, home


def test_adopt_legacy_home(tmp_path):
    root, home = make_legacy(tmp_path)
    before = {p.name: p.read_bytes() for p in home.iterdir() if p.is_file()}
    cfg = init.adopt(home, root)
    assert cfg.lang == "he" and cfg.home == home and cfg.root == root
    assert [n["physical"] for n in cfg.tree] == ["00_מוח", "01_Acme_Ltd", "02_כספי_הבית", "03_בית", "09_אישי"]
    fin = next(n for n in cfg.tree if n["physical"] == "02_כספי_הבית")
    assert fin["num"] == "02" and fin["name"] == "כספי_הבית" and fin["handoff"] == {"inbox": "02_כספי_הבית/_inbox", "originals": True}
    assert next(n for n in cfg.tree if n["physical"] == "03_בית")["handoff"] is None
    assert sensitive.level(cfg, "09_אישי/רפואי_דנה/x.pdf") == "ask"
    assert sensitive.level(cfg, "09_אישי/רכב/x.pdf") == "open"
    for name, data in before.items():  # nothing that existed was touched
        assert (home / name).read_bytes() == data, name
    proposed = (home / "עץ_מוצע.md").read_text(encoding="utf-8")
    assert "02_כספי_הבית" in proposed and "01 כספים" in proposed and "05 עסקים" in proposed and "03 משפחה" in proposed
    assert "| 02_כספי_הבית |" in proposed and "| 1 |" in proposed  # file count per folder


def test_adopt_marks_medical_named_folders_not_yet_covered(tmp_path):
    root, home = make_legacy(tmp_path)
    (home / "רגיש.json").write_text("{}", encoding="utf-8")  # nothing listed yet
    cfg = init.adopt(home, root)
    g = json.loads((home / "רגיש.json").read_text(encoding="utf-8"))
    assert g["levels"] == {"09_אישי/רפואי_דנה": "locked"}
    assert sensitive.level(cfg, "09_אישי/רפואי_דנה/x.pdf") == "locked"


def test_adopt_with_addons_appends_new_branches(tmp_path):
    root, home = make_legacy(tmp_path)
    cfg = init.adopt(home, root, addons=["dev_projects", "studies"])
    assert [n["physical"] for n in cfg.tree][-2:] == ["07_פרויקטי_פיתוח", "08_לימודים"]
    assert next(n for n in cfg.tree if n["id"] == "studies")["num"] == "08"
    assert not (root / "08_לימודים").exists()  # registered, not created
    with pytest.raises(ValueError):
        init.adopt(tmp_path / "other", root, addons=["nope"])


def test_adopt_refuses_when_instance_exists(home):
    with pytest.raises(FileExistsError):
        init.adopt(home, home.parent)


def test_adopt_detects_english(tmp_path):
    root = tmp_path / "Docs"
    home = root / "00_Brain"
    (home / "_inbox").mkdir(parents=True)
    (root / "01_Money").mkdir()
    with open(home / "index.csv", "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(names.KEYS["index"])
    cfg = init.adopt(home, root)
    assert cfg.lang == "en" and cfg.tree[1]["physical"] == "01_Money" and (home / "proposed_tree.md").is_file()


def test_scan_counts_names_only(home):
    cfg = config.Config.load(home)
    make_pdf(cfg.root / "01_כספים" / "בנק" / "a.pdf", "a")
    make_pdf(cfg.root / "01_כספים" / "b.pdf", "b")
    make_pdf(cfg.root / "03_משפחה" / "דנה" / "בריאות" / "c.pdf", "c")
    s = init.scan(cfg)
    by = {f["path"]: f for f in s["folders"]}
    assert s["total"] == 3 and by["01_כספים"]["files"] == 1 and by["01_כספים/בנק"]["files"] == 1
    assert by["03_משפחה/דנה"]["files"] == 0 and "03_משפחה/דנה/בריאות" not in by  # depth 2 only
    assert by["01_כספים"]["sensitive"] is False
    assert all(set(f) == {"path", "files", "sensitive"} for f in s["folders"])


def test_doctor_json_shape():
    checks = doctor.checks()
    assert all(set(c) == {"id", "ok", "detail", "required", "fix"} for c in checks)
    ids = [c["id"] for c in checks]
    assert {"python", "pymupdf", "pillow", "openpyxl", "claude_cli", "git", "tailscale", "syncthing", "remote_control"} <= set(ids)
    assert next(c for c in checks if c["id"] == "python")["ok"] is True
    assert next(c for c in checks if c["id"] == "tailscale")["required"] is False


def run_cli(*args, home=None):
    env = {**os.environ}
    env.pop("SEDER_HOME", None)
    if home:
        env["SEDER_HOME"] = str(home)
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_cli_init_scan_doctor(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    home = root / "00_המוח"
    r = run_cli("init", "--home", str(home), "--root", str(root), "--lang", "he", "--owner", "דנה", "--entities", "דנה,יוסי", "--addons", "dev_projects,studies")
    d = json.loads(r.stdout)
    assert r.returncode == 0 and d["ok"] and d["home"] == str(home) and d["tree"][-2]["num"] == "08"
    r = run_cli("scan", home=home)
    assert json.loads(r.stdout) == {"ok": True, "folders": [], "total": 0}
    r = run_cli("doctor")
    d = json.loads(r.stdout)
    assert d["ok"] and isinstance(d["checks"], list) and "home" in d
    r = run_cli("adopt", "--home", str(home), "--root", str(root))
    assert r.returncode == 1 and json.loads(r.stdout)["ok"] is False
