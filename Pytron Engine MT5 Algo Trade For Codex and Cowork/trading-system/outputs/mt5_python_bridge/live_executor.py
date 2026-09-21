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
import hashlib
import json
import math
import secrets
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PENDING_FILE = ROOT / "work" / "mt5_pending_order.json"

import MetaTrader5 as mt5  # noqa: E402


TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
SYMBOL = "XAUUSD.sml"
MAGIC = 8252026
TOKEN_TTL_SECONDS = 180


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def connect():
    if not mt5.initialize(path=TERMINAL):
        raise RuntimeError(f"initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    symbol = mt5.symbol_info(SYMBOL)
    if not terminal or not terminal.connected:
        raise RuntimeError("MT5 terminal is not connected")
    if not terminal.trade_allowed:
        raise RuntimeError("Terminal automated trading is disabled")
    if not account or not account.trade_allowed:
        raise RuntimeError("Account trading is disabled")
    if not symbol:
        raise RuntimeError(f"Symbol {SYMBOL} is unavailable")
    if not symbol.visible and not mt5.symbol_select(SYMBOL, True):
        raise RuntimeError(f"Could not select {SYMBOL}: {mt5.last_error()}")
    return terminal, account, mt5.symbol_info(SYMBOL)


def volume_is_valid(volume: float, minimum: float, maximum: float, step: float) -> bool:
    if volume < minimum or volume > maximum:
        return False
    units = (volume - minimum) / step
    return math.isclose(units, round(units), abs_tol=1e-8)


def validate(plan: dict, *, max_price_drift: float | None = None) -> tuple[dict, dict]:
    _, account, symbol = connect()
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        raise RuntimeError(f"No current tick: {mt5.last_error()}")
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        raise RuntimeError('MT5 position state unavailable; refusing a new order')
    if positions:
        raise RuntimeError(f"Existing {SYMBOL} position found; refusing to stack")

    volume = float(plan["volume"])
    if not volume_is_valid(volume, symbol.volume_min, symbol.volume_max, symbol.volume_step):
        raise RuntimeError(
            f"Invalid volume {volume}; min={symbol.volume_min}, max={symbol.volume_max}, step={symbol.volume_step}"
        )
    side = plan["side"]
    is_buy = side == "buy"
    entry = float(tick.ask if is_buy else tick.bid)
    sl = float(plan["sl"])
    tp = float(plan["tp"])
    spread = float(tick.ask - tick.bid)
    if spread > float(plan["max_spread"]):
        raise RuntimeError(f"Spread {spread:.3f} exceeds {plan['max_spread']:.3f}")
    if is_buy and not (sl < entry < tp):
        raise RuntimeError("BUY requires SL < latest entry < TP")
    if not is_buy and not (tp < entry < sl):
        raise RuntimeError("SELL requires TP < latest entry < SL")
    if max_price_drift is not None:
        drift = abs(entry - float(plan["entry_snapshot"]))
        if drift > max_price_drift:
            raise RuntimeError(f"Price drift {drift:.3f} exceeds {max_price_drift:.3f}")

    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    risk_value = mt5.order_calc_profit(order_type, SYMBOL, volume, entry, sl)
    if risk_value is None:
        raise RuntimeError(f"Risk calculation failed: {mt5.last_error()}")
    risk_usd = abs(float(risk_value))
    risk_pct = 100.0 * risk_usd / float(account.equity)
    rr = abs(tp - entry) / abs(entry - sl)
    if risk_pct > float(plan["max_risk_pct"]):
        raise RuntimeError(f"Risk {risk_pct:.2f}% exceeds {plan['max_risk_pct']:.2f}%")
    if rr < float(plan["min_rr"]):
        raise RuntimeError(f"Reward/risk {rr:.2f} is below {plan['min_rr']:.2f}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "deviation": int(plan["deviation"]),
        "magic": MAGIC,
        "comment": "codex-confirmed-live",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        raise RuntimeError(f"order_check failed: {check}; last_error={mt5.last_error()}")
    metrics = {
        "entry": entry,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": spread,
        "risk_usd": risk_usd,
        "risk_pct_equity": risk_pct,
        "reward_risk": rr,
        "equity": account.equity,
        "margin_after_check": check.margin,
        "margin_free_after_check": check.margin_free,
    }
    return request, metrics


def plan_digest(plan: dict) -> str:
    stable = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(stable.encode()).hexdigest()[:12]


def prepare(args) -> int:
    plan = {
        "side": args.side,
        "volume": args.volume,
        "sl": args.sl,
        "tp": args.tp,
        "max_risk_pct": args.max_risk_pct,
        "min_rr": args.min_rr,
        "max_spread": args.max_spread,
        "max_price_drift": args.max_price_drift,
        "deviation": args.deviation,
    }
    _request, metrics = validate(plan)
    plan["entry_snapshot"] = metrics["entry"]
    plan["created_at"] = int(time.time())
    plan["expires_at"] = plan["created_at"] + TOKEN_TTL_SECONDS
    plan["token"] = secrets.token_urlsafe(18)
    plan["digest"] = plan_digest({k: v for k, v in plan.items() if k not in ("token", "digest")})
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    emit({
        "ok": True,
        "mode": "PREPARED_NOT_SENT",
        "confirmation_token": plan["token"],
        "digest": plan["digest"],
        "expires_in_seconds": TOKEN_TTL_SECONDS,
        "order": {"side": plan["side"], "volume": plan["volume"], "sl": plan["sl"], "tp": plan["tp"]},
        "metrics": metrics,
        "message": "No order was sent. Confirm this exact order before execute.",
    })
    return 0


def execute(args) -> int:
    if args.confirm_live != "CONFIRM_LIVE_ORDER":
        raise RuntimeError("Missing exact --confirm-live CONFIRM_LIVE_ORDER")
    if not PENDING_FILE.exists():
        raise RuntimeError("No prepared order exists")
    plan = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    if not secrets.compare_digest(args.token, plan["token"]):
        raise RuntimeError("Confirmation token does not match")
    now = int(time.time())
    if now > int(plan["expires_at"]):
        raise RuntimeError("Prepared order expired; analyze and prepare again")
    expected = plan_digest({k: v for k, v in plan.items() if k not in ("token", "digest")})
    if not secrets.compare_digest(expected, plan["digest"]):
        raise RuntimeError("Prepared order file was modified")

    request, metrics = validate(plan, max_price_drift=float(plan["max_price_drift"]))
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
    done = result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL)
    audit = PENDING_FILE.with_name(f"mt5_order_result_{now}.json")
    audit.write_text(json.dumps({"plan": plan, "metrics": metrics, "result": result._asdict()}, default=str, indent=2), encoding="utf-8")
    PENDING_FILE.unlink(missing_ok=True)
    emit({
        "ok": done,
        "mode": "LIVE_ORDER_RESULT",
        "retcode": result.retcode,
        "comment": result.comment,
        "deal": result.deal,
        "order": result.order,
        "volume": result.volume,
        "price": result.price,
        "metrics": metrics,
        "audit_file": str(audit),
    })
    return 0 if done else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two-phase confirmed live MT5 executor")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--side", choices=("buy", "sell"), required=True)
    prep.add_argument("--volume", type=float, default=0.001)
    prep.add_argument("--sl", type=float, required=True)
    prep.add_argument("--tp", type=float, required=True)
    prep.add_argument("--max-risk-pct", type=float, default=2.0)
    prep.add_argument("--min-rr", type=float, default=1.5)
    prep.add_argument("--max-spread", type=float, default=0.6)
    prep.add_argument("--max-price-drift", type=float, default=0.5)
    prep.add_argument("--deviation", type=int, default=50)
    run = sub.add_parser("execute")
    run.add_argument("--token", required=True)
    run.add_argument("--confirm-live", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return prepare(args) if args.command == "prepare" else execute(args)
    except Exception as exc:
        emit({"ok": False, "error": str(exc), "last_error": mt5.last_error()})
        return 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
