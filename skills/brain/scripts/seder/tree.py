"""The logical tree and its mapping to physical folders.

`brain.json` holds the tree as a list of branches; each branch names the
physical folder it lives in (`physical`), so an adopted archive keeps its
existing folder names and other tools that depend on them keep working.
Every target folder goes through `check_target` before anything is moved.
"""
import json
import re
from pathlib import Path

from .config import Config

ASSETS = Path(__file__).resolve().parents[2] / "assets"
FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _asset(lang: str) -> dict:
    return json.loads((ASSETS / f"tree.{lang}.json").read_text(encoding="utf-8"))


def physical_name(num: str, name: str) -> str:
    return f"{num}_{name.replace(' ', '_')}"


def _node(item: dict) -> dict:
    node = dict(item)
    node.setdefault("physical", physical_name(item["num"], item["name"]))
    node.setdefault("privacy", "open")
    node.setdefault("handoff", None)
    node.setdefault("locked_subfolders", [])
    node.setdefault("per_item", False)
    return node


def default_tree(lang: str) -> list[dict]:
    """The eight standard branches (00..06, 99), ready to be written into brain.json."""
    return [_node(i) for i in _asset(lang)["tree"]]


def addons(lang: str) -> list[dict]:
    """Optional branches the onboarding offers when relevant (07, 08, ...)."""
    return [_node(i) for i in _asset(lang)["addons"]]


def normalize(folder: str) -> str:
    # slashes only: a trailing space or dot inside a segment must stay visible to check_target
    return str(folder).replace("\\", "/").strip("/")


def _split(folder: str) -> tuple[str, str]:
    norm = normalize(folder)
    head, _, rest = norm.partition("/")
    return head, rest


def find_node(cfg: Config, segment: str) -> dict | None:
    """Match a branch by its number, its name, or its physical folder name."""
    seg = segment.strip()
    if not seg:
        return None
    for node in cfg.tree:
        canonical = physical_name(str(node.get("num", "")), str(node.get("name", "")))
        if seg in (node.get("num"), node.get("name"), node.get("physical"), node.get("id"), canonical):
            return node
    low = seg.casefold()
    for node in cfg.tree:
        if low in {str(node.get(k, "")).casefold() for k in ("name", "physical", "id")}:
            return node
    # "01_anything": the number prefix alone identifies the branch (the physical folder may have been renamed)
    m = re.match(r"^(\d{2})_", seg)
    if m:
        return next((n for n in cfg.tree if n.get("num") == m.group(1)), None)
    return None


def node_by_id(cfg: Config, node_id: str) -> dict | None:
    return next((n for n in cfg.tree if n.get("id") == node_id), None)


def resolve(cfg: Config, logical: str) -> Path:
    """`01_כספים/בנק`, `כספים/בנק` or `01/בנק` -> <root>/<physical of 01>/בנק."""
    head, rest = _split(logical)
    node = find_node(cfg, head)
    if node is None:
        raise ValueError(f"unknown branch: {head!r}")
    out = cfg.root / node["physical"]
    return out / rest if rest else out


def check_target(cfg: Config, folder: str) -> Path:
    """Validate a target folder and return its absolute path (it need not exist yet).

    Rejects: empty, `.`/`..` segments, Windows-forbidden characters, segments
    ending with a dot or a space, unknown branches, anything inside the brain
    folder, and anything that lands outside the root.
    """
    norm = normalize(folder)
    if not norm:
        raise ValueError("empty target")
    for seg in norm.split("/"):
        if seg in ("", ".", ".."):
            raise ValueError(f"bad path segment: {seg!r}")
        if FORBIDDEN.search(seg):
            raise ValueError(f"forbidden character in: {seg!r}")
        if seg != seg.rstrip(". "):
            raise ValueError(f"segment ends with a dot or space: {seg!r}")
    target = resolve(cfg, norm)
    root = cfg.root.resolve()
    home = cfg.home.resolve()
    abs_target = (root / target.relative_to(cfg.root)).resolve()
    if not abs_target.is_relative_to(root):
        raise ValueError("target is outside the root")
    if abs_target == home or abs_target.is_relative_to(home):
        raise ValueError("target is inside the brain folder")
    return target


def handoff_for(cfg: Config, folder: str) -> dict | None:
    """When the branch hands its documents to another engine, where its inbox is."""
    head, _ = _split(folder)
    node = find_node(cfg, head)
    h = node.get("handoff") if node else None
    if not h or not h.get("inbox"):
        return None
    return {"inbox": cfg.root / normalize(h["inbox"]), "originals": bool(h.get("originals", False))}


def allowed_subfolders(cfg: Config, node_id: str) -> list[str]:
    node = node_by_id(cfg, node_id)
    return list(node.get("subfolders", [])) if node else []
