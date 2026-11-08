# Seder

**A private document archive for Claude Code.** Your bills, payslips, contracts,
letters and scans in a plain folder tree on your own disk. Claude reads a document,
proposes a name and a folder, and a script files it after you say yes. No server, no
cloud, no database. Hebrew and English.

*סדר במסמכים, סדר בראש. The Hebrew chapter is in [README.he.md](README.he.md).*

## The person approves everything

Nothing moves without a yes. Every proposal is a table: name, folder, why. The scripts
then do what must come out the same every time: build the PDF, move without
overwriting, verify the hash, write a log row with an undo command, update the index
and the ledger. Claude proposes; you decide; the script executes.

## Install

```
claude plugin marketplace add jaicob83b-alt/seder
claude plugin install seder@seder
```

From a local clone instead: `claude plugin marketplace add C:\path\to\seder` and the
same install line. Update later with `claude plugin update seder@seder`.

Then open Claude Code and say **"set up my archive"** (or in Hebrew: **"תקים לי ארכיון"**).
The first meeting:

1. Checks your machine and installs what is missing, after a yes.
2. Asks what you want to call the archive ("Seder", "Dana's cabinet", anything; renamable).
3. Asks to look, then scans Documents, Downloads, Desktop, OneDrive and Google Drive by
   **names only**: no file is opened or moved.
4. Shows what it found: how many documents, where, and about what ("38 about motorcycles").
5. Interviews you from those findings, one question at a time.
6. Proposes a **tree tailored to you** (a rider gets a wider vehicles branch), as a table;
   nothing is created until you say yes.
7. Asks for a first document.

A folder you already keep in order is adopted as it is, without moving a file.

## From the phone

**"Connect my phone"**: Tailscale on the computer and the phone (a private network of
your own devices), then `brain.py site`. The phone opens a page named after your
archive: approve or reject each proposed document, **photograph a document straight
into the inbox**, search by name, and the weekly review. The site listens only on the
Tailscale address, never on Wi-Fi or the internet, and never calls a model.

Documents from WhatsApp and the phone's Downloads arrive by themselves through
Syncthing (copied phone to computer); the PC's Downloads through `brain.py sources add`.

Requirements: Python 3.11+, `pymupdf`, `Pillow`, `openpyxl`
(`python -m pip install pymupdf Pillow openpyxl`), Claude Code.

## What a day looks like

1. A photo of a letter arrives (sent to the chat, dropped into the inbox folder, or
   pulled by an optional source).
2. "File what arrived" → a table: `2026-09_חשבון חשמל - דנה.pdf` → `01_כספים/חשבונות שוטפים`,
   because it is September's electricity bill, 412.30, due 20.10.
3. "Yes" → filed, logged, indexed, and a ledger row with the amount and the due date.
4. "Where is the August bill?" → the path, from names alone.
5. Once a week, "give me a review" → a page: what came in, what waits, which recurring
   documents are missing a month, what is open and overdue.

## What you set up yourself

The onboarding asks for: the root folder, the language, your name, the people and
businesses that appear in your documents, the add-ons you want (dev projects,
studies, pets...), which folders should ask before opening or stay locked, and which
sources to connect. Sources beyond the inbox folder and the chat (Gmail, WhatsApp via
Syncthing, a phone site via Tailscale) are optional and are not bundled in v0.1.

## Privacy

| action | what leaves your computer |
|---|---|
| filing | the content of the files Claude reads (never the quarantined ones) |
| finding, step 1 | file names only |
| finding, step 2 | only the files you approved |
| weekly review | ledger rows, never content |
| folder at `ask` | content only after a yes, per file |
| folder at `locked` | never content |

Three privacy levels per folder, enforced by a `PreToolUse` hook, not by a prompt.
Quarantine for medical-looking files before any model sees them. Deny rules for
unattended runs. No secrets in the repository, by test. The full page:
[docs/privacy.md](docs/privacy.md).

## The standard tree

| | | |
|---|---|---|
| 00 | Brain | the system: settings, naming, index, ledger, log, inbox |
| 01 | Finance | bank · credit cards · loans and mortgage · savings and pension · tax · income |
| 02 | Home | one folder per property |
| 03 | Family | one folder per person; Health is locked (names only) |
| 04 | Vehicles | one folder per vehicle |
| 05 | Business | one folder per business |
| 06 | Projects and events | one folder per project with a card |
| 99 | Archive | what is over |

Add-ons: 07 Dev projects, 08 Studies, pets, media, community, military, immigration.
The principle: **a document goes to the thing it is about, not to its document type.**
An existing archive is adopted as it is; the standard mapping is written as a proposal.

## Inside

```
skills/brain/            the skill: SKILL.md, references/, assets/, scripts/brain.py + seder/
skills/brain-review/     the weekly review skill and page
hooks/                   the privacy hook (PreToolUse on Read, Glob, Grep)
tests/                   pytest, synthetic documents, no personal data
docs/                    privacy.md, architecture.md, homework-15.md
```

Development: `python -m pip install pytest` then `python -m pytest`. See
[docs/architecture.md](docs/architecture.md).

## Roadmap

- v0.1 (this): the engine, both skills, the hook, onboarding, adoption of an existing archive.
- next: bundled optional sources (mail, phone folders, the phone site) for Mac and Linux
  too; a dry-run reorganisation of an adopted archive into the standard tree; a 60-second demo.

## License

MIT.
