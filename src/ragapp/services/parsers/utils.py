"""
src/ragapp/services/parsers/utils.py

Utility functions for document parsing: file type detection, encoding validation,
file validation, and other helper functions.
"""

import os
import io
import chardet
from pathlib import Path
from typing import Optional, Tuple

from ragapp.schemas.parsing import DocumentType
from ragapp.exception.parsing_exception import (
    UnsupportedDocumentTypeError,
    EncodingError,
    FileSizeExceededError,
    FileNotFoundError as ParsingFileNotFoundError,
    CorruptedDocumentError,
)
from ragapp.logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__name__)


# ── File Type Detection ────────────────────────────────────────────────────────

def detect_document_type(file_path: str | Path) -> DocumentType:
    """
    Detect document type from file extension and magic bytes.
    
    Performs two-level detection:
    1. Extension-based detection (fast)
    2. Magic byte detection (accurate, fallback)
    
    Args:
        file_path: Path to the file
        
    Returns:
        DocumentType enum value
        
    Raises:
        FileNotFoundError: If file doesn't exist
        UnsupportedDocumentTypeError: If type cannot be determined or is unsupported
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error("File not found", file_path=str(file_path))
        raise ParsingFileNotFoundError(str(file_path))
    
    # Extension-based detection (fast path)
    extension = file_path.suffix.lower()
    
    extension_map = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".doc": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
        ".text": DocumentType.TXT,
        ".html": DocumentType.HTML,
        ".htm": DocumentType.HTML,
        ".md": DocumentType.MARKDOWN,
        ".markdown": DocumentType.MARKDOWN,
    }
    
    if extension in extension_map:
        doc_type = extension_map[extension]
        logger.info("Detected document type from extension", 
                   file=str(file_path), type=doc_type.value)
        return doc_type
    
    # Magic byte detection (accurate path)
    try:
        with open(file_path, "rb") as f:
            magic_bytes = f.read(512)
        
        detected_type = _detect_by_magic_bytes(magic_bytes)
        if detected_type != DocumentType.UNKNOWN:
            logger.info("Detected document type from magic bytes",
                       file=str(file_path), type=detected_type.value)
            return detected_type
    except Exception as e:
        logger.warning("Failed to detect document type from magic bytes",
                      file=str(file_path), error=str(e))
    
    logger.error("Cannot determine document type",
                file=str(file_path), extension=extension)
    raise UnsupportedDocumentTypeError(
        document_type=extension or "unknown",
        supported_types=[dt.value for dt in DocumentType if dt != DocumentType.UNKNOWN],
    )


def _detect_by_magic_bytes(data: bytes) -> DocumentType:
    """
    Detect document type from file magic bytes (file signatures).
    
    Args:
        data: First 512 bytes of file
        
    Returns:
        DocumentType if recognized, else DocumentType.UNKNOWN
    """
    # PDF: %PDF
    if data.startswith(b"%PDF"):
        return DocumentType.PDF
    
    # DOCX/PPTX/XLSX: ZIP format with specific internal files
    if data.startswith(b"PK\x03\x04"):
        # DOCX contains word/document.xml
        if b"word/" in data or b"ppt/" in data or b"xl/" in data:
            return DocumentType.DOCX
    
    # HTML/XML: Common HTML/XML signatures
    if data.startswith(b"<!DOCTYPE") or data.startswith(b"<html") or data.startswith(b"<?xml"):
        return DocumentType.HTML
    
    # Don't treat all UTF-8 decodable files as TXT
    # Plain text detection should be more restrictive
    return DocumentType.UNKNOWN


# ── Encoding Detection & Normalization ──────────────────────────────────────

def detect_encoding(file_path: str | Path, sample_size: int = 10000) -> str:
    """
    Detect file encoding using chardet library.
    
    Reads a sample of the file and uses statistical analysis to detect encoding.
    Falls back to UTF-8 if detection fails.
    
    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample for detection
        
    Returns:
        Detected encoding name (e.g., 'utf-8', 'iso-8859-1')
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise ParsingFileNotFoundError(str(file_path))
    
    try:
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)
        
        detection = chardet.detect(sample)
        
        if detection and detection.get("encoding"):
            encoding = detection["encoding"].lower()
            confidence = detection.get("confidence", 0)
            logger.info("Detected file encoding",
                       file=str(file_path), encoding=encoding,
                       confidence=confidence)
            return encoding
    except Exception as e:
        logger.warning("Error during encoding detection",
                      file=str(file_path), error=str(e))
    
    # Fallback to UTF-8
    logger.info("Falling back to UTF-8 encoding",
               file=str(file_path))
    return "utf-8"


def normalize_to_utf8(
    content: str,
    source_encoding: Optional[str] = None,
) -> str:
    """
    Normalize text to UTF-8, handling invalid characters gracefully.
    
    Args:
        content: Text content to normalize
        source_encoding: Source encoding (if already decoded, can be None)
        
    Returns:
        UTF-8 normalized text with invalid characters replaced or removed
    """
    if isinstance(content, bytes):
        # If bytes, decode with error handling
        if source_encoding:
            try:
                content = content.decode(source_encoding, errors="replace")
            except Exception:
                content = content.decode("utf-8", errors="replace")
        else:
            content = content.decode("utf-8", errors="replace")
    
    # Remove NULL bytes and other problematic characters
    content = content.replace("\x00", "")
    
    # Normalize line endings to \n
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    
    # Remove multiple consecutive spaces/newlines (normalize whitespace)
    # But preserve intentional formatting
    import re
    content = re.sub(r"\n\n\n+", "\n\n", content)
    
    return content


def validate_and_decode_text_file(
    file_path: str | Path,
) -> Tuple[str, str]:
    """
    Validate and decode a text file with automatic encoding detection.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (decoded_content, used_encoding)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        EncodingError: If file cannot be decoded
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise ParsingFileNotFoundError(str(file_path))
    
    encoding = detect_encoding(file_path)
    
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
        
        # Normalize to UTF-8
        content = normalize_to_utf8(content, encoding)
        
        logger.info("Successfully decoded text file",
                   file=str(file_path), encoding=encoding)
        return content, encoding
    except Exception as e:
        logger.error("Failed to decode text file",
                    file=str(file_path), encoding=encoding, error=str(e))
        raise EncodingError(str(file_path), encoding, e)


# ── File Validation ────────────────────────────────────────────────────────────

async def validate_file(
    file_path: str | Path,
    max_size_mb: int = 50,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file exists, is readable, and within size constraints.
    
    Args:
        file_path: Path to file to validate
        max_size_mb: Maximum allowed file size in megabytes
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if all validations pass
        - error_message: None if valid, error description if invalid
    """
    file_path = Path(file_path)
    
    # Check existence
    if not file_path.exists():
        error_msg = f"File not found: {file_path}"
        logger.warning("File validation failed", reason=error_msg)
        return False, error_msg
    
    # Check if it's a file (not directory)
    if not file_path.is_file():
        error_msg = f"Path is not a file: {file_path}"
        logger.warning("File validation failed", reason=error_msg)
        return False, error_msg
    
    # Check readability
    if not os.access(file_path, os.R_OK):
        error_msg = f"File is not readable: {file_path}"
        logger.warning("File validation failed", reason=error_msg)
        return False, error_msg
    
    # Check file size
    file_size_bytes = file_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        error_msg = (
            f"File size ({file_size_mb:.2f} MB) exceeds "
            f"maximum allowed ({max_size_mb} MB)"
        )
        logger.warning("File validation failed", reason=error_msg)
        return False, error_msg
    
    # Check minimum size (at least 1 byte)
    if file_size_bytes == 0:
        error_msg = "File is empty"
        logger.warning("File validation failed", reason=error_msg)
        return False, error_msg
    
    logger.info("File validation passed",
               file=str(file_path), size_mb=file_size_mb)
    return True, None


# ── Document Structure Detection ───────────────────────────────────────────────

def is_html_like(content: str) -> bool:
    """
    Detect if content appears to be HTML or XML-based.
    
    Args:
        content: Text content to check
        
    Returns:
        True if content looks like HTML/XML
    """
    if not content:
        return False
    
    content_lower = content.lower().strip()
    html_indicators = [
        "<!doctype",
        "<html",
        "<head",
        "<body",
        "<div",
        "<span",
        "<p>",
        "<table",
        "<?xml",
    ]
    
    return any(content_lower.startswith(indicator) for indicator in html_indicators)


def is_markdown_like(content: str) -> bool:
    """
    Detect if content appears to be Markdown formatted.
    
    Args:
        content: Text content to check
        
    Returns:
        True if content looks like Markdown
    """
    if not content:
        return False
    
    import re
    
    markdown_patterns = [
        r"^#+\s+",           # Headings (# ## ### etc)
        r"^[-*]\s+",         # Unordered lists
        r"^\d+\.\s+",        # Ordered lists  
        r"\[.+\]",           # Links
        r"!\[.+\]",          # Images
        r"```",              # Code blocks
        r"\*\*.+?\*\*",      # Bold
        r"__.+?__",          # Bold (alt)
        r"\*.+?\*",          # Italic
        r"_.+?_",            # Italic (alt)
    ]
    
    # Check for at least 1 markdown pattern
    for pattern in markdown_patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    
    return False
