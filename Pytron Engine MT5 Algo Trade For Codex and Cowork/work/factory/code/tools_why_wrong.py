# -*- coding: utf-8 -*-
"""why_wrong.py — วิเคราะห์ "ทำไมทายผิด" + จำลองระยะ SL/TP จากราคาจริง (30 ก.ย. 2026)

เจ้าของระบบสั่ง: หาสาเหตุที่ทายผิดแบบละเอียด + สงสัยกลยุทธ์/ประตู + สงสัยว่าระยะ SL แคบไป
                  (SL ชนแล้วราคาเด้งกลับ) → ให้จำลองสถานการณ์ด้วยข้อมูลจริงก่อนแก้

วิธี: ใช้ "ข้อเสนอเทรด" ทุกครั้งที่ระบบวิเคราะห์ (ทั้งที่เข้าไม้และที่ถูกประตูปิด)
      จับคู่กับ "ราคาจริงตามเวลา" (บันทึกทุกรอบ ~1-2 นาที) แล้วเดินราคาไปข้างหน้า
      → วัด (ก) ทายทิศถูกไหม (ข) ราคาสวนสูงสุด/ไปทางสูงสุด (ค) ถ้าใช้ SL/TP กว้างกว่าเดิม ผลเป็นอย่างไร
"""
import io
import json
import datetime as dt
import collections

AUD = "work/auto_trader_audit.jsonl"
HORIZON_MIN = 240          # เดินราคาไปข้างหน้าได้ไม่เกิน 4 ชม.
HOURS_BACK = 72            # วิเคราะห์ย้อนหลัง 72 ชม.


def fnum(d, *names):
    for n in names:
        v = d.get(n)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=HOURS_BACK)

    proposals = []      # ข้อเสนอเทรด (มีทิศ/ราคาเข้า/SL/TP)
    timeline = []       # (เวลา, ราคา) ใช้จำลองเส้นทางราคา
    taken = set()
    skip_reasons = collections.Counter()
    introspect = {}

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
        ev = d.get("event")
        if ev in ("skip",):
            skip_reasons[str(d.get("reason"))[:60]] += 1
        an = d.get("analysis") or {}
        if not isinstance(an, dict):
            continue
        if ev in ("order_result", "no_trade") and an:
            if ev not in introspect:
                introspect[ev] = sorted(an.keys())
            side = str(an.get("side") or an.get("signal_side") or "").lower()
            entry = fnum(an, "entry", "price", "entry_price", "ask", "bid", "signal_price")
            sl = fnum(an, "sl", "stop_loss", "sl_price")
            tp = fnum(an, "tp", "take_profit", "tp_price")
            if entry:
                timeline.append((t, entry))
            if side in ("buy", "sell") and entry and sl and tp:
                sd = abs(entry - sl)
                td = abs(tp - entry)
                if sd > 0.01:
                    proposals.append({
                        "t": t, "side": side, "entry": entry, "sl": sl, "tp": tp,
                        "sd": sd, "rr": td / sd,
                        "strategy": str(an.get("strategy") or an.get("chosen_strategy") or "?")[:16],
                        "taken": ev == "order_result",
                        "regime": str(an.get("regime") or an.get("market_regime") or "?")[:12],
                    })
                    if ev == "order_result":
                        taken.add(t)

    timeline.sort()
    if not proposals:
        print("⚠ ไม่พบข้อเสนอเทรด (ต้องตรวจชื่อฟิลด์)")
        for k, v in introspect.items():
            print("  %s keys: %s" % (k, ", ".join(v)))
        return

    print("══ 1) ภาพรวม %d ชม. ══" % HOURS_BACK)
    print("   ข้อเสนอเทรดทั้งหมด %d · เข้าไม้จริง %d · ถูกประตูปิด %d"
          % (len(proposals), sum(1 for p in proposals if p["taken"]),
             sum(1 for p in proposals if not p["taken"])))
    print("   ราคาตามเวลา %d จุด (%s → %s)" % (len(timeline),
          timeline[0][0].astimezone(dt.timezone(dt.timedelta(hours=7))).strftime("%d %H:%M"),
          timeline[-1][0].astimezone(dt.timezone(dt.timedelta(hours=7))).strftime("%d %H:%M")))
    print("   เหตุผลที่ประตูปิด (top):")
    for r, n in skip_reasons.most_common(5):
        print("     %-52s %d" % (r, n))

    def path_after(t0):
        return [(t, p) for t, p in timeline if t0 < t <= t0 + dt.timedelta(minutes=HORIZON_MIN)]

    # ── 2) ทายทิศถูกไหม (ไม่สนใจ SL/TP) ──
    for mins in (15, 30, 60):
        ok = tot = 0
        for p in proposals:
            seg = [(t, v) for t, v in path_after(p["t"]) if (t - p["t"]).total_seconds() <= mins * 60]
            if not seg:
                continue
            v = seg[-1][1]
            good = v > p["entry"] if p["side"] == "buy" else v < p["entry"]
            tot += 1
            ok += 1 if good else 0
        if tot:
            print("\n══ 2) ทายทิศถูกไหม (ที่ +%d นาที) ══" % mins)
            print("   ถูก %d/%d = %.0f%%" % (ok, tot, 100.0 * ok / tot))
            break

    # ── 3) ราคาสวนสูงสุด (MAE) เทียบระยะ SL ──
    mae_ratio = []
    for p in proposals:
        seg = path_after(p["t"])
        worst = 0.0
        for t, v in seg:
            adverse = (p["entry"] - v) if p["side"] == "buy" else (v - p["entry"])
            worst = max(worst, adverse)
        # หยุดนับเมื่อเลยเวลา (ใช้ทั้งหน้าต่างเป็น MAE ภายใน 4 ชม.)
        mae_ratio.append(worst / p["sd"])
    mae_ratio.sort()
    n = len(mae_ratio)
    print("\n══ 3) ราคาสวนสูงสุด (MAE) เทียบระยะ SL ══")
    for q in (0.25, 0.5, 0.75, 0.9):
        print("   percentile %2d%%: สวนสูงสุด = %.2f เท่าของระยะ SL" % (int(q * 100), mae_ratio[int(q * (n - 1))]))
    over = sum(1 for m in mae_ratio if m > 1.0) / float(n)
    print("   สวนเกินระยะ SL (โดนชนแน่): %.0f%% ของข้อเสนอทั้งหมด" % (100 * over))

    # ── 4) จำลอง SL กว้างขึ้น × RR ต่างๆ (คิดเป็นหน่วย R · ตั้งขนาดไม้ตามความเสี่ยงคงที่) ──
    print("\n══ 4) จำลอง: ถ้าใช้ SL กว้างขึ้น ผลเป็นอย่างไร (หน่วย R) ══")
    ks = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    rrs = [1.0, 1.3, 1.6, 2.0]
    print("   k = ตัวคูณระยะ SL (1.00 = ปัจจุบัน 1.2×ATR) · ช่อง = กำไรสุทธิรวม (R) / อัตราชนะ")
    print("   %-7s %s" % ("k\\RR", "  ".join("%14s" % ("RR %.1f" % r) for r in rrs)))
    best = None
    for k in ks:
        row = []
        for rr in rrs:
            wins = losses = 0
            net = 0.0
            for p in proposals:
                sl_new = p["sd"] * k
                tp_new = sl_new * rr
                sgn = 1.0 if p["side"] == "buy" else -1.0
                res = None
                for t, v in path_after(p["t"]):
                    mv = (v - p["entry"]) * sgn
                    if mv <= -sl_new:
                        res = -1.0
                        break
                    if mv >= tp_new:
                        res = rr
                        break
                if res is None:
                    continue            # ยังไม่ชนภายใน 4 ชม. → ไม่นับ (ต้องมีข้อมูลครบ)
                if res > 0:
                    wins += 1
                else:
                    losses += 1
                net += res
            tot = wins + losses
            wr = (100.0 * wins / tot) if tot else 0.0
            row.append("%7.1f (%3.0f%%)" % (net, wr))
            if best is None or net > best[0]:
                best = (net, k, rr, wr, tot)
        print("   %-7.2f %s" % (k, "  ".join(row)))
    print("\n   ★ นัยสำคัญ: สูงสุด = k=%.2f · RR=%.1f → สุทธิ %+.1fR จาก %d ไม้ (ชนะ %.0f%%)"
          % (best[1], best[2], best[0], best[4], best[3]))
    base = None
    for p in proposals:
        sl_new, tp_new = p["sd"], p["sd"] * 1.3
        sgn = 1.0 if p["side"] == "buy" else -1.0
        for t, v in path_after(p["t"]):
            mv = (v - p["entry"]) * sgn
            if mv <= -sl_new:
                base = (base or 0) - 1.0
                break
            if mv >= tp_new:
                base = (base or 0) + 1.3
                break
    print("   เทียบของเดิม (k=1.00 · RR=1.3): สุทธิ %+.1fR" % (base or 0.0))

    # ── 5) แยกตามกลยุทธ์/ทิศ ──
    print("\n══ 5) แยกตามกลยุทธ์ (ของเดิม k=1.00 · RR=1.3) ══")
    by = collections.defaultdict(lambda: [0, 0, 0.0])
    for p in proposals:
        sl_new, tp_new = p["sd"], p["sd"] * 1.3
        sgn = 1.0 if p["side"] == "buy" else -1.0
        out = 0.0
        got = False
        for t, v in path_after(p["t"]):
            mv = (v - p["entry"]) * sgn
            if mv <= -sl_new:
                out = -1.0
                got = True
                break
            if mv >= tp_new:
                out = 1.3
                got = True
                break
        if not got:
            continue
        b = by[p["strategy"]]
        b[0 if out > 0 else 1] += 1
        b[2] += out
    for s, (w, l, net) in sorted(by.items(), key=lambda x: -x[1][2]):
        t = w + l
        print("   %-16s ไม้ %3d · ชนะ %3d (%3.0f%%) · สุทธิ %+6.1fR" % (s, t, w, 100.0 * w / t if t else 0, net))


if __name__ == "__main__":
    main()