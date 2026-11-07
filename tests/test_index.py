import csv

from helpers import make_pdf
from seder import config, index, names


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def test_rebuild_marks_sensitive_and_roundtrips_hebrew(home):
    cfg = config.Config.load(home)
    make_pdf(cfg.root / "01_כספים" / "בנק" / "2026-01_דף חשבון - דנה.pdf", "a")
    make_pdf(cfg.root / "03_משפחה" / "דנה" / "בריאות" / "2026-02_סיכום - דנה.pdf", "b")
    (cfg.root / "01_כספים" / "desktop.ini").write_text("x")
    (cfg.root / "_junk").mkdir()
    make_pdf(cfg.root / "_junk" / "x.pdf", "c")
    n = index.rebuild(cfg)
    assert n == 2
    raw = (home / "אינדקס.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM, like the live file
    table = _read(home / "אינדקס.csv")
    assert table[0] == names.header("index", "he")
    rows = index.rows(cfg)
    bank = next(r for r in rows if r["name"] == "2026-01_דף חשבון - דנה.pdf")
    health = next(r for r in rows if r["name"] == "2026-02_סיכום - דנה.pdf")
    assert bank["date"] == "2026-01" and bank["ext"] == "pdf" and bank["sensitive"] == "" and len(bank["sha12"]) == 12
    assert bank["topic"] == "01_כספים" and bank["subfolder"] == "בנק" and bank["path"] == "01_כספים\\בנק\\2026-01_דף חשבון - דנה.pdf"
    assert health["sensitive"] == "רפואי" and health["subfolder"] == "דנה\\בריאות"


def test_update_row_replaces_not_duplicates(home):
    cfg = config.Config.load(home)
    p = make_pdf(cfg.root / "01_כספים" / "בנק" / "x.pdf", "a")
    index.rebuild(cfg)
    make_pdf(p, "changed content")
    index.update_row(cfg, "01_כספים/בנק/x.pdf")
    rows = index.rows(cfg)
    assert len(rows) == 1 and rows[0]["sha12"] == index.sha12(p)
    make_pdf(cfg.root / "02_בית" / "y.pdf", "b")
    index.update_row(cfg, "02_בית\\y.pdf")
    assert [r["name"] for r in index.rows(cfg)] == ["x.pdf", "y.pdf"]
    assert _read(home / "אינדקס.csv")[0] == names.header("index", "he")


def test_rows_empty_without_file(home):
    assert index.rows(config.Config.load(home)) == []


def test_find_by_sha(home):
    cfg = config.Config.load(home)
    p = make_pdf(cfg.root / "01_כספים" / "בנק" / "x.pdf", "same")
    index.rebuild(cfg)
    assert index.find_by_sha(cfg, index.sha12(p)) == ["01_כספים\\בנק\\x.pdf"]
    assert index.find_by_sha(cfg, "000000000000") == []


def test_english_instance_uses_english_header(home_en):
    cfg = config.Config.load(home_en)
    make_pdf(cfg.root / "01_Finance" / "Bank" / "2026-01_statement - Dana.pdf", "a")
    index.rebuild(cfg)
    assert _read(home_en / "index.csv")[0] == names.KEYS["index"]
    assert index.rows(cfg)[0]["sensitive"] == ""
