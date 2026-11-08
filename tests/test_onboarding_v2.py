"""Onboarding v2: the names-only discovery scan, the tailored tree, and the archive's own name."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from seder import config, discover, init, tree

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def run_cli(*args):
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1, r.stdout + r.stderr
    return json.loads(lines[0])


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


@pytest.fixture
def docs(tmp_path):
    """A fake person's folders: motorcycle papers, payslips, a medical letter, code and noise."""
    d = tmp_path / "Documents"
    for i in range(4):
        touch(d / "אופנוע ימאהה" / f"ביטוח אופנוע {i}.pdf")
    for i in range(3):
        touch(d / "עבודה" / f"תלוש משכורת {i}.pdf")
    for i in range(3):
        touch(d / "שונות" / f"סיכום רופא {i}.pdf")
    touch(d / "שונות" / "photo.mp4")  # not a document
    touch(d / "dev" / "node_modules" / "pkg" / "invoice.pdf")  # skipped folder
    touch(d / "dev" / "README.pdf")
    dl = tmp_path / "Downloads"
    for i in range(3):
        touch(dl / f"Motorcycle registration {i}.pdf")
    return [d, dl]


def test_discover_counts_documents_and_topics_by_name_only(docs):
    out = discover.discover(docs, lang="he")
    assert out["total_documents"] == 4 + 3 + 3 + 1 + 3  # mp4 and node_modules left out
    topics = {t["id"]: t for t in out["topics"]}
    assert topics["motorcycles"]["documents"] == 7  # Hebrew substring + Latin token
    assert topics["motorcycles"]["where"][0] == "אופנוע ימאהה"
    assert topics["payslips"]["documents"] == 3
    assert out["suggested_plan"]["rename"]["vehicles"] == "רכב ואופנועים"
    assert "ציוד ואביזרים" in out["suggested_plan"]["subfolders_add"]["vehicles"]


def test_discover_never_names_files_and_hides_medical_places(docs):
    out = discover.discover(docs, lang="he")
    text = json.dumps(out, ensure_ascii=False)
    for fname in ("סיכום רופא", "תלוש משכורת 0", "ביטוח אופנוע 0", "README"):
        assert fname not in text, fname
    medical = next(t for t in out["topics"] if t["id"] == "medical")
    assert medical["documents"] == 3 and "where" not in medical


def test_discover_latin_words_match_whole_tokens_only(tmp_path):
    d = tmp_path / "D"
    for i in range(5):
        touch(d / f"remote {i}.pdf")  # contains "moto" inside a word: no match
    out = discover.discover([d])
    assert "motorcycles" not in {t["id"] for t in out["topics"]}


def test_discover_reports_existing_archive_without_counting_its_system_folder(tmp_path):
    root = tmp_path / "Documents"
    for n in ("01_a", "02_b", "03_c"):
        (root / n).mkdir(parents=True)
    touch(root / "00_brain" / "brain.json")
    touch(root / "00_brain" / "_inbox" / "x.pdf")
    touch(root / "01_a" / "y.pdf")
    out = discover.discover([root])
    assert out["organized_archives"] == [str(root)]
    assert out["existing_instances"] == [str(root / "00_brain")]
    assert out["total_documents"] == 1


def test_discover_writes_nothing(docs):
    before = sorted(p for d in docs for p in d.rglob("*"))
    discover.discover(docs)
    assert sorted(p for d in docs for p in d.rglob("*")) == before


def test_build_applies_a_plan():
    b = tree.build("he", ["pets"], {
        "rename": {"vehicles": "רכב ואופנועים"},
        "subfolders_add": {"vehicles": ["ציוד ואביזרים", "ביטוח"]},
        "items": {"vehicles": ["ימאהה MT-07"]},
        "drop": ["business"],
        "extra": [{"name": "ספורט", "subfolders": ["מנויים"]}],
    })
    by = {n["id"]: n for n in b}
    assert by["vehicles"]["physical"] == "04_רכב_ואופנועים"
    assert by["vehicles"]["subfolders"].count("ביטוח") == 1 and "ציוד ואביזרים" in by["vehicles"]["subfolders"]
    assert by["vehicles"]["items"] == ["ימאהה MT-07"]
    assert "business" not in by and "pets" in by
    extra = next(n for n in b if n["name"] == "ספורט")
    assert extra["custom"] and extra["num"] not in {n["num"] for n in tree.addons("he")}
    assert [n["num"] for n in b] == sorted(n["num"] for n in b)
    assert tree.default_tree("he")[4]["name"] == "רכב"  # the asset is untouched


@pytest.mark.parametrize("plan", [
    {"drop": ["brain"]}, {"drop": ["archive"]}, {"rename": {"nope": "x"}}, {"rename": {"vehicles": "a/b"}},
    {"items": {"finance": ["x"]}}, {"bogus": 1}, {"addons": ["nope"]}, {"extra": [{"name": "bad."}]},
])
def test_build_rejects_bad_plans(plan):
    with pytest.raises(ValueError):
        tree.build("he", [], plan)


def test_create_with_name_and_plan(tmp_path):
    root = tmp_path / "root"
    cfg = init.create(root / "00_הארון", root, "he", "דנה", ["דנה"], plan={"rename": {"vehicles": "רכב ואופנועים"}},
                      name="הארון של דנה")
    data = json.loads((cfg.home / "brain.json").read_text(encoding="utf-8"))
    assert data["name"] == "הארון של דנה"
    assert data["tree"][0]["name"] == "הארון של דנה" and data["tree"][0]["physical"] == "00_הארון"
    assert any(n["physical"] == "04_רכב_ואופנועים" for n in data["tree"])
    assert not (root / "04_רכב_ואופנועים").exists()  # folders appear with the first document


def test_create_default_name(tmp_path):
    cfg = init.create(tmp_path / "r" / "00_Brain", tmp_path / "r", "en", "Dana", [])
    assert cfg.data["name"] == "Seder"


def test_rename_display_only(home):
    cfg = config.Config.load(home)
    out = init.rename(cfg, "הארון")
    assert out["moved"] is False and home.is_dir()
    assert config.Config.load(home).data["name"] == "הארון"


def test_rename_moves_folder_and_pointer(home, tmp_path, monkeypatch):
    ptr = tmp_path / "ptr" / "home"
    ptr.parent.mkdir()
    ptr.write_text(str(home) + "\n", encoding="utf-8")
    monkeypatch.setattr(config, "HOME_POINTER", ptr)
    cfg = config.Config.load(home)
    out = init.rename(cfg, "הארון של דנה", move_folder=True)
    new_home = home.parent / "00_הארון_של_דנה"
    assert out["moved"] and out["pointer_updated"] and not home.exists() and new_home.is_dir()
    assert ptr.read_text(encoding="utf-8").strip() == str(new_home)
    cfg2 = config.Config.load(new_home)
    assert cfg2.tree[0]["physical"] == "00_הארון_של_דנה" and cfg2.data["name"] == "הארון של דנה"


def test_rename_refuses_existing_folder(home):
    (home.parent / "00_תפוס").mkdir()
    with pytest.raises(FileExistsError):
        init.rename(config.Config.load(home), "תפוס", move_folder=True)
    assert home.is_dir()


def test_cli_discover_preview_init_rename(docs, tmp_path):
    d = run_cli("discover", "--roots", *docs)
    assert d["ok"] and d["total_documents"] == 14
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(d["suggested_plan"], ensure_ascii=False), encoding="utf-8")
    p = run_cli("tree-preview", "--plan", plan)
    assert any(n["physical"] == "04_רכב_ואופנועים" for n in p["tree"])
    root = tmp_path / "archive"
    i = run_cli("init", "--home", root / "00_סדר", "--root", root, "--owner", "דנה", "--plan", plan, "--name", "סדר")
    assert i["ok"] and i["name"] == "סדר"
    r = run_cli("--home", root / "00_סדר", "rename", "הארון")
    assert r["ok"] and r["name"] == "הארון" and r["moved"] is False


def test_cli_bad_plan_file_is_one_json_error(tmp_path):
    bad = tmp_path / "plan.json"
    bad.write_text("[1, 2]", encoding="utf-8")
    out = run_cli("tree-preview", "--plan", bad)
    assert out["ok"] is False and "plan" in out["error"]
