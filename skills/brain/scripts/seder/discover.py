"""The first look: where a new person's documents live, by names only.

Runs before there is an instance, after the person says yes. It walks the
usual places (Documents, Downloads, Desktop, cloud-sync folders), counts the
files that look like documents, and recognises topics in file and folder
names with the lexicon in `assets/topics.json`. Nothing is opened, moved or
written. The output holds counts and folder names only, never file names, so
the summary can go into the conversation without carrying anyone's paperwork.
"""
import json
import os
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "assets"
DOC_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".webp",
            ".doc", ".docx", ".xls", ".xlsx", ".csv", ".odt", ".ods", ".rtf"}
SKIP_DIRS = {"node_modules", "appdata", "site-packages", "__pycache__", "venv", ".venv", "env",
             "program files", "program files (x86)", "windows", "$recycle.bin", "system volume information",
             "library", "dist", "build", "target", "my music", "my videos"}
NUM_RE = re.compile(r"^\d{2}[_ -]")
LATIN_TOKEN = re.compile(r"[a-z0-9]+")
DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_FILES = 50000


def lexicon() -> dict:
    return json.loads((ASSETS / "topics.json").read_text(encoding="utf-8"))


def candidate_roots(home: Path | None = None) -> list[Path]:
    """The usual places documents collect, those that exist. Drives of cloud-sync clients included."""
    h = Path(home) if home else Path.home()
    out = [h / "Documents", h / "Downloads", h / "Desktop"]
    try:
        out += sorted(p for p in h.iterdir() if p.is_dir() and p.name.lower().startswith(("onedrive", "google drive", "dropbox", "icloud")))
    except OSError:
        pass
    if os.name == "nt" and home is None:
        for letter in "GH":
            drive = Path(f"{letter}:/My Drive")
            out.append(drive)
    seen, result = set(), []
    for p in out:
        try:
            if p.is_dir() and p.resolve() not in seen:
                seen.add(p.resolve())
                result.append(p)
        except OSError:
            continue
    return result


def _matcher(words: list[str]):
    heb = [w for w in words if not w.isascii()]
    lat = {w.lower() for w in words if w.isascii()}
    lat_phrases = [w for w in lat if " " in w]
    lat_tokens = {w for w in lat if " " not in w}

    def match(text: str) -> bool:
        if any(w in text for w in heb):
            return True
        low = text.lower()
        if any(p in low for p in lat_phrases):
            return True
        return bool(lat_tokens & set(LATIN_TOKEN.findall(low)))
    return match


def _skip(name: str) -> bool:
    return name.startswith((".", "~$", "$")) or name.lower() in SKIP_DIRS


def discover(roots: list[Path] | None = None, max_depth: int = DEFAULT_MAX_DEPTH,
             max_files: int = DEFAULT_MAX_FILES, lang: str = "he") -> dict:
    """Counts per place, per top folder and per topic. Names only; nothing is read or written."""
    lex = lexicon()
    topics = [(t, _matcher(t["words"])) for t in lex["topics"]]
    roots = [Path(r) for r in (roots if roots is not None else candidate_roots())]
    places, topic_hits, topic_places = [], {t["id"]: 0 for t, _ in topics}, {t["id"]: {} for t, _ in topics}
    seen_files, truncated = 0, False
    archives, instances = [], []
    for root in roots:
        if not root.is_dir():
            continue
        place = {"path": str(root), "documents": 0, "by_type": {}, "top_folders": {}}
        try:
            top = [d for d in os.listdir(root) if (root / d).is_dir() and not _skip(d)]
        except OSError:
            top = []
        if sum(1 for d in top if NUM_RE.match(d)) >= 3:
            archives.append(str(root))
        for dirpath, dirnames, filenames in os.walk(root):
            d = Path(dirpath)
            rel = d.relative_to(root)
            if "brain.json" in filenames:  # an existing archive's system folder: report it, do not count it
                instances.append(str(d))
                dirnames[:] = []
                continue
            if len(rel.parts) >= max_depth:
                dirnames[:] = []
            dirnames[:] = [x for x in dirnames if not _skip(x)]
            folder_text = " ".join(rel.parts)
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext not in DOC_EXTS:
                    continue
                seen_files += 1
                if seen_files > max_files:
                    truncated = True
                    break
                place["documents"] += 1
                place["by_type"][ext] = place["by_type"].get(ext, 0) + 1
                head = rel.parts[0] if rel.parts else "."
                place["top_folders"][head] = place["top_folders"].get(head, 0) + 1
                text = f"{folder_text} {f}"
                for t, match in topics:
                    if match(text):
                        topic_hits[t["id"]] += 1
                        if not t.get("count_only"):
                            key = head if head != "." else root.name
                            topic_places[t["id"]][key] = topic_places[t["id"]].get(key, 0) + 1
            if truncated:
                break
        place["top_folders"] = dict(sorted(place["top_folders"].items(), key=lambda kv: -kv[1])[:12])
        places.append(place)
        if truncated:
            break
    found = []
    for t, _ in topics:
        n = topic_hits[t["id"]]
        if n < lex.get("min_hits", 3):
            continue
        row = {"id": t["id"], "label": t["label"].get(lang, t["label"]["en"]), "documents": n, "branch": t["branch"],
               "question": t["question"].get(lang, "") or None}
        if not t.get("count_only"):
            row["where"] = [k for k, _ in sorted(topic_places[t["id"]].items(), key=lambda kv: -kv[1])[:6]]
        found.append(row)
    found.sort(key=lambda r: -r["documents"])
    return {"places": places, "topics": found, "total_documents": sum(p["documents"] for p in places),
            "organized_archives": archives, "existing_instances": instances, "truncated": truncated,
            "suggested_plan": suggest_plan([r["id"] for r in found], lang)}


def suggest_plan(topic_ids: list[str], lang: str = "he") -> dict:
    """A tree plan (see tree.build) merged from the plan fragments of the topics that were found."""
    by_id = {t["id"]: t for t in lexicon()["topics"]}
    plan: dict = {"rename": {}, "subfolders_add": {}, "addons": []}
    addon_ids = {"pets", "military", "studies", "media", "community", "immigration", "dev_projects"}
    for tid in topic_ids:
        t = by_id.get(tid)
        if not t:
            continue
        if t["branch"] in addon_ids and t["branch"] not in plan["addons"]:
            plan["addons"].append(t["branch"])
        frag = t.get("plan") or {}
        for branch, names in (frag.get("rename") or {}).items():
            plan["rename"].setdefault(branch, names.get(lang) or names.get("en"))
        for branch, subs in (frag.get("subfolders_add") or {}).items():
            cur = plan["subfolders_add"].setdefault(branch, [])
            for s in subs.get(lang) or subs.get("en") or []:
                if s not in cur:
                    cur.append(s)
    return {k: v for k, v in plan.items() if v}
