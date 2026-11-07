from helpers import make_image, make_pdf
from seder import pdf


def test_build_pdf_from_images_and_pdf(tmp_path):
    a = make_image(tmp_path / "a.jpg", size=(3000, 2000))   # long side above the 2400 cap
    b = make_image(tmp_path / "b.png", size=(400, 600))
    c = make_pdf(tmp_path / "c.pdf", "page", pages=1)
    out = tmp_path / "out.pdf"
    n = pdf.build_pdf([a, b, c], [0, 90, 0], out)
    assert n == 3 and out.exists() and pdf.page_count(out) == 3


def test_build_pdf_refuses_to_overwrite(tmp_path):
    a = make_image(tmp_path / "a.jpg")
    out = tmp_path / "out.pdf"
    out.write_bytes(b"x")
    try:
        pdf.build_pdf([a], [0], out)
        assert False, "expected FileExistsError"
    except FileExistsError:
        pass


def test_text_sample_reads_first_page_text(tmp_path):
    p = make_pdf(tmp_path / "t.pdf", "Electricity bill 2026-09", pages=2)
    s = pdf.text_sample(p)
    assert "Electricity bill 2026-09" in s and "2" not in s.split("2026-09")[-1]  # first page only


def test_text_sample_empty_for_image_pdf(tmp_path):
    a = make_image(tmp_path / "a.jpg")
    out = tmp_path / "img.pdf"
    pdf.build_pdf([a], [0], out)
    assert pdf.text_sample(out) == ""


def test_text_sample_empty_for_non_pdf(tmp_path):
    a = make_image(tmp_path / "a.jpg")
    assert pdf.text_sample(a) == ""
