#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ตรวจเวลาตลาดของระบบ เทียบกับเวลาจริงของโบรกเกอร์ (เพิ่ม 19 ก.ย. 2026)

ทำไมต้องมี: `market_clock.py` ใช้ตารางมาตรฐาน CME/COMEX + DST สหรัฐฯ
แต่โบรกเกอร์แต่ละรายอาจเปิด/ปิดต่างกันเล็กน้อย → ควรรันเครื่องมือนี้ **ตอนตลาดเปิด**
(ตลาดปิดอยู่ MT5 จะตอบ 'Terminal: Call failed' และไม่มีแท่งให้ตรวจ)

วิธีตรวจ: ดึงแท่งจริง → นับว่าชั่วโมง UTC ใดมี/ไม่มีแท่ง ในแต่ละวันในสัปดาห์
         แล้วเทียบกับ market_clock.market_open() → รายงานจุดที่ไม่ตรง

ใช้:  python tools/verify_market_hours.py [--days 14] [--tf M1]
"""
import argparse
import collections
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
sys.path.insert(0, BR)

import MetaTrader5 as mt5  # noqa: E402
import market_clock as mc  # noqa: E402

WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TF = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}


def fetch(symbol, tf, days):
    """ลองหลายวิธี เพราะบางช่วง terminal ให้เฉพาะบาง API"""
    now = datetime.datetime.now(datetime.timezone.utc)
    tries = [
        ("copy_rates_from_pos", lambda: mt5.copy_rates_from_pos(symbol, tf, 0, 20000)),
        ("copy_rates_from", lambda: mt5.copy_rates_from(symbol, tf, now - datetime.timedelta(days=days), 50000)),
        ("copy_rates_range", lambda: mt5.copy_rates_range(symbol, tf, now - datetime.timedelta(days=days), now)),
    ]
    for label, fn in tries:
        try:
            r = fn()
        except Exception as exc:
            print(f"  {label}: error {exc}")
            continue
        n = 0 if r is None else len(r)
        print(f"  {label}: {n} แท่ง | last_error={mt5.last_error()}")
        if n:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSD.sml")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--tf", default="M1", choices=list(TF))
    args = ap.parse_args()

    if not mt5.initialize():
        print("เชื่อม MT5 ไม่ได้:", mt5.last_error())
        return 1
    mt5.symbol_select(args.symbol, True)
    print(f"ตรวจเวลาตลาด: {args.symbol} · {args.tf} · {args.days} วัน")
    rates = fetch(args.symbol, TF[args.tf], args.days)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        print("")
        print("ยังดึงแท่งไม่ได้ — ให้รันใหม่ตอนตลาดเปิด (ตลาดปิด MT5 จะตอบ 'Terminal: Call failed')")
        return 2

    grid = collections.Counter()
    span = [None, None]
    for r in rates:
        t = datetime.datetime.fromtimestamp(int(r["time"]), datetime.timezone.utc)
        grid[(t.weekday(), t.hour)] += 1
        span[0] = t if span[0] is None else min(span[0], t)
        span[1] = t if span[1] is None else max(span[1], t)
    print(f"ช่วงข้อมูล: {span[0].isoformat()[:16]} -> {span[1].isoformat()[:16]} ({len(rates)} แท่ง)")

    weeks = max(args.days / 7.0, 1.0)
    print("")
    print("=== เทียบ market_clock กับแท่งจริง ===")
    mismatch = []
    for wd in range(7):
        for hour in range(24):
            have = grid.get((wd, hour), 0)
            bar_open = have >= max(1, int(weeks * 0.5))     # มีแท่งอย่างน้อยครึ่งหนึ่งของสัปดาห์ที่ผ่านมา
            # ใช้ 'วันในสัปดาห์/ชั่วโมง' ของแท่งจริงเป็นตัวแทนเวลานั้น
            probe = datetime.datetime(2026, 9, 14, hour, 0, tzinfo=datetime.timezone.utc)  # จันทร์อ้างอิง
            probe = probe + datetime.timedelta(days=wd)
            clock_open = mc.market_open(probe)
            if bar_open != clock_open:
                mismatch.append((WD[wd], hour, bar_open, clock_open, have))

    if not mismatch:
        print("  ✓ ตรงกันทุกชั่วโมง — market_clock สอดคล้องกับแท่งจริงของโบรกเกอร์")
        return 0
    print(f"  พบจุดที่ไม่ตรง {len(mismatch)} ชั่วโมง (วัน/ชม. UTC · แท่งจริง · market_clock · จำนวนแท่ง)")
    for wd, hour, bar_open, clock_open, have in mismatch[:40]:
        print(f"    {wd} {hour:02d}:00 UTC | แท่งจริง={'เปิด' if bar_open else 'ปิด'} "
              f"| clock={'เปิด' if clock_open else 'ปิด'} | แท่ง={have}")
    print("")
    print("→ ถ้าจุดที่ไม่ตรงอยู่ช่วงเวลามาตรฐาน (พ.ย.–มี.ค.) ให้ปรับ market_hours() ใน market_clock.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
