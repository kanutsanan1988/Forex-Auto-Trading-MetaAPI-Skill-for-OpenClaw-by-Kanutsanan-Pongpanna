#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
"""Exercise the project's own advisory file lock on the current host OS."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

BRIDGE = Path(__file__).resolve().parents[1]
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

import runtime_support  # noqa: E402


class RuntimeSupportLockTests(unittest.TestCase):
    def test_lock_acquires_and_releases_on_host_os(self):
        with tempfile.TemporaryDirectory(prefix="runtime-lock-") as tmp:
            lock_path = Path(tmp) / "settings.json.lock"
            with runtime_support.file_lock(lock_path, timeout=1):
                self.assertTrue(lock_path.is_file())
            # Reacquiring after the context verifies the OS lock is released.
            with runtime_support.file_lock(lock_path, timeout=1):
                self.assertTrue(lock_path.is_file())


if __name__ == "__main__":
    unittest.main()
