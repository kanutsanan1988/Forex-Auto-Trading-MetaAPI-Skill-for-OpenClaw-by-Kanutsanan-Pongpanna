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

import math
from copy import deepcopy


STRATEGIES = ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")
SIDES = ("buy", "sell")
SCORE_KEYS = tuple(f"{strategy}_{side}" for strategy in STRATEGIES for side in SIDES)


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _r_multiple(position: dict, close: float) -> float:
    distance = max(float(position["stop_distance"]), 1e-9)
    move = close - float(position["entry"])
    return (move if position["side"] == "buy" else -move) / distance


def _resolve_positions(router: dict, bar: dict, max_hold_bars: int) -> list[dict]:
    closed = []
    for key, position in list(router["positions"].items()):
        position["age"] = int(position.get("age", 0)) + 1
        if position["side"] == "buy":
            sl_hit = float(bar["low"]) <= float(position["sl"])
            tp_hit = float(bar["high"]) >= float(position["tp"])
        else:
            sl_hit = float(bar["high"]) >= float(position["sl"])
            tp_hit = float(bar["low"]) <= float(position["tp"])
        if sl_hit:  # pessimistic when both levels occur in one closed bar
            result, reason = -1.0, "sl"
        elif tp_hit:
            result, reason = float(position["reward_risk"]), "tp"
        elif position["age"] >= max_hold_bars:
            result, reason = _r_multiple(position, float(bar["close"])), "timeout"
        else:
            continue
        outcome = {**position, "closed_bar_time": int(bar["time"]), "r_multiple": round(result, 6), "reason": reason}
        closed.append(outcome)
        del router["positions"][key]
    return closed


def _group_metrics(outcomes: list[dict], strategy: str, side: str, regime: str, half_life: float) -> dict:
    matches = [o for o in outcomes if o["strategy"] == strategy and o["side"] == side and o["regime"] == regime]
    if not matches:
        return {"samples": 0, "expectancy": 0.0, "weight": 1.0, "validated": False}
    weighted_sum = 0.0
    weight_sum = 0.0
    for age, outcome in enumerate(reversed(matches)):
        decay = 0.5 ** (age / max(half_life, 1.0))
        weighted_sum += decay * float(outcome["r_multiple"])
        weight_sum += decay
    expectancy = weighted_sum / max(weight_sum, 1e-9)
    confidence = len(matches) / (len(matches) + 12.0)
    shrunk = expectancy * confidence
    midpoint = max(1, len(matches) // 2)
    older = matches[:midpoint]
    newer = matches[midpoint:]
    older_mean = sum(float(o["r_multiple"]) for o in older) / len(older)
    newer_mean = sum(float(o["r_multiple"]) for o in newer) / len(newer) if newer else older_mean
    validated = len(matches) >= 12 and older_mean > 0.0 and newer_mean > 0.0
    raw_weight = 1.0 + 0.35 * shrunk
    if len(matches) >= 12 and not validated:
        raw_weight = min(raw_weight, 1.0)
    return {
        "samples": len(matches), "expectancy": round(expectancy, 5),
        "older_expectancy": round(older_mean, 5), "newer_expectancy": round(newer_mean, 5),
        "validated": validated, "weight": round(_bounded(raw_weight, 0.75, 1.25), 4),
    }


def prepare_cycle(config: dict, state: dict, regime_hint: str | None = None) -> tuple[dict, dict]:
    """Build per-strategy/side/regime weights using only already-closed shadow outcomes."""
    settings = config["strategy_router"].get("adaptive", {})
    if not settings.get("shadow_enabled", True):
        return config, {}
    router = state.setdefault("adaptive_shadow", {"version": 2, "positions": {}, "outcomes": []})
    router.setdefault("positions", {})
    outcomes = router.setdefault("outcomes", [])[-int(settings.get("shadow_history_limit", 400)):]
    regime = regime_hint or str(router.get("last_regime", "transition"))
    metrics = {}
    weights = {}
    probability_weights = router.get("probability_weights", {})
    for strategy in STRATEGIES:
        side_metrics = {}
        for side in SIDES:
            item = _group_metrics(outcomes, strategy, side, regime, float(settings.get("decay_half_life", 40)))
            side_metrics[side] = item
            key = f"{strategy}_{side}"
            weights[key] = round(item["weight"] * _bounded(float(probability_weights.get(key, 1.0)), 0.80, 1.20), 4)
        metrics[strategy] = side_metrics
    previous = router.get("active_weights", {})
    recent = outcomes[-8:]
    if previous and len(recent) >= 8 and sum(float(o["r_multiple"]) for o in recent) < -2.0:
        weights = dict(router.get("last_good_weights", previous))
        router["rollback_count"] = int(router.get("rollback_count", 0)) + 1
        rollback = True
    else:
        router["last_good_weights"] = dict(previous or weights)
        rollback = False
    router["active_weights"] = dict(weights)
    updated = deepcopy(config)
    updated["strategy_router"]["directional_weights"] = weights
    probabilities = {key: float(item.get("win_probability", 0.5)) for key, item in router.get("probability_metrics", {}).items()}
    if not probabilities:
        probabilities = {key: 0.5 for key in weights}
    router["directional_probabilities"] = probabilities
    updated["strategy_router"]["directional_probabilities"] = probabilities
    return updated, {"regime": regime, "weights": weights, "probabilities": probabilities,
                     "metrics": metrics, "probability_metrics": router.get("probability_metrics", {}), "rollback": rollback}


def _update_probability_model(router: dict, config: dict) -> dict:
    """Estimate P(win | score signal) and pair co-occurrence, with Laplace smoothing."""
    settings = config["strategy_router"].get("adaptive", {})
    outcomes = router.get("outcomes", [])
    minimum = int(settings.get("probability_min_samples", 8))
    metrics, weights = {}, {}
    chart_metrics = config["strategy_router"].get("chart_metrics", {})
    for key in SCORE_KEYS:
        strategy, side = key.rsplit("_", 1)
        matches = [o for o in outcomes if o.get("strategy") == strategy and o.get("side") == side]
        wins = sum(float(o.get("r_multiple", 0.0)) > 0 for o in matches)
        p = (wins + 1.0) / (len(matches) + 2.0)
        if len(matches) < minimum:
            prior_pf = float(chart_metrics.get(strategy, {}).get("profit_factor") or 1.0)
            p = 0.5 * p + 0.5 * (prior_pf / (1.0 + prior_pf))
        signal_weight = 0.80 + 0.40 * p
        metrics[key] = {"samples": len(matches), "win_probability": round(p, 4), "weight": round(signal_weight, 4)}
        weights[key] = signal_weight
    # Relation score: when another directional score was simultaneously active,
    # blend its observed win probability into the target's weight.
    for target in SCORE_KEYS:
        related = []
        for outcome in outcomes:
            snapshot = outcome.get("score_snapshot", {})
            if float(snapshot.get(target, 0.0)) < float(settings.get("relation_signal_floor", 0.20)):
                continue
            active_others = [key for key in SCORE_KEYS if key != target and float(snapshot.get(key, 0.0)) >= float(settings.get("relation_signal_floor", 0.20))]
            if active_others:
                related.append((float(outcome.get("r_multiple", 0.0)) > 0, active_others))
        if len(related) < minimum:
            continue
        pair_p = sum(win for win, _ in related) / len(related)
        weights[target] = _bounded(0.70 * weights[target] + 0.30 * (0.80 + 0.40 * pair_p), 0.80, 1.20)
        metrics[target]["relation_samples"] = len(related)
        metrics[target]["relation_win_probability"] = round(pair_p, 4)
        metrics[target]["weight"] = round(weights[target], 4)
    router["probability_weights"] = {key: round(value, 4) for key, value in weights.items()}
    router["probability_metrics"] = metrics
    return metrics


def update_after_analysis(state: dict, decision: dict, frames: dict, config: dict) -> dict:
    """Resolve and open paper-only candidates for every Agent direction each M1 cycle."""
    settings = config["strategy_router"].get("adaptive", {})
    router = state.setdefault("adaptive_shadow", {"version": 2, "positions": {}, "outcomes": []})
    router.setdefault("positions", {})
    router.setdefault("outcomes", [])
    router.setdefault("score_snapshots", [])
    m1 = frames["M1"]
    closed = _resolve_positions(router, m1, int(settings.get("shadow_max_hold_bars", 60)))
    router["outcomes"].extend(closed)
    del router["outcomes"][:-int(settings.get("shadow_history_limit", 400))]
    regime = str(decision.get("regime", {}).get("regime", "transition"))
    router["last_regime"] = regime
    score_snapshot = {key: float(decision.get("regime", {}).get("scores", {}).get(key, 0.0)) for key in SCORE_KEYS}
    router["score_snapshots"].append({"bar_time": int(m1["time"]), "regime": regime, "scores": score_snapshot})
    del router["score_snapshots"][:-int(settings.get("shadow_history_limit", 400))]
    min_score = float(settings.get("shadow_min_score", 0.20))
    atr = float(frames["M5"]["atr14"])
    stop_factors = {
        "trend": 1.2, "range": 1.0, "mean_reversion": 1.1, "breakout": 1.25,
        "counter_trend": 1.0, "breakout_reversal": 1.0,
    }
    candidates = {c.get("strategy"): c for c in decision.get("candidates", [])}
    opened = []
    for strategy in STRATEGIES:
        candidate = candidates.get(strategy, {})
        for side in SIDES:
            score = float(candidate.get(f"{side}_score", 0.0))
            key = f"{strategy}:{side}:{regime}"
            if score < min_score or key in router["positions"]:
                continue
            entry = float(m1["close"])
            stop_distance = max(atr * stop_factors[strategy], 1e-6)
            reward_risk = float(candidate.get("reward_risk") or 1.0)
            if bool(config.get("enforce_equal_tp_sl", False)):
                reward_risk = min(reward_risk, 1.0)
            sl = entry - stop_distance if side == "buy" else entry + stop_distance
            tp = entry + stop_distance * reward_risk if side == "buy" else entry - stop_distance * reward_risk
            position = {
                "strategy": strategy, "side": side, "regime": regime, "score": score,
                "entry": entry, "sl": sl, "tp": tp, "stop_distance": stop_distance,
                "reward_risk": reward_risk, "opened_bar_time": int(m1["time"]), "age": 0,
                "score_snapshot": dict(score_snapshot),
            }
            router["positions"][key] = position
            opened.append(position)
    metrics = _update_probability_model(router, config)
    return {"opened": opened, "closed": closed, "open_count": len(router["positions"]),
            "probability_metrics": metrics}


def health_check(frames: dict, tick, max_spread: float, now_timestamp: float) -> tuple[bool, list[str]]:
    reasons = []
    spread = float(tick.ask - tick.bid)
    if not math.isfinite(spread) or spread <= 0.0:
        reasons.append("invalid spread")
    if spread > max_spread * 3.0:
        reasons.append("extreme spread")
    if now_timestamp - float(getattr(tick, "time", 0)) > 180.0:
        reasons.append("stale tick")
    limits = {"M1": 180, "M5": 900, "M15": 1800, "H1": 7200}
    for name, seconds in limits.items():
        frame = frames.get(name, {})
        values = [frame.get("open"), frame.get("high"), frame.get("low"), frame.get("close"), frame.get("atr14")]
        if any(value is None or not math.isfinite(float(value)) for value in values):
            reasons.append(f"{name} invalid data")
        if now_timestamp - float(frame.get("time", 0)) > seconds:
            reasons.append(f"{name} stale bars")
    return not reasons, reasons
