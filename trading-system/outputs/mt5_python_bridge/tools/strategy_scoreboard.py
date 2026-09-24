#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""กระดานคะแนนกลยุทธ์ — วัด 'กำไรจริง' รายกลยุทธ์/ทิศทาง และวัดว่าวิวัฒนาการได้ผลไหม

ที่มา (เจ้าของระบบกำหนด 23 ก.ย. 2026): "ความสามารถในการทำกำไรอย่างราบรื่นและยั่งยืน
ขึ้นอยู่กับความสามารถในการปรับตัวและความสามารถด้านวิวัฒนาการของระบบ"

ทำไมต้องมี: ชั้นปรับตัวใน auto_trader.py ตัดสินจาก PF ในหน้าต่าง 40 ไม้ล่าสุด (ในหน่วยความจำ)
แต่ไม่มีที่ให้เห็นว่าการปรับตัว 'ได้ผลจริง' ไหม — ไฟล์นี้ตอบด้วยตัวเลขจริงจากบันทึกไม้ที่ปิด

หลักการ:
  1. ใช้ไม้ที่ปิดจริงเท่านั้น (event=position_closed) — ห้ามสมมติ
  2. แยกตาม 'กลยุทธ์' และ 'ทิศทาง' (ระบบใหม่บันทึกครบตั้งแต่ 19 ก.ย. 2026)
  3. ไม้ที่กลยุทธ์เป็น unknown (รุ่นเก่าก่อนแก้) รายงานแยก ไม่ใช้ตัดสินกลยุทธ์
  4. เปรียบเทียบ 'หน้าต่างล่าสุด' กับ 'ทั้งหมด' → เห็นทิศทางว่าดีขึ้นหรือแย่ลง

ใช้: .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\strategy_scoreboard.py [--window 40] [--json]
"""
import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
AUDIT = os.path.join(ROOT, "work", "auto_trader_audit.jsonl")
STRATS = ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")


def load_closes():
    """อ่านไม้ที่ปิดจริง (สตรีมไฟล์ ไม่กินแรม)"""
    out = []
    if not os.path.exists(AUDIT):
        return out
    with io.open(AUDIT, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"position_closed"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event") != "position_closed":
                continue
            out.append(d)
    return out


def summarize(rows):
    nets = [float(r.get("net") or 0.0) for r in rows]
    if not nets:
        return None
    wins = [n for n in nets if n > 0]
    losses = [n for n in nets if n <= 0]
    gp, gl = sum(wins), abs(sum(losses))
    return {
        "n": len(nets), "net": sum(nets), "avg": sum(nets) / len(nets),
        "win_rate": 100.0 * len(wins) / len(nets),
        "pf": (gp / gl if gl else 99.0),
        "last": rows[-1].get("time", "")[:16],
    }


def line(tag, s):
    if not s:
        return "  %-18s %5s" % (tag, "-")
    return ("  %-18s %5d %+8.2f %+8.3f %6.1f%% %6.2f %s"
            % (tag[:18], s["n"], s["net"], s["avg"], s["win_rate"], s["pf"],
               "✓" if s["net"] > 0 else "✗"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=40, help="ขนาดหน้าต่างล่าสุดต่อกลยุทธ์ (ค่าเดียวกับชั้นปรับตัว)")
    ap.add_argument("--json", action="store_true", help="ส่งออก JSON แทนตาราง")
    ap.add_argument("--compact", action="store_true", help="ย่อเหลือ ~6 บรรทัด (พอดีเพดานข้อความ)")
    a = ap.parse_args()

    rows = load_closes()
    if not rows:
        print("ยังไม่มีไม้ที่ปิดในบันทึก (%s)" % AUDIT)
        return 0

    # จัดกลุ่ม: ทั้งหมด → ตามกลยุทธ์ → ตามทิศทาง → ตาม (กลยุทธ์, ทิศทาง)
    by_strat = collections.defaultdict(list)
    by_side = collections.defaultdict(list)
    by_pair = collections.defaultdict(list)
    for r in rows:
        st = str(r.get("strategy") or "unknown")
        sd = str(r.get("side") or "unknown")
        by_strat[st].append(r)
        by_side[sd].append(r)
        by_pair[(st, sd)].append(r)

    data = {
        "all": summarize(rows),
        "window": int(a.window),
        "by_strategy": {k: summarize(v) for k, v in by_strat.items()},
        "by_strategy_recent": {k: summarize(v[-a.window:]) for k, v in by_strat.items()},
        "by_side": {k: summarize(v) for k, v in by_side.items()},
        "by_pair": {"%s/%s" % k: summarize(v) for k, v in by_pair.items()},
        "period": {"first": rows[0].get("time", "")[:16], "last": rows[-1].get("time", "")[:16]},
        "attributed": sum(1 for r in rows if str(r.get("strategy") or "unknown") in STRATS),
    }

    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if a.compact:
        al = data["all"] or {}
        print("📊 กระดานคะแนนกลยุทธ์: %d ไม้ (%s → %s) | net %+.2f | เฉลี่ย %+.3f | ชนะ %.1f%% | PF %.2f %s"
              % (al.get("n", 0), data["period"]["first"][:16], data["period"]["last"][:16],
                 al.get("net", 0), al.get("avg", 0), al.get("win_rate", 0), al.get("pf", 0),
                 "✓" if al.get("net", 0) > 0 else "✗"))
        real = [(k, v) for k, v in data["by_strategy"].items() if k in STRATS and v]
        if real:
            for k, v in sorted(real, key=lambda x: -x[1]["net"])[:4]:
                r = data["by_strategy_recent"].get(k) or {}
                print("   · %-16s ไม้ %3d | net %+6.2f | PF %5.2f %s | %d ล่าสุด: %+.3f/ไม้ %s"
                      % (k, v["n"], v["net"], v["pf"], "✓" if v["net"] > 0 else "✗",
                         r.get("n", 0), r.get("avg", 0),
                         "ดีขึ้น ✓" if (r.get("avg") or 0) > v["avg"] else "แย่ลง ✗"))
        else:
            print("   · ยังไม่มีไม้ที่ระบุกลยุทธ์ได้ (%d ไม้ = รุ่นเก่าก่อนแก้ 19 ก.ย.)"
                  % (len(rows) - data["attributed"]))
        sides = [(k, v) for k, v in data["by_side"].items() if k in ("buy", "sell") and v]
        if sides:
            print("   · ทิศทาง: " + " · ".join("%s %+.2f (%d ไม้)" % (k, v["net"], v["n"]) for k, v in sides))
        print("   → กลยุทธ์ net ติดลบ+PF<0.85 ควรถูกกด · หน้าต่างล่าสุดดีขึ้น = การปรับตัวได้ผล ✓")
        return 0

    print("📊 กระดานคะแนนกลยุทธ์ — ไม้ปิดจริง %d ไม้ (%s → %s)"
          % (len(rows), data["period"]["first"], data["period"]["last"]))
    print("   ระบุกลยุทธ์ได้ %d ไม้ | ไม่ระบุ (รุ่นเก่า) %d ไม้"
          % (data["attributed"], len(rows) - data["attributed"]))
    print()
    print("  %-18s %5s %8s %8s %7s %6s" % ("ภาพรวม/กลยุทธ์", "ไม้", "net", "เฉลี่ย", "ชนะ%", "PF"))
    print(line("ทั้งหมด", data["all"]))
    print()
    for k in sorted(data["by_strategy"], key=lambda x: -(data["by_strategy"][x] or {}).get("net", -99)):
        s = data["by_strategy"][k]
        note = "" if k in STRATS else "  ← ไม่ใช้ตัดสิน (รุ่นเก่า)"
        print(line(k, s) + note)
        if k in STRATS and s and s["n"] > a.window:
            r = data["by_strategy_recent"][k]
            print("      ↳ %d ไม้ล่าสุด:" % a.window + line("", r).rstrip() + "  " +
                  ("ดีขึ้น ✓" if (r and s and r["avg"] > s["avg"]) else "แย่ลง ✗"))
    print()
    print("=== แยกตามทิศทาง ===")
    for k in sorted(data["by_side"], key=lambda x: -(data["by_side"][x] or {}).get("net", -99)):
        print(line(k, data["by_side"][k]))
    print()
    print("=== แยกตามกลยุทธ์+ทิศทาง (เฉพาะที่ระบุได้) ===")
    for k in sorted(data["by_pair"], key=lambda x: -(data["by_pair"][x] or {}).get("net", -99)):
        if k.split("/")[0] in STRATS:
            print(line(k, data["by_pair"][k]))
    print()
    print("ใช้ประกอบดุลยพินิจ: กลยุทธ์ net ติดลบ+PF<0.85 ควรถูกกด/ปิด (ชั้นปรับตัวทำอัตโนมัติ) · "
          "ถ้าหน้าต่างล่าสุดดีขึ้น = การปรับตัว/วิวัฒนาการได้ผล ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())