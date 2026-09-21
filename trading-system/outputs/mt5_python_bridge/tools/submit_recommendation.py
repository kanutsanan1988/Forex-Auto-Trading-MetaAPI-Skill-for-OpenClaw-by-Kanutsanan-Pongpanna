#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ตรวจ + ส่งคำแนะนำของบอทเข้าสู่ระบบ (จุดเดียวที่บอทใช้คุยกับสคริปต์ Python)

เจ้าของระบบกำหนด (19 ก.ย. 2026): "บอทต้องรู้ทุกครั้งว่าต้องสื่อสารกับ python script ยังไง"
→ เครื่องมือนี้ทำให้บอท (ทั้งโหมด 2 และแอดมินบอท) ตรวจคำแนะนำของตัวเองได้ก่อนส่ง
   และส่งด้วยวิธีที่ปลอดภัย (atomic + สำรองของเดิม + ติดป้าย source)

ใช้:
  # 1) ตรวจก่อนส่ง (บังคับ) — บอกชัดว่าผิดฟิลด์ไหน ถ้าไม่ผ่าน
  python tools/submit_recommendation.py --check work/_rec.json

  # 2) ส่งเข้าระบบ (ตรวจให้อัตโนมัติก่อนเขียน)
  python tools/submit_recommendation.py --submit work/_rec.json --source bot

  # 3) ดูสัญญาการสื่อสารฉบับเต็ม (บอทควรอ่านทุกครั้งถ้าไม่แน่ใจ)
  python tools/rec_contract.py --print
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
sys.path.insert(0, BR)

import llm_recommendation_consumer as C  # noqa: E402
from runtime_support import current_mode, project_root, write_recommendation  # noqa: E402


def rec_path():
    return os.path.join(project_root(), "research", "recommendations", "latest_recommendation.json")


def autofill(rec):
    """เติมฟิลด์ที่ระบบรู้อยู่แล้วให้ (โหมด/epoch/เวลา) — ลดความผิดพลาดของบอท

    ไม่เติม auto_apply/changes ให้ เพราะสองฟิลด์นั้นคือ 'เจตนา' ของบอท (ต้องตั้งเอง)
    """
    import datetime
    mode = current_mode(project_root())
    if isinstance(rec, dict):
        if mode.get("mode"):
            rec.setdefault("mode", mode["mode"])
        if mode.get("epoch"):
            rec.setdefault("mode_epoch", mode["epoch"])
        # This is the BOT submission interface. Python internal writers use the
        # shared write_recommendation helper and label their own provenance.
        rec.setdefault("uses_llm", True)
        rec.setdefault("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    return rec


def validated_record(path):
    with io.open(path, encoding="utf-8") as stream:
        rec = json.load(stream)
    if not isinstance(rec, dict):
        raise ValueError('คำแนะนำต้องเป็น JSON object')
    rec = autofill(dict(rec))
    ok, err = C.validate(rec)
    if not ok:
        raise ValueError(err)
    mode = current_mode(project_root())
    if rec.get('mode_epoch') != mode.get('epoch') or rec.get('mode') != mode['mode']:
        raise ValueError('โหมด/epoch ไม่ตรงกับระบบปัจจุบัน')
    if mode['mode'] != 'internal_llm_join':
        raise ValueError('โหมด 1 ไม่รับคำแนะนำจาก AI Agent Bot')
    if rec.get('uses_llm') is not True:
        raise ValueError('คำแนะนำจากบอทต้องระบุ uses_llm=true')
    return rec


def check(path):
    """ตรวจคำแนะนำ → (ผ่านไหม, ข้อความอธิบาย)"""
    try:
        validated_record(path)
    except Exception as exc:
        return False, str(exc)
    return True, "ผ่านทุกเงื่อนไข"


def submit(path, source="bot"):
    try:
        rec = validated_record(path)
    except (ValueError, OSError) as exc:
        print("ปฏิเสธ: คำแนะนำไม่ผ่านการตรวจ — %s" % exc)
        print("   ดูสัญญาการสื่อสาร: python outputs/mt5_python_bridge/tools/rec_contract.py --print")
        return 2
    write_recommendation(rec_path(), rec, source=source)
    print("ส่งคำแนะนำเข้าระบบแล้ว ✓ (source=%s · %d การปรับ)"
          % (source, len(rec.get("changes") or [])))
    print("   consumer (ทุก 5 นาที) จะตรวจซ้ำ → ประตูทดสอบ → apply → บันทึกผลลง audit")
    if (project_root() / "work" / "AUTO_TRADER_STOP").exists():
        print("   หมายเหตุ: ระบบปิดอยู่ (kill switch) — คำแนะนำจะถูกเก็บไว้ ยังไม่ถูกนำไปใช้")
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args:
        path = args[args.index("--check") + 1]
        ok, msg = check(path)
        print(("ผ่าน ✓ " if ok else "ไม่ผ่าน ✗ ") + msg)
        if not ok:
            print("   ดูสัญญาการสื่อสาร: python outputs/mt5_python_bridge/tools/rec_contract.py --print")
        return 0 if ok else 1
    if "--submit" in args:
        path = args[args.index("--submit") + 1]
        source = args[args.index("--source") + 1] if "--source" in args else "bot"
        return submit(path, source)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
