import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parents[1] / "hooks" / "seder_hook.py"


def run_hook(stdin: str, home):
    env = {**os.environ, "SEDER_HOME": str(home)}
    return subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input=stdin,
                          capture_output=True, text=True, encoding="utf-8", env=env)


def decision(r):
    return json.loads(r.stdout)["hookSpecificOutput"]


def test_hooks_json_points_at_the_hook():
    d = json.loads((HOOK.parent / "hooks.json").read_text(encoding="utf-8"))
    entry = d["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "Read|Glob|Grep"
    assert "${CLAUDE_PLUGIN_ROOT}/hooks/seder_hook.py" in entry["hooks"][0]["command"]


def test_asks_on_sensitive_read(home):
    p = str(home.parent / "03_משפחה" / "דנה" / "בריאות" / "a.pdf")
    r = run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": p}}), home)
    out = decision(r)
    assert r.returncode == 0 and out["permissionDecision"] == "ask" and "Anthropic" in out["permissionDecisionReason"]
    assert out["hookEventName"] == "PreToolUse"


def test_silent_on_normal_read(home):
    p = str(home.parent / "01_כספים" / "בנק" / "a.pdf")
    r = run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": p}}), home)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_silent_on_garbage(home):
    for s in ["", "{not json", json.dumps({"tool_name": "Read", "tool_input": {}}), json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x"}})]:
        r = run_hook(s, home)
        assert r.returncode == 0 and r.stdout.strip() == ""


def test_silent_without_instance(tmp_path):
    r = run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "a.pdf")}}), tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_asks_on_glob_into_sensitive(home):
    r = run_hook(json.dumps({"tool_name": "Glob", "tool_input": {"pattern": "**/*.pdf", "path": str(home.parent / "03_משפחה" / "דנה" / "בריאות")}}), home)
    assert decision(r)["permissionDecision"] == "ask"


def test_asks_on_grep_into_sensitive(home):
    r = run_hook(json.dumps({"tool_name": "Grep", "tool_input": {"pattern": "x", "path": str(home.parent / "03_משפחה" / "דנה" / "בריאות")}}), home)
    assert decision(r)["permissionDecision"] == "ask"


def test_denies_on_locked_read(home):
    from seder import config, sensitive
    sensitive.set_level(config.Config.load(home), "03_משפחה/דנה/בריאות", "locked")
    p = str(home.parent / "03_משפחה" / "דנה" / "בריאות" / "a.pdf")
    out = decision(run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": p}}), home))
    assert out["permissionDecision"] == "deny" and "privacy set" in out["permissionDecisionReason"]


def test_denies_secret_file(home):
    p = str(home.parent / "01_כספים" / ".env")
    out = decision(run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": p}}), home))
    assert out["permissionDecision"] == "deny"


def test_english_reason(home_en):
    p = str(home_en.parent / "03_Family" / "Dana" / "Health" / "a.pdf")
    out = decision(run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": p}}), home_en))
    assert out["permissionDecision"] == "ask" and out["permissionDecisionReason"].startswith("This file")
