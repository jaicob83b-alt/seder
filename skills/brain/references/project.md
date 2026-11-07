# Project cards (07 / 06)

Read this when the person opens a new project ("תפתח פרויקט", "new project card"),
asks what projects are active, or when the weekly review proposes archiving one.

A project folder is a card, not a workspace: the code and the large files stay where
they are (a repo, a drive), and the card links to them. The folder holds:

```
<07_פרויקטי_פיתוח or 06_פרויקטים_ואירועים>/<project name>/
  כרטיס.md        what it is · where the code is · state · next step · relevant lessons · updated
  החלטות.md       dated decisions, newest first
  מסמכים/         documents filed to this project through intake
```

## Commands

```
brain.py project new "<name>" [--code "<path or URL>"] [--branch dev_projects|projects]
brain.py project list
brain.py project archive-candidates [--days 90]
brain.py project archive "<name>"
```

`new` fills the card template (`assets/project_template/card.<lang>.md`) with the name,
the code path, today's date and, when a studies index exists (add-on 08), the
lessons whose topics match the project name. It never overwrites an existing project.
`list` returns name, created, last modified, card path. `archive-candidates` lists
projects with no file changed in the last 90 days that are not yet in `_ארכיון` /
`_archive`; the weekly review shows them as a proposal. `archive` moves a project into
`_ארכיון` and runs only after the person says yes to that name.

## Writing the card

After `new`, open the card and fill "what it is", "state" and "next step" from what
the person told you, in their language, in two or three lines each. Keep "updated" as
the date you touched it. A card nobody reads is worse than none, so prefer short.

## Filing documents to a project

A document about a project (a quote, an invoice, a sketch) goes to
`<branch>/<project name>/מסמכים` through the normal intake proposal; the branch's
allowed subfolder is `מסמכים` / `Documents`.
