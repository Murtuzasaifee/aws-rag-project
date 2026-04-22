"""
src/ragapp/schemas/parsing.py

Data models for document parsing results, including structured text extraction,
layout information, tables, forms, and other document elements.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    """Supported document file types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class BlockType(str, Enum):
    """Types of content blocks extracted from documents."""
    TEXT = "text"
    TABLE = "table"
    FORM = "form"
    IMAGE = "image"
    HEADING = "heading"
    SECTION = "section"
    LIST = "list"
    CODE = "code"


class ParsingBackend(str, Enum):
    """Available parsing backends/engines."""
    AWS_TEXTRACT = "aws_textract"
    FALLBACK_TEXTRACT = "fallback_textract"  # When file too small for native Textract
    SIMPLE_PARSER = "simple_parser"
    PYPDF = "pypdf"
    PYTHON_DOCX = "python_docx"
    BEAUTIFULSOUP = "beautifulsoup"
    MARKDOWN = "markdown"


# ── Cell/Row/Column Models ────────────────────────────────────────────────────

class TableCell(BaseModel):
    """A single cell within a table."""
    content: str = Field(..., description="Text content of the cell")
    row_index: int = Field(..., description="0-based row index")
    col_index: int = Field(..., description="0-based column index")
    is_header: bool = Field(default=False, description="Whether this is a header cell")
    confidence: Optional[float] = Field(
        None, 
        description="Confidence score (0-1) for content extraction (from OCR engines)"
    )


class TableRow(BaseModel):
    """A row within a table."""
    cells: list[TableCell] = Field(..., description="Cells in this row")
    row_index: int = Field(..., description="0-based row index")


class Table(BaseModel):
    """Structured table extracted from document."""
    rows: list[TableRow] = Field(..., description="Rows in the table")
    title: Optional[str] = Field(None, description="Table title if present")
    confidence: Optional[float] = Field(
        None,
        description="Average confidence score for table extraction"
    )
    page_number: Optional[int] = Field(None, description="Page this table appears on")
    

# ── Form Models ────────────────────────────────────────────────────────────────

class FormField(BaseModel):
    """A single form field (key-value pair)."""
    key: str = Field(..., description="Form field name/label")
    value: str = Field(..., description="Field value")
    confidence: Optional[float] = Field(
        None,
        description="Confidence score (0-1) for field extraction"
    )


class Form(BaseModel):
    """Structured form extracted from document."""
    fields: list[FormField] = Field(..., description="Form fields")
    form_type: Optional[str] = Field(None, description="Type of form (e.g., 'tax_form', 'application')")
    confidence: Optional[float] = Field(None, description="Average confidence for form extraction")
    page_number: Optional[int] = Field(None, description="Page this form appears on")


# ── Content Block Models ──────────────────────────────────────────────────────

class TextBlock(BaseModel):
    """A block of extracted text with metadata."""
    type: BlockType = Field(default=BlockType.TEXT, description="Type of content block")
    content: str = Field(..., description="Extracted text content")
    page_number: int = Field(..., description="Page number (1-based)")
    confidence: Optional[float] = Field(
        None,
        description="Confidence score (0-1) from OCR engine"
    )
    heading_level: Optional[int] = Field(
        None,
        description="Heading level (1-6 for H1-H6) if this is a heading"
    )
    is_bold: bool = Field(default=False, description="Whether text is bold")
    is_italic: bool = Field(default=False, description="Whether text is italic")
    bounding_box: Optional[dict[str, float]] = Field(
        None,
        description="Bounding box coordinates {top, left, width, height} normalized to page"
    )


class DocumentElement(BaseModel):
    """Base model for document elements (text blocks, tables, forms)."""
    element_id: str = Field(..., description="Unique element identifier within document")
    type: BlockType = Field(..., description="Type of element")
    page_number: int = Field(..., description="Page number (1-based)")
    content: Optional[str] = Field(None, description="Text content for text elements")
    table: Optional[Table] = Field(None, description="Table data if element is a table")
    form: Optional[Form] = Field(None, description="Form data if element is a form")
    confidence: Optional[float] = Field(None, description="Confidence score for extraction")


# ── Page Models ────────────────────────────────────────────────────────────────

class Page(BaseModel):
    """Extracted content from a single page."""
    page_number: int = Field(..., description="Page number (1-based)")
    text: str = Field(..., description="Full page text (concatenated)")
    element_count: int = Field(..., description="Number of elements extracted from page")
    tables: list[Table] = Field(default_factory=list, description="Tables on this page")
    forms: list[Form] = Field(default_factory=list, description="Forms on this page")
    elements: list[DocumentElement] = Field(
        default_factory=list,
        description="All document elements on this page"
    )


# ── Document Models ────────────────────────────────────────────────────────────

class ParsedDocument(BaseModel):
    """Complete parsed document with all extracted content."""
    document_id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    document_type: DocumentType = Field(..., description="Type of document")
    parsing_backend: ParsingBackend = Field(..., description="Backend used for parsing")
    
    # Content
    full_text: str = Field(..., description="Complete concatenated text from all pages")
    pages: list[Page] = Field(..., description="Content organized by page")
    
    # Metadata
    total_pages: int = Field(..., description="Total number of pages in document")
    total_tables: int = Field(..., description="Total number of tables extracted")
    total_forms: int = Field(..., description="Total number of forms extracted")
    
    # Quality metrics
    average_confidence: Optional[float] = Field(
        None,
        description="Average confidence score across all OCR/extraction operations"
    )
    extraction_errors: int = Field(
        default=0,
        description="Number of errors encountered during extraction"
    )
    
    # Processing metadata
    encoding: str = Field(default="utf-8", description="Text encoding used")
    processing_time_seconds: Optional[float] = Field(
        None,
        description="Time taken to parse document"
    )
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom key-value metadata"
    )


# ── Parsing Request/Response ──────────────────────────────────────────────────

class ParsedDocumentResponse(BaseModel):
    """Response from document parsing operation."""
    success: bool = Field(..., description="Whether parsing succeeded")
    document: Optional[ParsedDocument] = Field(None, description="Parsed document")
    error: Optional[str] = Field(None, description="Error message if parsing failed")
    error_details: Optional[dict[str, Any]] = Field(
        None,
        description="Detailed error information for debugging"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings during parsing"
    )
