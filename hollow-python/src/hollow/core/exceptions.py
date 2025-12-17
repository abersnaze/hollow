"""Exception classes for Netflix Hollow Python implementation."""


class HollowException(Exception):
    """Base exception for all Hollow-related errors."""

    pass


class SchemaException(HollowException):
    """Exception raised for schema-related errors."""

    pass


class EncodingException(HollowException):
    """Exception raised for encoding/decoding errors."""

    pass


class BlobException(HollowException):
    """Exception raised for blob read/write errors."""

    pass
