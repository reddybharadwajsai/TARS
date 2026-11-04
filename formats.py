"""File format readers — extract text from .txt, .md, .docx, .pdf."""

import os


class UnsupportedFormat(Exception):
    """Raised when a file extension is not supported."""
    pass


def read_text(path: str) -> str:
    """Read plain text or markdown files."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_docx(path: str) -> str:
    """Extract text from a .docx file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise UnsupportedFormat("python-docx is not installed. Run: pip install python-docx")

    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def read_pdf(path: str) -> str:
    """Extract text from a .pdf file using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise UnsupportedFormat("pypdf is not installed. Run: pip install pypdf")

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def read_document(path: str) -> str:
    """Dispatch to the appropriate reader based on file extension."""
    ext = os.path.splitext(path)[1].lower()

    if ext in (".txt", ".md"):
        return read_text(path)
    elif ext == ".docx":
        return read_docx(path)
    elif ext == ".pdf":
        return read_pdf(path)
    else:
        raise UnsupportedFormat(f"Cannot read '{ext}' files. Supported: .txt, .md, .docx, .pdf")
