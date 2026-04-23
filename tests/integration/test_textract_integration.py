"""
Integration tests for AWS Textract parser with real AWS service.

These tests require:
- AWS credentials configured (aws configure)
- Active AWS account with Textract permissions
- Test documents in tests/fixtures/
"""

import pytest
from pathlib import Path
from ragapp.services.parsers.textract_parser import AWSTextractParser
from ragapp.schemas.parsing import DocumentType, ParsingBackend


class TestTextractIntegration:
    """Integration tests with real AWS Textract service."""

    @pytest.fixture
    def parser(self):
        """Create Textract parser instance."""
        return AWSTextractParser()

    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a simple test PDF file."""
        # For this test, we'll create a minimal PDF
        # In production, you'd use actual PDF files
        pdf_path = tmp_path / "test_document.pdf"
        
        # Create a minimal PDF with text
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello from Textract Test) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000220 00000 n 
0000000333 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
428
%%EOF
"""
        pdf_path.write_bytes(pdf_content)
        return pdf_path

    @pytest.mark.asyncio
    async def test_textract_parse_pdf(self, parser, sample_pdf):
        """Test parsing PDF with real AWS Textract."""
        try:
            result = await parser.parse(sample_pdf, DocumentType.PDF)
            
            # Verify result structure
            assert result is not None
            assert result.file_name == "test_document.pdf"
            assert result.document_type == DocumentType.PDF
            assert result.parsing_backend == ParsingBackend.AWS_TEXTRACT
            assert result.total_pages > 0
            assert len(result.full_text) > 0
            
            print(f"✅ Successfully parsed PDF")
            print(f"   - Pages: {result.total_pages}")
            print(f"   - Text length: {len(result.full_text)} chars")
            print(f"   - Tables: {result.total_tables}")
            print(f"   - Forms: {result.total_forms}")
            
        except Exception as e:
            if "credentials" in str(e).lower() or "not configured" in str(e).lower():
                pytest.skip("AWS credentials not configured - skipping Textract test")
            raise

    @pytest.mark.asyncio
    async def test_textract_extract_tables(self, parser, sample_pdf):
        """Test table extraction with Textract."""
        try:
            result = await parser.parse(sample_pdf, DocumentType.PDF)
            
            # Verify table extraction capability
            assert hasattr(result, 'pages')
            assert len(result.pages) > 0
            
            # Check if any tables were extracted
            total_tables = sum(len(page.tables) for page in result.pages)
            print(f"✅ Table extraction test passed - Found {total_tables} tables")
            
        except Exception as e:
            if "credentials" in str(e).lower():
                pytest.skip("AWS credentials not configured")
            raise

    @pytest.mark.asyncio
    async def test_textract_parse_with_confidence(self, parser, sample_pdf):
        """Test confidence score tracking from Textract."""
        try:
            result = await parser.parse(sample_pdf, DocumentType.PDF)
            
            # Verify confidence tracking
            if result.average_confidence is not None:
                assert 0 <= result.average_confidence <= 1
                print(f"✅ Confidence score: {result.average_confidence:.2f}")
            else:
                print("✅ No confidence scores (expected for simple documents)")
            
        except Exception as e:
            if "credentials" in str(e).lower():
                pytest.skip("AWS credentials not configured")
            raise


class TestTextractWithRealDocument:
    """Tests using real document files if available."""

    @pytest.mark.asyncio
    async def test_parse_real_pdf_if_exists(self):
        """Test with real PDF file if available in fixtures."""
        pdf_path = Path("tests/fixtures/sample.pdf")
        
        if not pdf_path.exists():
            pytest.skip(f"Test document not found at {pdf_path}")
        
        parser = AWSTextractParser()
        
        try:
            result = await parser.parse(pdf_path, DocumentType.PDF)
            
            assert result is not None
            assert result.total_pages > 0
            print(f"✅ Parsed real PDF: {pdf_path}")
            print(f"   - Pages: {result.total_pages}")
            print(f"   - Text preview: {result.full_text[:200]}...")
            
        except Exception as e:
            if "credentials" in str(e).lower():
                pytest.skip("AWS credentials not configured")
            raise

    @pytest.mark.asyncio
    async def test_parse_real_docx_if_exists(self):
        """Test with real DOCX file if available in fixtures."""
        docx_path = Path("tests/fixtures/sample.docx")
        
        if not docx_path.exists():
            pytest.skip(f"Test document not found at {docx_path}")
        
        parser = AWSTextractParser()
        
        try:
            result = await parser.parse(docx_path, DocumentType.DOCX)
            
            assert result is not None
            assert result.total_pages > 0
            print(f"✅ Parsed real DOCX: {docx_path}")
            print(f"   - Pages: {result.total_pages}")
            
        except Exception as e:
            if "credentials" in str(e).lower():
                pytest.skip("AWS credentials not configured")
            raise
