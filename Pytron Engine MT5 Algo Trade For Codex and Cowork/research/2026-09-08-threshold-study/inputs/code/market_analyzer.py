# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import json
from pathlib import Path

import MetaTrader5 as mt5  # noqa: E402

from strategy_engine import atr, decide_market, ema, rsi, summarize_rows
from openrouter_agents import run_dual_agents


TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
SYMBOL = "XAUUSD.sml"
HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "auto_config.json"


def closed_rows(timeframe: int, symbol_name: str = SYMBOL, count: int = 260):
    raw = mt5.copy_rates_from_pos(symbol_name, timeframe, 0, count + 1)
    if raw is None or len(raw) < 201:
        raise RuntimeError(f"Insufficient closed bars for {symbol_name}: {mt5.last_error()}")
    return raw[:-1]  # The newest MT5 row can still be forming.


def frame_summary(timeframe: int, symbol_name: str = SYMBOL) -> dict:
    return summarize_rows(closed_rows(timeframe, symbol_name))


def market_frames(symbol_name: str = SYMBOL) -> dict:
    return {
        "M1": frame_summary(mt5.TIMEFRAME_M1, symbol_name),
        "M5": frame_summary(mt5.TIMEFRAME_M5, symbol_name),
        "M15": frame_summary(mt5.TIMEFRAME_M15, symbol_name),
        "H1": frame_summary(mt5.TIMEFRAME_H1, symbol_name),
    }


def main() -> int:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    symbol_name = config.get("symbol", SYMBOL)
    if not mt5.initialize(path=TERMINAL):
        print(json.dumps({"ok": False, "error": mt5.last_error()}))
        return 1
    try:
        tick = mt5.symbol_info_tick(symbol_name)
        account = mt5.account_info()
        symbol = mt5.symbol_info(symbol_name)
        if tick is None or account is None or symbol is None:
            raise RuntimeError(f"MT5 market snapshot is incomplete: {mt5.last_error()}")

        frames = market_frames(symbol_name)
        # Read-only view uses the exact same deterministic Python decision path
        # as the live trader; no external service or persisted router state.
        technical_decision = decide_market(frames, config)
        dual_agents = run_dual_agents(config, frames, technical_decision)
        decision = dual_agents["trade_decision"]
        side = decision["side"]
        entry = float(tick.ask if side == "buy" else tick.bid)
        stop_distance = decision["stop_distance"]
        risk_usd = None
        risk_pct = None
        if side is not None and stop_distance is not None:
            order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
            stop = entry - stop_distance if side == "buy" else entry + stop_distance
            calculated = mt5.order_calc_profit(order_type, symbol_name, config["volume"], entry, stop)
            if calculated is None:
                raise RuntimeError(f"Risk calculation failed: {mt5.last_error()}")
            risk_usd = abs(float(calculated))
            risk_pct = 100.0 * risk_usd / float(account.equity)

        risk_budget = float(account.equity) * float(config["max_risk_pct"]) / 100.0
        dollars_per_price_unit = symbol.trade_tick_value / symbol.trade_tick_size * config["volume"]
        max_stop_distance = risk_budget / dollars_per_price_unit
        print(json.dumps({
            "ok": True,
            "mode": (
                "read_only_legacy_h1" if not config["strategy_router"]["enabled"]
                else "read_only_strategy_router"
            ),
            "execution_router_enabled": config["strategy_router"]["enabled"],
            "symbol": symbol_name,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": tick.ask - tick.bid,
            "equity": account.equity,
            "configured_volume": config["volume"],
            "risk_limit_pct": config["max_risk_pct"],
            "risk_budget_usd": risk_budget,
            "max_stop_distance_at_configured_volume": max_stop_distance,
            "decision": decision,
            "technical_decision": technical_decision,
            "dual_agents": dual_agents,
            "candidate_risk_usd": risk_usd,
            "candidate_risk_pct": risk_pct,
            "risk_feasible": risk_pct is None or risk_pct <= float(config["max_risk_pct"]),
            "frames": frames,
            "note": "Read-only closed-bar analysis; no order was prepared or sent.",
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
