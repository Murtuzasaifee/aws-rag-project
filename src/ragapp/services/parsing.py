"""
src/ragapp/services/parsing.py

Document parsing service — extract text from PDF, DOCX, TXT, HTML, Markdown, etc.

This module provides the high-level parsing interface for the RAG application.
It uses a pluggable parser architecture with AWS Textract as the primary engine,
and fallback parsers for simpler document types.

Supported formats:
- PDF (via AWS Textract)
- DOCX (via AWS Textract or python-docx fallback)
- TXT (plain text with encoding detection)
- HTML (with BeautifulSoup or regex fallback)
- Markdown (with structure preservation)

The service handles:
- Automatic file type detection
- Encoding validation and UTF-8 normalization
- Multi-page document support
- Structured extraction (text, tables, forms)
- Comprehensive error handling and reporting
"""

from pathlib import Path
from typing import Optional, Any

from ragapp.schemas.parsing import ParsedDocument, ParsedDocumentResponse, DocumentType
from ragapp.services.parsers.factory import DocumentParserService, DefaultParserFactory
from ragapp.exception.parsing_exception import (
    ParsingException,
    create_error_response,
)
from ragapp.logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)


# ── Module-Level Parser Service ────────────────────────────────────────────

_parser_service: Optional[DocumentParserService] = None


def get_parser_service(aws_region: str = "us-east-1") -> DocumentParserService:
    """
    Get or initialize the global parser service.
    
    Args:
        aws_region: AWS region for Textract
        
    Returns:
        DocumentParserService instance
    """
    global _parser_service
    
    if _parser_service is None:
        factory = DefaultParserFactory(aws_region=aws_region)
        _parser_service = DocumentParserService(factory)
        logger.info("Initialized global parser service")
    
    return _parser_service


# ── High-Level Parsing Functions ───────────────────────────────────────────

async def parse_document(
    file_path: str | Path,
    metadata: Optional[dict[str, Any]] = None,
    document_type: Optional[DocumentType] = None,
    aws_region: str = "us-east-1",
) -> ParsedDocument:
    """
    Parse a document and extract structured content.
    
    This is the main entry point for document parsing. It:
    1. Auto-detects document type if not provided
    2. Selects appropriate parser
    3. Extracts and structures content
    4. Validates and normalizes text
    
    Args:
        file_path: Path to document file
        metadata: Optional custom metadata to attach
        document_type: Document type (auto-detected if None)
        aws_region: AWS region for Textract service
        
    Returns:
        ParsedDocument with extracted content
        
    Raises:
        Various ParsingException subclasses on failure
        
    Example:
        >>> document = await parse_document("report.pdf")
        >>> print(f"Extracted {document.total_pages} pages")
        >>> for page in document.pages:
        ...     print(f"Page {page.page_number}: {len(page.elements)} elements")
    """
    service = get_parser_service(aws_region)
    return await service.parse(
        str(file_path),
        metadata=metadata,
        document_type=document_type,
        allow_fallback=True,
    )


async def parse_document_safe(
    file_path: str | Path,
    metadata: Optional[dict[str, Any]] = None,
    document_type: Optional[DocumentType] = None,
    aws_region: str = "us-east-1",
) -> ParsedDocumentResponse:
    """
    Parse a document with comprehensive error handling.
    
    This is a safe wrapper that always returns a ParsedDocumentResponse,
    never raising exceptions. Useful for API endpoints.
    
    Args:
        file_path: Path to document file
        metadata: Optional custom metadata
        document_type: Document type (auto-detected if None)
        aws_region: AWS region for Textract
        
    Returns:
        ParsedDocumentResponse with success/error information
        
    Example:
        >>> response = await parse_document_safe("document.pdf")
        >>> if response.success:
        ...     print(f"Parsed {response.document.total_pages} pages")
        ... else:
        ...     print(f"Error: {response.error}")
    """
    try:
        document = await parse_document(
            file_path,
            metadata=metadata,
            document_type=document_type,
            aws_region=aws_region,
        )
        
        return ParsedDocumentResponse(
            success=True,
            document=document,
        )
        
    except ParsingException as e:
        logger.error("Parsing exception",
                    file=str(file_path),
                    error_code=e.error_code,
                    error=e.error_message)
        
        return ParsedDocumentResponse(
            success=False,
            error=e.error_message,
            error_details=create_error_response(e),
        )
        
    except Exception as e:
        logger.error("Unexpected error during parsing",
                    file=str(file_path),
                    error=str(e),
                    error_type=type(e).__name__)
        
        return ParsedDocumentResponse(
            success=False,
            error=f"Unexpected error: {str(e)}",
            error_details={
                "error_type": type(e).__name__,
                "file": str(file_path),
            }
        )


# ── Utility Functions ──────────────────────────────────────────────────────

def get_supported_document_types() -> list[str]:
    """
    Get list of supported document types.
    
    Returns:
        List of supported file types (e.g., ['pdf', 'txt', 'docx', 'md', 'html'])
    """
    service = get_parser_service()
    types = [dt.value for dt in service.get_supported_types()]
    # Add 'md' as an alias for 'markdown'
    if "markdown" in types and "md" not in types:
        types.append("md")
    return sorted(types)


def is_document_type_supported(file_path: str | Path) -> bool:
    """
    Check if a document type is supported.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file type is supported
    """
    try:
        from ragapp.services.parsers.utils import detect_document_type
        doc_type = detect_document_type(file_path)
        service = get_parser_service()
        return service.factory.supports_document_type(doc_type)
    except Exception:
        return False
