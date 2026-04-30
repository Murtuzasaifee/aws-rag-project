"""
src/ragapp/services/parsers/factory.py

Parser factory and orchestration logic for selecting and managing document parsers.
Implements a factory pattern for dynamic parser selection based on document type.
"""

from typing import Optional, Any, Dict, List

from ragapp.schemas.parsing import DocumentType, ParsedDocument
from ragapp.services.parsers.base import BaseDocumentParser, ParserFactory
from ragapp.services.parsers.textract_parser import AWSTextractParser
from ragapp.services.parsers.fallback_parsers import (
    PlainTextParser,
    MarkdownParser,
    HTMLParser,
    SimpleDOCXParser,
)
from ragapp.exception.parsing_exception import (
    ParserInitializationError,
    UnsupportedDocumentTypeError,
)
from ragapp.logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)


class DefaultParserFactory(ParserFactory):
    """
    Default implementation of ParserFactory with built-in parsers.
    
    Manages parser registration, selection, and fallback logic.
    Uses a priority-based approach: tries primary parsers first,
    falls back to simpler parsers if needed.
    """

    def __init__(self, aws_region: str = "us-east-1"):
        """
        Initialize parser factory with default parsers.
        
        Args:
            aws_region: AWS region for Textract
        """
        self.aws_region = aws_region
        self._parsers: Dict[str, BaseDocumentParser] = {}
        self._document_type_map: Dict[DocumentType, List[str]] = {}
        
        self._initialize_default_parsers()
        logger.info("Initialized DefaultParserFactory")

    def _initialize_default_parsers(self) -> None:
        """Initialize built-in parser instances."""
        # AWS Textract (primary OCR parser)
        try:
            textract = AWSTextractParser(self.aws_region)
            self.register_parser(textract, [DocumentType.PDF, DocumentType.DOCX])
            logger.info("Registered AWS Textract parser")
        except Exception as e:
            logger.warning("Failed to initialize AWS Textract parser", error=str(e))
        
        # Fallback parsers (text-based, no OCR)
        parsers_to_register = [
            (PlainTextParser(), [DocumentType.TXT]),
            (MarkdownParser(), [DocumentType.MARKDOWN]),
            (HTMLParser(), [DocumentType.HTML]),
            (SimpleDOCXParser(), [DocumentType.DOCX]),
        ]
        
        for parser, doc_types in parsers_to_register:
            self.register_parser(parser, doc_types)
            logger.info(f"Registered {parser.get_parser_name()} parser")

    def register_parser(
        self,
        parser: BaseDocumentParser,
        document_types: List[DocumentType],
    ) -> None:
        """
        Register a parser for specific document types.
        
        If multiple parsers support the same type, the most recently
        registered one becomes the primary parser.
        
        Args:
            parser: Parser instance
            document_types: List of DocumentType it supports
        """
        parser_name = parser.get_parser_name()
        self._parsers[parser_name] = parser
        
        for doc_type in document_types:
            if doc_type not in self._document_type_map:
                self._document_type_map[doc_type] = []
            
            # Add to front of list (most recent = primary)
            self._document_type_map[doc_type].insert(0, parser_name)
        
        logger.info(
            f"Registered parser '{parser_name}' for types: "
            f"{', '.join([dt.value for dt in document_types])}"
        )

    def get_parser(self, document_type: DocumentType) -> BaseDocumentParser:
        """
        Get appropriate parser for document type.
        
        Returns primary parser if available, else first fallback.
        
        Args:
            document_type: Type of document to parse
            
        Returns:
            Parser instance for this document type
            
        Raises:
            UnsupportedDocumentTypeError: If no parser available
        """
        parser_names = self._document_type_map.get(document_type, [])
        
        if not parser_names:
            supported = [dt.value for dt in self._document_type_map.keys()]
            logger.error(
                "No parser available for document type",
                document_type=document_type.value,
                supported_types=supported
            )
            raise UnsupportedDocumentTypeError(
                document_type.value,
                supported,
            )
        
        # Return primary parser (first in list)
        parser_name = parser_names[0]
        parser = self._parsers.get(parser_name)
        
        if not parser:
            raise ParserInitializationError(
                parser_name,
                "Parser not found in registry"
            )
        
        logger.info(
            f"Selected parser '{parser_name}' for document type '{document_type.value}'"
        )
        
        return parser

    def get_parser_chain(
        self,
        document_type: DocumentType,
    ) -> List[BaseDocumentParser]:
        """
        Get all available parsers for a document type in priority order.
        
        Useful for trying multiple parsers if first one fails.
        
        Args:
            document_type: Type of document
            
        Returns:
            List of parsers sorted by priority
        """
        parser_names = self._document_type_map.get(document_type, [])
        return [self._parsers[name] for name in parser_names if name in self._parsers]

    def get_available_parsers(self) -> Dict[str, BaseDocumentParser]:
        """Get all registered parsers."""
        return dict(self._parsers)

    def supports_document_type(self, document_type: DocumentType) -> bool:
        """Check if any parser supports this document type."""
        return document_type in self._document_type_map

    def get_supported_types(self) -> List[DocumentType]:
        """Get all supported document types."""
        return list(self._document_type_map.keys())


class DocumentParserService:
    """
    High-level service for parsing documents.
    
    Orchestrates parser selection, error handling, and retry logic.
    Provides a simple interface for the rest of the application.
    """

    def __init__(self, factory: Optional[ParserFactory] = None):
        """
        Initialize parser service.
        
        Args:
            factory: ParserFactory instance (uses DefaultParserFactory if None)
        """
        self.factory = factory or DefaultParserFactory()
        logger.info("Initialized DocumentParserService")

    async def parse(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_type: Optional[DocumentType] = None,
        allow_fallback: bool = True,
        include_traceback: bool = False,
    ) -> ParsedDocument:
        """
        Parse a document with automatic parser selection.
        
        Args:
            file_path: Path to the document
            metadata: Optional custom metadata
            document_type: Document type (auto-detected if None)
            allow_fallback: Whether to try fallback parsers on primary failure
            include_traceback: Include detailed error traceback
            
        Returns:
            ParsedDocument with extracted content
            
        Raises:
            UnsupportedDocumentTypeError: If type not supported
            CorruptedDocumentError: If document cannot be parsed
            Various parsing-specific exceptions
        """
        from ragapp.services.parsers.utils import detect_document_type
        
        # Auto-detect document type if not provided
        if document_type is None:
            document_type = detect_document_type(file_path)
            logger.info(f"Auto-detected document type: {document_type.value}")
        
        # Get parser chain for this type
        parser_chain = self.factory.get_parser_chain(document_type)
        
        if not parser_chain:
            raise UnsupportedDocumentTypeError(
                document_type.value,
                [dt.value for dt in self.factory.get_supported_types()]
            )
        
        last_error = None
        
        # Try each parser in chain
        for parser in parser_chain:
            try:
                logger.info(
                    f"Attempting parse with {parser.get_parser_name()}",
                    file=file_path,
                    type=document_type.value
                )
                
                document = await parser.parse(file_path, document_type, metadata)
                
                logger.info(
                    f"Successfully parsed document with {parser.get_parser_name()}",
                    file=file_path,
                    pages=document.total_pages,
                    elements=sum(len(p.elements) for p in document.pages)
                )
                
                return document
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Parser {parser.get_parser_name()} failed",
                    file=file_path,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                if not allow_fallback:
                    raise
                
                # Continue to next parser
                continue
        
        # All parsers failed
        if last_error:
            logger.error(
                "All parsers failed for document",
                file=file_path,
                type=document_type.value,
                last_error=str(last_error)
            )
            raise last_error
        else:
            raise UnsupportedDocumentTypeError(
                document_type.value,
                [dt.value for dt in self.factory.get_supported_types()]
            )

    def get_supported_types(self) -> List[DocumentType]:
        """Get all supported document types."""
        return self.factory.get_supported_types()

    def get_supported_types_str(self) -> str:
        """Get supported types as comma-separated string."""
        return ", ".join([dt.value for dt in self.get_supported_types()])
