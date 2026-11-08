# Changelog

## 0.2.0 - 2026-11-08 (first outside tester)

- Onboarding v2: the person names the archive (`init --name`, `adopt --name`,
  `rename NAME [--folder]`); the name appears on the review page.
- `discover`: with a yes, a names-only first look at Documents, Downloads, Desktop and
  cloud-sync folders: documents per place, biggest folders, topics recognised in names
  (`assets/topics.json`), organised archives and existing instances, and a suggested
  plan. Never prints a file name; medical topics are a count only.
- Tailored tree: `tree.build` applies a plan (rename, subfolders, subfolders_add, drop,
  items, extra branches, add-ons); `tree-preview` shows it; `init --plan` creates it.
- The onboarding reference follows the new order: machine, name, look, findings,
  interview from findings, tailored tree, create or adopt, first document.
- `allowed-tools` in both skills' frontmatter.

## 0.1.0 - 2026-11-11

First release, built for lesson 15 of the AI Dev course.

- `brain` skill: onboarding (doctor, init, adopt, scan), intake from an inbox with
  duplicates and quarantine, a proposal contract, approval-first filing with hash,
  log and undo, names-only index, ledger with name backfill, recurring gaps and open
  actions, project cards, studies import with topic names.
- `brain-review` skill: the weekly review page (what came in, what waits, gaps, open
  actions, dormant projects, small things).
- Privacy: three levels per folder (open / ask / locked), a PreToolUse hook, secret
  patterns, quarantine for medical-looking files, headless deny settings, transcript
  pruning, the privacy page.
- Health-named folders (`בריאות` / `Health` / `רפואי` / `Medical`) are locked by default;
  `ask` is an explicit choice per folder.
- Hebrew and English: file names, CSV headers, templates and messages per instance language.
- An existing archive is adopted as it is; the standard tree is proposed, never applied.
