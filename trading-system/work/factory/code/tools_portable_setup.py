#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ติดตั้งสำหรับเครื่องใหม่ — พา "ระบบเทรดทองคำ" ไปรันเครื่องอื่นได้ (เจ้าของระบบสั่ง 23 ก.ย. 2026)

หลักการ:
  1) หาเส้นทางเชื่อมต่อ Jev เองอัตโนมัติ (env → ไฟล์คีย์ → .env → ค่าที่ Hermes ใช้)
  2) ถ้าเชื่อมไม่ได้ → ตั้งค่าปิด Jev แล้วระบบทำงานต่อด้วยกฎตัวเลขเดิม (ไม่พัง · ไม่ต้องมี Jev)
  3) ตรวจความพร้อมของเครื่องก่อนใช้งานจริง แล้วรายงานเป็นข้อ ๆ

ใช้:  python tools\\portable_setup.py             # ตรวจความพร้อม (ไม่แก้อะไร)
      python tools\\portable_setup.py --apply     # สร้าง venv + ติดตั้งไลบรารี + เชื่อม Jev
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BRIDGE))
VENV_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe") if os.name == "nt" \
    else os.path.join(ROOT, ".venv", "bin", "python")


def run(cmd, cwd=None, timeout=900):
    try:
        p = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return 1, "%s: %s" % (type(exc).__name__, exc)


def check_python():
    ok = sys.version_info >= (3, 9)
    v = sys.version_info
    return ok, "Python %d.%d.%d%s" % (v[0], v[1], v[2], "" if ok else " (ต้องการ ≥ 3.9)")


def check_venv():
    return os.path.exists(VENV_PY), VENV_PY if os.path.exists(VENV_PY) else "ยังไม่มี .venv"


def check_deps():
    """ไลบรารีที่ระบบใช้จริง — MetaTrader5 ต้องมีเฉพาะเครื่องที่ต่อ MT5"""
    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    rc, out = run([py, "-c",
                   "import importlib.util\n"
                                      "mods=['MetaTrader5','requests']\n"
                   "print(','.join(m for m in mods if importlib.util.find_spec(m)) )"], timeout=120)
    have = [m for m in (out or "").strip().split(",") if m]
    need = ["MetaTrader5"]
    missing = [m for m in need if m not in have]
    return not missing, "มี: %s%s" % (", ".join(have) or "-",
                                      (" · ขาด: " + ", ".join(missing)) if missing else "")


def check_jev():
    rc, out = run([VENV_PY if os.path.exists(VENV_PY) else sys.executable,
                   os.path.join(HERE, "jev_connect.py"), "--setup", "--dry"], timeout=300)
    connected = "✅" in (out or "")
    return connected, ("เชื่อมต่อ Jev ได้" if connected else "เชื่อมต่อ Jev ไม่ได้ → ระบบจะทำงานโดยไม่มี Jev (ปกติ)")


def check_mt5():
    """หา terminal ของ MetaTrader 5 ในเครื่องนี้ (ไม่บังคับ — เฉพาะเครื่องที่จะเทรดจริง)"""
    cands = [r"C:\Program Files\MetaTrader 5\terminal64.exe",
             r"C:\Program Files\OANDA Global MetaTrader 5 Terminal\terminal64.exe"]
    found = [p for p in cands if os.path.exists(p)]
    return bool(found), (", ".join(found) if found else "ไม่พบ (ต้องมีเฉพาะเครื่องที่เทรดจริง)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ลงมือติดตั้ง (สร้าง venv/ไลบรารี/เชื่อม Jev)")
    a = ap.parse_args()

    print("🧳 ตั้งเครื่องใหม่ — ระบบเทรดทองคำ (Quantum Trading + AI Live Research)")
    print("   โฟลเดอร์ระบบ: %s" % ROOT)
    results = []
    for name, fn in (("Python เวอร์ชันพอใช้", check_python),
                     (".venv พร้อมใช้", check_venv),
                     ("ไลบรารีหลักครบ", check_deps),
                     ("เส้นทางเชื่อม Jev", check_jev),
                     ("MetaTrader 5 ในเครื่องนี้", check_mt5)):
        ok, msg = fn()
        results.append((name, ok, msg))
        print("   %s %-26s %s" % ("✓" if ok else "•", name, msg))

    if a.apply:
        print("\n   ▶ ลงมือติดตั้ง")
        if not os.path.exists(VENV_PY):
            base = sys.executable
            print("     สร้าง .venv …")
            run([base, "-m", "venv", os.path.join(ROOT, ".venv")], timeout=600)
        req = os.path.join(BRIDGE, "requirements.txt")
        if os.path.exists(req) and os.path.exists(VENV_PY):
            print("     ติดตั้งไลบรารีจาก requirements.txt …")
            rc, out = run([VENV_PY, "-m", "pip", "install", "-r", req], timeout=1800)
            print("     %s" % ("ติดตั้งสำเร็จ ✓" if rc == 0 else "มีข้อผิดพลาด (ดูด้านล่าง)"))
            if rc != 0:
                print("\n".join(out.splitlines()[-6:]))
        print("     ตั้งค่าเส้นทางเชื่อม Jev (อัตโนมัติ) …")
        rc, out = run([VENV_PY if os.path.exists(VENV_PY) else sys.executable,
                       os.path.join(HERE, "jev_connect.py"), "--setup"], timeout=400)
        print(out.strip())

    print("\n   📋 ขั้นถัดไปสำหรับเครื่องใหม่")
    print("     1) ถ้าไม่มีเส้นทางเชื่อม Jev: ใส่คีย์ได้ 3 ทาง — ตัวแปรสภาพแวดล้อม JEV_API_KEY,")
    print("        ไฟล์ work\\jev_key.txt (บรรทัดเดียว) หรือ .env ในโฟลเดอร์โปรเจกต์ (.env แบบ KEY=ค่า)")
    print("        แล้วรัน: tools\\jev_connect.py --setup")
    print("     2) ตรวจสุขภาพระบบ: tools\\full_audit.py   (ควรผ่านครบ)")
    print("     3) ดูอำนาจ Jev:    tools\\jev_power.py --status")
    print("     4) ⚠️ เปิด-ปิดระบบเทรดเป็นอำนาจเจ้าของระบบเท่านั้น (kill switch: AUTO_TRADER_STOP)")
    print("     5) ⚠️ ห้ามคัดลอกโฟลเดอร์ work\\ ข้ามเครื่อง (มี state/lock/audit ของเครื่องเดิม)")
    print("        ให้เริ่ม work\\ ใหม่บนเครื่องนี้")
    bad = [r for r in results if not r[1] and r[0] != "MetaTrader 5 ในเครื่องนี้"]
    return 0 if len(bad) <= 1 else 1


if __name__ == "__main__":
    sys.exit(main())