"""Tests for the file saving module with UTF-8 handling."""

import os
import tempfile

from src.file_saver import BUFFER_SIZE, calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Tests for byte-length calculation."""

    def test_ascii_only(self):
        text = "hello"
        assert calculate_buffer_size(text) == 5

    def test_multibyte_emoji(self):
        # Each emoji is 4 bytes in UTF-8
        text = "\U0001f600"  # 😀
        assert calculate_buffer_size(text) == 4

    def test_cjk_characters(self):
        # CJK characters are 3 bytes each in UTF-8
        text = "\u4e16\u754c"  # 世界
        assert calculate_buffer_size(text) == 6

    def test_mixed_content(self):
        text = "hello \U0001f600 \u4e16\u754c"
        # 'hello ' = 6 bytes, 😀 = 4, ' ' = 1, 世界 = 6
        assert calculate_buffer_size(text) == 17

    def test_empty_string(self):
        assert calculate_buffer_size("") == 0


class TestSaveFile:
    """Tests for file saving with correct UTF-8 handling."""

    def test_save_ascii_small_file(self):
        content = "a" * 1000
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                assert f.read() == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_emoji_at_64kb_boundary(self):
        """Save a file with exactly 64KB of emoji text."""
        # Each emoji is 4 bytes; 16384 emoji = 65536 bytes = 64KB
        emoji = "\U0001f600"
        content = emoji * (BUFFER_SIZE // 4)
        assert calculate_buffer_size(content) == BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
            assert len(saved) == BUFFER_SIZE
        finally:
            os.unlink(path)

    def test_save_emoji_above_64kb(self):
        """Save a file with >64KB of emoji text (the crash case)."""
        emoji = "\U0001f600"
        # 20000 emoji * 4 bytes = 80000 bytes > 64KB
        content = emoji * 20000

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
            assert len(saved) == 80000
        finally:
            os.unlink(path)

    def test_save_ascii_above_64kb(self):
        """Save a file with >64KB of ASCII text (control case)."""
        content = "x" * 70000

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
            assert len(saved) == 70000
        finally:
            os.unlink(path)

    def test_save_mixed_content_above_64kb(self):
        """Save mixed ASCII/emoji straddling the 64KB byte boundary."""
        # ~32KB of ASCII + enough emoji to push past 64KB
        ascii_part = "a" * 32768
        emoji_part = "\U0001f600" * 9000  # 36000 bytes
        content = ascii_part + emoji_part

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_content_integrity(self):
        """Verify saved files reopen with content intact."""
        content = "Hello \U0001f30d\u4e16\u754c! " * 5000

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "r", encoding="utf-8") as f:
                restored = f.read()
            assert restored == content
        finally:
            os.unlink(path)

    def test_save_rejects_non_string(self):
        """Content must be a string."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            try:
                save_file(path, b"bytes")
                assert False, "Should have raised TypeError"
            except TypeError:
                pass
        finally:
            os.unlink(path)
