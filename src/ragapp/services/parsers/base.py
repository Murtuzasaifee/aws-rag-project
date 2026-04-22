"""
src/ragapp/services/parsers/base.py

Abstract base classes and interfaces for document parsers.
This module defines the contract that all parser implementations must follow,
enabling a plug-and-play architecture for different parsing backends.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any

from ragapp.schemas.parsing import ParsedDocument, DocumentType


class BaseDocumentParser(ABC):
    """
    Abstract base class for document parsers.
    
    All parser implementations must inherit from this class and implement
    the required abstract methods. This enables a plug-and-play architecture
    where different parsing backends can be easily swapped.
    """

    def __init__(self, parser_name: str):
        """
        Initialize the parser.
        
        Args:
            parser_name: Human-readable name of the parser (e.g., 'AWS Textract', 'PyPDF')
        """
        self.parser_name = parser_name

    @abstractmethod
    async def parse(
        self,
        file_path: str | Path,
        document_type: DocumentType,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ParsedDocument:
        """
        Parse a document and extract structured content.
        
        Args:
            file_path: Path to the document file (can be local or remote)
            document_type: Type of document (PDF, DOCX, etc.)
            metadata: Optional custom metadata to attach to the parsed document
            
        Returns:
            ParsedDocument: Structured representation of parsed content
            
        Raises:
            UnsupportedDocumentTypeError: If document type not supported by parser
            CorruptedDocumentError: If document is corrupted or unreadable
            FileNotFoundError: If file not found at specified path
            UnicodeDecodeError: If encoding issues prevent parsing
        """
        pass

    @abstractmethod
    def supports_document_type(self, document_type: DocumentType) -> bool:
        """
        Check if this parser can handle a specific document type.
        
        Args:
            document_type: Type of document to check
            
        Returns:
            True if parser supports this document type, False otherwise
        """
        pass

    @abstractmethod
    async def validate_file(
        self,
        file_path: str | Path,
        max_size_mb: int = 50,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that a file is readable and within size constraints.
        
        Args:
            file_path: Path to file to validate
            max_size_mb: Maximum file size in megabytes
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if file is valid and readable
            - error_message: None if valid, error description if invalid
        """
        pass

    def get_parser_name(self) -> str:
        """Return the name of this parser."""
        return self.parser_name

    def get_supported_types(self) -> list[DocumentType]:
        """
        Return list of document types this parser supports.
        
        Returns:
            List of supported DocumentType enums
        """
        return [
            doc_type for doc_type in DocumentType
            if self.supports_document_type(doc_type)
        ]


class OCRParser(BaseDocumentParser):
    """
    Base class for OCR-based parsers that extract text and layout from images/scanned documents.
    
    This extends BaseDocumentParser with additional OCR-specific capabilities:
    - Confidence scores for character/word recognition
    - Layout and structure preservation
    - Support for tables, forms, and other structured elements
    - Multi-language support (if backend supports it)
    """

    @abstractmethod
    async def extract_tables(self, file_path: str | Path) -> list[dict[str, Any]]:
        """
        Extract structured table data from document.
        
        Args:
            file_path: Path to document
            
        Returns:
            List of table representations with rows/columns/cells
        """
        pass

    @abstractmethod
    async def extract_forms(self, file_path: str | Path) -> list[dict[str, Any]]:
        """
        Extract structured form data (key-value pairs) from document.
        
        Args:
            file_path: Path to document
            
        Returns:
            List of form representations with field names and values
        """
        pass

    @abstractmethod
    def supports_ocr(self) -> bool:
        """
        Check if this parser has OCR capabilities.
        
        Returns:
            True if parser can perform OCR on scanned/image-based documents
        """
        pass


class SimpleParser(BaseDocumentParser):
    """
    Base class for simple text-based parsers (TXT, basic Markdown, basic HTML).
    
    These parsers work on plaintext or structured text formats without OCR,
    focusing on encoding detection and basic structural extraction.
    """

    @abstractmethod
    def detect_encoding(self, file_path: str | Path) -> str:
        """
        Detect the text encoding of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected encoding name (e.g., 'utf-8', 'iso-8859-1')
        """
        pass

    @abstractmethod
    def normalize_encoding(self, content: str, target_encoding: str = "utf-8") -> str:
        """
        Normalize text to a target encoding (typically UTF-8).
        
        Args:
            content: Text content to normalize
            target_encoding: Target encoding (default: utf-8)
            
        Returns:
            Normalized text content
        """
        pass


class ParserFactory(ABC):
    """
    Abstract factory for creating parser instances based on document type and availability.
    
    Implementations of this interface should:
    1. Check available parsers and their capabilities
    2. Select appropriate parser based on document type
    3. Handle fallback scenarios when primary parser unavailable
    4. Manage parser lifecycle and dependencies
    """

    @abstractmethod
    def get_parser(self, document_type: DocumentType) -> BaseDocumentParser:
        """
        Get appropriate parser for a document type.
        
        Args:
            document_type: Type of document to parse
            
        Returns:
            Parser instance configured for this document type
            
        Raises:
            ValueError: If no suitable parser available for document type
        """
        pass

    @abstractmethod
    def get_available_parsers(self) -> dict[str, BaseDocumentParser]:
        """
        Get all available parsers.
        
        Returns:
            Dictionary mapping parser names to parser instances
        """
        pass

    @abstractmethod
    def register_parser(
        self,
        parser: BaseDocumentParser,
        document_types: list[DocumentType],
    ) -> None:
        """
        Register a parser for handling specific document types.
        
        Args:
            parser: Parser instance to register
            document_types: List of document types this parser handles
        """
        pass

    @abstractmethod
    def supports_document_type(self, document_type: DocumentType) -> bool:
        """
        Check if any parser is available for a document type.
        
        Args:
            document_type: Document type to check
            
        Returns:
            True if a parser is available for this type
        """
        pass
