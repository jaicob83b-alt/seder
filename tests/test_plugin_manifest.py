import json
import re
from pathlib import Path

import seder

ROOT = Path(__file__).parents[1]


def test_plugin_json_shape_and_version():
    d = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert d["name"] == "seder" and d["version"] == seder.__version__ and d["license"] == "MIT"
    assert d["description"] and "author" in d and d["repository"].startswith("https://github.com/")
    assert "privacy" in d["keywords"]


def test_marketplace_json_points_at_this_repo():
    d = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert d["name"] == "seder" and d["owner"]["name"]
    p = d["plugins"][0]
    assert p["name"] == "seder" and p["source"] == "./" and p["version"] == seder.__version__ and p["description"]


def test_hooks_manifest_and_skills_are_where_the_plugin_expects():
    assert (ROOT / "hooks" / "hooks.json").is_file()
    assert (ROOT / "skills" / "brain" / "SKILL.md").is_file() and (ROOT / "skills" / "brain-review" / "SKILL.md").is_file()


def test_readme_has_install_lines_and_hebrew_chapter():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "claude plugin marketplace add" in text and "claude plugin install seder@seder" in text
    assert "README.he.md" in text and "docs/privacy.md" in text and "approve" in text.lower()
    he = (ROOT / "README.he.md").read_text(encoding="utf-8")
    assert "סדר" in he and "claude plugin install seder@seder" in he


def test_changelog_has_current_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## \[?{re.escape(seder.__version__)}\]?", text, re.M)


def test_homework_doc_has_ten_questions():
    text = (ROOT / "docs" / "homework-15.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## \d+\.", text, re.M)) == 10
