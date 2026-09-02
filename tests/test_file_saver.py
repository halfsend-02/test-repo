"""Tests for the file saver module.

Covers the fix for issue #1960: crash when saving files larger than 64KB
that contain UTF-8 multibyte characters.
"""

import os
import tempfile
import unittest

from src.file_saver import BUFFER_SIZE, save_file


class TestSaveFile(unittest.TestCase):
    """Tests for save_file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _path(self, name):
        return os.path.join(self.tmpdir, name)

    def test_save_small_ascii(self):
        """Small ASCII content saves correctly."""
        content = "hello world"
        path = self._path("small.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_large_ascii(self):
        """ASCII content larger than 64KB saves correctly."""
        content = "A" * (BUFFER_SIZE + 1024)
        path = self._path("large_ascii.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_large_multibyte_utf8(self):
        """Content where char count < 64K but byte count > 64KB saves.

        Each emoji is 4 bytes in UTF-8. 20000 emoji = 80000 bytes > 64KB,
        but only 20000 characters.
        """
        content = "\U0001f600" * 20000  # 80 KB of emoji
        path = self._path("large_emoji.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_exactly_64kb_multibyte(self):
        """Exactly 64KB of multibyte text saves correctly."""
        # 4-byte emoji: need BUFFER_SIZE / 4 characters for exactly 64KB
        count = BUFFER_SIZE // 4
        content = "\U0001f600" * count
        self.assertEqual(len(content.encode("utf-8")), BUFFER_SIZE)
        path = self._path("exact_64kb.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_boundary_mid_multibyte_sequence(self):
        """64KB boundary falling mid-multibyte sequence saves correctly.

        Fill up to one byte before 64KB with ASCII, then add a 4-byte
        emoji so the multibyte sequence straddles the boundary.
        """
        padding = "A" * (BUFFER_SIZE - 1)
        content = padding + "\U0001f600"
        encoded = content.encode("utf-8")
        self.assertGreater(len(encoded), BUFFER_SIZE)
        path = self._path("boundary.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_large_cjk(self):
        """CJK characters (3 bytes each) larger than 64KB save correctly."""
        # 3-byte CJK char: need > BUFFER_SIZE / 3 characters
        count = (BUFFER_SIZE // 3) + 1000
        content = "世" * count  # U+4E16 = 'world' in Chinese
        self.assertGreater(len(content.encode("utf-8")), BUFFER_SIZE)
        path = self._path("large_cjk.txt")
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_save_creates_parent_directories(self):
        """Parent directories are created if they do not exist."""
        path = os.path.join(self.tmpdir, "sub", "dir", "file.txt")
        save_file("content", path)
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "content")

    def test_save_empty_content(self):
        """Empty content saves as an empty file."""
        path = self._path("empty.txt")
        save_file("", path)
        self.assertEqual(os.path.getsize(path), 0)


if __name__ == "__main__":
    unittest.main()
