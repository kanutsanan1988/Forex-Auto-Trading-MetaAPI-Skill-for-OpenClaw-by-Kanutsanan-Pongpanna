# Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
"""Independent QC pass 1: static structure, safety, license, SDK, syntax, and offline tests."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".txt", ".toml", ".yml", ".yaml", ".cfg", ".ini"}
SECRET_PATTERNS = {
    "jwt": re.compile(r"eyJhbGciOiJ[A-Za-z0-9_.-]{60,}"),
    "openrouter": re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
}
REQUIRED = [
    "SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
    "trading-system/README.md", "trading-system/LICENSE",
    "trading-system/research/README.md",
    "trading-system/research/SESSION-STATE.md",
    "trading-system/research/2026-09-24-metaapi-readonly-validation.md",
    "trading-system/work/AUTO_TRADER_STOP",
    "metaapi/metaapi_mt5_shim.py", "metaapi/test_shim_offline.py",
    "metaapi/METAAPI-SDK-LICENSE.txt",
    "metaapi/evidence/live-readonly-verify-20260924.json",
    "vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl",
    "vendor/SHA256SUMS.txt", "scripts/verify_package.py",
    "requirements-metaapi.txt",
    "scripts/metaapi_connect_check.py", "scripts/metaapi_engine_smoke.py",
]


def main() -> int:
    checks: list[dict] = []

    def record(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    record("required files", not missing, ", ".join(missing))

    forbidden = []
    syntax_errors = []
    secret_hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".venv", "venv", ".git"}]
        for name in files:
            path = Path(base) / name
            rel = path.relative_to(ROOT).as_posix()
            if name == ".env" or name.startswith(".env.") or path.suffix.lower() in {".pyc", ".pyo", ".pyd"}:
                forbidden.append(rel)
            if path.suffix.lower() == ".py":
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=rel)
                except Exception as exc:  # report only the relative file, not source content
                    syntax_errors.append(rel)
            if path.suffix.lower() in TEXT_SUFFIXES:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for label, pattern in SECRET_PATTERNS.items():
                    if pattern.search(text):
                        secret_hits.append(f"{rel}:{label}")
                        break
    record("no credential/cache artifacts", not forbidden, ", ".join(forbidden))
    record("no high-risk secret patterns", not secret_hits, ", ".join(secret_hits))
    record("Python syntax parses", not syntax_errors, ", ".join(syntax_errors))

    cfg = ROOT / "trading-system/outputs/mt5_python_bridge/auto_config.json"
    try:
        live_disabled = json.loads(cfg.read_text(encoding="utf-8")).get("live_enabled") is False
    except Exception:
        live_disabled = False
    record("distribution Live disabled and Kill Switch present",
           live_disabled and (ROOT / "trading-system/work/AUTO_TRADER_STOP").exists())
    record("license scopes separated",
           "MIT No Attribution" in (ROOT / "LICENSE").read_text(encoding="utf-8")
           and "MIT License" in (ROOT / "trading-system/LICENSE").read_text(encoding="utf-8")
           and "METAAPI-SDK-LICENSE.txt" in (ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8"))

    wheel = ROOT / "vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl"
    expected = "A2B16AB0277614AFF8BE2C6D02704CB3B4DD75FA946ED64F1445F8D775CF57F0"
    actual = hashlib.sha256(wheel.read_bytes()).hexdigest().upper() if wheel.exists() else ""
    record("bundled SDK wheel checksum", actual == expected)

    verify = subprocess.run([sys.executable, str(ROOT / "scripts/verify_package.py")],
                            cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    record("package self-check", verify.returncode == 0)
    tests = subprocess.run([sys.executable, str(ROOT / "metaapi/test_shim_offline.py")],
                           cwd=ROOT, capture_output=True, text=True, timeout=180,
                           encoding="utf-8", errors="replace")
    record("offline MetaAPI adapter tests", tests.returncode == 0,
           tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "")
    lock_test = subprocess.run(
        [sys.executable, str(ROOT / "trading-system/outputs/mt5_python_bridge/test_platform_lock.py")],
        cwd=ROOT / "trading-system/outputs/mt5_python_bridge",
        capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace")
    record("cross-platform engine lock test", lock_test.returncode == 0,
           lock_test.stdout.strip().splitlines()[-1] if lock_test.stdout.strip() else "")

    result = {"round": 1, "method": "static + package self-check + offline adapter tests",
              "passed": all(item["passed"] for item in checks), "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
