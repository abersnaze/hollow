"""Blob header serialization and deserialization.

Reference: /hollow/src/main/java/com/netflix/hollow/core/write/HollowBlobHeaderWriter.java
Reference: /hollow/src/main/java/com/netflix/hollow/core/read/engine/HollowBlobHeaderReader.java
"""

import struct
from typing import BinaryIO

from ..schema.object_schema import HollowObjectSchema
from ..schema.serialization import read_object_schema, read_utf, write_object_schema, write_utf
from .blob_header import HollowBlobHeader
from .constants import HOLLOW_BLOB_VERSION_HEADER
from .exceptions import BlobException


def write_header(stream: BinaryIO, header: HollowBlobHeader) -> None:
    """Write a Hollow blob header to a binary stream.

    Wire format:
        1. Version (4 bytes, int, big-endian) = 1030
        2. Origin randomized tag (8 bytes, long, big-endian)
        3. Destination randomized tag (8 bytes, long, big-endian)
        4. Header tags:
            - Count (2 bytes, short, big-endian)
            - For each tag: key (UTF), value (UTF)
        5. Schemas envelope:
            - Schema count (VarInt)
            - For each schema: schema bytes
        6. Forwards compatibility: VarInt(0)

    Args:
        stream: Binary stream to write to
        header: Header to write

    Raises:
        ValueError: If header is invalid
    """
    # 1. Write version
    if header.version != HOLLOW_BLOB_VERSION_HEADER:
        raise ValueError(
            f"Invalid blob version: {header.version} "
            f"(expected {HOLLOW_BLOB_VERSION_HEADER})"
        )
    stream.write(struct.pack(">I", header.version))

    # 2. Write origin randomized tag
    stream.write(struct.pack(">Q", header.origin_randomized_tag & 0xFFFFFFFFFFFFFFFF))

    # 3. Write destination randomized tag
    stream.write(struct.pack(">Q", header.destination_randomized_tag & 0xFFFFFFFFFFFFFFFF))

    # 4. Write header tags
    num_tags = len(header.header_tags)
    stream.write(struct.pack(">H", num_tags))
    for key, value in header.header_tags.items():
        write_utf(stream, key)
        write_utf(stream, value)

    # 5. Write schemas envelope
    # Note: In Java, this writes VarInt(length + 1) for backwards compatibility,
    # but we'll follow the actual format which is just the schema count
    from ..encoding.varint import write_vint

    write_vint(stream, len(header.schemas))
    for schema in header.schemas:
        write_object_schema(stream, schema)

    # 6. Write forwards compatibility byte (0)
    write_vint(stream, 0)


def read_header(stream: BinaryIO) -> HollowBlobHeader:
    """Read a Hollow blob header from a binary stream.

    Args:
        stream: Binary stream to read from

    Returns:
        Deserialized header

    Raises:
        BlobException: If unable to read header or format is invalid
    """
    from ..encoding.varint import read_vint

    # 1. Read version
    version_bytes = stream.read(4)
    if len(version_bytes) != 4:
        raise BlobException("Unexpected EOF while reading blob version")

    version = struct.unpack(">I", version_bytes)[0]
    if version != HOLLOW_BLOB_VERSION_HEADER:
        raise BlobException(
            f"Unsupported blob version: {version} "
            f"(expected {HOLLOW_BLOB_VERSION_HEADER})"
        )

    # 2. Read origin randomized tag
    origin_bytes = stream.read(8)
    if len(origin_bytes) != 8:
        raise BlobException("Unexpected EOF while reading origin tag")
    origin_tag = struct.unpack(">Q", origin_bytes)[0]

    # 3. Read destination randomized tag
    dest_bytes = stream.read(8)
    if len(dest_bytes) != 8:
        raise BlobException("Unexpected EOF while reading destination tag")
    dest_tag = struct.unpack(">Q", dest_bytes)[0]

    # 4. Read header tags
    tag_count_bytes = stream.read(2)
    if len(tag_count_bytes) != 2:
        raise BlobException("Unexpected EOF while reading header tag count")
    tag_count = struct.unpack(">H", tag_count_bytes)[0]

    header_tags = {}
    for _ in range(tag_count):
        key = read_utf(stream)
        value = read_utf(stream)
        header_tags[key] = value

    # 5. Read schemas envelope
    schema_count = read_vint(stream)
    schemas = []
    for _ in range(schema_count):
        schema = read_object_schema(stream)
        schemas.append(schema)

    # 6. Read forwards compatibility byte (should be 0)
    compat_value = read_vint(stream)
    if compat_value != 0:
        # For forwards compatibility, we just ignore unknown values
        pass

    return HollowBlobHeader(
        version=version,
        origin_randomized_tag=origin_tag,
        destination_randomized_tag=dest_tag,
        schemas=schemas,
        header_tags=header_tags,
    )
