"""Names of the instance's system files and CSV headers, per language.

The code works on fixed internal keys (`KEYS`); only the file names and the
header words change with `lang`. Hebrew reproduces the live archive exactly,
so an adopted archive keeps its files and its columns byte for byte.
"""

LANGS = ("he", "en")

FILES = {
    "he": {
        "index": "אינדקס.csv",
        "ledger": "פנקס.csv",
        "log": "יומן_קליטה.csv",
        "sensitive": "רגיש.json",
        "naming": "נוהל_שמות.md",
        "profile": "מי_אני.md",
        "inbox": "_נכנס",
        "proposed_tree": "עץ_מוצע.md",
        "studies_index": "אינדקס_לימודים.md",
        "review": "סקירה_שבועית.html",
    },
    "en": {
        "index": "index.csv",
        "ledger": "ledger.csv",
        "log": "intake_log.csv",
        "sensitive": "sensitive.json",
        "naming": "naming.md",
        "profile": "about_me.md",
        "inbox": "_inbox",
        "proposed_tree": "proposed_tree.md",
        "studies_index": "studies_index.md",
        "review": "weekly_review.html",
    },
}

KEYS = {
    "index": ["path", "topic", "subfolder", "name", "date", "ext", "kb", "sensitive", "sha12"],
    "log": ["when", "orig", "new", "folder", "why", "approved", "sha12", "undo"],
    "ledger": ["path", "type", "counterparty", "whose", "period", "amount", "currency",
               "due", "action", "recurring", "done", "source"],
}

HEADERS = {
    "he": {
        "index": ["נתיב", "נושא", "תת_תיקייה", "שם", "תאריך", "סוג_קובץ", "KB", "רגיש", "sha12"],
        "log": ["תאריך", "שם_מקורי", "שם_חדש", "תיקייה", "למה", "אישור", "sha12", "ביטול"],
        "ledger": ["נתיב", "סוג", "צד_שני", "של_מי", "תקופה", "סכום", "מטבע", "תאריך_יעד",
                   "פעולה", "חוזר", "בוצע", "מקור"],
    },
    "en": KEYS,
}

MESSAGES = {
    "he": {
        "no_home": "לא נמצאה תיקיית מוח. להריץ init, או להגדיר SEDER_HOME.",
        "bad_lang": "שפה לא נתמכת. אפשר he או en.",
    },
    "en": {
        "no_home": "No archive found. Run init, or set SEDER_HOME.",
        "bad_lang": "Unsupported language. Use he or en.",
    },
}


def _check(kind: str, lang: str) -> None:
    if kind not in KEYS:
        raise KeyError(f"unknown table: {kind}")
    if lang not in LANGS:
        raise KeyError(f"unknown lang: {lang}")


def header(kind: str, lang: str) -> list[str]:
    """Column names of a table in the given language."""
    _check(kind, lang)
    return list(HEADERS[lang][kind])


def to_row(kind: str, lang: str, rec: dict) -> list[str]:
    """Internal record -> list of cell strings in the table's column order."""
    _check(kind, lang)
    return ["" if rec.get(k) is None else str(rec.get(k)) for k in KEYS[kind]]


def from_row(kind: str, lang: str, row: dict) -> dict:
    """Row keyed by the language's header words -> record keyed by internal keys."""
    _check(kind, lang)
    return {k: row.get(h, "") for k, h in zip(KEYS[kind], HEADERS[lang][kind])}
