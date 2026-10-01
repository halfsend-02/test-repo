"""Tests for the buffered file saver with UTF-8 boundary handling.

Covers the scenarios from issue #2495: saving files at and around the
64 KB boundary with multibyte UTF-8 content must not crash or corrupt
data.
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, _find_safe_split, load_file, save_file


@pytest.fixture()
def tmp_path_file(tmp_path):
    """Return a callable that yields a fresh temp file path inside tmp_path."""

    def _make(name="output.txt"):
        return str(tmp_path / name)

    return _make


# ------------------------------------------------------------------
# _find_safe_split unit tests
# ------------------------------------------------------------------


class TestFindSafeSplit:
    """Verify that _find_safe_split never lands inside a multibyte sequence."""

    def test_ascii_boundary(self):
        data = b"abcdefgh"
        assert _find_safe_split(data, 4) == 4

    def test_split_before_two_byte_char(self):
        # 'A' * 3 + U+00E9 (é = 0xC3 0xA9, 2 bytes)
        data = b"AAA\xc3\xa9"
        # max_size=4 lands on the continuation byte 0xA9 → must back up
        assert _find_safe_split(data, 4) == 3

    def test_split_includes_complete_two_byte_char(self):
        data = b"AAA\xc3\xa9"
        assert _find_safe_split(data, 5) == 5

    def test_split_before_three_byte_char(self):
        # U+4E16 (世 = 0xE4 0xB8 0x96)
        data = b"AA\xe4\xb8\x96"
        # max_size=3 lands on first continuation byte → back up to 2
        assert _find_safe_split(data, 3) == 2

    def test_split_before_four_byte_char(self):
        # U+1F600 (😀 = 0xF0 0x9F 0x98 0x80)
        data = b"A\xf0\x9f\x98\x80"
        # max_size=2 lands on continuation byte → back up to 1
        assert _find_safe_split(data, 2) == 1

    def test_max_size_beyond_data(self):
        data = b"hello"
        assert _find_safe_split(data, 100) == 5


# ------------------------------------------------------------------
# save_file / load_file round-trip tests
# ------------------------------------------------------------------


class TestSaveFile:
    """End-to-end save/load tests mirroring the bug-report scenarios."""

    def test_small_ascii_file(self, tmp_path_file):
        path = tmp_path_file()
        content = "Hello, world!\n"
        save_file(content, path)
        assert load_file(path) == content

    def test_small_file_with_multibyte(self, tmp_path_file):
        """File under 64 KB with multibyte characters (regression guard)."""
        path = tmp_path_file()
        content = "Hello 🌍🌎🌏\n" * 100  # well under 64 KB
        save_file(content, path)
        assert load_file(path) == content

    def test_large_ascii_file(self, tmp_path_file):
        """File over 64 KB, ASCII only — should save without issues."""
        path = tmp_path_file()
        content = "A" * (BUFFER_SIZE + 1024)
        save_file(content, path)
        assert load_file(path) == content

    def test_large_file_with_emoji(self, tmp_path_file):
        """~70 KB file with emoji throughout — the primary crash scenario."""
        path = tmp_path_file()
        # Each emoji is 4 bytes; build content that exceeds 64 KB.
        emoji_block = "😀😃😄😁😆" * 200  # 200 * 5 * 4 = 4000 bytes per rep
        content = emoji_block * 20  # ~80 KB of emoji
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        save_file(content, path)
        assert load_file(path) == content

    def test_file_exactly_at_boundary_ending_mid_multibyte(self, tmp_path_file):
        """File exactly 64 KB where the boundary falls mid-multibyte."""
        path = tmp_path_file()
        # Fill to just under the boundary with ASCII, then add a 4-byte
        # emoji so the character straddles the 64 KB mark.
        filler = "X" * (BUFFER_SIZE - 2)
        content = filler + "😀" + "tail"
        raw = content.encode("utf-8")
        # The emoji starts at byte 65534 and extends to 65538 — straddles.
        assert raw[BUFFER_SIZE - 2] == 0xF0  # emoji lead byte
        save_file(content, path)
        assert load_file(path) == content

    def test_mixed_ascii_and_cjk_crossing_boundary(self, tmp_path_file):
        """Mixed ASCII and CJK crossing the 64 KB boundary."""
        path = tmp_path_file()
        # '世' is 3 bytes (0xE4 0xB8 0x96).  Build a string where CJK
        # characters straddle the 64 KB mark.
        ascii_part = "A" * (BUFFER_SIZE - 1)  # 65535 ASCII bytes
        cjk_part = "世界你好" * 500  # plenty of 3-byte chars after the boundary
        content = ascii_part + cjk_part
        save_file(content, path)
        assert load_file(path) == content

    def test_custom_small_buffer(self, tmp_path_file):
        """Use a tiny buffer to force many chunk boundaries through multibyte."""
        path = tmp_path_file()
        content = "café ☕ naïve résumé 日本語 🎉" * 50
        save_file(content, path, buffer_size=16)
        assert load_file(path) == content

    def test_empty_file(self, tmp_path_file):
        path = tmp_path_file()
        save_file("", path)
        assert load_file(path) == ""

    def test_byte_for_byte_fidelity(self, tmp_path_file):
        """Saved content matches original byte-for-byte."""
        path = tmp_path_file()
        content = "Hello 🌍 世界 café\n" * 5000
        expected_bytes = content.encode("utf-8")
        save_file(content, path)
        with open(path, "rb") as f:
            actual_bytes = f.read()
        assert actual_bytes == expected_bytes
