# -*- coding: utf-8 -*-
"""concurrent_sim.py — จำลองจำนวนไม้ซ้อนกันที่ให้ผลดีที่สุด (30 ก.ย. 2026)

เจ้าของระบบสั่ง: "ปรับให้มี position ซ้อนกันได้ไม่เกิน 5 ไม้จะดีไหม หรือไม่เกินกี่ไม้
                 ลองคำนวณดูว่าซ้อนกันได้กี่ไม้จะเป็นผลดีที่สุด"

บริบทจริงที่ทำให้ต้องถาม: เหตุผลปิดกั้นอันดับ 1 = "position already open" (1,119 ครั้งใน 72 ชม.)
→ สัญญาณดีจำนวนมากถูกทิ้งเพราะมีไม้ค้างอยู่ 1 ไม้

วิธี: ใช้ข้อเสนอเทรดจริงทุกครั้ง + เส้นทางราคาจริง (บันทึกทุกรอบ ~1-2 นาที)
      จำลองพอร์ตที่มีช่องไม้ N ช่อง → นับว่าได้ไม้กี่ไม้ กำไรสุทธิเท่าไร (หน่วย R)
      และทดสอบ 2 แบบ: (ก) ความเสี่ยงต่อไม้คงที่ (ข) ความเสี่ยงรวมคงที่ (แบ่ง 1/N ต่อไม้)
"""
import io
import json
import datetime as dt

AUD = "work/auto_trader_audit.jsonl"
HORIZON_MIN = 240
HOURS_BACK = 96
SL_K = 1.25          # ค่าใหม่ที่เพิ่งใช้ (SL = 1.25 x ของเดิม = 1.5xATR)
RR = 1.3             # ค่าเดิมที่คงไว้ (กติกา TP >= SL)


def fnum(d, *names):
    for n in names:
        v = d.get(n)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def load():
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=HOURS_BACK)
    props, timeline = [], []
    for ln in io.open(AUD, encoding="utf-8", errors="replace"):
        if '"time"' not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        try:
            t = dt.datetime.fromisoformat(d["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        if t < cutoff:
            continue
        an = d.get("analysis") or {}
        if not isinstance(an, dict):
            continue
        side = str(an.get("side") or an.get("signal_side") or "").lower()
        entry = fnum(an, "entry", "price", "entry_price", "ask", "bid", "signal_price")
        sl = fnum(an, "sl", "stop_loss", "sl_price")
        tp = fnum(an, "tp", "take_profit", "tp_price")
        if entry:
            timeline.append((t, entry))
        if side in ("buy", "sell") and entry and sl and tp and abs(entry - sl) > 0.01:
            props.append({"t": t, "side": side, "entry": entry, "sd": abs(entry - sl),
                          "strategy": str(an.get("strategy") or an.get("chosen_strategy") or "?")[:14]})
    timeline.sort()
    props.sort(key=lambda x: x["t"])
    return props, timeline


def outcome(p, timeline):
    """เดินราคาไปข้างหน้า → (กำไรหน่วย R, เวลาออก, ราคาออก)"""
    sl = p["sd"] * SL_K
    tp = sl * RR
    sgn = 1.0 if p["side"] == "buy" else -1.0
    last_t, last_v = None, None
    for t, v in timeline:
        if t <= p["t"]:
            continue
        if (t - p["t"]).total_seconds() > HORIZON_MIN * 60:
            break
        last_t, last_v = t, v
        mv = (v - p["entry"]) * sgn
        if mv <= -sl:
            return -1.0, t, v
        if mv >= tp:
            return RR, t, v
    if last_t is None:
        return None, None, None
    mv = (last_v - p["entry"]) * sgn
    return mv / sl, last_t, last_v      # ปิดที่ราคาสุดท้าย (ยังไม่ชน)


def run(sim, max_n, dir_cap):
    """เดินเวลา → เปิดไม้เมื่อช่องว่างและไม่ชนเพดานทิศทาง"""
    open_pos = []
    out = []
    for p in props_all:
        open_pos = [o for o in open_pos if o["exit"] > p["t"]]
        if len(open_pos) >= max_n:
            continue
        if dir_cap:
            same = sum(1 for o in open_pos if o["side"] == p["side"])
            if same >= dir_cap:
                continue
        r, exit_t, _ = res[p["key"]]
        if r is None:
            continue
        open_pos.append({"exit": exit_t, "side": p["side"]})
        out.append(r)
    if not out:
        return None
    # ── สถิติ ──
    win = sum(1 for r in out if r > 0)
    total = sum(out)
    # เส้นทุนสะสม → max drawdown
    eq, peak, dd = 0.0, 0.0, 0.0
    for r in out:
        eq += r
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    return {"n": len(out), "win": win, "wr": 100.0 * win / len(out),
            "total": total, "dd": dd, "per": total / len(out)}


props_all, timeline = load()
# คำนวณผลของแต่ละข้อเสนอครั้งเดียว (ใช้ซ้ำทุกแบบจำลอง)
res = {}
for i, p in enumerate(props_all):
    p["key"] = i
    res[i] = outcome(p, timeline)

print("══ ข้อมูลตั้งต้น (%d ชม.) ══" % HOURS_BACK)
print("   ข้อเสนอเทรด %d · มีเส้นทางราคาครบ %d" % (len(props_all), sum(1 for k in res if res[k][0] is not None)))
print("   ใช้ค่า SL ที่เพิ่งแก้ (1.5xATR = %.2fx ของเดิม) · TP = RR %.1f" % (SL_K, RR))
print("\n══ จำลอง: จำนวนไม้ซ้อนกันสูงสุด N ══")
print("   N | ไม้ที่ได้ | ชนะ%  | สุทธิ(R) | ต่อไม้ | DD แย่สุด | สุทธิเมื่อแบ่งความเสี่ยง 1/N")
print("   ---+---------+-------+---------+--------+----------+--------------------------")
base_n = None
for n in (1, 2, 3, 4, 5, 6, 8, 10, 99):
    st = run(None, n, None)
    if not st:
        continue
    norm = st["total"] / float(n if n != 99 else 5)     # ความเสี่ยงรวมคงที่
    print("   %-2s | %7d | %5.0f | %+7.1f | %+6.2f | %8.1f | %+7.1f"
          % ("∞" if n == 99 else n, st["n"], st["wr"], st["total"], st["per"], st["dd"], norm))
    if n == 1:
        base_n = st
print("\n══ เทียบแบบจำกัด 1 ไม้ต่อทิศทาง (กันเสี่ยงทิศเดียวซ้ำ) ══")
for n in (2, 3, 4, 5, 6):
    st = run(None, n, 1)
    if st:
        print("   N=%-2d · ไม้ %3d · ชนะ %3.0f%% · สุทธิ %+6.1fR · ต่อไม้ %+.2fR · DD %.1fR"
              % (n, st["n"], st["wr"], st["total"], st["per"], st["dd"]))
print("\n══ เพดานทิศทางเดียวกัน 2 ไม้ ══")
for n in (3, 4, 5, 6):
    st = run(None, n, 2)
    if st:
        print("   N=%-2d · ไม้ %3d · ชนะ %3.0f%% · สุทธิ %+6.1fR · ต่อไม้ %+.2fR · DD %.1fR"
              % (n, st["n"], st["wr"], st["total"], st["per"], st["dd"]))
if base_n:
    print("\n   เทียบของเดิม (N=1): ไม้ %d · สุทธิ %+.1fR · DD %.1fR" % (base_n["n"], base_n["total"], base_n["dd"]))