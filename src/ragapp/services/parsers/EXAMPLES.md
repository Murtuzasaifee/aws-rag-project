"""
src/ragapp/services/parsers/EXAMPLES.md

# Document Parsing Examples

Practical examples for using the document parsing service.

## Quick Start

### Parse a Document (Auto-detect Type)

```python
import asyncio
from ragapp.services.parsing import parse_document

async def main():
    # Auto-detects PDF and uses AWS Textract
    document = await parse_document("report.pdf")
    
    print(f"File: {document.file_name}")
    print(f"Pages: {document.total_pages}")
    print(f"Tables: {document.total_tables}")
    print(f"Text length: {len(document.full_text)} characters")

asyncio.run(main())
```

### Parse Multiple Documents

```python
import asyncio
from pathlib import Path
from ragapp.services.parsing import parse_document

async def process_directory(directory):
    docs = []
    for file_path in Path(directory).glob("*.pdf"):
        doc = await parse_document(file_path)
        docs.append(doc)
        print(f"✓ Parsed {file_path.name} - {doc.total_pages} pages")
    
    return docs

# Usage
documents = asyncio.run(process_directory("./documents"))
```

### Handle Parsing Errors Gracefully

```python
from ragapp.services.parsing import parse_document_safe

async def safe_parse():
    response = await parse_document_safe("document.pdf")
    
    if response.success:
        print(f"✓ Successfully parsed: {response.document.total_pages} pages")
    else:
        print(f"✗ Parsing failed: {response.error}")
        if response.error_details:
            print(f"  Details: {response.error_details}")

asyncio.run(safe_parse())
```

## Document Type Examples

### Plain Text Files

```python
async def parse_text_report():
    document = await parse_document("annual_report.txt")
    
    # Access parsed structure
    for page in document.pages:
        print(f"Page {page.page_number}:")
        for element in page.elements:
            print(f"  {element.type.value}: {element.content[:50]}...")
    
    return document

asyncio.run(parse_text_report())
```

### Markdown Files (with Structure)

```python
from ragapp.schemas.parsing import BlockType

async def parse_readme():
    document = await parse_document("README.md")
    
    # Extract headings
    headings = []
    for page in document.pages:
        for element in page.elements:
            if element.type == BlockType.HEADING:
                headings.append(element.content)
    
    print("Document Structure:")
    for heading in headings:
        print(f"  - {heading}")
    
    return headings

asyncio.run(parse_readme())
```

### HTML Files

```python
async def parse_webpage():
    document = await parse_document("webpage.html")
    
    # HTML tags are automatically stripped
    print(f"Extracted text:")
    print(document.full_text[:500])  # First 500 chars
    
    # Count paragraphs
    text_elements = [e for e in document.pages[0].elements 
                     if e.type.value == "text"]
    print(f"Paragraphs: {len(text_elements)}")

asyncio.run(parse_webpage())
```

### DOCX Files (with Tables)

```python
from ragapp.schemas.parsing import BlockType

async def parse_docx_table():
    document = await parse_document("data.docx")
    
    # Find and process tables
    for page in document.pages:
        if page.tables:
            print(f"Found {len(page.tables)} tables on page {page.page_number}")
            
            for table in page.tables:
                print(f"\nTable with {len(table.rows)} rows:")
                for row in table.rows:
                    row_data = [cell.content for cell in row.cells]
                    print(f"  {row_data}")

asyncio.run(parse_docx_table())
```

### PDF with Advanced Features

```python
async def parse_pdf_advanced():
    document = await parse_document("form.pdf", metadata={
        "document_type": "financial_form",
        "fiscal_year": 2024
    })
    
    print(f"File: {document.file_name}")
    print(f"Parser: {document.parsing_backend.value}")
    print(f"Confidence: {document.average_confidence:.1%}")
    
    # Extract forms if present
    for page in document.pages:
        if page.forms:
            for form in page.forms:
                print(f"\nForm on page {page.page_number}:")
                for field in form.fields:
                    print(f"  {field.key}: {field.value}")
                    if field.confidence:
                        print(f"    Confidence: {field.confidence:.1%}")

asyncio.run(parse_pdf_advanced())
```

## API Integration Example

### FastAPI Endpoint

```python
from fastapi import FastAPI, File, UploadFile
from ragapp.services.parsing import parse_document_safe
import tempfile
from pathlib import Path

app = FastAPI()

@app.post("/parse")
async def parse_file(file: UploadFile):
    """Parse uploaded document"""
    
    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse document
        response = await parse_document_safe(tmp_path)
        
        if response.success:
            return {
                "success": True,
                "document": response.document.model_dump()
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "details": response.error_details
            }
    finally:
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)
```

## Batch Processing Example

```python
import asyncio
from pathlib import Path
from typing import List
from ragapp.schemas.parsing import ParsedDocument
from ragapp.services.parsing import parse_document_safe

async def batch_parse(directory: str, max_concurrent: int = 3) -> List[ParsedDocument]:
    """Parse all documents in directory with concurrency limit"""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def parse_with_limit(path):
        async with semaphore:
            response = await parse_document_safe(path)
            if response.success:
                return response.document
            else:
                print(f"✗ Failed to parse {path}: {response.error}")
                return None
    
    # Find all supported documents
    files = list(Path(directory).glob("*.pdf"))
    files.extend(Path(directory).glob("*.txt"))
    files.extend(Path(directory).glob("*.docx"))
    files.extend(Path(directory).glob("*.md"))
    files.extend(Path(directory).glob("*.html"))
    
    # Parse concurrently
    results = await asyncio.gather(*[
        parse_with_limit(f) for f in files
    ])
    
    # Filter successful parses
    documents = [d for d in results if d is not None]
    
    print(f"✓ Successfully parsed {len(documents)}/{len(files)} documents")
    return documents

# Usage
docs = asyncio.run(batch_parse("./documents"))
```

## Content Analysis Examples

### Extract Key Information

```python
from ragapp.schemas.parsing import BlockType

async def extract_structure(file_path: str):
    """Extract document structure"""
    document = await parse_document(file_path)
    
    structure = {
        "headings": [],
        "sections": [],
        "code_blocks": [],
        "lists": [],
        "tables_count": 0,
    }
    
    for page in document.pages:
        for element in page.elements:
            if element.type == BlockType.HEADING:
                structure["headings"].append(element.content)
            elif element.type == BlockType.SECTION:
                structure["sections"].append(element.content[:100])
            elif element.type == BlockType.CODE:
                structure["code_blocks"].append(element.content[:50])
            elif element.type == BlockType.LIST:
                structure["lists"].append(element.content)
        
        structure["tables_count"] += len(page.tables)
    
    return structure

structure = asyncio.run(extract_structure("document.pdf"))
print(structure)
```

### Create Summary Statistics

```python
async def document_statistics(file_path: str):
    """Generate document statistics"""
    document = await parse_document(file_path)
    
    stats = {
        "file": document.file_name,
        "type": document.document_type.value,
        "pages": document.total_pages,
        "total_text_length": len(document.full_text),
        "average_page_length": len(document.full_text) / document.total_pages,
        "tables": document.total_tables,
        "forms": document.total_forms,
        "ocr_confidence": document.average_confidence,
        "processing_time": document.processing_time_seconds,
    }
    
    # Count element types
    from ragapp.schemas.parsing import BlockType
    element_counts = {}
    for page in document.pages:
        for element in page.elements:
            elem_type = element.type.value
            element_counts[elem_type] = element_counts.get(elem_type, 0) + 1
    
    stats["elements_by_type"] = element_counts
    
    return stats

stats = asyncio.run(document_statistics("report.pdf"))
for key, value in stats.items():
    print(f"{key}: {value}")
```

## Error Recovery Examples

### Retry with Fallback

```python
from ragapp.services.parsing import parse_document
from ragapp.exception.parsing_exception import TextractServiceError

async def parse_with_retry(file_path: str, max_retries: int = 3):
    """Parse document with retry logic"""
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}...")
            document = await parse_document(file_path)
            print(f"✓ Success!")
            return document
        except TextractServiceError as e:
            print(f"  ✗ Textract error: {e.error_message}")
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"  ✗ Error: {e}")
            raise
    
    raise Exception(f"Failed to parse after {max_retries} attempts")

# Usage
document = asyncio.run(parse_with_retry("document.pdf"))
```

### Type-Safe Parsing

```python
from ragapp.schemas.parsing import DocumentType

async def parse_specific_type(file_path: str, expected_type: DocumentType):
    """Parse and validate document type"""
    document = await parse_document(file_path)
    
    if document.document_type != expected_type:
        raise ValueError(
            f"Expected {expected_type.value}, "
            f"got {document.document_type.value}"
        )
    
    return document

# Usage
pdf_doc = asyncio.run(
    parse_specific_type("report.pdf", DocumentType.PDF)
)
```

## Performance Examples

### Measure Parsing Performance

```python
import asyncio
import time
from ragapp.services.parsing import parse_document

async def benchmark_parsing():
    """Benchmark parsing performance"""
    
    test_files = [
        "small.txt",
        "medium.pdf",
        "large.docx",
    ]
    
    for file_path in test_files:
        start = time.time()
        try:
            document = await parse_document(file_path)
            elapsed = time.time() - start
            
            throughput = len(document.full_text) / elapsed  # chars/sec
            
            print(f"{file_path}:")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Text: {len(document.full_text)} chars")
            print(f"  Throughput: {throughput:.0f} chars/sec")
            print(f"  Confidence: {document.average_confidence:.1%}")
        except Exception as e:
            print(f"✗ {file_path}: {e}")

asyncio.run(benchmark_parsing())
```

## Checking Supported Types

```python
from ragapp.services.parsing import (
    get_supported_document_types,
    is_document_type_supported
)

# List all supported types
supported_types = get_supported_document_types()
print(f"Supported: {', '.join(supported_types)}")

# Check specific file
is_supported = is_document_type_supported("document.pdf")
print(f"document.pdf supported: {is_supported}")
```
"""
