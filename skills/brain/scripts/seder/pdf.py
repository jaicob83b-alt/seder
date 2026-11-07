"""PDF building and reading, all local: images and PDFs in, one PDF out; text of the first page.

PyMuPDF is not thread-safe, so every call runs under `PDF_LOCK`.
"""
import io
import threading
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

PDF_LOCK = threading.RLock()
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
MAX_SIDE = 2400  # px; phone photos above this are scaled down


def _image_as_pdf(path: Path, rotation: int) -> bytes:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if rotation % 360:
        im = im.rotate(-rotation, expand=True)  # PIL rotates counter-clockwise; we mean clockwise
    long_side = max(im.size)
    if long_side > MAX_SIDE:
        r = MAX_SIDE / long_side
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PDF", resolution=200, quality=82)
    return buf.getvalue()


def build_pdf(pages: list, rotations: list, out: Path) -> int:
    """Join images and PDFs, in order, into `out`. Returns the page count. Never overwrites."""
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"already exists, not overwriting: {out}")
    pages = [Path(p) for p in pages]
    if not pages:
        raise ValueError("no pages")
    rotations = [int(r or 0) for r in rotations] + [0] * (len(pages) - len(rotations))
    with PDF_LOCK:
        doc = pymupdf.open()
        try:
            for p, rot in zip(pages, rotations):
                if p.suffix.lower() == ".pdf":
                    src = pymupdf.open(str(p))
                    first = len(doc)
                    doc.insert_pdf(src)
                    src.close()
                    if rot % 360:
                        for i in range(first, len(doc)):
                            doc[i].set_rotation((doc[i].rotation + rot) % 360)
                else:
                    img = pymupdf.open("pdf", _image_as_pdf(p, rot))
                    doc.insert_pdf(img)
                    img.close()
            out.parent.mkdir(parents=True, exist_ok=True)
            n = len(doc)
            doc.save(str(out), garbage=3, deflate=True)
        finally:
            doc.close()
    return n


def page_count(path: Path) -> int:
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return 1 if path.suffix.lower() in IMAGE_EXT else 0
    with PDF_LOCK:
        try:
            doc = pymupdf.open(str(path))
        except Exception:
            return 0
        try:
            return len(doc)
        finally:
            doc.close()


def text_sample(path: Path, max_chars: int = 2000) -> str:
    """Text of the first page (local extraction, no model). Empty for scans and non-PDFs."""
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return ""
    with PDF_LOCK:
        try:
            doc = pymupdf.open(str(path))
        except Exception:
            return ""
        try:
            if len(doc) == 0:
                return ""
            return doc[0].get_text().strip()[:max_chars]
        except Exception:
            return ""
        finally:
            doc.close()
