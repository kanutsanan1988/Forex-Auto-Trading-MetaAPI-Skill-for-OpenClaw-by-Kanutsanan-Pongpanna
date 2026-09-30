# -*- coding: utf-8 -*-
"""concurrent_compare.py — เทียบ 2 แนวทาง (30 ก.ย. 2026)

A) "ซ้อนกันได้ N ไม้": สัญญาณใหม่เข้ามา ถ้ายังมีช่องว่างก็เปิดเพิ่ม (ไม่ปิดของเก่า)
B) "สัญญาณใหม่ = ปิดของเก่าทันที": ไม่ว่าจะกำไรหรือขาดทุน แล้วเปิดไม้ใหม่แทน

เจ้าของระบบสั่ง: "อะไรดีกว่ากันลองประเมินสถานการณ์ให้ด้วย"

หลักฐานที่ใช้: ข้อเสนอเทรดจริง + เส้นทางราคาจริงจากบันทึกของตัวเทรดเอง
ต้นทุนที่คิดด้วย (ของจริง): สเปรด ~7.5% ของระยะ SL ต่อการเปิด-ปิดหนึ่งรอบ
ตั้งค่า SL: 1.5xATR (ค่าใหม่ที่เพิ่งใช้) · TP = RR 1.3
"""
import io
import json
import datetime as dt

AUD = "work/auto_trader_audit.jsonl"
HORIZON_MIN = 240
HOURS_BACK = 96
SL_K = 1.25       # SL ใหม่ = 1.25 x ของเดิม (1.2xATR) = 1.5xATR
RR = 1.3
SPREAD_R = 0.075  # ต้นทุนสเปรดต่อรอบ (7.5% ของระยะ SL) — วัดจากข้อมูลจริง


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
        if entry:
            timeline.append((t, entry))
        if side in ("buy", "sell") and entry and sl and abs(entry - sl) > 0.01:
            props.append({"t": t, "side": side, "entry": entry, "sd": abs(entry - sl)})
    timeline.sort()
    props.sort(key=lambda x: x["t"])
    return props, timeline


def sl_price_hit(p, timeline):
    """(ผล R, เวลาออก) ของไม้เดียวตาม SL/TP จริง"""
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
            return -1.0, t
        if mv >= tp:
            return RR, t
    if last_t is None:
        return None, None
    return ((last_v - p["entry"]) * sgn) / sl, last_t


def stats(seq, label):
    if not seq:
        return None
    wins = sum(1 for r in seq if r > 0)
    tot = sum(seq)
    eq = peak = dd = 0.0
    for r in seq:
        eq += r
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    return {"label": label, "n": len(seq), "wr": 100.0 * wins / len(seq),
            "tot": tot, "per": tot / len(seq), "dd": dd}


def run_A(props, timeline, max_n, cost=True):
    """A: ซ้อนได้ N ไม้"""
    out, open_list = [], []
    for p in props:
        open_list = [o for o in open_list if o["exit"] > p["t"]]
        if len(open_list) >= max_n:
            continue
        r, exit_t = sl_price_hit(p, timeline)
        if r is None:
            continue
        out.append(r - (SPREAD_R if cost else 0.0))
        open_list.append({"exit": exit_t})
    return out


def run_B(props, timeline, cost=True):
    """B: สัญญาณใหม่ → ปิดของเก่าทันที (กำไรหรือขาดทุนก็ปิด)"""
    out, open_list = [], []
    for p in props:
        # ปิดทุกไม้ที่ถืออยู่ ณ ราคาของสัญญาณใหม่ (ราคาปัจจุบัน = p['entry'])
        for o in open_list:
            sgn = 1.0 if o["side"] == "buy" else -1.0
            mv = (p["entry"] - o["entry"]) * sgn
            out.append(mv / (o["sd"] * SL_K) - (SPREAD_R if cost else 0.0))
        open_list = [{"side": p["side"], "entry": p["entry"], "sd": p["sd"], "t": p["t"]}]
    # ปิดไม้สุดท้ายที่ราคาสุดท้าย
    last_v = timeline[-1][1] if timeline else None
    for o in open_list:
        sgn = 1.0 if o["side"] == "buy" else -1.0
        mv = (last_v - o["entry"]) * sgn
        out.append(mv / (o["sd"] * SL_K) - (SPREAD_R if cost else 0.0))
    return out


props, timeline = load()
print("══ เทียบ 2 แนวทาง · ข้อมูลจริง %d ชม. · %d ข้อเสนอ ══" % (HOURS_BACK, len(props)))
print("   (หักต้นทุนสเปรด %.3fR ต่อรอบการเปิด-ปิด · SL 1.5xATR · RR %.1f)\n" % (SPREAD_R, RR))
rows = []
for n in (1, 2, 3, 5, 8):
    rows.append(stats(run_A(props, timeline, n), "A) ซ้อนได้สูงสุด %d ไม้" % n))
rows.append(stats(run_B(props, timeline), "B) สัญญาณใหม่ → ปิดของเก่าทันที"))
print("   %-28s %5s %6s %9s %8s %9s" % ("แนวทาง", "ไม้", "ชนะ%", "สุทธิ(R)", "ต่อไม้", "DD(R)"))
for r in rows:
    if r:
        print("   %-28s %5d %5.0f %+9.1f %+8.2f %9.1f"
              % (r["label"], r["n"], r["wr"], r["tot"], r["per"], r["dd"]))

print("\n══ ตรวจความทนทาน: แบ่งครึ่งเวลา (ครึ่งแรก vs ครึ่งหลัง) ══")
mid = props[len(props) // 2]["t"]
h1 = [p for p in props if p["t"] < mid]
h2 = [p for p in props if p["t"] >= mid]
tl1 = [(t, v) for t, v in timeline if t < mid]
tl2 = [(t, v) for t, v in timeline if t >= mid]
for name, fn in (("A) ซ้อน 3 ไม้", lambda ps, tl: run_A(ps, tl, 3)),
                 ("A) ซ้อน 5 ไม้", lambda ps, tl: run_A(ps, tl, 5)),
                 ("B) ปิดของเก่าทันที", run_B)):
    s1, s2 = stats(fn(h1, tl1), "h1"), stats(fn(h2, tl2), "h2")
    if s1 and s2:
        print("   %-20s ครึ่งแรก %+6.1fR (%d ไม้) · ครึ่งหลัง %+6.1fR (%d ไม้)"
              % (name, s1["tot"], s1["n"], s2["tot"], s2["n"]))

print("\n══ สรุปจุดที่ควรระวัง ══")
bA3 = stats(run_A(props, timeline, 3), "a3")
bB = stats(run_B(props, timeline), "b")
print("   ไม้ของ B มี %d ไม้ (churn สูง → เสียสเปรดมาก) เทียบ A(3) = %d ไม้"
      % (bB["n"], bA3["n"]))
print("   ต้นทุนสเปรดรวมของ B ≈ %.1fR · ของ A(3) ≈ %.1fR" % (bB["n"] * SPREAD_R, bA3["n"] * SPREAD_R))