"""Environment checks for onboarding: what is installed, what is missing, what is optional.

Every check is a dict: id, ok, detail, required, fix. Nothing is installed here.
"""
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def _check(cid, ok, detail, required, fix):
    return {"id": cid, "ok": bool(ok), "detail": detail, "required": required, "fix": fix}


def _module(name, cid, fix):
    try:
        mod = importlib.import_module(name)
        ver = getattr(mod, "__version__", "") or getattr(mod, "VersionBind", "")
        return _check(cid, True, f"{name} {ver}".strip(), True, "")
    except Exception as e:  # ImportError or a broken install
        return _check(cid, False, f"{name}: {e.__class__.__name__}", True, fix)


def _which(cid, names, required, fix, detail_ok=None):
    for n in names:
        p = shutil.which(n)
        if p:
            return _check(cid, True, detail_ok or p, required, "")
    return _check(cid, False, "not found on PATH", required, fix)


def _claude_cli():
    exe = shutil.which("claude")
    if not exe:
        return _check("claude_cli", False, "claude not found on PATH", True, "install Claude Code: https://docs.claude.com/en/docs/claude-code")
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15)
        return _check("claude_cli", r.returncode == 0, (r.stdout or r.stderr).strip()[:80], True, "" if r.returncode == 0 else "reinstall Claude Code")
    except Exception as e:
        return _check("claude_cli", False, f"claude --version failed: {e.__class__.__name__}", True, "reinstall Claude Code")


def _remote_control():
    on = False
    try:
        on = bool(json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8")).get("remoteControlAtStartup"))
    except Exception:
        pass
    detail = ("Remote Control is on: conversations, including documents Claude reads, also pass through Anthropic's servers so your phone can see them"
              if on else "Remote Control is off")
    return _check("remote_control", True, detail, False, "")


def checks() -> list[dict]:
    v = sys.version_info
    out = [
        _check("python", v >= (3, 11), f"Python {v.major}.{v.minor}.{v.micro}", True, "install Python 3.11 or newer"),
        _module("pymupdf", "pymupdf", "python -m pip install pymupdf"),
        _module("PIL", "pillow", "python -m pip install Pillow"),
        _module("openpyxl", "openpyxl", "python -m pip install openpyxl"),
        _claude_cli(),
        _which("git", ["git"], True, "install git: https://git-scm.com"),
        _which("tailscale", ["tailscale"], False, "optional, for the phone site: https://tailscale.com/download"),
        _which("syncthing", ["syncthing"], False, "optional, for WhatsApp/phone folders: https://syncthing.net"),
        _which("office", ["winword", "WINWORD.EXE"], False, "optional (Windows): Microsoft Office converts xlsx/docx to PDF"),
        _which("libreoffice", ["soffice", "libreoffice"], False, "optional: LibreOffice converts xlsx/docx to PDF on Mac/Linux"),
        _which("tesseract", ["tesseract"], False, "optional: local OCR for scans in locked folders"),
        _remote_control(),
    ]
    return out
