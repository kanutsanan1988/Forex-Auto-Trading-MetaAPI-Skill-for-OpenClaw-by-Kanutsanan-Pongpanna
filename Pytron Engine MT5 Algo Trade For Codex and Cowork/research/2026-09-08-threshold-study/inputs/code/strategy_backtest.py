# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

from strategy_engine import decide_market, summarize_rows


HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "auto_config.json"
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"


def load_closed_rates(symbol: str, timeframe: int, count: int):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count + 1)
    if rates is None or len(rates) < 300:
        raise RuntimeError(f"Insufficient historical rates: {mt5.last_error()}")
    return rates[:-1]


def close_times(rates, seconds: int) -> list[int]:
    return [int(row["time"]) + seconds for row in rates]


def result_metrics(trades: list[dict]) -> dict:
    returns = [float(trade["r_multiple"]) for trade in trades]
    wins = [value for value in returns if value > 0.0]
    losses = [value for value in returns if value < 0.0]
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": None if not trades else 100.0 * len(wins) / len(trades),
        "total_r": sum(returns),
        "average_r": None if not trades else sum(returns) / len(trades),
        "profit_factor": None if gross_loss == 0.0 else gross_profit / gross_loss,
        "max_drawdown_r": max_drawdown,
    }


def grouped_metrics(trades: list[dict], key) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for trade in trades:
        groups[str(key(trade))].append(trade)
    return {name: result_metrics(group) for name, group in sorted(groups.items())}


def simulate_exit(rates, start_index: int, side: str, entry: float, stop_distance: float,
                  reward_risk: float, spread: float, max_hold_bars: int) -> tuple[int, float, str, float]:
    sl = entry - stop_distance if side == "buy" else entry + stop_distance
    tp = entry + stop_distance * reward_risk if side == "buy" else entry - stop_distance * reward_risk
    final_index = min(len(rates) - 1, start_index + max_hold_bars - 1)
    for index in range(start_index, final_index + 1):
        row = rates[index]
        if side == "buy":
            stop_hit = float(row["low"]) <= sl
            target_hit = float(row["high"]) >= tp
        else:
            stop_hit = float(row["high"]) + spread >= sl
            target_hit = float(row["low"]) + spread <= tp
        if stop_hit:
            return index, -1.0, "sl", sl
        if target_hit:
            return index, reward_risk, "tp", tp
    close = float(rates[final_index]["close"])
    exit_price = close if side == "buy" else close + spread
    r_multiple = (exit_price - entry) / stop_distance if side == "buy" else (entry - exit_price) / stop_distance
    return final_index, r_multiple, "timeout", exit_price


def run_backtest(config: dict, bars: int, spread: float, max_hold_bars: int) -> dict:
    config = json.loads(json.dumps(config))
    symbol = config["symbol"]
    account = mt5.account_info()
    symbol_info = mt5.symbol_info(symbol)
    if account is None or symbol_info is None:
        raise RuntimeError(f"Account or symbol information unavailable: {mt5.last_error()}")
    risk_equity = float(account.equity)
    dollars_per_price_unit = (
        float(symbol_info.trade_tick_value) / float(symbol_info.trade_tick_size)
        * float(config["volume"])
    )
    m5 = load_closed_rates(symbol, mt5.TIMEFRAME_M5, bars)
    m15 = load_closed_rates(symbol, mt5.TIMEFRAME_M15, max(1200, bars // 3 + 300))
    h1 = load_closed_rates(symbol, mt5.TIMEFRAME_H1, max(700, bars // 12 + 300))
    m15_closes = close_times(m15, 15 * 60)
    h1_closes = close_times(h1, 60 * 60)
    regimes: Counter[str] = Counter()
    no_trade_reasons: Counter[str] = Counter()
    trades: list[dict] = []
    index = 260
    last_trade_exit_time = 0
    cooldown_seconds = int(float(config["cooldown_minutes"]) * 60)
    m15_cache: dict[int, dict] = {}
    h1_cache: dict[int, dict] = {}

    while index < len(m5) - 1:
        signal_close_time = int(m5[index]["time"]) + 5 * 60
        m15_index = bisect.bisect_right(m15_closes, signal_close_time) - 1
        h1_index = bisect.bisect_right(h1_closes, signal_close_time) - 1
        if m15_index < 259 or h1_index < 259:
            index += 1
            continue
        if m15_index not in m15_cache:
            m15_cache[m15_index] = summarize_rows(m15[m15_index - 259:m15_index + 1])
        if h1_index not in h1_cache:
            h1_cache[h1_index] = summarize_rows(h1[h1_index - 259:h1_index + 1])
        frames = {
            "M5": summarize_rows(m5[max(0, index - 259):index + 1]),
            "M15": m15_cache[m15_index],
            "H1": h1_cache[h1_index],
        }
        decision = decide_market(frames, config)
        regime = decision["regime"]["regime"]
        regimes[regime] += 1
        if decision["side"] is None:
            no_trade_reasons[decision["reason"]] += 1
            index += 1
            continue
        if signal_close_time - last_trade_exit_time < cooldown_seconds:
            no_trade_reasons["cooldown"] += 1
            index += 1
            continue

        entry_index = index + 1
        side = decision["side"]
        entry = float(m5[entry_index]["open"]) + (spread if side == "buy" else 0.0)
        stop_distance = float(decision["stop_distance"])
        reward_risk = float(decision["reward_risk"])
        risk_usd = stop_distance * dollars_per_price_unit
        risk_pct = 100.0 * risk_usd / risk_equity
        if spread > float(config["max_spread"]):
            no_trade_reasons["spread limit exceeded"] += 1
            index += 1
            continue
        if risk_pct > float(config["max_risk_pct"]):
            no_trade_reasons["risk limit exceeded at current equity"] += 1
            index += 1
            continue
        exit_index, r_multiple, exit_reason, exit_price = simulate_exit(
            m5, entry_index, side, entry, stop_distance, reward_risk, spread, max_hold_bars
        )
        exit_time = int(m5[exit_index]["time"]) + 5 * 60
        trades.append({
            "signal_time": signal_close_time,
            "entry_time": int(m5[entry_index]["time"]),
            "exit_time": exit_time,
            "strategy": decision["strategy"],
            "regime": regime,
            "side": side,
            "confidence": decision["confidence"],
            "entry": entry,
            "exit": exit_price,
            "stop_distance": stop_distance,
            "reward_risk": reward_risk,
            "risk_usd_at_current_volume": risk_usd,
            "risk_pct_at_current_equity": risk_pct,
            "exit_reason": exit_reason,
            "r_multiple": r_multiple,
        })
        last_trade_exit_time = exit_time
        index = exit_index + 1

    split_time = int(m5[0]["time"] + 0.7 * (int(m5[-1]["time"]) - int(m5[0]["time"])))
    train = [trade for trade in trades if trade["entry_time"] < split_time]
    test = [trade for trade in trades if trade["entry_time"] >= split_time]
    by_strategy = {
        strategy: result_metrics([trade for trade in trades if trade["strategy"] == strategy])
        for strategy in sorted({trade["strategy"] for trade in trades})
    }
    return {
        "symbol": symbol,
        "strategy_mode": "legacy_h1" if not config["strategy_router"]["enabled"] else config["strategy_router"].get("mode"),
        "timeframes": ["M5", "M15", "H1"],
        "bars_requested": bars,
        "bars_loaded": len(m5),
        "period_start_utc": datetime.fromtimestamp(int(m5[0]["time"]), timezone.utc).isoformat(),
        "period_end_utc": datetime.fromtimestamp(int(m5[-1]["time"]) + 300, timezone.utc).isoformat(),
        "assumptions": {
            "spread": spread,
            "max_holding_m5_bars": max_hold_bars,
            "same_bar_sl_and_tp": "SL first (conservative)",
            "entry": "next M5 open; buy pays assumed spread",
            "sell_exit": "assumed ask equals bar bid plus spread",
            "risk_filter_equity": risk_equity,
            "configured_volume": config["volume"],
            "maximum_risk_pct": config["max_risk_pct"],
            "daily_loss_and_consecutive_loss_gates": "not simulated",
        },
        "regime_counts": dict(regimes),
        "no_trade_reasons": dict(no_trade_reasons),
        "all": result_metrics(trades),
        "first_70_pct": result_metrics(train),
        "last_30_pct_out_of_sample": result_metrics(test),
        "by_strategy": by_strategy,
        "first_70_pct_by_strategy": grouped_metrics(train, lambda trade: trade["strategy"]),
        "last_30_pct_by_strategy": grouped_metrics(test, lambda trade: trade["strategy"]),
        "by_side": grouped_metrics(trades, lambda trade: trade["side"]),
        "by_signal_hour_utc": grouped_metrics(
            trades,
            lambda trade: datetime.fromtimestamp(trade["signal_time"], timezone.utc).hour,
        ),
        "last_30_pct_by_signal_hour_utc": grouped_metrics(
            test,
            lambda trade: datetime.fromtimestamp(trade["signal_time"], timezone.utc).hour,
        ),
        "recent_trades": trades[-10:],
        "warning": "Bar backtest is an approximation, not a guarantee of live profitability.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservative closed-bar backtest for the active strategy mode")
    parser.add_argument("--bars", type=int, default=6000)
    parser.add_argument("--spread", type=float, default=0.4)
    parser.add_argument("--max-hold-bars", type=int, default=72)
    args = parser.parse_args()
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not mt5.initialize(path=TERMINAL):
        print(json.dumps({"ok": False, "error": mt5.last_error()}))
        return 1
    try:
        result = run_backtest(config, args.bars, args.spread, args.max_hold_bars)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
