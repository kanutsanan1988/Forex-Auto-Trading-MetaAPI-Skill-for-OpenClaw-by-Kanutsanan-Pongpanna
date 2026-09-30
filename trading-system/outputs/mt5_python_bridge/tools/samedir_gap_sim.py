# -*- coding: utf-8 -*-
"""samedir_gap_sim.py — จำลอง "เว้นช่วงกี่นาที" ระหว่างไม้ซ้อนทิศทางเดียวกัน (30 ก.ย. 2026)

เจ้าของระบบสั่ง: "การวาง position ที่ซ้ำกันได้ต้องเว้นช่วงเวลาอย่างน้อย 5 นาที… อันนี้มันถี่เกินไป
                 หรือจะเป็น 10 นาทีดีอันไหนดี"

ทดสอบ: ซ้อนสูงสุด 2 ไม้ ทิศทางเดียวกัน + เว้นช่วงขั้นต่ำ G นาที (นับจากไม้ที่เข้าล่าสุด)
       G = 0 (ของเดิม) · 5 · 10 · 15 · 30 · 60 → ดูว่ากี่นาทีให้ผลดีที่สุด
"""
import io
import json
import datetime as dt

AUD = "work/auto_trader_audit.jsonl"
HORIZON_MIN, HOURS_BACK = 240, 96
SL_K, RR, SPREAD_R = 1.25, 1.3, 0.075


def fnum(d, *names):
    for n in names:
        v = d.get(n)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def load():
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=HOURS_BACK)
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
    timeline.sort(); props.sort(key=lambda x: x["t"])
    return props, timeline


def outcome(p, timeline):
    sl, tp = p["sd"] * SL_K, p["sd"] * SL_K * RR
    sgn = 1.0 if p["side"] == "buy" else -1.0
    last_t = last_v = None
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


def stats(seq):
    if not seq:
        return None
    w = sum(1 for r in seq if r > 0)
    eq = peak = dd = 0.0
    for r in seq:
        eq += r; peak = max(peak, eq); dd = min(dd, eq - peak)
    return {"n": len(seq), "wr": 100.0 * w / len(seq), "tot": sum(seq), "dd": dd}


def run(props, timeline, gap_min, max_n=2):
    res = {}
    for i, p in enumerate(props):
        res[i] = outcome(p, timeline)
    out, open_list, last_entry = [], [], None
    for i, p in enumerate(props):
        open_list = [o for o in open_list if o["exit"] > p["t"]]
        r, ex = res[i]
        if r is None:
            continue
        if open_list and any(o["side"] != p["side"] for o in open_list):
            continue                                   # ห้ามถือสองทิศ
        if len(open_list) >= max_n:
            continue
        if last_entry is not None and (p["t"] - last_entry).total_seconds() < gap_min * 60:
            continue                                   # ★ ยังไม่พ้นช่วงเว้นขั้นต่ำ
        out.append(r - SPREAD_R)
        open_list.append({"exit": ex, "side": p["side"]})
        last_entry = p["t"]
    return out


props, timeline = load()
print("══ จำลองช่วงเว้นขั้นต่ำ (ซ้อน 2 ไม้ ทิศทางเดียวกัน) ══")
print("   ข้อมูลจริง %d ชม. · %d ข้อเสนอ · SL 1.5xATR · RR %.1f · หักสเปรด %.3fR\n" % (
    HOURS_BACK, len(props), RR, SPREAD_R))
print("   %-22s %5s %7s %9s %9s %10s" % ("ช่วงเว้นขั้นต่ำ", "ไม้", "ชนะ%", "สุทธิ(R)", "DD(R)", "ต่อไม้"))
best = None
for g in (0, 5, 10, 15, 30, 60):
    st = stats(run(props, timeline, g))
    if not st:
        continue
    tag = "ของเดิม (ไม่มีเว้น)" if g == 0 else "%d นาที" % g
    print("   %-22s %5d %7.0f %+9.1f %9.1f %10.3f"
          % (tag, st["n"], st["wr"], st["tot"], st["dd"], st["tot"] / st["n"]))
    if best is None or st["tot"] > best[1]["tot"]:
        best = (g, st)
print("\n   ★ ดีที่สุด: เว้น %d นาที → สุทธิ %+.1fR (ชนะ %.0f%% · %d ไม้ · DD %.1fR)"
      % (best[0], best[1]["tot"], best[1]["wr"], best[1]["n"], best[1]["dd"]))

# เทียบกับ 1 ไม้ (ไม่มีซ้อน) เพื่อดูว่าเว้นแล้วยังดีกว่าไหม
st1 = stats(run(props, timeline, 0, max_n=1))
print("   เทียบ: 1 ไม้ (ไม่ซ้อน) → สุทธิ %+.1fR (ชนะ %.0f%% · %d ไม้ · DD %.1fR)"
      % (st1["tot"], st1["wr"], st1["n"], st1["dd"]))

print("\n══ ความทนทาน: ครึ่งแรก vs ครึ่งหลัง (ช่วง 5 และ 10 นาที) ══")
mid = props[len(props) // 2]["t"]
h1 = [p for p in props if p["t"] < mid]
h2 = [p for p in props if p["t"] >= mid]
tl1 = [(t, v) for t, v in timeline if t < mid]
tl2 = [(t, v) for t, v in timeline if t >= mid]
for g in (0, 5, 10):
    a, b = stats(run(h1, tl1, g)), stats(run(h2, tl2, g))
    if a and b:
        print("   เว้น %-2d นาที → ครึ่งแรก %+6.1fR (%d ไม้) · ครึ่งหลัง %+6.1fR (%d ไม้)"
              % (g, a["tot"], a["n"], b["tot"], b["n"]))