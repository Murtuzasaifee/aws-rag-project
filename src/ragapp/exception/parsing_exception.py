"""
src/ragapp/exception/parsing_exception.py

Parsing-specific exception classes for structured error reporting.
"""

from typing import Optional, Any
from ragapp.exception.custom_exception import RagAppException


class ParsingException(RagAppException):
    """Base exception for all parsing-related errors."""

    def __init__(
        self,
        error_message: str,
        error_details: Optional[object] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(error_message, error_details)
        self.error_code = error_code or "PARSING_ERROR"


class UnsupportedDocumentTypeError(ParsingException):
    """Raised when document type is not supported by any parser."""

    def __init__(
        self,
        document_type: str,
        supported_types: Optional[list[str]] = None,
        error_details: Optional[object] = None,
    ):
        msg = f"Document type '{document_type}' is not supported"
        if supported_types:
            msg += f". Supported types: {', '.join(supported_types)}"
        super().__init__(msg, error_details, "UNSUPPORTED_DOCUMENT_TYPE")
        self.document_type = document_type
        self.supported_types = supported_types or []


class CorruptedDocumentError(ParsingException):
    """Raised when document is corrupted, unreadable, or malformed."""

    def __init__(
        self,
        file_name: str,
        reason: str,
        error_details: Optional[object] = None,
    ):
        msg = f"Document '{file_name}' is corrupted or unreadable: {reason}"
        super().__init__(msg, error_details, "CORRUPTED_DOCUMENT")
        self.file_name = file_name
        self.reason = reason


class EncodingError(ParsingException):
    """Raised when file encoding cannot be detected or text cannot be decoded."""

    def __init__(
        self,
        file_name: str,
        detected_encoding: Optional[str] = None,
        error_details: Optional[object] = None,
    ):
        msg = f"Encoding error in '{file_name}'"
        if detected_encoding:
            msg += f". Detected encoding: {detected_encoding}"
        super().__init__(msg, error_details, "ENCODING_ERROR")
        self.file_name = file_name
        self.detected_encoding = detected_encoding


class FileSizeExceededError(ParsingException):
    """Raised when file size exceeds maximum allowed."""

    def __init__(
        self,
        file_name: str,
        file_size_mb: float,
        max_size_mb: int,
        error_details: Optional[object] = None,
    ):
        msg = (
            f"File '{file_name}' size ({file_size_mb:.2f} MB) "
            f"exceeds maximum allowed size ({max_size_mb} MB)"
        )
        super().__init__(msg, error_details, "FILE_SIZE_EXCEEDED")
        self.file_name = file_name
        self.file_size_mb = file_size_mb
        self.max_size_mb = max_size_mb


class FileNotFoundError(ParsingException):
    """Raised when document file cannot be found."""

    def __init__(
        self,
        file_path: str,
        error_details: Optional[object] = None,
    ):
        msg = f"Document file not found: {file_path}"
        super().__init__(msg, error_details, "FILE_NOT_FOUND")
        self.file_path = file_path


class ParserInitializationError(ParsingException):
    """Raised when parser cannot be initialized or configured."""

    def __init__(
        self,
        parser_name: str,
        reason: str,
        error_details: Optional[object] = None,
    ):
        msg = f"Failed to initialize parser '{parser_name}': {reason}"
        super().__init__(msg, error_details, "PARSER_INITIALIZATION_ERROR")
        self.parser_name = parser_name
        self.reason = reason


class TextractServiceError(ParsingException):
    """Raised when AWS Textract service fails or returns error."""

    def __init__(
        self,
        error_code: str,
        message: str,
        request_id: Optional[str] = None,
        error_details: Optional[object] = None,
    ):
        msg = f"AWS Textract error ({error_code}): {message}"
        if request_id:
            msg += f" (RequestId: {request_id})"
        super().__init__(msg, error_details, f"TEXTRACT_{error_code}")
        self.textract_error_code = error_code
        self.request_id = request_id


class ExtractionQualityWarning(ParsingException):
    """Raised as warning when extraction quality is below acceptable threshold."""

    def __init__(
        self,
        message: str,
        confidence_score: Optional[float] = None,
        error_details: Optional[object] = None,
    ):
        msg = f"Low extraction quality: {message}"
        if confidence_score is not None:
            msg += f" (confidence: {confidence_score:.2%})"
        super().__init__(msg, error_details, "EXTRACTION_QUALITY_WARNING")
        self.confidence_score = confidence_score


class ParsingTimeoutError(ParsingException):
    """Raised when parsing operation exceeds time limit."""

    def __init__(
        self,
        file_name: str,
        timeout_seconds: float,
        error_details: Optional[object] = None,
    ):
        msg = (
            f"Parsing of '{file_name}' exceeded timeout "
            f"({timeout_seconds:.1f} seconds)"
        )
        super().__init__(msg, error_details, "PARSING_TIMEOUT")
        self.file_name = file_name
        self.timeout_seconds = timeout_seconds


def create_error_response(
    exception: ParsingException,
    include_traceback: bool = False,
) -> dict[str, Any]:
    """
    Create a structured error response from a parsing exception.
    
    Args:
        exception: The parsing exception
        include_traceback: Whether to include full traceback
        
    Returns:
        Dictionary with error details suitable for API responses
    """
    error_dict: dict[str, Any] = {
        "success": False,
        "error_code": exception.error_code,
        "error_message": exception.error_message,
        "file": exception.file_name if hasattr(exception, "file_name") else None,
        "line": exception.lineno,
    }

    if include_traceback and exception.traceback_str:
        error_dict["traceback"] = exception.traceback_str

    # Add type-specific details
    if isinstance(exception, UnsupportedDocumentTypeError):
        error_dict["document_type"] = exception.document_type
        error_dict["supported_types"] = exception.supported_types
    elif isinstance(exception, FileSizeExceededError):
        error_dict["file_size_mb"] = exception.file_size_mb
        error_dict["max_size_mb"] = exception.max_size_mb
    elif isinstance(exception, EncodingError):
        error_dict["detected_encoding"] = exception.detected_encoding
    elif isinstance(exception, TextractServiceError):
        error_dict["textract_error_code"] = exception.textract_error_code
        error_dict["request_id"] = exception.request_id

    return error_dict
