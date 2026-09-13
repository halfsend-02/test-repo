"""File saver module.

Handles saving document content to disk with proper UTF-8 encoding support.
"""

import os

# Maximum buffer size for chunked writes (64 KiB).
BUFFER_SIZE = 64 * 1024


def save_file(content, path):
    """Save text content to the given file path.

    Writes the content in chunks to handle large files efficiently.
    Content is encoded as UTF-8 before writing.

    Args:
        content: The text content to save.
        path: The filesystem path to write to.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            end = offset + BUFFER_SIZE
            f.write(encoded[offset:end])
            offset = end
