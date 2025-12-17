"""Field types for Hollow schemas.

These field types must match the Java implementation exactly for wire compatibility.
Reference: /hollow/src/main/java/com/netflix/hollow/core/schema/HollowObjectSchema.java
"""

from enum import Enum


class FieldType(str, Enum):
    """Supported field types in Hollow OBJECT schemas."""

    REFERENCE = "REFERENCE"
    INT = "INT"
    LONG = "LONG"
    BOOLEAN = "BOOLEAN"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    BYTES = "BYTES"

    def __str__(self) -> str:
        """Return the field type name as a string."""
        return self.value
