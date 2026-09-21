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

import math
from statistics import fmean, pstdev
from typing import Any, Sequence


EPSILON = 1e-12


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _value(row: Any, key: str) -> float:
    return float(row[key])


def ema(values: Sequence[float], period: int) -> float:
    if len(values) == 0:
        raise ValueError("EMA requires at least one value")
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) < period + 1:
        raise ValueError(f"RSI({period}) requires at least {period + 1} closes")
    changes = [float(b) - float(a) for a, b in zip(values[:-1], values[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    avg_gain = fmean(gains[:period])
    avg_loss = fmean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = ((period - 1.0) * avg_gain + gain) / period
        avg_loss = ((period - 1.0) * avg_loss + loss) / period
    if avg_loss <= EPSILON:
        return 100.0 if avg_gain > EPSILON else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + relative_strength)


def true_ranges(rows: Sequence[Any]) -> list[float]:
    if len(rows) == 0:
        return []
    result = [_value(rows[0], "high") - _value(rows[0], "low")]
    for previous, current in zip(rows[:-1], rows[1:]):
        previous_close = _value(previous, "close")
        result.append(max(
            _value(current, "high") - _value(current, "low"),
            abs(_value(current, "high") - previous_close),
            abs(_value(current, "low") - previous_close),
        ))
    return result


def wilder_average(values: Sequence[float], period: int) -> float:
    if len(values) < period:
        raise ValueError(f"Wilder average requires at least {period} values")
    result = fmean(float(value) for value in values[:period])
    for value in values[period:]:
        result = ((period - 1.0) * result + float(value)) / period
    return result


def atr(rows: Sequence[Any], period: int = 14) -> float:
    return wilder_average(true_ranges(rows), period)


def adx(rows: Sequence[Any], period: int = 14) -> float:
    if len(rows) < period * 2 + 1:
        raise ValueError(f"ADX({period}) requires at least {period * 2 + 1} bars")
    ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for previous, current in zip(rows[:-1], rows[1:]):
        up_move = _value(current, "high") - _value(previous, "high")
        down_move = _value(previous, "low") - _value(current, "low")
        plus_dm.append(up_move if up_move > down_move and up_move > 0.0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0.0 else 0.0)
        previous_close = _value(previous, "close")
        ranges.append(max(
            _value(current, "high") - _value(current, "low"),
            abs(_value(current, "high") - previous_close),
            abs(_value(current, "low") - previous_close),
        ))

    smoothed_tr = sum(ranges[:period])
    smoothed_plus = sum(plus_dm[:period])
    smoothed_minus = sum(minus_dm[:period])
    dx_values: list[float] = []
    for index in range(period - 1, len(ranges)):
        if index >= period:
            smoothed_tr = smoothed_tr - smoothed_tr / period + ranges[index]
            smoothed_plus = smoothed_plus - smoothed_plus / period + plus_dm[index]
            smoothed_minus = smoothed_minus - smoothed_minus / period + minus_dm[index]
        if smoothed_tr <= EPSILON:
            dx_values.append(0.0)
            continue
        plus_di = 100.0 * smoothed_plus / smoothed_tr
        minus_di = 100.0 * smoothed_minus / smoothed_tr
        denominator = plus_di + minus_di
        dx_values.append(0.0 if denominator <= EPSILON else 100.0 * abs(plus_di - minus_di) / denominator)
    return wilder_average(dx_values, min(period, len(dx_values)))


def efficiency_ratio(values: Sequence[float], period: int = 20) -> float:
    window = [float(value) for value in values[-(period + 1):]]
    if len(window) < period + 1:
        return 0.0
    direction = abs(window[-1] - window[0])
    movement = sum(abs(b - a) for a, b in zip(window[:-1], window[1:]))
    return 0.0 if movement <= EPSILON else clamp(direction / movement)


def choppiness(rows: Sequence[Any], period: int = 14) -> float:
    window = rows[-period:]
    if len(window) < period:
        return 50.0
    total_range = sum(true_ranges(rows)[-period:])
    price_range = max(_value(row, "high") for row in window) - min(_value(row, "low") for row in window)
    if total_range <= EPSILON or price_range <= EPSILON:
        return 50.0
    return clamp(100.0 * math.log10(total_range / price_range) / math.log10(period), 0.0, 100.0)


def summarize_rows(rows: Sequence[Any], lookback: int = 20) -> dict:
    if len(rows) < 200:
        raise ValueError("A timeframe summary requires at least 200 closed bars")
    closes = [_value(row, "close") for row in rows]
    last_row = rows[-1]
    previous_row = rows[-2]
    last = closes[-1]
    current_atr = atr(rows, 14)
    ema9 = ema(closes[-100:], 9)
    previous_ema9 = ema(closes[-101:-1], 9)
    ema21 = ema(closes[-120:], 21)
    ema50 = ema(closes[-180:], 50)
    ema21_three_bars_ago = ema(closes[-123:-3], 21)
    if last > ema9 > ema21 > ema50:
        trend = "bullish"
    elif last < ema9 < ema21 < ema50:
        trend = "bearish"
    else:
        trend = "neutral"

    bollinger_window = closes[-20:]
    bollinger_mid = fmean(bollinger_window)
    bollinger_std = pstdev(bollinger_window)
    bollinger_upper = bollinger_mid + 2.0 * bollinger_std
    bollinger_lower = bollinger_mid - 2.0 * bollinger_std
    zscore = 0.0 if bollinger_std <= EPSILON else (last - bollinger_mid) / bollinger_std
    previous_bollinger_window = closes[-21:-1]
    previous_bollinger_mid = fmean(previous_bollinger_window)
    previous_bollinger_std = pstdev(previous_bollinger_window)
    previous_zscore = (
        0.0
        if previous_bollinger_std <= EPSILON
        else (closes[-2] - previous_bollinger_mid) / previous_bollinger_std
    )

    prior_rows = rows[-(lookback + 1):-1]
    prior_high = max(_value(row, "high") for row in prior_rows)
    prior_low = min(_value(row, "low") for row in prior_rows)
    price_range = prior_high - prior_low
    range_position = 0.5 if price_range <= EPSILON else clamp((last - prior_low) / price_range)
    earlier_prior_rows = rows[-(lookback + 2):-2]
    earlier_prior_high = max(_value(row, "high") for row in earlier_prior_rows)
    earlier_prior_low = min(_value(row, "low") for row in earlier_prior_rows)
    previous_range = earlier_prior_high - earlier_prior_low
    previous_range_position = (
        0.5
        if previous_range <= EPSILON
        else clamp((_value(previous_row, "close") - earlier_prior_low) / previous_range)
    )
    volume_values = [float(row["tick_volume"]) for row in rows[-21:-1]]
    average_volume = fmean(volume_values) if volume_values else 0.0
    volume_ratio = 1.0 if average_volume <= EPSILON else float(last_row["tick_volume"]) / average_volume
    previous_volume_values = [float(row["tick_volume"]) for row in rows[-22:-2]]
    previous_average_volume = fmean(previous_volume_values) if previous_volume_values else 0.0
    previous_volume_ratio = (
        1.0
        if previous_average_volume <= EPSILON
        else float(previous_row["tick_volume"]) / previous_average_volume
    )
    body = abs(_value(last_row, "close") - _value(last_row, "open"))
    full_range = _value(last_row, "high") - _value(last_row, "low")
    close_location = 0.5 if full_range <= EPSILON else clamp(
        (_value(last_row, "close") - _value(last_row, "low")) / full_range
    )
    previous_full_range = _value(previous_row, "high") - _value(previous_row, "low")
    previous_body = abs(_value(previous_row, "close") - _value(previous_row, "open"))
    previous_close_location = 0.5 if previous_full_range <= EPSILON else clamp(
        (_value(previous_row, "close") - _value(previous_row, "low")) / previous_full_range
    )

    return {
        "time": int(last_row["time"]),
        "open": _value(last_row, "open"),
        "high": _value(last_row, "high"),
        "low": _value(last_row, "low"),
        "close": _value(last_row, "close"),
        "last_closed": last,
        "previous_close": _value(previous_row, "close"),
        "ema9": ema9,
        "previous_ema9": previous_ema9,
        "ema21": ema21,
        "ema50": ema50,
        "ema21_slope_atr": (ema21 - ema21_three_bars_ago) / max(3.0 * current_atr, EPSILON),
        "ema_spread_atr": abs(ema9 - ema50) / max(current_atr, EPSILON),
        "rsi14": rsi(closes, 14),
        "previous_rsi14": rsi(closes[:-1], 14),
        "atr14": current_atr,
        "atr_ratio_14_50": current_atr / max(fmean(true_ranges(rows)[-50:]), EPSILON),
        "adx14": adx(rows, 14),
        "choppiness14": choppiness(rows, 14),
        "efficiency20": efficiency_ratio(closes, 20),
        "trend": trend,
        "prior_high_20": prior_high,
        "prior_low_20": prior_low,
        "prior_high_20_before_previous": earlier_prior_high,
        "prior_low_20_before_previous": earlier_prior_low,
        "range_position_20": range_position,
        "previous_range_position_20": previous_range_position,
        "bollinger_mid20": bollinger_mid,
        "bollinger_upper20": bollinger_upper,
        "bollinger_lower20": bollinger_lower,
        "bollinger_zscore20": zscore,
        "previous_bollinger_zscore20": previous_zscore,
        "volume_ratio20": volume_ratio,
        "previous_volume_ratio20": previous_volume_ratio,
        "body_atr": body / max(current_atr, EPSILON),
        "previous_body_atr": previous_body / max(current_atr, EPSILON),
        "close_location": close_location,
        "previous_close_location": previous_close_location,
        "candle_direction": (
            "bullish" if last > _value(last_row, "open")
            else "bearish" if last < _value(last_row, "open")
            else "neutral"
        ),
    }


def tpsl_stop_atr(settings: dict, config: dict, strategy: str) -> float:
    """SL ต่อกลยุทธ์ = ATR x ค่านี้  (รอบ 10/5 นาที ปรับได้ผ่าน REC set_tpsl -> {strategy}_stop_atr)"""
    try:
        return float(settings.get(f"{strategy}_stop_atr", config["atr_stop_multiplier"]))
    except Exception:
        return float(config.get("atr_stop_multiplier", 1.2))


def tpsl_reward_risk(settings: dict, config: dict, strategy: str) -> float:
    """TP (R:R) ต่อกลยุทธ์ (ปรับได้ผ่าน REC set_tpsl -> {strategy}_reward_risk); ขั้นต่ำ 0.8"""
    try:
        v = float(settings.get(f"{strategy}_reward_risk", config["min_reward_risk"]))
    except Exception:
        v = float(config.get("min_reward_risk", 1.8))
    return max(0.8, v)


def _strategy_settings(config: dict) -> dict:
    return config.get("strategy_router", {})


def m1_trigger_allows(side: str | None, frames: dict, config: dict) -> bool:
    """Use a freshly closed M1 EMA/RSI candle only as entry timing confirmation."""
    m1 = frames.get("M1")
    if m1 is None or config.get("trigger_timeframe", "M5") != "M1" or side is None:
        return True
    settings = config.get("m1_trigger", {})
    buy_ok = (
        m1["previous_close"] <= m1["previous_ema9"]
        and m1["last_closed"] > m1["ema9"]
        and float(settings.get("buy_rsi_min", 42.0)) <= m1["rsi14"] <= float(settings.get("buy_rsi_max", 68.0))
        and m1["candle_direction"] == "bullish"
        and m1["close_location"] >= float(settings.get("min_close_location", 0.55))
    )
    sell_ok = (
        m1["previous_close"] >= m1["previous_ema9"]
        and m1["last_closed"] < m1["ema9"]
        and float(settings.get("sell_rsi_min", 32.0)) <= m1["rsi14"] <= float(settings.get("sell_rsi_max", 58.0))
        and m1["candle_direction"] == "bearish"
        and m1["close_location"] <= 1.0 - float(settings.get("min_close_location", 0.55))
    )
    return buy_ok if side == "buy" else sell_ok


def classify_regime(frames: dict, config: dict) -> dict:
    settings = _strategy_settings(config)
    m5, m15, h1 = frames["M5"], frames["M15"], frames["H1"]
    trends = [m5["trend"], m15["trend"], h1["trend"]]
    bullish_count = trends.count("bullish")
    bearish_count = trends.count("bearish")
    direction = "buy" if bullish_count >= 2 else "sell" if bearish_count >= 2 else None
    directional_alignment = max(bullish_count, bearish_count) / 3.0

    trend_adx_min = float(settings.get("trend_adx_min", 22.0))
    trend_adx = fmean([m15["adx14"], h1["adx14"]])
    trend_adx_score = clamp((trend_adx - 15.0) / max(35.0 - 15.0, EPSILON))
    trend_efficiency = max(m15["efficiency20"], h1["efficiency20"])
    trend_slope = clamp(max(abs(m15["ema21_slope_atr"]), abs(h1["ema21_slope_atr"])) / 0.12)
    trend_score = (
        0.42 * directional_alignment
        + 0.28 * trend_adx_score
        + 0.18 * trend_efficiency
        + 0.12 * trend_slope
    )
    if trend_adx < trend_adx_min:
        trend_score *= 0.85

    range_adx_max = float(settings.get("range_adx_max", 22.0))
    range_adx = fmean([m5["adx14"], m15["adx14"]])
    range_adx_score = clamp((range_adx_max - range_adx) / max(range_adx_max - 10.0, EPSILON))
    range_chop_score = clamp((fmean([m5["choppiness14"], m15["choppiness14"]]) - 42.0) / 20.0)
    range_inefficiency = 1.0 - fmean([m5["efficiency20"], m15["efficiency20"]])
    neutral_score = trends.count("neutral") / 3.0
    range_score = (
        0.35 * range_adx_score
        + 0.28 * range_chop_score
        + 0.22 * range_inefficiency
        + 0.15 * neutral_score
    )

    breakout_buffer = float(settings.get("breakout_buffer_atr", 0.05)) * m5["atr14"]
    breakout_side = None
    breakout_level = None
    earlier_high = m5["prior_high_20_before_previous"]
    earlier_low = m5["prior_low_20_before_previous"]
    if (
        m5["previous_close"] > earlier_high + breakout_buffer
        and m5["last_closed"] > earlier_high + breakout_buffer
    ):
        breakout_side, breakout_level = "buy", earlier_high
    elif (
        m5["previous_close"] < earlier_low - breakout_buffer
        and m5["last_closed"] < earlier_low - breakout_buffer
    ):
        breakout_side, breakout_level = "sell", earlier_low

    breakout_score = 0.0
    if breakout_side is not None:
        minimum_body = float(settings.get("breakout_min_body_atr", 0.45))
        minimum_volume = float(settings.get("breakout_volume_ratio_min", 1.15))
        body_score = clamp(m5["previous_body_atr"] / max(minimum_body, EPSILON))
        volume_score = clamp(m5["previous_volume_ratio20"] / max(minimum_volume, EPSILON))
        aligned = direction == breakout_side
        opposed = direction is not None and direction != breakout_side
        direction_score = 1.0 if aligned else 0.2 if opposed else 0.65
        close_score = (
            m5["previous_close_location"]
            if breakout_side == "buy"
            else 1.0 - m5["previous_close_location"]
        )
        breakout_score = 0.45 + 0.20 * body_score + 0.18 * volume_score + 0.10 * direction_score + 0.07 * close_score

    breakout_threshold = float(settings.get("breakout_regime_min_score", 0.68))
    trend_threshold = float(settings.get("trend_regime_min_score", 0.62))
    range_threshold = float(settings.get("range_regime_min_score", 0.60))
    if breakout_side is not None and breakout_score >= breakout_threshold:
        regime = "breakout"
        confidence = breakout_score
    elif trend_score >= trend_threshold and trend_score >= range_score + 0.05:
        regime = "trend"
        confidence = trend_score
    elif range_score >= range_threshold and range_score >= trend_score + 0.05:
        regime = "range"
        confidence = range_score
    else:
        regime = "transition"
        confidence = clamp(1.0 - max(trend_score, range_score, breakout_score))

    # Directional scores make the evidence auditable instead of collapsing
    # opposing buy/sell pressure into one aggregate strategy score.
    bullish_ratio = bullish_count / 3.0
    bearish_ratio = bearish_count / 3.0
    trend_buy = (
        0.45 * trend_score
        + 0.25 * bullish_ratio
        + 0.15 * clamp((fmean([m5["ema21_slope_atr"], m15["ema21_slope_atr"], h1["ema21_slope_atr"]]) + 0.05) / 0.15)
        + 0.15 * clamp(1.0 - abs(m5["rsi14"] - 55.0) / 25.0)
    )
    trend_sell = (
        0.45 * trend_score
        + 0.25 * bearish_ratio
        + 0.15 * clamp((-fmean([m5["ema21_slope_atr"], m15["ema21_slope_atr"], h1["ema21_slope_atr"]]) + 0.05) / 0.15)
        + 0.15 * clamp(1.0 - abs(m5["rsi14"] - 45.0) / 25.0)
    )
    range_buy = range_score * (
        0.55 * clamp(1.0 - m5["range_position_20"])
        + 0.25 * clamp((50.0 - m5["rsi14"]) / 25.0)
        + 0.20 * clamp(m5["choppiness14"] / 70.0)
    )
    range_sell = range_score * (
        0.55 * clamp(m5["range_position_20"])
        + 0.25 * clamp((m5["rsi14"] - 50.0) / 25.0)
        + 0.20 * clamp(m5["choppiness14"] / 70.0)
    )
    breakout_buy = breakout_score if breakout_side == "buy" else 0.0
    breakout_sell = breakout_score if breakout_side == "sell" else 0.0
    mean_entry_z = float(settings.get("mean_reversion_entry_z", 1.65))
    mean_buy = (
        0.55 * clamp(max(0.0, -m5["bollinger_zscore20"]) / mean_entry_z)
        + 0.25 * clamp((35.0 - m5["rsi14"]) / 20.0)
        + 0.20 * clamp(m5["choppiness14"] / 70.0)
    ) * range_score
    mean_sell = (
        0.55 * clamp(max(0.0, m5["bollinger_zscore20"]) / mean_entry_z)
        + 0.25 * clamp((m5["rsi14"] - 65.0) / 20.0)
        + 0.20 * clamp(m5["choppiness14"] / 70.0)
    ) * range_score

    # Contrarian scores require both a directional market and exhaustion.
    oversold = 0.55 * clamp(max(0.0, -m5["bollinger_zscore20"]) / 2.0) + 0.45 * clamp((40.0 - m5["rsi14"]) / 20.0)
    overbought = 0.55 * clamp(max(0.0, m5["bollinger_zscore20"]) / 2.0) + 0.45 * clamp((m5["rsi14"] - 60.0) / 20.0)
    counter_trend_buy = trend_sell * oversold if direction == "sell" else 0.0
    counter_trend_sell = trend_buy * overbought if direction == "buy" else 0.0

    # A failed breakout closes back inside the previous boundary.  The score
    # rewards distance beyond the level, re-entry strength and rejection.
    failed_down = m5["previous_close"] < earlier_low - breakout_buffer and m5["last_closed"] > earlier_low
    failed_up = m5["previous_close"] > earlier_high + breakout_buffer and m5["last_closed"] < earlier_high
    breakout_reversal_buy = (
        0.45 + 0.25 * oversold + 0.15 * clamp(m5["close_location"]) + 0.15 * clamp(m5["previous_volume_ratio20"] / 1.2)
        if failed_down else 0.0
    )
    breakout_reversal_sell = (
        0.45 + 0.25 * overbought + 0.15 * clamp(1.0 - m5["close_location"]) + 0.15 * clamp(m5["previous_volume_ratio20"] / 1.2)
        if failed_up else 0.0
    )

    return {
        "regime": regime,
        "confidence": clamp(confidence),
        "direction": direction,
        "breakout_side": breakout_side,
        "breakout_level": breakout_level,
        "scores": {
            "trend": clamp(trend_score),
            "range": clamp(range_score),
            "breakout": clamp(breakout_score),
            "trend_buy": clamp(trend_buy),
            "trend_sell": clamp(trend_sell),
            "range_buy": clamp(range_buy),
            "range_sell": clamp(range_sell),
            "breakout_buy": clamp(breakout_buy),
            "breakout_sell": clamp(breakout_sell),
            "mean_reversion_buy": clamp(mean_buy),
            "mean_reversion_sell": clamp(mean_sell),
            "counter_trend_buy": clamp(counter_trend_buy),
            "counter_trend_sell": clamp(counter_trend_sell),
            "breakout_reversal_buy": clamp(breakout_reversal_buy),
            "breakout_reversal_sell": clamp(breakout_reversal_sell),
        },
        "evidence": {
            "timeframe_trends": {name: frames[name]["trend"] for name in ("M5", "M15", "H1")},
            "adx": {name: frames[name]["adx14"] for name in ("M5", "M15", "H1")},
            "atr_m5": m5["atr14"],
            "rsi_m5": m5["rsi14"],
            "choppiness_m5": m5["choppiness14"],
            "volume_ratio_m5": m5["volume_ratio20"],
            "range_position_m5": m5["range_position_20"],
        },
    }


def _proposal(
    strategy: str,
    *,
    eligible: bool,
    side: str | None = None,
    confidence: float = 0.0,
    reason: str,
    stop_distance: float | None = None,
    reward_risk: float | None = None,
    strength: float | None = None,
    buy_score: float | None = None,
    sell_score: float | None = None,
) -> dict:
    resolved_strength = clamp(confidence if strength is None else strength)
    resolved_buy = resolved_strength if buy_score is None and side == "buy" else (0.0 if buy_score is None else buy_score)
    resolved_sell = resolved_strength if sell_score is None and side == "sell" else (0.0 if sell_score is None else sell_score)
    return {
        "strategy": strategy,
        "eligible": bool(eligible),
        "side": side,
        "confidence": clamp(confidence),
        "strength": resolved_strength,
        "buy_score": clamp(resolved_buy),
        "sell_score": clamp(resolved_sell),
        "reason": reason,
        "stop_distance": stop_distance,
        "reward_risk": reward_risk,
    }


def trend_agent(frames: dict, regime: dict, config: dict) -> dict:
    settings = _strategy_settings(config)
    m5 = frames["M5"]
    side = regime["direction"]
    if regime["regime"] != "trend" or side is None:
        return _proposal("trend", eligible=False, strength=regime["scores"]["trend"], buy_score=regime["scores"]["trend_buy"], sell_score=regime["scores"]["trend_sell"], reason="market regime is not a confirmed trend")
    # A trend entry must be a fresh pullback-resumption cross on the closed
    # M5 candle: price was on the pullback side of EMA9, then closed back
    # through EMA9 in the trend direction.  Keeping this as a named signal
    # makes it visible in diagnostics and prevents a score-only router from
    # silently bypassing the Trend Agent's entry condition.
    buy_trigger = (
        m5["previous_close"] <= m5["previous_ema9"]
        and m5["last_closed"] > m5["ema9"]
    )
    sell_trigger = (
        m5["previous_close"] >= m5["previous_ema9"]
        and m5["last_closed"] < m5["ema9"]
    )
    buy_setup_ok = (
        side == "buy"
        and m5["trend"] == "bullish"
        and frames["M15"]["trend"] == "bullish"
        and frames["H1"]["trend"] != "bearish"
        and 46.0 <= m5["rsi14"] <= 64.0
        and m5["candle_direction"] == "bullish"
        and m5["body_atr"] >= 0.18
        and m5["close_location"] >= 0.60
        and m5["volume_ratio20"] >= 0.80
    )
    sell_setup_ok = (
        side == "sell"
        and m5["trend"] == "bearish"
        and frames["M15"]["trend"] == "bearish"
        and frames["H1"]["trend"] != "bullish"
        and 36.0 <= m5["rsi14"] <= 54.0
        and m5["candle_direction"] == "bearish"
        and m5["body_atr"] >= 0.18
        and m5["close_location"] <= 0.40
        and m5["volume_ratio20"] >= 0.80
    )
    buy_ok = buy_setup_ok and buy_trigger
    sell_ok = sell_setup_ok and sell_trigger
    if not (buy_ok or sell_ok):
        trigger = buy_trigger if side == "buy" else sell_trigger
        setup_ok = buy_setup_ok if side == "buy" else sell_setup_ok
        rsi_ok = 46.0 <= m5["rsi14"] <= 64.0 if side == "buy" else 36.0 <= m5["rsi14"] <= 54.0
        candle_ok = m5["candle_direction"] == ("bullish" if side == "buy" else "bearish")
        close_ok = m5["close_location"] >= 0.60 if side == "buy" else m5["close_location"] <= 0.40
        strength = 0.40 * regime["confidence"] + 0.20 * float(trigger) + 0.15 * float(rsi_ok) + 0.15 * float(candle_ok) + 0.10 * float(close_ok)
        proposal = _proposal(
            "trend", eligible=False, side=side, strength=strength,
            reason="no fresh M5 pullback-resumption cross with valid RSI",
            stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "trend") if setup_ok else None,
            reward_risk=tpsl_reward_risk(settings, config, "trend") if setup_ok else None,
        )
        proposal["pullback_resumption_cross"] = bool(trigger)
        proposal["entry_checks_without_cross"] = bool(setup_ok)
        return proposal
    momentum = clamp(abs(m5["ema21_slope_atr"]) / 0.10)
    confidence = 0.65 * regime["confidence"] + 0.20 * momentum + 0.15 * clamp(m5["adx14"] / 35.0)
    proposal = _proposal(
        "trend", eligible=True, side=side, confidence=confidence,
        reason="EMA alignment, ADX and M5 RSI confirm trend continuation",
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "trend"),
        reward_risk=tpsl_reward_risk(settings, config, "trend"),
        strength=confidence,
    )
    proposal["pullback_resumption_cross"] = True
    proposal["entry_checks_without_cross"] = True
    return proposal


def range_agent(frames: dict, regime: dict, config: dict) -> dict:
    settings = _strategy_settings(config)
    m5, m15 = frames["M5"], frames["M15"]
    if regime["regime"] != "range":
        return _proposal("range", eligible=False, strength=regime["scores"]["range"], buy_score=regime["scores"]["range_buy"], sell_score=regime["scores"]["range_sell"], reason="market regime is not a confirmed horizontal range")
    edge = float(settings.get("range_edge_fraction", 0.22))
    buy_ok = (
        m5["previous_range_position_20"] <= edge
        and m5["range_position_20"] <= edge * 1.5
        and m5["previous_rsi14"] <= float(settings.get("range_rsi_buy_max", 36.0))
        and m5["rsi14"] > m5["previous_rsi14"]
        and m5["previous_bollinger_zscore20"] <= -1.2
        and m5["bollinger_zscore20"] > m5["previous_bollinger_zscore20"]
        and m5["candle_direction"] == "bullish"
        and m5["close_location"] >= 0.58
    )
    sell_ok = (
        m5["previous_range_position_20"] >= 1.0 - edge
        and m5["range_position_20"] >= 1.0 - edge * 1.5
        and m5["previous_rsi14"] >= float(settings.get("range_rsi_sell_min", 64.0))
        and m5["rsi14"] < m5["previous_rsi14"]
        and m5["previous_bollinger_zscore20"] >= 1.2
        and m5["bollinger_zscore20"] < m5["previous_bollinger_zscore20"]
        and m5["candle_direction"] == "bearish"
        and m5["close_location"] <= 0.42
    )
    side = "buy" if buy_ok else "sell" if sell_ok else None
    if side is None or m15["trend"] != "neutral":
        edge_score = 1.0 - abs(m5["range_position_20"] - 0.5) * 2.0
        strength = 0.55 * regime["confidence"] + 0.25 * clamp(edge_score) + 0.20 * clamp(m5["choppiness14"] / 70.0)
        return _proposal("range", eligible=False, side=side, strength=strength, reason="price is not at a validated range edge or M15 is directional")
    # ขายที่ขอบบนของกรอบ (range_position สูง) / ซื้อที่ขอบล่าง — คะแนนคุณภาพขอบ
    edge_quality = m5["range_position_20"] if side == "sell" else 1.0 - m5["range_position_20"]
    confidence = 0.65 * regime["confidence"] + 0.20 * clamp(edge_quality) + 0.15 * clamp(m5["choppiness14"] / 65.0)
    return _proposal(
        "range", eligible=True, side=side, confidence=confidence,
        reason="price reached a horizontal range edge with RSI confirmation",
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "range"),
        reward_risk=tpsl_reward_risk(settings, config, "range"),
        strength=confidence,
    )


def mean_reversion_agent(frames: dict, regime: dict, config: dict) -> dict:
    settings = _strategy_settings(config)
    m5 = frames["M5"]
    regime_scores = regime["scores"]
    if regime["regime"] != "range":
        return _proposal("mean_reversion", eligible=False, strength=max(regime_scores["mean_reversion_buy"], regime_scores["mean_reversion_sell"]), buy_score=regime_scores["mean_reversion_buy"], sell_score=regime_scores["mean_reversion_sell"], reason="mean reversion is disabled outside a range regime")
    entry_z = float(settings.get("mean_reversion_entry_z", 1.65))
    buy_ok = (
        m5["previous_bollinger_zscore20"] <= -entry_z
        and m5["bollinger_zscore20"] > m5["previous_bollinger_zscore20"] + 0.12
        and m5["previous_rsi14"] <= 33.0
        and m5["rsi14"] > m5["previous_rsi14"]
        and m5["candle_direction"] == "bullish"
    )
    sell_ok = (
        m5["previous_bollinger_zscore20"] >= entry_z
        and m5["bollinger_zscore20"] < m5["previous_bollinger_zscore20"] - 0.12
        and m5["previous_rsi14"] >= 67.0
        and m5["rsi14"] < m5["previous_rsi14"]
        and m5["candle_direction"] == "bearish"
    )
    side = "buy" if buy_ok else "sell" if sell_ok else None
    if side is None:
        strength = 0.50 * regime["confidence"] + 0.30 * clamp(abs(m5["bollinger_zscore20"]) / max(entry_z, 0.01)) + 0.20 * clamp(m5["choppiness14"] / 70.0)
        return _proposal("mean_reversion", eligible=False, strength=strength, buy_score=regime_scores["mean_reversion_buy"], sell_score=regime_scores["mean_reversion_sell"], reason="Bollinger z-score and RSI are not extreme enough")
    extreme_score = clamp(abs(m5["bollinger_zscore20"]) / 2.5)
    confidence = 0.58 * regime["confidence"] + 0.27 * extreme_score + 0.15 * clamp(m5["choppiness14"] / 65.0)
    return _proposal(
        "mean_reversion", eligible=True, side=side, confidence=confidence,
        reason="statistical price deviation and RSI support a return toward the mean",
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "mean_reversion"),
        reward_risk=tpsl_reward_risk(settings, config, "mean_reversion"),
        strength=confidence,
        buy_score=regime_scores["mean_reversion_buy"],
        sell_score=regime_scores["mean_reversion_sell"],
    )


def breakout_agent(frames: dict, regime: dict, config: dict) -> dict:
    settings = _strategy_settings(config)
    m5, m15, h1 = frames["M5"], frames["M15"], frames["H1"]
    side = regime["breakout_side"]
    if regime["regime"] != "breakout" or side is None:
        level = regime.get("breakout_level")
        distance = 0.0 if level is None else abs(m5["last_closed"] - float(level)) / max(m5["atr14"], EPSILON)
        return _proposal("breakout", eligible=False, side=side, strength=0.45 * regime["scores"]["breakout"] + 0.55 * clamp(distance), buy_score=regime["scores"]["breakout_buy"], sell_score=regime["scores"]["breakout_sell"], reason="no confirmed close beyond the prior 20-bar boundary")
    rsi_ok = 52.0 <= m5["rsi14"] <= 80.0 if side == "buy" else 20.0 <= m5["rsi14"] <= 48.0
    close_ok = (
        m5["previous_close_location"] >= 0.75
        if side == "buy"
        else m5["previous_close_location"] <= 0.25
    )
    body_ok = m5["previous_body_atr"] >= float(settings.get("breakout_min_body_atr", 0.65))
    volume_ok = m5["previous_volume_ratio20"] >= float(settings.get("breakout_volume_ratio_min", 1.30))
    hold_ok = (
        m5["last_closed"] >= float(regime["breakout_level"])
        and m5["close_location"] >= 0.45
        if side == "buy"
        else m5["last_closed"] <= float(regime["breakout_level"])
        and m5["close_location"] <= 0.55
    )
    direction_ok = (
        m15["trend"] == ("bullish" if side == "buy" else "bearish")
        and h1["trend"] != ("bearish" if side == "buy" else "bullish")
    )
    if not rsi_ok or not close_ok or not body_ok or not volume_ok or not hold_ok or not direction_ok:
        return _proposal(
            "breakout", eligible=False, side=side,
            strength=regime["scores"]["breakout"],
            buy_score=regime["scores"]["breakout_buy"],
            sell_score=regime["scores"]["breakout_sell"],
            reason="breakout strength, volume or higher-timeframe confirmation failed",
        )
    confidence = (
        0.65 * regime["confidence"]
        + 0.20 * clamp(m5["previous_volume_ratio20"] / float(settings.get("breakout_volume_ratio_min", 1.30)))
        + 0.15 * clamp(m5["previous_body_atr"] / float(settings.get("breakout_min_body_atr", 0.65)))
    )
    return _proposal(
        "breakout", eligible=True, side=side, confidence=confidence,
        reason="closed-bar breakout, candle strength and momentum are confirmed",
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "breakout"),
        reward_risk=tpsl_reward_risk(settings, config, "breakout"),
        strength=confidence,
    )


def counter_trend_agent(frames: dict, regime: dict, config: dict) -> dict:
    """Fade an exhausted established trend only after a closed-bar rejection."""
    settings = _strategy_settings(config)
    m5 = frames["M5"]
    scores = regime["scores"]
    if regime.get("direction") not in {"buy", "sell"} or "counter_trend_buy" not in scores:
        return _proposal("counter_trend", eligible=False, reason="counter-trend evidence unavailable")
    buy_ok = (
        regime["direction"] == "sell"
        and m5["previous_bollinger_zscore20"] <= -float(settings.get("counter_trend_z", 1.6))
        and m5["bollinger_zscore20"] > m5["previous_bollinger_zscore20"]
        and m5["previous_rsi14"] <= float(settings.get("counter_trend_rsi_low", 32.0))
        and m5["rsi14"] > m5["previous_rsi14"]
        and m5["candle_direction"] == "bullish" and m5["close_location"] >= 0.60
    )
    sell_ok = (
        regime["direction"] == "buy"
        and m5["previous_bollinger_zscore20"] >= float(settings.get("counter_trend_z", 1.6))
        and m5["bollinger_zscore20"] < m5["previous_bollinger_zscore20"]
        and m5["previous_rsi14"] >= float(settings.get("counter_trend_rsi_high", 68.0))
        and m5["rsi14"] < m5["previous_rsi14"]
        and m5["candle_direction"] == "bearish" and m5["close_location"] <= 0.40
    )
    side = "buy" if buy_ok else "sell" if sell_ok else None
    score = scores["counter_trend_buy"] if side == "buy" else scores["counter_trend_sell"] if side == "sell" else 0.0
    return _proposal(
        "counter_trend", eligible=side is not None, side=side, confidence=score,
        strength=max(scores["counter_trend_buy"], scores["counter_trend_sell"]),
        buy_score=scores["counter_trend_buy"], sell_score=scores["counter_trend_sell"],
        reason=("trend exhaustion, RSI/Bollinger reversal and rejection candle confirmed" if side else "counter-trend exhaustion reversal is not confirmed"),
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "counter_trend") if side else None,
        reward_risk=tpsl_reward_risk(settings, config, "counter_trend") if side else None,
    )


def breakout_reversal_agent(frames: dict, regime: dict, config: dict) -> dict:
    """Trade opposite a failed breakout only after price closes back in range."""
    settings = _strategy_settings(config)
    m5 = frames["M5"]
    scores = regime["scores"]
    if "breakout_reversal_buy" not in scores or "prior_high_20_before_previous" not in m5:
        return _proposal("breakout_reversal", eligible=False, reason="failed-breakout evidence unavailable")
    buffer = float(settings.get("breakout_buffer_atr", 0.05)) * m5["atr14"]
    high = m5["prior_high_20_before_previous"]
    low = m5["prior_low_20_before_previous"]
    buy_ok = (
        m5["previous_close"] < low - buffer and m5["last_closed"] > low
        and m5["candle_direction"] == "bullish" and m5["close_location"] >= 0.55
        and m5["rsi14"] > m5["previous_rsi14"]
    )
    sell_ok = (
        m5["previous_close"] > high + buffer and m5["last_closed"] < high
        and m5["candle_direction"] == "bearish" and m5["close_location"] <= 0.45
        and m5["rsi14"] < m5["previous_rsi14"]
    )
    side = "buy" if buy_ok else "sell" if sell_ok else None
    score = scores["breakout_reversal_buy"] if side == "buy" else scores["breakout_reversal_sell"] if side == "sell" else 0.0
    return _proposal(
        "breakout_reversal", eligible=side is not None, side=side, confidence=score,
        strength=max(scores["breakout_reversal_buy"], scores["breakout_reversal_sell"]),
        buy_score=scores["breakout_reversal_buy"], sell_score=scores["breakout_reversal_sell"],
        reason=("failed breakout closed back inside the range with reversal confirmation" if side else "no confirmed failed-breakout reversal"),
        stop_distance=m5["atr14"] * tpsl_stop_atr(settings, config, "breakout_reversal") if side else None,
        reward_risk=tpsl_reward_risk(settings, config, "breakout_reversal") if side else None,
    )


def legacy_trend_decision(frames: dict, config: dict) -> dict:
    """Previously deployed M5/M15/H1 trend-only behavior without a router."""
    selected_names = ("M5", "M15", "H1")
    selected = tuple(frames[name] for name in selected_names)
    bullish = sum(frame["trend"] == "bullish" for frame in selected)
    bearish = sum(frame["trend"] == "bearish" for frame in selected)
    rsi = float(frames["M5"]["rsi14"])
    settings = config.get("legacy_trend", {})
    required_votes = int(settings.get("required_votes", 2))
    require_h1 = bool(settings.get("require_h1_alignment", False))
    h1_trend = frames["H1"]["trend"]
    buy_alignment = bullish >= required_votes and (not require_h1 or h1_trend == "bullish")
    sell_alignment = bearish >= required_votes and (not require_h1 or h1_trend == "bearish")
    side = None
    if buy_alignment and float(settings.get("buy_rsi_min", 40.0)) <= rsi <= float(settings.get("buy_rsi_max", 70.0)):
        side = "buy"
    elif sell_alignment and float(settings.get("sell_rsi_min", 30.0)) <= rsi <= float(settings.get("sell_rsi_max", 60.0)):
        side = "sell"
    # ★ แก้ 19 ก.ย. 2026: เดิมใช้ locals().get("reason", ...) ซึ่งเปราะ (เปลี่ยนชื่อตัวแปรแล้วพังเงียบ)
    reason = None
    if side is not None and not m1_trigger_allows(side, frames, config):
        side = None
        reason = "legacy trend passed but fresh M1 trigger did not pass"
    reason = (
        "legacy M5/M15/H1 trend alignment and fresh M1 trigger passed"
        if side is not None
        else (reason or "legacy M5/M15/H1 trend alignment or M5 RSI did not pass")
    )
    regime = {
        "regime": "trend" if side is not None else "transition",
        "confidence": max(bullish, bearish) / 3.0,
        "direction": side,
        "breakout_side": None,
        "breakout_level": None,
        "scores": {
            "trend": max(bullish, bearish) / 3.0,
            "range": 0.0,
            "breakout": 0.0,
        },
        "evidence": {
            "timeframe_trends": {name: frames[name]["trend"] for name in selected_names},
            "rsi_m5": rsi,
            "atr_m5": frames["M5"]["atr14"],
        },
    }
    candidate = _proposal(
        "trend_legacy",
        eligible=side is not None,
        side=side,
        confidence=max(bullish, bearish) / 3.0 if side is not None else 0.0,
        reason=reason,
        stop_distance=(
            frames["M5"]["atr14"] * tpsl_stop_atr(_strategy_settings(config), config, "trend")
            if side is not None
            else None
        ),
        reward_risk=tpsl_reward_risk(_strategy_settings(config), config, "trend") if side is not None else None,
    )
    return {
        "side": candidate["side"],
        "strategy": candidate["strategy"] if side is not None else None,
        "confidence": candidate["confidence"],
        "reason": reason,
        "stop_distance": candidate["stop_distance"],
        "reward_risk": candidate["reward_risk"],
        "regime": regime,
        "candidates": [candidate],
        "router_enabled": False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ★ "ด่านที่ 1" = ประตู net ต่อกลยุทธ์-ทิศทาง (ลำดับด่านตามที่ผู้ใช้กำหนด)
#    ด่าน 1 = ประตู net  →  คัดตัวที่ net ล่าสุดติดลบออกก่อน
#    ด่าน 2 = คะแนน 36 ค่า (raw / probability / weighted)
#    แล้วจึง "เรียงลำดับผู้รอด" ด้วยหลักการเดิม (probability → weighted_score)
#    เพื่อเลือกตัวที่จะเทรด
#   อ่านจากสมุดบัญชี work/side_net_ledger.json (เขียนทุกรอบ 10 นาที · incremental)
#   rolling: ไม้ใหม่ที่ปิดแล้วมีผลภายใน 20 วินาที (แคช) — ไม่ต้องรีสตาร์ทระบบ
# ─────────────────────────────────────────────────────────────────────────────

import side_net

_SIDE_NET_LEDGER_CACHE: dict = {"t": 0.0, "data": None, "path": None}


def _side_net_ledger() -> dict:
    """อ่านสมุดบัญชี net — ★ 19 ก.ย. 2026: ใช้โมดูลกลาง side_net (แคช 20 วิ)"""
    return side_net.load_ledger()


def side_net_deferred_keys(config: dict) -> dict:
    """→ {key: เหตุผล} ของกลยุทธ์-ทิศทางที่ "ด่าน 1" ชะลอ (net ล่าสุดติดลบ)

    • หลักฐานไม่ถึง min_samples → ปล่อยผ่าน (ไม่เดาจากเสี้ยวข้อมูล)
    • กลับเป็นบวกเมื่อไร → หลุดรายการทันที (rolling จากไม้ที่ปิดจริง)
    • ปิดประตูทั้งด่าน: config["side_net_gate"]["enabled"] = false
    ★ 19 ก.ย. 2026: ย้ายตรรกะไปไว้ที่โมดูลกลาง `side_net` (เดิมเขียนซ้ำกับ auto_trader)
    """
    return side_net.deferred_keys(config)


def _cd_floor(low_value, high_value, applies, margin):
    """★ พื้นคะแนนสำหรับไม้ "สวนแนวโน้ม" (เจ้าของระบบ 15 ก.ย. 2026)
    ยกพื้นขึ้น = margin แต่ไม่เกิน 80% ของความกว้าง band → ประตูยังมีช่วงให้ผ่านได้เสมอ
    (กันปัญหาประตูตัน/ไม่เทรดเลย ที่เคยเกิดจาก band แคบ)"""
    if not applies:
        return float(low_value)
    low_f = float(low_value)
    if isinstance(high_value, (int, float)) and float(high_value) > low_f:
        return low_f + min(float(margin), 0.80 * (float(high_value) - low_f))
    return low_f + float(margin)


def decide_market(frames: dict, config: dict) -> dict:
    if not bool(_strategy_settings(config).get("enabled", True)):
        return legacy_trend_decision(frames, config)
    regime = classify_regime(frames, config)
    candidates = [
        trend_agent(frames, regime, config),
        range_agent(frames, regime, config),
        mean_reversion_agent(frames, regime, config),
        breakout_agent(frames, regime, config),
        counter_trend_agent(frames, regime, config),
        breakout_reversal_agent(frames, regime, config),
    ]
    settings = _strategy_settings(config)
    strategy_weights = settings.get("strategy_weights", {})
    directional_weights = settings.get("directional_weights", {})
    directional_probabilities = settings.get("directional_probabilities", {})
    bounded_live = settings.get("bounded_live", {})
    bounded_live_enabled = bool(bounded_live.get("enabled", False))
    bounded_matrix = bounded_live.get("governance", {})
    # ★ ลำดับด่าน (ผู้ใช้กำหนด): ด่าน 1 = ประตู net → คัดก่อน · ด่าน 2 = คะแนน 36 ค่า
    #   คำนวณครั้งเดียวต่อรอบ (อ่านสมุดบัญชี net แคช 20 วินาที)
    net_deferred = side_net_deferred_keys(config) if bounded_live_enabled else {}
    # ★ ตั้งค่า "ไม้สวนแนวโน้ม H1 ต้องแรงกว่าปกติ" (เจ้าของระบบ 15 ก.ย. 2026)
    _cd_cfg = dict(bounded_live.get("counter_direction")
                   or ((config.get("strategy_router") or {}).get("auto_threshold") or {}).get("counter_direction")
                   or config.get("counter_direction") or {})
    _cd_on = bool(_cd_cfg.get("enabled", False))
    _cd_margin = float(_cd_cfg.get("margin", 0.05) or 0.05)
    _h1_trend = str((frames.get("H1") or {}).get("trend") or "").lower()
    stage1_blocked: set = set()
    score_keys = {
        "trend": ("trend_buy", "trend_sell"),
        "range": ("range_buy", "range_sell"),
        "mean_reversion": ("mean_reversion_buy", "mean_reversion_sell"),
        "breakout": ("breakout_buy", "breakout_sell"),
        "counter_trend": ("counter_trend_buy", "counter_trend_sell"),
        "breakout_reversal": ("breakout_reversal_buy", "breakout_reversal_sell"),
    }
    for candidate in candidates:
        candidate["trade_enabled"] = bool(settings.get("trade_enabled", {}).get(candidate["strategy"], True))
        # Router inputs are the Agent directional scores and probabilities.
        # Strategy/regime fields are retained only as diagnostics.
        buy_key, sell_key = score_keys[candidate["strategy"]]
        candidate["structural_eligible"] = bool(candidate.get("eligible", False))
        candidate["structural_side"] = candidate.get("side")
        candidate["raw_buy_score"] = float(regime["scores"].get(buy_key, 0.0))
        candidate["raw_sell_score"] = float(regime["scores"].get(sell_key, 0.0))
        candidate["buy_score"] = candidate["raw_buy_score"]
        candidate["sell_score"] = candidate["raw_sell_score"]
        # The bounded-live controller deliberately uses narrower weight bands
        # than the legacy adaptive range.  This limits multiplicative exposure.
        strategy_low, strategy_high = ((0.85, 1.15) if bounded_live_enabled else (0.75, 1.25))
        direction_low, direction_high = ((0.90, 1.10) if bounded_live_enabled else (0.75, 1.25))
        weight = max(strategy_low, min(strategy_high, float(strategy_weights.get(candidate["strategy"], 1.0))))
        candidate["weight"] = weight
        buy_weight = max(direction_low, min(direction_high, float(directional_weights.get(f"{candidate['strategy']}_buy", 1.0))))
        sell_weight = max(direction_low, min(direction_high, float(directional_weights.get(f"{candidate['strategy']}_sell", 1.0))))
        candidate["buy_probability"] = float(directional_probabilities.get(f"{candidate['strategy']}_buy", 0.5))
        candidate["sell_probability"] = float(directional_probabilities.get(f"{candidate['strategy']}_sell", 0.5))
        candidate["buy_weight"] = buy_weight
        candidate["sell_weight"] = sell_weight
        candidate["buy_score"] = min(1.0, candidate["buy_score"] * weight * buy_weight)
        candidate["sell_score"] = min(1.0, candidate["sell_score"] * weight * sell_weight)

    # Rank every Agent direction using only its directional score and
    # probability. Strategy/regime checks remain diagnostic metadata and do
    # not veto an otherwise score/probability-qualified entry.
    directional_scores = []
    bounded_diagnostics = []
    for candidate in candidates:
        if not candidate.get("trade_enabled", True):
            continue
        for side in ("buy", "sell"):
            score = float(candidate.get(f"{side}_score", 0.0))
            raw_score = float(candidate.get(f"raw_{side}_score", 0.0))
            probability = float(directional_probabilities.get(f"{candidate['strategy']}_{side}", 0.5))
            if score <= 0.0:
                continue
            # ── ด่าน 1: ประตู net ต่อกลยุทธ์-ทิศทาง (คัดก่อนเข้าด่านคะแนน 36 ค่า) ──
            #    คีย์ที่ net ล่าสุดติดลบ = ชะลอไว้ก่อน แล้วให้ผู้ที่เหลือไปแข่งกันที่ด่าน 2
            key_side = f"{candidate['strategy']}_{side}"
            if key_side in net_deferred:
                why_net = net_deferred[key_side]
                gate_s1 = {
                    "strategy": candidate["strategy"], "side": side, "passed": False,
                    "stage": "1_side_net", "blocked_by": "side_net_gate",
                    "raw_score": raw_score, "raw_gate": None,
                    "probability": probability, "probability_gate": None,
                    "weighted_score": score, "weighted_gate": None,
                    "reason": why_net,
                }
                # ★ เจ้าของระบบ 15 ก.ย. 2026: คีย์ที่ถูกประตู net สกัด ยังคำนวณ "36 ค่า" ไว้
                #   → ด่าน 3 ใช้เป็นตัวเลือกสำรองได้ (การประมวลผลช่วงหลังไม่ต้องผ่านด่าน net)
                _b = bounded_matrix.get(candidate["strategy"], {})
                _b_raw = float(_b.get(f"raw_{side}", _b.get("raw", 1.0)))
                _b_prob = float(_b.get(f"probability_{side}", _b.get("probability", 1.0)))
                _b_w = float(_b.get(f"weighted_{side}", _b.get("weighted", 1.0)))
                _b_raw_max = _b.get(f"raw_max_{side}", _b.get("raw_max"))
                _b_prob_max = _b.get(f"probability_max_{side}", _b.get("probability_max"))
                _b_w_max = _b.get(f"weighted_max_{side}", _b.get("weighted_max"))
                _b_ok = bool(
                    raw_score >= _b_raw and probability >= _b_prob and score >= _b_w
                    and ((_b_raw_max is None) or raw_score <= _b_raw_max)
                    and ((_b_prob_max is None) or probability <= _b_prob_max)
                    and ((_b_w_max is None) or score <= _b_w_max)
                )
                gate_s1["band_only"] = True
                gate_s1["band_passed"] = _b_ok
                gate_s1["raw_gate"] = _b_raw
                gate_s1["probability_gate"] = _b_prob
                gate_s1["weighted_gate"] = _b_w
                candidate[f"{side}_bounded_live_gate"] = gate_s1
                bounded_diagnostics.append(gate_s1)
                stage1_blocked.add(key_side)
                continue
            if bounded_live_enabled:
                rules = bounded_matrix.get(candidate["strategy"], {})
                # Per-side thresholds (36 values): if {key}_{side} exists use it,
                # else fall back to the shared strategy-level gate.  This lets
                # auto-threshold tune buy and sell independently.
                gs = side
                raw_gate = float(rules.get(f"raw_{gs}", rules.get("raw", 1.0)))
                probability_gate = float(rules.get(f"probability_{gs}", rules.get("probability", 1.0)))
                weighted_gate = float(rules.get(f"weighted_{gs}", rules.get("weighted", 1.0)))
                # Optional BAND gates: if *_max present, score must NOT exceed
                # the upper bound either.  A saturated score (indicator pinned
                # at its extreme) often signals an overextended move with higher
                # reversal risk for mean-reverting / range / counter-trend
                # strategies.  Absent *_max == lower-bound only (old behaviour).
                raw_max = rules.get(f"raw_max_{gs}", rules.get("raw_max"))
                probability_max = rules.get(f"probability_max_{gs}", rules.get("probability_max"))
                weighted_max = rules.get(f"weighted_max_{gs}", rules.get("weighted_max"))
                # Structural setup is intentionally diagnostic-only.  It helps
                # explain signal quality but must not veto an Agent direction
                # that passes the three owner-approved numerical gates.
                structural_confirmed = bool(
                    candidate.get("structural_eligible")
                    and candidate.get("structural_side") == side
                )
                gate = {
                    "strategy": candidate["strategy"], "side": side,
                    "raw_score": raw_score, "raw_gate": raw_gate,
                    "probability": probability, "probability_gate": probability_gate,
                    "weighted_score": score, "weighted_gate": weighted_gate,
                    "raw_gate_max": raw_max, "probability_gate_max": probability_max,
                    "weighted_gate_max": weighted_max,
                    "structural_confirmed": structural_confirmed,
                    "structural_mode": "diagnostic_only",
                }
                band_raw_ok = (raw_max is None) or (raw_score <= raw_max)
                band_prob_ok = (probability_max is None) or (probability <= probability_max)
                band_weight_ok = (weighted_max is None) or (score <= weighted_max)
                # ★ ไม้ "สวนแนวโน้ม H1" → ยกพื้นคะแนนขึ้น margin (ไม่เกิน 80% ของความกว้าง band)
                _cd_applies = bool(_cd_on and ((_h1_trend == "bearish" and side == "buy")
                                               or (_h1_trend == "bullish" and side == "sell")))
                raw_gate_eff = _cd_floor(raw_gate, raw_max, _cd_applies, _cd_margin)
                probability_gate_eff = _cd_floor(probability_gate, probability_max, _cd_applies, _cd_margin)
                weighted_gate_eff = _cd_floor(weighted_gate, weighted_max, _cd_applies, _cd_margin)
                gate["counter_direction"] = bool(_cd_applies)
                gate["counter_direction_margin"] = round(float(raw_gate_eff) - float(raw_gate), 4)
                gate["raw_gate_effective"] = round(float(raw_gate_eff), 4)
                gate["probability_gate_effective"] = round(float(probability_gate_eff), 4)
                gate["weighted_gate_effective"] = round(float(weighted_gate_eff), 4)
                gate["passed"] = bool(
                    raw_score >= raw_gate_eff and probability >= probability_gate_eff
                    and score >= weighted_gate_eff
                    and band_raw_ok and band_prob_ok and band_weight_ok
                )
                candidate[f"{side}_bounded_live_gate"] = gate
                bounded_diagnostics.append(gate)
                if not gate["passed"]:
                    continue
            directional_scores.append((probability, score, side, candidate))
    if not directional_scores:
        # แยกว่า "ว่างเพราะด่าน 1 (ประตู net)" หรือ "ว่างเพราะด่าน 2 (คะแนน 36 ค่า)"
        _reached_band = [g for g in bounded_diagnostics if g.get("stage") != "1_side_net"]
        if bounded_live_enabled and stage1_blocked and not _reached_band:
            _why_empty = ("stage-1 side-net: ทุกกลยุทธ์-ทิศทางถูกประตู net ชะลอ ("
                          + ", ".join(sorted(stage1_blocked)) + ") — รอ net กลับเป็นบวก")
        elif bounded_live_enabled:
            _why_empty = ("bounded-live: no Agent passed raw/probability/weighted gates"
                          + (f" · ประตู net ชะลอไว้ก่อน {len(stage1_blocked)} คีย์" if stage1_blocked else ""))
        elif any(candidate.get("eligible") for candidate in candidates):
            _why_empty = "validation-locked: all strategies are disabled"
        else:
            _why_empty = "no positive Agent score available"
        return {
            "side": None, "strategy": None, "confidence": 0.0,
            "reason": _why_empty, "stop_distance": None,
            "reward_risk": None, "regime": regime, "candidates": candidates,
            "router_enabled": True,
            "bounded_live": bounded_live_enabled,
            "bounded_live_diagnostics": bounded_diagnostics,
        }
    score_threshold = float(settings.get("agent_score_threshold", 0.60))
    score_thresholds = settings.get("agent_score_thresholds", {})
    # Ranking priority (research-driven): "prob" = rank by probability first,
    # "weight" = rank by weighted score first, "auto" = last chosen verdict
    # written by research/ranking_research.py into config (strategy_router.ranking_priority).
    _rp = str(settings.get("ranking_priority", "prob")).lower()
    if _rp == "weight":
        directional_scores.sort(key=lambda item: (item[1], item[0]), reverse=True)
    else:  # prob (default) or auto (falls back to prob until research decides)
        directional_scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
    top_four = directional_scores[:4]
    buy_pressure = sum(probability * score for probability, score, side, _ in top_four if side == "buy")
    sell_pressure = sum(probability * score for probability, score, side, _ in top_four if side == "sell")
    preferred_side = "buy" if buy_pressure > sell_pressure else "sell" if sell_pressure > buy_pressure else max(
        top_four, key=lambda item: item[1]
    )[2]
    _all_eligible = list(directional_scores)   # ★ ผู้ผ่านด่าน 1+2 ทั้งสองฝั่ง (ใช้ในด่าน 3)
    directional_scores = [item for item in top_four if item[2] == preferred_side]
    selected = None
    for rank, (probability, score, side, candidate) in enumerate(directional_scores):
        if bounded_live_enabled:
            selected = (score, side, candidate,
                        f"bounded-live {preferred_side.upper()} pressure {buy_pressure:.3f}/{sell_pressure:.3f}; "
                        f"rank {rank + 1} passed raw/probability/weighted gates; "
                        f"structural setup is diagnostic-only")
            break
        candidate_threshold = float(score_thresholds.get(candidate["strategy"], score_threshold))
        if score <= candidate_threshold:
            continue
        selected = (score, side, candidate, f"{preferred_side.upper()} pressure {buy_pressure:.3f}/{sell_pressure:.3f}; Agent probability-ranked {rank + 1} passed score threshold {candidate_threshold:.3f}")
        break
    if selected is None:
        best_probability, best_score = directional_scores[0][0], directional_scores[0][1]
        best_candidate = directional_scores[0][3]
        best_threshold = float(score_thresholds.get(best_candidate["strategy"], score_threshold))
        reason = f"no ranked Agent passed its score threshold (highest threshold {best_threshold:.3f})"
        if best_score <= best_threshold:
            reason = f"top probability {best_probability:.2%} direction score {best_score:.3f} is below {best_threshold:.3f}"
        return {
            "side": None,
            "strategy": None,
            "confidence": 0.0,
            "reason": reason,
            "stop_distance": None,
            "reward_risk": None,
            "regime": regime,
            "candidates": candidates,
            "router_enabled": True,
            "probability_top_four": [{"strategy": item[3]["strategy"], "side": item[2], "probability": item[0], "score": item[1]} for item in top_four],
            "preferred_side": preferred_side, "buy_pressure": buy_pressure, "sell_pressure": sell_pressure,
            "bounded_live": bounded_live_enabled,
            "bounded_live_diagnostics": bounded_diagnostics,
        }

    best_score, best_side, winner, selection_reason = selected
    # ── ★ ด่าน 3 (เจ้าของระบบกำหนด 15 ก.ย. 2026): เทียบ "สองฝั่ง" ของกลยุทธ์ที่ผ่านด่าน 1+2 ──
    #   เทียบด้วย (probability, weighted_score) เหมือนกติกาการเรียงลำดับของระบบ
    #   • ฝั่งตรงข้ามของ "กลยุทธ์เดียวกัน" ไม่น่าสนใจกว่า → เทรดฝั่งเดิม (keep)
    #   • น่าสนใจกว่า + ผ่านประตู net (ด่าน 1) → พลิกไปเทรดฝั่งนั้นของกลยุทธ์เดิม (flip_same)
    #   • น่าสนใจกว่า แต่ไม่ผ่านประตู net → มองหากลยุทธ์ "ฝั่งนั้น" ที่ผ่านด่าน 1+2 ตั้งแต่แรก
    #       – มี → ชั่งน้ำหนัก (prob → weighted) เลือกตัวดีที่สุด แล้วเทรดตัวนั้น (flip_other)
    #       – ไม่มีเลย → ไม่เทรดรอบนี้ (abstain)
    _s3 = {}
    _s3_blocked = None
    _s3_decision = "off"
    _s3_note = None
    if bounded_live_enabled:
        _s3 = dict(config.get("stage3") or bounded_live.get("stage3") or {})
        if _s3.get("enabled", True):
            _s3_decision = "keep"
            _chosen_score = best_score
            _other = "sell" if best_side == "buy" else "buy"
            _other_key = f"{winner['strategy']}_{_other}"
            _other_strategy = winner["strategy"]
            _other_score = float(winner.get(f"{_other}_score", 0.0) or 0.0)
            _other_prob = float(winner.get(f"{_other}_probability", 0.0) or 0.0)
            _chosen_prob = float(winner.get(f"{best_side}_probability", 0.0) or 0.0)
            if _other_score > 0.0 and (_other_prob, _other_score) > (_chosen_prob, _chosen_score):
                _hist = [float(x) for x in ((_side_net_ledger().get("keys") or {}).get(_other_key) or [])]
                _mean_hist = (sum(_hist) / len(_hist)) if _hist else 0.0
                _net_ok = _other_key not in net_deferred
                # ★ กติกาด่าน 3 (เจ้าของระบบ 15 ก.ย. 2026): ฝั่งตรงข้ามของกลยุทธ์เดิม
                #   จะเทรดได้ต้อง "ผ่าน 36 ค่า" ด้วย (ไม่ใช่ผ่านแค่ประตู net)
                _og = winner.get(f"{_other}_bounded_live_gate") or {}
                _other_band_ok = bool(_og.get("passed") or _og.get("band_passed"))
                _picked = None
                _picked_net_deferred = False
                if not _other_band_ok:      # ค้นหาตัวสำรองเมื่อฝั่งตรงข้ามไม่ผ่าน 36 ค่า
                    _alts = [item for item in _all_eligible
                             if item[2] == _other and item[3] is not winner]
                    # ★ เจ้าของระบบ 15 ก.ย. 2026: ตัวเลือกสำรองคิดจาก "36 ค่า" อย่างเดียว
                    #   (การประมวลผลช่วงหลังไม่ต้องผ่านประตู net)
                    if bool(_s3.get("allow_net_deferred", True)):
                        for _g in bounded_diagnostics:
                            if ((_g.get("band_only") and _g.get("band_passed")) or _g.get("passed")
                                    and _g.get("side") == _other
                                    and _g.get("strategy") != _other_strategy):
                                _c2 = next((c for c in candidates
                                            if c.get("strategy") == _g.get("strategy")), None)
                                if _c2 is not None and f"{_g.get('side')}_bounded_live_gate" in _c2:
                                    _c2["_stage3_from_band"] = not bool(_g.get("passed"))
                                    _alts.append((float(_g.get("probability") or 0.0),
                                                  float(_g.get("weighted_score") or 0.0),
                                                  _other, _c2))
                    if _alts:
                        _alts.sort(key=lambda it: (it[0], it[1]), reverse=True)
                        _picked = _alts[0]
                        _picked_net_deferred = bool(_picked[3].get("_stage3_from_band"))
                if _other_band_ok:      # ★ ฝั่งตรงข้ามทั้งหมด: ใช้ 36 ค่าเป็นเกณฑ์ ไม่ต้องผ่านประตู net
                    _s3_decision = "flip_same"
                    best_side = _other
                    best_score = _other_score
                    _s3_note = ("stage-3(a): ฝั่ง %s น่าสนใจกว่า (prob %.2f/score %.3f vs %.2f/%.3f) "
                                "และผ่านประตู net (ประวัติ net %+.3f · n=%d) → เทรดฝั่ง %s ของกลยุทธ์เดิม"
                                % (_other, _other_prob, _other_score, _chosen_prob, _chosen_score,
                                   _mean_hist, len(_hist), _other))
                elif _picked is not None:
                    _s3_decision = "flip_other"
                    winner = _picked[3]
                    _all_eligible = [item for item in _all_eligible if item[3] is not winner]
                    best_side = _other
                    best_score = float(_picked[1])
                    _s3_note = ("stage-3(b): ฝั่ง %s ของ %s น่าสนใจกว่าแต่ไม่ผ่านประตู net → "
                                "เลือกกลยุทธ์ฝั่ง %s ตัวที่ดีที่สุดคือ %s (prob %.2f/score %.3f)%s"
                                % (_other, _other_strategy, _other, winner["strategy"],
                                   float(_picked[0]), float(_picked[1]),
                                   " · คิดจาก 36 ค่า (ไม่ต้องผ่านประตู net ตามกติกาเจ้าของระบบ)"
                                   if _picked_net_deferred else " · ผ่านด่าน 1+2"))
                else:
                    _s3_decision = "abstain"
                    _s3_blocked = ("stage-3(c): ฝั่ง %s ของ %s น่าสนใจกว่าแต่ฝั่งตรงข้ามใช้ไม่ได้ %s "
                                   "และไม่มีกลยุทธ์ฝั่ง %s ตัวอื่นที่ผ่าน 36 ค่า → ไม่เทรดรอบนี้"
                                   % (_other, _other_strategy,
                                      "(ไม่ผ่าน 36 ค่า)",
                                      _other))
                bounded_diagnostics.append({
                    "strategy": _other_strategy, "side": _other, "stage": "3_two_sides",
                    "blocked_by": "stage3", "passed": bool(_s3_decision != "abstain"),
                    "stage3_decision": _s3_decision,
                    "chosen_side": best_side, "other_side": _other,
                    "chosen_probability": _chosen_prob, "other_probability": _other_prob,
                    "chosen_weighted": _chosen_score, "other_weighted": _other_score,
                    "other_net_ok": bool(_net_ok), "other_hist_n": len(_hist),
                    "other_hist_mean": round(_mean_hist, 4),
                    "picked_strategy": (winner["strategy"] if _s3_decision == "flip_other" else None),
                    "reason": (_s3_note or _s3_blocked),
                })
    if _s3_blocked:
        return {
            "side": None, "strategy": _other_strategy, "confidence": 0.0,
            "reason": _s3_blocked, "stop_distance": None, "reward_risk": None,
            "regime": regime, "candidates": candidates, "router_enabled": True,
            "bounded_live": bounded_live_enabled,
            "bounded_live_diagnostics": bounded_diagnostics,
            "stage3": {"decision": "abstain", "side_blocked": _other_key},
        }
    if _s3_note:
        selection_reason = ((selection_reason or "") + " | " + _s3_note)

    m5_atr = float(frames["M5"]["atr14"])
    stop_multipliers = {
        "trend": tpsl_stop_atr(settings, config, "trend"),
        "range": float(settings.get("range_stop_atr", 1.0)),
        "mean_reversion": float(settings.get("mean_reversion_stop_atr", 1.1)),
        "breakout": float(settings.get("breakout_stop_atr", 1.25)),
        "counter_trend": float(settings.get("counter_trend_stop_atr", 1.0)),
        "breakout_reversal": float(settings.get("breakout_reversal_stop_atr", 1.0)),
    }
    reward_risk = tpsl_reward_risk(settings, config, winner["strategy"])
    if winner["strategy"] == "breakout":
        reward_risk = max(reward_risk, float(settings.get("breakout_reward_risk", 2.0)))
    winner.update(
        eligible=True,
        side=best_side,
        confidence=best_score,
        strength=best_score,
        stop_distance=m5_atr * stop_multipliers[winner["strategy"]],
        reward_risk=reward_risk,
        # ★ ลดรูป 19 ก.ย. 2026: เดิมมี ternary ซ้อนที่สาขาสุดท้ายไม่มีทางถูกเรียก
        #   (rejected = bool(selection_reason) จึงเป็น False เสมอเมื่อมาถึงสาขานั้น)
        reason=(selection_reason or
                f"highest ranked eligible Agent score {best_score:.3f} passed {score_threshold:.3f}"),
    )
    return {
        "side": best_side,
        "strategy": winner["strategy"],
        "confidence": best_score,
        "reason": winner["reason"],
        "stop_distance": winner["stop_distance"],
        "reward_risk": winner["reward_risk"],
        "regime": regime,
        "candidates": candidates,
        "router_enabled": True,
        "bounded_live": bounded_live_enabled,
        "bounded_live_diagnostics": bounded_diagnostics,
        "probability_top_four": [{"strategy": item[3]["strategy"], "side": item[2], "probability": item[0], "score": item[1]} for item in top_four],
        "preferred_side": preferred_side, "buy_pressure": buy_pressure, "sell_pressure": sell_pressure,
    }
