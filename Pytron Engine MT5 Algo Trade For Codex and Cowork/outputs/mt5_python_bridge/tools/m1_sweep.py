# -*- coding: utf-8 -*-
"""m1_sweep.py — ตัวตรวจจับ "การลากกินรวบ" ระดับ M1 (โหมดเงา / shadow)

คำสั่งเจ้าของระบบ (29 ก.ย. 2026):
  "เจ้ามือลากไปกินรวบ สวนทาง position รายย่อยที่วางไว้เยอะๆ ... ถ้าไม่ใช้ m1 จะไม่ทันเหตุ"
  "นำ m1 ไปคำนวณกลยุทธ์ร่วมด้วย เอาไปร่วม ไม่ใช่ใช้แต่ m1"

★ สถานะ: **โหมดเงา** — คำนวณ + บันทึกเท่านั้น **ไม่มีผลต่อการเทรด** จนกว่าจะพิสูจน์ด้วยข้อมูลจริง
   (เกณฑ์เปิดใช้: ตัดไม้แพ้ออกได้มากกว่าตัดไม้ชนะอย่างชัดเจน)

วิธีจับ (อยู่ในระดับนาที ซึ่ง M5/M15/H1 มองไม่เห็น):
  1) แท่ง M1 ล่าสุดกว้างผิดปกติ  (range >= spike_atr_mult × ATR14(M1))
  2) ไส้ข้างหนึ่งยาวผิดปกติ      (wick >= wick_ratio × range)  = การลากสวนทาง
  3) ปิดกลับเข้าโซน             (close_location กลับไปฝั่งตรงข้ามไส้) = ราคากลับ
  ⇒ ทิศของ sweep = ฝั่งที่ไส้ชี้ (ไส้ล่าง = กวาดลง = สัญญาณกลับขึ้น / ไส้บน = กวาดขึ้น = สัญญาณกลับลง)

ไม่ใช้ AI · $0 · ไม่มี side effect ต่อพอร์ต
"""
from __future__ import annotations

import json
import sys

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - ให้ import ไม่พังเมื่อไม่มี MT5
    mt5 = None  # type: ignore

DEFAULTS = {
    "spike_atr_mult": 2.0,   # ช่วงแท่งต้องกว้างกี่เท่าของ ATR14(M1)
    "wick_ratio": 0.45,      # ไส้ต้องยาวกี่สัดส่วนของช่วงแท่ง
    "min_bars": 30,          # จำนวนแท่งขั้นต่ำที่ใช้คำนวณ
    "bars": 60,
    "confirm_close_location": 0.45,  # ปิดกลับเข้าโซนฝั่งตรงข้ามไส้
}


def _cfg(config: dict | None) -> dict:
    out = dict(DEFAULTS)
    try:
        out.update((config or {}).get("m1_sweep") or {})
    except Exception:
        pass
    return out


def _atr(bars, period: int = 14) -> float:
    """ATR แบบง่าย (ค่าเฉลี่ย true range) ของแท่งที่ปิดแล้ว"""
    if len(bars) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h = float(bars[i]["high"])
        l = float(bars[i]["low"])
        pc = float(bars[i - 1]["close"])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    tail = trs[-period:]
    return sum(tail) / len(tail) if tail else 0.0


def _point_size(symbol_name: str) -> float:
    try:
        info = mt5.symbol_info(symbol_name) if mt5 else None
        if info is not None and float(getattr(info, "point", 0) or 0) > 0:
            return float(info.point)
    except Exception:
        pass
    return 0.01  # ค่าประมาณสำหรับ XAUUSD


def load_m1(symbol_name: str, count: int = 60):
    """ดึงแท่ง M1 (ต้องอยู่ในโปรเซสเดียวกับที่ถือการเชื่อมต่อ MT5)"""
    if mt5 is None:
        return None
    try:
        rates = mt5.copy_rates_from_pos(symbol_name, mt5.TIMEFRAME_M1, 0, max(count, 20))
    except Exception:
        return None
    if rates is None or len(rates) < 5:
        return None
    return rates


def detect(symbol_name: str, config: dict | None = None, rates=None) -> dict:
    """ตรวจสัญญาณ sweep จากแท่ง M1 — คืนค่าเป็น dict (ปลอดภัย: ไม่ throw)"""
    c = _cfg(config)
    out = {"ok": False, "detected": False, "kind": None, "reason": "", "bars": 0}
    try:
        bars = rates if rates is not None else load_m1(symbol_name, int(c["bars"]))
        if bars is None or len(bars) < int(c["min_bars"]):
            out["reason"] = "ข้อมูล M1 ไม่พอ"
            return out
        closed = bars[:-1]           # ตัดแท่งที่ยังไม่ปิด
        if len(closed) < 16:
            out["reason"] = "แท่งปิดไม่พอ"
            return out
        atr = _atr(closed, 14)
        last = closed[-1]
        high = float(last["high"]); low = float(last["low"]); close = float(last["close"]); open_ = float(last["open"])
        rng = high - low
        if atr <= 0 or rng <= 0:
            out["reason"] = "ATR/ช่วงแท่งเป็นศูนย์"
            return out
        ratio = rng / atr
        upper_wick = high - max(open_, close)
        lower_wick = min(open_, close) - low
        close_loc = (close - low) / rng if rng > 0 else 0.5
        out.update({
            "ok": True, "bars": int(len(closed)),
            "atr_m1": round(atr, 4), "range": round(rng, 4), "range_atr_ratio": round(ratio, 3),
            "upper_wick": round(upper_wick, 4), "lower_wick": round(lower_wick, 4),
            "close_location": round(close_loc, 3),
            "last_close": round(close, 4),
        })
        spike = ratio >= float(c["spike_atr_mult"])
        wick_min = float(c["wick_ratio"]) * rng
        # ไส้ล่างยาว + ปิดกลับขึ้น = กวาดโซนขายลงแล้วราคากลับขึ้น (bullish sweep)
        bull = (spike and lower_wick >= wick_min and close_loc >= float(c["confirm_close_location"]))
        # ไส้บนยาว + ปิดกลับลง = กวาดโซนซื้อขึ้นแล้วราคากลับลง (bearish sweep)
        bear = (spike and upper_wick >= wick_min and close_loc <= 1.0 - float(c["confirm_close_location"]))
        if bull or bear:
            out.update({
                "detected": True,
                "kind": "bullish_sweep" if bull else "bearish_sweep",
                "strength": round(ratio, 3),
                "reason": ("ลากกวาด%s %.2f เท่าของ ATR M1 แล้วปิดกลับ (ไส้ %s) — ตามทฤษฎีเจ้ามือกินรวบ"
                           % ("ลง" if bull else "ขึ้น", ratio, "ล่าง" if bull else "บน")),
            })
        else:
            out["reason"] = "ไม่พบลักษณะลากกินรวบ (ช่วง %.2f×ATR · ปิดที่ %.2f)" % (ratio, close_loc)
        return out
    except Exception as exc:  # ต้องไม่ทำให้ตัวเทรดพัง
        out["reason"] = "ข้อผิดพลาด: %s" % exc
        return out


def snapshot(symbol_name: str, config: dict | None = None, rates=None) -> dict:
    """บริบท M1 ณ จุดตัดสินใจ (สำหรับบันทึกไว้ทดสอบย้อนหลัง)"""
    c = _cfg(config)
    try:
        bars = rates if rates is not None else load_m1(symbol_name, 12)
        if bars is None or len(bars) < 6:
            return {"ok": False}
        closed = bars[:-1]
        atr = _atr(closed, 14) if len(closed) > 15 else _atr(bars, min(14, len(bars) - 1))
        tail = closed[-5:]
        closes = [round(float(b["close"]), 4) for b in tail]
        return {
            "ok": True,
            "atr_m1": round(atr, 4),
            "last_close": closes[-1] if closes else None,
            "closes_5": closes,
            "trend_m1": ("up" if len(closes) >= 3 and closes[-1] > closes[0]
                         else "down" if len(closes) >= 3 and closes[-1] < closes[0] else "flat"),
            "spike_atr_mult": float(c["spike_atr_mult"]),
        }
    except Exception:
        return {"ok": False}


def _default_symbol() -> str:
    """สัญลักษณ์จริงของพอร์ต (อ่านจาก auto_config.json) — กันค่าเริ่มต้นผิด เช่น XAUUSD เปล่า

    ★ แก้ 30 ก.ย. 2026 (ที่ปรึกษา): โบรกเกอร์ใช้ชื่อ 'XAUUSD.sml' — ค่าเริ่มต้นเดิม
    ทำให้ตัวตรวจ standalone คืน 'ข้อมูล M1 ไม่พอ' เสมอ (ตรวจ sweep ไม่ได้)
    """
    try:
        import os
        cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_config.json")
        with open(cfg, encoding="utf-8") as fh:
            return str(json.load(fh).get("symbol") or "XAUUSD")
    except Exception:
        return "XAUUSD"


def main() -> int:
    """ทดสอบมือ: python tools/m1_sweep.py [SYMBOL]"""
    symbol = sys.argv[1] if len(sys.argv) > 1 else _default_symbol()
    if mt5 is None:
        print(json.dumps({"ok": False, "error": "ไม่มีโมดูล MetaTrader5"}, ensure_ascii=False))
        return 1
    if not mt5.initialize():
        print(json.dumps({"ok": False, "error": str(mt5.last_error())}, ensure_ascii=False))
        return 1
    try:
        print(json.dumps(snapshot(symbol), ensure_ascii=False, indent=2))
        print(json.dumps(detect(symbol), ensure_ascii=False, indent=2))
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())