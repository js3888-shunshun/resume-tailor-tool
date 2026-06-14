"""Extract plain text from an uploaded resume file.

Supports PDF (via pypdf), and treats .txt/.tex/.md/anything else as UTF-8 text.
(.docx is intentionally out of scope for now — export to PDF instead.)
"""

from __future__ import annotations

import io


def extract_text(filename: str, data: bytes) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return _extract_pdf(data)
    # txt / tex / md / unknown -> decode as text.
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts).strip()
