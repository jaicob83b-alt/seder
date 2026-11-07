"""The inbox: what arrived, duplicates, quarantine, and applying an approved proposal.

Claude (in the conversation) reads the files that are not held, writes
`_proposal.json` (the contract below), and shows a table. After the person
says yes, `apply` does everything that must come out the same every time:
build the PDF, move without overwriting, verify the hash, log, index, ledger.

Proposal contract (`_proposal.json` in the inbox):
{"docs": [{"pages": ["01.jpg", "02.jpg"], "rotate": [0, 0], "name": "YYYY-MM_type - whose.pdf",
           "folder": "01_.../sub", "new_folder": false, "entity": "", "summary": "", "readable": true,
           "duplicate": "", "sensitive": "open|ask|locked", "confidence": "high|medium|low",
           "why": "", "skip": "",
           "ledger": {"type": "", "counterparty": "", "whose": "", "period": "", "amount": "",
                      "currency": "", "due": "", "action": "", "recurring": ""}}],
 "note": ""}
"""
import shutil
from pathlib import Path

from . import filing, index, ledger, pdf, sensitive, tree
from .config import Config

PROPOSAL = "_proposal.json"
OUT_DIR, DONE_DIR, SKIPPED_DIR = "_out", "_done", "_skipped"
OFFICE_EXT = {".xlsx", ".xls", ".docx", ".doc", ".pptx", ".csv"}
LEDGER_FIELDS = ("type", "counterparty", "whose", "period", "amount", "currency", "due", "action", "recurring")
HOLD_WHY = {
    "he": {"name": "השם נראה רפואי", "text": "בתוך המסמך יש מילים רפואיות"},
    "en": {"name": "the name looks medical", "text": "medical words inside the document"},
}


def _hold_reason(cfg: Config, name: str, text: str) -> str:
    why = HOLD_WHY.get(cfg.lang, HOLD_WHY["en"])
    if sensitive.looks_medical(cfg, "", [name], ""):
        return why["name"]
    if text and sensitive.looks_medical(cfg, "", [], text):
        return why["text"]
    return ""


def list_inbox(cfg: Config) -> list[dict]:
    """Every file waiting in the inbox: size, hash, duplicates in the index, quarantine."""
    box = cfg.path("inbox")
    if not box.is_dir():
        return []
    out = []
    for p in sorted(box.iterdir()):
        if not p.is_file() or p.name.startswith(("_", ".", "~$")):
            continue
        sha = index.sha12(p)
        text = pdf.text_sample(p) if p.suffix.lower() == ".pdf" else ""
        held_why = _hold_reason(cfg, p.name, text)
        out.append({
            "file": p.name, "size": p.stat().st_size, "ext": p.suffix.lower().lstrip("."), "sha12": sha,
            "dup_of": index.find_by_sha(cfg, sha), "held": bool(held_why), "held_why": held_why,
            "suggested_name": sensitive.template_name(cfg, p, text=text) if held_why else "",
        })
    return out


def _park(box: Path, p: Path, sub: str) -> Path:
    """Move a file into a side folder of the inbox (never delete), with a free name."""
    d = box / sub
    d.mkdir(exist_ok=True)
    dest = d / filing.free_name(d, p.name)
    shutil.move(str(p), str(dest))
    return dest


def _apply_one(cfg: Config, box: Path, i: int, d: dict, name_override, folder_override, mk: bool) -> dict:
    pages = [box / p for p in d.get("pages", [])]
    if not pages:
        raise ValueError("no pages")
    for p in pages:
        if not p.is_file():
            raise FileNotFoundError(f"page missing: {p.name}")
    if d.get("skip"):
        moved = [str(_park(box, p, SKIPPED_DIR)) for p in pages]
        return {"i": i, "ok": True, "skipped": True, "why": d["skip"], "moved": moved}

    folder = folder_override or d.get("folder") or ""
    if not folder:
        raise ValueError("no folder")
    lfields = d.get("ledger") or {}
    locked = sensitive.level(cfg, folder) == "locked" or d.get("sensitive") == "locked"
    first = pages[0]
    rotations = [int(r or 0) for r in (d.get("rotate") or [])]
    single = len(pages) == 1
    text = pdf.text_sample(first) if single and first.suffix.lower() == ".pdf" else ""

    name = name_override or d.get("name") or ""
    if locked and not name_override:
        name = sensitive.template_name(cfg, first, whose=lfields.get("whose") or d.get("entity", ""), text=text)
    if not name:
        raise ValueError("no name")

    original = None
    built = None
    if single and first.suffix.lower() in OFFICE_EXT:
        src = original = first
        name = Path(name).stem + first.suffix.lower()
    elif single and first.suffix.lower() == ".pdf" and not any(rotations):
        src = first
    else:
        out_dir = box / OUT_DIR
        out_dir.mkdir(exist_ok=True)
        src = built = out_dir / filing.free_name(out_dir, f"doc{i}.pdf")
        pdf.build_pdf(pages, rotations, src)
    if original is None:
        companions = sorted(box.glob(first.stem + ".orig.*"))
        if companions:
            original = companions[0]

    why = "" if locked else (d.get("why") or d.get("summary") or "")
    r = filing.file_doc(cfg, src, folder, name, why, mkdir=mk, original=original)

    for p in pages:  # pages that were not the moved file are kept, out of the way
        if p.exists():
            _park(box, p, DONE_DIR)
    if built is not None and built.exists():
        _park(box, built, DONE_DIR)

    dest = Path(r["dest"])
    rel = dest.relative_to(cfg.root).as_posix()
    if not locked and not r["handoff"] and not sensitive.is_sensitive(cfg, rel):
        ledger.append(cfg, {"path": rel, **{k: str(lfields.get(k, "") or "") for k in LEDGER_FIELDS}, "done": "", "source": "intake"})
    return {"i": i, "ok": True, "skipped": False, "name": dest.name, **r}


def apply(cfg: Config, proposal: dict, approved: list[int], names: dict | None = None,
          folders: dict | None = None, mkdir: set | None = None) -> list[dict]:
    """File the approved documents of a proposal (0-based indexes). Unapproved ones are not touched."""
    box = cfg.path("inbox")
    docs = proposal.get("docs") or []
    names, folders, mkdir = names or {}, folders or {}, mkdir or set()
    results = []
    for i in approved:
        if not 0 <= i < len(docs):
            results.append({"i": i, "ok": False, "error": f"no document {i}"})
            continue
        try:
            results.append(_apply_one(cfg, box, i, docs[i], names.get(i), folders.get(i), i in mkdir))
        except Exception as e:
            results.append({"i": i, "ok": False, "error": f"{e.__class__.__name__}: {e}"})
    return results
