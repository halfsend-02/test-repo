"""File handler module for saving documents.

Handles file saving with proper UTF-8 encoding support, using byte
length (not character count) for buffer sizing to avoid buffer overflow
when saving files containing multibyte characters.
"""

import os
import tempfile

# Default buffer size for chunked file writes.
DEFAULT_BUFFER_SIZE = 64 * 1024  # 64KB


def save_file(content: str, filepath: str) -> None:
    """Save content to a file with proper UTF-8 byte-length handling.

    Uses byte length of the encoded content for buffer management,
    ensuring that multibyte UTF-8 characters (emoji, CJK, etc.) do
    not cause buffer overflows.

    The write is performed atomically via a temporary file to prevent
    data loss if the process is interrupted.

    Args:
        content: The text content to save.
        filepath: The destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    dirpath = os.path.dirname(os.path.abspath(filepath))

    # Write atomically: write to a temp file then rename, so a crash
    # mid-write doesn't corrupt the target file.
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        offset = 0
        total = len(encoded)  # byte length, not character count
        while offset < total:
            end = min(offset + DEFAULT_BUFFER_SIZE, total)
            os.write(fd, encoded[offset:end])
            offset = end
        os.fsync(fd)
        os.close(fd)
        fd = -1  # mark as closed
        os.replace(tmp_path, filepath)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        # Clean up the temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_file(filepath: str) -> str:
    """Read a UTF-8 encoded file and return its content as a string.

    Args:
        filepath: The file path to read.

    Returns:
        The decoded text content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    with open(filepath, "rb") as f:
        return f.read().decode("utf-8")
