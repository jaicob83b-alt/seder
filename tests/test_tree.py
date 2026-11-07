import pytest

from seder import config, tree


def test_default_tree_shape():
    t = tree.default_tree("he")
    assert [n["num"] for n in t] == ["00", "01", "02", "03", "04", "05", "06", "99"]
    assert next(n for n in t if n["num"] == "03")["locked_subfolders"] == ["בריאות"]
    assert tree.default_tree("en")[1]["name"] == "Finance"
    assert all(n["physical"] == f"{n['num']}_{n['name'].replace(' ', '_')}" for n in t)
    assert [n["per_item"] for n in t] == [False, False, True, True, True, True, True, False]


def test_addons_shape():
    a = tree.addons("he")
    assert [n["num"] for n in a[:2]] == ["07", "08"]
    assert len(a) == 7 and all(n["num"] for n in a[2:])
    assert tree.addons("en")[0]["name"] == "Dev projects"


def test_resolve_by_num_name_physical(home):
    cfg = config.Config.load(home)
    assert tree.resolve(cfg, "01_כספים/בנק") == cfg.root / "01_כספים" / "בנק"
    assert tree.resolve(cfg, "כספים/בנק") == cfg.root / "01_כספים" / "בנק"
    assert tree.resolve(cfg, "01/בנק") == cfg.root / "01_כספים" / "בנק"


def test_resolve_uses_physical_mapping(home):
    cfg = config.Config.load(home)
    cfg.tree[1]["physical"] = "X_old_money"
    cfg.save()
    assert tree.resolve(config.Config.load(home), "01_כספים/בנק") == cfg.root / "X_old_money" / "בנק"


def test_resolve_unknown_branch_is_error(home):
    with pytest.raises(ValueError):
        tree.resolve(config.Config.load(home), "77_אין/x")


@pytest.mark.parametrize("bad", ["../x", "01_כספים/../..", "00_המוח/x", "01_כספים/a:b", "C:/Windows", "", "01_כספים/x.", "01_כספים/x "])
def test_check_target_rejects(home, bad):
    with pytest.raises(ValueError):
        tree.check_target(config.Config.load(home), bad)


def test_check_target_accepts_backslashes(home):
    cfg = config.Config.load(home)
    assert tree.check_target(cfg, "01_כספים\\בנק") == cfg.root / "01_כספים" / "בנק"


def test_check_target_accepts_new_subfolder_of_known_branch(home):
    cfg = config.Config.load(home)
    assert tree.check_target(cfg, "02_בית/דירה בחיפה") == cfg.root / "02_בית" / "דירה בחיפה"


def test_handoff(home):
    cfg = config.Config.load(home)
    cfg.tree[1]["handoff"] = {"inbox": "01_כספים/_inbox", "originals": True}
    cfg.save()
    h = tree.handoff_for(config.Config.load(home), "01_כספים/בנק")
    assert h["originals"] is True and h["inbox"] == cfg.root / "01_כספים" / "_inbox"
    assert tree.handoff_for(cfg, "02_בית") is None


def test_allowed_subfolders(home):
    cfg = config.Config.load(home)
    assert "בנק" in tree.allowed_subfolders(cfg, "finance")
    assert tree.allowed_subfolders(cfg, "nope") == []
