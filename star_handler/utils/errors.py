"""Common error types for star handler."""

class StarFileError(Exception):
    """Base exception class for all star_handler errors."""
    pass

class FormatError(StarFileError):
    """Raised when input file format is invalid."""
    pass

class ProcessingError(StarFileError):
    """Raised when processing operations fail."""
    pass

class ValidationError(StarFileError):
    """Raised when input validation fails."""
    pass

class AnalysisError(StarFileError):
    """Base exception for analysis errors."""
    pass
