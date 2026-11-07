"""Guard: nothing personal leaks into the repository.

`tests/private_terms.txt` is git-ignored and holds the owner's private terms
(user name, host names, addresses, family and business names). The test is
skipped when the file is absent, so contributors without it are unaffected.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
TERMS = ROOT / "tests" / "private_terms.txt"
SCANNED = {".py", ".md", ".json", ".html", ".txt", ".toml"}
SKIP_DIRS = {".git", ".superpowers", "__pycache__", ".pytest_cache"}
SKIP_PATHS = {Path("docs") / "superpowers"}  # internal planning docs, git-ignored


@pytest.mark.skipif(not TERMS.exists(), reason="private terms file not present")
def test_repo_has_no_private_terms():
    terms = [t.strip() for t in TERMS.read_text(encoding="utf-8").splitlines() if t.strip() and not t.startswith("#")]
    hits = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p == TERMS or p.suffix not in SCANNED:
            continue
        rel = p.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts) or any(rel.is_relative_to(s) for s in SKIP_PATHS):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{rel}: {t}" for t in terms if t in text]
    assert hits == []
