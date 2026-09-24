#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ผลงานของ Jev — วัดว่า "คำแนะนำของ Jev ถูกจริงไหม" ด้วยผลลัพธ์จริงหลังการเรียก

ทำไมต้องมี: คำถามเจ้าของระบบ 23 ก.ย. 2026 — "Jev ควรเป็นแค่ผู้ช่วย หรือเป็นผู้ตัดสินใจได้ด้วย"
คำตอบต้องมาจากหลักฐาน ไม่ใช่ความเห็น → ไฟล์นี้วัด: หลัง Jev แนะนำ X แล้ว ไม้ที่ปิดถัดไปเป็นอย่างไร

วิธีวัด (ไม่ใช้ LLM เลย · อ่านไฟล์จริง):
  1. การเรียก Jev: work/jev_audit.jsonl (เวลา · preset · context · derived)
  2. ไม้ที่ปิดจริง: work/auto_trader_audit.jsonl (event=position_closed)
  3. ต่อการเรียกแต่ละครั้ง → หาไม้ที่ปิดในช่วง [เวลาเรียก, เวลาเรียก + window]
     แล้วคิด net รวม/เฉลี่ย/win rate ของไม้นั้น
  4. สรุปตาม "คำแนะนำที่ Jev ให้" (decision / safe / direction) → เห็นว่าคำแนะนำไหนให้ผลจริง

เกณฑ์ตัดสิน (ตกลงล่วงหน้า กันเข้าข้างตัวเอง):
  • ≥ 30 เคสขึ้นไปต่อคำแนะนำ → เริ่มใช้เป็นหลักฐานได้
  • เฉลี่ย net ของกรณีที่ Jev "อนุมัติ" ต้องดีกว่ากรณีที่ "ชะลอ" อย่างชัดเจน
  • ถ้าผลตรงข้ามหรือไม่มีข้อมูล → Jev ยังเป็นได้แค่ "ผู้ช่วย" ไม่ใช่ผู้ตัดสินใจ
"""
import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WORK = os.path.join(ROOT, "work")
JEV = os.path.join(WORK, "jev_audit.jsonl")
TRADES = os.path.join(WORK, "auto_trader_audit.jsonl")
MIN_CASES = 30


def _load(path, marker=None):
    if not os.path.exists(path):
        return []
    out = []
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if marker and marker not in line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _ts(s):
    """ISO → วินาที (รองรับ +07:00/+00:00) — คืน None ถ้าอ่านไม่ได้"""
    import datetime
    try:
        t = str(s).replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(t).timestamp()
    except Exception:
        return None


def verdict_of(row):
    """สรุป 'คำแนะนำ' ของการเรียกหนึ่งครั้ง — รองรับทั้ง derived (ใหม่) และ summary (เดิม)"""
    d = dict(row.get("derived") or {})
    s = row.get("summary")
    if isinstance(s, dict):
        for k, v in s.items():
            d.setdefault(k, v)
    for k in ("decision", "next_action", "next_lever", "direction", "pressure", "biggest_risk", "theme"):
        if d.get(k):
            return "%s=%s" % (k, str(d[k]).split("(")[0].strip())
    if d.get("safe") is not None:
        return "safe=%s" % str(d["safe"]).split("(")[0].strip()
    if d.get("pass") is not None:
        return "pass=%s" % str(d["pass"]).split("(")[0].strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=float, default=4.0, help="หน้าต่างวัดผลหลังการเรียก (ชั่วโมง)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    calls = _load(JEV)
    trades = [t for t in _load(TRADES, '"position_closed"') if t.get("event") == "position_closed"]
    trades_t = [(_ts(t.get("time")), float(t.get("net") or 0.0)) for t in trades]
    trades_t = [(x, n) for x, n in trades_t if x]

    joined = collections.defaultdict(list)
    unmatched = 0
    for c in calls:
        v = verdict_of(c)
        tc = _ts(c.get("ts"))
        if not v or not tc:
            continue
        window = [n for x, n in trades_t if tc <= x <= tc + a.window_hours * 3600]
        if window:
            joined[v].extend(window)
        else:
            unmatched += 1

    data = {
        "calls_total": len(calls),
        "calls_with_verdict": sum(1 for c in calls if verdict_of(c)),
        "calls_without_followup_trade": unmatched,
        "window_hours": a.window_hours,
        "trades_total": len(trades_t),
        "groups": {},
    }
    for k, nets in sorted(joined.items()):
        wins = [n for n in nets if n > 0]
        data["groups"][k] = {
            "n": len(nets), "net": sum(nets), "avg": sum(nets) / len(nets),
            "win_rate": 100.0 * len(wins) / len(nets),
            "enough": len(nets) >= MIN_CASES,
        }

    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print("📏 ผลงานของ Jev — วัดจากไม้จริงหลังการเรียก (หน้าต่าง %.1f ชม.)" % a.window_hours)
    print("   เรียก Jev ทั้งหมด %d ครั้ง (มีคำแนะนำให้วัด %d) · ไม้ที่ปิดจริง %d ไม้"
          % (data["calls_total"], data["calls_with_verdict"], data["trades_total"]))
    print("   การเรียกที่ 'ยังไม่มีไม้ตามหลัง' (วัดไม่ได้): %d ครั้ง" % unmatched)
    print()
    if not data["groups"]:
        print("   ⚠️ ยังไม่มีข้อมูลพอตัดสิน: ไม่มีการเรียก Jev ครั้งใดที่มีไม้ปิดจริงตามหลัง")
        print("   → ตามเกณฑ์: Jev ยังเป็นได้แค่ 'ผู้ช่วย' (ยังไม่ควรให้เป็นผู้ตัดสินใจ)")
        print("   → ระบบจะสะสมหลักฐานเองอัตโนมัติเมื่อมีการเทรดจริงหลังการเรียก Jev")
        return 0
    print("   %-24s %6s %9s %9s %8s %s" % ("คำแนะนำของ Jev", "เคส", "net รวม", "เฉลี่ย/ไม้", "ชนะ%", "พอตัดสิน?"))
    for k, v in sorted(data["groups"].items(), key=lambda x: -x[1]["avg"]):
        print("   %-24s %6d %+9.2f %+9.3f %7.1f%% %s"
              % (k, v["n"], v["net"], v["avg"], v["win_rate"], "ได้ ✓" if v["enough"] else "ยังไม่พอ (ต้อง ≥%d)" % MIN_CASES))
    print()
    print("   เกณฑ์: คำแนะนำที่ Jev 'อนุมัติ' ต้องให้เฉลี่ย/ไม้ดีกว่ากลุ่ม 'ชะลอ' อย่างชัดเจน + มี ≥%d เคส" % MIN_CASES)
    return 0


if __name__ == "__main__":
    sys.exit(main())