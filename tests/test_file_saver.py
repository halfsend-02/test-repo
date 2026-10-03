"""Tests for the file saver module.

Verifies correct handling of UTF-8 multibyte characters near and above
the 64KB buffer boundary, addressing the segfault reported in issue #2584.
"""

import os
import tempfile

import pytest

from src.file_saver import read_file, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_emoji_text(target_bytes):
    """Generate a string of emoji characters targeting a specific byte size.

    Each emoji (e.g., U+1F600) encodes to 4 bytes in UTF-8.
    """
    emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
    count = target_bytes // 4
    return emoji * count


def _make_cjk_text(target_bytes):
    """Generate a string of CJK characters targeting a specific byte size.

    Each CJK character (e.g., U+4E16 '世') encodes to 3 bytes in UTF-8.
    """
    char = "世"  # 世 — 3 bytes in UTF-8
    count = target_bytes // 3
    return char * count


def _make_mixed_text(target_bytes):
    """Generate mixed ASCII + CJK text targeting a specific byte size."""
    # Alternate between ASCII (1 byte) and CJK (3 bytes) = 4 bytes per pair
    pair = "A世"  # 'A世' — 4 bytes per pair
    count = target_bytes // 4
    return pair * count


class TestSaveFileUTF8:
    """Test saving files with multibyte UTF-8 content near the 64KB boundary."""

    def test_save_emoji_under_64kb(self, tmp_dir):
        """63KB of emoji text should save and read back correctly."""
        target = 63 * 1024
        content = _make_emoji_text(target)
        filepath = os.path.join(tmp_dir, "emoji_under.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_save_emoji_over_64kb(self, tmp_dir):
        """65KB of emoji text should save and read back correctly."""
        target = 65 * 1024
        content = _make_emoji_text(target)
        filepath = os.path.join(tmp_dir, "emoji_over.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_save_ascii_over_64kb(self, tmp_dir):
        """65KB of pure ASCII should save and read back correctly."""
        content = "A" * (65 * 1024)
        filepath = os.path.join(tmp_dir, "ascii_over.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_save_mixed_128kb(self, tmp_dir):
        """128KB of mixed ASCII + CJK should save and read back correctly."""
        target = 128 * 1024
        content = _make_mixed_text(target)
        filepath = os.path.join(tmp_dir, "mixed_128k.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_save_cjk_over_64kb(self, tmp_dir):
        """65KB of CJK characters should save and read back correctly."""
        target = 65 * 1024
        content = _make_cjk_text(target)
        filepath = os.path.join(tmp_dir, "cjk_over.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content

    def test_file_integrity_large_emoji(self, tmp_dir):
        """Verify byte-level integrity of a large emoji file."""
        target = 70 * 1024
        content = _make_emoji_text(target)
        filepath = os.path.join(tmp_dir, "integrity.txt")

        save_file(content, filepath)

        with open(filepath, "rb") as f:
            raw = f.read()

        assert raw == content.encode("utf-8")

    def test_empty_file(self, tmp_dir):
        """Empty content should produce an empty file."""
        filepath = os.path.join(tmp_dir, "empty.txt")

        save_file("", filepath)
        result = read_file(filepath)

        assert result == ""

    def test_save_exactly_64kb_emoji(self, tmp_dir):
        """Exactly 64KB of emoji text (boundary case) should save correctly."""
        target = 64 * 1024
        content = _make_emoji_text(target)
        filepath = os.path.join(tmp_dir, "exact_64k.txt")

        save_file(content, filepath)
        result = read_file(filepath)

        assert result == content
