"""ZigZag encoding for signed integers.

ZigZag encoding maps signed integers to unsigned integers so that numbers with
a small absolute value have a small varint encoded value. This is used for
INT and LONG field types in Hollow.

Reference: /hollow/src/main/java/com/netflix/hollow/core/memory/encoding/ZigZag.java
"""


def encode_int(value: int) -> int:
    """Encode a signed 32-bit integer using ZigZag encoding.

    Args:
        value: Signed integer to encode

    Returns:
        Unsigned integer encoded value

    Examples:
        0 -> 0
        -1 -> 1
        1 -> 2
        -2 -> 3
    """
    # Ensure value is in 32-bit signed range
    value = value & 0xFFFFFFFF
    if value & 0x80000000:  # If sign bit is set, treat as negative
        value = value - 0x100000000

    return ((value << 1) ^ (value >> 31)) & 0xFFFFFFFF


def decode_int(value: int) -> int:
    """Decode a ZigZag encoded 32-bit integer.

    Args:
        value: Unsigned integer to decode

    Returns:
        Decoded signed integer

    Note:
        Java: (i >>> 1) ^ ((i << 31) >> 31)
        The ((i << 31) >> 31) creates a sign extension mask based on bit 0.
    """
    value = value & 0xFFFFFFFF
    # Extract bit 0 and create sign extension mask: -1 if bit 0 is set, else 0
    sign_mask = -(value & 1)
    result = (value >> 1) ^ sign_mask

    # Result is now signed - ensure it's in 32-bit signed range
    result = result & 0xFFFFFFFF
    if result & 0x80000000:
        result = result - 0x100000000

    return result


def encode_long(value: int) -> int:
    """Encode a signed 64-bit integer using ZigZag encoding.

    Args:
        value: Signed long integer to encode

    Returns:
        Unsigned long integer encoded value
    """
    # Ensure value is in 64-bit signed range
    value = value & 0xFFFFFFFFFFFFFFFF
    if value & 0x8000000000000000:  # If sign bit is set, treat as negative
        value = value - 0x10000000000000000

    return ((value << 1) ^ (value >> 63)) & 0xFFFFFFFFFFFFFFFF


def decode_long(value: int) -> int:
    """Decode a ZigZag encoded 64-bit integer.

    Args:
        value: Unsigned long integer to decode

    Returns:
        Decoded signed long integer

    Note:
        Java: (l >>> 1) ^ ((l << 63) >> 63)
        The ((l << 63) >> 63) creates a sign extension mask based on bit 0.
    """
    value = value & 0xFFFFFFFFFFFFFFFF
    # Extract bit 0 and create sign extension mask: -1 if bit 0 is set, else 0
    sign_mask = -(value & 1)
    result = (value >> 1) ^ sign_mask

    # Result is now signed - ensure it's in 64-bit signed range
    result = result & 0xFFFFFFFFFFFFFFFF
    if result & 0x8000000000000000:
        result = result - 0x10000000000000000

    return result
