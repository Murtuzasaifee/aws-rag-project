# Modular Document Parsing Service - Architecture & Implementation Guide

## Overview

A production-ready document parsing service with AWS Textract as the primary OCR engine and pluggable fallback parsers for multiple document formats. Designed for the AWS RAG (Retrieval-Augmented Generation) application.

## Supported Formats

| Format | Parser | Features | Fallback |
|--------|--------|----------|----------|
| **PDF** | AWS Textract | OCR, Tables, Forms, Layout | ❌ None |
| **DOCX** | AWS Textract | Full text, Tables, Metadata | ✅ python-docx |
| **TXT** | Plain Text | Encoding detection, UTF-8 normalization | ❌ Built-in |
| **HTML** | BeautifulSoup4 | Tag stripping, Structure extraction | ✅ Regex fallback |
| **Markdown** | Custom | Heading/list/code preservation | ❌ Built-in |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Document Parsing Service                         │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
         ┌──────────▼──────────────┐  ┌──────▼─────────────────────┐
         │  parse_document()       │  │  parse_document_safe()     │
         │  (main entry point)     │  │  (exception-safe wrapper)  │
         └──────────┬──────────────┘  └──────────┬──────────────────┘
                    │                            │
                    └────────────┬────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │ DocumentParserService    │
                    │ - Auto-detect type       │
                    │ - Select parser          │
                    │ - Manage fallback chain  │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  DefaultParserFactory    │
                    │  - Manage parsers        │
                    │  - Register backends     │
                    │  - Get parser chain      │
                    └────────────┬─────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
    ┌────▼────────────┐  ┌──────▼──────────┐  ┌─────────▼─────────┐
    │ AWS Textract    │  │ Fallback        │  │ Utility Functions │
    │ - OCR engine    │  │ Parsers         │  │ - Type detection  │
    │ - Tables/Forms  │  │ - TXT           │  │ - Encoding detect │
    │ - Multi-page    │  │ - Markdown      │  │ - Validation      │
    │ - Confidence    │  │ - HTML          │  │ - Normalization   │
    │                 │  │ - DOCX simple   │  │                   │
    └────┬────────────┘  └────┬────────────┘  └─────┬─────────────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  ParsedDocument    │
                    │  (output model)    │
                    │  - Pages[]         │
                    │  - Elements[]      │
                    │  - Tables[]        │
                    │  - Forms[]         │
                    │  - Metadata        │
                    └────────────────────┘
```

## Parser Priority Chain

### For PDF Files
1. **AWS Textract** (primary) - Full OCR + tables + forms + layout
2. ❌ No fallback - Textract required

### For DOCX Files
1. **AWS Textract** (primary) - Full Textract capabilities
2. **SimpleDOCXParser** (fallback) - Basic text via python-docx
3. ❌ No further fallback

### For TXT Files
1. **PlainTextParser** (only) - Encoding detection + UTF-8 normalization

### For HTML Files
1. **HTMLParser** (primary) - BeautifulSoup4 parsing
2. **HTMLParser** (fallback) - Regex-based tag stripping
3. ❌ No further fallback

### For Markdown Files
1. **MarkdownParser** (only) - Structure-aware parsing

## Data Flow

```
Input File
    │
    ├─→ [File Type Detection]
    │   - Extension check
    │   - Magic byte check
    │
    ├─→ [File Validation]
    │   - Exists?
    │   - Readable?
    │   - Under size limit?
    │
    ├─→ [Parser Selection]
    │   - Get parser chain
    │   - Select primary parser
    │
    ├─→ [Document Parsing]
    │   - Parse content
    │   - Extract structure
    │   - Detect encoding (if text-based)
    │   - Normalize to UTF-8
    │   - Maintain page numbers
    │
    ├─→ [Structure Extraction]
    │   - Heading detection
    │   - Table extraction
    │   - Form field extraction
    │   - List detection
    │   - Code block detection
    │
    ├─→ [Error Handling]
    │   - Catch exceptions
    │   - Try fallback parsers
    │   - Return error response
    │
    └─→ ParsedDocument
        ├─ File metadata
        ├─ Pages with content
        ├─ Confidence scores
        ├─ Custom metadata
        └─ Processing metrics
```

## Key Classes & Interfaces

### Abstract Base Classes

```python
class BaseDocumentParser:
    """Interface for all parsers"""
    - parse(file_path, document_type, metadata) → ParsedDocument
    - supports_document_type(doc_type) → bool
    - validate_file(file_path, max_size) → (bool, Optional[str])
    - get_parser_name() → str
    - get_supported_types() → List[DocumentType]

class OCRParser(BaseDocumentParser):
    """Extended interface for OCR engines"""
    - extract_tables(file_path) → List[Dict]
    - extract_forms(file_path) → List[Dict]
    - supports_ocr() → bool

class SimpleParser(BaseDocumentParser):
    """Extended interface for text-based parsers"""
    - detect_encoding(file_path) → str
    - normalize_encoding(content, target) → str

class ParserFactory:
    """Factory interface for parser management"""
    - get_parser(document_type) → BaseDocumentParser
    - get_available_parsers() → Dict[str, BaseDocumentParser]
    - register_parser(parser, document_types) → None
    - supports_document_type(doc_type) → bool
```

### Concrete Implementations

```python
class AWSTextractParser(OCRParser):
    """AWS Textract-based parser for OCR"""
    - Supports: PDF, DOCX
    - Features: OCR, tables, forms, multi-page
    - Confidence scores available

class PlainTextParser(SimpleParser):
    """Plain text file parser"""
    - Supports: TXT
    - Features: Encoding detection, UTF-8 normalization

class MarkdownParser(SimpleParser):
    """Markdown file parser"""
    - Supports: MARKDOWN
    - Features: Heading/list/code structure preservation

class HTMLParser(SimpleParser):
    """HTML file parser"""
    - Supports: HTML
    - Features: Tag stripping, paragraph extraction

class SimpleDOCXParser(SimpleParser):
    """Simple DOCX file parser"""
    - Supports: DOCX
    - Features: Basic text extraction via python-docx

class DefaultParserFactory(ParserFactory):
    """Built-in parser factory"""
    - Manages all default parsers
    - Handles parser registration
    - Manages fallback chain

class DocumentParserService:
    """High-level parsing orchestration"""
    - parse(file_path, metadata, document_type)
    - Handles auto-detection
    - Manages parser selection
    - Orchestrates fallback logic
```

### Data Models

```python
@dataclass
class ParsedDocument:
    document_id: str
    file_name: str
    document_type: DocumentType  # PDF, DOCX, TXT, HTML, MARKDOWN
    parsing_backend: ParsingBackend  # Which parser used
    
    full_text: str
    pages: List[Page]
    
    total_pages: int
    total_tables: int
    total_forms: int
    
    average_confidence: Optional[float]  # OCR confidence
    extraction_errors: int
    
    encoding: str
    processing_time_seconds: Optional[float]
    custom_metadata: Dict[str, Any]

@dataclass
class Page:
    page_number: int
    text: str
    element_count: int
    tables: List[Table]
    forms: List[Form]
    elements: List[DocumentElement]

@dataclass
class DocumentElement:
    element_id: str
    type: BlockType  # TEXT, TABLE, FORM, HEADING, LIST, CODE, etc.
    page_number: int
    content: Optional[str]
    table: Optional[Table]
    form: Optional[Form]
    confidence: Optional[float]

@dataclass
class Table:
    rows: List[TableRow]
    title: Optional[str]
    confidence: Optional[float]
    page_number: Optional[int]

@dataclass
class Form:
    fields: List[FormField]
    form_type: Optional[str]
    confidence: Optional[float]
    page_number: Optional[int]
```

## Exception Hierarchy

```
ParsingException (base)
├── UnsupportedDocumentTypeError
│   └── info: document_type, supported_types
├── CorruptedDocumentError
│   └── info: file_name, reason
├── EncodingError
│   └── info: file_name, detected_encoding
├── FileSizeExceededError
│   └── info: file_name, file_size_mb, max_size_mb
├── FileNotFoundError
│   └── info: file_path
├── ParserInitializationError
│   └── info: parser_name, reason
├── TextractServiceError
│   └── info: error_code, message, request_id
├── ExtractionQualityWarning
│   └── info: confidence_score
└── ParsingTimeoutError
    └── info: file_name, timeout_seconds
```

## Configuration Parameters

```python
# Document Processing
max_file_size_mb: int = 50
allowed_extensions: List[str] = [".pdf", ".txt", ".docx", ".html", ".md"]

# AWS Textract
aws_region: str = "us-east-1"
textract_feature_types: List[str] = ["TABLES", "FORMS"]
textract_timeout_seconds: int = 300

# Quality Control
parsing_confidence_threshold: float = 0.7
enable_ocr: bool = True
enable_fallback_parsers: bool = True
```

## Usage Examples

### Basic Usage

```python
from ragapp.services.parsing import parse_document

# Auto-detect type and parse
document = await parse_document("report.pdf")

# Access results
for page in document.pages:
    print(f"Page {page.page_number}:")
    for element in page.elements:
        print(f"  - {element.type.value}: {element.content[:50]}")
```

### Safe API Usage

```python
from ragapp.services.parsing import parse_document_safe

response = await parse_document_safe("document.docx")

if response.success:
    print(f"✓ Parsed {response.document.total_pages} pages")
else:
    print(f"✗ Error: {response.error}")
    print(f"  Details: {response.error_details}")
```

### With Metadata

```python
document = await parse_document(
    "invoice.pdf",
    metadata={
        "document_type": "financial",
        "fiscal_year": 2024,
        "source": "accounting_dept"
    }
)

print(f"Metadata: {document.custom_metadata}")
```

### Advanced Features

```python
# Extract tables from DOCX
document = await parse_document("data.docx")
for page in document.pages:
    for table in page.tables:
        for row in table.rows:
            print([cell.content for cell in row.cells])

# Extract forms from PDF
document = await parse_document("form.pdf")
for page in document.pages:
    for form in page.forms:
        for field in form.fields:
            print(f"{field.key}: {field.value} ({field.confidence:.0%})")

# Check document structure
from ragapp.schemas.parsing import BlockType
headings = [e for e in document.pages[0].elements 
            if e.type == BlockType.HEADING]
lists = [e for e in document.pages[0].elements 
         if e.type == BlockType.LIST]
```

## File Organization

```
src/ragapp/services/parsers/
├── __init__.py              # Package exports
├── base.py                  # Abstract base classes (400 lines)
├── utils.py                 # File detection, encoding (500 lines)
├── textract_parser.py       # AWS Textract implementation (600 lines)
├── fallback_parsers.py      # TXT, MD, HTML, DOCX (700 lines)
├── factory.py               # Factory & service (400 lines)
├── README.md                # Complete guide
└── EXAMPLES.md              # Practical examples

src/ragapp/schemas/
├── parsing.py               # Data models (400 lines)

src/ragapp/exception/
├── parsing_exception.py     # Exception types (300 lines)

src/ragapp/services/
├── parsing.py               # Main module (200 lines)

tests/unit/
├── test_parsing.py          # 45+ unit tests

tests/integration/
├── test_parsing_integration.py  # 20+ integration tests
```

## Dependencies Added

```
chardet                 # Encoding detection
beautifulsoup4          # HTML parsing
python-docx             # DOCX parsing
pypdf                   # PDF utilities
html5lib                # HTML5 parsing
structlog               # Already in project
```

## Integration Points

### With Ingest Service
```python
from ragapp.services.parsing import parse_document
from ragapp.services.ingest import IngestService

# In IngestService
document = await parse_document(local_file_path)
# Then chunk and embed the content
```

### With API Endpoints
```python
@app.post("/parse")
async def parse_endpoint(file: UploadFile):
    response = await parse_document_safe(temp_path)
    return response.model_dump()
```

### With Chunking Service
```python
# After parsing
document = await parse_document(file_path)

# Pass to chunking service
chunks = await chunking_service.chunk_document(
    document.full_text,
    metadata={
        "source": document.file_name,
        "pages": document.total_pages,
        "document_id": document.document_id,
    }
)
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Type detection | <10ms | Extension + magic bytes |
| Encoding detection | 10-50ms | Reads first 10KB |
| TXT parsing (10KB) | 50-100ms | Encoding normalization |
| MD parsing (10KB) | 100-200ms | Structure extraction |
| HTML parsing (10KB) | 200-500ms | BeautifulSoup parsing |
| DOCX parsing (100KB) | 500-1000ms | python-docx extraction |
| PDF/Textract (1 page) | 2-5s | AWS Textract overhead |
| PDF/Textract (10 pages) | 20-40s | Linear scaling |

## Testing Coverage

- Unit tests: 45+ test cases
- Integration tests: 20+ test cases
- Coverage areas:
  - Type detection (6 tests)
  - Encoding detection (3 tests)
  - All 5 parsers (35+ tests)
  - Factory logic (5 tests)
  - Error handling (8 tests)
  - Integration scenarios (20 tests)

## Future Enhancements

1. **Async Textract API** - For files > 10MB
2. **Caching layer** - Cache parsed documents
3. **Incremental parsing** - Resume from page N
4. **Parallel processing** - Multi-document batch
5. **Custom OCR** - TensorFlow/alternative engines
6. **Language detection** - Multi-language support
7. **Table semantics** - Smart table understanding
8. **Incremental updates** - Update vs. full re-parse

---

**Last Updated**: April 2026
**Status**: Production Ready
**Maintainer**: AWS RAG Team
