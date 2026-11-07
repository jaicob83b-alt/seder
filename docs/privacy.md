# Privacy: what Seder sends, keeps and never touches

Seder is a folder tree on your own disk plus a Claude Code skill. There is no Seder
server, no account, no cloud copy of your documents. The only place your documents
go is the one every Claude Code conversation already goes: Anthropic's API, to be
processed by the model. This page says exactly when that happens, and what stops it.

## What leaves the computer

| action | what is sent to Anthropic |
|---|---|
| filing documents from the inbox or from photos you sent | the content of the files Claude reads (never the quarantined ones), your naming procedure and your profile |
| finding a document, step 1 | file names only (the index) |
| finding a document, step 2 | only the files you approved opening |
| the weekly review | ledger rows: document type, amount, dates. Never document content |
| a folder at level `ask` | content only after you answered yes, per file |
| a folder at level `locked` | never content. The template name is made locally |
| storage in the cloud | none, beyond the conversation itself |

## Three privacy levels per folder

- **open** (default): Claude may read and file.
- **ask**: before every file, Claude Code stops with "Opening this file sends its content to Anthropic. Continue?".
- **locked**: Claude sees names only. A document that belongs in a locked folder is
  filed under a template name (`2026-09_רפואי - דנה.pdf`) that a local script builds
  from the file's own text or date; you confirm the name, nobody reads the content.

Defaults for a new archive: everything open, every Health (`בריאות`) folder on ask.

```
brain.py privacy list
brain.py privacy set "03_משפחה/דנה/בריאות" locked
```

## How it is enforced (not promised)

1. **A hook, not a prompt.** The plugin registers a `PreToolUse` hook on Read, Glob
   and Grep. It compares the path with your levels file and answers `ask` or `deny`
   before the tool runs. Claude cannot talk its way past it. Secret files (`.env`,
   keys, passwords, tokens) are always denied.
2. **Deny rules for unattended runs.** Anything that runs Claude without you watching
   (a mail puller, a phone site) must use the settings `brain.py settings --headless`
   writes: read only inside the root, deny on every ask/locked folder and secret
   pattern, no write tools, no connectors, a turn cap, no saved transcript.
3. **Quarantine before any model.** The inbox listing is a local check: a medical
   sender, a medical word in the file name, or two medical words in locally extracted
   text marks the file `held`. Held files are proposed by template name and never opened.
4. **No secrets in the skill.** Nothing in this repository holds a password, a token
   or a personal path. A test fails the build if one slips in. Mail credentials, when
   you enable mail, live in the operating system's credential store.
5. **No overwrite, no delete.** Every move checks the file's hash before and after,
   writes a log row with the undo command, and refuses an existing target. Archiving
   a project, pruning transcripts: moves, never deletes.

## Transcripts and Remote Control

Claude Code saves every conversation as a transcript file on your disk
(`~/.claude/projects/...`). A document Claude read during filing is in that file.
With Remote Control (seeing the conversation on your phone), the conversation also
passes through Anthropic's servers so the phone can show it.

What this means in practice:

- For documents you consider sensitive, set the folder to `ask` or `locked`, or file
  them from a conversation on the computer with Remote Control off.
- `brain.py prune-transcripts --older-days 7` lists the intake transcripts older than
  a week; with `--go` it moves them into `<brain folder>/_ארכיון_תמלילים`. Nothing
  is deleted; you empty that folder yourself.
- Your Anthropic account has a privacy setting that decides whether conversations
  may be used to improve Claude. Check it once.

## What Claude never does with your archive

- Open a `held` or `locked` file "just to name it".
- Write medical details into your profile, into a summary, into a ledger row or into
  memory, even after you approved opening the file.
- Do money math across documents. Sums belong to your finance tool.
- Move, rename or delete a file outside the scripts, which log every move.
