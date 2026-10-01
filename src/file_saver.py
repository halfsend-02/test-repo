"""Buffered file saver with UTF-8-safe chunking.

Writes file content in chunks (default 64 KB) while ensuring that
multibyte UTF-8 sequences are never split across chunk boundaries.
"""

BUFFER_SIZE = 65536  # 64 KB


def _find_safe_split(data: bytes, max_size: int) -> int:
    """Return the largest index <= max_size that does not split a UTF-8 character.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80..0xBF).
    Walking backward from *max_size* until we hit a non-continuation byte
    gives us the start of the last (possibly incomplete) character.  If that
    character fits entirely within *max_size* we keep it; otherwise we split
    just before it.
    """
    if max_size >= len(data):
        return len(data)

    pos = max_size
    # Walk back over any continuation bytes (10xxxxxx).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # *pos* now points at a leading byte (or 0).  Determine how many bytes
    # the character starting at *pos* occupies.
    lead = data[pos]
    if lead < 0x80:
        char_len = 1
    elif lead < 0xE0:
        char_len = 2
    elif lead < 0xF0:
        char_len = 3
    else:
        char_len = 4

    # If the full character fits within max_size, include it.
    if pos + char_len <= max_size:
        return pos + char_len

    # Otherwise split before this character.
    return pos


def save_file(content: str, path: str, buffer_size: int = BUFFER_SIZE) -> None:
    """Save *content* to *path* using buffered writes that respect UTF-8 boundaries.

    Parameters
    ----------
    content:
        The text to write.
    path:
        Destination file path.
    buffer_size:
        Maximum number of bytes per write call.  Defaults to 64 KB.
    """
    data = content.encode("utf-8")
    with open(path, "wb") as fh:
        offset = 0
        while offset < len(data):
            end = min(offset + buffer_size, len(data))
            split = _find_safe_split(data, end)
            # Validate each chunk is valid UTF-8 before writing.
            chunk = data[offset:split]
            chunk.decode("utf-8")  # raises UnicodeDecodeError on bad split
            fh.write(chunk)
            offset = split


def load_file(path: str) -> str:
    """Read and return the text content of *path*."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
