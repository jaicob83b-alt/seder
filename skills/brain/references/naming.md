# Names, and finding documents

The instance's own naming procedure (`נוהל_שמות.md` / `naming.md` in the home folder)
is the authority; it was generated from this reference and the person may have
changed it. Read it first.

## The name

```
YYYY-MM_type - whose.ext
```

| part | rule | examples |
|---|---|---|
| `YYYY-MM` | the date written inside the document: issue date, or the period it covers. Month unknown: `YYYY_`. No date at all: no prefix | `2026-09_`, `2026_`, (none) |
| `type` | what the document is, in the words the person would search for, in the instance language | חשבון חשמל, תלוש שכר, חוזה שכירות, אישור ביטוח; electricity bill, payslip, lease |
| `whose` | a person or entity from `entities` in `brain.json`, spelled as there | דנה, יוסי, קינג בע"מ |
| extra | an identifying detail after another dash, when needed | ` - 3 עמודים`, ` - הזמנה 4471`, ` - ספק X` |

Rules the script enforces (a bad name is rejected, the document stays in the inbox):
no `\ / : * ? " < > |` or control characters; no leading or trailing space or dot; a
stem that does not end with a space or dot; at most 180 characters. Rules you
enforce: no `(1)`, no "final", no `_v2`; the type in the instance language; the
"whose" exactly as in `entities`; sort by content, not by the original file name.

## Which folder

The document goes to the thing it is about. The branch's allowed subfolders are in
`brain.json` (`subfolders`); `tree-default.md` explains the standard tree. A document
that fits nothing gets a proposed new subfolder under the right branch, with
`new_folder: true`, and waits for a yes.

## Finding a document ("איפה החשבון", "where is")

1. **Names first.** The index (`אינדקס.csv` / `index.csv` in the home folder) holds one
   row per document: path, branch, subfolder, name, date, type, size, sensitivity
   mark, hash. It is names only, so reading or grepping it sends no document content
   anywhere. `brain.py index` prints the row count; `brain.py index --rebuild` refreshes
   it (names only, safe to run).
2. **Answer with the path.** "Found: `01_כספים\חשבונות שוטפים\2026-08_חשבון חשמל - דנה.pdf`."
   Not found: say so, and list the closest names (same type, other months; same
   month, other type).
3. **Content only with consent.** Open the file itself only when the person asks for
   its content, and only after a yes if its folder is at level `ask` (the hook asks
   anyway). A `locked` folder is never opened; offer the name and the path.
4. **No money math.** Read the number off the document when asked; do not sum, compare
   or reconcile across documents. That belongs to the person's finance tool.

## Ledger rows

Every filed, non-sensitive document gets a row in the ledger (`פנקס.csv` /
`ledger.csv`): type, counterparty, whose, period, amount, currency, due date, action,
recurring. `brain.py ledger backfill` adds rows from names alone for documents that
have none (an adopted archive). `brain.py ledger open` lists actions not yet done;
`brain.py ledger done PATH` marks one done, which is a row update, never a deletion.
