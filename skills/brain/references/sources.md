# Sources: how documents reach the inbox

The inbox always works and needs nothing installed. Everything else is optional,
chosen in the onboarding or later, and recorded in `brain.json` under `sources`.
Present the options as a checklist: what each gives, what it needs, how long it
takes, what it sends. "No" is a complete answer for every row.

| source | gives | needs | minutes | what leaves the computer |
|---|---|---|---|---|
| **chat** (always) | photos and files sent to the Claude Code conversation, also from the phone with Remote Control | nothing | 0 | the files you read, as in any conversation |
| **inbox folder** (always) | anything saved into `<home>/_נכנס` / `_inbox`: downloads, drag and drop, a sync client the person already has (OneDrive, Google Drive, iCloud) | nothing | 0 | nothing until intake |
| **Gmail** (optional) | attachments of new mail, pulled into the inbox | an app password stored in the OS credential store (Windows Credential Manager / macOS Keychain), never in a file; the quarantine checks sender and words before any model sees a file | 3 | attachments, after intake; mail text is not read |
| **WhatsApp from the phone** (optional) | documents received in WhatsApp land in the inbox by themselves | Syncthing on the phone and on the computer, one shared folder | 15 | nothing beyond intake |
| **phone Downloads** (optional) | files downloaded on the phone | the same Syncthing share | 5 | nothing beyond intake |
| **phone site** (optional) | approve proposals from the phone in a browser, no cloud | Tailscale on both devices; the site binds to the private tailnet address only | 10 | nothing beyond intake |

## Status in v0.1

The chat and the inbox folder are the two sources this version of the skill runs.
The Gmail, WhatsApp, Downloads and phone-site modules are the owner's existing
scripts, Windows-only today, and are not bundled with the plugin yet. Set the flags in
`brain.json` when the person wants them so the onboarding and the review know, and
say plainly that they are a later module. Do not promise a module that is not there.

## Rules for any automatic source

- It drops files into the inbox and stops. Filing still goes through a proposal and a yes.
- The quarantine runs locally first (`held` in `brain.py inbox`): a medical sender, a
  medical word in the name, two medical words in locally extracted text.
- It runs Claude, if at all, with the headless settings from `brain.py settings
  --headless` (see `privacy.md`), never with the interactive session's permissions.
- Its status must be visible: what it pulled, when, and the last error. A source that
  fails silently is worse than none.
