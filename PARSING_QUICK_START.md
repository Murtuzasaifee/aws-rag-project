# Document Parsing Service - Quick Reference

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

## Quick Start

### 1. Basic Parsing

```python
from ragapp.services.parsing import parse_document
import asyncio

async def main():
    doc = await parse_document("document.pdf")
    print(f"✓ Parsed {doc.total_pages} pages")

asyncio.run(main())
```

### 2. Safe Parsing (for APIs)

```python
from ragapp.services.parsing import parse_document_safe

response = await parse_document_safe("file.docx")
if response.success:
    print(document.total_pages)
else:
    print(f"Error: {response.error}")
```

### 3. With Metadata

```python
doc = await parse_document(
    "report.pdf",
    metadata={"category": "financial", "year": 2024}
)
```

## Supported Formats

| Format | Extension | Parser | Features |
|--------|-----------|--------|----------|
| PDF | .pdf | AWS Textract | OCR, tables, forms |
| DOCX | .docx | AWS Textract | Text, tables, forms |
| Text | .txt | PlainText | Encoding detection |
| HTML | .html, .htm | BeautifulSoup | Tag stripping |
| Markdown | .md | Markdown | Structure preserved |

## Common Operations

### Extract Tables

```python
from ragapp.schemas.parsing import BlockType

doc = await parse_document("data.docx")
for page in doc.pages:
    for table in page.tables:
        for row in table.rows:
            print([cell.content for cell in row.cells])
```

### Extract Document Structure

```python
# Get headings
headings = [e for e in doc.pages[0].elements 
           if e.type == BlockType.HEADING]

# Get code blocks  
code_blocks = [e for e in doc.pages[0].elements 
              if e.type == BlockType.CODE]

# Get lists
lists = [e for e in doc.pages[0].elements 
        if e.type == BlockType.LIST]
```

### Access Page-by-Page Content

```python
for page in doc.pages:
    print(f"Page {page.page_number}:")
    print(f"  Text: {len(page.text)} chars")
    print(f"  Elements: {page.element_count}")
    print(f"  Tables: {len(page.tables)}")
```

### Check Supported Types

```python
from ragapp.services.parsing import get_supported_document_types

print(get_supported_document_types())
# ['pdf', 'docx', 'txt', 'html', 'markdown']
```

## Configuration

Set in `.env`:

```env
AWS_REGION=us-east-1
MAX_FILE_SIZE_MB=50
PARSING_CONFIDENCE_THRESHOLD=0.7
ENABLE_OCR=true
ENABLE_FALLBACK_PARSERS=true
```

## Error Handling

```python
from ragapp.exception.parsing_exception import (
    UnsupportedDocumentTypeError,
    CorruptedDocumentError,
    EncodingError,
)

try:
    doc = await parse_document("file.pdf")
except UnsupportedDocumentTypeError as e:
    print(f"Format not supported: {e.document_type}")
except CorruptedDocumentError as e:
    print(f"File corrupted: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/unit/test_parsing.py::TestPlainTextParser

# With coverage
pytest tests/ --cov=src/ragapp/services/parsers
```

## Data Model Quick Reference

```python
# Main output structure
ParsedDocument:
  - document_id: str
  - file_name: str
  - document_type: DocumentType
  - parsing_backend: ParsingBackend
  - full_text: str
  - pages: List[Page]
  - total_pages: int
  - total_tables: int
  - total_forms: int
  - average_confidence: Optional[float]
  - custom_metadata: dict

# Page structure
Page:
  - page_number: int
  - text: str
  - element_count: int
  - tables: List[Table]
  - forms: List[Form]
  - elements: List[DocumentElement]

# Element types
BlockType:
  - TEXT
  - TABLE
  - FORM
  - HEADING
  - LIST
  - CODE
  - IMAGE
  - SECTION

# Element structure
DocumentElement:
  - element_id: str
  - type: BlockType
  - page_number: int
  - content: str
  - confidence: Optional[float]
```

## Performance Tips

1. **Use fallback parsers** - TXT/MD/HTML faster than OCR
2. **Set confidence threshold** - Filter low-quality extractions
3. **Process async** - Don't block on parsing
4. **Cache results** - Avoid re-parsing same files
5. **Batch operations** - Use semaphore for concurrent parsing

```python
async def batch_parse(files, max_concurrent=3):
    sem = asyncio.Semaphore(max_concurrent)
    
    async def parse_with_limit(f):
        async with sem:
            return await parse_document(f)
    
    return await asyncio.gather(*[
        parse_with_limit(f) for f in files
    ])
```

## Module Structure

```
src/ragapp/services/parsers/
├── base.py              # Abstract interfaces
├── utils.py             # File detection, encoding
├── textract_parser.py   # AWS Textract backend
├── fallback_parsers.py  # TXT, MD, HTML, DOCX
├── factory.py           # Factory & orchestration
├── README.md            # Full documentation
└── EXAMPLES.md          # Detailed examples

src/ragapp/services/
└── parsing.py          # Main entry point

src/ragapp/exception/
└── parsing_exception.py # Exception types

src/ragapp/schemas/
└── parsing.py          # Data models
```

## Common Issues

### "AWS credentials not found"
```bash
aws configure
# Or set env vars:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### "Unsupported document type"
- Check file extension
- Verify file is not corrupted
- Use `parse_document_safe()` for error details

### "Encoding error"
- Parser auto-detects encoding
- Falls back to UTF-8
- Can manually normalize:
```python
from ragapp.services.parsers.utils import normalize_to_utf8
normalized = normalize_to_utf8(content)
```

### "File size exceeded"
- Increase `MAX_FILE_SIZE_MB` in config
- Or split large files
- Note: AWS Textract API limit is 10MB for sync

## API Integration Example

```python
from fastapi import FastAPI, File, UploadFile
from ragapp.services.parsing import parse_document_safe
import tempfile
from pathlib import Path

app = FastAPI()

@app.post("/parse")
async def parse_file(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    
    try:
        response = await parse_document_safe(tmp_path)
        return response.model_dump()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
```

## Next Steps

1. Read [README.md](src/ragapp/services/parsers/README.md) for complete guide
2. Check [EXAMPLES.md](src/ragapp/services/parsers/EXAMPLES.md) for code examples
3. Review [PARSING_SERVICE_ARCHITECTURE.md](PARSING_SERVICE_ARCHITECTURE.md)
4. Run tests: `pytest tests/`
5. Integrate into your workflow

## Support & Documentation

- **Architecture**: [PARSING_SERVICE_ARCHITECTURE.md](PARSING_SERVICE_ARCHITECTURE.md)
- **User Guide**: [src/ragapp/services/parsers/README.md](src/ragapp/services/parsers/README.md)
- **Examples**: [src/ragapp/services/parsers/EXAMPLES.md](src/ragapp/services/parsers/EXAMPLES.md)
- **Tests**: [tests/unit/test_parsing.py](tests/unit/test_parsing.py), [tests/integration/test_parsing_integration.py](tests/integration/test_parsing_integration.py)

---

For more information, see the full documentation in the parsers directory.
