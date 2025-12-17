"""Schema serialization and deserialization for wire format compatibility.

This module implements reading and writing Hollow schemas in the same binary format
as the Java implementation, ensuring wire compatibility.

Reference: /hollow/src/main/java/com/netflix/hollow/core/schema/HollowSchema.java
"""

import struct
from typing import BinaryIO

from ..core.exceptions import SchemaException
from ..encoding.varint import read_vint, write_vint
from .field_type import FieldType
from .object_schema import FieldDefinition, HollowObjectSchema, PrimaryKey

# Schema type IDs (must match Java implementation)
SCHEMA_TYPE_OBJECT = 0
SCHEMA_TYPE_OBJECT_WITH_PK = 6


def write_utf(stream: BinaryIO, s: str) -> None:
    """Write a string in Java DataOutputStream.writeUTF() format.

    Format:
        - 2 bytes: unsigned short length (number of bytes in UTF-8 encoding)
        - N bytes: UTF-8 encoded string

    Args:
        stream: Binary stream to write to
        s: String to write

    Raises:
        ValueError: If string is too long (> 65535 bytes when UTF-8 encoded)
    """
    utf8_bytes = s.encode("utf-8")
    length = len(utf8_bytes)

    if length > 65535:
        raise ValueError(f"String too long for writeUTF: {length} bytes (max 65535)")

    # Write length as unsigned short (2 bytes, big-endian)
    stream.write(struct.pack(">H", length))
    # Write UTF-8 bytes
    stream.write(utf8_bytes)


def read_utf(stream: BinaryIO) -> str:
    """Read a string in Java DataInputStream.readUTF() format.

    Format:
        - 2 bytes: unsigned short length (number of bytes)
        - N bytes: UTF-8 encoded string

    Args:
        stream: Binary stream to read from

    Returns:
        Decoded string

    Raises:
        SchemaException: If unable to read string
    """
    # Read length as unsigned short (2 bytes, big-endian)
    length_bytes = stream.read(2)
    if len(length_bytes) != 2:
        raise SchemaException("Unexpected EOF while reading UTF string length")

    length = struct.unpack(">H", length_bytes)[0]

    # Read UTF-8 bytes
    utf8_bytes = stream.read(length)
    if len(utf8_bytes) != length:
        raise SchemaException(f"Unexpected EOF while reading UTF string (expected {length} bytes)")

    try:
        return utf8_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SchemaException(f"Invalid UTF-8 encoding: {e}")


def write_object_schema(stream: BinaryIO, schema: HollowObjectSchema) -> None:
    """Write a Hollow OBJECT schema to a binary stream.

    Wire format:
        - 1 byte: type ID (0 for no PK, 6 for with PK)
        - UTF string: schema name
        - If has PK:
            - VarInt: number of key field paths
            - For each: UTF string field path
        - 2 bytes (short): number of fields
        - For each field:
            - UTF string: field name
            - UTF string: field type name
            - If REFERENCE: UTF string referenced type name

    Args:
        stream: Binary stream to write to
        schema: Schema to write

    Raises:
        ValueError: If schema is invalid
    """
    # Write type ID
    if schema.has_primary_key():
        stream.write(bytes([SCHEMA_TYPE_OBJECT_WITH_PK]))
    else:
        stream.write(bytes([SCHEMA_TYPE_OBJECT]))

    # Write schema name
    write_utf(stream, schema.name)

    # Write primary key if present
    if schema.primary_key:
        write_vint(stream, len(schema.primary_key.field_paths))
        for field_path in schema.primary_key.field_paths:
            write_utf(stream, field_path)

    # Write field count as short (2 bytes, big-endian)
    num_fields = schema.num_fields()
    stream.write(struct.pack(">H", num_fields))

    # Write each field
    for field in schema.fields:
        write_utf(stream, field.name)
        write_utf(stream, field.field_type.value)

        # Write referenced type for REFERENCE fields
        if field.field_type == FieldType.REFERENCE:
            if field.referenced_type is None:
                raise ValueError(
                    f"REFERENCE field '{field.name}' in schema '{schema.name}' "
                    "must have referenced_type"
                )
            write_utf(stream, field.referenced_type)


def read_object_schema(stream: BinaryIO) -> HollowObjectSchema:
    """Read a Hollow OBJECT schema from a binary stream.

    Args:
        stream: Binary stream to read from

    Returns:
        Deserialized schema

    Raises:
        SchemaException: If unable to read schema or format is invalid
    """
    # Read type ID
    type_id_bytes = stream.read(1)
    if len(type_id_bytes) != 1:
        raise SchemaException("Unexpected EOF while reading schema type ID")

    type_id = type_id_bytes[0]

    if type_id not in (SCHEMA_TYPE_OBJECT, SCHEMA_TYPE_OBJECT_WITH_PK):
        raise SchemaException(f"Invalid OBJECT schema type ID: {type_id}")

    has_pk = type_id == SCHEMA_TYPE_OBJECT_WITH_PK

    # Read schema name
    schema_name = read_utf(stream)

    # Read primary key if present
    primary_key = None
    if has_pk:
        num_key_fields = read_vint(stream)
        field_paths = []
        for _ in range(num_key_fields):
            field_paths.append(read_utf(stream))
        primary_key = PrimaryKey(schema_name=schema_name, field_paths=field_paths)

    # Read field count
    field_count_bytes = stream.read(2)
    if len(field_count_bytes) != 2:
        raise SchemaException("Unexpected EOF while reading field count")

    field_count = struct.unpack(">H", field_count_bytes)[0]

    # Read fields
    fields = []
    for _ in range(field_count):
        field_name = read_utf(stream)
        field_type_str = read_utf(stream)

        try:
            field_type = FieldType(field_type_str)
        except ValueError:
            raise SchemaException(f"Invalid field type: {field_type_str}")

        # Read referenced type for REFERENCE fields
        referenced_type = None
        if field_type == FieldType.REFERENCE:
            referenced_type = read_utf(stream)

        fields.append(
            FieldDefinition(name=field_name, field_type=field_type, referenced_type=referenced_type)
        )

    # Create and return schema
    return HollowObjectSchema(name=schema_name, fields=fields, primary_key=primary_key)
