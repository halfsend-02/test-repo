"""File saving module with proper UTF-8 buffer handling.

This module handles saving document content to disk using a chunked
buffer strategy. Buffer sizes are calculated in bytes (not character
count) to correctly handle multibyte UTF-8 characters such as emoji
and CJK characters.

Fixed in v2.3.2: Prior to this fix, the buffer was allocated using
character count (len(content)), which underestimates the byte length
of multibyte UTF-8 text. When the byte length exceeded the 64KB
buffer but the character count did not, a buffer overflow occurred
(segmentation fault). The fix ensures all buffer sizing uses the
actual byte length of the UTF-8-encoded content.
"""

import os
import tempfile

# Buffer size in bytes for chunked writing.
WRITE_BUFFER_SIZE = 65536  # 64KB


def _byte_length(text):
    """Return the byte length of text when encoded as UTF-8."""
    return len(text.encode("utf-8"))


def _encode_content(content):
    """Encode content to UTF-8 bytes.

    Args:
        content: String content to encode.

    Returns:
        UTF-8 encoded bytes.

    Raises:
        UnicodeEncodeError: If content cannot be encoded as UTF-8.
    """
    if isinstance(content, bytes):
        return content
    return content.encode("utf-8")


def save_file(filepath, content):
    """Save content to a file with proper UTF-8 handling.

    Uses atomic write (write to temp file, then rename) to prevent
    data corruption on crash. Buffer allocation is based on byte
    length of the UTF-8-encoded content, not character count.

    Args:
        filepath: Path to the destination file.
        content: String or bytes content to save.

    Raises:
        OSError: If the file cannot be written.
        UnicodeEncodeError: If string content cannot be encoded as UTF-8.
    """
    encoded = _encode_content(content)
    total_bytes = len(encoded)

    # Use a temporary file in the same directory for atomic rename.
    dirpath = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".save_")
    try:
        with os.fdopen(fd, "wb") as f:
            offset = 0
            while offset < total_bytes:
                end = min(offset + WRITE_BUFFER_SIZE, total_bytes)
                f.write(encoded[offset:end])
                offset = end
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except BaseException:
        # Clean up temp file on any failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_file(filepath):
    """Read a file and return its content as a string.

    Args:
        filepath: Path to the file to read.

    Returns:
        String content decoded from UTF-8.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If content is not valid UTF-8.
    """
    with open(filepath, "rb") as f:
        return f.read().decode("utf-8")
