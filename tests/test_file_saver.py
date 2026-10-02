"""Tests for file_saver module.

Covers the buffer-overflow regression where files >64KB with multibyte
UTF-8 characters caused a segmentation fault (issue #2528).
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_saver import CHUNK_SIZE, load_file, save_file


def test_save_large_file_with_multibyte_chars():
    """Save >64KB of text containing emoji — the original crash case."""
    # ~72KB of emoji (each emoji is 4 bytes in UTF-8)
    content = "\U0001f600" * 18000  # 72000 bytes
    assert len(content.encode("utf-8")) > CHUNK_SIZE

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)


def test_save_large_file_ascii_only():
    """Control case: >64KB of ASCII should save without issue."""
    content = "a" * (CHUNK_SIZE + 1024)
    assert len(content.encode("utf-8")) > CHUNK_SIZE

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)


def test_save_file_under_threshold():
    """Files under 64KB with multibyte chars should save fine."""
    content = "\U0001f600" * 100  # 400 bytes
    assert len(content.encode("utf-8")) < CHUNK_SIZE

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)


def test_multibyte_char_straddles_chunk_boundary():
    """A multibyte character that straddles the 64KB boundary."""
    # Fill up to just before the boundary with ASCII, then add emoji
    ascii_prefix = "x" * (CHUNK_SIZE - 1)
    # The next character is a 4-byte emoji — it would straddle the boundary
    content = ascii_prefix + "\U0001f600" + "y" * 1000

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)


def test_exactly_64kb_with_multibyte():
    """Boundary case: exactly 64KB with multibyte characters."""
    # 4-byte emoji, 16384 of them = exactly 65536 bytes = 64KB
    content = "\U0001f600" * (CHUNK_SIZE // 4)
    assert len(content.encode("utf-8")) == CHUNK_SIZE

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)


def test_cjk_characters_large_file():
    """CJK characters (3-byte UTF-8) in a large file."""
    # CJK characters are 3 bytes each in UTF-8
    content = "世" * 25000  # 75000 bytes
    assert len(content.encode("utf-8")) > CHUNK_SIZE

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        result = load_file(path)
        assert result == content
    finally:
        os.unlink(path)
