"""Tests for file saving with multibyte UTF-8 content.

These tests verify the fix for the segmentation fault that occurred
when saving files larger than 64KB containing multibyte UTF-8
characters (issue #2371). The root cause was buffer allocation based
on character count instead of byte length.
"""

import os
import tempfile

import pytest

from src.file_saver import (
    WRITE_BUFFER_SIZE,
    _byte_length,
    _encode_content,
    read_file,
    save_file,
)


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestByteLength:
    """Tests for _byte_length helper."""

    def test_ascii_text(self):
        assert _byte_length("hello") == 5

    def test_emoji_characters(self):
        # Each emoji is 4 bytes in UTF-8.
        assert _byte_length("\U0001f600") == 4

    def test_cjk_characters(self):
        # CJK characters are 3 bytes in UTF-8.
        assert _byte_length("世") == 3

    def test_mixed_content(self):
        text = "hello \U0001f600 世"
        # 5 (hello) + 1 (space) + 4 (emoji) + 1 (space) + 3 (CJK) = 14
        assert _byte_length(text) == 14


class TestEncodeContent:
    """Tests for _encode_content helper."""

    def test_string_input(self):
        result = _encode_content("hello")
        assert result == b"hello"

    def test_bytes_passthrough(self):
        data = b"\xff\xfe"
        result = _encode_content(data)
        assert result is data

    def test_multibyte_encoding(self):
        result = _encode_content("\U0001f600")
        assert result == "\U0001f600".encode("utf-8")
        assert len(result) == 4


class TestSaveFileLargeMultibyte:
    """Tests for saving large files with multibyte UTF-8 content.

    These are the core regression tests for issue #2371.
    """

    def test_save_large_emoji_file(self, tmp_dir):
        """Save ~70KB of emoji characters without crash."""
        # Each emoji is 4 bytes. 18000 emojis = 72000 bytes > 64KB.
        content = "\U0001f600" * 18000
        assert _byte_length(content) > WRITE_BUFFER_SIZE

        filepath = os.path.join(tmp_dir, "emoji.txt")
        save_file(filepath, content)

        result = read_file(filepath)
        assert result == content

    def test_save_exactly_64kb_multibyte(self, tmp_dir):
        """Save exactly 64KB of multibyte characters."""
        # 3 bytes per CJK char. 21846 chars ≈ 65538 bytes (just over 64KB).
        count = WRITE_BUFFER_SIZE // 3 + 1
        content = "世" * count
        byte_len = _byte_length(content)
        assert byte_len > WRITE_BUFFER_SIZE

        filepath = os.path.join(tmp_dir, "cjk.txt")
        save_file(filepath, content)

        result = read_file(filepath)
        assert result == content

    def test_save_mixed_ascii_multibyte_over_64kb(self, tmp_dir):
        """Save >64KB of mixed ASCII and multibyte characters."""
        # Build content that's over 64KB in bytes.
        ascii_part = "a" * 32768  # 32KB ASCII
        emoji_part = "\U0001f600" * 8500  # 34000 bytes of emoji
        content = ascii_part + emoji_part
        assert _byte_length(content) > WRITE_BUFFER_SIZE

        filepath = os.path.join(tmp_dir, "mixed.txt")
        save_file(filepath, content)

        result = read_file(filepath)
        assert result == content

    def test_save_ascii_over_64kb(self, tmp_dir):
        """Control case: ASCII-only >64KB should also work."""
        content = "x" * (WRITE_BUFFER_SIZE + 1024)
        filepath = os.path.join(tmp_dir, "ascii.txt")
        save_file(filepath, content)

        result = read_file(filepath)
        assert result == content


class TestSaveFileBasic:
    """Basic save/read functionality tests."""

    def test_save_and_read_small_file(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "small.txt")
        save_file(filepath, "hello world")
        assert read_file(filepath) == "hello world"

    def test_save_empty_file(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "empty.txt")
        save_file(filepath, "")
        assert read_file(filepath) == ""

    def test_save_bytes_content(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "bytes.txt")
        save_file(filepath, b"raw bytes")
        assert read_file(filepath) == "raw bytes"

    def test_save_creates_parent_dirs(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "sub", "dir", "file.txt")
        save_file(filepath, "nested")
        assert read_file(filepath) == "nested"

    def test_save_overwrites_existing(self, tmp_dir):
        filepath = os.path.join(tmp_dir, "overwrite.txt")
        save_file(filepath, "first")
        save_file(filepath, "second")
        assert read_file(filepath) == "second"

    def test_read_nonexistent_raises(self, tmp_dir):
        with pytest.raises(FileNotFoundError):
            read_file(os.path.join(tmp_dir, "nope.txt"))
