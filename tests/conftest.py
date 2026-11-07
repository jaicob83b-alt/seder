"""Test setup: make the `seder` package importable from the skill's scripts folder."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "brain" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
