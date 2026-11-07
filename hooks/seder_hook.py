"""PreToolUse hook: stop before Claude reads, globs or greps a sensitive path.

Reads the hook JSON from stdin. For a folder at level `ask` it answers
"ask" (Claude Code pauses and asks the person); for `locked` folders and
secret files it answers "deny". Anything else, including any error, is
silence with exit 0, which means "continue".
"""
import json
import sys
from pathlib import Path

MESSAGES = {
    "he": {
        "ask": "הקובץ בתיקייה רגישה. פתיחה שולחת את התוכן ל-Anthropic. להמשיך?",
        "locked": "התיקייה נעולה: המודל רואה רק שמות. לשנות: brain.py privacy set <תיקייה> ask",
        "secret": "קובץ סודות לא נקרא.",
    },
    "en": {
        "ask": "This file is in a sensitive folder. Opening it sends its content to Anthropic. Continue?",
        "locked": "This folder is locked: the model sees names only. To change: brain.py privacy set <folder> ask",
        "secret": "Secret files are never read.",
    },
}


def answer(decision: str, reason: str) -> None:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    sys.stdout.flush()


def main() -> None:
    data = json.loads(sys.stdin.read())
    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}
    if tool not in ("Read", "Glob", "Grep"):
        return
    target = tool_input.get("file_path") if tool == "Read" else tool_input.get("path")
    if not target:
        return
    target = Path(str(target))
    if not target.is_absolute():
        target = Path.cwd() / target

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "brain" / "scripts"))
    from seder import config, sensitive

    home = config.find_home(cwd=Path.cwd())
    if home is None:
        return
    cfg = config.Config.load(home)
    msgs = MESSAGES.get(cfg.lang, MESSAGES["en"])
    if sensitive.is_secret(str(target)):
        answer("deny", msgs["secret"])
        return
    lv = sensitive.level(cfg, str(target))
    if lv == "locked":
        answer("deny", msgs["locked"])
    elif lv == "ask":
        answer("ask", msgs["ask"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
