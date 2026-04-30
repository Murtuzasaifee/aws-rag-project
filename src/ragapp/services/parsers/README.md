"""
src/ragapp/services/parsers/README.md

Document Parsing Service Documentation
"""

# Document Parsing Service

A highly modular, plug-and-play document parsing service that extracts clean text from multiple document formats with AWS Textract integration as the primary OCR engine.

## Features

### Supported Document Formats

- **PDF** - Via AWS Textract (OCR support) or PyPDF fallback
- **DOCX** - Via AWS Textract (with table support) or python-docx fallback  
- **TXT** - Plain text with automatic encoding detection and UTF-8 normalization
- **HTML** - Via BeautifulSoup4 or regex fallback
- **Markdown** - With structure preservation (headings, lists, code blocks)

### Core Capabilities

✅ **Multi-page document support** - Extracts and organizes content by page  
✅ **Structured extraction** - Preserves headings, sections, tables, and forms  
✅ **Encoding validation** - Automatic detection and UTF-8 normalization  
✅ **File type detection** - Extension and magic byte-based detection  
✅ **Confidence scores** - OCR confidence metrics from Textract  
✅ **Modular architecture** - Easily pluggable backends for different parsing engines  
✅ **Comprehensive error handling** - Structured error reporting with actionable messages  
✅ **Fallback parsing** - Automatic fallback to simpler parsers on failure  

## Architecture

### Component Overview

```
DocumentParserService
    └── DefaultParserFactory
            ├── AWSTextractParser (OCR-based)
            ├── SimpleDOCXParser (python-docx)
            ├── PlainTextParser (encoding-aware)
            ├── MarkdownParser (structure-preserving)
            └── HTMLParser (tag-stripping)
```

### Parser Types

#### OCRParser (Abstract)
Primary OCR-based parsing with advanced capabilities:
- Confidence scores for character/word recognition
- Table and form extraction
- Layout preservation
- Implemented by: `AWSTextractParser`

#### SimpleParser (Abstract)
Text-based parsing without OCR:
- Encoding detection and normalization
- Basic structural extraction
- Implemented by: `PlainTextParser`, `MarkdownParser`, `HTMLParser`, `SimpleDOCXParser`

## Usage

### Basic Parsing

```python
from ragapp.services.parsing import parse_document

# Auto-detect document type and parse
document = await parse_document("report.pdf")

print(f"Extracted {document.total_pages} pages")
print(f"Total tables: {document.total_tables}")

# Access parsed content
for page in document.pages:
    print(f"Page {page.page_number}:")
    print(f"  - Elements: {page.element_count}")
    print(f"  - Tables: {len(page.tables)}")
```

### Safe Parsing (API Endpoint)

```python
from ragapp.services.parsing import parse_document_safe

# Returns response object, never raises exception
response = await parse_document_safe("document.docx")

if response.success:
    document = response.document
    print(f"Parsed {document.total_pages} pages")
else:
    print(f"Error: {response.error}")
    print(f"Details: {response.error_details}")
```

### Custom Metadata

```python
document = await parse_document(
    "invoice.pdf",
    metadata={
        "category": "financial",
        "fiscal_year": 2024,
        "source": "accounting_dept"
    }
)

print(f"Custom metadata: {document.custom_metadata}")
```

### Check Supported Types

```python
from ragapp.services.parsing import get_supported_document_types

supported = get_supported_document_types()
print(f"Supported formats: {supported}")
# Output: ['pdf', 'docx', 'txt', 'html', 'markdown']
```

## Data Models

### ParsedDocument

Complete parsed document with all extracted content:

```python
@dataclass
class ParsedDocument:
    document_id: str              # Unique identifier
    file_name: str                # Original filename
    document_type: DocumentType   # PDF, DOCX, TXT, HTML, MARKDOWN
    parsing_backend: ParsingBackend  # Which parser was used
    
    full_text: str                # Complete concatenated text
    pages: list[Page]             # Content organized by page
    
    total_pages: int              # Number of pages
    total_tables: int             # Tables extracted
    total_forms: int              # Forms extracted
    
    average_confidence: float     # OCR confidence score
    extraction_errors: int        # Errors encountered
    
    encoding: str                 # Text encoding
    processing_time_seconds: float  # Parse duration
    custom_metadata: dict         # User metadata
```

### Page

Single page from a parsed document:

```python
@dataclass
class Page:
    page_number: int              # 1-based page number
    text: str                     # Full page text
    element_count: int            # Number of elements
    tables: list[Table]           # Tables on this page
    forms: list[Form]             # Forms on this page
    elements: list[DocumentElement]  # All structured elements
```

### DocumentElement

Individual content element (text, table, form, etc.):

```python
@dataclass
class DocumentElement:
    element_id: str               # Unique ID within document
    type: BlockType               # TEXT, TABLE, FORM, HEADING, LIST, CODE
    page_number: int              # Page location
    content: str                  # Text content
    table: Table                  # Table data (if type=TABLE)
    form: Form                    # Form data (if type=FORM)
    confidence: float             # Extraction confidence
```

### Table and Form Models

```python
@dataclass
class Table:
    rows: list[TableRow]
    title: str
    confidence: float
    page_number: int

@dataclass
class Form:
    fields: list[FormField]
    form_type: str
    confidence: float
    page_number: int
```

## Configuration

Set in `.env` or as environment variables:

```env
# AWS Region
AWS_REGION=us-east-1

# Textract features to extract
TEXTRACT_FEATURE_TYPES=TABLES,FORMS

# Textract operation timeout (seconds)
TEXTRACT_TIMEOUT_SECONDS=300

# Minimum confidence for extracted data
PARSING_CONFIDENCE_THRESHOLD=0.7

# Enable/disable OCR
ENABLE_OCR=true

# Allow fallback to simpler parsers
ENABLE_FALLBACK_PARSERS=true

# Maximum file size (MB)
MAX_FILE_SIZE_MB=50
```

## Parser Priority/Fallback Chain

The factory uses a priority-based approach:

1. **PDF Files**
   - Primary: `AWSTextractParser` (OCR with tables/forms)
   - Fallback: None (Textract required for PDF)

2. **DOCX Files**
   - Primary: `AWSTextractParser` (full Textract capabilities)
   - Fallback: `SimpleDOCXParser` (python-docx, text only)

3. **TXT Files**
   - Primary: `PlainTextParser` (encoding detection)

4. **HTML Files**
   - Primary: `HTMLParser` (BeautifulSoup)

5. **Markdown Files**
   - Primary: `MarkdownParser` (structure preservation)

## Error Handling

### Exception Hierarchy

```
ParsingException (base)
  ├── UnsupportedDocumentTypeError
  ├── CorruptedDocumentError
  ├── EncodingError
  ├── FileSizeExceededError
  ├── FileNotFoundError
  ├── ParserInitializationError
  ├── TextractServiceError
  ├── ExtractionQualityWarning
  └── ParsingTimeoutError
```

### Example Error Handling

```python
from ragapp.exception.parsing_exception import (
    UnsupportedDocumentTypeError,
    CorruptedDocumentError,
    EncodingError,
)

try:
    document = await parse_document("file.xyz")
except UnsupportedDocumentTypeError as e:
    print(f"Format not supported: {e.document_type}")
    print(f"Supported: {e.supported_types}")
except CorruptedDocumentError as e:
    print(f"File corrupted: {e.reason}")
except EncodingError as e:
    print(f"Encoding issue: {e.detected_encoding}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Extending with Custom Parsers

### Create a Custom Parser

```python
from ragapp.services.parsers.base import BaseDocumentParser
from ragapp.schemas.parsing import DocumentType, ParsedDocument

class CustomParser(BaseDocumentParser):
    def __init__(self):
        super().__init__("My Custom Parser")
    
    async def parse(self, file_path, document_type, metadata=None):
        # Implement parsing logic
        document = ParsedDocument(
            document_id="custom-doc-1",
            file_name=Path(file_path).name,
            document_type=document_type,
            parsing_backend=ParsingBackend.CUSTOM,
            full_text="...",
            pages=[...],
            total_pages=1,
        )
        return document
    
    def supports_document_type(self, document_type):
        return document_type == DocumentType.PDF  # or custom type
    
    async def validate_file(self, file_path, max_size_mb=50):
        # Implement validation logic
        return (True, None)  # (is_valid, error_message)
```

### Register Custom Parser

```python
from ragapp.services.parsers.factory import DefaultParserFactory

factory = DefaultParserFactory()
custom_parser = CustomParser()

factory.register_parser(
    custom_parser,
    document_types=[DocumentType.PDF]  # Or your custom types
)
```

## Testing

### Unit Tests

```bash
pytest tests/unit/test_parsing.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_parsing_integration.py -v
```

### Test with Real Files

```python
import asyncio
from ragapp.services.parsing import parse_document

async def test():
    doc = await parse_document("path/to/your/document.pdf")
    print(f"✓ Successfully parsed {doc.total_pages} pages")

asyncio.run(test())
```

## Performance Considerations

### AWS Textract Limits

- Maximum file size: 10 MB (synchronous API)
- Larger files require async job-based API with S3
- Typical latency: 2-10 seconds per page

### Optimization Tips

1. **Use fallback parsers for non-PDF/DOCX** - Faster than Textract
2. **Enable confidence threshold** - Filter low-confidence extractions
3. **Process large files asynchronously** - Don't block web server
4. **Cache parsed documents** - Avoid re-parsing same files
5. **Use file type detection** - Route to optimal parser quickly

## Troubleshooting

### "Unsupported document type" Error

**Cause**: File format not in supported list  
**Solution**: Check `get_supported_document_types()` or use `parse_document_safe()` to get specific error

### "Encoding error" for TXT Files

**Cause**: File uses non-UTF-8 encoding  
**Solution**: Parser automatically detects encoding, but can also specify:

```python
from ragapp.services.parsers.utils import normalize_to_utf8
normalized = normalize_to_utf8(content, source_encoding="iso-8859-1")
```

### AWS Textract Failing

**Cause**: Missing AWS credentials or insufficient permissions  
**Solution**: Configure AWS credentials:

```bash
aws configure
# Or set environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### "File size exceeded" Error

**Cause**: File larger than `MAX_FILE_SIZE_MB` setting  
**Solution**: Increase in config or split large files

## Future Enhancements

- [ ] Async job API for Textract (files > 10MB)
- [ ] Multi-language OCR support
- [ ] Custom OCR engine integration (TensorFlow, etc.)
- [ ] PDF form field extraction
- [ ] Handwriting recognition
- [ ] Table extraction with semantic understanding
- [ ] Caching layer for parsed documents
- [ ] Incremental parsing (resume from page N)
- [ ] Parallel multi-document processing
