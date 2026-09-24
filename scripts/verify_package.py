# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ตรวจความสมบูรณ์และความปลอดภัยของแพ็กก่อนนำไปใช้

ใช้:  python scripts/verify_package.py           (ตรวจโครงสร้าง + สแกนความลับ)
      python scripts/verify_package.py --deep    (เพิ่มการแฮชทุกไฟล์)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)

# คีย์/รหัสที่ต้องไม่ปรากฏในแพ็กแจกจ่ายเด็ดขาด
SECRET_PATTERNS = {
    "openrouter_key": re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"),
    "jwt_token": re.compile(r"eyJhbGciOiJ[A-Za-z0-9_\-\.]{60,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "metaapi_account": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
}
TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".txt", ".cmd", ".ps1", ".cfg", ".ini",
            ".yml", ".yaml", ".toml", ".csv", ".env"}
# ไฟล์ที่ห้ามมีในแพ็ก (สถานะสด/ความลับ)
FORBIDDEN = {".env", ".env.local", "auto_trader.lock", "consumer.lock",
             "research-cycle.lock", "auto_trader_supervisor.lock",
             "openrouter_api_key.machine.dpapi", "auto_trader_audit.jsonl",
             "auto_trader_state.json", "auto_config.json.lock"}
HISTORICAL_RESEARCH_INPUTS = {"auto_trader_audit.jsonl", "auto_trader_state.json"}
# นามสกุล/รูปแบบไฟล์ที่ไม่ควรติดไปกับชุดแจกจ่าย (สำรองค่า/ไฟล์ชั่วคราว/ไบต์โค้ด)
FORBIDDEN_SUFFIX = (".pyc", ".pyo", ".pyd", ".bak", ".tmp", ".orig", ".rej", ".swp")
FORBIDDEN_RE = re.compile(r"(?i)^(auto_config\.json\.bak.*|.*\.bak_.*|.*_patch.*|.*_debug.*|.*_fix.*)$")
FORBIDDEN_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                  ".idea", ".vscode", ".git", "node_modules", ".venv", "venv"}
REQUIRED = ["SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
            "trading-system", "metaapi", "references",
            "trading-system/work/AUTO_TRADER_STOP"]

# path ตายตัวของผู้สร้าง (ต้องไม่เหลือในโค้ด)
# ประกอบสตริงขึ้นมาเพื่อไม่ให้ตัวตรวจตั้งธงตัวเอง (self-match)
AUTHOR_PATHS = [
    "D:" + chr(92) + chr(92) + "AI WorkSpace",
    "D:/AI " + "WorkSpace",
    "C:" + chr(92) + chr(92) + "Users" + chr(92) + chr(92) + "Administrator",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="ตรวจแพ็ก Pytron Engine MT5 Algo Trade")
    ap.add_argument("--deep", action="store_true", help="แฮชทุกไฟล์และรายงาน manifest")
    args = ap.parse_args()

    problems, warnings, stats = [], [], {"files": 0, "bytes": 0}
    manifest = {}

    for name in REQUIRED:
        if not os.path.exists(os.path.join(PACKAGE, name)):
            problems.append(f"missing required entry: {name}")

    for root, dirs, files in os.walk(PACKAGE):
        # Runtime bytecode caches are ignored and excluded from manifests/packages.
        dirs[:] = [d for d in dirs if d not in FORBIDDEN_DIRS]
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, PACKAGE)
            stats["files"] += 1
            try:
                stats["bytes"] += os.path.getsize(path)
            except OSError:
                pass

            rel_posix = rel.replace(os.sep, "/")
            is_archived_research_input = (
                fn in HISTORICAL_RESEARCH_INPUTS
                and rel_posix.startswith("trading-system/research/")
            )
            if fn in FORBIDDEN and not is_archived_research_input:
                problems.append(f"forbidden file present: {rel}")
            if fn.lower().endswith(FORBIDDEN_SUFFIX) or FORBIDDEN_RE.match(fn):
                problems.append(f"forbidden file kind (backup/junk/temp): {rel}")

            if args.deep and fn != "file-manifest.json":
                try:
                    with io.open(path, "rb") as fh:
                        manifest[rel.replace(os.sep, "/")] = hashlib.sha256(
                            fh.read()).hexdigest()
                except OSError:
                    pass

            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            try:
                text = io.open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue

            for label, rx in SECRET_PATTERNS.items():
                hit = rx.search(text)
                # MetaAPI account uuid ในหลักฐานคือข้อมูลบัญชีที่ทดสอบ — เตือน ไม่ใช่ข้อผิดพลาดร้ายแรง
                if hit:
                    msg = f"{label} pattern in {rel}: {hit.group(0)[:14]}..."
                    if label == "metaapi_account":
                        warnings.append(msg)
                    else:
                        problems.append(msg)
                    break

            if ext in (".py", ".cmd", ".ps1"):
                for bad in AUTHOR_PATHS:
                    if bad in text:
                        problems.append(f"hardcoded author path in code: {rel} ({bad})")
                        break


    # ตรวจว่าแพ็กเริ่มที่สภาวะหยุด
    cfg = os.path.join(PACKAGE, "trading-system", "outputs", "mt5_python_bridge",
                       "auto_config.json")
    if os.path.exists(cfg):
        try:
            value = json.load(io.open(cfg, encoding="utf-8"))
            if value.get("live_enabled") is True:
                problems.append("auto_config.json: live_enabled = true "
                                "(แพ็กแจกจ่ายต้องเริ่มที่ false ให้ผู้รับเปิดเอง)")
        except Exception as exc:
            problems.append(f"auto_config.json unreadable: {exc}")

    print("=" * 68)
    print("ผลตรวจแพ็ก: Pytron Engine MT5 Algo Trade")
    print("=" * 68)
    print(f"ไฟล์ทั้งหมด : {stats['files']}")
    print(f"ขนาดรวม     : {stats['bytes'] / 1048576:.1f} MB")
    print(f"ปัญหา       : {len(problems)}")
    print(f"คำเตือน     : {len(warnings)}")
    for item in problems:
        print("  [ปัญหา]  ", item)
    for item in warnings:
        print("  [เตือน]   ", item)
    if args.deep:
        out = os.path.join(PACKAGE, "file-manifest.json")
        io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(
            {"package": os.path.basename(PACKAGE),
             "creator": "Kanutsanan Pongpanna",
             "files": len(manifest), "sha256": manifest},
            ensure_ascii=False, indent=1))
        print(f"manifest    : {out}")
        print("              (sha256 ของทุกไฟล์ ยกเว้นตัว manifest เอง"
              " เพื่อไม่ให้แฮชอ้างตัวเอง)")
    stop = os.path.join(PACKAGE, "trading-system", "work", "AUTO_TRADER_STOP")
    if not os.path.exists(stop):
        warnings.append("ไม่พบ trading-system/work/AUTO_TRADER_STOP "
                        "(ควรมี เพื่อให้ผู้รับเริ่มจากสภาวะหยุด)")
    print("=" * 68)
    print("สถานะเริ่มต้น :", "หยุด (STOP) - ปลอดภัย" if os.path.exists(stop) else "ไม่มีไฟล์หยุด")
    print("ผลลัพธ์:", "ผ่าน - พร้อมใช้" if not problems else "ไม่ผ่าน - แก้ก่อน")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
