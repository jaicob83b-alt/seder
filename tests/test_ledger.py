import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from helpers import make_pdf
from seder import config, index, ledger, names

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def rec(**kw):
    return {**dict.fromkeys(ledger.KEYS, ""), **kw}


def test_parse_name():
    assert ledger.parse_name("2026-09_חשבון חשמל - דנה.pdf") == {"period": "2026-09", "type": "חשבון חשמל", "whose": "דנה"}
    assert ledger.parse_name("2026_אישור שנתי - דנה.pdf")["period"] == "2026"
    assert ledger.parse_name("מכתב.pdf") == {"period": "", "type": "מכתב", "whose": ""}
    assert ledger.parse_name("2026-09_חשבון - דנה - 3 עמודים.pdf")["whose"] == "דנה"


def test_append_and_rows_hebrew_header(home):
    cfg = config.Config.load(home)
    ledger.append(cfg, rec(path="01_כספים/בנק/a.pdf", type="חשבון", whose="דנה", period="2026-09", amount="412.30", currency="ILS"))
    text = (home / "פנקס.csv").read_text(encoding="utf-8-sig").splitlines()
    assert text[0] == ",".join(names.header("ledger", "he"))
    rows = ledger.rows(cfg)
    assert len(rows) == 1 and rows[0]["amount"] == "412.30" and rows[0]["path"] == "01_כספים/בנק/a.pdf"


def test_append_refuses_sensitive_path(home):
    cfg = config.Config.load(home)
    with pytest.raises(ValueError):
        ledger.append(cfg, rec(path="03_משפחה/דנה/בריאות/x.pdf", type="סיכום"))
    assert ledger.rows(cfg) == []


def test_gap_detection_monthly(home):
    cfg = config.Config.load(home)
    for p in ["2026-05", "2026-06", "2026-07", "2026-09"]:
        ledger.append(cfg, rec(path=f"01_כספים/{p}_חשבון חשמל - דנה.pdf", type="חשבון חשמל", whose="דנה", period=p, source="name"))
    gaps = ledger.recurring_gaps(cfg, date(2026, 11, 7))
    assert gaps == [{"type": "חשבון חשמל", "whose": "דנה", "counterparty": "", "every_months": 1, "missing": ["2026-08"],
                     "missing_total": 1, "older": 0, "last": "2026-09"}]


def test_gap_detection_flags_overdue_after_grace(home):
    cfg = config.Config.load(home)
    for p in ["2026-03", "2026-04", "2026-05", "2026-06"]:
        ledger.append(cfg, rec(path=f"01_כספים/{p}_x.pdf", type="חשבון מים", whose="דנה", period=p))
    gaps = ledger.recurring_gaps(cfg, date(2026, 11, 7))
    assert gaps[0]["missing"] == ["2026-07", "2026-08", "2026-09"]   # October still inside the grace month


def test_gap_detection_bimonthly(home):
    cfg = config.Config.load(home)
    for p in ["2026-01", "2026-03", "2026-07"]:
        ledger.append(cfg, rec(path=f"01_כספים/{p}_x.pdf", type="ארנונה", whose="בית", period=p))
    gaps = ledger.recurring_gaps(cfg, date(2026, 9, 1))
    assert gaps == [{"type": "ארנונה", "whose": "בית", "counterparty": "", "every_months": 2, "missing": ["2026-05"],
                     "missing_total": 1, "older": 0, "last": "2026-07"}]


def test_gap_detection_reports_only_recent_months(home):
    cfg = config.Config.load(home)
    periods = ["2021-03", "2021-05", "2021-06", "2021-08"] + [f"2026-{m:02d}" for m in (1, 2, 3, 5, 6, 7, 9)]
    for p in periods:
        ledger.append(cfg, rec(path=f"01_כספים/{p}_תלוש שכר - דנה.pdf", type="תלוש שכר", whose="דנה", period=p))
    gaps = ledger.recurring_gaps(cfg, date(2026, 11, 7))
    assert gaps[0]["missing"] == ["2025-11", "2025-12", "2026-04", "2026-08"]   # 12-month window; 2021 holes are history
    assert gaps[0]["missing_total"] >= 50 and gaps[0]["older"] == gaps[0]["missing_total"] - 4
    assert ledger.recurring_gaps(cfg, date(2026, 11, 7), lookback_months=3)[0]["missing"] == ["2026-08"]


def test_gap_detection_drops_series_that_ended_before_the_window(home):
    cfg = config.Config.load(home)
    for p in ["2023-01", "2023-02", "2023-03", "2023-05"]:   # a supplier that stopped in 2023
        ledger.append(cfg, rec(path=f"01_כספים/{p}_חשבונית ספק ישן - עסק.pdf", type="חשבונית ספק ישן", whose="עסק", period=p))
    assert ledger.recurring_gaps(cfg, date(2026, 11, 7)) == []
    assert ledger.recurring_gaps(cfg, date(2023, 8, 1))[0]["missing"] == ["2023-04", "2023-06"]


def test_gap_detection_skips_bad_periods_and_short_series(home):
    cfg = config.Config.load(home)
    for p in ["2026", "2026-Q3", "", "2026-01", "2026-02"]:
        ledger.append(cfg, rec(path=f"x/{p or 'none'}.pdf", type="t", whose="w", period=p))
    assert ledger.recurring_gaps(cfg, date(2026, 11, 7)) == []


def test_open_items_order_and_done(home):
    cfg = config.Config.load(home)
    ledger.append(cfg, rec(path="a.pdf", action="לשלם", due="2026-11-20"))
    ledger.append(cfg, rec(path="b.pdf", action="לחתום", due=""))
    ledger.append(cfg, rec(path="c.pdf", action="לשלם", due="2026-11-10"))
    ledger.append(cfg, rec(path="d.pdf", action="", due="2026-11-01"))
    items = ledger.open_items(cfg, date(2026, 11, 12))
    assert [r["path"] for r in items] == ["c.pdf", "a.pdf", "b.pdf"]
    assert [r["overdue"] for r in items] == [True, False, False]
    ledger.mark_done(cfg, "c.pdf", "2026-11-08")
    assert [r["path"] for r in ledger.open_items(cfg, date(2026, 11, 7))] == ["a.pdf", "b.pdf"]
    assert next(r for r in ledger.rows(cfg) if r["path"] == "c.pdf")["done"] == "2026-11-08"


def test_backfill_skips_sensitive_and_existing(home):
    cfg = config.Config.load(home)
    make_pdf(cfg.root / "01_כספים" / "בנק" / "2026-01_דף חשבון - דנה.pdf", "a")
    make_pdf(cfg.root / "03_משפחה" / "דנה" / "בריאות" / "2026-02_סיכום - דנה.pdf", "b")
    index.rebuild(cfg)
    assert ledger.backfill_from_names(cfg) == 1
    rows = ledger.rows(cfg)
    assert rows[0]["type"] == "דף חשבון" and rows[0]["whose"] == "דנה" and rows[0]["period"] == "2026-01" and rows[0]["source"] == "name"
    assert ledger.backfill_from_names(cfg) == 0   # idempotent


def run_cli(home, *args):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(CLI), *args],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_ledger_cli(home):
    cfg = config.Config.load(home)
    for p in ["2026-05", "2026-06", "2026-07"]:
        make_pdf(cfg.root / "01_כספים" / "בנק" / f"{p}_חשבון חשמל - דנה.pdf", p)
    index.rebuild(cfg)
    r = run_cli(home, "ledger", "backfill")
    assert json.loads(r.stdout) == {"ok": True, "added": 3}
    r = run_cli(home, "ledger", "add", "--json", json.dumps({"path": "01_כספים/בנק/z.pdf", "type": "חשבונית", "action": "לשלם", "due": "2026-12-01"}, ensure_ascii=False))
    assert json.loads(r.stdout)["ok"] is True
    r = run_cli(home, "ledger", "gaps", "--today", "2026-11-07")
    assert json.loads(r.stdout)["gaps"][0]["missing"] == ["2026-08", "2026-09"]
    r = run_cli(home, "ledger", "open")
    assert [i["path"] for i in json.loads(r.stdout)["items"]] == ["01_כספים/בנק/z.pdf"]
    r = run_cli(home, "ledger", "done", "01_כספים/בנק/z.pdf")
    assert json.loads(r.stdout)["ok"] and json.loads(run_cli(home, "ledger", "open").stdout)["items"] == []
