# -*- coding: utf-8 -*-
"""jev_advise.py — ตัวช่วย "ที่ปรึกษา (Hermes)" ในการใช้ Jev

คำสั่งเจ้าของระบบ (29 ก.ย. 2026):
  "Jev ต้องคอยช่วยงานและทำงานร่วมกับหรือตัดสินใจแทนได้ในบางกรณีทั้งบอทวิจัย admin bot และที่ปรึกษาด้วย"

หลักการ:
  • ใช้ "โมดูล Jev ที่มีอยู่" (tools/jev.py) — ไม่ตัดสินใจแทนโมดูล (ค้นหา/เชื่อมต่อ/provider จัดการเอง)
  • สวิตช์แยกที่ jev_config.json → use_in_advisor (เปิดไว้ตามคำสั่งเจ้าของระบบ)
  • พรีเซ็ต: hermes-decision = ช่วยดุลยพินิจก่อนตัดสินใจ/อนุมัติในระบบเทรด
             central-decision = Jev ตัดสินใจแทนได้ (ในระบบกลางของ Hermes)
  • ผลลัพธ์บันทึกลงบันทึกของ Jev เสมอ (ตรวจย้อนหลังได้)

ใช้:
  python tools/jev_advise.py --preset hermes-decision --proposal "..." --evidence "..."
  python tools/jev_advise.py --preset central-decision  --task "..." --decide
  python tools/jev_advise.py --status
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)                     # outputs/mt5_python_bridge
SYSROOT = os.path.dirname(os.path.dirname(BR))  # เทรดทองคำ
JEV_CFG = os.path.join(BR, "jev_config.json")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

PRESETS = ("hermes-decision", "central-decision")


def _cfg() -> dict:
    try:
        with open(JEV_CFG, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _switch_on() -> tuple[bool, str]:
    c = _cfg()
    if not bool(c.get("enabled", True)):
        return False, "Jev ปิดอยู่ (jev_config.enabled=false)"
    if not bool(c.get("use_in_advisor", True)):
        return False, "เจตนาไม่ใช้ Jev ในที่ปรึกษา (use_in_advisor=false)"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="ให้ Jev ช่วยดุลยพินิจของที่ปรึกษา (Hermes)")
    ap.add_argument("--preset", default="hermes-decision", choices=PRESETS)
    ap.add_argument("--context", default="hermes", help="บริบทของ Jev (ค่าเริ่มต้น hermes)")
    ap.add_argument("--proposal", default="", help="ข้อเสนอ/แผนที่กำลังพิจารณา")
    ap.add_argument("--task", default="", help="งานที่ให้ Jev ช่วยตัดสิน (central-decision)")
    ap.add_argument("--evidence", default="", help="หลักฐาน/ตัวเลขจริงประกอบ")
    ap.add_argument("--situation", default="", help="สถานการณ์ระบบตอนนี้")
    ap.add_argument("--decide", action="store_true", help="ให้ Jev ตัดสินใจแทน (central-decision)")
    ap.add_argument("--status", action="store_true", help="แสดงสถานะสวิตช์ (ไม่เรียก AI)")
    ap.add_argument("--json", dest="as_json", action="store_true", help="พิมพ์ผลแบบ JSON")
    args = ap.parse_args()

    ok, why = _switch_on()
    if args.status:
        c = _cfg()
        print(json.dumps({"provider": "jev", "enabled": bool(c.get("enabled", True)),
                          "use_in_advisor": bool(c.get("use_in_advisor", True)),
                          "model": c.get("model"), "ready": ok, "note": why or "พร้อมใช้"},
                         ensure_ascii=False, indent=2))
        return 0
    if not ok:
        print(json.dumps({"ok": False, "reason": why}, ensure_ascii=False))
        return 3

    state = {
        "proposal": args.proposal or args.task,
        "task": args.task or args.proposal,
        "evidence": args.evidence,
        "situation": args.situation,
        "who": "ที่ปรึกษา (Hermes / สมองหลักของระบบเทรด)",
        "decide_now": bool(args.decide),
        "asked_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        import jev  # โมดูล Jev ของระบบ
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": "นำเข้าโมดูล Jev ไม่ได้: %s" % exc}, ensure_ascii=False))
        return 4

    try:
        answers = jev.ask_preset(args.preset, state, context=args.context)
        derived = {}
        try:
            derived = jev.derive(args.preset, answers) or {}
        except Exception:
            derived = {}
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": "Jev ตอบไม่ได้: %s" % exc}, ensure_ascii=False))
        return 5

    out = {"ok": True, "preset": args.preset, "context": args.context,
           "decide_now": bool(args.decide), "answers": answers, "derived": derived}
    if args.as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("── ความเห็นของ Jev (%s · context=%s)%s ──" % (
            args.preset, args.context, " · โหมดตัดสินใจแทน" if args.decide else ""))
        if isinstance(derived, dict) and derived:
            for k, v in derived.items():
                print("  • %s: %s" % (k, json.dumps(v, ensure_ascii=False)[:220]))
        else:
            print("  (ไม่มีผลสรุปจาก derive — ดูคำตอบดิบด้านล่าง)")
        if isinstance(answers, dict):
            for k, v in list(answers.items())[:8]:
                print("  · %s = %s" % (k, json.dumps(v, ensure_ascii=False)[:180]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())