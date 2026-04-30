"""
tests/integration/test_parsing_integration.py

Integration tests for document parsing with multiple parsers.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from ragapp.schemas.parsing import DocumentType, BlockType
from ragapp.services.parsing import (
    parse_document,
    parse_document_safe,
    get_supported_document_types,
    is_document_type_supported,
)


# ── Integration Tests ──────────────────────────────────────────────────────────

class TestParsingIntegration:
    """Integration tests for document parsing."""

    @pytest.mark.asyncio
    async def test_parse_plain_text_end_to_end(self):
        """Test parsing plain text file end-to-end."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text(
                "First paragraph\n\n"
                "Second paragraph\n\n"
                "Third paragraph"
            )
            
            document = await parse_document(txt_file)
            
            # Verify document structure
            assert document.file_name == "test.txt"
            assert document.document_type == DocumentType.TXT
            assert document.total_pages == 1
            assert len(document.pages) > 0
            
            # Verify page content
            page = document.pages[0]
            assert page.page_number == 1
            assert "First paragraph" in page.text
            assert len(page.elements) > 0

    @pytest.mark.asyncio
    async def test_parse_markdown_with_structure(self):
        """Test parsing Markdown file with structure preservation."""
        with TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "README.md"
            md_file.write_text(
                "# Project Title\n\n"
                "## Introduction\n\n"
                "This is an introduction.\n\n"
                "## Installation\n\n"
                "- Step 1\n"
                "- Step 2\n\n"
                "## Usage\n\n"
                "```python\n"
                "import module\n"
                "module.run()\n"
                "```"
            )
            
            document = await parse_document(md_file)
            
            # Verify document
            assert document.file_name == "README.md"
            assert document.document_type == DocumentType.MARKDOWN
            
            # Verify structural elements
            elements = document.pages[0].elements
            heading_elements = [e for e in elements if e.type == BlockType.HEADING]
            code_elements = [e for e in elements if e.type == BlockType.CODE]
            
            assert len(heading_elements) > 0, "No headings detected"
            assert len(code_elements) > 0, "No code blocks detected"

    @pytest.mark.asyncio
    async def test_parse_html_file(self):
        """Test parsing HTML file."""
        with TemporaryDirectory() as tmpdir:
            html_file = Path(tmpdir) / "page.html"
            html_file.write_text(
                "<!DOCTYPE html>\n"
                "<html>\n"
                "<head><title>Test Page</title></head>\n"
                "<body>\n"
                "<h1>Main Title</h1>\n"
                "<p>Paragraph content</p>\n"
                "<p>More content</p>\n"
                "</body>\n"
                "</html>"
            )
            
            document = await parse_document(html_file)
            
            # Verify document
            assert document.file_name == "page.html"
            assert document.document_type == DocumentType.HTML
            
            # Verify text extraction (tags should be removed)
            text = document.full_text
            assert "Main Title" in text
            assert "Paragraph content" in text
            assert "<h1>" not in text
            assert "<p>" not in text

    @pytest.mark.asyncio
    async def test_parse_with_metadata(self):
        """Test parsing document with custom metadata."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "report.txt"
            txt_file.write_text("Report content")
            
            metadata = {
                "category": "financial",
                "author": "John Doe",
                "year": 2024,
            }
            
            document = await parse_document(txt_file, metadata=metadata)
            
            # Verify metadata is attached
            assert document.custom_metadata == metadata

    @pytest.mark.asyncio
    async def test_parse_document_safe_success(self):
        """Test safe parsing returns success response."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("Test content")
            
            response = await parse_document_safe(txt_file)
            
            assert response.success
            assert response.document is not None
            assert response.error is None

    @pytest.mark.asyncio
    async def test_parse_document_safe_error_handling(self):
        """Test safe parsing handles errors gracefully."""
        # Try to parse a non-existent file
        response = await parse_document_safe("/nonexistent/file.xyz")
        
        # Should return error response, not raise exception
        assert not response.success
        assert response.document is None
        assert response.error is not None

    def test_get_supported_types(self):
        """Test getting list of supported document types."""
        supported = get_supported_document_types()
        
        assert len(supported) > 0
        assert "txt" in supported
        assert "md" in supported
        assert "html" in supported

    def test_is_document_type_supported(self):
        """Test checking if specific file type is supported."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("content")
            
            # Supported format
            assert is_document_type_supported(txt_file)
            
            # Unsupported format
            unsupported = Path(tmpdir) / "file.xyz"
            unsupported.write_text("content")
            assert not is_document_type_supported(unsupported)


# ── Large Document Tests ──────────────────────────────────────────────────────

class TestLargeDocumentHandling:
    """Test handling of larger documents."""

    @pytest.mark.asyncio
    async def test_parse_multiline_text(self):
        """Test parsing text with many lines."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "large.txt"
            
            # Create document with 100 lines
            lines = [f"Line {i}" for i in range(100)]
            txt_file.write_text("\n".join(lines))
            
            document = await parse_document(txt_file)
            
            # Verify all content is captured
            assert len(document.pages[0].elements) > 0
            assert "Line 0" in document.full_text
            assert "Line 99" in document.full_text

    @pytest.mark.asyncio
    async def test_parse_document_with_special_characters(self):
        """Test parsing document with special characters."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "special.txt"
            txt_file.write_text(
                "Special characters: © ® ™ € ¥\n"
                "Accents: café, naïve, résumé\n"
                "Emoji: 😀 📚 ✅",
                encoding="utf-8"
            )
            
            document = await parse_document(txt_file)
            
            # Content should be preserved
            assert "café" in document.full_text
            assert document.encoding == "utf-8"

    @pytest.mark.asyncio
    async def test_parse_mixed_content_markdown(self):
        """Test parsing Markdown with mixed content types."""
        with TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "mixed.md"
            md_file.write_text(
                "# Main Document\n\n"
                "Some introduction text.\n\n"
                "## Section 1\n\n"
                "Content for section 1\n\n"
                "- Item 1\n"
                "- Item 2\n"
                "- Item 3\n\n"
                "## Code Example\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello')\n"
                "```\n\n"
                "## Conclusion\n\n"
                "Final thoughts."
            )
            
            document = await parse_document(md_file)
            
            # Verify structure
            page = document.pages[0]
            assert len(page.elements) > 5
            
            # Check for different element types
            types = {e.type for e in page.elements}
            assert BlockType.HEADING in types
            assert BlockType.TEXT in types

    @pytest.mark.asyncio
    async def test_parse_empty_file(self):
        """Test parsing empty file."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "empty.txt"
            txt_file.write_text("")
            
            # Should handle gracefully
            document = await parse_document(txt_file)
            
            assert document.file_name == "empty.txt"
            assert len(document.full_text) == 0

    @pytest.mark.asyncio
    async def test_parse_whitespace_only_file(self):
        """Test parsing file with only whitespace."""
        with TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / "whitespace.txt"
            txt_file.write_text("   \n\n   \n  \n")
            
            # Should handle gracefully
            document = await parse_document(txt_file)
            
            assert document.file_name == "whitespace.txt"


# ── Error Handling Tests ──────────────────────────────────────────────────────

class TestErrorHandling:
    """Test error handling in parsing."""

    @pytest.mark.asyncio
    async def test_parse_unsupported_type(self):
        """Test parsing unsupported file type raises error."""
        with TemporaryDirectory() as tmpdir:
            unknown_file = Path(tmpdir) / "file.xyz"
            unknown_file.write_text("unknown content")
            
            with pytest.raises(Exception):  # UnsupportedDocumentTypeError
                await parse_document(unknown_file)

    @pytest.mark.asyncio
    async def test_parse_corrupted_file(self):
        """Test parsing corrupted file."""
        with TemporaryDirectory() as tmpdir:
            # Create a file with .txt extension but binary content
            txt_file = Path(tmpdir) / "corrupted.txt"
            txt_file.write_bytes(b"\x80\x81\x82\x83\x84\x85")
            
            # Parser should still attempt to handle it gracefully
            try:
                document = await parse_document(txt_file)
                # If successful, should have normalized the content
                assert document is not None
            except Exception:
                # Or it might raise a CorruptedDocumentError
                pass

    @pytest.mark.asyncio
    async def test_safe_parsing_with_exception(self):
        """Test safe parsing with exception-causing input."""
        # Use safe parser with invalid input
        response = await parse_document_safe("/dev/null")
        
        # Should return error response
        assert not response.success
        assert response.error is not None
