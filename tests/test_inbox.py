import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import make_image, make_pdf
from seder import config, inbox, index, ledger, pdf, sensitive

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def doc(**kw):
    base = {"pages": [], "rotate": [], "name": "", "folder": "", "new_folder": False, "entity": "", "summary": "",
            "readable": True, "duplicate": "", "sensitive": "open", "confidence": "high", "why": "", "skip": "",
            "ledger": {"type": "", "counterparty": "", "whose": "", "period": "", "amount": "", "currency": "",
                       "due": "", "action": "", "recurring": ""}}
    base.update(kw)
    return base


def test_list_marks_duplicates_and_held(home):
    cfg = config.Config.load(home)
    filed = make_pdf(cfg.root / "01_כספים" / "בנק" / "x.pdf", "same")
    index.rebuild(cfg)
    (home / "_נכנס" / "dup.pdf").write_bytes(filed.read_bytes())
    make_pdf(home / "_נכנס" / "סיכום מיון.pdf", "x")
    make_image(home / "_נכנס" / "photo.jpg")
    (home / "_נכנס" / "_out").mkdir()
    make_pdf(home / "_נכנס" / "_out" / "ignored.pdf", "z")
    files = inbox.list_inbox(cfg)
    by = {f["file"]: f for f in files}
    assert set(by) == {"dup.pdf", "סיכום מיון.pdf", "photo.jpg"}
    assert by["dup.pdf"]["dup_of"] == ["01_כספים\\בנק\\x.pdf"] and by["dup.pdf"]["held"] is False
    assert by["סיכום מיון.pdf"]["held"] is True and by["סיכום מיון.pdf"]["held_why"]
    assert by["סיכום מיון.pdf"]["suggested_name"].endswith("_רפואי - לא ידוע.pdf")
    assert by["photo.jpg"]["held"] is False and by["photo.jpg"]["suggested_name"] == ""
    assert by["photo.jpg"]["ext"] == "jpg" and by["photo.jpg"]["size"] > 0 and len(by["photo.jpg"]["sha12"]) == 12
    assert all(set(f) == {"file", "size", "ext", "sha12", "dup_of", "held", "held_why", "suggested_name"} for f in files)


def test_list_holds_by_text_not_only_name(home):
    cfg = config.Config.load(home)
    # the synthetic PDF's base font has no Hebrew glyphs, so the text check uses the English default words
    make_pdf(home / "_נכנס" / "scan.pdf", "Discharge summary and lab results, visit 03.09.2026")
    f = inbox.list_inbox(cfg)[0]
    assert f["held"] is True and f["suggested_name"] == "2026-09_רפואי - לא ידוע.pdf"


def test_apply_only_approved(home):
    cfg = config.Config.load(home)
    make_image(home / "_נכנס" / "p1.jpg")
    make_image(home / "_נכנס" / "p2.jpg", size=(300, 500))
    make_pdf(home / "_נכנס" / "other.pdf", "other")
    proposal = {"docs": [
        doc(pages=["p1.jpg", "p2.jpg"], rotate=[0, 90], name="2026-03_חשבון חשמל - דנה.pdf", folder="01_כספים/בנק", why="bill",
            ledger={"type": "חשבון חשמל", "counterparty": "חברת החשמל", "whose": "דנה", "period": "2026-03", "amount": "412.30",
                    "currency": "ILS", "due": "2026-03-20", "action": "לשלם", "recurring": "חודשי"}),
        doc(pages=["other.pdf"], rotate=[0], name="2026-01_מכתב - דנה.pdf", folder="02_בית"),
    ], "note": ""}
    results = inbox.apply(cfg, proposal, approved=[0])
    dest = cfg.root / "01_כספים" / "בנק" / "2026-03_חשבון חשמל - דנה.pdf"
    assert len(results) == 1 and results[0]["i"] == 0 and results[0]["dest"] == str(dest) and dest.exists()
    assert pdf.page_count(dest) == 2
    assert not (home / "_נכנס" / "p1.jpg").exists() and (home / "_נכנס" / "_done" / "p1.jpg").exists()  # pages kept, out of the way
    assert (home / "_נכנס" / "other.pdf").exists()  # not approved: untouched
    rows = ledger.rows(cfg)
    assert len(rows) == 1 and rows[0]["type"] == "חשבון חשמל" and rows[0]["amount"] == "412.30" and rows[0]["source"] == "intake"
    assert rows[0]["path"] == "01_כספים/בנק/2026-03_חשבון חשמל - דנה.pdf"
    assert any(r["name"] == "2026-03_חשבון חשמל - דנה.pdf" for r in index.rows(cfg))


def test_apply_single_pdf_moves_it_as_is(home):
    cfg = config.Config.load(home)
    src = make_pdf(home / "_נכנס" / "one.pdf", "x")
    proposal = {"docs": [doc(pages=["one.pdf"], rotate=[0], name="2026-01_מכתב - דנה.pdf", folder="02_בית")]}
    r = inbox.apply(cfg, proposal, approved=[0])
    assert not src.exists() and (cfg.root / "02_בית" / "2026-01_מכתב - דנה.pdf").exists() and r[0]["handoff"] is False


def test_apply_overrides_name_folder_and_mkdir(home):
    cfg = config.Config.load(home)
    make_pdf(home / "_נכנס" / "one.pdf", "x")
    proposal = {"docs": [doc(pages=["one.pdf"], rotate=[0], name="bad name.pdf", folder="02_בית")]}
    r = inbox.apply(cfg, proposal, approved=[0], names={0: "2026-01_מכתב - יוסי.pdf"}, folders={0: "02_בית/דירה"}, mkdir={0})
    assert (cfg.root / "02_בית" / "דירה" / "2026-01_מכתב - יוסי.pdf").exists() and r[0]["name"] == "2026-01_מכתב - יוסי.pdf"


def test_apply_uses_original_for_xlsx_handoff(home):
    cfg = config.Config.load(home)
    cfg.tree[1]["handoff"] = {"inbox": "01_כספים/_inbox", "originals": True}
    cfg.save()
    cfg = config.Config.load(home)
    make_pdf(home / "_נכנס" / "04.pdf", "x")
    (home / "_נכנס" / "04.orig.xlsx").write_bytes(b"PK\x03\x04fake")
    (home / "_נכנס" / "card.xlsx").write_bytes(b"PK\x03\x04fake2")
    proposal = {"docs": [
        doc(pages=["04.pdf"], rotate=[0], name="2026-09_כרטיס - דנה.pdf", folder="01_כספים/כרטיסי אשראי"),
        doc(pages=["card.xlsx"], rotate=[0], name="2026-10_כרטיס - דנה.pdf", folder="01_כספים/כרטיסי אשראי"),
    ]}
    r = inbox.apply(cfg, proposal, approved=[0, 1])
    inbox_dir = cfg.root / "01_כספים" / "_inbox"
    assert (inbox_dir / "2026-09_כרטיס - דנה.xlsx").exists() and (inbox_dir / "2026-10_כרטיס - דנה.xlsx").exists()
    assert r[0]["handoff"] is True and r[1]["handoff"] is True and ledger.rows(cfg) == []  # the other engine extracts the fields


def test_apply_locked_uses_template_name_and_no_ledger(home):
    cfg = config.Config.load(home)
    sensitive.set_level(cfg, "03_משפחה/דנה/בריאות", "locked")
    make_pdf(home / "_נכנס" / "s.pdf", "ביקור 03.09.2026")
    cfg.owner = "דנה"
    cfg.save()
    proposal = {"docs": [doc(pages=["s.pdf"], rotate=[0], name="whatever.pdf", folder="03_משפחה/דנה/בריאות", sensitive="locked",
                             summary="should not be stored", ledger={"type": "סיכום", "counterparty": "", "whose": "דנה", "period": "2026-09",
                                                                      "amount": "", "currency": "", "due": "", "action": "", "recurring": ""})]}
    r = inbox.apply(cfg, proposal, approved=[0])
    assert r[0]["name"] == "2026-09_רפואי - דנה.pdf" and (cfg.root / "03_משפחה" / "דנה" / "בריאות" / "2026-09_רפואי - דנה.pdf").exists()
    assert ledger.rows(cfg) == [] and index.rows(cfg)[0]["sensitive"] == "רפואי"
    assert "should not be stored" not in (home / "יומן_קליטה.csv").read_text(encoding="utf-8-sig")
    make_pdf(home / "_נכנס" / "s2.pdf", "x")
    r = inbox.apply(cfg, {"docs": [doc(pages=["s2.pdf"], rotate=[0], name="x.pdf", folder="03_משפחה/דנה/בריאות")]},
                    approved=[0], names={0: "2026-02_רפואי - דנה.pdf"})
    assert r[0]["name"] == "2026-02_רפואי - דנה.pdf"


def test_apply_skip_moves_to_skipped(home):
    cfg = config.Config.load(home)
    make_image(home / "_נכנס" / "ad.jpg")
    r = inbox.apply(cfg, {"docs": [doc(pages=["ad.jpg"], rotate=[0], skip="advert")]}, approved=[0])
    assert r[0]["skipped"] is True and (home / "_נכנס" / "_skipped" / "ad.jpg").exists() and not (home / "_נכנס" / "ad.jpg").exists()


def test_apply_failure_leaves_other_docs_and_reports(home):
    cfg = config.Config.load(home)
    make_pdf(home / "_נכנס" / "a.pdf", "a")
    make_pdf(home / "_נכנס" / "b.pdf", "b")
    proposal = {"docs": [doc(pages=["a.pdf"], rotate=[0], name="x.pdf", folder="01_כספים/לא קיימת"),
                         doc(pages=["b.pdf"], rotate=[0], name="y.pdf", folder="02_בית")]}
    r = inbox.apply(cfg, proposal, approved=[0, 1])
    assert r[0]["ok"] is False and "error" in r[0] and (home / "_נכנס" / "a.pdf").exists()
    assert r[1]["ok"] is True and (cfg.root / "02_בית" / "y.pdf").exists()


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_inbox_cli(home):
    make_pdf(home / "_נכנס" / "one.pdf", "x")
    make_pdf(home / "_נכנס" / "two.pdf", "y")
    d = json.loads(run_cli(home, "inbox").stdout)
    assert d["ok"] and [f["file"] for f in d["files"]] == ["one.pdf", "two.pdf"]
    proposal = {"docs": [doc(pages=["one.pdf"], rotate=[0], name="2026-01_מכתב - דנה.pdf", folder="02_בית"),
                         doc(pages=["two.pdf"], rotate=[0], name="2026-02_מכתב - דנה.pdf", folder="02_בית")], "note": ""}
    (home / "_נכנס" / "_proposal.json").write_text(json.dumps(proposal, ensure_ascii=False), encoding="utf-8")
    r = run_cli(home, "intake-apply", "--approve", "2", "--name", "2=2026-02_מכתב - יוסי.pdf", "--folder", "2=02_בית/חדש", "--mkdir", "2")
    d = json.loads(r.stdout)
    assert r.returncode == 0 and d["ok"] and d["results"][0]["i"] == 2 and d["results"][0]["name"] == "2026-02_מכתב - יוסי.pdf"
    assert (home.parent / "02_בית" / "חדש" / "2026-02_מכתב - יוסי.pdf").exists() and (home / "_נכנס" / "one.pdf").exists()
