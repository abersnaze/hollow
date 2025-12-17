"""Unit tests for schema serialization."""

import io

import pytest

from hollow.core.exceptions import SchemaException
from hollow.schema.field_type import FieldType
from hollow.schema.object_schema import HollowObjectSchema, PrimaryKey
from hollow.schema.serialization import (
    SCHEMA_TYPE_OBJECT,
    SCHEMA_TYPE_OBJECT_WITH_PK,
    read_object_schema,
    read_utf,
    write_object_schema,
    write_utf,
)


class TestUTFSerialization:
    """Tests for UTF string serialization (Java DataOutputStream format)."""

    def test_write_utf_simple_string(self) -> None:
        """Should write simple ASCII string."""
        stream = io.BytesIO()
        write_utf(stream, "hello")

        result = stream.getvalue()
        # First 2 bytes: length (5)
        # Next 5 bytes: "hello"
        assert result == b"\x00\x05hello"

    def test_write_utf_unicode_string(self) -> None:
        """Should write Unicode string correctly."""
        stream = io.BytesIO()
        write_utf(stream, "café")

        result = stream.getvalue()
        # "café" in UTF-8 is 5 bytes (é = 0xC3 0xA9)
        assert result[:2] == b"\x00\x05"
        assert result[2:] == "café".encode("utf-8")

    def test_write_utf_empty_string(self) -> None:
        """Should write empty string."""
        stream = io.BytesIO()
        write_utf(stream, "")

        result = stream.getvalue()
        assert result == b"\x00\x00"

    def test_write_utf_too_long(self) -> None:
        """Should raise error for strings > 65535 bytes."""
        stream = io.BytesIO()
        # Create string that's too long when UTF-8 encoded
        long_string = "a" * 70000

        with pytest.raises(ValueError, match="String too long"):
            write_utf(stream, long_string)

    def test_read_utf_simple_string(self) -> None:
        """Should read simple ASCII string."""
        stream = io.BytesIO(b"\x00\x05hello")
        result = read_utf(stream)

        assert result == "hello"

    def test_read_utf_unicode_string(self) -> None:
        """Should read Unicode string correctly."""
        stream = io.BytesIO(b"\x00\x05" + "café".encode("utf-8"))
        result = read_utf(stream)

        assert result == "café"

    def test_read_utf_empty_string(self) -> None:
        """Should read empty string."""
        stream = io.BytesIO(b"\x00\x00")
        result = read_utf(stream)

        assert result == ""

    def test_read_utf_unexpected_eof_length(self) -> None:
        """Should raise error on EOF while reading length."""
        stream = io.BytesIO(b"\x00")  # Only 1 byte instead of 2

        with pytest.raises(SchemaException, match="Unexpected EOF.*length"):
            read_utf(stream)

    def test_read_utf_unexpected_eof_data(self) -> None:
        """Should raise error on EOF while reading string data."""
        stream = io.BytesIO(b"\x00\x05hel")  # Only 3 bytes instead of 5

        with pytest.raises(SchemaException, match="Unexpected EOF.*string"):
            read_utf(stream)

    def test_utf_roundtrip(self) -> None:
        """UTF strings should roundtrip correctly."""
        test_strings = ["", "a", "hello", "café", "🎉 emoji", "日本語"]

        for test_str in test_strings:
            stream = io.BytesIO()
            write_utf(stream, test_str)
            stream.seek(0)
            result = read_utf(stream)
            assert result == test_str


class TestSchemaSerializationSimple:
    """Tests for simple schema serialization without primary keys."""

    def test_write_empty_schema(self) -> None:
        """Should write schema with no fields."""
        schema = HollowObjectSchema(name="Empty")
        stream = io.BytesIO()

        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Should start with type ID (0 for no PK)
        assert result[0] == SCHEMA_TYPE_OBJECT
        # Should contain schema name
        assert b"Empty" in result

    def test_write_schema_with_single_field(self) -> None:
        """Should write schema with one field."""
        schema = HollowObjectSchema(name="Simple")
        schema.add_field("id", FieldType.INT)

        stream = io.BytesIO()
        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Verify type ID
        assert result[0] == SCHEMA_TYPE_OBJECT
        # Verify it contains field name and type
        assert b"id" in result
        assert b"INT" in result

    def test_write_schema_with_multiple_fields(self) -> None:
        """Should write schema with multiple fields."""
        schema = HollowObjectSchema(name="Movie")
        schema.add_field("id", FieldType.INT)
        schema.add_field("title", FieldType.STRING)
        schema.add_field("year", FieldType.INT)

        stream = io.BytesIO()
        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Verify all field names are present
        assert b"id" in result
        assert b"title" in result
        assert b"year" in result

    def test_write_schema_with_reference_field(self) -> None:
        """Should write schema with REFERENCE field."""
        schema = HollowObjectSchema(name="Movie")
        schema.add_field("director", FieldType.REFERENCE, "Person")

        stream = io.BytesIO()
        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Verify REFERENCE type and referenced type name
        assert b"director" in result
        assert b"REFERENCE" in result
        assert b"Person" in result

    def test_roundtrip_simple_schema(self) -> None:
        """Simple schema should roundtrip correctly."""
        schema = HollowObjectSchema(name="Person")
        schema.add_field("name", FieldType.STRING)
        schema.add_field("age", FieldType.INT)

        # Write
        stream = io.BytesIO()
        write_object_schema(stream, schema)

        # Read
        stream.seek(0)
        result = read_object_schema(stream)

        # Verify
        assert result.name == "Person"
        assert result.num_fields() == 2
        assert result.get_field(0).name == "name"
        assert result.get_field(0).field_type == FieldType.STRING
        assert result.get_field(1).name == "age"
        assert result.get_field(1).field_type == FieldType.INT

    def test_roundtrip_all_field_types(self) -> None:
        """Schema with all field types should roundtrip."""
        schema = HollowObjectSchema(name="AllTypes")
        schema.add_field("intField", FieldType.INT)
        schema.add_field("longField", FieldType.LONG)
        schema.add_field("boolField", FieldType.BOOLEAN)
        schema.add_field("floatField", FieldType.FLOAT)
        schema.add_field("doubleField", FieldType.DOUBLE)
        schema.add_field("stringField", FieldType.STRING)
        schema.add_field("bytesField", FieldType.BYTES)
        schema.add_field("refField", FieldType.REFERENCE, "OtherType")

        # Write and read
        stream = io.BytesIO()
        write_object_schema(stream, schema)
        stream.seek(0)
        result = read_object_schema(stream)

        # Verify all fields
        assert result.num_fields() == 8
        assert result.get_field_by_name("intField").field_type == FieldType.INT
        assert result.get_field_by_name("refField").field_type == FieldType.REFERENCE
        assert result.get_field_by_name("refField").referenced_type == "OtherType"


class TestSchemaSerializationWithPrimaryKey:
    """Tests for schema serialization with primary keys."""

    def test_write_schema_with_simple_primary_key(self) -> None:
        """Should write schema with single-field primary key."""
        pk = PrimaryKey(schema_name="Movie", field_paths=["id"])
        schema = HollowObjectSchema(name="Movie", primary_key=pk)
        schema.add_field("id", FieldType.INT)
        schema.add_field("title", FieldType.STRING)

        stream = io.BytesIO()
        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Verify type ID for schema with PK
        assert result[0] == SCHEMA_TYPE_OBJECT_WITH_PK
        # Verify PK field path is present
        assert b"id" in result

    def test_write_schema_with_composite_primary_key(self) -> None:
        """Should write schema with multi-field primary key."""
        pk = PrimaryKey(schema_name="UserEvent", field_paths=["userId", "timestamp"])
        schema = HollowObjectSchema(name="UserEvent", primary_key=pk)
        schema.add_field("userId", FieldType.INT)
        schema.add_field("timestamp", FieldType.LONG)
        schema.add_field("eventType", FieldType.STRING)

        stream = io.BytesIO()
        write_object_schema(stream, schema)
        result = stream.getvalue()

        # Verify both PK field paths are present
        assert b"userId" in result
        assert b"timestamp" in result

    def test_roundtrip_schema_with_primary_key(self) -> None:
        """Schema with primary key should roundtrip correctly."""
        pk = PrimaryKey(schema_name="Movie", field_paths=["id"])
        schema = HollowObjectSchema(name="Movie", primary_key=pk)
        schema.add_field("id", FieldType.INT)
        schema.add_field("title", FieldType.STRING)

        # Write and read
        stream = io.BytesIO()
        write_object_schema(stream, schema)
        stream.seek(0)
        result = read_object_schema(stream)

        # Verify
        assert result.name == "Movie"
        assert result.has_primary_key()
        assert result.primary_key is not None
        assert result.primary_key.field_paths == ["id"]
        assert result.num_fields() == 2

    def test_roundtrip_schema_with_composite_primary_key(self) -> None:
        """Schema with composite primary key should roundtrip."""
        pk = PrimaryKey(schema_name="UserEvent", field_paths=["userId", "eventId"])
        schema = HollowObjectSchema(name="UserEvent", primary_key=pk)
        schema.add_field("userId", FieldType.INT)
        schema.add_field("eventId", FieldType.LONG)
        schema.add_field("data", FieldType.STRING)

        # Write and read
        stream = io.BytesIO()
        write_object_schema(stream, schema)
        stream.seek(0)
        result = read_object_schema(stream)

        # Verify
        assert result.has_primary_key()
        assert result.primary_key.field_paths == ["userId", "eventId"]


class TestSchemaDeserializationErrors:
    """Tests for schema deserialization error handling."""

    def test_read_invalid_type_id(self) -> None:
        """Should raise error for invalid type ID."""
        stream = io.BytesIO(b"\xFF")  # Invalid type ID

        with pytest.raises(SchemaException, match="Invalid OBJECT schema type ID"):
            read_object_schema(stream)

    def test_read_unexpected_eof(self) -> None:
        """Should raise error on unexpected EOF."""
        stream = io.BytesIO(b"")  # Empty stream

        with pytest.raises(SchemaException, match="Unexpected EOF"):
            read_object_schema(stream)

    def test_read_invalid_field_type(self) -> None:
        """Should raise error for invalid field type string."""
        # Manually construct invalid schema bytes
        stream = io.BytesIO()
        stream.write(bytes([SCHEMA_TYPE_OBJECT]))  # Type ID
        write_utf(stream, "Test")  # Schema name
        stream.write(b"\x00\x01")  # 1 field
        write_utf(stream, "field1")  # Field name
        write_utf(stream, "INVALID_TYPE")  # Invalid field type

        stream.seek(0)
        with pytest.raises(SchemaException, match="Invalid field type"):
            read_object_schema(stream)
