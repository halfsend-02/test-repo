"""Tests for the UTF-8 aware chunked file writer.

Covers the buffer-boundary splitting fix for issue #2588: files larger
than 64KB containing multibyte UTF-8 characters must save and reload
without corruption or crash.
"""

import os
import tempfile

import pytest

from src.file_writer import (
    BUFFER_SIZE,
    _find_utf8_safe_boundary,
    load_file,
    save_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _roundtrip(content: str, buffer_size: int = BUFFER_SIZE) -> str:
    """Save *content* via save_file, reload it, and return the result."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path, buffer_size=buffer_size)
        return load_file(path)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# _find_utf8_safe_boundary unit tests
# ---------------------------------------------------------------------------

class TestFindUtf8SafeBoundary:
    """Verify that the boundary finder never splits a multibyte character."""

    def test_ascii_boundary(self):
        data = b"Hello, world!"
        assert _find_utf8_safe_boundary(data, 5) == 5

    def test_limit_beyond_data(self):
        data = b"abc"
        assert _find_utf8_safe_boundary(data, 100) == 3

    def test_two_byte_char_not_split(self):
        # U+00E9 (é) = 0xC3 0xA9
        data = "aaé".encode("utf-8")  # b'aa\xc3\xa9'
        # Splitting at offset 3 would land on continuation byte 0xA9.
        assert _find_utf8_safe_boundary(data, 3) == 2

    def test_three_byte_char_not_split(self):
        # U+4E16 (世) = 0xE4 0xB8 0x96
        data = "a世".encode("utf-8")  # b'a\xe4\xb8\x96'
        # offset 2 is a continuation byte
        assert _find_utf8_safe_boundary(data, 2) == 1
        # offset 3 is also a continuation byte
        assert _find_utf8_safe_boundary(data, 3) == 1

    def test_four_byte_char_not_split(self):
        # U+1F600 (😀) = 0xF0 0x9F 0x98 0x80
        data = "a😀".encode("utf-8")  # b'a\xf0\x9f\x98\x80'
        assert _find_utf8_safe_boundary(data, 2) == 1
        assert _find_utf8_safe_boundary(data, 3) == 1
        assert _find_utf8_safe_boundary(data, 4) == 1

    def test_boundary_on_char_start_is_safe(self):
        # U+1F600 (😀) followed by ASCII
        data = "😀a".encode("utf-8")  # b'\xf0\x9f\x98\x80a'
        # offset 4 is the ASCII 'a' — a valid boundary
        assert _find_utf8_safe_boundary(data, 4) == 4


# ---------------------------------------------------------------------------
# save_file / load_file integration tests
# ---------------------------------------------------------------------------

class TestSaveFileRoundtrip:
    """End-to-end tests: save, reload, and compare."""

    def test_ascii_small_file(self):
        content = "Hello, world!\n" * 100
        assert _roundtrip(content) == content

    def test_ascii_large_file(self):
        content = "A" * (BUFFER_SIZE + 1000)
        assert _roundtrip(content) == content

    def test_multibyte_small_file(self):
        content = "café résumé naïve 日本語 🎉🎊✨"
        assert _roundtrip(content) == content

    def test_multibyte_over_64kb(self):
        """Core regression test for #2588.

        Create >64KB of text containing 4-byte emoji characters so that
        a multibyte character is very likely to straddle the 64KB boundary.
        """
        emoji = "😀"  # 4 bytes in UTF-8
        # 70KB / 4 bytes per emoji ≈ 17920 emoji
        count = (70 * 1024) // 4
        content = emoji * count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        assert _roundtrip(content) == content

    def test_boundary_spanning_two_byte_char(self):
        """Place a 2-byte character exactly at the 64KB boundary."""
        # Fill up to byte 65535 with ASCII, then place a 2-byte char.
        prefix = "A" * (BUFFER_SIZE - 1)
        suffix = "é" + "B" * 100  # é is 2 bytes
        content = prefix + suffix
        assert _roundtrip(content) == content

    def test_boundary_spanning_three_byte_char(self):
        """Place a 3-byte CJK character at the 64KB boundary."""
        prefix = "A" * (BUFFER_SIZE - 1)
        suffix = "世" + "B" * 100  # 世 is 3 bytes
        content = prefix + suffix
        assert _roundtrip(content) == content

    def test_boundary_spanning_four_byte_char(self):
        """Place a 4-byte emoji at the 64KB boundary."""
        prefix = "A" * (BUFFER_SIZE - 1)
        suffix = "😀" + "B" * 100  # 😀 is 4 bytes
        content = prefix + suffix
        assert _roundtrip(content) == content

    def test_exactly_64kb_multibyte(self):
        """File of exactly 64KB made entirely of multibyte characters."""
        char = "日"  # 3 bytes
        count = BUFFER_SIZE // 3
        content = char * count
        assert _roundtrip(content) == content

    def test_small_buffer_many_chunks(self):
        """Use a tiny buffer to force many chunk boundaries."""
        content = "Hello 🌍 World 🌎 Foo 🌏 Bar"
        result = _roundtrip(content, buffer_size=8)
        assert result == content

    def test_empty_file(self):
        assert _roundtrip("") == ""

    def test_single_multibyte_char(self):
        assert _roundtrip("😀") == "😀"

    def test_mixed_content_large(self):
        """Mix of ASCII, 2-byte, 3-byte, and 4-byte chars over 64KB."""
        block = "Hello café 世界 😀 "  # mixed widths
        # Repeat until >64KB
        count = (BUFFER_SIZE * 2) // len(block.encode("utf-8")) + 1
        content = block * count
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        assert _roundtrip(content) == content
