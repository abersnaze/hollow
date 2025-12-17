"""Core constants for Netflix Hollow Python implementation.

These constants must match the Java implementation exactly for wire compatibility.
"""

# Blob format version - must match Java's HOLLOW_BLOB_VERSION_HEADER
HOLLOW_BLOB_VERSION_HEADER = 1030

# Null ordinal value
NULL_ORDINAL = -1

# VarInt null indicator
VARINT_NULL = 0x80
