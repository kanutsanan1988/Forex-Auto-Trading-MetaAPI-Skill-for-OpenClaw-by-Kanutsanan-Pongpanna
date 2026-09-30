# -*- coding: utf-8 -*-
"""position_protection.py — ใส่ TP/SL ให้ไม้ที่ไม่มี (เจ้าของระบบสั่ง 30 ก.ย. 2026)

คำสั่งเจ้าของระบบ (ถ้อยคำจริง):
  "ทุกครั้งที่มีการเช็คเทรด บางครั้งจะมีมนุษย์ร่วมเทรด เขากดเทรดมักจะไม่มี TP และ SL ด้วย
   (position จะซ้อนกันเพราะมนุษย์กดเทรดร่วม) เอาเป็นว่าทุกครั้งที่มีการเช็คเทรด
   ให้ดูว่า position ไหนไม่มี TP และ SL ก็ให้ใส่ TP และ SL ให้ position นั้นด้วย"

หลักการออกแบบ (ปลอดภัยกับเงินจริงที่สุด):
  1) แตะเฉพาะไม้ของสัญลักษณ์ที่ระบบดูแล (XAUUSD) และ "ยังไม่มี" SL หรือ TP เท่านั้น
     — ไม้ที่มี SL/TP อยู่แล้ว **ห้ามแตะ** (ไม่รื้อของที่ตั้งไว้)
  2) ระยะ SL = ATR(M5) x atr_stop_multiplier (ค่ากลางเดียวกับกลยุทธ์ trend)
     ระยะ TP = ระยะ SL x reward_risk (ค่าเริ่มต้น trend_reward_risk / min_reward_risk)
  3) SL วางจากฝั่งที่ "แคบกว่า" ระหว่าง (ราคาเข้า) กับ (ราคาปัจจุบัน)
     → ถ้าไม้กำไรอยู่ = ล็อกกำไรบางส่วนไปในตัว · ถ้าไม้ขาดทุนอยู่ = ไม่ขยายความเสี่ยงเพิ่ม
  4) เคารพระยะห่างขั้นต่ำของโบรกเกอร์ (trade_stops_level) — ไม่ตั้ง SL/TP ชิดราคาเกินไป
  5) ทุกครั้งที่ลงมือ บันทึก audit event `position_protection` (ไม่มี AI · $0)
"""
from __future__ import annotations

import datetime as dt

PROTECT_HORIZON = 90        # นาที: ถ้าไม้ถูกเปิดมานานกว่านี้และยังไม่มี SL/TP ก็ยังใส่ให้ (ไม่จำกัดเวลา)


def _now():
    return dt.datetime.now(dt.timezone.utc)


def compute_levels(side: str, entry: float, current: float, atr: float,
                   stop_mult: float, rr: float, stops_level: float):
    """คำนวณ SL/TP ของไม้ที่ไม่มี — คืน (sl, tp)"""
    d = max(atr * stop_mult, stops_level * 1.2, 0.01)
    if side == "buy":
        base = max(entry, current)              # ฝั่งที่แคบกว่า (ปลอดภัยกว่า)
        sl = base - d
        tp = current + d * rr
        if sl >= current:                        # ต้องอยู่ใต้ราคาปัจจุบันจริง
            sl = current - d
    else:
        base = min(entry, current)
        sl = base + d
        tp = current - d * rr
        if sl <= current:
            sl = current + d
    return round(sl, 3), round(tp, 3)


def scan(mt5, symbol: str, cfg: dict, dry_run: bool = False, atr: float = None) -> list:
    """ตรวจไม้ทั้งหมด → ใส่ SL/TP ให้ไม้ที่ยังไม่มี · คืนรายการที่ทำ (หรือจะทำ)"""
    out = []
    try:
        positions = mt5.positions_get(symbol=symbol) or []
    except Exception as exc:
        return [{"action": "error", "detail": str(exc)[:120]}]

    # ATR: ใช้ค่าที่ตัวเทรดคำนวณไว้แล้ว (แม่นและปลอดภัยกว่า) — ถ้าไม่มีค่อยคำนวณเอง
    atr_src = "caller"
    try:
        atr = float(atr or 0.0)
    except Exception:
        atr = 0.0
    atr_err = ""
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 30) or []
        if len(rates) >= 15:
            trs = []
            for i in range(1, len(rates)):
                h, l, pc = float(rates[i][2]), float(rates[i][3]), float(rates[i - 1][4])
                trs.append(max(h - l, abs(h - pc), abs(l - pc)))
            atr = sum(trs[-14:]) / float(len(trs[-14:]))
            atr_src = "m5_rates"
    except Exception as exc:
        atr_err = str(exc)[:100]

    stop_mult = float(cfg.get("atr_stop_multiplier", 1.5))
    rr = float(cfg.get("trend_reward_risk", cfg.get("min_reward_risk", 1.3)))

    stops_level = 0.0
    try:
        si = mt5.symbol_info(symbol)
        if si is not None:
            stops_level = float(getattr(si, "trade_stops_level", 0) or 0) * float(getattr(si, "point", 0.01) or 0.01)
    except Exception:
        stops_level = 0.0

    try:
        tick = mt5.symbol_info_tick(symbol)
    except Exception:
        tick = None
    if tick is None:
        return [{"action": "error", "detail": "no tick"}]

    for p in positions:
        side = "buy" if int(p.type) == 0 else "sell"
        entry = float(p.price_open)
        current = float(tick.ask) if side == "buy" else float(tick.bid)
        has_sl = float(getattr(p, "sl", 0) or 0) > 0
        has_tp = float(getattr(p, "tp", 0) or 0) > 0
        if has_sl and has_tp:
            continue
        _atr = atr
        _src = atr_src
        if _atr <= 0:
            # ★ ค่าสำรอง (กันไม้หลุดการป้องกัน): 0.12% ของราคา ≈ ATR(M5) ของทองคำที่เห็นจริง
            _atr = max(current * 0.0012, 0.5)
            _src = "fallback(0.12%%)" + ((" err=" + atr_err) if atr_err else "")
        atr = _atr
        sl, tp = compute_levels(side, entry, current, atr, stop_mult, rr, stops_level)
        want_sl = sl if not has_sl else float(p.sl)
        want_tp = tp if not has_tp else float(p.tp)
        rec = {"action": "would_set" if dry_run else "set", "ticket": int(p.ticket),
               "side": side, "entry": round(entry, 3), "current": round(current, 3),
               "sl": want_sl, "tp": want_tp, "atr": round(atr, 3), "atr_src": _src,
               "had_sl": has_sl, "had_tp": has_tp}
        if not dry_run:
            try:
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": int(p.ticket),
                       "symbol": symbol, "sl": float(want_sl), "tp": float(want_tp)}
                res = mt5.order_send(req)
                rc = getattr(res, "retcode", None)
                rec["retcode"] = rc
                rec["ok"] = rc == mt5.TRADE_RETCODE_DONE
                if not rec["ok"]:
                    rec["detail"] = str(getattr(res, "comment", ""))[:80]
            except Exception as exc:
                rec["ok"] = False
                rec["detail"] = str(exc)[:100]
        out.append(rec)
    return out


def main():     # ทดสอบแบบไม่แตะระบบ: python position_protection.py --dry-run
    import argparse
    import json
    import os
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--symbol", default="XAUUSD")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        print("โหลด MetaTrader5 ไม่ได้: %s" % exc)
        return
    if not mt5.initialize():
        print("เชื่อม MT5 ไม่ได้ (ตัวเทรดอาจถืออยู่) — ลองรันในโปรเซสตัวเทรด")
        return
    cfgp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_config.json")
    try:
        cfg = json.load(open(cfgp, encoding="utf-8"))
    except Exception:
        cfg = {}
    res = scan(mt5, a.symbol, cfg, dry_run=a.dry_run)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:1500])
    mt5.shutdown()


if __name__ == "__main__":
    main()