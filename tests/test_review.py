import csv
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from helpers import make_pdf
from seder import config, index, ledger, names

REVIEW_DIR = Path(__file__).parents[1] / "skills" / "brain-review"
sys.path.insert(0, str(REVIEW_DIR / "scripts"))
import review  # noqa: E402


def rec(**kw):
    return {**dict.fromkeys(ledger.KEYS, ""), **kw}


def seed(home):
    """A monthly series with a gap, two open actions, a row without a period, 2 filings this week + 1 old, one undated file, one pending inbox file."""
    cfg = config.Config.load(home)
    for p in ["2026-05", "2026-06", "2026-07", "2026-09"]:
        ledger.append(cfg, rec(path=f"01_כספים/בנק/{p}_חשבון חשמל - דנה.pdf", type="חשבון חשמל", whose="דנה", period=p))
    ledger.append(cfg, rec(path="a.pdf", action="לשלם", due="2026-11-20"))
    ledger.append(cfg, rec(path="b.pdf", action="לחתום", due=""))
    ledger.append(cfg, rec(path="c.pdf", type="מכתב", period=""))
    with open(cfg.path("log"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(names.header("log", cfg.lang))
        for when, new in [("2026-11-05 10:00", "x1.pdf"), ("2026-11-06 09:30", "x2.pdf"), ("2026-10-01 08:00", "old.pdf")]:
            w.writerow([when, "orig", new, "01_כספים", "why", "כן", "abc", "undo"])
    make_pdf(cfg.root / cfg.tree[1]["physical"] / "מכתב בלי תאריך.pdf", "x")
    make_pdf(cfg.root / cfg.tree[1]["physical"] / "2026-01_דף - דנה.pdf", "y")
    index.rebuild(cfg)
    make_pdf(cfg.path("inbox") / "new.pdf", "n")
    return cfg


def test_compute(home):
    cfg = seed(home)
    d = review.compute(cfg, date(2026, 11, 7))
    assert d["week"]["filed"] == 2 and [r["new"] for r in d["week"]["rows"]] == ["x2.pdf", "x1.pdf"]
    assert d["pending_inbox"] == 1
    assert d["gaps"][0]["type"] == "חשבון חשמל" and d["gaps"][0]["missing"] == ["2026-08"]
    assert [r["path"] for r in d["open"]] == ["a.pdf", "b.pdf"]
    assert d["archive_candidates"] == []
    assert d["small_things"] == {"undated": 1, "no_period": 3}  # a.pdf, b.pdf, c.pdf carry no period
    assert d["today"] == "2026-11-07" and d["totals"]["documents"] == 2


def test_pending_count_ignores_state_files(home):
    cfg = config.Config.load(home)
    (cfg.path("inbox") / "sources_state.json").write_text("{}", encoding="utf-8")
    (cfg.path("inbox") / "_proposal.json").write_text("{}", encoding="utf-8")
    make_pdf(cfg.path("inbox") / "real.pdf", "x")
    assert review.compute(cfg, date(2026, 11, 7))["pending_inbox"] == 1


def test_compute_on_empty_instance(home):
    d = review.compute(config.Config.load(home), date(2026, 11, 7))
    assert d["week"]["filed"] == 0 and d["gaps"] == [] and d["open"] == [] and d["pending_inbox"] == 0


def test_render_values_lists_and_empty_blocks():
    tpl = "<h1>{{title}}</h1><ul>{{#gaps}}<li>{{type}}: {{missing}}</li>{{/gaps}}</ul>{{^gaps}}<p>none</p>{{/gaps}}<p>{{week.filed}}</p>"
    out = review.render({"title": "T", "gaps": [{"type": "a", "missing": ["2026-08", "2026-09"]}], "week": {"filed": 2}}, tpl)
    assert out == "<h1>T</h1><ul><li>a: 2026-08, 2026-09</li></ul><p>2</p>"
    out2 = review.render({"title": "T", "gaps": [], "week": {"filed": 0}}, tpl)
    assert "<li>" not in out2 and "<p>none</p>" in out2 and "{{" not in out2


def test_render_escapes_html_and_tolerates_missing_keys():
    assert review.render({"x": "<b>"}, "{{x}}") == "&lt;b&gt;"
    assert review.render({}, "[{{nothing}}]") == "[]"


def test_main_writes_page_without_opening(home, capsys):
    cfg = seed(home)
    rc = review.main(["--home", str(home), "--today", "2026-11-07", "--no-open"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"] and Path(out["file"]) == cfg.path("review") and cfg.path("review").exists()
    html = cfg.path("review").read_text(encoding="utf-8")
    assert "חשבון חשמל" in html and "2026-08" in html and 'dir="rtl"' in html and "{{" not in html
    assert out["summary"] == {"filed": 2, "pending_inbox": 1, "gaps": 1, "open": 2, "archive_candidates": 0, "undated": 1, "no_period": 3}


def test_main_english_template(home_en, capsys):
    rc = review.main(["--home", str(home_en), "--today", "2026-11-07", "--no-open"])
    out = json.loads(capsys.readouterr().out)
    html = Path(out["file"]).read_text(encoding="utf-8")
    assert rc == 0 and 'dir="ltr"' in html and "Weekly review" in html


def test_review_cli_subprocess(home):
    env = {**os.environ, "SEDER_HOME": str(home)}
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(REVIEW_DIR / "scripts" / "review.py"), "--no-open"],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is True


def test_brain_review_skill_md():
    text = (REVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: brain-review\n")
    for w in ("סקירה שבועית", "weekly review", "מה חסר", "what am I missing"):
        assert w in text, w
    assert "review.py" in text and "brain" in text
