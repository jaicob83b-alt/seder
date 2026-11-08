import json
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).parents[1] / "skills" / "brain" / "scripts" / "brain.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-I", "-X", "utf8", str(CLI), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def test_version_prints_json():
    r = run_cli("version")
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"ok": True, "version": "0.2.0"}


def test_unknown_command_is_json_error():
    r = run_cli("nope")
    assert r.returncode == 1
    assert json.loads(r.stdout)["ok"] is False
