# The standard tree

One tree for any household, in Israel or elsewhere. Seven main folders, no more. The
principle that removes most hesitation: **a document goes to the thing it is about,
not to its document type.** Car insurance under the car, home insurance under the
home, life insurance under the person. So there is no "insurance" folder and no
"certificates" folder at the top.

The exact lists live in `assets/tree.he.json` and `assets/tree.en.json`; an instance's
own copy is in `brain.json` (`tree`), with the physical folder each branch maps to.

| num | branch | inside | rule |
|---|---|---|---|
| 00 | המוח / Brain | settings, naming, index, ledger, log, inbox | the system itself; never a document target |
| 01 | כספים / Finance | בנק · כרטיסי אשראי · הלוואות ומשכנתא · חיסכון ופנסיה · מס וביטוח לאומי · הכנסות ותלושים · היסטוריה | everything that is household money |
| 02 | בית / Home | one folder per property: רכישה או שכירות · בנייה ושיפוצים · חשבונות שוטפים · ביטוח דירה · ועד בית | the property itself; the loan on it is Finance |
| 03 | משפחה / Family | one folder per person (adult, child, parent): תעודות ורישיונות · בריאות · חינוך ולימודים · זכויות וביטוח לאומי · ביטוח וחיסכון · עבודה · שונות | a document about a person goes to that person; בריאות / Health asks before opening |
| 04 | רכב / Vehicles | one folder per vehicle: רישיון וטסט · ביטוח · טיפולים · קנסות | |
| 05 | עסקים / Business | one folder per business: בנק · ספקים וחשבוניות · לקוחות ומכירות · עובדים ושכר · חוזים · מס ורשויות | sole trader or company |
| 06 | פרויקטים ואירועים / Projects and events | one folder per project with a short card | code and large files stay where they are |
| 99 | ארכיון / Archive | what is over: a closed business, a sold property, an old car | kept, out of the way |

**Add-ons** the onboarding offers only when relevant: 07 פרויקטי פיתוח / Dev projects
(one folder per project from a template: card, documents, decisions; `_ארכיון` for
dormant ones), 08 לימודים / Studies (one folder per course, one lesson per topic),
09 חיות מחמד / Pets, 10 מדיה / Media, 11 קהילה ודת / Community and religion,
12 צבא ומילואים / Military and reserves, 13 הגירה ואזרחות / Immigration and citizenship.

## Rules

- Subfolders are an allowed list, not folders that exist up front. A folder is
  created with its first document, after a yes. No cabinet full of empty folders.
- "One folder per X" branches (02, 03, 04, 05, 06, 07, 08): the first level is the
  item (the property, the person, the car), the allowed subfolders sit under it:
  `03_משפחה/דנה/בריאות`, `04_רכב/טויוטה 2019/ביטוח`.
- A document that fits no row: propose a new subfolder under the right branch and wait.
- A branch may have a `handoff` (another engine's inbox, originals kept): documents
  for that branch go there, not into its subfolders.
- An adopted archive keeps its existing folder names. `brain.json` maps the logical
  branch to the physical folder, and `עץ_מוצע.md` / `proposed_tree.md` holds the
  suggested mapping to this standard tree. Nothing moves until the person runs a
  separate, dry-run reorganisation.

## Worked examples

| document | goes to |
|---|---|
| electricity bill for the flat | 02 בית / <property> / חשבונות שוטפים |
| mortgage statement | 01 כספים / הלוואות ומשכנתא |
| child's school report | 03 משפחה / <child> / חינוך ולימודים |
| car insurance policy | 04 רכב / <car> / ביטוח |
| supplier invoice to the business | 05 עסקים / <business> / ספקים וחשבוניות |
| life insurance of a parent | 03 משפחה / <parent> / ביטוח וחיסכון |
| hospital discharge letter | 03 משפחה / <person> / בריאות (level ask, or locked if the person chose so) |
| contract of a business that closed | 99 ארכיון / <business> |
