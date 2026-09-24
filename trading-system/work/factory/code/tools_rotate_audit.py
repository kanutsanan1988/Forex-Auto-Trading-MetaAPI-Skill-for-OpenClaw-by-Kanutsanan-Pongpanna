#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""หมุน/บีบอัด audit log — เก็บข้อมูลเก่าเป็น .gz ไม่ลบอะไรทิ้ง (เพิ่ม 19 ก.ย. 2026)

เหตุผล: work/auto_trader_audit.jsonl โตต่อเนื่อง (ตรวจล่าสุด ~87 MB / 30,448 บรรทัด)
        ทำให้เครื่องมือที่อ่านทั้งไฟล์ช้า และเปลืองพื้นที่

หลักการ (ปลอดภัยที่สุด):
  1) ไม่ลบข้อมูล — ย้ายส่วนเก่าไปเป็นไฟล์ .gz ใน work/archive/
  2) ต้องให้ตัวเทรดหยุดก่อน (ถ้ารันอยู่จะปฏิเสธ) เพื่อไม่ให้เขียนชนกับข้อมูลที่กำลังถูก append
  3) สำรองไฟล์เดิมไว้ 1 ชุดก่อนเขียนทับ
  4) เขียนไฟล์ใหม่แบบ atomic (temp + os.replace)

ใช้:
  python tools/rotate_audit.py --dry-run          # ดูว่าจะย้ายอะไร (ไม่แตะไฟล์)
  python tools/rotate_audit.py --keep-days 30     # เก็บ 30 วันล่าสุดไว้ในไฟล์จริง
"""
import argparse
import datetime
import gzip
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "work")
AUDIT = os.path.join(WORK, "auto_trader_audit.jsonl")
ARCHIVE_DIR = os.path.join(WORK, "archive")
STOP_FILE = os.path.join(WORK, "AUTO_TRADER_STOP")
SUPERVISOR_PID = os.path.join(WORK, "auto_trader_supervisor.pid")
TRADER_PID = os.path.join(WORK, "auto_trader.pid")


def trader_running() -> bool:
    for p in (SUPERVISOR_PID, TRADER_PID):
        if not os.path.exists(p):
            continue
        try:
            pid = int(io.open(p, encoding="ascii").read().strip())
        except Exception:
            continue
        try:
            import subprocess
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True, timeout=20).stdout or ""
            if str(pid) in out:
                return True
        except Exception:
            pass
    return False


def parse_ts(value):
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-days", type=float, default=30.0, help="เก็บกี่วันล่าสุดไว้ในไฟล์จริง")
    ap.add_argument("--dry-run", action="store_true", help="แสดงผลอย่างเดียว ไม่แตะไฟล์")
    ap.add_argument("--force", action="store_true", help="ทำแม้ตัวเทรดกำลังรัน (ไม่แนะนำ)")
    args = ap.parse_args()

    if not os.path.exists(AUDIT):
        print("ไม่พบไฟล์ audit:", AUDIT)
        return 1

    if trader_running() and not args.force:
        print("ปฏิเสธ: ตัวเทรดกำลังรันอยู่ — หยุดระบบก่อน (กันเขียนชนกับข้อมูลที่กำลัง append)")
        print("ถ้ามั่นใจจริง ๆ ใช้ --force (ไม่แนะนำ)")
        return 2

    size_before = os.path.getsize(AUDIT)
    print(f"ไฟล์ audit: {size_before/1048576:.1f} MB")

    # อ่านทั้งไฟล์ + แยกตามเวลา
    keep_rows, old_rows = [], []
    total = bad = 0
    with io.open(AUDIT, encoding="utf-8") as fh:
        for line in fh:
            total += 1
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                keep_rows.append(line)          # บรรทัดที่ parse ไม่ได้ → เก็บไว้ (ไม่ทิ้ง)
                continue
            ts = parse_ts(rec.get("time"))
            if ts is None:
                keep_rows.append(line)          # ไม่มีเวลา → เก็บไว้
                continue
            (keep_rows if (datetime.datetime.now(datetime.timezone.utc) - ts).days < args.keep_days
             else old_rows).append(line)

    print(f"บรรทัดทั้งหมด: {total} | เก็บไว้: {len(keep_rows)} | ย้ายเข้า archive: {len(old_rows)}"
          + (f" | parse ไม่ได้: {bad}" if bad else ""))

    if not old_rows:
        print("ไม่มีอะไรต้องหมุน (ข้อมูลใหม่ทั้งหมดอยู่ในช่วงที่กำหนด)")
        return 0

    # ช่วงเวลาของส่วนที่จะย้าย
    first = parse_ts(json.loads(old_rows[0]).get("time")) if old_rows else None
    last = parse_ts(json.loads(old_rows[-1]).get("time")) if old_rows else None
    stamp = (first or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%d")
    arch_name = f"audit-{stamp}.jsonl.gz"
    arch_path = os.path.join(ARCHIVE_DIR, arch_name)
    print(f"จะสร้าง: {arch_path}")
    if first and last:
        print(f"  ช่วงข้อมูลที่ย้าย: {first.isoformat()[:16]} -> {last.isoformat()[:16]}")

    if args.dry_run:
        print("\n(dry-run — ไม่ได้แตะไฟล์ใด ๆ)")
        return 0

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    # 1) เขียน archive (.gz)
    with gzip.open(arch_path, "wt", encoding="utf-8") as gz:
        gz.writelines(old_rows)
    # 2) สำรองไฟล์เดิม
    bak = AUDIT + ".bak_rotate_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(AUDIT, bak)
    # 3) เขียนไฟล์จริงใหม่แบบ atomic
    fd, tmp = tempfile.mkstemp(dir=WORK, prefix="_audit_", suffix=".tmp")
    try:
        with io.open(fd, "w", encoding="utf-8", closefd=True) as out:
            out.writelines(keep_rows)
        os.replace(tmp, AUDIT)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    size_after = os.path.getsize(AUDIT)
    arch_size = os.path.getsize(arch_path)
    print("")
    print(f"สำเร็จ: ไฟล์จริง {size_before/1048576:.1f} MB -> {size_after/1048576:.1f} MB "
          f"| archive {arch_size/1048576:.1f} MB (บีบอัดแล้ว)")
    print(f"สำรองไว้ที่: {bak}")
    print("อ่าน archive ได้ด้วย: zcat " + arch_name + " | head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
