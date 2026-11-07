import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from helpers import make_pdf
from seder import config, filing, index, names

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


@pytest.mark.parametrize("bad", ["a:b.pdf", "x.", "x ", ".hidden.pdf", "a/b.pdf", "a" * 200 + ".pdf", "", "a\tb.pdf"])
def test_clean_name_rejects(bad):
    with pytest.raises(ValueError):
        filing.clean_name(bad)


def test_clean_name_adds_ext_and_keeps_case():
    assert filing.clean_name("2026-01_חשבון - דנה", ".pdf") == "2026-01_חשבון - דנה.pdf"
    assert filing.clean_name("x.PDF", ".pdf") == "x.PDF"
    with pytest.raises(ValueError):
        filing.clean_name(" x.pdf")   # stray spaces are an error, not silently trimmed
    with pytest.raises(ValueError):
        filing.clean_name("x .pdf")


def test_free_name(tmp_path):
    (tmp_path / "x.pdf").write_bytes(b"1")
    (tmp_path / "x (2).pdf").write_bytes(b"1")
    assert filing.free_name(tmp_path, "x.pdf") == "x (3).pdf"
    assert filing.free_name(tmp_path, "y.pdf") == "y.pdf"


def test_file_doc_moves_logs_indexes(home):
    cfg = config.Config.load(home)
    src = make_pdf(home / "_נכנס" / "01.pdf", "hello")
    r = filing.file_doc(cfg, src, "01_כספים/בנק", "2026-01_דף חשבון - דנה.pdf", "test")
    dest = cfg.root / "01_כספים" / "בנק" / "2026-01_דף חשבון - דנה.pdf"
    assert dest.exists() and not src.exists() and r["dest"] == str(dest) and r["handoff"] is False
    log = (home / "יומן_קליטה.csv").read_text(encoding="utf-8-sig").splitlines()
    assert log[0] == ",".join(names.header("log", "he")) and "Move-Item" in log[1] and ",כן," in log[1]
    assert r["undo"].startswith("Move-Item -LiteralPath") and str(dest) in r["undo"] and str(src) in r["undo"]
    assert any(row["name"] == "2026-01_דף חשבון - דנה.pdf" and row["sha12"] == r["sha12"] for row in index.rows(cfg))


def test_file_doc_never_overwrites(home):
    cfg = config.Config.load(home)
    make_pdf(cfg.root / "01_כספים" / "בנק" / "x.pdf", "a")
    src = make_pdf(home / "_נכנס" / "02.pdf", "b")
    with pytest.raises(FileExistsError):
        filing.file_doc(cfg, src, "01_כספים/בנק", "x.pdf", "t")
    assert src.exists()


def test_mkdir_requires_flag_and_parent(home):
    cfg = config.Config.load(home)
    src = make_pdf(home / "_נכנס" / "03.pdf", "c")
    with pytest.raises(ValueError):
        filing.file_doc(cfg, src, "01_כספים/חדש", "x.pdf", "t")
    with pytest.raises(ValueError):
        filing.file_doc(cfg, src, "01_כספים/a/b", "x.pdf", "t", mkdir=True)
    filing.file_doc(cfg, src, "01_כספים/חדש", "x.pdf", "t", mkdir=True)
    assert (cfg.root / "01_כספים" / "חדש" / "x.pdf").exists()


def test_file_doc_rejects_brain_folder_and_bad_name(home):
    cfg = config.Config.load(home)
    src = make_pdf(home / "_נכנס" / "05.pdf", "c")
    with pytest.raises(ValueError):
        filing.file_doc(cfg, src, "00_המוח/x", "x.pdf", "t")
    with pytest.raises(ValueError):
        filing.file_doc(cfg, src, "01_כספים/בנק", "x .pdf", "t")
    assert src.exists()


def test_handoff_files_original_not_pdf(home):
    cfg = config.Config.load(home)
    cfg.tree[1]["handoff"] = {"inbox": "01_כספים/_inbox", "originals": True}
    cfg.save()
    cfg = config.Config.load(home)
    (cfg.root / "01_כספים" / "_inbox").mkdir()
    pdf = make_pdf(home / "_נכנס" / "04.pdf", "x")
    xlsx = home / "_נכנס" / "04.orig.xlsx"
    xlsx.write_bytes(b"PK\x03\x04fake")
    r = filing.file_doc(cfg, pdf, "01_כספים/בנק", "2026-09_כרטיס - דנה.pdf", "t", original=xlsx)
    target = cfg.root / "01_כספים" / "_inbox" / "2026-09_כרטיס - דנה.xlsx"
    assert r["handoff"] is True and target.exists() and pdf.exists() and not xlsx.exists()
    assert r["dest"] == str(target)


def test_handoff_without_original_moves_pdf_to_inbox(home):
    cfg = config.Config.load(home)
    cfg.tree[1]["handoff"] = {"inbox": "01_כספים/_inbox", "originals": True}
    cfg.save()
    cfg = config.Config.load(home)
    (cfg.root / "01_כספים" / "_inbox").mkdir()
    pdf = make_pdf(home / "_נכנס" / "06.pdf", "x")
    r = filing.file_doc(cfg, pdf, "01_כספים/בנק", "2026-09_דף - דנה.pdf", "t")
    assert r["handoff"] is True and (cfg.root / "01_כספים" / "_inbox" / "2026-09_דף - דנה.pdf").exists()


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_cli_file_and_namecheck(home):
    cfg = config.Config.load(home)
    src = make_pdf(home / "_נכנס" / "07.pdf", "cli")
    r = run_cli(home, "namecheck", "01_כספים/בנק", "2026-03_דף - דנה.pdf", "--src", str(src))
    assert json.loads(r.stdout) == {"ok": True, "exists": False, "same": None, "free": "2026-03_דף - דנה.pdf"}
    r = run_cli(home, "file", str(src), "01_כספים/בנק", "2026-03_דף - דנה.pdf", "--why", "cli test")
    d = json.loads(r.stdout)
    assert r.returncode == 0 and d["ok"] and d["dest"].endswith("2026-03_דף - דנה.pdf")
    src2 = home / "_נכנס" / "08.pdf"
    src2.write_bytes(Path(d["dest"]).read_bytes())  # byte-identical to the filed one
    r = run_cli(home, "namecheck", "01_כספים/בנק", "2026-03_דף - דנה.pdf", "--src", str(src2))
    d = json.loads(r.stdout)
    assert d["exists"] is True and d["same"] is True and d["free"] == "2026-03_דף - דנה (2).pdf"
    r = run_cli(home, "index", "--rebuild")
    assert json.loads(r.stdout)["ok"] and json.loads(r.stdout)["rows"] == 1
    r = run_cli(home, "file", str(src2), "01_כספים/בנק", "2026-03_דף - דנה.pdf", "--why", "dup")
    assert r.returncode == 1 and json.loads(r.stdout)["ok"] is False and src2.exists()
