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

import bisect
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5  # noqa: E402


TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
SYMBOL = "XAUUSD.sml"
LOOKBACK_DAYS = 60
VOLUME = 0.001
MAX_RISK_PCT = 2.0
ATR_MULTIPLIER = 1.2
MAX_SPREAD_PRICE = 0.6
BANGKOK = timezone(timedelta(hours=7))


def ema_series(values, period):
    alpha = 2.0 / (period + 1)
    output = []
    current = float(values[0])
    for value in values:
        current = alpha * float(value) + (1.0 - alpha) * current
        output.append(current)
    return output


def rsi_series(values, period=14):
    result = [None] * len(values)
    for index in range(period, len(values)):
        changes = [float(values[i]) - float(values[i - 1]) for i in range(index - period + 1, index + 1)]
        gain = sum(max(change, 0.0) for change in changes) / period
        loss = sum(max(-change, 0.0) for change in changes) / period
        result[index] = 100.0 if loss == 0 else 100.0 - 100.0 / (1.0 + gain / loss)
    return result


def atr_series(rows, period=14):
    true_ranges = [0.0]
    for index in range(1, len(rows)):
        previous_close = float(rows[index - 1]["close"])
        high = float(rows[index]["high"])
        low = float(rows[index]["low"])
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    result = [None] * len(rows)
    for index in range(period, len(rows)):
        result[index] = sum(true_ranges[index - period + 1:index + 1]) / period
    return result


def indicators(rows, duration_seconds):
    closes = [float(row["close"]) for row in rows]
    ema9 = ema_series(closes, 9)
    ema21 = ema_series(closes, 21)
    ema50 = ema_series(closes, 50)
    rsi14 = rsi_series(closes)
    atr14 = atr_series(rows)
    output = []
    for index, row in enumerate(rows):
        trend = "neutral"
        if closes[index] > ema9[index] > ema21[index] > ema50[index]:
            trend = "bullish"
        elif closes[index] < ema9[index] < ema21[index] < ema50[index]:
            trend = "bearish"
        output.append({
            "open_time": int(row["time"]),
            "close_time": int(row["time"]) + duration_seconds,
            "close": closes[index],
            "trend": trend,
            "rsi14": rsi14[index],
            "atr14": atr14[index],
            "spread_points": int(row["spread"]),
        })
    return output


def prior_closed(series, close_times, decision_time):
    index = bisect.bisect_right(close_times, decision_time) - 1
    return None if index < 0 else series[index]


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    weight = position - low
    return values[low] * (1 - weight) + values[high] * weight


def main():
    if not mt5.initialize(path=TERMINAL):
        raise RuntimeError(mt5.last_error())
    try:
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=LOOKBACK_DAYS + 5)
        specs = {
            "M5": (mt5.TIMEFRAME_M5, 300),
            "M15": (mt5.TIMEFRAME_M15, 900),
            "M30": (mt5.TIMEFRAME_M30, 1800),
        }
        series = {}
        close_times = {}
        for name, (timeframe, duration) in specs.items():
            raw = mt5.copy_rates_range(SYMBOL, timeframe, start, end)
            if raw is None or len(raw) < 100:
                raise RuntimeError(f"Insufficient {name} data: {mt5.last_error()}")
            series[name] = indicators(raw[:-1], duration)
            close_times[name] = [row["close_time"] for row in series[name]]

        risk_budget = float(account.equity) * MAX_RISK_PCT / 100.0
        dollars_per_price_unit = symbol.trade_tick_value / symbol.trade_tick_size * VOLUME
        max_stop_distance = risk_budget / dollars_per_price_unit
        total = risk_ok = signal_ok = eligible = 0
        risk_hours = Counter()
        eligible_hours = Counter()
        eligible_weekdays = Counter()
        required_equities = []
        signal_required_equities = []
        signal_candidates = []

        for m5 in series["M5"]:
            if m5["atr14"] is None or m5["rsi14"] is None:
                continue
            decision_time = m5["close_time"]
            m15 = prior_closed(series["M15"], close_times["M15"], decision_time)
            m30 = prior_closed(series["M30"], close_times["M30"], decision_time)
            if not m15 or not m30 or m15["rsi14"] is None or m30["rsi14"] is None:
                continue
            total += 1
            stop_distance = float(m5["atr14"] * ATR_MULTIPLIER)
            risk_usd = stop_distance * dollars_per_price_unit
            required_equities.append(risk_usd / (MAX_RISK_PCT / 100.0))
            risk_pass = stop_distance <= max_stop_distance
            spread_pass = m5["spread_points"] * symbol.point <= MAX_SPREAD_PRICE
            trends = [m5["trend"], m15["trend"], m30["trend"]]
            buy = trends.count("bullish") >= 2 and 40 <= m5["rsi14"] < 70
            sell = trends.count("bearish") >= 2 and 30 < m5["rsi14"] <= 60
            signal_pass = buy or sell
            local = datetime.fromtimestamp(decision_time, tz=timezone.utc).astimezone(BANGKOK)
            if risk_pass:
                risk_ok += 1
                risk_hours[local.hour] += 1
            if signal_pass:
                signal_ok += 1
                if spread_pass:
                    required_equity = risk_usd / (MAX_RISK_PCT / 100.0)
                    signal_required_equities.append(required_equity)
                    signal_candidates.append((decision_time, required_equity))
            if risk_pass and signal_pass and spread_pass:
                eligible += 1
                eligible_hours[local.hour] += 1
                eligible_weekdays[local.strftime("%a")] += 1

        hour_rows = []
        for hour in range(24):
            hour_rows.append({
                "bangkok_hour": f"{hour:02d}:00-{(hour + 1) % 24:02d}:00",
                "risk_feasible_bars": risk_hours[hour],
                "fully_eligible_bars": eligible_hours[hour],
            })
        hour_rows.sort(key=lambda row: row["fully_eligible_bars"], reverse=True)
        equity_scenarios = []
        for scenario_equity in (10.73, 15, 20, 25, 30, 36, 40, 50, 60, 75, 100):
            count = 0
            last_counted = 0
            for decision_time, required in signal_candidates:
                if required <= scenario_equity and decision_time - last_counted >= 15 * 60:
                    count += 1
                    last_counted = decision_time
            equity_scenarios.append({
                "equity": scenario_equity,
                "risk_feasible_bar_pct": 100.0 * sum(
                    required <= scenario_equity for required in required_equities
                ) / len(required_equities),
                "eligible_windows_60d_after_15m_cooldown": count,
                "avg_windows_per_30_calendar_days": count / LOOKBACK_DAYS * 30,
            })
        payload = {
            "ok": True,
            "lookback_days": LOOKBACK_DAYS,
            "sample_m5_bars": total,
            "equity": account.equity,
            "risk_budget_2pct": risk_budget,
            "max_stop_distance": max_stop_distance,
            "risk_feasible_bars": risk_ok,
            "signal_bars": signal_ok,
            "fully_eligible_bars": eligible,
            "eligible_rate_pct": 100.0 * eligible / total if total else 0.0,
            "required_equity_for_atr_stop": {
                "p10": percentile(required_equities, 0.10),
                "p25": percentile(required_equities, 0.25),
                "median": percentile(required_equities, 0.50),
                "p75": percentile(required_equities, 0.75),
            },
            "best_bangkok_hours": hour_rows[:8],
            "eligible_by_weekday": dict(eligible_weekdays),
            "equity_scenarios": equity_scenarios,
            "limitations": [
                "Historical bar spread is used; slippage is not modeled.",
                "A 15-minute cooldown is approximated; daily-loss and open-position duration are not simulated.",
                "Past eligibility does not predict profitable future trades.",
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
