"""File saver module with buffered write support for UTF-8 content."""

import os
import tempfile

# Default buffer size: 64KB
BUFFER_SIZE = 65536


def save_file(content, filepath):
    """Save content to a file using buffered writes.

    Writes content in chunks to handle large files efficiently.
    The buffer size is based on byte length of the encoded content,
    ensuring correct handling of multibyte UTF-8 characters.

    Args:
        content: String content to save.
        filepath: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    # Write to a temporary file first, then rename for atomicity
    dir_name = os.path.dirname(os.path.abspath(filepath))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        with os.fdopen(fd, "wb") as f:
            offset = 0
            while offset < total_bytes:
                end = min(offset + BUFFER_SIZE, total_bytes)
                f.write(encoded[offset:end])
                offset = end
        os.replace(tmp_path, filepath)
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_file(filepath):
    """Read a UTF-8 encoded file and return its content as a string.

    Args:
        filepath: Path to the file to read.

    Returns:
        The file content as a string.

    Raises:
        OSError: If the file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    with open(filepath, "rb") as f:
        return f.read().decode("utf-8")
