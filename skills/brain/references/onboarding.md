# Onboarding: the first meeting

Read this when `doctor` reports `home: null`, or when the person asks to set up,
install or connect their archive. It is a conversation, not a form: one question
per message, in the person's language, and every question follows from what you
already learned. Install nothing, look at nothing and move nothing without a yes.

The order: check the machine, ask for a name, ask to look, show what you found,
interview from the findings, show the tailored tree, create or adopt, first document.

## 1. Check the machine

`python -I -X utf8 "<skill dir>/scripts/brain.py" doctor`

Explain the checks that are not ok in plain words. Required ones (Python, pymupdf,
Pillow, openpyxl, Claude Code, git) block intake; offer the `fix` command and run it
only after a yes. Optional ones (Tailscale, Syncthing, Office or LibreOffice,
Tesseract) are mentioned only when the matching source comes up. If `remote_control`
is on, say the Remote Control sentence from `privacy.md` once.

## 2. The name

"איך תרצה לקרוא לארכיון? למשל 'סדר', 'הארון של דנה', או כל שם אחר. אפשר לשנות
אחר כך." / "What would you like to call your archive? 'Seder', 'Dana's cabinet',
anything. You can change it later."

The name is used in your answers and on the review page. The brain folder is
`00_<name>` with spaces as underscores, unless the person wants another folder name.
Later: `brain.py rename "<new name>"` changes the name; `--folder` also renames the
brain folder and updates the pointer.

## 3. Ask to look

Say what the look does before asking:

"אני רוצה להציץ בתיקיות שבהן מסמכים בדרך כלל מצטברים: מסמכים, הורדות, שולחן
העבודה, ותיקיות סנכרון כמו OneDrive או Google Drive. אני רואה רק שמות של קבצים
ותיקיות, לא פותח אף קובץ ולא מזיז כלום. ככה אציע עץ שמתאים לך. להציץ?"

On yes:
```
brain.py discover --lang he
```
It prints counts only: documents per place, the biggest folders, topics recognised
in file and folder names, archives that already look organised, any existing Seder
instance, and a `suggested_plan`. It never prints a file name and never opens a file.
The person can name other places (`--roots "D:\Scans" "E:\Phone"`), for example a
folder where their phone or WhatsApp backs up. On no: skip to step 5 and ask the
questions without findings.

If `existing_instances` is not empty, there is already an archive: run `brain.py --home
"<it>" doctor` and stop the onboarding.

## 4. Show what you found

A short table, biggest first, in plain words. For example:

| | |
|---|---|
| מסמכים שמצאתי | 640, רובם בהורדות (410) |
| אופנועים | 38 מסמכים, בעיקר ב"אופנוע ימאהה" |
| תלושי שכר | 25 |
| בנק | 20 |
| נראים רפואיים | 12 (בלי שמות; התיקייה תהיה נעולה) |

Say where the mess is ("רוב המסמכים בהורדות, בלי תיקיות") and that nothing has moved.
Medical documents are reported as a number only; never name their folders.

If `organized_archives` lists a folder with numbered subfolders, ask whether that
is their archive. A yes means **adopt** (step 7) instead of a new tree.

## 5. The interview, built from the findings

Ask only what the findings make relevant, biggest topic first, one per message.
Every topic in the scan output carries a ready `question`; use it, or your own
words. Then the four questions every archive needs:

1. **Where should the archive live?** The root folder (often the Documents folder).
2. **Language?** `he` or `en`: the interface, the system file names, folder names.
3. **Your name, as it appears in document names.** The owner.
4. **Who else, and which businesses?** People in the household, parents, a company.
   These become `entities`, the allowed "whose" in names. Spelling matters.

From the topic answers, fill the plan:
- many motorcycle or car documents: the vehicle branch renamed and widened, one
  item per vehicle (`items`), and the extra subfolders from `suggested_plan`;
- payslips of two people: both are entities;
- a business: an item in 05 with its name; no business at all: offer to `drop` 05;
- a hobby or field with many documents that fits no branch (sport, music, a club):
  an `extra` branch of its own;
- pets, military, studies, dev projects: the matching add-on.

Privacy, once, when health documents came up or at the end: "תיקיות בריאות נעולות
(רק שמות). להשאיר נעול, או שאלה לפני כל פתיחה?" Sources, once: the checklist from
`sources.md`; record the yes/no flags in `brain.json`.

## 6. The tailored tree

Write the plan to a JSON file in the scratchpad, then preview it:
```
brain.py tree-preview --lang he --addons pets --plan "<plan.json>"
```
Plan keys, all optional: `addons`, `rename` {branch: name}, `subfolders` {branch:
[names]} (replace), `subfolders_add` {branch: [names]}, `drop` [branch] (not 00 or
99), `items` {branch: [names]} (per-item branches only), `extra` [{name, subfolders,
per_item, item, rule}]. Branch ids: finance, home, family, vehicles, business,
projects, archive and the add-on ids.

Show the result as a table, branch, subfolders and items, and mark what differs
from the standard tree ("מורחב בשבילך"). Change it until the person says yes.
Say that folders are created only when the first document arrives.

## 7. Create or adopt

New:
```
brain.py init --home "<root>/00_<name>" --root "<root>" --lang he --owner "<owner>" --entities "a,b" --name "<name>" --plan "<plan.json>"
```
Existing archive:
```
brain.py adopt --home "<existing brain folder>" --root "<root>" --name "<name>"
```
`adopt` registers every top-level folder as a branch with its current name, keeps the
existing index, log and naming files byte for byte, marks medical-looking folders,
detects a hand-off inbox (`_inbox` inside a branch), and writes `עץ_מוצע.md` /
`proposed_tree.md`: where each folder would sit in the standard tree. Show it and say
it is a proposal for a later, separate reorganisation. Nothing moves now.

If `init` or `adopt` says an instance already exists, run `doctor`.

## 8. Make the hook work everywhere

The privacy hook finds the instance through `SEDER_HOME` or the pointer file
`~/.seder/home`. Offer `brain.py pointer --write` after a yes. Without it, the hook
protects only conversations that run inside the root.

## 9. First light

- `brain.py index --rebuild` (names only; say how many documents it found).
- For an adopted archive, `brain.py ledger backfill`, so the first weekly review
  already shows recurring documents and gaps.
- `brain.py scan`: the biggest folders, anything that looks sensitive and is still
  `open` (offer `brain.py privacy set`).
- Open the naming file and the profile with the person; they are theirs to edit.
- The documents the scan found stay where they are. Offer the next step in plain
  words: "רוצה שנתחיל מההורדות? תעביר לתיקיית _נכנס את מה שרלוונטי, או שאציע רשימה."
  Anything that moves goes through the inbox, a proposal and a yes.
- End with: "שלח לי צילום של מסמך, ואני אציע שם ותיקייה."
