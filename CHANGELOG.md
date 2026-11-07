# Changelog

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
