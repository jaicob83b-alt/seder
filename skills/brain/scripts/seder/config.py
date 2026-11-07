"""The private instance: `brain.json` in the archive's brain folder, and how to find it.

Nothing personal lives in code. The root path, language, owner, entities,
the logical tree (with its physical folder mapping) and the enabled sources
all come from this file.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import names

BRAIN_FILE = "brain.json"
ENV_VAR = "SEDER_HOME"
HOME_POINTER = Path.home() / ".seder" / "home"


@dataclass
class Config:
    home: Path
    root: Path
    lang: str = "he"
    owner: str = ""
    entities: list = field(default_factory=list)
    tree: list = field(default_factory=list)
    sources: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)  # everything else in brain.json (version, remote_warning, ...)

    @classmethod
    def load(cls, home: Path) -> "Config":
        home = Path(home)
        data = json.loads((home / BRAIN_FILE).read_text(encoding="utf-8"))
        lang = data.get("lang", "he")
        if lang not in names.LANGS:
            raise ValueError(f"unsupported lang in {BRAIN_FILE}: {lang}")
        root = Path(data.get("root") or home.parent)
        if not root.is_absolute():
            root = (home / root).resolve()
        known = {"lang", "owner", "root", "entities", "tree", "sources"}
        return cls(
            home=home,
            root=root,
            lang=lang,
            owner=data.get("owner", ""),
            entities=list(data.get("entities", [])),
            tree=list(data.get("tree", [])),
            sources=dict(data.get("sources", {})),
            data={k: v for k, v in data.items() if k not in known},
        )

    def to_dict(self) -> dict:
        out = {"version": self.data.get("version", 1), "lang": self.lang, "owner": self.owner,
               "root": str(self.root), "entities": self.entities, "tree": self.tree, "sources": self.sources}
        out.update({k: v for k, v in self.data.items() if k not in out})
        return out

    def save(self) -> None:
        """Atomic write: temp file in the same folder, then replace."""
        target = self.home / BRAIN_FILE
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, target)

    def path(self, key: str) -> Path:
        """Absolute path of a system file or folder of this instance, by internal key."""
        return self.home / names.FILES[self.lang][key]

    def t(self, key: str) -> str:
        """A user-facing message in the instance's language."""
        return names.MESSAGES[self.lang].get(key) or names.MESSAGES["en"].get(key, key)


def _has_brain(p: Path) -> bool:
    try:
        return (p / BRAIN_FILE).is_file()
    except OSError:
        return False


def find_home(explicit: Path | None = None, cwd: Path | None = None) -> Path | None:
    """Locate the instance folder (the one holding brain.json).

    Order: `explicit` -> env SEDER_HOME -> ~/.seder/home pointer file ->
    brain.json in cwd, in cwd's direct children, then in cwd's parents.
    Returns None when nothing is found.
    """
    if explicit is not None:
        p = Path(explicit)
        return p if _has_brain(p) else None
    env = os.environ.get(ENV_VAR)
    if env and _has_brain(Path(env)):
        return Path(env)
    try:
        if HOME_POINTER.is_file():
            line = HOME_POINTER.read_text(encoding="utf-8").strip().splitlines()
            if line and _has_brain(Path(line[0].strip())):
                return Path(line[0].strip())
    except OSError:
        pass
    start = Path(cwd) if cwd is not None else Path.cwd()
    if _has_brain(start):
        return start
    try:
        for child in sorted(start.iterdir()):
            if child.is_dir() and _has_brain(child):
                return child
    except OSError:
        pass
    for parent in start.parents:
        if _has_brain(parent):
            return parent
    return None
