"""File save module with correct UTF-8 buffer handling.

This module provides file-saving functionality that correctly handles
multibyte UTF-8 characters by allocating buffers based on byte length
rather than character count.
"""

# Buffer size threshold for chunked writes (64KB)
CHUNK_SIZE = 65536


def save_file(content: str, filepath: str) -> None:
    """Save content to a file using chunked writes.

    Uses byte length (not character count) for buffer allocation to
    correctly handle multibyte UTF-8 characters such as emoji and CJK
    characters.

    Args:
        content: The text content to save.
        filepath: The destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    with open(filepath, "wb") as f:
        offset = 0
        while offset < len(encoded):
            end = offset + CHUNK_SIZE
            # Avoid splitting a multibyte character at the chunk boundary.
            # UTF-8 continuation bytes start with 0b10xxxxxx (0x80..0xBF).
            if end < len(encoded):
                while end > offset and (encoded[end] & 0xC0) == 0x80:
                    end -= 1
            chunk = encoded[offset:end]
            f.write(chunk)
            offset += len(chunk)


def load_file(filepath: str) -> str:
    """Load text content from a file.

    Args:
        filepath: The source file path.

    Returns:
        The decoded text content.

    Raises:
        OSError: If the file cannot be read.
    """
    with open(filepath, "rb") as f:
        return f.read().decode("utf-8")
