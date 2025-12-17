"""Unit tests for Hollow OBJECT schema with Pydantic."""

import pytest
from pydantic import ValidationError

from hollow.schema.field_type import FieldType
from hollow.schema.object_schema import FieldDefinition, HollowObjectSchema, PrimaryKey


class TestFieldDefinition:
    """Tests for FieldDefinition Pydantic model."""

    def test_create_int_field(self) -> None:
        """Should create INT field without referenced_type."""
        field = FieldDefinition(name="age", field_type=FieldType.INT)
        assert field.name == "age"
        assert field.field_type == FieldType.INT
        assert field.referenced_type is None

    def test_create_reference_field(self) -> None:
        """Should create REFERENCE field with referenced_type."""
        field = FieldDefinition(
            name="author", field_type=FieldType.REFERENCE, referenced_type="Person"
        )
        assert field.name == "author"
        assert field.field_type == FieldType.REFERENCE
        assert field.referenced_type == "Person"

    def test_reference_field_requires_referenced_type(self) -> None:
        """REFERENCE fields must have referenced_type."""
        with pytest.raises(ValidationError, match="REFERENCE fields must specify referenced_type"):
            FieldDefinition(name="author", field_type=FieldType.REFERENCE)

    def test_non_reference_field_cannot_have_referenced_type(self) -> None:
        """Non-REFERENCE fields cannot have referenced_type."""
        with pytest.raises(ValidationError, match="Only REFERENCE fields can have referenced_type"):
            FieldDefinition(name="age", field_type=FieldType.INT, referenced_type="SomeType")


class TestPrimaryKey:
    """Tests for PrimaryKey Pydantic model."""

    def test_create_simple_primary_key(self) -> None:
        """Should create primary key with single field."""
        pk = PrimaryKey(schema_name="Movie", field_paths=["id"])
        assert pk.schema_name == "Movie"
        assert pk.field_paths == ["id"]

    def test_create_composite_primary_key(self) -> None:
        """Should create composite primary key with multiple fields."""
        pk = PrimaryKey(schema_name="UserEvent", field_paths=["userId", "timestamp"])
        assert pk.schema_name == "UserEvent"
        assert len(pk.field_paths) == 2

    def test_primary_key_requires_at_least_one_field(self) -> None:
        """Primary key must have at least one field path."""
        with pytest.raises(ValidationError):
            PrimaryKey(schema_name="Movie", field_paths=[])


class TestHollowObjectSchema:
    """Tests for HollowObjectSchema Pydantic model."""

    def test_create_empty_schema(self) -> None:
        """Should create schema with no fields."""
        schema = HollowObjectSchema(name="Empty")
        assert schema.name == "Empty"
        assert schema.num_fields() == 0
        assert not schema.has_primary_key()

    def test_create_schema_with_fields(self) -> None:
        """Should create schema with predefined fields."""
        fields = [
            FieldDefinition(name="id", field_type=FieldType.INT),
            FieldDefinition(name="title", field_type=FieldType.STRING),
        ]
        schema = HollowObjectSchema(name="Movie", fields=fields)
        assert schema.num_fields() == 2
        assert schema.get_field(0).name == "id"
        assert schema.get_field(1).name == "title"

    def test_add_field(self) -> None:
        """Should add fields and return correct positions."""
        schema = HollowObjectSchema(name="Person")

        pos0 = schema.add_field("name", FieldType.STRING)
        pos1 = schema.add_field("age", FieldType.INT)
        pos2 = schema.add_field("email", FieldType.STRING)

        assert pos0 == 0
        assert pos1 == 1
        assert pos2 == 2
        assert schema.num_fields() == 3

    def test_get_position_by_name(self) -> None:
        """Should retrieve field position by name."""
        schema = HollowObjectSchema(name="Person")
        schema.add_field("name", FieldType.STRING)
        schema.add_field("age", FieldType.INT)

        assert schema.get_position("name") == 0
        assert schema.get_position("age") == 1

    def test_get_position_nonexistent_field(self) -> None:
        """Should raise KeyError for nonexistent field."""
        schema = HollowObjectSchema(name="Person")
        schema.add_field("name", FieldType.STRING)

        with pytest.raises(KeyError, match="Field 'age' not found"):
            schema.get_position("age")

    def test_get_field_by_position(self) -> None:
        """Should retrieve field by position."""
        schema = HollowObjectSchema(name="Person")
        schema.add_field("name", FieldType.STRING)
        schema.add_field("age", FieldType.INT)

        field = schema.get_field(1)
        assert field.name == "age"
        assert field.field_type == FieldType.INT

    def test_get_field_by_name(self) -> None:
        """Should retrieve field by name."""
        schema = HollowObjectSchema(name="Person")
        schema.add_field("name", FieldType.STRING)
        schema.add_field("age", FieldType.INT)

        field = schema.get_field_by_name("age")
        assert field.name == "age"
        assert field.field_type == FieldType.INT

    def test_add_reference_field(self) -> None:
        """Should add REFERENCE field with referenced type."""
        schema = HollowObjectSchema(name="Movie")
        schema.add_field("director", FieldType.REFERENCE, "Person")

        field = schema.get_field(0)
        assert field.field_type == FieldType.REFERENCE
        assert field.referenced_type == "Person"

    def test_create_schema_with_primary_key(self) -> None:
        """Should create schema with primary key."""
        pk = PrimaryKey(schema_name="Movie", field_paths=["id"])
        schema = HollowObjectSchema(name="Movie", primary_key=pk)

        assert schema.has_primary_key()
        assert schema.primary_key is not None
        assert schema.primary_key.field_paths == ["id"]

    def test_primary_key_schema_name_must_match(self) -> None:
        """Primary key schema_name must match schema name."""
        pk = PrimaryKey(schema_name="WrongName", field_paths=["id"])

        with pytest.raises(ValidationError, match="does not match schema name"):
            HollowObjectSchema(name="Movie", primary_key=pk)

    def test_all_field_types(self) -> None:
        """Should support all field types."""
        schema = HollowObjectSchema(name="AllTypes")

        schema.add_field("intField", FieldType.INT)
        schema.add_field("longField", FieldType.LONG)
        schema.add_field("boolField", FieldType.BOOLEAN)
        schema.add_field("floatField", FieldType.FLOAT)
        schema.add_field("doubleField", FieldType.DOUBLE)
        schema.add_field("stringField", FieldType.STRING)
        schema.add_field("bytesField", FieldType.BYTES)
        schema.add_field("refField", FieldType.REFERENCE, "OtherType")

        assert schema.num_fields() == 8
        assert schema.get_field_by_name("refField").referenced_type == "OtherType"

    def test_schema_name_required(self) -> None:
        """Schema name is required."""
        with pytest.raises(ValidationError):
            HollowObjectSchema(name="")


class TestSchemaEquality:
    """Tests for schema comparison and hashing."""

    def test_schemas_with_same_data_are_equal(self) -> None:
        """Schemas with identical data should be equal."""
        schema1 = HollowObjectSchema(name="Movie")
        schema1.add_field("title", FieldType.STRING)
        schema1.add_field("year", FieldType.INT)

        schema2 = HollowObjectSchema(name="Movie")
        schema2.add_field("title", FieldType.STRING)
        schema2.add_field("year", FieldType.INT)

        # Pydantic models use model_dump for equality
        assert schema1.model_dump() == schema2.model_dump()

    def test_schemas_with_different_names_are_not_equal(self) -> None:
        """Schemas with different names should not be equal."""
        schema1 = HollowObjectSchema(name="Movie")
        schema2 = HollowObjectSchema(name="Book")

        assert schema1.model_dump() != schema2.model_dump()
