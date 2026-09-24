# Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
import tempfile
import unittest

from platform_lock import lock_nonblocking, unlock


class PlatformLockTests(unittest.TestCase):
    def test_acquire_and_release_lock(self):
        with tempfile.TemporaryFile(mode="w+b") as handle:
            handle.write(b"0")
            handle.flush()
            lock_nonblocking(handle)
            unlock(handle)


if __name__ == "__main__":
    unittest.main()
