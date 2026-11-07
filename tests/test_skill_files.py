import json
import re
from pathlib import Path

SK = Path(__file__).parents[1] / "skills"
SKILLS = sorted(p.name for p in SK.iterdir() if (p / "SKILL.md").is_file())
assert "brain" in SKILLS


def frontmatter(skill):
    text = (SK / skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{skill}: no frontmatter"
    fields = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fields[k.strip()] = v.strip()
    return fields, text[m.end():]


def test_frontmatter_valid():
    for s in SKILLS:
        fields, _ = frontmatter(s)
        assert fields["name"] == s and re.fullmatch(r"[a-z0-9-]{1,64}", fields["name"])
        assert 10 <= len(fields["description"]) <= 1024, s
        assert "<" not in fields["description"] and ">" not in fields["description"]


def test_brain_description_has_hebrew_and_english_triggers():
    fields, _ = frontmatter("brain")
    d = fields["description"]
    for word in ("file", "תייק", "איפה", "archive", "הארון"):
        assert word in d, word


def test_skill_md_under_500_lines_and_references_exist():
    for s in SKILLS:
        _, body = frontmatter(s)
        assert len(body.splitlines()) <= 500, s
        for ref in re.findall(r"references/([a-z-]+\.md)", body):
            assert (SK / s / "references" / ref).exists(), f"{s}: {ref}"


def test_brain_references_present():
    for ref in ("intake", "naming", "tree-default", "privacy", "sources", "onboarding", "project"):
        p = SK / "brain" / "references" / f"{ref}.md"
        assert p.is_file() and p.stat().st_size > 400, ref


def test_brain_skill_points_at_every_cli_command_it_needs():
    _, body = frontmatter("brain")
    refs = " ".join((SK / "brain" / "references" / f).read_text(encoding="utf-8") for f in
                    ("intake.md", "onboarding.md", "naming.md", "project.md", "privacy.md"))
    text = body + refs
    for cmd in ("brain.py doctor", "brain.py init", "brain.py adopt", "brain.py inbox", "brain.py intake-apply",
                "brain.py namecheck", "brain.py privacy", "brain.py ledger", "brain.py project"):
        assert cmd in text, cmd


def test_intake_reference_carries_the_proposal_contract():
    text = (SK / "brain" / "references" / "intake.md").read_text(encoding="utf-8")
    for key in ('"pages"', '"rotate"', '"name"', '"folder"', '"new_folder"', '"sensitive"', '"skip"', '"ledger"', '"confidence"', '"duplicate"', '"readable"'):
        assert key in text, key
    assert "_proposal.json" in text and "held" in text and "suggested_name" in text


def test_no_personal_paths_in_skill_text():
    for p in (SK / "brain").rglob("*.md"):
        text = p.read_text(encoding="utf-8")
        assert "C:\\Users\\" not in text and "/Users/" not in text, p
