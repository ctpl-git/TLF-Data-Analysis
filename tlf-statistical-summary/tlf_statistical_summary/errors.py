"""
errors.py — shared file-write error handling
A locked/open/unwritable output file is a routine, recoverable
situation (close the file and retry) — not a programming error — so
it gets a plain-language message instead of a raw traceback.
"""


class ReportWriteError(OSError):
    """Raised when a report/export file can't be written — e.g. it's
    open in another program (a common Windows lock) or the path isn't
    writable."""


def open_for_write(path: str, mode: str, **kwargs):
    """Wraps open() for writing with a clear error on failure."""
    try:
        return open(path, mode, **kwargs)
    except PermissionError:
        raise ReportWriteError(
            f"Couldn't write to '{path}' — it may be open in another program "
            f"(e.g. Excel or a text editor). Close it and try again, or choose "
            f"a different path."
        )
    except OSError as e:
        raise ReportWriteError(f"Couldn't write to '{path}': {e}")
