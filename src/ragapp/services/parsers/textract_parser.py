"""
src/ragapp/services/parsers/textract_parser.py

AWS Textract-based document parser for extracting text, layout, tables, and forms.
This is the primary OCR/parsing engine with advanced capabilities.
"""

import time
import asyncio
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from ragapp.schemas.parsing import (
    ParsedDocument,
    DocumentType,
    ParsingBackend,
    Page,
    DocumentElement,
    BlockType,
    Table,
    TableRow,
    TableCell,
    Form,
    FormField,
    TextBlock,
)
from ragapp.services.parsers.base import OCRParser
from ragapp.services.parsers.utils import (
    validate_file,
    detect_document_type,
    normalize_to_utf8,
)
from ragapp.exception.parsing_exception import (
    TextractServiceError,
    CorruptedDocumentError,
    ExtractionQualityWarning,
    ParsingTimeoutError,
    UnsupportedDocumentTypeError,
)
from ragapp.logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)


class AWSTextractParser(OCRParser):
    """
    AWS Textract-based document parser.
    
    Supports PDF, PNG, JPEG, and DOCX files. Uses AWS Textract for OCR
    and structural analysis, extracting text, tables, forms, and layout information.
    """

    def __init__(
        self,
        aws_region: str = "us-east-1",
        client_config: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize AWS Textract parser.
        
        Args:
            aws_region: AWS region for Textract service
            client_config: Optional Textract client configuration
        """
        super().__init__("AWS Textract")
        self.aws_region = aws_region
        self.textract_client = boto3.client("textract", region_name=aws_region)
        self._supported_types = [
            DocumentType.PDF,
            DocumentType.DOCX,
        ]
        logger.info("Initialized AWS Textract parser", region=aws_region)

    def supports_document_type(self, document_type: DocumentType) -> bool:
        """Check if Textract supports this document type."""
        return document_type in self._supported_types

    async def validate_file(
        self,
        file_path: str | Path,
        max_size_mb: int = 50,
    ) -> tuple[bool, Optional[str]]:
        """Validate file for Textract processing."""
        is_valid, error = await validate_file(file_path, max_size_mb)
        
        if not is_valid:
            return False, error
        
        # Textract-specific: file must be PDF or DOCX
        try:
            doc_type = detect_document_type(file_path)
            if not self.supports_document_type(doc_type):
                return False, f"AWS Textract does not support {doc_type.value} files"
        except Exception as e:
            return False, f"Cannot determine file type: {str(e)}"
        
        return True, None

    async def parse(
        self,
        file_path: str | Path,
        document_type: DocumentType,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ParsedDocument:
        """
        Parse document using AWS Textract.
        
        Args:
            file_path: Path to the document
            document_type: Type of document
            metadata: Custom metadata
            
        Returns:
            ParsedDocument with extracted content
            
        Raises:
            UnsupportedDocumentTypeError: If document type not supported
            CorruptedDocumentError: If document is corrupted
            TextractServiceError: If Textract service fails
        """
        file_path = Path(file_path)
        start_time = time.time()
        
        logger.info("Starting Textract parsing",
                   file=str(file_path), type=document_type.value)
        
        # Validate file
        if not self.supports_document_type(document_type):
            raise UnsupportedDocumentTypeError(
                document_type.value,
                [dt.value for dt in self._supported_types],
            )
        
        is_valid, error = await self.validate_file(file_path)
        if not is_valid:
            raise CorruptedDocumentError(file_path.name, error or "Unknown validation error")
        
        try:
            # Upload file to S3 and start Textract analysis
            # For MVP, we'll use synchronous API for small files
            # In production, would use async job API with SNS notifications
            
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            logger.info("Starting Textract analysis",
                       file=str(file_path), size_bytes=len(file_bytes))
            
            # Call Textract (synchronous for files < 10MB)
            if len(file_bytes) < 10 * 1024 * 1024:
                response = self.textract_client.analyze_document(
                    Document={"Bytes": file_bytes},
                    FeatureTypes=["TABLES", "FORMS"],
                )
            else:
                # For larger files, would need job-based API
                raise TextractServiceError(
                    "INVALID_FILE_SIZE",
                    "File must be < 10MB for synchronous processing. "
                    "Use async job API for larger files.",
                )
            
            # Parse Textract response
            document = self._parse_textract_response(
                response,
                file_path,
                document_type,
                metadata,
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            document.processing_time_seconds = processing_time
            
            logger.info("Successfully parsed document with Textract",
                       file=str(file_path),
                       pages=document.total_pages,
                       tables=document.total_tables,
                       forms=document.total_forms,
                       time_seconds=processing_time)
            
            return document
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UNKNOWN")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            request_id = e.response.get("ResponseMetadata", {}).get("RequestId")
            
            logger.error("Textract service error",
                        file=str(file_path), error_code=error_code,
                        error_msg=error_msg, request_id=request_id)
            
            raise TextractServiceError(error_code, error_msg, request_id, e)
        
        except Exception as e:
            logger.error("Unexpected error during Textract parsing",
                        file=str(file_path), error=str(e), error_type=type(e).__name__)
            raise CorruptedDocumentError(file_path.name, str(e), e)

    def _parse_textract_response(
        self,
        response: dict[str, Any],
        file_path: Path,
        document_type: DocumentType,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ParsedDocument:
        """
        Parse Textract API response and build ParsedDocument.
        
        Args:
            response: Response from Textract analyze_document
            file_path: Original file path
            document_type: Document type
            metadata: Custom metadata
            
        Returns:
            ParsedDocument object
        """
        blocks = response.get("Blocks", [])
        
        # Build block index for easy lookup
        block_map = {block["Id"]: block for block in blocks}
        
        # Extract pages and content
        pages: list[Page] = []
        all_text = []
        all_tables: list[Table] = []
        all_forms: list[Form] = []
        total_elements = 0
        confidence_scores = []
        
        # Find all pages
        page_blocks = [b for b in blocks if b.get("BlockType") == "PAGE"]
        
        for page_num, page_block in enumerate(page_blocks, 1):
            page_id = page_block["Id"]
            page_text = []
            page_elements: list[DocumentElement] = []
            page_tables: list[Table] = []
            page_forms: list[Form] = []
            
            # Get relationships for this page
            relationships = page_block.get("Relationships", [])
            child_ids = []
            for rel in relationships:
                if rel["Type"] == "CHILD":
                    child_ids.extend(rel.get("Ids", []))
            
            # Process children
            element_counter = 0
            for child_id in child_ids:
                child_block = block_map.get(child_id)
                if not child_block:
                    continue
                
                block_type = child_block.get("BlockType")
                
                if block_type == "LINE":
                    # Extract text line
                    line_text = child_block.get("Text", "")
                    confidence = child_block.get("Confidence")
                    
                    if confidence:
                        confidence_scores.append(confidence / 100.0)
                    
                    page_text.append(line_text)
                    
                    text_element = DocumentElement(
                        element_id=f"page{page_num}_element{element_counter}",
                        type=BlockType.TEXT,
                        page_number=page_num,
                        content=line_text,
                        confidence=confidence,
                    )
                    page_elements.append(text_element)
                    element_counter += 1
                
                elif block_type == "TABLE":
                    # Extract table
                    table = self._extract_table(child_id, block_map, page_num)
                    page_tables.append(table)
                    all_tables.append(table)
                    
                    table_element = DocumentElement(
                        element_id=f"page{page_num}_table{len(page_tables)-1}",
                        type=BlockType.TABLE,
                        page_number=page_num,
                        table=table,
                    )
                    page_elements.append(table_element)
                    element_counter += 1
            
            all_text.extend(page_text)
            total_elements += len(page_elements)
            
            # Extract key-value pairs as forms
            if "KEY_VALUE_SET" in [b.get("BlockType") for b in child_ids]:
                form = self._extract_form(page_block, block_map, page_num)
                if form:
                    page_forms.append(form)
                    all_forms.append(form)
            
            # Create page object
            page = Page(
                page_number=page_num,
                text="\n".join(page_text),
                element_count=len(page_elements),
                tables=page_tables,
                forms=page_forms,
                elements=page_elements,
            )
            pages.append(page)
        
        # Calculate average confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else None
        )
        
        # Create ParsedDocument
        document = ParsedDocument(
            document_id=f"{file_path.stem}_{int(datetime.now().timestamp())}",
            file_name=file_path.name,
            document_type=document_type,
            parsing_backend=ParsingBackend.AWS_TEXTRACT,
            full_text="\n\n".join(all_text),
            pages=pages,
            total_pages=len(pages),
            total_tables=len(all_tables),
            total_forms=len(all_forms),
            average_confidence=avg_confidence,
            custom_metadata=metadata or {},
        )
        
        return document

    def _extract_table(
        self,
        table_id: str,
        block_map: dict[str, Any],
        page_number: int,
    ) -> Table:
        """Extract table structure from Textract blocks."""
        table_block = block_map.get(table_id)
        if not table_block:
            return Table(rows=[], page_number=page_number)
        
        rows: list[TableRow] = []
        relationships = table_block.get("Relationships", [])
        
        for rel in relationships:
            if rel["Type"] != "CHILD":
                continue
            
            cell_ids = rel.get("Ids", [])
            cells: list[TableCell] = []
            
            for cell_id in cell_ids:
                cell_block = block_map.get(cell_id)
                if not cell_block or cell_block.get("BlockType") != "CELL":
                    continue
                
                cell_text = cell_block.get("Text", "")
                row_idx = cell_block.get("RowIndex", 0)
                col_idx = cell_block.get("ColumnIndex", 0)
                is_header = cell_block.get("Confidence", 0) > 95
                confidence = cell_block.get("Confidence")
                
                cell = TableCell(
                    content=cell_text,
                    row_index=row_idx,
                    col_index=col_idx,
                    is_header=is_header,
                    confidence=confidence,
                )
                cells.append(cell)
            
            if cells:
                row = TableRow(cells=cells, row_index=len(rows))
                rows.append(row)
        
        return Table(rows=rows, page_number=page_number)

    def _extract_form(
        self,
        page_block: dict[str, Any],
        block_map: dict[str, Any],
        page_number: int,
    ) -> Optional[Form]:
        """Extract form (key-value pairs) from Textract response."""
        relationships = page_block.get("Relationships", [])
        fields: list[FormField] = []
        
        for rel in relationships:
            if rel["Type"] != "CHILD":
                continue
            
            for block_id in rel.get("Ids", []):
                block = block_map.get(block_id)
                if not block or block.get("BlockType") != "KEY_VALUE_SET":
                    continue
                
                entity_types = block.get("EntityTypes", [])
                if "KEY" not in entity_types:
                    continue
                
                # Get key text
                key_block = block_map.get(block_id)
                key_text = key_block.get("Text", "")
                
                # Find associated VALUE
                value_text = ""
                value_relationships = block.get("Relationships", [])
                for v_rel in value_relationships:
                    if v_rel["Type"] == "VALUE":
                        for value_id in v_rel.get("Ids", []):
                            value_block = block_map.get(value_id)
                            if value_block:
                                value_text += value_block.get("Text", "") + " "
                
                if key_text:
                    field = FormField(
                        key=key_text,
                        value=value_text.strip(),
                        confidence=block.get("Confidence"),
                    )
                    fields.append(field)
        
        if fields:
            return Form(fields=fields, page_number=page_number)
        return None

    async def extract_tables(self, file_path: str | Path) -> list[dict[str, Any]]:
        """Extract tables from document."""
        document = await self.parse(file_path, DocumentType.PDF)
        
        tables = []
        for page in document.pages:
            for table in page.tables:
                tables.append({
                    "page": page.page_number,
                    "rows": [
                        [cell.content for cell in row.cells]
                        for row in table.rows
                    ],
                })
        
        return tables

    async def extract_forms(self, file_path: str | Path) -> list[dict[str, Any]]:
        """Extract forms from document."""
        document = await self.parse(file_path, DocumentType.PDF)
        
        forms = []
        for page in document.pages:
            for form in page.forms:
                forms.append({
                    "page": page.page_number,
                    "fields": [
                        {"key": field.key, "value": field.value}
                        for field in form.fields
                    ],
                })
        
        return forms

    def supports_ocr(self) -> bool:
        """AWS Textract supports OCR."""
        return True
