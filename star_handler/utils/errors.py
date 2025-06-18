"""Common error types for star handler processors."""

class StarHandlerError(Exception):
    """Base exception class for star handler errors."""
    pass

class FormatError(StarHandlerError):
    """Raised when input file format is invalid."""
    pass

class ProcessingError(StarHandlerError):
    """Raised when processing operations fail."""
    pass

class ValidationError(StarHandlerError):
    """Raised when input validation fails."""
    pass
