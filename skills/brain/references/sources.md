# Sources and the phone: how documents reach the inbox

The inbox always works and needs nothing installed. Everything else is optional,
offered in the onboarding or later. Present the options as a checklist: what each
gives, what it needs, how long it takes, what it sends. "No" is a complete answer
for every row. Install nothing without a yes, and explain each command before it runs.

| source | gives | needs | minutes | what leaves the computer |
|---|---|---|---|---|
| **chat** (always) | photos and files sent to the conversation, also from the phone with Remote Control | nothing | 0 | the files you read, as in any conversation |
| **inbox folder** (always) | anything saved into `<home>/_נכנס` / `_inbox` | nothing | 0 | nothing until intake |
| **PC Downloads** | new documents downloaded on this computer are copied into the inbox | nothing (`brain.py sources add`) | 1 | nothing until intake |
| **phone site** | on the phone: approve or reject proposals, photograph a document straight into the inbox, search, open a filed document, the weekly review | Tailscale on the computer and the phone | 10 | nothing; Tailscale connects the two devices directly, encrypted |
| **phone Downloads and WhatsApp** | documents downloaded on the phone, and documents received in WhatsApp, reach the inbox by themselves | Syncthing on the computer and the phone | 15 | nothing; Syncthing copies device to device |
| **Gmail** | attachments of new mail | a later module, not in this version | | |

Say plainly that Gmail is a later module. Do not promise what is not there.

## Watched folders (`sources`, `pull`)

A watched folder is any folder on the computer whose new documents should come in:
the PC's Downloads, or a folder Syncthing fills from the phone.

```
brain.py sources add "<folder>" --label "הורדות במחשב"
brain.py sources list
brain.py sources remove "<folder>"
brain.py pull
```

`pull` copies (never moves) new documents into the inbox: top level only, documents
only, nothing older than the day the folder was added, each file once (by content,
so a renamed copy is not pulled twice). The phone site runs `pull` every minute
while it is up; without the site, run `pull` at the start of an intake.

## The phone site

What the person gets: a page on the phone, named after their archive, with four
tabs: approve (the proposal Claude wrote, one card per document with a thumbnail,
approve / edit / reject), snap (the camera, straight into the inbox), search (by
name), review (the weekly page). Claude still writes the proposals: the person says
"תייק את מה שהגיע" in the chat, or from the phone through Remote Control, then
approves on the site whenever it suits them.

### 1. Tailscale on the computer

Explain first: "Tailscale is a private network between your own devices. The site
will be reachable only from your phone and computer, not from Wi-Fi neighbours and
not from the internet. It is free for personal use."

```
brain.py site --check
```
- `tailscale_installed: false`: offer `winget install --id Tailscale.Tailscale -e`
  (Windows; on a Mac, the App Store). Then the person signs in from the Tailscale
  icon near the clock, with Google or another account.
- `tailscale_up: false`: ask them to open Tailscale and sign in, then check again.

### 2. Tailscale on the phone

"On the phone: Play Store (or App Store) → Tailscale → install → sign in with the
same account as on the computer → allow the VPN when asked." Then check again;
`phone_url` is the address to open.

### 3. Start the site

```
brain.py site
```
It listens on the Tailscale address only (or 127.0.0.1 without Tailscale) and
refuses any other address. Tell the person to open `phone_url` on the phone (or
`phone_url_name`, the computer's name), then "Add to home screen" from the browser
menu so it opens like an app.

The site runs while the conversation's command runs. To have it always on, offer
(after a yes) to start it with Windows:
```
brain.py site --autostart install      # remove | status
```
It writes one small file in the user's Startup folder; `remove` deletes it.

## Phone Downloads and WhatsApp (Syncthing)

On an Android phone, WhatsApp keeps received documents in its own folder, not in
Downloads: `Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Documents`. So there
are two phone folders to share, and both are optional.

1. **On the computer:** `winget install --id Syncthing.Syncthing -e`, then open
   `http://127.0.0.1:8384` (Syncthing's own page, local only).
2. **On the phone:** Play Store → "Syncthing-Fork" → install → allow access to all
   files (needed to see the WhatsApp folder).
3. **Pair:** in the phone app, add a device and scan the QR code shown on the
   computer under Actions → Show ID. Accept the pairing on the computer.
4. **Share the folders from the phone:** add folder → `Download` (and/or the WhatsApp
   Documents folder above) → folder type **Send Only** → share with the computer.
   On the computer, accept and choose where they land, for example
   `<home>/../phone/הורדות` and `<home>/../phone/וואטסאפ` (outside the brain folder).
5. **Watch them:** `brain.py sources add "<that folder>" --label "וואטסאפ"`, same for Downloads.

Send Only on the phone means nothing on the phone changes when files are copied or
filed on the computer.

## Rules for any automatic source

- It drops files into the inbox and stops. Filing still goes through a proposal and a yes.
- The quarantine runs locally first (`held` in `brain.py inbox`): a medical sender, a
  medical word in the name, two medical words in locally extracted text.
- It runs Claude, if at all, with the headless settings from `brain.py settings
  --headless` (see `privacy.md`), never with the interactive session's permissions.
- Its status must be visible: `brain.py sources list` shows the last run, how many
  files each folder gave and the last error. A source that fails silently is worse than none.
