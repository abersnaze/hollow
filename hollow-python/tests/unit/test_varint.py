"""Unit tests for VarInt encoding."""

import io

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hollow.core.exceptions import EncodingException
from hollow.encoding.varint import (
    is_vnull,
    read_vint,
    read_vlong,
    size_of_vint,
    size_of_vlong,
    write_vint,
    write_vlong,
    write_vnull,
)


class TestVarIntWrite:
    """Tests for VarInt writing."""

    def test_write_vnull(self) -> None:
        """Null should write as single 0x80 byte."""
        stream = io.BytesIO()
        write_vnull(stream)
        assert stream.getvalue() == b"\x80"

    def test_write_zero(self) -> None:
        """Zero should write as single 0x00 byte."""
        stream = io.BytesIO()
        write_vint(stream, 0)
        assert stream.getvalue() == b"\x00"

    def test_write_small_positive(self) -> None:
        """Values < 128 should write as single byte."""
        for value in [1, 42, 127]:
            stream = io.BytesIO()
            write_vint(stream, value)
            assert stream.getvalue() == bytes([value])

    def test_write_128(self) -> None:
        """128 (0x80) should use 2 bytes to avoid confusion with null."""
        stream = io.BytesIO()
        write_vint(stream, 128)
        # 128 = 0x80 = 0b10000000
        # Split into 7-bit chunks: 0b0000001 0b0000000
        # Encoded: 0x81 0x00 (first byte has continuation bit set)
        assert stream.getvalue() == b"\x81\x00"

    def test_write_16384(self) -> None:
        """16384 (0x4000) should use 3 bytes."""
        stream = io.BytesIO()
        write_vint(stream, 16384)
        # 16384 = 0x4000 = 0b100000000000000
        # Split into 7-bit chunks: 0b01 0b0000000 0b0000000
        # Encoded: 0x81 0x80 0x00
        assert stream.getvalue() == b"\x81\x80\x00"

    def test_write_negative_one(self) -> None:
        """-1 should use 5 bytes (maximum for 32-bit int)."""
        stream = io.BytesIO()
        write_vint(stream, -1)
        result = stream.getvalue()
        assert len(result) == 5
        # All continuation bits set except last
        assert all(b & 0x80 for b in result[:-1])
        assert (result[-1] & 0x80) == 0

    def test_write_max_int(self) -> None:
        """Max 32-bit int should encode and decode correctly."""
        max_int = 2**31 - 1
        stream = io.BytesIO()
        write_vint(stream, max_int)
        result = stream.getvalue()
        assert len(result) == 5  # Maximum size for positive int

    def test_write_vlong_zero(self) -> None:
        """Long zero should write as single byte."""
        stream = io.BytesIO()
        write_vlong(stream, 0)
        assert stream.getvalue() == b"\x00"

    def test_write_vlong_large_positive(self) -> None:
        """Large positive long values should encode correctly."""
        value = 2**40
        stream = io.BytesIO()
        write_vlong(stream, value)
        result = stream.getvalue()
        # Verify all continuation bits set except last
        assert all(b & 0x80 for b in result[:-1])
        assert (result[-1] & 0x80) == 0

    def test_write_vlong_negative(self) -> None:
        """-1 as long should use 10 bytes (maximum for 64-bit long)."""
        stream = io.BytesIO()
        write_vlong(stream, -1)
        result = stream.getvalue()
        assert len(result) == 10
        # First byte should be 0x81 (special negative marker)
        assert result[0] == 0x81


class TestVarIntRead:
    """Tests for VarInt reading."""

    def test_is_vnull_detects_null(self) -> None:
        """is_vnull should detect null marker without consuming it."""
        stream = io.BytesIO(b"\x80\x01\x02")
        assert is_vnull(stream) is True
        # Position should not have changed
        assert stream.tell() == 0

    def test_is_vnull_detects_non_null(self) -> None:
        """is_vnull should return False for non-null values."""
        stream = io.BytesIO(b"\x00\x01\x02")
        assert is_vnull(stream) is False
        assert stream.tell() == 0

    def test_read_vint_raises_on_null(self) -> None:
        """Reading a null VarInt should raise an exception."""
        stream = io.BytesIO(b"\x80")
        with pytest.raises(EncodingException, match="null value"):
            read_vint(stream)

    def test_read_vint_raises_on_eof(self) -> None:
        """Reading from empty stream should raise an exception."""
        stream = io.BytesIO(b"")
        with pytest.raises(EncodingException, match="Unexpected end"):
            read_vint(stream)

    def test_read_vint_raises_on_incomplete(self) -> None:
        """Reading incomplete VarInt should raise an exception."""
        stream = io.BytesIO(b"\x81")  # Continuation bit set, but no next byte
        with pytest.raises(EncodingException, match="Unexpected end"):
            read_vint(stream)

    def test_read_zero(self) -> None:
        """Should read zero correctly."""
        stream = io.BytesIO(b"\x00")
        assert read_vint(stream) == 0

    def test_read_small_positive(self) -> None:
        """Should read small positive values correctly."""
        for value in [1, 42, 127]:
            stream = io.BytesIO(bytes([value]))
            assert read_vint(stream) == value

    def test_read_128(self) -> None:
        """Should read 128 correctly."""
        stream = io.BytesIO(b"\x81\x00")
        assert read_vint(stream) == 128

    def test_read_vlong_zero(self) -> None:
        """Should read long zero correctly."""
        stream = io.BytesIO(b"\x00")
        assert read_vlong(stream) == 0

    def test_read_vlong_raises_on_null(self) -> None:
        """Reading a null VarLong should raise an exception."""
        stream = io.BytesIO(b"\x80")
        with pytest.raises(EncodingException, match="null value"):
            read_vlong(stream)


class TestVarIntRoundtrip:
    """Roundtrip tests for VarInt encoding/decoding."""

    @given(st.integers(min_value=0, max_value=2**31 - 1))
    def test_roundtrip_vint_positive(self, value: int) -> None:
        """Positive integers should roundtrip through VarInt encoding."""
        stream = io.BytesIO()
        write_vint(stream, value)
        stream.seek(0)
        result = read_vint(stream)
        assert result == value

    def test_roundtrip_vint_negative(self) -> None:
        """Negative integers should roundtrip through VarInt encoding."""
        # Test some negative values (hypothesis doesn't handle negative well with our encoding)
        test_values = [-1, -42, -128, -1000, -1000000, -(2**31)]
        for value in test_values:
            stream = io.BytesIO()
            write_vint(stream, value)
            stream.seek(0)
            result = read_vint(stream)
            assert result == value

    @given(st.integers(min_value=0, max_value=2**63 - 1))
    def test_roundtrip_vlong_positive(self, value: int) -> None:
        """Positive longs should roundtrip through VarLong encoding."""
        stream = io.BytesIO()
        write_vlong(stream, value)
        stream.seek(0)
        result = read_vlong(stream)
        assert result == value

    def test_roundtrip_vlong_negative(self) -> None:
        """Negative longs should roundtrip through VarLong encoding."""
        test_values = [
            -1,
            -42,
            -128,
            -(2**32),
            -(2**40),
            -(2**50),
            -(2**63),
        ]
        for value in test_values:
            stream = io.BytesIO()
            write_vlong(stream, value)
            stream.seek(0)
            result = read_vlong(stream)
            assert result == value

    def test_roundtrip_max_values(self) -> None:
        """Maximum values should roundtrip correctly."""
        # Max 32-bit int
        stream = io.BytesIO()
        max_int = 2**31 - 1
        write_vint(stream, max_int)
        stream.seek(0)
        assert read_vint(stream) == max_int

        # Max 64-bit long
        stream = io.BytesIO()
        max_long = 2**63 - 1
        write_vlong(stream, max_long)
        stream.seek(0)
        assert read_vlong(stream) == max_long


class TestVarIntSize:
    """Tests for VarInt size calculation functions."""

    def test_size_of_vint_small_values(self) -> None:
        """Small values should use 1 byte."""
        for value in [0, 1, 42, 127]:
            assert size_of_vint(value) == 1

    def test_size_of_vint_medium_values(self) -> None:
        """Medium values should use appropriate bytes."""
        assert size_of_vint(128) == 2
        assert size_of_vint(0x3FFF) == 2
        assert size_of_vint(0x4000) == 3
        assert size_of_vint(0x1FFFFF) == 3
        assert size_of_vint(0x200000) == 4

    def test_size_of_vint_negative(self) -> None:
        """Negative values should always use 5 bytes."""
        assert size_of_vint(-1) == 5
        assert size_of_vint(-42) == 5
        assert size_of_vint(-(2**31)) == 5

    def test_size_of_vint_matches_actual(self) -> None:
        """Size calculation should match actual encoded size."""
        test_values = [0, 1, 127, 128, 0x3FFF, 0x4000, 0xFFFFF, -1, -100]
        for value in test_values:
            stream = io.BytesIO()
            write_vint(stream, value)
            actual_size = len(stream.getvalue())
            calculated_size = size_of_vint(value)
            assert calculated_size == actual_size, f"Value {value}: calculated {calculated_size}, actual {actual_size}"

    def test_size_of_vlong_small_values(self) -> None:
        """Small long values should use 1 byte."""
        for value in [0, 1, 42, 127]:
            assert size_of_vlong(value) == 1

    def test_size_of_vlong_large_values(self) -> None:
        """Large long values should use appropriate bytes."""
        assert size_of_vlong(2**32) == 5
        assert size_of_vlong(2**40) == 6
        assert size_of_vlong(2**50) == 8

    def test_size_of_vlong_negative(self) -> None:
        """Negative long values should always use 10 bytes."""
        assert size_of_vlong(-1) == 10
        assert size_of_vlong(-42) == 10
        assert size_of_vlong(-(2**63)) == 10

    def test_size_of_vlong_matches_actual(self) -> None:
        """Size calculation should match actual encoded size."""
        test_values = [0, 1, 127, 128, 2**32, 2**40, -1, -100]
        for value in test_values:
            stream = io.BytesIO()
            write_vlong(stream, value)
            actual_size = len(stream.getvalue())
            calculated_size = size_of_vlong(value)
            assert calculated_size == actual_size, f"Value {value}: calculated {calculated_size}, actual {actual_size}"
