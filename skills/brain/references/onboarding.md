# Onboarding: a new archive, or an existing one

Read this when `doctor` reports `home: null`, or when the person asks to set up,
install or connect their archive. One question at a time, in the person's language.
Install nothing and move nothing without a yes.

## 1. Check the machine

`python -I -X utf8 "<skill dir>/scripts/brain.py" doctor`

Explain the checks that are not ok. Required ones (Python, pymupdf, Pillow,
openpyxl, Claude Code, git) block intake; offer the `fix` command and run it only
after a yes. Optional ones (Tailscale, Syncthing, Office or LibreOffice, Tesseract)
are mentioned only when the matching source comes up. If `remote_control` is on,
say the Remote Control sentence from `privacy.md` once.

## 2. New archive or existing folder?

- The person already has a folder of documents (numbered folders, a previous system):
  **adopt**. Nothing is renamed or moved.
- Nothing organised yet: **init** with the standard tree.

## 3. The questions (one per message)

1. **Where do the documents live?** The root folder (for example the Documents folder).
   The brain folder is created inside it: `00_המוח` (Hebrew) or `00_Brain` (English).
2. **Which language?** `he` or `en`. It sets the interface, the file names of the
   system files, the CSV headers and the default folder names.
3. **What is your name?** The owner, as it should appear in document names.
4. **Who else, and which businesses?** People in the household, parents, a company.
   These become `entities`, the allowed values of "whose" in names. Spelling matters.
5. **Add-ons?** Offer only what fits what they said: dev projects (07), studies (08),
   pets, media, community, military, immigration.
6. **Privacy.** "אילו תיקיות ישאלו לפני פתיחה, ואילו נעולות? ברירת המחדל: הכל פתוח,
   ותיקיות בריאות שואלות." Apply the answer with `brain.py privacy set`.
7. **Sources.** The checklist from `sources.md`. Record the yes/no flags in `brain.json`.

## 4. Create or adopt

New:
```
brain.py init --home "<root>/00_המוח" --root "<root>" --lang he --owner "<name>" --entities "a,b" --addons dev_projects,studies
```
Existing:
```
brain.py adopt --home "<existing brain folder>" --root "<root>"
```
`adopt` registers every top-level folder as a branch with its current name, keeps the
existing index, log and naming files byte for byte, marks medical-looking folders as
`ask`, detects a hand-off inbox (`_inbox` inside a branch), and writes
`עץ_מוצע.md` / `proposed_tree.md`: for each folder, where it would sit in the
standard tree. Show that table and say that it is a proposal for a later, separate
reorganisation with a dry run. Nothing moves now.

If `adopt` says an instance already exists, it was done before; just run `doctor`.

## 5. Make the hook work everywhere

The privacy hook finds the instance through `SEDER_HOME` or the pointer file
`~/.seder/home`. Offer to write the pointer (one line, the home folder's path) with
the Write tool, after a yes. Without it, the hook protects only conversations that
run inside the root.

## 6. First light

- `brain.py index --rebuild` (names only; say how many documents it found).
- For an adopted archive, `brain.py ledger backfill` turns the existing names into
  ledger rows, so the first weekly review already shows recurring documents and gaps.
- `brain.py scan` and a short look at the result: the biggest folders, anything that
  looks sensitive and is still `open` (offer `privacy set`).
- Open the naming file and the profile with the person; they are theirs to edit.
- End with what to do tomorrow: "שלח לי צילום של מסמך, ואני אציע שם ותיקייה."
