# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import argparse
import json
import math

import MetaTrader5 as mt5  # noqa: E402


TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
SYMBOL = "XAUUSD.sml"
MAGIC = 8252026


def fail(message: str, **details) -> int:
    print(json.dumps({"ok": False, "error": message, **details}, ensure_ascii=False, indent=2, default=str))
    return 1


def connect():
    if not mt5.initialize(path=TERMINAL):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    symbol = mt5.symbol_info(SYMBOL)
    if not terminal or not terminal.connected:
        raise RuntimeError("MT5 terminal is not connected")
    if not account:
        raise RuntimeError("Trading account is unavailable")
    if not symbol:
        raise RuntimeError(f"Symbol {SYMBOL} is unavailable")
    if not symbol.visible and not mt5.symbol_select(SYMBOL, True):
        raise RuntimeError(f"Could not select {SYMBOL}: {mt5.last_error()}")
    return terminal, account, mt5.symbol_info(SYMBOL)


def snapshot() -> dict:
    terminal, account, symbol = connect()
    tick = mt5.symbol_info_tick(SYMBOL)
    positions = mt5.positions_get(symbol=SYMBOL) or ()
    return {
        "ok": True,
        "mode": "read_only_snapshot",
        "terminal_trade_allowed": bool(terminal.trade_allowed),
        "account_trade_allowed": bool(account.trade_allowed),
        "balance": account.balance,
        "equity": account.equity,
        "margin_free": account.margin_free,
        "symbol": SYMBOL,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": tick.ask - tick.bid,
        "volume_min": symbol.volume_min,
        "volume_step": symbol.volume_step,
        "positions_on_symbol": len(positions),
    }


def aligned(value: float, minimum: float, step: float) -> bool:
    if value < minimum:
        return False
    units = (value - minimum) / step
    return math.isclose(units, round(units), abs_tol=1e-8)


def check_order(args) -> dict:
    terminal, account, symbol = connect()
    if not terminal.trade_allowed or not account.trade_allowed:
        raise ValueError("Automated trading is not allowed")
    if not aligned(args.volume, symbol.volume_min, symbol.volume_step):
        raise ValueError(
            f"Volume must be >= {symbol.volume_min} and aligned to step {symbol.volume_step}"
        )

    tick = mt5.symbol_info_tick(SYMBOL)
    spread = tick.ask - tick.bid
    if spread > args.max_spread:
        raise ValueError(f"Spread {spread:.3f} exceeds limit {args.max_spread:.3f}")

    is_buy = args.side == "buy"
    entry = tick.ask if is_buy else tick.bid
    if is_buy and not (args.sl < entry < args.tp):
        raise ValueError("BUY requires SL < entry < TP")
    if not is_buy and not (args.tp < entry < args.sl):
        raise ValueError("SELL requires TP < entry < SL")

    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    risk_value = mt5.order_calc_profit(order_type, SYMBOL, args.volume, entry, args.sl)
    if risk_value is None:
        raise ValueError(f"Could not calculate risk: {mt5.last_error()}")
    risk_usd = abs(float(risk_value))
    risk_pct = 100.0 * risk_usd / account.equity
    if risk_pct > args.max_risk_pct:
        raise ValueError(
            f"Risk {risk_pct:.2f}% (${risk_usd:.2f}) exceeds limit {args.max_risk_pct:.2f}%"
        )

    reward_risk = abs(args.tp - entry) / abs(entry - args.sl)
    if reward_risk < args.min_rr:
        raise ValueError(
            f"Reward/risk {reward_risk:.2f} is below minimum {args.min_rr:.2f}"
        )

    positions = mt5.positions_get(symbol=SYMBOL) or ()
    if positions:
        # หมายเหตุ (19 ก.ย. 2026): เครื่องมือนี้เป็น "สั่งไม้ด้วยมือ" จึงเข้มกว่าตัวเทรดออโต้
        # (ตัวเทรดออโต้ยอมให้ถือได้สูงสุด 2 ไม้เพื่อทำ hedge ตาม auto_trader.py)
        raise ValueError(f"Existing {SYMBOL} position found; refusing to stack positions")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": args.volume,
        "type": order_type,
        "price": entry,
        "sl": args.sl,
        "tp": args.tp,
        "deviation": args.deviation,
        "magic": MAGIC,
        "comment": "codex-preview-only",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    checked = mt5.order_check(request)
    return {
        "ok": checked is not None and checked.retcode == 0,
        "mode": "PREVIEW_ONLY_NO_ORDER_SEND",
        "side": args.side,
        "volume": args.volume,
        "entry_snapshot": entry,
        "sl": args.sl,
        "tp": args.tp,
        "spread": spread,
        "risk_usd": risk_usd,
        "risk_pct_equity": risk_pct,
        "reward_risk": reward_risk,
        "order_check": None if checked is None else checked._asdict(),
        "last_error": mt5.last_error(),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Read-only MT5 snapshot and order preview guard")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("snapshot")
    check = sub.add_parser("check")
    check.add_argument("--side", choices=("buy", "sell"), required=True)
    check.add_argument("--volume", type=float, default=0.001)
    check.add_argument("--sl", type=float, required=True)
    check.add_argument("--tp", type=float, required=True)
    check.add_argument("--max-risk-pct", type=float, default=2.0)
    check.add_argument("--max-spread", type=float, default=0.6)
    check.add_argument("--min-rr", type=float, default=1.5)
    check.add_argument("--deviation", type=int, default=50)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        result = snapshot() if args.command == "snapshot" else check_order(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("ok") else 2
    except Exception as exc:
        return fail(str(exc), last_error=mt5.last_error())
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
