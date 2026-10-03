"""UTF-8 aware chunked file writer.

Writes files in chunks without splitting multibyte UTF-8 characters
at buffer boundaries. Fixes a crash (segfault) that occurred when
saving files larger than 64KB containing multibyte characters such
as emoji or CJK text.
"""

BUFFER_SIZE = 65536  # 64KB


def _find_utf8_safe_boundary(data: bytes, limit: int) -> int:
    """Return the largest offset <= limit that does not split a UTF-8 character.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80..0xBF).
    Walking backward from *limit* until we land on a non-continuation byte
    gives us the start of the character that straddles the boundary.  If that
    character extends past *limit* we must split before it; otherwise *limit*
    itself is safe.
    """
    if limit >= len(data):
        return len(data)

    # If the byte at `limit` is not a continuation byte, `limit` is already
    # on a character boundary.
    if (data[limit] & 0xC0) != 0x80:
        return limit

    # Walk back to the leading byte of the character that spans the boundary.
    pos = limit
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # `pos` now points at the leading byte.  The character starting there
    # extends past `limit`, so we must split just before it.
    return pos


def save_file(content: str, path: str, buffer_size: int = BUFFER_SIZE) -> None:
    """Write *content* to *path* in chunks of *buffer_size* bytes.

    Unlike the naive implementation that sliced raw bytes at fixed offsets,
    this version respects UTF-8 character boundaries so that no multibyte
    character is ever split across two write calls.
    """
    data = content.encode("utf-8")
    with open(path, "wb") as fh:
        offset = 0
        while offset < len(data):
            end = min(offset + buffer_size, len(data))
            safe_end = _find_utf8_safe_boundary(data, end)
            # Guard against a single character wider than the buffer (should
            # not happen with valid UTF-8 and buffer_size >= 4, but be safe).
            if safe_end == offset:
                safe_end = end
            fh.write(data[offset:safe_end])
            offset = safe_end


def load_file(path: str) -> str:
    """Read a file written by :func:`save_file` and return its text."""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")
