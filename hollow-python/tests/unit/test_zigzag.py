"""Unit tests for ZigZag encoding."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hollow.encoding.zigzag import decode_int, decode_long, encode_int, encode_long


class TestZigZagInt:
    """Tests for 32-bit integer ZigZag encoding."""

    def test_encode_zero(self) -> None:
        """Zero should encode to zero."""
        assert encode_int(0) == 0

    def test_encode_negative_one(self) -> None:
        """-1 should encode to 1."""
        assert encode_int(-1) == 1

    def test_encode_positive_one(self) -> None:
        """1 should encode to 2."""
        assert encode_int(1) == 2

    def test_encode_negative_two(self) -> None:
        """-2 should encode to 3."""
        assert encode_int(-2) == 3

    def test_encode_positive_two(self) -> None:
        """2 should encode to 4."""
        assert encode_int(2) == 4

    def test_encode_max_int(self) -> None:
        """Max int (2^31 - 1) should encode correctly."""
        max_int = 2**31 - 1
        encoded = encode_int(max_int)
        assert encoded == 0xFFFFFFFE

    def test_encode_min_int(self) -> None:
        """Min int (-2^31) should encode correctly."""
        min_int = -(2**31)
        encoded = encode_int(min_int)
        assert encoded == 0xFFFFFFFF

    def test_decode_zero(self) -> None:
        """Zero should decode to zero."""
        assert decode_int(0) == 0

    def test_decode_one(self) -> None:
        """1 should decode to -1."""
        assert decode_int(1) == -1

    def test_decode_two(self) -> None:
        """2 should decode to 1."""
        assert decode_int(2) == 1

    @given(st.integers(min_value=-(2**31), max_value=2**31 - 1))
    def test_roundtrip_int(self, value: int) -> None:
        """Any 32-bit signed integer should roundtrip through encoding."""
        encoded = encode_int(value)
        decoded = decode_int(encoded)
        assert decoded == value

    def test_small_positive_values(self) -> None:
        """Small positive values should encode to even numbers."""
        for i in range(1, 100):
            encoded = encode_int(i)
            assert encoded == i * 2
            assert decode_int(encoded) == i

    def test_small_negative_values(self) -> None:
        """Small negative values should encode to odd numbers."""
        for i in range(-100, 0):
            encoded = encode_int(i)
            assert encoded == (-i) * 2 - 1
            assert decode_int(encoded) == i


class TestZigZagLong:
    """Tests for 64-bit long integer ZigZag encoding."""

    def test_encode_zero(self) -> None:
        """Zero should encode to zero."""
        assert encode_long(0) == 0

    def test_encode_negative_one(self) -> None:
        """-1 should encode to 1."""
        assert encode_long(-1) == 1

    def test_encode_positive_one(self) -> None:
        """1 should encode to 2."""
        assert encode_long(1) == 2

    def test_encode_max_long(self) -> None:
        """Max long (2^63 - 1) should encode correctly."""
        max_long = 2**63 - 1
        encoded = encode_long(max_long)
        assert encoded == 0xFFFFFFFFFFFFFFFE

    def test_encode_min_long(self) -> None:
        """Min long (-2^63) should encode correctly."""
        min_long = -(2**63)
        encoded = encode_long(min_long)
        assert encoded == 0xFFFFFFFFFFFFFFFF

    def test_decode_zero(self) -> None:
        """Zero should decode to zero."""
        assert decode_long(0) == 0

    def test_decode_one(self) -> None:
        """1 should decode to -1."""
        assert decode_long(1) == -1

    def test_decode_two(self) -> None:
        """2 should decode to 1."""
        assert decode_long(2) == 1

    @given(st.integers(min_value=-(2**63), max_value=2**63 - 1))
    def test_roundtrip_long(self, value: int) -> None:
        """Any 64-bit signed integer should roundtrip through encoding."""
        encoded = encode_long(value)
        decoded = decode_long(encoded)
        assert decoded == value

    def test_large_positive_values(self) -> None:
        """Large positive values should encode correctly."""
        test_values = [
            2**32,
            2**32 + 1,
            2**40,
            2**50,
            2**62,
        ]
        for value in test_values:
            encoded = encode_long(value)
            decoded = decode_long(encoded)
            assert decoded == value

    def test_large_negative_values(self) -> None:
        """Large negative values should encode correctly."""
        test_values = [
            -(2**32),
            -(2**32 + 1),
            -(2**40),
            -(2**50),
            -(2**62),
        ]
        for value in test_values:
            encoded = encode_long(value)
            decoded = decode_long(encoded)
            assert decoded == value
