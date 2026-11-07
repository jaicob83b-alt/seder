# Architecture

## Two layers

**The engine** is this repository: a Claude Code plugin with two skills, one hook, a
Python package and tests. It holds no data about anyone.

**The instance** is a person's brain folder on their disk (for example
`Documents/00_המוח`), created by `init` or registered by `adopt`:

| file | holds |
|---|---|
| `brain.json` | language, owner, entities, the logical tree with its physical folders, enabled sources |
| `נוהל_שמות.md` / `naming.md` | the person's naming and routing procedure, generated from a template, editable |
| `מי_אני.md` / `about_me.md` | the person's profile, read before every proposal |
| `רגיש.json` / `sensitive.json` | privacy levels per folder, secret patterns, quarantine words |
| `אינדקס.csv` / `index.csv` | one row per document: path, branch, subfolder, name, date, type, size, sensitivity, hash |
| `פנקס.csv` / `ledger.csv` | one structured row per filed document: type, counterparty, whose, period, amount, due, action, recurring, done |
| `יומן_קליטה.csv` / `intake_log.csv` | every move with its undo command |
| `_נכנס` / `_inbox` | where documents wait; `_proposal.json`, `_out`, `_done`, `_skipped` inside |

Every system file name and every CSV header comes from one mapping in `names.py`,
keyed by `lang`. Hebrew reproduces the owner's original archive exactly, so the tools
that already read those files keep working.

## Logical tree, physical folders

`brain.json` lists branches (`id`, `num`, `name`, `physical`, `privacy`, `handoff`,
`subfolders`). `tree.resolve` turns `01_כספים/בנק`, `כספים/בנק` or `01/בנק` into
`<root>/<physical>/בנק`, so an adopted archive keeps its folder names and a branch
can later be renamed on disk by changing one field. `tree.check_target` rejects
anything outside the root, inside the brain folder, or with unsafe path segments.

A branch with `handoff` sends its documents to another engine's inbox, in the
original format when `originals` is true. That is how a separate finance tool keeps
owning its own intake.

## Who does what

| | Claude, in the conversation | the scripts |
|---|---|---|
| reads | documents that are not held, the naming procedure, the profile | names, sizes, hashes, locally extracted text |
| decides | nothing; proposes names, folders, reasons, ledger fields | nothing; validates and refuses |
| writes | `_proposal.json`, the table, the answer | PDFs, moves, log, index, ledger, review page |

The person says yes. Only then does `intake-apply` run, and only for the approved rows.

## Modules (`skills/brain/scripts/seder/`)

| module | responsibility |
|---|---|
| `names` | file names, headers, messages per language |
| `config` | `brain.json`, finding the instance (`SEDER_HOME`, `~/.seder/home`, cwd) |
| `tree` | default tree, add-ons, resolve, target checks, hand-off |
| `sensitive` | privacy levels, secrets, quarantine words, deny rules, template names |
| `pdf` | build one PDF from photos and PDFs, page count, first-page text |
| `index` | the names-only index, hashes, duplicates |
| `filing` | name checks, the move with hash + log + undo, free names |
| `ledger` | rows, name backfill, recurring gaps, open items, done |
| `inbox` | listing with duplicates and quarantine, the proposal contract, apply |
| `init` / `doctor` | create, adopt, scan, environment checks |
| `project` | project cards, dormant projects, archive on request |
| `studies` | course import with topic names, studies index, relevant lessons |
| `prune` | moving old intake transcripts out of the active folder |

`brain.py` is the only entry point: every command prints one JSON line.
`skills/brain-review/scripts/review.py` imports the same package and renders the
review page from the index, the ledger and the log.

## Privacy enforcement

1. `hooks/hooks.json` registers `hooks/seder_hook.py` on `PreToolUse` for Read, Glob
   and Grep. It answers `ask` for folders at level `ask`, `deny` for `locked` folders
   and secret files, and stays silent otherwise or on any error.
2. `sensitive.write_headless_settings` produces the allow/deny settings for unattended
   runs: read only inside the root, every sensitive folder and secret pattern denied,
   no write tools.
3. `inbox.list_inbox` marks medical-looking files `held` from local signals only, with
   a template name made locally; `apply` files a locked document without a ledger row.

## Tests

`tests/` run against throwaway instances in a temp folder (`conftest.py`), with
synthetic PDFs and images. `test_no_private_data.py` scans the repository for the
owner's private terms from a git-ignored list. The live archive is never touched by
the tests.
