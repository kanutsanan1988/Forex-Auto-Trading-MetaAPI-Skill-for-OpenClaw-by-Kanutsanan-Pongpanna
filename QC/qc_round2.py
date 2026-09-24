# Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
"""Independent QC pass 2: inspect and test the final ZIP after extracting it to a spaced path."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXPECTED_WHEEL = "A2B16AB0277614AFF8BE2C6D02704CB3B4DD75FA946ED64F1445F8D775CF57F0"
FORBIDDEN = {".env", ".env.local", "__pycache__", ".venv", "venv", ".git"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    args = ap.parse_args()
    archive = args.archive.resolve(strict=True)
    checks: list[dict] = []

    def record(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    try:
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            infos = zf.infolist()
            names = [x.filename for x in infos]
            unsafe = []
            forbidden = []
            for name in names:
                p = PurePosixPath(name)
                if p.is_absolute() or ".." in p.parts or "\\" in name:
                    unsafe.append(name)
                if any(part in FORBIDDEN for part in p.parts) or p.name.startswith(".env."):
                    forbidden.append(name)
            record("ZIP integrity", bad is None, bad or "")
            record("safe archive paths", not unsafe, ", ".join(unsafe))
            record("no environment/cache/private repository files", not forbidden,
                   ", ".join(forbidden))
            roots = {PurePosixPath(n).parts[0] for n in names if PurePosixPath(n).parts}
            record("single package root", len(roots) == 1, ", ".join(sorted(roots)))
            wheel_path = next((n for n in names if n.endswith("/vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl")), None)
            if wheel_path:
                wheel_hash = hashlib.sha256(zf.read(wheel_path)).hexdigest().upper()
            else:
                wheel_hash = ""
            record("SDK wheel present and checksum matches", wheel_hash == EXPECTED_WHEEL)

            with tempfile.TemporaryDirectory(prefix="Pytron QC รอบสอง ") as temp:
                dest = Path(temp).resolve()
                for name in names:
                    target = (dest / name).resolve()
                    try:
                        target.relative_to(dest)
                    except ValueError:
                        raise RuntimeError("archive path escaped extraction root")
                zf.extractall(dest)
                package = dest / next(iter(roots))
                required = ["SKILL.md", "README.md", "trading-system/README.md",
                            "trading-system/research/README.md",
                            "trading-system/research/SESSION-STATE.md",
                            "trading-system/research/2026-09-24-metaapi-readonly-validation.md",
                            "trading-system/work/AUTO_TRADER_STOP",
                            "trading-system/outputs/mt5_python_bridge/platform_lock.py",
                            "trading-system/outputs/mt5_python_bridge/test_platform_lock.py",
                            "metaapi/metaapi_mt5_shim.py", "metaapi/METAAPI-SDK-LICENSE.txt",
                            "requirements-metaapi.txt",
                            "scripts/verify_package.py", "QC/qc_round1.py", "QC/qc_round2.py"]
                missing = [p for p in required if not (package / p).is_file()]
                record("final extracted package structure", not missing, ", ".join(missing))
                verify = subprocess.run([sys.executable, str(package / "scripts/verify_package.py")],
                                        cwd=package, capture_output=True, text=True, timeout=180,
                                        encoding="utf-8", errors="replace")
                record("extracted package self-check", verify.returncode == 0)
                tests = subprocess.run([sys.executable, str(package / "metaapi/test_shim_offline.py")],
                                       cwd=package, capture_output=True, text=True, timeout=180,
                                       encoding="utf-8", errors="replace")
                record("extracted offline adapter tests", tests.returncode == 0,
                       tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "")
                lock_test = subprocess.run(
                    [sys.executable, str(package / "trading-system/outputs/mt5_python_bridge/test_platform_lock.py")],
                    cwd=package / "trading-system/outputs/mt5_python_bridge",
                    capture_output=True, text=True, timeout=60,
                    encoding="utf-8", errors="replace")
                record("extracted cross-platform lock test", lock_test.returncode == 0,
                       lock_test.stdout.strip().splitlines()[-1] if lock_test.stdout.strip() else "")
    except Exception as exc:
        record("QC execution", False, type(exc).__name__)

    result = {"round": 2, "method": "final ZIP integrity + safe extraction + extracted-package tests",
              "passed": all(item["passed"] for item in checks), "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
