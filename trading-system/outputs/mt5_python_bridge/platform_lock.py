# Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
"""Small cross-platform nonblocking lock adapter used by the distribution copy."""
from __future__ import annotations

import os


def lock_nonblocking(handle) -> None:
    """Lock byte zero on Windows, or the lock file on POSIX; raise OSError if busy."""
    position = handle.tell()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        handle.seek(position)


def unlock(handle) -> None:
    """Release the lock acquired by :func:`lock_nonblocking`."""
    position = handle.tell()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.seek(position)
