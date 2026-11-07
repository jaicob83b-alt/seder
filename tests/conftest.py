"""Test setup: make the `seder` package importable, and provide throwaway instances.

`home` is a Hebrew instance (what Yaakov's archive looks like after init),
`home_en` the same in English. Both live under pytest's tmp_path.
"""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "brain" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TREES = {
    "he": [
        {"id": "brain", "num": "00", "name": "המוח", "physical": "00_המוח", "privacy": "open", "handoff": None, "subfolders": []},
        {"id": "finance", "num": "01", "name": "כספים", "physical": "01_כספים", "privacy": "open", "handoff": None,
         "subfolders": ["בנק", "כרטיסי אשראי", "הלוואות ומשכנתא", "חיסכון ופנסיה", "מס וביטוח לאומי", "הכנסות ותלושים", "היסטוריה"]},
        {"id": "home", "num": "02", "name": "בית", "physical": "02_בית", "privacy": "open", "handoff": None,
         "subfolders": ["רכישה או שכירות", "בנייה ושיפוצים", "חשבונות שוטפים", "ביטוח דירה", "ועד בית"]},
        {"id": "family", "num": "03", "name": "משפחה", "physical": "03_משפחה", "privacy": "open", "handoff": None,
         "subfolders": ["תעודות ורישיונות", "בריאות", "חינוך ולימודים", "זכויות וביטוח לאומי", "ביטוח וחיסכון", "עבודה", "שונות"]},
    ],
    "en": [
        {"id": "brain", "num": "00", "name": "Brain", "physical": "00_Brain", "privacy": "open", "handoff": None, "subfolders": []},
        {"id": "finance", "num": "01", "name": "Finance", "physical": "01_Finance", "privacy": "open", "handoff": None,
         "subfolders": ["Bank", "Credit cards", "Loans and mortgage", "Savings and pension", "Tax and social security", "Income and payslips", "History"]},
        {"id": "home", "num": "02", "name": "Home", "physical": "02_Home", "privacy": "open", "handoff": None,
         "subfolders": ["Purchase or rent", "Building and renovation", "Utilities", "Home insurance", "Building committee"]},
        {"id": "family", "num": "03", "name": "Family", "physical": "03_Family", "privacy": "open", "handoff": None,
         "subfolders": ["IDs and licences", "Health", "Education", "Benefits and social security", "Insurance and savings", "Work", "Misc"]},
    ],
}

# physical folders the fixture creates in the root (relative paths)
FOLDERS = {
    "he": ["01_כספים/בנק", "02_בית", "03_משפחה/דנה/בריאות"],
    "en": ["01_Finance/Bank", "02_Home", "03_Family/Dana/Health"],
}

INBOX = {"he": "_נכנס", "en": "_inbox"}


def make_instance(tmp_path: Path, lang: str) -> Path:
    root = tmp_path / "root"
    for rel in FOLDERS[lang]:
        (root / rel).mkdir(parents=True, exist_ok=True)
    home = root / TREES[lang][0]["physical"]
    (home / INBOX[lang]).mkdir(parents=True)
    brain = {
        "version": 1,
        "lang": lang,
        "owner": "",
        "root": str(root),
        "entities": ["דנה", "יוסי"] if lang == "he" else ["Dana", "Yossi"],
        "tree": TREES[lang],
        "sources": {"inbox": True, "gmail": False, "whatsapp": False, "downloads": False, "site": False},
        "remote_warning": True,
    }
    (home / "brain.json").write_text(json.dumps(brain, ensure_ascii=False, indent=1), encoding="utf-8")
    return home


@pytest.fixture
def home(tmp_path):
    return make_instance(tmp_path, "he")


@pytest.fixture
def home_en(tmp_path):
    return make_instance(tmp_path, "en")
