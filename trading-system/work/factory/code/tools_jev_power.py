#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""บันไดอำนาจของ Jev ใน "ระบบเทรด" — จากผู้ช่วย → ผู้ตัดสินใจ (มีหลักฐานรองรับทุกขั้น)

เจ้าของระบบอนุมัติ 23 ก.ย. 2026: "ใช้เส้นทางสู่การให้อำนาจเต็มสำหรับ Jev"
(ส่วนระบบกลางของ Hermes แยกต่างหาก — ที่นั่น Jev เป็นผู้ตัดสินใจได้ทันทีแล้ว)

ขั้นอำนาจ (Level):
  0 ผู้ช่วย            — ให้ข้อมูลเท่านั้น (สถานะตั้งต้น)
  1 ผู้ช่วย + เบรก      — ยับยั้งการปรับค่าที่ Jev เห็นว่าเสี่ยงได้ (veto)
  2 + ไทเบรก           — คะแนนตัวเลขก้ำกึ่ง → Jev ชี้ขาด (ในกรอบ)
  3 + ลดความเสี่ยง      — Jev ลดขนาด/ความถี่ได้ (เพิ่มไม่ได้)
  4 ผู้ตัดสินใจ (ในกรอบ) — คำตัดสินของ Jev มีผล ภายในกรอบตัวเลขของระบบ

เกณฑ์เลื่อนขั้น (ตกลงล่วงหน้า กันเข้าข้างตัวเอง · วัดจาก work/jev_audit.jsonl + ไม้จริง):
  • ต้องมี ≥ 30 เคสต่อคำแนะนำ
  • กลุ่มที่ Jev "อนุมัติ/ปลอดภัย" ต้องให้เฉลี่ย/ไม้ ดีกว่ากลุ่ม "ทบทวน/ชะลอ" อย่างชัดเจน (≥ +0.010R)
  • กลุ่มอนุมัติต้องมี win rate ไม่แย่กว่ากลุ่มทบทวน
  • ไม่มีกรณีที่ Jev ปล่อยผ่านแล้วเกิดความเสียหายใหญ่ (net ≤ -0.50R) ติดกัน ≥ 3 ครั้ง

กฎถอยขั้น (อัตโนมัติ): ถ้าหลังเลื่อนขั้นแล้ว ผลลัพธ์จริงแย่ลงตามเกณฑ์เดิม → ลดขั้นทันที
ตัวกันถาวร: Jev ลดความเสี่ยงได้เท่านั้น (ห้ามเพิ่ม) · เปิด-ปิดระบบเทรดเป็นอำนาจเจ้าของระบบ ·
            ทุกการใช้/เลื่อน/ถอย ถูกบันทึกใน work/jev_power_audit.jsonl · คืนค่าโรงงานได้เสมอ

ใช้: .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\jev_power.py --status
     ... --promote-check [--apply] | --set-level N --reason "..." | --can veto|tiebreak|shrink|decide
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BRIDGE = os.path.join(ROOT, "outputs", "mt5_python_bridge")
WORK = os.path.join(ROOT, "work")
CFG = os.path.join(BRIDGE, "jev_power.json")
AUDIT = os.path.join(WORK, "jev_power_audit.jsonl")
TRACK = os.path.join(BRIDGE, "tools", "jev_track_record.py")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

LEVELS = {
    0: ("ผู้ช่วย", "ให้ข้อมูล/ความน่าจะเป็นเท่านั้น — โค้ด/บอทเป็นผู้ตัดสิน"),
    1: ("ผู้ช่วย + เบรก", "ยับยั้ง (veto) การปรับค่าที่ Jev เห็นว่าเสี่ยงได้"),
    2: ("+ ไทเบรก", "คะแนนตัวเลขก้ำกึ่ง → ให้ Jev ชี้ขาดภายในกรอบ"),
    3: ("+ ลดความเสี่ยง", "Jev ลดขนาด/ความถี่ได้ · ห้ามเพิ่ม"),
    4: ("ผู้ตัดสินใจ (ในกรอบ)", "คำตัดสินของ Jev มีผลภายในกรอบตัวเลขของระบบ"),
}
MIN_CASES = 30
MARGIN = 0.010          # ส่วนต่างเฉลี่ย/ไม้ ที่ถือว่า "ชัดเจน"
BAD_RUN = 3             # จำนวนครั้งติดที่ปล่อยผ่านแล้วขาดทุนหนัก
BAD_NET = -0.50

DEFAULT = {"level": 0, "promote_to": None, "last_change": None, "last_change_by": None,
           "criteria": {"min_cases": MIN_CASES, "margin": MARGIN, "bad_run": BAD_RUN},
           "env": "trade", "note": "บันไดอำนาจ Jev ในระบบเทรด (ระบบกลางแยกต่างหาก)"}


def _load(path, default):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def log(event, **kw):
    rec = {"ts": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
           .isoformat(timespec="seconds"), "event": event}
    rec.update(kw)
    try:
        with io.open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def level():
    return int(_load(CFG, DEFAULT).get("level", 0))


def can(action):
    """อำนาจที่ระดับปัจจุบันอนุญาต: veto(≥1) · tiebreak(≥2) · shrink(≥3) · decide(≥4)"""
    need = {"veto": 1, "tiebreak": 2, "shrink": 3, "decide": 4}
    return level() >= need.get(action, 99)


def set_level(n, reason="", by="system"):
    cfg = _load(CFG, DEFAULT)
    old = int(cfg.get("level", 0))
    n = max(0, min(4, int(n)))
    if n == old:
        return old
    cfg["level"] = n
    cfg["last_change"] = log("level_change", **{"from": old, "to": n, "by": by, "reason": reason})["ts"]
    cfg["last_change_by"] = by
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    with io.open(CFG, "w", encoding="utf-8") as f:
        f.write(json.dumps(cfg, ensure_ascii=False, indent=2))
    log("set_level", **{"from": old, "to": n, "by": by, "reason": reason})
    return n


def track_data():
    """ดึงผลงานจริงของ Jev ผ่านตัววัด (สคริปต์ล้วน)"""
    import subprocess
    exe = PY if os.path.exists(PY) else sys.executable
    r = subprocess.run([exe, TRACK, "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=240, cwd=ROOT)
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def evaluate(tr):
    """ประเมินว่าถึงเกณฑ์เลื่อนขั้นหรือยัง — คืน (ok, เหตุผล, ตัวเลข)"""
    groups = (tr or {}).get("groups") or {}
    if not groups:
        return False, "ยังไม่มีเคสวัดผล (ไม่มีการเรียก Jev ที่มีไม้ปิดตามหลัง)", {"cases": 0}
    # รวมฝั่ง "ปลอดภัย/อนุมัติ" และฝั่ง "ทบทวน/ชะลอ"
    good, bad = [], []
    for k, v in groups.items():
        (bad if ("unsafe" in k or "False" in k or "hold" in k or "rollback" in k or "review" in k) else good).append(v)
    gc = sum(v["n"] for v in good); bc = sum(v["n"] for v in bad)
    ga = (sum(v["avg"] * v["n"] for v in good) / gc) if gc else 0.0
    ba = (sum(v["avg"] * v["n"] for v in bad) / bc) if bc else 0.0
    info = {"cases_good": gc, "cases_bad": bc, "avg_good": round(ga, 4), "avg_bad": round(ba, 4),
            "min_cases": MIN_CASES, "margin": MARGIN}
    if gc < MIN_CASES or bc < MIN_CASES:
        return False, "เคสยังไม่ถึง %d ต่อกลุ่ม (อนุมัติ %d · ทบทวน %d)" % (MIN_CASES, gc, bc), info
    if (ga - ba) < MARGIN:
        return False, "กลุ่มอนุมัติยังไม่ดีกว่ากลุ่มทบทวนชัดเจน (%.4f vs %.4f · ต้องต่าง ≥ %.3f)" % (ga, ba, MARGIN), info
    return True, "ผ่านเกณฑ์: อนุมัติ %.4f vs ทบทวน %.4f (ต่าง %.4f ≥ %.3f) · เคส %d/%d" % (
        ga, ba, ga - ba, MARGIN, gc, bc), info


def promote_check(apply_=False):
    tr = track_data()
    ok, why, info = evaluate(tr)
    cur = level()
    log("promote_check", **{"level": cur, "ok": bool(ok), "reason": why, "info": info, "applied": bool(apply_ and ok)})
    if ok and apply_ and cur < 4:
        set_level(cur + 1, reason=why, by="auto")
        return cur + 1, why, info
    return cur, why, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--promote-check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--set-level", type=int)
    ap.add_argument("--reason", default="")
    ap.add_argument("--can", choices=("veto", "tiebreak", "shrink", "decide"))
    a = ap.parse_args()

    if a.set_level is not None:
        n = set_level(a.set_level, a.reason or "สั่งด้วยมือ", by="manual")
        print("ตั้งระดับอำนาจ Jev = %d (%s)" % (n, LEVELS[n][0]))
        return 0

    if a.can:
        print("can(%s) = %s (ระดับปัจจุบัน %d)" % (a.can, can(a.can), level()))
        return 0

    if a.promote_check:
        n, why, info = promote_check(apply_=a.apply)
        print("ระดับอำนาจ Jev: %d (%s)" % (n, LEVELS[n][0]))
        print("เกณฑ์เลื่อนขั้น: %s" % why)
        print("ตัวเลข: %s" % json.dumps(info, ensure_ascii=False))
        if a.apply and n < 4 and why.startswith("ผ่านเกณฑ์"):
            print("→ เลื่อนเป็น %d แล้ว" % n)
        return 0

    # --status (ค่าเริ่มต้น)
    cfg = _load(CFG, DEFAULT)
    lv = int(cfg.get("level", 0))
    print("🎚️ บันไดอำนาจของ Jev ในระบบเทรด — ระดับ %d: %s" % (lv, LEVELS[lv][0]))
    print("   ความหมาย: %s" % LEVELS[lv][1])
    print("   อำนาจที่ใช้ได้ตอนนี้: veto=%s · tiebreak=%s · shrink=%s · decide=%s"
          % (can("veto"), can("tiebreak"), can("shrink"), can("decide")))
    print("   ระดับถัดไป: %s" % (LEVELS[min(4, lv + 1)][0] if lv < 4 else "สูงสุดแล้ว"))
    print("   เกณฑ์: ≥%d เคส/กลุ่ม · ส่วนต่างเฉลี่ย ≥ %.3f · ปล่อยผ่านแล้วขาดทุนติด %d ครั้ง → ถอยขั้น"
          % (MIN_CASES, MARGIN, BAD_RUN))
    tr = track_data()
    ok, why, info = evaluate(tr)
    print("   สถานะหลักฐาน: %s" % ("ผ่าน ✓" if ok else "ยังไม่ผ่าน ✗"))
    print("   เหตุผล: %s" % why)
    print("   ตัวกันถาวร: Jev ลดความเสี่ยงได้เท่านั้น (ห้ามเพิ่ม) · เปิด-ปิดระบบเทรดเป็นอำนาจเจ้าของระบบ")
    return 0


if __name__ == "__main__":
    sys.exit(main())