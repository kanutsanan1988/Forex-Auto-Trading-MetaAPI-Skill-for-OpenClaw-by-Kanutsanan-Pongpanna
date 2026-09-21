# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import argparse
import bisect
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

from strategy_backtest import close_times, load_closed_rates, result_metrics, simulate_exit
from trade_window_analysis import indicators


HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "auto_config.json"
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"


RSI_PROFILES = (
    (40.0, 70.0, 30.0, 60.0),
    (42.0, 68.0, 32.0, 58.0),
    (45.0, 65.0, 35.0, 55.0),
    (48.0, 68.0, 32.0, 52.0),
    (50.0, 72.0, 28.0, 50.0),
)

SESSIONS_UTC = {
    "all": set(range(24)),
    "london": set(range(7, 17)),
    "london_new_york": set(range(7, 22)),
    "new_york": set(range(12, 22)),
    "asia_london_overlap": set(range(5, 15)),
}


def prepare(config: dict, bars: int):
    symbol = config["symbol"]
    m5 = load_closed_rates(symbol, mt5.TIMEFRAME_M5, bars)
    m15 = load_closed_rates(symbol, mt5.TIMEFRAME_M15, max(1200, bars // 3 + 300))
    h1 = load_closed_rates(symbol, mt5.TIMEFRAME_H1, max(700, bars // 12 + 300))
    m5_series = indicators(m5, 5 * 60)
    m15_series = indicators(m15, 15 * 60)
    h1_series = indicators(h1, 60 * 60)
    m15_closes = [row["close_time"] for row in m15_series]
    h1_closes = [row["close_time"] for row in h1_series]
    records = []
    for index in range(260, len(m5) - 1):
        signal_time = int(m5[index]["time"]) + 5 * 60
        m15_index = bisect.bisect_right(m15_closes, signal_time) - 1
        h1_index = bisect.bisect_right(h1_closes, signal_time) - 1
        if m15_index < 259 or h1_index < 259:
            continue
        m5_summary = m5_series[index]
        records.append({
            "index": index,
            "signal_time": signal_time,
            "utc_hour": datetime.fromtimestamp(signal_time, timezone.utc).hour,
            "trends": (m5_summary["trend"], m15_series[m15_index]["trend"], h1_series[h1_index]["trend"]),
            "rsi": float(m5_summary["rsi14"]),
            "atr": float(m5_summary["atr14"]),
        })
    split_time = int(m5[0]["time"] + 0.7 * (int(m5[-1]["time"]) - int(m5[0]["time"])))
    return m5, records, split_time


def signal_side(record: dict, params: dict) -> str | None:
    trends = record["trends"]
    bullish = trends.count("bullish")
    bearish = trends.count("bearish")
    h1 = trends[2]
    rsi = record["rsi"]
    buy_alignment = bullish >= params["required_votes"] and (
        not params["require_h1_alignment"] or h1 == "bullish"
    )
    sell_alignment = bearish >= params["required_votes"] and (
        not params["require_h1_alignment"] or h1 == "bearish"
    )
    if buy_alignment and params["buy_rsi_min"] <= rsi <= params["buy_rsi_max"]:
        return "buy"
    if sell_alignment and params["sell_rsi_min"] <= rsi <= params["sell_rsi_max"]:
        return "sell"
    return None


def evaluate(records, m5, params, config, spread, dollars_per_unit, equity, start_time=None, end_time=None):
    selected = [
        record for record in records
        if (start_time is None or record["signal_time"] >= start_time)
        and (end_time is None or record["signal_time"] < end_time)
    ]
    trades = []
    last_exit_time = 0
    blocked_risk = 0
    cursor = 0
    previous_raw_side = None
    cooldown = int(float(config["cooldown_minutes"]) * 60)
    while cursor < len(selected):
        record = selected[cursor]
        cursor += 1
        raw_side = signal_side(record, params)
        fresh_signal = raw_side is not None and raw_side != previous_raw_side
        previous_raw_side = raw_side
        if record["signal_time"] < last_exit_time or record["signal_time"] - last_exit_time < cooldown:
            continue
        side = raw_side
        if side is None:
            continue
        if record["utc_hour"] not in SESSIONS_UTC[params["session"]]:
            continue
        if params["fresh_only"] and not fresh_signal:
            continue
        stop_distance = record["atr"] * params["atr_multiplier"]
        risk_pct = 100.0 * stop_distance * dollars_per_unit / equity
        if risk_pct > float(config["max_risk_pct"]):
            blocked_risk += 1
            continue
        entry_index = record["index"] + 1
        entry = float(m5[entry_index]["open"]) + (spread if side == "buy" else 0.0)
        exit_index, r_multiple, exit_reason, _ = simulate_exit(
            m5, entry_index, side, entry, stop_distance,
            params["reward_risk"], spread, 72,
        )
        exit_time = int(m5[exit_index]["time"]) + 5 * 60
        trades.append({
            "entry_time": int(m5[entry_index]["time"]),
            "exit_time": exit_time,
            "side": side,
            "r_multiple": r_multiple,
            "exit_reason": exit_reason,
        })
        last_exit_time = exit_time
        while cursor < len(selected) and selected[cursor]["signal_time"] <= exit_time:
            cursor += 1
    return {**result_metrics(trades), "risk_blocked": blocked_risk}


def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward optimizer for legacy M5/M15/H1 strategy")
    parser.add_argument("--bars", type=int, default=24000)
    args = parser.parse_args()
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not mt5.initialize(path=TERMINAL):
        raise RuntimeError(mt5.last_error())
    try:
        account = mt5.account_info()
        symbol = mt5.symbol_info(config["symbol"])
        if account is None or symbol is None:
            raise RuntimeError(mt5.last_error())
        dollars_per_unit = float(symbol.trade_tick_value) / float(symbol.trade_tick_size) * float(config["volume"])
        m5, records, split_time = prepare(config, args.bars)
        candidates = []
        modes = ((2, False), (2, True), (3, False))
        tested = 0
        for (votes, require_h1), rsi, atr_multiplier, reward_risk, session, fresh_only in itertools.product(
            modes, RSI_PROFILES, (1.0, 1.2, 1.5, 1.8), (1.8, 2.0, 2.2, 2.5), SESSIONS_UTC, (False, True)
        ):
            tested += 1
            params = {
                "required_votes": votes,
                "require_h1_alignment": require_h1,
                "buy_rsi_min": rsi[0], "buy_rsi_max": rsi[1],
                "sell_rsi_min": rsi[2], "sell_rsi_max": rsi[3],
                "atr_multiplier": atr_multiplier,
                "reward_risk": reward_risk,
                "session": session,
                "fresh_only": fresh_only,
            }
            train04 = evaluate(records, m5, params, config, 0.4, dollars_per_unit, float(account.equity), end_time=split_time)
            train06 = evaluate(records, m5, params, config, 0.6, dollars_per_unit, float(account.equity), end_time=split_time)
            if min(train04["trades"], train06["trades"]) < 100:
                continue
            robust_expectancy = min(train04["average_r"], train06["average_r"])
            robust_drawdown = max(train04["max_drawdown_r"], train06["max_drawdown_r"])
            score = robust_expectancy - 0.002 * robust_drawdown
            candidates.append((score, params, train04, train06))
        candidates.sort(key=lambda item: item[0], reverse=True)
        finalists = []
        for score, params, train04, train06 in candidates[:10]:
            test04 = evaluate(records, m5, params, config, 0.4, dollars_per_unit, float(account.equity), start_time=split_time)
            test06 = evaluate(records, m5, params, config, 0.6, dollars_per_unit, float(account.equity), start_time=split_time)
            full04 = evaluate(records, m5, params, config, 0.4, dollars_per_unit, float(account.equity))
            full06 = evaluate(records, m5, params, config, 0.6, dollars_per_unit, float(account.equity))
            finalists.append({
                "training_score": score,
                "params": params,
                "train_spread_0_4": train04,
                "train_spread_0_6": train06,
                "test_spread_0_4": test04,
                "test_spread_0_6": test06,
                "full_spread_0_4": full04,
                "full_spread_0_6": full06,
            })
        winner = finalists[0] if finalists else None
        validation_passed = bool(winner and
            winner["test_spread_0_4"]["trades"] >= 80 and
            winner["test_spread_0_4"]["profit_factor"] > 1.05 and
            winner["test_spread_0_6"]["profit_factor"] >= 1.0 and
            winner["full_spread_0_4"]["profit_factor"] > 1.05 and
            winner["full_spread_0_6"]["profit_factor"] >= 1.0)
        print(json.dumps({
            "ok": True,
            "period_start": datetime.fromtimestamp(int(m5[0]["time"]), timezone.utc).isoformat(),
            "period_end": datetime.fromtimestamp(int(m5[-1]["time"]) + 300, timezone.utc).isoformat(),
            "bars": len(m5),
            "parameter_sets_tested": tested,
            "selection": "ranked only on first 70%; last 30% held out",
            "winner": winner,
            "validation_passed": validation_passed,
            "top_10": finalists,
            "warning": "Optimization can overfit; held-out results do not guarantee future returns.",
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
