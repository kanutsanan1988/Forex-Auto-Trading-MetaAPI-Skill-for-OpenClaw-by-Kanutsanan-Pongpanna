# -*- coding: utf-8 -*-
"""samedir_sim.py — จำลอง "ซ้อนได้เฉพาะไม้ทิศทางเดียวกัน" (30 ก.ย. 2026)

เจ้าของระบบสั่ง: "ลองเช็คดูว่าถ้ามี position ซ้อนกันเฉพาะสิ่งที่ไปในทิศทางเดียวกันได้
                 มันจะเป็นยังไง ประมาณเหตุการณ์ให้ดูด้วยครับ"

นิยามที่จำลอง (ชัดเจน 3 แบบ):
  S(N)        = ซ้อนได้สูงสุด N ไม้ แต่**ทุกไม้ต้องทิศเดียวกัน** — สัญญาณสวนทางถูกข้าม
  S-win(N)    = เหมือน S(N) แต่เพิ่มได้เฉพาะเมื่อไม้ที่ถืออยู่**กำไรอยู่** (pyramid เข้าแข็ง)
  A(N)        = ซ้อนได้ N ไม้ อนุญาตสองทิศ (ของเดิมที่ทดสอบไปแล้ว — ใช้เทียบ)

ค่าที่ใช้: SL 1.5xATR (ค่าใหม่ที่ใช้จริง) · TP = RR 1.3 · หักสเปรด 0.075R ต่อรอบ
"""
import io
import json
import datetime as dt

AUD = "work/auto_trader_audit.jsonl"
HORIZON_MIN = 240
HOURS_BACK = 96
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


def run(props, timeline, max_n, mode):        # mode: "A" | "S" | "Swin"
    res, out = {}, []
    for i, p in enumerate(props):
        r, ex = outcome(p, timeline)
        res[i] = (r, ex)
    open_list = []
    for i, p in enumerate(props):
        open_list = [o for o in open_list if o["exit"] > p["t"]]
        r, ex = res[i]
        if r is None:
            continue
        if mode in ("S", "Swin") and open_list:
            if any(o["side"] != p["side"] for o in open_list):
                continue                                    # สัญญาณสวนทาง → ข้าม
            if mode == "Swin":
                if not all((p["entry"] - o["entry"]) * (1.0 if o["side"] == "buy" else -1.0) > 0
                           for o in open_list):
                    continue                                # ไม้เดิมยังไม่กำไร → ไม่เพิ่ม
        if len(open_list) >= max_n:
            continue
        out.append(r - SPREAD_R)
        open_list.append({"exit": ex, "side": p["side"], "entry": p["entry"]})
    return out


props, timeline = load()
print("══ จำลอง: ซ้อนได้เฉพาะทิศทางเดียวกัน · %d ชม. · %d ข้อเสนอ ══" % (HOURS_BACK, len(props)))
print("   (SL 1.5xATR · RR %.1f · หักสเปรด %.3fR · เดินราคาถึง 4 ชม. ต่อไม้)\n" % (RR, SPREAD_R))
print("   %-30s %5s %6s %9s %9s" % ("แบบ", "ไม้", "ชนะ%", "สุทธิ(R)", "DD(R)"))
rows = {}
for label, n, mode in (("ของเดิม (1 ไม้)", 1, "A"),
                       ("ซ้อนทิศเดียว 2 ไม้", 2, "S"),
                       ("ซ้อนทิศเดียว 3 ไม้", 3, "S"),
                       ("ซ้อนทิศเดียว 5 ไม้", 5, "S"),
                       ("ซ้อนทิศเดียว 8 ไม้", 8, "S"),
                       ("ซ้อนทิศเดียว2(ต้องกำไรก่อน)", 2, "Swin"),
                       ("ซ้อนทิศเดียว3(ต้องกำไรก่อน)", 3, "Swin"),
                       ("ซ้อนทิศเดียว5(ต้องกำไรก่อน)", 5, "Swin"),
                       ("[เทียบ] ซ้อน 2 ไม้ สองทิศ", 2, "A"),
                       ("[เทียบ] ซ้อน 5 ไม้ สองทิศ", 5, "A")):
    st = stats(run(props, timeline, n, mode))
    rows[label] = st
    if st:
        print("   %-30s %5d %6.0f %+9.1f %9.1f" % (label, st["n"], st["wr"], st["tot"], st["dd"]))

print("\n══ ความทนทาน: ครึ่งแรก vs ครึ่งหลัง ══")
mid = props[len(props) // 2]["t"]
h1 = [p for p in props if p["t"] < mid]
h2 = [p for p in props if p["t"] >= mid]
tl1 = [(t, v) for t, v in timeline if t < mid]
tl2 = [(t, v) for t, v in timeline if t >= mid]
for label, n, mode in (("ของเดิม 1 ไม้", 1, "A"), ("ทิศเดียว 2 ไม้", 2, "S"),
                       ("ทิศเดียว 3 ไม้", 3, "S"), ("ทิศเดียว 2(กำไรก่อน)", 2, "Swin"),
                       ("ทิศเดียว 3(กำไรก่อน)", 3, "Swin")):
    a, b = stats(run(h1, tl1, n, mode)), stats(run(h2, tl2, n, mode))
    if a and b:
        print("   %-24s ครึ่งแรก %+6.1fR (%d ไม้) · ครึ่งหลัง %+6.1fR (%d ไม้)"
              % (label, a["tot"], a["n"], b["tot"], b["n"]))

print("\n══ ข้อสังเกตเชิงกลไก ══")
base = rows.get("ของเดิม (1 ไม้)")
for label in ("ซ้อนทิศเดียว 3 ไม้", "ซ้อนทิศเดียว 5 ไม้", "ซ้อนทิศเดียว3(ต้องกำไรก่อน)"):
    st = rows.get(label)
    if base and st:
        print("   %-26s ไม้เพิ่ม %+3d · สุทธิ %+.1fR · DD %+.1fR · กำไรต่อไม้ %.2f → %.2f"
              % (label, st["n"] - base["n"], st["tot"] - base["tot"],
                 st["dd"] - base["dd"], base["tot"] / base["n"], st["tot"] / st["n"]))