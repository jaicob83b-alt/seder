"""The ledger: one structured row per document, like a bookkeeping journal.

From these rows the weekly review derives recurring documents and their
gaps, and open actions with due dates. Sensitive documents never get a row.
"""
import csv
import math
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import index, names, sensitive
from .config import Config

KEYS = names.KEYS["ledger"]
STEM_RE = re.compile(r"^(?:(\d{4}(?:-\d{2})?)_)?(.*)$")
PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")
ALLOWED_EVERY = (1, 2, 3, 6, 12)


def parse_name(name: str) -> dict:
    """`2026-09_חשבון חשמל - דנה.pdf` -> period, type, whose (extra identifiers after the second dash are ignored)."""
    m = STEM_RE.match(Path(name).stem)
    parts = [p.strip() for p in m.group(2).split(" - ")]
    return {"period": m.group(1) or "", "type": parts[0], "whose": parts[1] if len(parts) > 1 else ""}


def _norm(path: str) -> str:
    return str(path).replace("\\", "/").strip("/")


def rows(cfg: Config) -> list[dict]:
    path = cfg.path("ledger")
    if not path.is_file():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [names.from_row("ledger", cfg.lang, row) for row in csv.DictReader(f)]


def _write(cfg: Config, recs: list[dict]) -> None:
    path = cfg.path("ledger")
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(names.header("ledger", cfg.lang))
        for r in recs:
            w.writerow(names.to_row("ledger", cfg.lang, r))
    os.replace(tmp, path)


def _full(rec: dict) -> dict:
    return {k: ("" if rec.get(k) is None else str(rec.get(k))) for k in KEYS}


def append(cfg: Config, rec: dict) -> None:
    """Add one row. A sensitive path is refused."""
    rec = _full(rec)
    if sensitive.is_sensitive(cfg, rec["path"]):
        raise ValueError(f"sensitive document, no ledger row: {rec['path']}")
    path = cfg.path("ledger")
    new = not path.exists()
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(names.header("ledger", cfg.lang))
        w.writerow(names.to_row("ledger", cfg.lang, rec))


def backfill_from_names(cfg: Config) -> int:
    """A row for every indexed, non-sensitive document that has none, from its name only."""
    existing = {_norm(r["path"]) for r in rows(cfg)}
    added = []
    for r in index.rows(cfg):
        key = _norm(r["path"])
        if r["sensitive"] or key in existing or sensitive.is_sensitive(cfg, key):
            continue
        parsed = parse_name(r["name"])
        added.append(_full({"path": key, **parsed, "source": "name"}))
        existing.add(key)
    if added:
        _write(cfg, rows(cfg) + added)
    return len(added)


def _ym_index(period: str) -> int | None:
    m = PERIOD_RE.match(period or "")
    if not m or not 1 <= int(m.group(2)) <= 12:
        return None
    return int(m.group(1)) * 12 + int(m.group(2)) - 1


def _ym_str(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def recurring_gaps(cfg: Config, today: date, lookback_months: int = 12) -> list[dict]:
    """Document series with a regular monthly rhythm, and the periods that are missing.

    A series needs three periods of the form YYYY-MM. The rhythm is the gcd of
    the intervals (1, 2, 3, 6 or 12 months) and at least half the intervals
    must equal it. Expected periods run from the first one to the later of the
    last one and the horizon: today's month minus one month of grace minus one
    rhythm, so a bill that is simply not due yet is not reported. `missing`
    lists only holes inside the last `lookback_months` months (older holes are
    history, not this week's work); `missing_total` counts all of them and
    `older` the ones left out.
    """
    groups: dict[tuple, set] = defaultdict(set)
    for r in rows(cfg):
        i = _ym_index(r["period"])
        if i is not None:
            groups[(r["type"], r["whose"], r.get("counterparty", ""))].add(i)
    out = []
    today_idx = today.year * 12 + today.month - 1
    for key in sorted(groups):
        idxs = sorted(groups[key])
        if len(idxs) < 3:
            continue
        diffs = [b - a for a, b in zip(idxs, idxs[1:])]
        every = math.gcd(*diffs)
        if every not in ALLOWED_EVERY or sum(d == every for d in diffs) * 2 < len(diffs):
            continue
        have = set(idxs)
        since = today_idx - lookback_months
        if idxs[-1] < since:
            continue  # the series ended before the window: a closed supplier, not a gap
        end = max(idxs[-1], today_idx - 1 - every)
        all_missing = [i for i in range(idxs[0], end + 1, every) if i not in have]
        recent = [_ym_str(i) for i in all_missing if i >= since]
        if recent:
            out.append({"type": key[0], "whose": key[1], "counterparty": key[2],
                        "every_months": every, "missing": recent, "missing_total": len(all_missing),
                        "older": len(all_missing) - len(recent), "last": _ym_str(idxs[-1])})
    return out


def open_items(cfg: Config, today: date) -> list[dict]:
    """Rows with an action and no `done`, by due date (no date last), with an `overdue` flag."""
    items = [dict(r) for r in rows(cfg) if r["action"].strip() and not r["done"].strip()]
    for r in items:
        r["overdue"] = bool(r["due"].strip()) and r["due"].strip() < today.isoformat()
    items.sort(key=lambda r: (not r["due"].strip(), r["due"].strip()))
    return items


def mark_done(cfg: Config, path: str, when: str) -> int:
    """Set `done` on the row(s) of `path`. Returns how many rows changed."""
    current = rows(cfg)
    key = _norm(path)
    n = 0
    for r in current:
        if _norm(r["path"]) == key and not r["done"].strip():
            r["done"] = when
            n += 1
    if n:
        _write(cfg, current)
    return n
