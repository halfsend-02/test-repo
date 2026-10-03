"""Tests for file_handler module.

Covers the UTF-8 multibyte buffer overflow fix (issue #2595):
- ASCII-only files >64KB save and round-trip correctly.
- Files with emoji/CJK characters >64KB save and round-trip correctly.
- Files at exactly 64KB where trailing multibyte characters push byte
  count past 65536 save and round-trip correctly.
"""

import os
import tempfile

import pytest

from src.file_handler import DEFAULT_BUFFER_SIZE, read_file, save_file


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


class TestSaveFileASCII:
    """Verify that ASCII-only files larger than 64KB save correctly."""

    def test_ascii_file_over_64kb(self, tmp_dir):
        # Create ASCII content larger than 64KB
        content = "A" * (DEFAULT_BUFFER_SIZE + 1024)
        filepath = os.path.join(str(tmp_dir), "ascii_large.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content
        assert len(result) == len(content)

    def test_ascii_file_exactly_64kb(self, tmp_dir):
        content = "B" * DEFAULT_BUFFER_SIZE
        filepath = os.path.join(str(tmp_dir), "ascii_exact.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content


class TestSaveFileUTF8Multibyte:
    """Verify that files with multibyte UTF-8 characters save correctly."""

    def test_emoji_file_over_64kb(self, tmp_dir):
        # Each emoji is 4 bytes in UTF-8; fill past 64KB
        emoji_count = (DEFAULT_BUFFER_SIZE // 4) + 256
        content = "\U0001f600" * emoji_count  # 😀
        filepath = os.path.join(str(tmp_dir), "emoji_large.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content
        assert len(result.encode("utf-8")) > DEFAULT_BUFFER_SIZE

    def test_cjk_file_over_64kb(self, tmp_dir):
        # CJK characters are 3 bytes in UTF-8
        char_count = (DEFAULT_BUFFER_SIZE // 3) + 256
        content = "世" * char_count  # 世
        filepath = os.path.join(str(tmp_dir), "cjk_large.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content
        assert len(result.encode("utf-8")) > DEFAULT_BUFFER_SIZE

    def test_mixed_content_over_64kb(self, tmp_dir):
        # Mix ASCII, 2-byte, 3-byte, and 4-byte UTF-8 characters
        block = "Hello éè 世界 \U0001f600\U0001f389 "
        repeat_count = (DEFAULT_BUFFER_SIZE // len(block.encode("utf-8"))) + 10
        content = block * repeat_count
        filepath = os.path.join(str(tmp_dir), "mixed_large.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content
        assert len(result.encode("utf-8")) > DEFAULT_BUFFER_SIZE


class TestSaveFileBoundary:
    """Verify the exact 64KB boundary with trailing multibyte chars."""

    def test_boundary_trailing_multibyte(self, tmp_dir):
        # Create content where character count fits in 64KB but byte
        # count exceeds it due to trailing multibyte characters.
        # Fill with ASCII up to near the boundary, then add emoji.
        ascii_prefix = "X" * (DEFAULT_BUFFER_SIZE - 4)
        # Add emoji that pushes byte count past 65536
        trailing_emoji = "\U0001f600" * 2  # 8 bytes of emoji
        content = ascii_prefix + trailing_emoji
        filepath = os.path.join(str(tmp_dir), "boundary.txt")

        byte_len = len(content.encode("utf-8"))
        assert byte_len > DEFAULT_BUFFER_SIZE, (
            f"Test setup: byte length {byte_len} should exceed "
            f"{DEFAULT_BUFFER_SIZE}"
        )

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_boundary_exact_buffer_multibyte(self, tmp_dir):
        # Content whose byte length is exactly DEFAULT_BUFFER_SIZE,
        # but character count is less (due to multibyte chars).
        # 3-byte CJK char: we need DEFAULT_BUFFER_SIZE / 3 chars
        # to fill exactly (assuming divisible).
        chars_needed = DEFAULT_BUFFER_SIZE // 3
        remainder = DEFAULT_BUFFER_SIZE - (chars_needed * 3)
        content = "世" * chars_needed + "A" * remainder
        filepath = os.path.join(str(tmp_dir), "exact_boundary.txt")

        assert len(content.encode("utf-8")) == DEFAULT_BUFFER_SIZE

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content


class TestSaveFileEdgeCases:
    """Additional edge cases for robustness."""

    def test_empty_file(self, tmp_dir):
        filepath = os.path.join(str(tmp_dir), "empty.txt")

        save_file("", filepath)
        result = read_file(filepath)

        assert result == ""

    def test_small_file(self, tmp_dir):
        content = "Hello, world! \U0001f30d"
        filepath = os.path.join(str(tmp_dir), "small.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_overwrite_existing_file(self, tmp_dir):
        filepath = os.path.join(str(tmp_dir), "overwrite.txt")

        save_file("original content", filepath)
        save_file("new content \U0001f680", filepath)
        result = read_file(filepath)

        assert result == "new content \U0001f680"
