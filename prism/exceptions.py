"""
Custom exceptions for the Prism CLI application.
"""


class PrismError(Exception):
    """Base exception for all Prism-related errors."""
    pass


class ValidationError(PrismError):
    """Raised when validation fails for an item or operation."""
    pass


class NotFoundError(PrismError):
    """Raised when a requested item is not found."""
    pass


class InvalidOperationError(PrismError):
    """Raised when an operation is not allowed in the current state."""
    pass


class DuplicateError(PrismError):
    """Raised when attempting to create a duplicate item."""
    pass


class ConfigurationError(PrismError):
    """Raised when there's a configuration or setup issue."""
    pass
