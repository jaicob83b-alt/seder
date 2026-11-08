---
name: brain
description: Seder, a private document archive on the person's own disk. A standard folder tree, approval-first filing of documents from an inbox or from photos sent to the chat, finding documents by name, project cards, and per-folder privacy levels. Use this skill whenever the user wants to file, sort, name, archive or find personal or household documents (bills, payslips, contracts, letters, scans, PDFs, photos of paperwork), set up or adopt a document archive, open a project card, or asks what their archive sends to Anthropic, even when they never say "Seder". Hebrew triggers - תייק, תסדר את המסמכים, איפה החשבון, הארון, קליטה, מה הגיע, כרטיס פרויקט, תפתח פרויקט, המוח. English triggers - file this, sort my documents, where is the electricity bill, what arrived, set up my archive, new project card.
allowed-tools: Read, Glob, Grep
---

# Seder: the `brain` skill

Seder keeps a person's documents in a plain folder tree on their own disk, with no
server and no cloud. You read and propose; a script moves. The person decides.

## The one rule: propose, never move

A file moves only after the person says yes to a concrete proposal: a name, a
folder and a reason, shown in a table. The scripts then do the moving, because
they are the part that must come out the same every time: no overwrite, no
delete, a hash check before and after, a log row with an undo command, an index
and ledger update. Never move, rename or delete a document with Bash, `mv`,
`Move-Item` or the Write tool. A move without the script has no log and no undo,
and the person loses track of their own paperwork.

## Find the instance first

```
python -I -X utf8 "<skill dir>/scripts/brain.py" doctor
```

`<skill dir>` is the folder that holds this SKILL.md (`${CLAUDE_PLUGIN_ROOT}/skills/brain`
when installed as a plugin). Every command prints exactly one JSON line:
`{"ok": true, ...}` or `{"ok": false, "error": "..."}`.

- `home` in the doctor output is the instance folder (the one with `brain.json`).
  It is found through `SEDER_HOME`, the pointer file `~/.seder/home`, or a
  `brain.json` in or around the current folder. Pass `--home DIR` when it is elsewhere.
- `home` is `null`: there is no archive yet. Go to `references/onboarding.md`.
- Read the instance's own files before proposing anything: `brain.json` (language,
  owner, entities, the tree and its physical folders), the naming procedure
  (`נוהל_שמות.md` / `naming.md`) and the profile (`מי_אני.md` / `about_me.md`).
  They are the person's rules and win over the defaults in `references/`.

## Route by request

| The person wants | Read | Then |
|---|---|---|
| to file what arrived, photos sent to the chat, "תייק", "מה הגיע", "file this" | `references/intake.md` | inbox -> proposal -> yes -> intake-apply |
| to find a document, "איפה החשבון", "where is" | `references/naming.md` (retrieval section) | names first, content only with consent |
| a new archive, or to register an existing folder | `references/onboarding.md` | doctor, name, discover, interview, tree-preview, init or adopt |
| a project card, "תפתח פרויקט", "new project" | `references/project.md` | `brain.py project new` |
| to use the phone, connect WhatsApp or Downloads | `references/sources.md` | Tailscale and the site, Syncthing, watched folders; each after a yes |
| to know what leaves the computer, lock a folder | `references/privacy.md` | `brain.py privacy` |
| a weekly review, "מה חסר לי", "what am I missing" | the `brain-review` skill | run it after intake when asked "קלוט ואז סקירה" |
| the standard tree, where a kind of document goes | `references/tree-default.md` | the document goes to the thing it is about |

## The CLI at a glance

| Command | Does |
|---|---|
| `brain.py doctor` | environment checks, where the instance is |
| `brain.py init --home DIR --root DIR --lang he\|en --owner NAME --entities a,b --name NAME --plan FILE` | new instance with a tailored tree |
| `brain.py adopt --home DIR --root DIR [--name NAME]` | register an existing archive as it is; writes a proposed tree, moves nothing |
| `brain.py discover [--roots DIR...]` | before an archive exists, after a yes: where documents live and which topics, counts and folder names only |
| `brain.py tree-preview --plan FILE` | the tailored tree init would create; writes nothing |
| `brain.py rename NAME [--folder]` | the archive's own name; `--folder` also renames the brain folder |
| `brain.py site [--check] [--autostart install\|remove\|status]` | the phone site on the Tailscale address (or 127.0.0.1): approve, snap, search, review |
| `brain.py sources list\|add PATH --label L\|remove PATH` and `brain.py pull` | watched folders (PC Downloads, Syncthing folders from the phone) copied into the inbox |
| `brain.py scan` | folders to depth 2 with counts, names only |
| `brain.py inbox` | what is waiting: size, hash, duplicates, quarantine, suggested names |
| `brain.py intake-apply --approve 1,3 --name 2=NAME --folder 3=FOLDER --mkdir 3` | file the approved rows of `_proposal.json` |
| `brain.py namecheck FOLDER NAME --src PATH` | is the name taken, is it the same file, which name is free |
| `brain.py file SRC FOLDER NAME --why TEXT [--mkdir] [--original PATH]` | move one approved document |
| `brain.py pdf OUT PAGE... --rotate 0,90` | join photos and PDFs into one PDF |
| `brain.py index [--rebuild \| --update REL]` | the names-only index |
| `brain.py ledger add\|backfill\|gaps\|open\|done` | the structured rows behind the weekly review |
| `brain.py privacy list\|set FOLDER open\|ask\|locked` | per-folder privacy levels |
| `brain.py project new\|list\|archive-candidates\|archive` | project cards |

## Language and names

Answer in the instance language (`lang` in `brain.json`): Hebrew archive, Hebrew
answers and Hebrew file names. The name format is `YYYY-MM_type - whose.ext`, where
the date is the one written inside the document, never the download date. The
"whose" comes from `entities` in `brain.json`. Details and examples: `references/naming.md`.

## Privacy, in short

Every folder has a level: `open` (you may read), `ask` (a question before every
file), `locked` (names only). The plugin hook enforces this on Read, Glob and Grep;
the inbox listing marks files that look medical as `held`, with a template name you
propose without reading them. Whatever you do read goes through Anthropic's servers
to be processed, like anything else in the conversation, so say so when it matters:
`references/privacy.md` has the table of what leaves the computer and the wording
for people who use Remote Control. Never write medical details into the profile,
the summary field, the ledger or memory, even after an approved opening.

## Common mistakes

- Moving a file with the shell instead of `brain.py file` or `intake-apply`: no log, no undo.
- Reading a `held` file "just to name it". Propose the suggested template name and ask whose it is.
- Creating folders up front. A subfolder appears with its first document, after a yes.
- Taking the date from the file name or the download time instead of the document's own date.
- Doing money math. The archive points at documents; sums come from the person's finance tool.
- Filing a document about a person's car under "insurance". It goes to the car.
