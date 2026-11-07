---
name: brain-review
description: The weekly review of a Seder document archive, as a page the person opens - what came in this week, what waits in the inbox, which recurring documents (bills, payslips, statements) are missing a period, which actions are open and overdue, and which projects went quiet. Use this skill when the user asks for a review, a summary of their archive, what they are missing, what is open or overdue, or what arrived this week, and right after the brain skill filed documents when they asked to "file and then review". Hebrew triggers - סקירה שבועית, מה חסר לי, מה פתוח, מה נכנס השבוע, תן לי סקירה. English triggers - weekly review, what am I missing, what is open, what arrived this week, review my archive.
---

# Seder: the `brain-review` skill

The review is built from names and ledger rows only. No document content is read,
so it is safe to run at any time, on any archive, including locked folders.

## Run it

```
python -I -X utf8 "<skill dir>/scripts/review.py" [--home DIR] [--today YYYY-MM-DD] [--no-open]
```

`<skill dir>` is the folder holding this SKILL.md (`${CLAUDE_PLUGIN_ROOT}/skills/brain-review`
as a plugin). The script finds the instance like the `brain` skill does (`SEDER_HOME`,
`~/.seder/home`, or a `brain.json` around the current folder), writes the page as
`סקירה_שבועית.html` / `weekly_review.html` in the brain folder, opens it in the
browser, and prints one JSON line:

```
{"ok": true, "file": "...", "summary": {"filed": 2, "pending_inbox": 1, "gaps": 1, "open": 2, "archive_candidates": 0, "undated": 1, "no_period": 1}}
```

Use `--no-open` when the person is on the phone or asked for text only; then give the
file path.

## Then write the paragraph the page cannot

Read the JSON and write, in the instance language, one short paragraph titled
"על מה לשים דגש" / "What to focus on": the most consequential two or three items,
in order. A missing month of a bill, an overdue action, a quiet project. Say what the
person can do about each in one clause ("send me the September bill when it arrives",
"mark it done with ledger done"). Use only the numbers and names the script gave;
do not open documents to add detail, and do not do money math.

When the summary is all zeros, say that in one line and stop.

## Chaining

"קלוט את מה שהגיע ואז תן לי סקירה" / "file what arrived, then review": run the
`brain` skill's intake first, wait for the person's approval and the apply step,
then run this script. The review reads the log and ledger the intake just updated.

## What this skill does not do

It changes nothing. Archiving a quiet project (`brain.py project archive`) and
marking an action done (`brain.py ledger done`) are the `brain` skill's commands and
run only after the person says yes to the specific item. There is no action with an
effect outside the computer here; if one is ever added (a reminder, a message), it gets
`disable-model-invocation: true` so that only the person can start it.
