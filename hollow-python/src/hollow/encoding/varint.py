"""Variable-length integer encoding and decoding.

Variable-byte integer encoding uses 7 bits per byte for data, with the high bit
(0x80) indicating continuation. Smaller values use fewer bytes.

Reference: /hollow/src/main/java/com/netflix/hollow/core/memory/encoding/VarInt.java
"""

import io
from typing import BinaryIO

from ..core.constants import VARINT_NULL
from ..core.exceptions import EncodingException


def write_vnull(stream: BinaryIO) -> None:
    """Write a null VarInt value.

    Args:
        stream: Binary stream to write to
    """
    stream.write(bytes([VARINT_NULL]))


def is_vnull(stream: BinaryIO) -> bool:
    """Check if the next byte is a null VarInt marker without consuming it.

    Args:
        stream: Binary stream to peek from

    Returns:
        True if next byte is null marker (0x80)
    """
    pos = stream.tell()
    byte = stream.read(1)
    stream.seek(pos)

    return len(byte) > 0 and byte[0] == VARINT_NULL


def write_vint(stream: BinaryIO, value: int) -> None:
    """Encode and write a 32-bit integer using variable-length encoding.

    Args:
        stream: Binary stream to write to
        value: Integer value to encode (32-bit signed)

    Note:
        Negative values always use 5 bytes (maximum for 32-bit int).
        Positive values use 1-5 bytes depending on magnitude.
    """
    # Convert to unsigned 32-bit representation
    if value < 0:
        value = (value & 0xFFFFFFFF)

    # For negative values (now large unsigned), write all bytes
    if value > 0x0FFFFFFF:
        stream.write(bytes([0x80 | ((value >> 28) & 0xFF)]))
    if value > 0x1FFFFF:
        stream.write(bytes([0x80 | ((value >> 21) & 0x7F)]))
    if value > 0x3FFF:
        stream.write(bytes([0x80 | ((value >> 14) & 0x7F)]))
    if value > 0x7F:
        stream.write(bytes([0x80 | ((value >> 7) & 0x7F)]))

    # Last byte - no continuation bit
    stream.write(bytes([value & 0x7F]))


def read_vint(stream: BinaryIO) -> int:
    """Read and decode a variable-length 32-bit integer.

    Args:
        stream: Binary stream to read from

    Returns:
        Decoded integer value

    Raises:
        EncodingException: If null value encountered or unexpected EOF
    """
    byte_data = stream.read(1)
    if len(byte_data) == 0:
        raise EncodingException("Unexpected end of VarInt record")

    b = byte_data[0]

    if b == VARINT_NULL:
        raise EncodingException("Attempting to read null value as int")

    value = b & 0x7F
    while (b & 0x80) != 0:
        byte_data = stream.read(1)
        if len(byte_data) == 0:
            raise EncodingException("Unexpected end of VarInt record")

        b = byte_data[0]
        value <<= 7
        value |= b & 0x7F

    # Convert from unsigned to signed 32-bit
    if value & 0x80000000:
        value = value - 0x100000000

    return value


def write_vlong(stream: BinaryIO, value: int) -> None:
    """Encode and write a 64-bit integer using variable-length encoding.

    Args:
        stream: Binary stream to write to
        value: Long integer value to encode (64-bit signed)

    Note:
        Negative values always use 10 bytes (maximum for 64-bit long).
        Positive values use 1-9 bytes depending on magnitude.
    """
    # Convert to unsigned 64-bit representation
    is_negative = value < 0
    if is_negative:
        value = (value & 0xFFFFFFFFFFFFFFFF)

    # For negative values, write special negative marker first
    if is_negative:
        stream.write(bytes([0x81]))

    # Write variable-length bytes
    # Thresholds are based on 7-bit chunks: 2^(7*n) - 1
    if value > 0xFFFFFFFFFFFFFF:    # 2^56 - 1
        stream.write(bytes([0x80 | ((value >> 56) & 0x7F)]))
    if value > 0x1FFFFFFFFFFFF:     # 2^49 - 1
        stream.write(bytes([0x80 | ((value >> 49) & 0x7F)]))
    if value > 0x3FFFFFFFFFF:       # 2^42 - 1
        stream.write(bytes([0x80 | ((value >> 42) & 0x7F)]))
    if value > 0x7FFFFFFFF:         # 2^35 - 1
        stream.write(bytes([0x80 | ((value >> 35) & 0x7F)]))
    if value > 0xFFFFFFF:           # 2^28 - 1
        stream.write(bytes([0x80 | ((value >> 28) & 0x7F)]))
    if value > 0x1FFFFF:            # 2^21 - 1
        stream.write(bytes([0x80 | ((value >> 21) & 0x7F)]))
    if value > 0x3FFF:              # 2^14 - 1
        stream.write(bytes([0x80 | ((value >> 14) & 0x7F)]))
    if value > 0x7F:                # 2^7 - 1
        stream.write(bytes([0x80 | ((value >> 7) & 0x7F)]))

    # Last byte - no continuation bit
    stream.write(bytes([value & 0x7F]))


def read_vlong(stream: BinaryIO) -> int:
    """Read and decode a variable-length 64-bit integer.

    Args:
        stream: Binary stream to read from

    Returns:
        Decoded long integer value

    Raises:
        EncodingException: If null value encountered or unexpected EOF
    """
    byte_data = stream.read(1)
    if len(byte_data) == 0:
        raise EncodingException("Unexpected end of VarInt record")

    b = byte_data[0]

    if b == VARINT_NULL:
        raise EncodingException("Attempting to read null value as long")

    value = b & 0x7F
    while (b & 0x80) != 0:
        byte_data = stream.read(1)
        if len(byte_data) == 0:
            raise EncodingException("Unexpected end of VarInt record")

        b = byte_data[0]
        value <<= 7
        value |= b & 0x7F

    # Convert from unsigned to signed 64-bit
    if value & 0x8000000000000000:
        value = value - 0x10000000000000000

    return value


def size_of_vint(value: int) -> int:
    """Calculate the size in bytes of a VarInt encoded 32-bit integer.

    Args:
        value: Integer value

    Returns:
        Number of bytes required to encode the value
    """
    if value < 0:
        return 5
    if value < 0x80:
        return 1
    if value < 0x4000:
        return 2
    if value < 0x200000:
        return 3
    if value < 0x10000000:
        return 4
    return 5


def size_of_vlong(value: int) -> int:
    """Calculate the size in bytes of a VarInt encoded 64-bit integer.

    Args:
        value: Long integer value

    Returns:
        Number of bytes required to encode the value
    """
    if value < 0:
        return 10
    if value < 0x80:
        return 1
    if value < 0x4000:
        return 2
    if value < 0x200000:
        return 3
    if value < 0x10000000:
        return 4
    if value < 0x800000000:
        return 5
    if value < 0x40000000000:
        return 6
    if value < 0x2000000000000:
        return 7
    if value < 0x100000000000000:
        return 8
    return 9
