"""Tests for file format readers."""

import os
import tempfile
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from formats import read_document, read_text, UnsupportedFormat


@pytest.fixture
def sample_dir(tmp_path):
    """Create sample files for testing."""
    # .txt file
    (tmp_path / "sample.txt").write_text("This is a plain text file.\nWith two lines.")

    # .md file
    (tmp_path / "sample.md").write_text("# Heading\n\nThis is **markdown** content.")

    # Empty file
    (tmp_path / "empty.txt").write_text("")

    # Unsupported extension
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")

    return tmp_path


class TestReadText:
    def test_reads_txt(self, sample_dir):
        content = read_text(str(sample_dir / "sample.txt"))
        assert "plain text file" in content
        assert "two lines" in content

    def test_reads_md(self, sample_dir):
        content = read_text(str(sample_dir / "sample.md"))
        assert "# Heading" in content
        assert "**markdown**" in content

    def test_empty_file(self, sample_dir):
        content = read_text(str(sample_dir / "empty.txt"))
        assert content == ""


class TestReadDocument:
    def test_dispatches_txt(self, sample_dir):
        content = read_document(str(sample_dir / "sample.txt"))
        assert "plain text file" in content

    def test_dispatches_md(self, sample_dir):
        content = read_document(str(sample_dir / "sample.md"))
        assert "Heading" in content

    def test_unsupported_format_raises(self, sample_dir):
        with pytest.raises(UnsupportedFormat):
            read_document(str(sample_dir / "image.png"))

    def test_unknown_extension(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("some data")
        with pytest.raises(UnsupportedFormat):
            read_document(str(f))

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_document(str(tmp_path / "nonexistent.txt"))


class TestReadDocx:
    def test_reads_docx(self, tmp_path):
        """Create a minimal .docx and verify extraction."""
        try:
            from docx import Document
        except ImportError:
            pytest.skip("python-docx not installed")

        doc = Document()
        doc.add_paragraph("First paragraph of the document.")
        doc.add_paragraph("Second paragraph with more content.")
        path = str(tmp_path / "test.docx")
        doc.save(path)

        content = read_document(path)
        assert "First paragraph" in content
        assert "Second paragraph" in content


class TestReadPdf:
    def test_reads_pdf(self, tmp_path):
        """Create a minimal PDF and verify extraction."""
        try:
            from pypdf import PdfReader
        except ImportError:
            pytest.skip("pypdf not installed")

        # Create a simple PDF with reportlab if available, otherwise skip
        try:
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError:
            pytest.skip("reportlab not installed (needed to create test PDF)")

        path = str(tmp_path / "test.pdf")
        c = rl_canvas.Canvas(path)
        c.drawString(72, 720, "This is a test PDF document.")
        c.save()

        content = read_document(path)
        assert "test PDF document" in content
