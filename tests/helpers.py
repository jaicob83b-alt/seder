"""Synthetic documents for tests: small images and one-page PDFs with given text."""
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw


def make_pdf(path: Path, text: str = "hello", pages: int = 1) -> Path:
    """A PDF with `pages` pages, each carrying `text` as real (searchable) text."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"{text} {i + 1}" if pages > 1 else text, fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


def make_image(path: Path, size=(640, 480), color=(220, 220, 220), text: str = "") -> Path:
    """A plain image (JPEG/PNG by extension), optionally with a word drawn on it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, color)
    if text:
        ImageDraw.Draw(im).text((20, 20), text, fill=(0, 0, 0))
    im.save(path)
    return path
