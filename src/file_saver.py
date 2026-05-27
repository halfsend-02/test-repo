"""File saving module with correct UTF-8 handling.

This module provides file saving functionality that correctly handles
UTF-8 multibyte characters by using byte length (not character count)
for buffer allocation.
"""

import os

# Buffer size threshold for chunked writing
BUFFER_SIZE = 65536  # 64KB


def save_file(filepath, content):
    """Save content to a file, correctly handling UTF-8 multibyte characters.

    Uses byte length for buffer calculations to avoid overflow when content
    contains multibyte UTF-8 characters (e.g., emoji, CJK characters).

    Args:
        filepath: Path to the file to save.
        content: String content to write.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    # Write in chunks based on byte length, not character count.
    # Previous implementation (v2.3.1 regression) used len(content) which
    # counts characters, not bytes. For multibyte UTF-8 characters (2-4
    # bytes each), this under-allocated the buffer and caused a segfault
    # when byte usage exceeded the 64KB boundary.
    with open(filepath, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += BUFFER_SIZE


def calculate_buffer_size(content):
    """Calculate the required buffer size for content in bytes.

    Returns the byte length of the UTF-8 encoded content, not the
    character count. This distinction matters for multibyte characters.

    Args:
        content: String content to measure.

    Returns:
        The byte length of the UTF-8 encoded content.
    """
    return len(content.encode("utf-8"))
