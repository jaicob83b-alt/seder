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


PLAN_KEYS = {"addons", "rename", "subfolders", "subfolders_add", "drop", "items", "extra"}
KEEP = {"brain", "archive"}


def _check_name(name: str) -> str:
    name = str(name).strip()
    if not name or FORBIDDEN.search(name) or name != name.rstrip(". ") or name in (".", ".."):
        raise ValueError(f"bad folder name: {name!r}")
    return name


def build(lang: str, addon_ids: list[str] = (), plan: dict | None = None) -> list[dict]:
    """The standard tree, plus add-ons, tailored by a plan the person approved.

    plan keys (all optional):
      addons          more add-on ids
      rename          {branch_id: new name}         the physical folder follows the new name
      subfolders      {branch_id: [names]}          replaces the allowed subfolders
      subfolders_add  {branch_id: [names]}          appends to them
      drop            [branch_id]                   a standard branch the person does not want (not 00, not 99)
      items           {branch_id: [names]}          the known items of a per-item branch (a car, a person)
      extra           [{name, subfolders, per_item, item, rule}]  a branch of their own, numbered after the rest
    Nothing here creates a folder; folders appear with the first filed document.
    """
    plan = dict(plan or {})
    unknown = set(plan) - PLAN_KEYS
    if unknown:
        raise ValueError(f"unknown plan key(s): {', '.join(sorted(unknown))}")
    branches = default_tree(lang)
    known_addons = {a["id"]: a for a in addons(lang)}
    wanted = list(dict.fromkeys(list(addon_ids or []) + list(plan.get("addons") or [])))
    bad = [a for a in wanted if a not in known_addons]
    if bad:
        raise ValueError(f"unknown add-on(s): {', '.join(bad)}; choose from {', '.join(known_addons)}")
    branches += [known_addons[a] for a in wanted]
    by_id = {n["id"]: n for n in branches}

    def node(bid):
        if bid not in by_id:
            raise ValueError(f"unknown branch in plan: {bid!r}")
        return by_id[bid]

    drop = set(plan.get("drop") or [])
    if drop & KEEP:
        raise ValueError("the brain (00) and archive (99) branches cannot be dropped")
    for bid in drop:
        node(bid)
    for bid, name in (plan.get("rename") or {}).items():
        n = node(bid)
        n["name"] = _check_name(name)
        n["physical"] = physical_name(n["num"], n["name"])
    for bid, subs in (plan.get("subfolders") or {}).items():
        node(bid)["subfolders"] = [_check_name(s) for s in subs]
    for bid, subs in (plan.get("subfolders_add") or {}).items():
        n = node(bid)
        n["subfolders"] = list(n.get("subfolders", []))
        for s in subs:
            s = _check_name(s)
            if s not in n["subfolders"]:
                n["subfolders"].append(s)
    for bid, items in (plan.get("items") or {}).items():
        n = node(bid)
        if not n.get("per_item"):
            raise ValueError(f"branch {bid!r} has no items (it is not one folder per item)")
        n["items"] = [_check_name(i) for i in items]
    branches = [n for n in branches if n["id"] not in drop]
    used = {int(n["num"]) for n in branches if str(n["num"]).isdigit()} | {int(a["num"]) for a in known_addons.values()}
    for ex in plan.get("extra") or []:
        name = _check_name(ex["name"])
        num = next(i for i in range(7, 99) if i not in used)
        used.add(num)
        bid = re.sub(r"\W+", "_", name).strip("_").lower() or f"extra_{num}"
        if bid in {n["id"] for n in branches}:
            bid = f"{bid}_{num}"
        branches.append(_node({"id": bid, "num": f"{num:02d}", "name": name,
                               "per_item": bool(ex.get("per_item", False)), "item": ex.get("item", ""),
                               "subfolders": [_check_name(s) for s in ex.get("subfolders", [])],
                               "locked_subfolders": [], "rule": ex.get("rule", ""), "custom": True}))
    branches.sort(key=lambda n: n["num"])
    return branches


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
