"""
src/ragapp/services/parsers/__init__.py

Document parsing service package.
Exports the main parsing service and factories.
"""

from ragapp.services.parsers.base import (
    BaseDocumentParser,
    OCRParser,
    SimpleParser,
    ParserFactory,
)
from ragapp.services.parsers.factory import (
    DefaultParserFactory,
    DocumentParserService,
)
from ragapp.services.parsers.textract_parser import AWSTextractParser
from ragapp.services.parsers.fallback_parsers import (
    PlainTextParser,
    MarkdownParser,
    HTMLParser,
    SimpleDOCXParser,
)

__all__ = [
    "BaseDocumentParser",
    "OCRParser",
    "SimpleParser",
    "ParserFactory",
    "DefaultParserFactory",
    "DocumentParserService",
    "AWSTextractParser",
    "PlainTextParser",
    "MarkdownParser",
    "HTMLParser",
    "SimpleDOCXParser",
]
