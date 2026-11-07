# Intake: from "what arrived" to filed documents

Read this when the person wants to file documents: photos sent to the chat, files in
the inbox, "תייק", "מה הגיע", "file this", "sort these".

## The flow

0. **Mark the conversation.** Your first message of an intake contains the line
   `SEDER_INTAKE` on its own (a small print line is fine). It is how
   `brain.py prune-transcripts` later recognises transcripts that hold document
   content, so the person can move them off the disk.
1. **Stage the files in the inbox.** The inbox is `<home>/_נכנס` (Hebrew) or
   `<home>/_inbox` (English); `brain.json` has `lang`. Files already there are ready.
   Photos the person sent to the chat live in the conversation's uploads folder:
   *copy* them into the inbox (never move the person's originals). Files on the
   phone or in mail arrive here through the optional sources (`sources.md`).
2. **List the inbox.**
   `python -I -X utf8 "<skill dir>/scripts/brain.py" inbox`
   Each file comes with `size`, `ext`, `sha12`, `dup_of` (paths in the index with the
   same content), `held`, `held_why` and `suggested_name`.
3. **Read what you may read.** Open every file that is not `held` with the Read tool
   (images are viewed, PDFs come as text and pages). Do not open a `held` file: it
   looks medical, and its content must not reach the model unless the person asks
   for that file by name. For a held file you propose `suggested_name` and ask only
   two things: whose it is, and whether the name is right.
4. **Group pages into documents.** Several photos of one letter are one PDF. Decide
   by the order of sending, the letterhead, page numbers and text that continues.
   When unsure, ask before proposing. A photo that is upside down or sideways gets a
   `rotate` value (clockwise degrees) instead of a complaint.
5. **Write `_proposal.json`** into the inbox with the Write tool, following the
   contract below. One entry per document, in the order you will show them.
6. **Show the table** in the instance language, one row per document:
   number, pages, proposed name, folder, why (one short clause), ledger summary
   (type, amount, due date), note (duplicate / held / new folder / low confidence).
   Then wait. Do not run anything until the person answers.
7. **Apply only what was approved.**
   `brain.py intake-apply --approve 1,3 --name 2="<corrected name>" --folder 3="<corrected folder>" --mkdir 3`
   Numbers are the table's 1-based numbers. `--mkdir N` only for a row whose new
   folder the person approved. Unapproved rows are not touched; they stay in the inbox.
8. **Report** from the JSON: where each document went, that the log holds an undo
   command, and every `"ok": false` row with its error, so the person can decide.

## The proposal contract (`_proposal.json`)

```json
{"docs": [
  {"pages": ["01.jpg", "02.jpg"], "rotate": [0, 0],
   "name": "2026-09_חשבון חשמל - דנה.pdf", "folder": "01_כספים/חשבונות שוטפים", "new_folder": false,
   "entity": "דנה", "summary": "חשבון חשמל ספטמבר 2026, 412.30 ₪, לתשלום עד 20.10", "readable": true,
   "duplicate": "", "sensitive": "open", "confidence": "high", "why": "חשבון חשמל של הבית", "skip": "",
   "ledger": {"type": "חשבון", "counterparty": "חברת החשמל", "whose": "דנה", "period": "2026-09",
              "amount": "412.30", "currency": "ILS", "due": "2026-10-20", "action": "לשלם", "recurring": "חודשי"}}
 ],
 "note": ""}
```

- `pages`: file names inside the inbox, in reading order. One PDF page with
  `rotate` 0 is moved as it is; anything else is built into a new PDF.
- `name`: by `naming.md`. Spaces at the ends and Windows-forbidden characters are
  rejected by the script, so get it right here.
- `folder`: `<branch>/<subfolder>` using the branch's physical folder, number or name
  (`01_כספים/בנק`, `01/בנק`). Subfolders come from the branch's allowed list in
  `brain.json`; a folder that does not exist yet needs `new_folder: true`, a sentence
  in `why`, and the person's yes (then `--mkdir N`). Never a path inside the brain folder.
- `duplicate`: the index path from `dup_of` when the content already exists. Propose
  `skip: "כפילות"` unless it is a newer version of the same document.
- `sensitive`: `"locked"` for a held file or a target folder at level `locked`;
  `"ask"` when the folder asks; otherwise `"open"`. For `locked`: `summary` empty,
  `why` empty, `ledger` fields empty except `whose`; the script files it under the
  template name and writes no ledger row.
- `confidence`: `low` when the date, the type or the owner is a guess. Say so in the table.
- `skip`: a short reason when the file should not be kept at all (an advert, a chat
  screenshot, a blurred duplicate photo). The person decides; an approved skip parks
  the file in `_skipped`, nothing is deleted.
- `readable`: `false` when the text cannot be read (blur, cut page). Still propose a
  name from what is visible, with `confidence: low`.
- `ledger`: every field is a string; leave what the document does not say empty.
  `period` is `YYYY-MM` (or a range such as `2026-01..2026-03`), `due` is `YYYY-MM-DD`,
  `recurring` one of חודשי / דו-חודשי / רבעוני / שנתי / חד-פעמי (monthly / bimonthly /
  quarterly / yearly / one-off), `action` is the verb the person must do, or empty.

## Rules that decide the hard cases

- **Names:** the date is the one inside the document (issue date or covered period).
  No date at all: no prefix. Use `brain.py namecheck FOLDER NAME --src PATH` when a
  name might be taken: it returns `exists`, `same` (same content) and `free`.
- **A newer version of an existing document:** keep both. Propose the new one with the
  free name the namecheck returns or with a distinguishing detail, and tell the person
  the older file can be marked " - גרסה קודמת" by hand.
- **Hand-off branches** (a branch with `handoff` in `brain.json`, such as a separate
  finance engine): the document goes to that engine's inbox in its original format.
  An `xlsx` or `docx` next to its PDF (`<stem>.orig.xlsx`) is moved as the original;
  propose the ledger fields anyway, the other engine extracts them.
- **Office files** (`xlsx`, `docx`) with no PDF: proposed and filed as themselves.
- **A photo that is not a document** (a receipt is a document; a selfie is not): `skip`.
- **Several documents in one photo** cannot be split; propose the main one and say so.
