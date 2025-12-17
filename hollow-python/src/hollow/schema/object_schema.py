"""Hollow OBJECT schema implementation using Pydantic.

Reference: /hollow/src/main/java/com/netflix/hollow/core/schema/HollowObjectSchema.java
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .field_type import FieldType


class FieldDefinition(BaseModel):
    """Definition of a field in a Hollow OBJECT schema."""

    name: str = Field(..., description="Field name")
    field_type: FieldType = Field(..., description="Field type")
    referenced_type: Optional[str] = Field(None, description="Referenced type name for REFERENCE fields")

    @model_validator(mode="after")
    def validate_reference_type(self) -> "FieldDefinition":
        """Validate that REFERENCE fields have a referenced_type."""
        if self.field_type == FieldType.REFERENCE and self.referenced_type is None:
            raise ValueError("REFERENCE fields must specify referenced_type")
        if self.field_type != FieldType.REFERENCE and self.referenced_type is not None:
            raise ValueError(f"Only REFERENCE fields can have referenced_type, got {self.field_type}")
        return self


class PrimaryKey(BaseModel):
    """Primary key definition for a Hollow OBJECT schema."""

    schema_name: str = Field(..., description="Name of the schema this primary key belongs to")
    field_paths: list[str] = Field(..., min_length=1, description="Field paths that make up the primary key")


class HollowObjectSchema(BaseModel):
    """Pydantic model for Hollow OBJECT schema.

    This represents the schema for a Hollow OBJECT type, which contains a fixed set
    of strongly-typed fields. Fields can be primitives (INT, LONG, etc.), STRING/BYTES,
    or REFERENCE to other object types.

    Attributes:
        name: Schema name (type name)
        fields: List of field definitions
        primary_key: Optional primary key definition
    """

    name: str = Field(..., min_length=1, description="Schema name")
    fields: list[FieldDefinition] = Field(default_factory=list, description="Field definitions")
    primary_key: Optional[PrimaryKey] = Field(None, description="Primary key definition")

    # Internal field for tracking field positions by name
    _field_index: dict[str, int] = {}

    @model_validator(mode="after")
    def build_field_index(self) -> "HollowObjectSchema":
        """Build internal index for field name lookups."""
        self._field_index = {field.name: idx for idx, field in enumerate(self.fields)}
        return self

    @model_validator(mode="after")
    def validate_primary_key_schema_name(self) -> "HollowObjectSchema":
        """Validate that primary key schema_name matches this schema's name."""
        if self.primary_key and self.primary_key.schema_name != self.name:
            raise ValueError(
                f"Primary key schema_name '{self.primary_key.schema_name}' "
                f"does not match schema name '{self.name}'"
            )
        return self

    def add_field(
        self, name: str, field_type: FieldType, referenced_type: Optional[str] = None
    ) -> int:
        """Add a field to the schema.

        Args:
            name: Field name
            field_type: Field type
            referenced_type: Referenced type name (required for REFERENCE fields)

        Returns:
            Position (index) of the newly added field

        Raises:
            ValueError: If validation fails
        """
        field = FieldDefinition(name=name, field_type=field_type, referenced_type=referenced_type)
        position = len(self.fields)
        self.fields.append(field)
        self._field_index[name] = position
        return position

    def get_position(self, field_name: str) -> int:
        """Get the position (index) of a field by name.

        Args:
            field_name: Name of the field

        Returns:
            Field position (0-indexed)

        Raises:
            KeyError: If field does not exist
        """
        if field_name not in self._field_index:
            raise KeyError(f"Field '{field_name}' not found in schema '{self.name}'")
        return self._field_index[field_name]

    def get_field(self, position: int) -> FieldDefinition:
        """Get a field definition by position.

        Args:
            position: Field position (0-indexed)

        Returns:
            Field definition

        Raises:
            IndexError: If position is out of range
        """
        return self.fields[position]

    def get_field_by_name(self, field_name: str) -> FieldDefinition:
        """Get a field definition by name.

        Args:
            field_name: Name of the field

        Returns:
            Field definition

        Raises:
            KeyError: If field does not exist
        """
        position = self.get_position(field_name)
        return self.fields[position]

    def num_fields(self) -> int:
        """Get the number of fields in this schema.

        Returns:
            Number of fields
        """
        return len(self.fields)

    def has_primary_key(self) -> bool:
        """Check if this schema has a primary key defined.

        Returns:
            True if primary key is defined
        """
        return self.primary_key is not None
