"""Blob header data structure.

Reference: /hollow/src/main/java/com/netflix/hollow/core/write/HollowBlobHeaderWriter.java
"""

from typing import Optional

from pydantic import BaseModel, Field

from ..schema.object_schema import HollowObjectSchema
from .constants import HOLLOW_BLOB_VERSION_HEADER


class HollowBlobHeader(BaseModel):
    """Header for a Hollow blob (snapshot or delta).

    The header contains metadata about the blob including version, state transition tags,
    schemas, and optional header tags.

    Attributes:
        version: Blob format version (must be HOLLOW_BLOB_VERSION_HEADER = 1030)
        origin_randomized_tag: Random tag identifying the origin state (for delta safety)
        destination_randomized_tag: Random tag identifying the destination state
        schemas: List of schemas in this blob
        header_tags: Optional key-value metadata tags
    """

    version: int = Field(default=HOLLOW_BLOB_VERSION_HEADER, description="Blob format version")
    origin_randomized_tag: int = Field(..., description="Origin state random tag")
    destination_randomized_tag: int = Field(..., description="Destination state random tag")
    schemas: list[HollowObjectSchema] = Field(default_factory=list, description="Schemas in blob")
    header_tags: dict[str, str] = Field(default_factory=dict, description="Optional metadata tags")

    def get_schema(self, name: str) -> Optional[HollowObjectSchema]:
        """Get a schema by name.

        Args:
            name: Schema name

        Returns:
            Schema if found, None otherwise
        """
        for schema in self.schemas:
            if schema.name == name:
                return schema
        return None

    def has_schema(self, name: str) -> bool:
        """Check if a schema with the given name exists.

        Args:
            name: Schema name

        Returns:
            True if schema exists
        """
        return self.get_schema(name) is not None

    def num_schemas(self) -> int:
        """Get the number of schemas in this header.

        Returns:
            Number of schemas
        """
        return len(self.schemas)
