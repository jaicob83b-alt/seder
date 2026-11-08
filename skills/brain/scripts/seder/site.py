"""The phone site: a small web page on the person's own computer, reached from their phone.

What it does: shows what waits (the proposal Claude wrote and the inbox), lets the
person approve or reject each proposed document, take a photo with the phone's
camera straight into the inbox, search the archive by name, open a filed
document, and open the weekly review page. It never calls a model.

Who can reach it: the server listens on the computer's Tailscale address (100.x),
or on 127.0.0.1 when Tailscale is not set up. It refuses to listen on any other
address (no Wi-Fi, no internet), answers only clients from the Tailscale range or
the computer itself, checks the Host header (DNS rebinding), and accepts a change
(POST) only with the custom header `X-Seder: 1` from the same origin, so a page on
another site cannot post to it.

Standard library only, plus the engine's own pdf helpers for thumbnails.
"""
import ipaddress
import json
import mimetypes
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import inbox, index, pull
from .config import Config

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "site"
DEFAULT_PORT = 8765
TAILNET = ipaddress.ip_network("100.64.0.0/10")
LOOPBACK = ipaddress.ip_network("127.0.0.0/8")
UPLOAD_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf"}
MAX_UPLOAD = 25 * 1024 * 1024
PULL_EVERY = 60
SAFE_NAME = re.compile(r'^[^\\/:*?"<>|\x00-\x1f]+$')


# ---------- where to listen ----------

def tailscale_exe() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    for p in (r"C:\Program Files\Tailscale\tailscale.exe", "/Applications/Tailscale.app/Contents/MacOS/Tailscale"):
        if Path(p).is_file():
            return p
    return None


def tailscale_ip() -> str | None:
    exe = tailscale_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in (r.stdout or "").split():
        try:
            if ipaddress.ip_address(line.strip()) in TAILNET:
                return line.strip()
        except ValueError:
            continue
    return None


def allowed_bind(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip in TAILNET or ip in LOOPBACK


def check(port: int = DEFAULT_PORT) -> dict:
    """What the onboarding needs to know: is Tailscale installed and up, and which address to open on the phone."""
    exe = tailscale_exe()
    ip = tailscale_ip() if exe else None
    host = socket.gethostname().lower()
    return {"tailscale_installed": bool(exe), "tailscale_up": bool(ip), "ip": ip,
            "phone_url": f"http://{ip}:{port}" if ip else None,
            "phone_url_name": f"http://{host}:{port}" if ip else None,
            "local_url": f"http://127.0.0.1:{port}"}


# ---------- what the page shows ----------

def _proposal(cfg: Config) -> dict:
    p = cfg.path("inbox") / inbox.PROPOSAL
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"docs": []}


def _write_proposal(cfg: Config, prop: dict) -> None:
    p = cfg.path("inbox") / inbox.PROPOSAL
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(prop, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def state(cfg: Config) -> dict:
    box = cfg.path("inbox")
    prop = _proposal(cfg)
    docs = []
    in_proposal = set()
    for i, d in enumerate(prop.get("docs") or []):
        pages = list(d.get("pages") or [])
        in_proposal.update(pages)
        waiting = bool(pages) and all((box / p).is_file() for p in pages)
        status = "rejected" if d.get("rejected") else ("waiting" if waiting else "done")
        locked = d.get("sensitive") == "locked"
        docs.append({"n": i + 1, "status": status, "pages": pages, "name": d.get("name", ""),
                     "folder": d.get("folder", ""), "why": "" if locked else d.get("why", ""),
                     "summary": "" if locked else d.get("summary", ""), "skip": d.get("skip", ""),
                     "duplicate": d.get("duplicate", ""), "new_folder": bool(d.get("new_folder")),
                     "confidence": d.get("confidence", ""), "locked": locked})
    loose = [f for f in inbox.list_inbox(cfg) if f["file"] not in in_proposal]
    for f in loose:
        f.pop("suggested_name", None)
    return {"name": cfg.data.get("name") or "", "lang": cfg.lang, "docs": docs, "inbox": loose,
            "review": cfg.path("review").is_file(), "sources": pull.status(cfg),
            "now": datetime.now().isoformat(timespec="seconds")}


def search(cfg: Config, q: str, limit: int = 60) -> list[dict]:
    words = [w.casefold() for w in q.split() if w.strip()]
    if not words:
        return []
    out = []
    for r in index.rows(cfg):
        hay = f"{r.get('path', '')} {r.get('name', '')}".casefold()
        if all(w in hay for w in words):
            out.append({"path": r["path"].replace("\\", "/"), "name": r.get("name", ""), "date": r.get("date", "")})
    out.sort(key=lambda r: r["date"], reverse=True)
    return out[:limit]


def inbox_file(cfg: Config, name: str) -> Path:
    if not name or not SAFE_NAME.match(name) or name.startswith(("_", ".")):
        raise ValueError("bad file name")
    p = cfg.path("inbox") / name
    if not p.is_file():
        raise FileNotFoundError(name)
    return p


def archive_file(cfg: Config, rel: str) -> Path:
    """A filed document by its root-relative path; never outside the root, never inside the brain folder."""
    rel = (rel or "").replace("\\", "/").strip("/")
    if not rel or any(seg in ("", ".", "..") for seg in rel.split("/")):
        raise ValueError("bad path")
    root = cfg.root.resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or p.is_relative_to(cfg.home.resolve()):
        raise ValueError("outside the archive")
    if not p.is_file():
        raise FileNotFoundError(rel)
    return p


def thumbnail(path: Path, width: int = 480) -> tuple[bytes, str]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        import pymupdf
        with pymupdf.open(str(path)) as doc:
            page = doc[0]
            zoom = width / max(page.rect.width, 1)
            return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"), "image/png"
    from PIL import Image, ImageOps
    import io
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((width, width * 2))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=80)
        return buf.getvalue(), "image/jpeg"


def save_upload(cfg: Config, filename: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower() or ".jpg"
    if ext not in UPLOAD_EXTS:
        raise ValueError(f"not a photo or PDF: {ext}")
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError("empty or too large")
    box = cfg.path("inbox")
    box.mkdir(exist_ok=True)
    from .filing import free_name
    name = free_name(box, f"phone_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}")
    tmp = box / f"_upload_{name}"
    tmp.write_bytes(data)
    tmp.replace(box / name)
    return name


def apply(cfg: Config, n: int, name: str = "", folder: str = "", mkdir: bool = False) -> dict:
    prop = _proposal(cfg)
    docs = prop.get("docs") or []
    if not 1 <= n <= len(docs):
        raise ValueError(f"no document {n}")
    if docs[n - 1].get("rejected"):
        raise ValueError("this document was rejected")
    if docs[n - 1].get("new_folder") and not mkdir:
        return {"i": n, "ok": False, "error": "folder does not exist"}
    res = inbox.apply(cfg, prop, [n - 1], names={n - 1: name} if name else None,
                      folders={n - 1: folder} if folder else None, mkdir={n - 1} if mkdir else None)[0]
    res["i"] = n
    return res


def reject(cfg: Config, n: int) -> dict:
    prop = _proposal(cfg)
    docs = prop.get("docs") or []
    if not 1 <= n <= len(docs):
        raise ValueError(f"no document {n}")
    docs[n - 1]["rejected"] = True
    _write_proposal(cfg, prop)
    return {"i": n, "rejected": True}


# ---------- the server ----------

def make_handler(cfg: Config, bind: str, port: int):
    host_names = {bind, "localhost", "127.0.0.1", socket.gethostname().lower()}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "seder"
        sys_version = ""

        def log_message(self, fmt, *args):  # no request log with document names on the console
            pass

        def _client_ok(self) -> bool:
            try:
                ip = ipaddress.ip_address(self.client_address[0])
            except ValueError:
                return False
            if not (ip in TAILNET or ip in LOOPBACK):
                return False
            host = (self.headers.get("Host") or "").split(":")[0].strip("[]").lower()
            return host in host_names or host.endswith(".ts.net")

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _file(self, p: Path):
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            disp = "inline; filename*=UTF-8''" + urllib.parse.quote(p.name)
            self._send(200, p.read_bytes(), ctype, {"Content-Disposition": disp})

        def do_GET(self):
            if not self._client_ok():
                return self._send(403, b"forbidden", "text/plain")
            url = urllib.parse.urlsplit(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    csp = "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
                    page = (ASSETS / "index.html").read_bytes()
                    return self._send(200, page, "text/html; charset=utf-8", {"Content-Security-Policy": csp})
                if url.path == "/api/state":
                    return self._json(state(cfg))
                if url.path == "/api/search":
                    return self._json({"results": search(cfg, q.get("q", ""))})
                if url.path == "/api/thumb":
                    body, ctype = thumbnail(inbox_file(cfg, q.get("file", "")))
                    return self._send(200, body, ctype)
                if url.path == "/api/inbox-file":
                    return self._file(inbox_file(cfg, q.get("file", "")))
                if url.path == "/api/file":
                    return self._file(archive_file(cfg, q.get("path", "")))
                if url.path == "/review":
                    if cfg.path("review").is_file():
                        return self._send(200, cfg.path("review").read_bytes(), "text/html; charset=utf-8")
                    return self._send(404, b"no review yet", "text/plain")
                return self._send(404, b"not found", "text/plain")
            except (ValueError, FileNotFoundError) as e:
                return self._json({"ok": False, "error": str(e)}, 400)
            except Exception as e:  # never a stack trace to the phone
                return self._json({"ok": False, "error": e.__class__.__name__}, 500)

        def do_POST(self):
            if not self._client_ok() or self.headers.get("X-Seder") != "1":
                return self._send(403, b"forbidden", "text/plain")
            origin = self.headers.get("Origin")
            if origin and (urllib.parse.urlsplit(origin).hostname or "").lower() not in host_names \
                    and not (urllib.parse.urlsplit(origin).hostname or "").lower().endswith(".ts.net"):
                return self._send(403, b"forbidden", "text/plain")
            url = urllib.parse.urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD:
                return self._json({"ok": False, "error": "too large"}, 413)
            body = self.rfile.read(length) if length else b""
            try:
                with lock:
                    if url.path == "/api/upload":
                        fname = urllib.parse.unquote(self.headers.get("X-Filename") or "photo.jpg")
                        return self._json({"ok": True, "file": save_upload(cfg, fname, body)})
                    data = json.loads(body or b"{}")
                    if url.path == "/api/apply":
                        res = apply(cfg, int(data.get("n", 0)), str(data.get("name") or ""),
                                    str(data.get("folder") or ""), bool(data.get("mkdir")))
                        if not res.get("ok"):
                            err = str(res.get("error") or "not filed")
                            if err.startswith(("folder does not exist", "ValueError: folder does not exist")):
                                return self._json({"ok": False, "error": "needs_folder"}, 409)
                            return self._json({"ok": False, "error": err.split(":")[0]}, 400)
                        return self._json({"ok": True, "result": res})
                    if url.path == "/api/reject":
                        return self._json({"ok": True, "result": reject(cfg, int(data.get("n", 0)))})
                    if url.path == "/api/pull":
                        return self._json({"ok": True, **pull.pull(cfg)})
                return self._send(404, b"not found", "text/plain")
            except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
                return self._json({"ok": False, "error": str(e)}, 400)
            except Exception as e:
                return self._json({"ok": False, "error": e.__class__.__name__}, 500)

    return Handler


def _pull_loop(cfg: Config, stop: threading.Event):
    while not stop.wait(PULL_EVERY):
        try:
            if pull.folders(cfg):
                pull.pull(cfg)
        except Exception:
            pass


def serve(cfg: Config, bind: str | None = None, port: int = DEFAULT_PORT, wait_for_tailscale: int = 0) -> None:
    """Run until interrupted. Picks the Tailscale address, else loopback; refuses anything else."""
    if bind is None:
        deadline = time.time() + wait_for_tailscale
        bind = tailscale_ip()
        while bind is None and time.time() < deadline:
            time.sleep(10)
            bind = tailscale_ip()
        bind = bind or "127.0.0.1"
    if not allowed_bind(bind):
        raise ValueError(f"refusing to listen on {bind}: only the Tailscale address (100.x) or 127.0.0.1")
    httpd = ThreadingHTTPServer((bind, port), make_handler(cfg, bind, port))
    stop = threading.Event()
    threading.Thread(target=_pull_loop, args=(cfg, stop), daemon=True).start()
    print(json.dumps({"ok": True, "serving": f"http://{bind}:{port}"}, ensure_ascii=False), flush=True)
    try:
        httpd.serve_forever()
    finally:
        stop.set()
        httpd.server_close()


# ---------- start with the computer (Windows), only after a yes ----------

def _startup_dir() -> Path:
    import os
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


STARTUP_FILE = "seder-site.cmd"


def autostart(cfg: Config, action: str, brain_py: Path, python: str) -> dict:
    """install | remove | status. Writes or removes one small .cmd in the user's Startup folder."""
    target = _startup_dir() / STARTUP_FILE
    if action == "status":
        return {"installed": target.is_file(), "file": str(target)}
    if action == "remove":
        existed = target.is_file()
        if existed:
            target.unlink()
        return {"installed": False, "removed": existed, "file": str(target)}
    if action == "install":
        if not _startup_dir().is_dir():
            raise ValueError("no Windows Startup folder here; start the site by hand")
        pyw = str(Path(python).with_name("pythonw.exe")) if Path(python).with_name("pythonw.exe").is_file() else python
        line = f'start "" /min "{pyw}" -I -X utf8 "{brain_py}" --home "{cfg.home}" site --wait-tailscale 600\r\n'
        target.write_text("@echo off\r\nchcp 65001 >nul\r\n" + line, encoding="utf-8")
        return {"installed": True, "file": str(target)}
    raise ValueError("action is install, remove or status")
