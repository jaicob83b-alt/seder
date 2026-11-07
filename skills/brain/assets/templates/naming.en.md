# Intake, naming and retrieval

> How {owner}'s archive files a new document and finds an existing one. Created {date} from the Seder template. Edit freely.

## The name

```
YYYY-MM_type - whose.ext
```

- **YYYY-MM** = the date written **inside** the document (issue date or the period it covers), not the download date. No month: `YYYY_`. No date at all: no prefix.
- **type** = what the document is, in the words you would search for: "payslip", "electricity bill", "lease", "invoice".
- **whose** = the person or entity: {entities}.
- An extra identifier is allowed after a dash: page count, order number, supplier.
- No `(1)`, no "final", no `_v2`. A new version of the same document: keep both, the old one gets " - previous version".
- **Sort by content, not by name.** The original file name is a hint; the content is the evidence.

## Which folder

The principle: **a document goes to the thing it is about, not to its document type.** Car insurance under the car, home insurance under the home, life insurance under the person.

| branch | folder on disk | allowed subfolders | rule |
|---|---|---|---|
{routing_table}

- Subfolders are an allowed list, not folders that exist up front. A folder is created when its first document arrives, with approval.
- A document that fits no row: the archive proposes a new folder and waits for approval. It never creates one on its own.
- A branch with a "hand-off" (for example a separate finance engine): the document goes to that engine's inbox, in its original format.

## Intake, step by step

1. The file lands in `{brain_folder}/{inbox}/` (a phone photo, a PDF, a screenshot, a mail attachment).
2. The archive reads it, unless it is quarantined (looks medical) or its target folder is locked: then it proposes a template name without reading.
3. Several pages of one document = one PDF. Order of sending, letterhead, page numbers and continuing content decide; when unsure, it asks.
4. It proposes a table: **name, folder, why**, plus the ledger fields (type, counterparty, whose, period, amount, due date, action).
5. {owner} answers "yes" (or corrects).
6. Move (not copy), a hash check that the file arrived intact, a row in `{log}` with the undo command, an update of `{index}` and `{ledger}`.

**Never:** no overwriting an existing file. No deleting. No filing without a "yes".

## Retrieval

1. Search `{index}` first (name, folder, date, whose).
2. Only then, and with approval, open the file itself.
3. The answer includes the **source path**. Not found: say so, and what was found nearby.
4. The archive does not do money math. Figures come from the documents or from the finance engine.

## Privacy: three levels per folder

- **open:** the archive reads and files.
- **ask:** before every file: "Opening this file sends its content to Anthropic. Continue?"
- **locked:** the model sees names only. Filing uses a template name, without reading.

Levels live in `{sensitive_file}`. Default: everything open, "Health" folders on ask. Change with `brain.py privacy set <folder> <open|ask|locked>`.
Even after an approved opening: medical details are never written to the profile, to memory, or to any summary page.

## Never read at all

`.env` files, keys, passwords, tokens. The Seder hook blocks them.
