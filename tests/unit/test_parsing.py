"""
tests/unit/test_parsing.py

Unit tests for document parsing components.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from tempfile import NamedTemporaryFile

from ragapp.schemas.parsing import (
    DocumentType,
    ParsedDocument,
    ParsingBackend,
    BlockType,
)
from ragapp.services.parsers.utils import (
    detect_document_type,
    detect_encoding,
    is_html_like,
    is_markdown_like,
)
from ragapp.services.parsers.base import BaseDocumentParser
from ragapp.services.parsers.factory import DefaultParserFactory, DocumentParserService
from ragapp.services.parsers.fallback_parsers import (
    PlainTextParser,
    MarkdownParser,
    HTMLParser,
)
from ragapp.exception.parsing_exception import (
    UnsupportedDocumentTypeError,
    ParsingException,
    CorruptedDocumentError,
)


# ── File Type Detection Tests ──────────────────────────────────────────────────

class TestDocumentTypeDetection:
    """Test document type detection from file extensions and magic bytes."""

    def test_detect_pdf_by_extension(self, tmp_path):
        """Test PDF detection by extension."""
        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")
        
        assert detect_document_type(pdf_file) == DocumentType.PDF

    def test_detect_txt_by_extension(self, tmp_path):
        """Test TXT detection by extension."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Hello world")
        
        assert detect_document_type(txt_file) == DocumentType.TXT

    def test_detect_html_by_extension(self, tmp_path):
        """Test HTML detection by extension."""
        html_file = tmp_path / "page.html"
        html_file.write_text("<html><body>Test</body></html>")
        
        assert detect_document_type(html_file) == DocumentType.HTML

    def test_detect_markdown_by_extension(self, tmp_path):
        """Test Markdown detection by extension."""
        md_file = tmp_path / "document.md"
        md_file.write_text("# Heading\n\nContent")
        
        assert detect_document_type(md_file) == DocumentType.MARKDOWN

    def test_file_not_found_raises_error(self):
        """Test that non-existent file raises error."""
        with pytest.raises(Exception):  # ParsingFileNotFoundError
            detect_document_type("/nonexistent/file.pdf")

    def test_unsupported_extension_raises_error(self, tmp_path):
        """Test that unsupported file type raises error."""
        unknown_file = tmp_path / "document.xyz"
        unknown_file.write_text("unknown format")
        
        with pytest.raises(UnsupportedDocumentTypeError):
            detect_document_type(unknown_file)


# ── Encoding Detection Tests ───────────────────────────────────────────────────

class TestEncodingDetection:
    """Test encoding detection for text files."""

    def test_detect_utf8_encoding(self, tmp_path):
        """Test UTF-8 encoding detection."""
        file = tmp_path / "utf8.txt"
        file.write_text("Hello world with UTF-8: café", encoding="utf-8")
        
        encoding = detect_encoding(file)
        assert encoding.lower() in ["utf-8", "utf8", "ascii"]

    def test_detect_encoding_with_special_chars(self, tmp_path):
        """Test encoding detection with special characters."""
        file = tmp_path / "special.txt"
        file.write_text("Ñoño señor", encoding="utf-8")
        
        encoding = detect_encoding(file)
        # Should detect utf-8 or close variant
        assert encoding is not None

    def test_encoding_detection_returns_string(self, tmp_path):
        """Test that encoding detection returns a string."""
        file = tmp_path / "test.txt"
        file.write_text("test content")
        
        encoding = detect_encoding(file)
        assert isinstance(encoding, str)
        assert len(encoding) > 0


# ── Content Structure Detection Tests ──────────────────────────────────────────

class TestContentStructureDetection:
    """Test detection of HTML and Markdown content."""

    def test_is_html_like_detects_html(self):
        """Test HTML content detection."""
        html = "<html><body>Content</body></html>"
        assert is_html_like(html)

    def test_is_html_like_with_doctype(self):
        """Test detection of HTML with DOCTYPE."""
        html = "<!DOCTYPE html><html></html>"
        assert is_html_like(html)

    def test_is_html_like_detects_non_html(self):
        """Test that plain text is not detected as HTML."""
        text = "This is plain text without any HTML"
        assert not is_html_like(text)

    def test_is_markdown_like_detects_markdown(self):
        """Test Markdown content detection."""
        markdown = "# Heading\n\n**Bold text** and *italic*"
        assert is_markdown_like(markdown)

    def test_is_markdown_like_detects_lists(self):
        """Test Markdown list detection."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        assert is_markdown_like(markdown)

    def test_is_markdown_like_detects_code(self):
        """Test Markdown code block detection."""
        markdown = "Some text\n\n```python\ncode here\n```\n\nMore text"
        assert is_markdown_like(markdown)


# ── Plain Text Parser Tests ────────────────────────────────────────────────────

class TestPlainTextParser:
    """Test plain text parser."""

    @pytest.mark.asyncio
    async def test_parse_plain_text(self, tmp_path):
        """Test parsing plain text file."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Line 1\n\nLine 2\n\nLine 3")
        
        parser = PlainTextParser()
        document = await parser.parse(txt_file, DocumentType.TXT)
        
        assert document.file_name == "document.txt"
        assert document.document_type == DocumentType.TXT
        assert document.total_pages == 1
        assert len(document.pages) == 1

    @pytest.mark.asyncio
    async def test_plain_text_parser_supports_txt(self):
        """Test that parser supports TXT type."""
        parser = PlainTextParser()
        assert parser.supports_document_type(DocumentType.TXT)

    @pytest.mark.asyncio
    async def test_plain_text_parser_doesnt_support_pdf(self):
        """Test that parser doesn't support PDF."""
        parser = PlainTextParser()
        assert not parser.supports_document_type(DocumentType.PDF)

    @pytest.mark.asyncio
    async def test_validate_text_file(self, tmp_path):
        """Test file validation."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        
        parser = PlainTextParser()
        is_valid, error = await parser.validate_file(txt_file)
        
        assert is_valid
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_nonexistent_file(self):
        """Test validation of nonexistent file."""
        parser = PlainTextParser()
        is_valid, error = await parser.validate_file("/nonexistent.txt")
        
        assert not is_valid
        assert error is not None


# ── Markdown Parser Tests ──────────────────────────────────────────────────────

class TestMarkdownParser:
    """Test Markdown parser."""

    @pytest.mark.asyncio
    async def test_parse_markdown_with_structure(self, tmp_path):
        """Test parsing Markdown with structural elements."""
        md_file = tmp_path / "document.md"
        md_file.write_text(
            "# Main Heading\n\n"
            "Some content\n\n"
            "## Subheading\n\n"
            "- Item 1\n"
            "- Item 2\n"
        )
        
        parser = MarkdownParser()
        document = await parser.parse(md_file, DocumentType.MARKDOWN)
        
        assert document.file_name == "document.md"
        assert document.document_type == DocumentType.MARKDOWN
        assert len(document.pages) == 1
        
        # Check that structural elements were extracted
        elements = document.pages[0].elements
        assert len(elements) > 0

    @pytest.mark.asyncio
    async def test_markdown_parser_detects_headings(self, tmp_path):
        """Test heading detection in Markdown."""
        md_file = tmp_path / "headings.md"
        md_file.write_text("# H1\n\n## H2\n\n### H3")
        
        parser = MarkdownParser()
        document = await parser.parse(md_file, DocumentType.MARKDOWN)
        
        elements = document.pages[0].elements
        heading_elements = [e for e in elements if e.type == BlockType.HEADING]
        assert len(heading_elements) > 0


# ── HTML Parser Tests ──────────────────────────────────────────────────────────

class TestHTMLParser:
    """Test HTML parser."""

    @pytest.mark.asyncio
    async def test_parse_simple_html(self, tmp_path):
        """Test parsing simple HTML."""
        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html>\n"
            "<body>\n"
            "<h1>Title</h1>\n"
            "<p>Content</p>\n"
            "</body>\n"
            "</html>"
        )
        
        parser = HTMLParser()
        document = await parser.parse(html_file, DocumentType.HTML)
        
        assert document.file_name == "page.html"
        assert document.document_type == DocumentType.HTML

    @pytest.mark.asyncio
    async def test_html_text_extraction(self, tmp_path):
        """Test that HTML tags are stripped."""
        html_file = tmp_path / "page.html"
        html_file.write_text("<html><body><p>Hello <b>World</b></p></body></html>")
        
        parser = HTMLParser()
        document = await parser.parse(html_file, DocumentType.HTML)
        
        # Text should be extracted without tags
        assert "Hello" in document.full_text
        assert "<p>" not in document.full_text


# ── Parser Factory Tests ───────────────────────────────────────────────────────

class TestDefaultParserFactory:
    """Test parser factory."""

    def test_factory_initialization(self):
        """Test factory initializes with default parsers."""
        factory = DefaultParserFactory()
        
        parsers = factory.get_available_parsers()
        assert len(parsers) > 0

    def test_factory_supports_txt(self):
        """Test factory supports TXT type."""
        factory = DefaultParserFactory()
        assert factory.supports_document_type(DocumentType.TXT)

    def test_factory_supports_markdown(self):
        """Test factory supports Markdown type."""
        factory = DefaultParserFactory()
        assert factory.supports_document_type(DocumentType.MARKDOWN)

    def test_factory_get_parser_for_txt(self):
        """Test getting parser for TXT type."""
        factory = DefaultParserFactory()
        parser = factory.get_parser(DocumentType.TXT)
        
        assert parser is not None
        assert parser.supports_document_type(DocumentType.TXT)

    def test_factory_raises_for_unsupported_type(self):
        """Test factory raises error for unsupported type."""
        factory = DefaultParserFactory()
        
        # Create mock unsupported type
        with pytest.raises(UnsupportedDocumentTypeError):
            factory.get_parser(DocumentType.UNKNOWN)

    def test_factory_get_supported_types(self):
        """Test getting list of supported types."""
        factory = DefaultParserFactory()
        supported = factory.get_supported_types()
        
        assert len(supported) > 0
        assert DocumentType.TXT in supported


# ── Document Parser Service Tests ──────────────────────────────────────────────

class TestDocumentParserService:
    """Test high-level parser service."""

    @pytest.mark.asyncio
    async def test_service_parse_text_file(self, tmp_path):
        """Test parsing text file through service."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Test content")
        
        service = DocumentParserService()
        document = await service.parse(str(txt_file))
        
        assert document.document_type == DocumentType.TXT
        assert "Test content" in document.full_text

    @pytest.mark.asyncio
    async def test_service_auto_detects_type(self, tmp_path):
        """Test service auto-detects document type."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Heading\n\nContent")
        
        service = DocumentParserService()
        # Don't pass document_type, let service auto-detect
        document = await service.parse(str(md_file))
        
        assert document.document_type == DocumentType.MARKDOWN

    @pytest.mark.asyncio
    async def test_service_handles_metadata(self, tmp_path):
        """Test service attaches metadata to document."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Content")
        
        metadata = {"category": "test", "author": "tester"}
        service = DocumentParserService()
        document = await service.parse(str(txt_file), metadata=metadata)
        
        assert document.custom_metadata == metadata

    def test_service_get_supported_types(self):
        """Test getting supported types from service."""
        service = DocumentParserService()
        supported = service.get_supported_types()
        
        assert len(supported) > 0
        assert DocumentType.TXT in supported


# ── Exception Tests ────────────────────────────────────────────────────────────

class TestParsingExceptions:
    """Test parsing exception classes."""

    def test_unsupported_document_type_error(self):
        """Test UnsupportedDocumentTypeError."""
        with pytest.raises(UnsupportedDocumentTypeError):
            raise UnsupportedDocumentTypeError("xyz", ["pdf", "txt"])

    def test_corrupted_document_error(self):
        """Test CorruptedDocumentError."""
        error = CorruptedDocumentError("file.pdf", "File is malformed")
        assert error.file_name == "file.pdf"
        assert error.reason == "File is malformed"

    def test_parsing_exception_inheritance(self):
        """Test that specific exceptions inherit from ParsingException."""
        error = UnsupportedDocumentTypeError("type", [])
        assert isinstance(error, ParsingException)
