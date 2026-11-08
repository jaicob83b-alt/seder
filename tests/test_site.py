"""The phone site and the folder sources: what it serves, what it refuses, and that approvals file documents."""
import http.client
import json
import os
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from helpers import make_image, make_pdf
from seder import config, pull, site


def _proposal(home, docs):
    (home / "_נכנס" / "_proposal.json").write_text(json.dumps({"docs": docs}, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def server(home):
    cfg = config.Config.load(home)
    cfg.data["name"] = "הארון"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), site.make_handler(cfg, "127.0.0.1", 0))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield cfg, httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def req(port, method, path, body=None, headers=None, host="127.0.0.1"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = {"Host": f"{host}:{port}"}
    h.update(headers or {})
    c.request(method, path, body=body, headers=h)
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, data, dict(r.getheaders())


def post(port, path, obj, extra=None):
    h = {"X-Seder": "1", "Content-Type": "application/json"}
    h.update(extra or {})
    return req(port, "POST", path, json.dumps(obj).encode(), h)


def test_page_and_state(server, home):
    cfg, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "electricity bill")
    _proposal(home, [{"pages": ["a.pdf"], "name": "2026-09_חשבון חשמל - דנה.pdf", "folder": "01_כספים/בנק", "why": "חשבון"}])
    code, body, hdr = req(port, "GET", "/")
    assert code == 200 and b"<html" in body and "frame-ancestors 'none'" in hdr["Content-Security-Policy"]
    code, body, _ = req(port, "GET", "/api/state")
    st = json.loads(body)
    assert st["name"] == "הארון" and st["docs"][0]["status"] == "waiting" and st["inbox"] == []


def test_approve_files_the_document(server, home):
    cfg, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "electricity bill")
    _proposal(home, [{"pages": ["a.pdf"], "name": "2026-09_חשבון חשמל - דנה.pdf", "folder": "01_כספים/בנק", "why": "חשבון"}])
    code, body, _ = post(port, "/api/apply", {"n": 1})
    assert code == 200 and json.loads(body)["ok"], body
    assert (cfg.root / "01_כספים" / "בנק" / "2026-09_חשבון חשמל - דנה.pdf").is_file()
    st = json.loads(req(port, "GET", "/api/state")[1])
    assert st["docs"][0]["status"] == "done"


def test_new_folder_needs_explicit_mkdir(server, home):
    cfg, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "x")
    _proposal(home, [{"pages": ["a.pdf"], "name": "x.pdf", "folder": "01_כספים/חדש", "new_folder": True}])
    code, body, _ = post(port, "/api/apply", {"n": 1})
    assert code == 409 and json.loads(body)["error"] == "needs_folder" and not (cfg.root / "01_כספים" / "חדש").exists()
    code, body, _ = post(port, "/api/apply", {"n": 1, "mkdir": True})
    assert code == 200 and (cfg.root / "01_כספים" / "חדש" / "x.pdf").is_file()


def test_reject_marks_and_keeps_the_file(server, home):
    cfg, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "x")
    _proposal(home, [{"pages": ["a.pdf"], "name": "x.pdf", "folder": "01_כספים/בנק"}])
    assert post(port, "/api/reject", {"n": 1})[0] == 200
    assert (home / "_נכנס" / "a.pdf").is_file()
    assert json.loads(req(port, "GET", "/api/state")[1])["docs"][0]["status"] == "rejected"
    assert post(port, "/api/apply", {"n": 1})[0] == 400


def test_upload_lands_in_inbox_with_a_safe_name(server, home):
    cfg, port = server
    img = make_image(home.parent / "p.jpg")
    code, body, _ = req(port, "POST", "/api/upload", img.read_bytes(),
                        {"X-Seder": "1", "Content-Type": "image/jpeg", "X-Filename": "..%2F..%2Fevil.jpg"})
    name = json.loads(body)["file"]
    assert code == 200 and name.startswith("phone_") and (home / "_נכנס" / name).is_file()
    code, _, _ = req(port, "POST", "/api/upload", b"MZ...", {"X-Seder": "1", "X-Filename": "run.exe"})
    assert code == 400


@pytest.mark.parametrize("hdrs", [{}, {"X-Seder": "1", "Origin": "http://evil.example"}])
def test_post_without_header_or_from_another_origin_is_refused(server, home, hdrs):
    cfg, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "x")
    _proposal(home, [{"pages": ["a.pdf"], "name": "x.pdf", "folder": "01_כספים/בנק"}])
    code, _, _ = req(port, "POST", "/api/apply", b'{"n":1}', hdrs)
    assert code == 403 and (home / "_נכנס" / "a.pdf").is_file()


def test_foreign_host_header_is_refused(server):
    _, port = server
    assert req(port, "GET", "/api/state", host="evil.example")[0] == 403


@pytest.mark.parametrize("q", ["/api/file?path=../../etc/passwd", "/api/file?path=00_%D7%94%D7%9E%D7%95%D7%97/brain.json",
                               "/api/inbox-file?file=../brain.json", "/api/thumb?file=_proposal.json"])
def test_path_escapes_are_refused(server, q):
    _, port = server
    assert req(port, "GET", q)[0] in (400, 404)


def test_search_and_open_filed_document(server, home):
    cfg, port = server
    make_pdf(cfg.root / "01_כספים" / "בנק" / "2026-08_חשבון חשמל - דנה.pdf", "x")
    from seder import index
    index.rebuild(cfg)
    res = json.loads(req(port, "GET", "/api/search?q=%D7%97%D7%A9%D7%9E%D7%9C")[1])["results"]
    assert res and res[0]["name"].startswith("2026-08")
    code, body, hdr = req(port, "GET", "/api/file?path=" + __import__("urllib.parse").parse.quote(res[0]["path"]))
    assert code == 200 and body.startswith(b"%PDF")


def test_thumbnail_of_pdf_and_image(server, home):
    _, port = server
    make_pdf(home / "_נכנס" / "a.pdf", "x")
    make_image(home / "_נכנס" / "b.jpg")
    assert req(port, "GET", "/api/thumb?file=a.pdf")[2]["Content-Type"] == "image/png"
    assert req(port, "GET", "/api/thumb?file=b.jpg")[2]["Content-Type"] == "image/jpeg"


def test_bind_refuses_lan_and_any():
    for addr in ("0.0.0.0", "192.168.1.5", "10.0.0.2", "8.8.8.8", "nonsense"):
        assert not site.allowed_bind(addr)
    assert site.allowed_bind("127.0.0.1") and site.allowed_bind("100.92.66.63")
    with pytest.raises(ValueError):
        site.serve(None, bind="0.0.0.0", port=0)


def test_autostart_writes_and_removes_one_file(home, tmp_path, monkeypatch):
    monkeypatch.setattr(site, "_startup_dir", lambda: tmp_path)
    cfg = config.Config.load(home)
    out = site.autostart(cfg, "install", Path("brain.py"), "python")
    text = (tmp_path / site.STARTUP_FILE).read_text(encoding="utf-8")
    assert out["installed"] and "site --wait-tailscale" in text and str(cfg.home) in text and "chcp 65001" in text
    assert site.autostart(cfg, "remove", Path("brain.py"), "python")["removed"]
    assert not (tmp_path / site.STARTUP_FILE).exists()


# ---------- folder sources ----------

def _old(p: Path, days: float):
    t = time.time() - days * 86400
    os.utime(p, (t, t))


def test_pull_copies_new_documents_once(home, tmp_path):
    cfg = config.Config.load(home)
    src = tmp_path / "phone_downloads"
    src.mkdir()
    pull.add(cfg, src, "הורדות טלפון")
    new = make_image(src / "bill.jpg")
    _old(new, 0.01)
    old = make_image(src / "old.jpg", color=(10, 10, 10))
    _old(old, 400)  # before the folder was added
    (src / "note.mp4").write_bytes(b"x" * 5000)  # not a document
    (src / "half.pdf.crdownload").write_bytes(b"x" * 5000)
    out = pull.pull(config.Config.load(home))
    assert out["copied"] == 1 and (home / "_נכנס" / "bill.jpg").is_file() and new.is_file()
    assert pull.pull(config.Config.load(home))["copied"] == 0  # copied once, by content
    (home / "_נכנס" / "bill.jpg").unlink()
    assert pull.pull(config.Config.load(home))["copied"] == 0  # filed or removed: not copied again


def test_sources_refuse_brain_folder_and_duplicates(home, tmp_path):
    cfg = config.Config.load(home)
    with pytest.raises(ValueError):
        pull.add(cfg, home / "_נכנס")
    d = tmp_path / "d"
    d.mkdir()
    pull.add(cfg, d)
    with pytest.raises(ValueError):
        pull.add(cfg, d)
    assert pull.remove(config.Config.load(home), d) and pull.folders(config.Config.load(home)) == []
