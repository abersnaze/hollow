"""Unit tests for blob header serialization."""

import io

import pytest

from hollow.core.blob_header import HollowBlobHeader
from hollow.core.constants import HOLLOW_BLOB_VERSION_HEADER
from hollow.core.exceptions import BlobException
from hollow.core.header_serialization import read_header, write_header
from hollow.schema.field_type import FieldType
from hollow.schema.object_schema import HollowObjectSchema, PrimaryKey


class TestBlobHeader:
    """Tests for HollowBlobHeader model."""

    def test_create_minimal_header(self) -> None:
        """Should create header with minimal fields."""
        header = HollowBlobHeader(
            origin_randomized_tag=12345, destination_randomized_tag=67890
        )

        assert header.version == HOLLOW_BLOB_VERSION_HEADER
        assert header.origin_randomized_tag == 12345
        assert header.destination_randomized_tag == 67890
        assert header.num_schemas() == 0
        assert len(header.header_tags) == 0

    def test_create_header_with_schemas(self) -> None:
        """Should create header with schemas."""
        schema1 = HollowObjectSchema(name="Movie")
        schema1.add_field("title", FieldType.STRING)

        schema2 = HollowObjectSchema(name="Person")
        schema2.add_field("name", FieldType.STRING)

        header = HollowBlobHeader(
            origin_randomized_tag=100,
            destination_randomized_tag=200,
            schemas=[schema1, schema2],
        )

        assert header.num_schemas() == 2
        assert header.has_schema("Movie")
        assert header.has_schema("Person")
        assert not header.has_schema("NonExistent")

    def test_get_schema_by_name(self) -> None:
        """Should retrieve schema by name."""
        schema = HollowObjectSchema(name="Movie")
        schema.add_field("title", FieldType.STRING)

        header = HollowBlobHeader(
            origin_randomized_tag=1, destination_randomized_tag=2, schemas=[schema]
        )

        retrieved = header.get_schema("Movie")
        assert retrieved is not None
        assert retrieved.name == "Movie"

    def test_get_nonexistent_schema(self) -> None:
        """Should return None for nonexistent schema."""
        header = HollowBlobHeader(origin_randomized_tag=1, destination_randomized_tag=2)

        assert header.get_schema("NonExistent") is None

    def test_create_header_with_tags(self) -> None:
        """Should create header with metadata tags."""
        header = HollowBlobHeader(
            origin_randomized_tag=1,
            destination_randomized_tag=2,
            header_tags={"env": "production", "version": "1.0"},
        )

        assert header.header_tags["env"] == "production"
        assert header.header_tags["version"] == "1.0"


class TestHeaderSerializationSimple:
    """Tests for simple header serialization without schemas."""

    def test_write_minimal_header(self) -> None:
        """Should write header with no schemas or tags."""
        header = HollowBlobHeader(
            origin_randomized_tag=123456789, destination_randomized_tag=987654321
        )

        stream = io.BytesIO()
        write_header(stream, header)
        result = stream.getvalue()

        # Should start with version (1030 = 0x00000406)
        assert result[0:4] == struct.pack(">I", 1030)
        # Should have minimum length (version + 2 tags + tag count + schema count + compat)
        assert len(result) > 20

    def test_roundtrip_minimal_header(self) -> None:
        """Minimal header should roundtrip correctly."""
        header = HollowBlobHeader(
            origin_randomized_tag=111111, destination_randomized_tag=222222
        )

        # Write
        stream = io.BytesIO()
        write_header(stream, header)

        # Read
        stream.seek(0)
        result = read_header(stream)

        # Verify
        assert result.version == header.version
        assert result.origin_randomized_tag == header.origin_randomized_tag
        assert result.destination_randomized_tag == header.destination_randomized_tag
        assert result.num_schemas() == 0
        assert len(result.header_tags) == 0

    def test_roundtrip_header_with_tags(self) -> None:
        """Header with tags should roundtrip correctly."""
        header = HollowBlobHeader(
            origin_randomized_tag=1000,
            destination_randomized_tag=2000,
            header_tags={"key1": "value1", "key2": "value2", "env": "test"},
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Verify tags
        assert result.header_tags == header.header_tags


class TestHeaderSerializationWithSchemas:
    """Tests for header serialization with schemas."""

    def test_roundtrip_header_with_single_schema(self) -> None:
        """Header with one schema should roundtrip."""
        schema = HollowObjectSchema(name="Movie")
        schema.add_field("title", FieldType.STRING)
        schema.add_field("year", FieldType.INT)

        header = HollowBlobHeader(
            origin_randomized_tag=100,
            destination_randomized_tag=200,
            schemas=[schema],
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Verify
        assert result.num_schemas() == 1
        assert result.has_schema("Movie")

        movie = result.get_schema("Movie")
        assert movie is not None
        assert movie.num_fields() == 2
        assert movie.get_field_by_name("title").field_type == FieldType.STRING
        assert movie.get_field_by_name("year").field_type == FieldType.INT

    def test_roundtrip_header_with_multiple_schemas(self) -> None:
        """Header with multiple schemas should roundtrip."""
        movie = HollowObjectSchema(name="Movie")
        movie.add_field("title", FieldType.STRING)
        movie.add_field("director", FieldType.REFERENCE, "Person")

        person = HollowObjectSchema(name="Person")
        person.add_field("name", FieldType.STRING)
        person.add_field("age", FieldType.INT)

        header = HollowBlobHeader(
            origin_randomized_tag=500,
            destination_randomized_tag=600,
            schemas=[movie, person],
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Verify
        assert result.num_schemas() == 2
        assert result.has_schema("Movie")
        assert result.has_schema("Person")

        # Check REFERENCE field
        movie_result = result.get_schema("Movie")
        assert movie_result is not None
        director_field = movie_result.get_field_by_name("director")
        assert director_field.field_type == FieldType.REFERENCE
        assert director_field.referenced_type == "Person"

    def test_roundtrip_header_with_schema_with_primary_key(self) -> None:
        """Header with schema that has primary key should roundtrip."""
        pk = PrimaryKey(schema_name="Movie", field_paths=["id"])
        schema = HollowObjectSchema(name="Movie", primary_key=pk)
        schema.add_field("id", FieldType.INT)
        schema.add_field("title", FieldType.STRING)

        header = HollowBlobHeader(
            origin_randomized_tag=10, destination_randomized_tag=20, schemas=[schema]
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Verify primary key preserved
        movie = result.get_schema("Movie")
        assert movie is not None
        assert movie.has_primary_key()
        assert movie.primary_key is not None
        assert movie.primary_key.field_paths == ["id"]

    def test_roundtrip_complete_header(self) -> None:
        """Complete header with schemas and tags should roundtrip."""
        schema = HollowObjectSchema(name="User")
        schema.add_field("id", FieldType.LONG)
        schema.add_field("email", FieldType.STRING)
        schema.add_field("active", FieldType.BOOLEAN)

        header = HollowBlobHeader(
            origin_randomized_tag=9999,
            destination_randomized_tag=8888,
            schemas=[schema],
            header_tags={"producer": "python-hollow", "timestamp": "2024-01-01"},
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Verify everything
        assert result.origin_randomized_tag == 9999
        assert result.destination_randomized_tag == 8888
        assert result.num_schemas() == 1
        assert result.header_tags["producer"] == "python-hollow"
        assert result.header_tags["timestamp"] == "2024-01-01"

        user = result.get_schema("User")
        assert user is not None
        assert user.num_fields() == 3


class TestHeaderValidation:
    """Tests for header validation and error handling."""

    def test_write_invalid_version(self) -> None:
        """Should reject invalid version."""
        header = HollowBlobHeader(
            version=9999,  # Wrong version
            origin_randomized_tag=1,
            destination_randomized_tag=2,
        )

        stream = io.BytesIO()
        with pytest.raises(ValueError, match="Invalid blob version"):
            write_header(stream, header)

    def test_read_invalid_version(self) -> None:
        """Should reject blob with wrong version."""
        stream = io.BytesIO()
        # Write wrong version
        import struct

        stream.write(struct.pack(">I", 9999))
        stream.write(b"\x00" * 100)  # Dummy data

        stream.seek(0)
        with pytest.raises(BlobException, match="Unsupported blob version"):
            read_header(stream)

    def test_read_unexpected_eof(self) -> None:
        """Should raise error on unexpected EOF."""
        stream = io.BytesIO(b"\x00\x00")  # Too short

        with pytest.raises(BlobException, match="Unexpected EOF"):
            read_header(stream)

    def test_large_randomized_tags(self) -> None:
        """Should handle large unsigned long values for tags."""
        # Use large unsigned long values
        origin = 0xFFFFFFFFFFFFFFFF
        dest = 0x8000000000000000

        header = HollowBlobHeader(
            origin_randomized_tag=origin, destination_randomized_tag=dest
        )

        # Write and read
        stream = io.BytesIO()
        write_header(stream, header)
        stream.seek(0)
        result = read_header(stream)

        # Tags should be preserved as unsigned
        assert result.origin_randomized_tag == origin
        assert result.destination_randomized_tag == dest


# Import struct for tests
import struct
