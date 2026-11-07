# Privacy: what leaves the computer, and how it is enforced

Read this when the person asks what Claude sees, wants to lock a folder, or when
`doctor` reports that Remote Control is on.

## Three levels per folder

| level | meaning | how it is enforced |
|---|---|---|
| `open` (default) | you may read and file | nothing to enforce |
| `ask` | a question before every file: "פתיחת הקובץ שולחת את התוכן ל-Anthropic. להמשיך?" | the plugin hook returns `ask` on Read/Glob/Grep; the person answers in Claude Code |
| `locked` | the model sees names only | the hook returns `deny`; intake files the document under a template name without reading it |

Secret files (`.env`, keys, passwords, tokens) are always denied.

Defaults for a new instance: everything open, every `בריאות` / `Health` /
`רפואי` / `Medical` folder on `ask`. The levels live in the instance's
`רגיש.json` / `sensitive.json`:

```
brain.py privacy list
brain.py privacy set "03_משפחה/דנה/בריאות" locked
brain.py privacy set "03_משפחה/דנה/בריאות" open
```

The hook needs to find the instance: it looks at `SEDER_HOME`, then `~/.seder/home`,
then around the current folder. The onboarding writes the pointer file so the hook
works from any folder.

## What leaves the computer

Everything the model reads is sent to Anthropic's servers to be processed, like any
other content in a Claude Code conversation. Seder does not add a server, a cloud or
a database of its own.

| action | what is sent |
|---|---|
| intake | the content of the files you read (not the held ones), the naming procedure and the profile |
| finding a document, step 1 | file names only (the index) |
| finding a document, step 2 | only the files the person approved |
| weekly review | ledger rows (type, amount, dates), never document content |
| a folder at `ask` | content only after a yes, per file |
| a folder at `locked` | never content; the template name is made locally |
| storage in the cloud | none beyond the conversation itself |

## Transcripts and Remote Control

Claude Code saves every conversation as a transcript on the person's own disk, so a
document read during intake is in that file. With Remote Control (phone access) the
conversation also passes through Anthropic's servers so the phone can show it.
`doctor` reports whether Remote Control is on; when it is and `remote_warning` in
`brain.json` is true, say once per session, in the instance language:

> הערה: Remote Control דולק, אז השיחה הזאת, כולל מסמכים שאני קורא, עוברת גם דרך השרתים
> של Anthropic כדי שהטלפון יראה אותה. אם זה לא רצוי למסמך מסוים, אפשר לעבוד עליו
> בשיחה מהמחשב, או לנעול את התיקייה שלו.

Recommend, do not nag: the person chose Remote Control for a reason. Two more things
worth saying when privacy comes up: the account's privacy settings have a switch for
whether conversations may be used to improve Claude, and `brain.py prune-transcripts`
(see `scripts`) removes old intake transcripts from the disk with the person's approval.

## Unattended runs

Optional modules (mail, phone folders, the phone site) run Claude without a person
watching. They must use the settings file `brain.py settings --headless` writes:
read only inside the root, deny on every `ask`/`locked` folder and every secret
pattern, no write tools, no connectors, a turn cap, no saved transcript. The quarantine
(`held`) is a local check that runs before any of this, with no model.

## What you never do

- Read a `held` file to "just name it".
- Write medical details into the profile, a summary, a ledger row or memory, even
  after the person approved opening the file. The index keeps the name and a
  sensitivity mark, nothing else.
- Keep a copy of a document outside the root (temp folders, uploads) once it is filed.
