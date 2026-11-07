"""Weekly review: what came in, what waits, which recurring documents are missing, what is open.

Reads the instance's index, ledger and intake log (names and ledger rows only, never
document content), fills the HTML template of the instance language, writes it next
to the other system files and opens it in the browser.

Usage: python -I -X utf8 review.py [--home DIR] [--today YYYY-MM-DD] [--no-open]
Prints one JSON line: {"ok": true, "file": "...", "summary": {...}}.
"""
import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "brain" / "scripts"))  # the sibling skill's engine

from seder import config, index, ledger, names  # noqa: E402

ASSETS = HERE.parent / "assets"
TITLE = {"he": "סקירה שבועית", "en": "Weekly review"}


def _week_rows(cfg, today: dt.date) -> list[dict]:
    path = cfg.path("log")
    if not path.is_file():
        return []
    since = today - dt.timedelta(days=7)
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            r = names.from_row("log", cfg.lang, raw)
            try:
                when = dt.datetime.strptime(r["when"][:16], "%Y-%m-%d %H:%M").date()
            except ValueError:
                continue
            if since < when <= today:
                rows.append({**r, "day": when.isoformat()})
    rows.sort(key=lambda r: r["when"], reverse=True)
    return rows


def _pending_inbox(cfg) -> int:
    box = cfg.path("inbox")
    if not box.is_dir():
        return 0
    return sum(1 for p in box.iterdir() if p.is_file() and not p.name.startswith(("_", ".", "~$")))


def _archive_candidates(cfg, today: dt.date) -> list[dict]:
    try:
        from seder import project  # Task 11; absent in earlier builds
    except ImportError:
        return []
    try:
        return project.archive_candidates(cfg, today)
    except Exception:
        return []


def compute(cfg, today: dt.date) -> dict:
    idx = index.rows(cfg)
    led = ledger.rows(cfg)
    week = _week_rows(cfg, today)
    gaps = ledger.recurring_gaps(cfg, today)
    open_items = ledger.open_items(cfg, today)
    return {
        "today": today.isoformat(),
        "owner": cfg.owner,
        "week": {"filed": len(week), "rows": week},
        "pending_inbox": _pending_inbox(cfg),
        "gaps": gaps,
        "open": open_items,
        "archive_candidates": _archive_candidates(cfg, today),
        "small_things": {
            "undated": sum(1 for r in idx if not r["date"]),
            "no_period": sum(1 for r in led if not r["period"].strip()),
        },
        "totals": {"documents": len(idx), "ledger_rows": len(led), "sensitive": sum(1 for r in idx if r["sensitive"])},
    }


# ---- a 40-line template engine: {{key}}, {{a.b}}, {{#list}}...{{/list}}, {{^list}}...{{/list}} ----

_BLOCK = re.compile(r"\{\{([#^])([\w.]+)\}\}(.*?)\{\{/\2\}\}", re.S)
_VAR = re.compile(r"\{\{([\w.]+)\}\}")


def _lookup(ctx: dict, key: str):
    cur = ctx
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "✓" if v else ""
    if isinstance(v, list):
        return ", ".join(_text(x) for x in v)
    return html.escape(str(v), quote=False)


def render(data: dict, template: str) -> str:
    def block(m):
        kind, key, body = m.group(1), m.group(2), m.group(3)
        value = _lookup(data, key)
        if kind == "#":
            if isinstance(value, list):
                return "".join(render({**data, **(item if isinstance(item, dict) else {".": item})}, body) for item in value)
            return render(data, body) if value else ""
        return "" if value else render(data, body)

    out = _BLOCK.sub(block, template)
    return _VAR.sub(lambda m: _text(_lookup(data, m.group(1))), out)


def build(cfg, today: dt.date) -> tuple[Path, dict]:
    data = compute(cfg, today)
    data["title"] = TITLE.get(cfg.lang, TITLE["en"])
    data["lang"] = cfg.lang
    data["counts"] = {"gaps": len(data["gaps"]), "open": len(data["open"]), "archive": len(data["archive_candidates"])}
    template = (ASSETS / f"review.{cfg.lang}.html").read_text(encoding="utf-8")
    out = cfg.path("review")
    out.write_text(render(data, template), encoding="utf-8")
    summary = {"filed": data["week"]["filed"], "pending_inbox": data["pending_inbox"], "gaps": len(data["gaps"]),
               "open": len(data["open"]), "archive_candidates": len(data["archive_candidates"]),
               "undated": data["small_things"]["undated"], "no_period": data["small_things"]["no_period"]}
    return out, summary


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="review.py")
    p.add_argument("--home")
    p.add_argument("--today")
    p.add_argument("--no-open", action="store_true")
    try:
        args = p.parse_args(argv)
        home = config.find_home(explicit=Path(args.home) if args.home else None)
        if home is None:
            raise SystemExit("לא נמצאה תיקיית מוח / no archive found: run init, or set SEDER_HOME")
        cfg = config.Config.load(home)
        today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
        out, summary = build(cfg, today)
        if not args.no_open:
            try:
                webbrowser.open(out.as_uri())
            except Exception:
                pass
        print(json.dumps({"ok": True, "file": str(out), "summary": summary}, ensure_ascii=False))
        return 0
    except SystemExit as e:
        if e.code in (0, None):
            return 0
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{e.__class__.__name__}: {e}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
