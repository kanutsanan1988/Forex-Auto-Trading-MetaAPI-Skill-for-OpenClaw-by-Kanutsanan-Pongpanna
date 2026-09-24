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
"""Bounded adaptive research observer.

This module is deliberately unable to place orders or alter the production
router.  It produces a shadow-only challenger snapshot from already-resolved
paper outcomes and the current deterministic Agent scores.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import math
import statistics


FAMILIES = (
    "trend", "range", "mean_reversion", "counter_trend",
    "breakout", "breakout_reversal",
)
SIDES = ("buy", "sell")
KEYS = tuple(f"{family}_{side}" for family in FAMILIES for side in SIDES)

# Research priors copied from the owner-provided specification.  They are
# governance envelopes, never asserted to be production-optimal values.
GOVERNANCE = {
    "trend": {"raw": (.60, .54, .70), "prob": (.56, .52, .65), "weighted": (.62, .56, .72), "fmax": 1.00, "up": .015, "down": .008},
    "range": {"raw": (.54, .47, .65), "prob": (.55, .51, .64), "weighted": (.57, .50, .67), "fmax": .90, "up": .015, "down": .007},
    "mean_reversion": {"raw": (.50, .43, .62), "prob": (.57, .53, .67), "weighted": (.54, .47, .65), "fmax": .80, "up": .015, "down": .006},
    "counter_trend": {"raw": (.46, .40, .58), "prob": (.61, .56, .72), "weighted": (.50, .44, .62), "fmax": .60, "up": .015, "down": .004},
    "breakout": {"raw": (.72, .64, .82), "prob": (.58, .54, .68), "weighted": (.70, .63, .82), "fmax": .80, "up": .012, "down": .005},
    "breakout_reversal": {"raw": (.66, .58, .77), "prob": (.62, .57, .73), "weighted": (.65, .57, .77), "fmax": .50, "up": .012, "down": .003},
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _score_map(decision: dict) -> dict[str, float]:
    scores = decision.get("regime", {}).get("scores", {})
    return {key: _clip(float(scores.get(key, 0.0)), 0.0, 1.0) for key in KEYS}


def _candidate_map(decision: dict) -> dict[str, dict]:
    return {str(item.get("strategy")): item for item in decision.get("candidates", [])}


def _weighted_map(decision: dict) -> dict[str, float]:
    candidates = _candidate_map(decision)
    return {
        key: _clip(float(candidates.get(key.rsplit("_", 1)[0], {}).get(f"{key.rsplit('_', 1)[1]}_score", 0.0)), 0.0, 1.0)
        for key in KEYS
    }


def _effective_n(values: list[float]) -> float:
    """Autocorrelation-aware first-order effective sample size."""
    if len(values) < 3:
        return float(len(values))
    mean = statistics.fmean(values)
    denom = sum((x - mean) ** 2 for x in values)
    rho = 0.0 if denom <= 1e-12 else sum(
        (values[i] - mean) * (values[i - 1] - mean) for i in range(1, len(values))
    ) / denom
    rho = _clip(rho, -0.90, 0.90)
    return _clip(len(values) * (1.0 - rho) / (1.0 + rho), 1.0, float(len(values)))


def _outcomes_by_key(outcomes: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in outcomes:
        key = f"{row.get('strategy')}_{row.get('side')}"
        if key in KEYS and isinstance(row.get("r_multiple"), (int, float)):
            grouped[key].append(row)
    return grouped


def _wilson_lower(wins: int, n: int, z: float = 1.6448536269514722) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / d
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return _clip(centre - margin, 0.0, 1.0)


def _learning_metrics(rows: list[dict], family_rows: list[dict], all_rows: list[dict], cost_r: float) -> dict:
    # Hierarchical neutral/global/family/direction shrinkage.  Prior strength
    # is intentionally conservative and stays inside the 20-50 research band.
    def rate(items: list[dict]) -> float:
        return (sum(float(x["r_multiple"]) > 0.0 for x in items) + 10.0) / (len(items) + 20.0)

    global_prior = rate(all_rows)
    family_prior = (sum(float(x["r_multiple"]) > 0.0 for x in family_rows) + 20.0 * global_prior) / (len(family_rows) + 20.0)
    wins = sum(float(x["r_multiple"]) > 0.0 for x in rows)
    posterior = (wins + 20.0 * family_prior) / (len(rows) + 20.0)
    r_values = [float(x["r_multiple"]) for x in rows]
    neff = _effective_n(r_values)
    sample_confidence = neff / (neff + 40.0)
    influence = 0.0 if len(rows) < 20 else .2 if len(rows) < 50 else .4 if len(rows) < 100 else .6 if len(rows) < 250 else .8
    effective_probability = family_prior + influence * sample_confidence * (posterior - family_prior)
    avg_win = statistics.fmean([x for x in r_values if x > 0]) if any(x > 0 for x in r_values) else 0.0
    avg_loss = -statistics.fmean([x for x in r_values if x < 0]) if any(x < 0 for x in r_values) else 1.0
    expected_r = effective_probability * avg_win - (1.0 - effective_probability) * avg_loss - cost_r
    se = statistics.stdev(r_values) / math.sqrt(neff) if len(r_values) > 1 else 1.0
    safe_er = expected_r - 1.645 * se
    if len(rows) < 20:
        probability_state = "COLD_START"
    elif len(rows) < 100:
        probability_state = "LEARNING"
    else:
        # CALIBRATED is intentionally impossible here: a separate out-of-
        # sample reliability test must promote it.
        probability_state = "UNCALIBRATED"
    return {
        "n": len(rows), "n_eff": round(neff, 4), "wins": wins,
        "prior": round(family_prior, 6), "posterior_point": round(posterior, 6),
        "probability_lower_90": round(_wilson_lower(wins, len(rows)), 6),
        "effective_probability": round(_clip(effective_probability, 0.0, 1.0), 6),
        "probability_state": probability_state, "probability_influence": influence,
        "sample_confidence": round(sample_confidence, 6),
        "average_win_r": round(avg_win, 6), "average_loss_r": round(avg_loss, 6),
        "expected_r": round(expected_r, 6), "safe_expected_r": round(safe_er, 6),
        "uncertainty_penalty_r": round(1.645 * se, 6),
    }


def _compatibility(family: str, regime: str) -> float:
    table = {
        "trend": {"trend": 1.0, "transition": .65, "range": .35},
        "range": {"range": 1.0, "transition": .55, "trend": .30, "breakout": .15},
        "mean_reversion": {"range": 1.0, "transition": .45, "trend": .20, "breakout": .10},
        "counter_trend": {"trend": .85, "transition": .65, "range": .35},
        "breakout": {"breakout": 1.0, "transition": .75, "trend": .65, "range": .35},
        "breakout_reversal": {"range": .80, "transition": .80, "breakout": .60, "trend": .35},
    }
    return table.get(family, {}).get(regime, .50)


def validate_settings(settings: dict) -> None:
    if not isinstance(settings, dict):
        raise ValueError("bounded_adaptive_research must be an object")
    if settings.get("mode", "shadow_only") != "shadow_only":
        raise ValueError("bounded adaptive research mode must remain shadow_only")
    if settings.get("apply_to_live", False) is not False:
        raise ValueError("bounded adaptive research is forbidden from applying to live routing")


def evaluate_shadow(config: dict, state: dict, analysis: dict, shadow_cycle: dict) -> dict:
    """Return one non-authoritative research snapshot and update research state.

    The returned object cannot be consumed as an order decision.  The caller
    may only persist/audit it.  Existing production decision fields are never
    mutated.
    """
    settings = config.get("bounded_adaptive_research", {})
    validate_settings(settings)
    decision = analysis["technical_decision"]
    raw_scores = _score_map(decision)
    production_weighted = _weighted_map(decision)
    regime = str(decision.get("regime", {}).get("regime", "transition"))
    outcomes = list(state.get("adaptive_shadow", {}).get("outcomes", []))
    grouped = _outcomes_by_key(outcomes)
    by_family = {
        family: [row for row in outcomes if row.get("strategy") == family]
        for family in FAMILIES
    }
    research_state = state.setdefault("bounded_adaptive_research", {
        "schema_version": 1, "mode": "shadow_only", "active_version": 0,
        "current": {}, "last_resolved_count": 0,
    })
    previous = research_state.get("current", {})
    spread = float(analysis.get("spread") or 0.0)
    stop = max(float(analysis.get("stop_distance") or analysis.get("frames", {}).get("M5", {}).get("atr14") or 1.0), 1e-9)
    cost_r = max(0.0, spread / stop)
    agents = {}
    for key in KEYS:
        family, side = key.rsplit("_", 1)
        gov = GOVERNANCE[family]
        perf = _learning_metrics(grouped.get(key, []), by_family[family], outcomes, cost_r)
        readiness = _clip((perf["n_eff"] / (perf["n_eff"] + 100.0)), 0.0, 1.0)
        health = 1.0 if perf["safe_expected_r"] >= 0 else .65 if perf["expected_r"] >= 0 else .35
        calibration_quality = 0.0 if perf["probability_state"] in {"COLD_START", "UNCALIBRATED"} else .35
        market_safety = _compatibility(family, regime)
        freedom = gov["fmax"] * readiness * health * market_safety * max(.20, calibration_quality)
        # Negative delta (loosening) requires positive safe ER.  Otherwise all
        # changes are baseline or conservative tightening.
        history_delta = -min(.03, perf["safe_expected_r"] * .02) if perf["safe_expected_r"] > 0 else min(.05, abs(perf["safe_expected_r"]) * .02)
        regime_delta = -.02 if market_safety >= .85 else .02 if market_safety >= .50 else .05
        uncertainty_delta = (1.0 - perf["sample_confidence"]) * .04
        execution_delta = _clip(cost_r - .05, 0.0, .05)
        target = gov["raw"][0] + freedom * history_delta + regime_delta + uncertainty_delta + execution_delta
        old = float(previous.get(key, {}).get("dynamic_raw_threshold", gov["raw"][0]))
        delta = _clip(target - old, -gov["down"], gov["up"])
        dynamic_raw = _clip(old + delta, gov["raw"][1], gov["raw"][2])
        # Research weights are bounded more tightly than legacy weights and
        # never boost negative safe ER.
        target_strategy_weight = 1.0 + freedom * _clip(perf["safe_expected_r"] * .10, -.15, .15)
        if perf["safe_expected_r"] < 0:
            target_strategy_weight = min(1.0, target_strategy_weight)
        strategy_weight = _clip(target_strategy_weight, .85, 1.15)
        direction_weight = _clip(1.0 + freedom * _clip((perf["posterior_point"] - perf["prior"]) * .10, -.10, .10), .90, 1.10)
        total_weight = _clip(strategy_weight * direction_weight, .82, 1.18)
        weighted_score = _clip(raw_scores[key] * total_weight, 0.0, 1.0)
        dynamic_weighted = _clip(gov["weighted"][0] + max(0.0, dynamic_raw - gov["raw"][0]), gov["weighted"][1], gov["weighted"][2])
        contribution = weighted_score * perf["effective_probability"] * market_safety * perf["sample_confidence"]
        status = "SHADOW_ONLY" if perf["n"] < 100 or perf["safe_expected_r"] <= 0 else "SHADOW_ADAPTIVE"
        passed = (
            raw_scores[key] >= dynamic_raw and weighted_score >= dynamic_weighted
            and perf["effective_probability"] >= gov["prob"][0]
            and perf["safe_expected_r"] >= float(settings.get("required_safe_er", .10))
            and status == "SHADOW_ADAPTIVE"
        )
        agents[key] = {
            "family": family, "side": side, "raw_score": round(raw_scores[key], 6),
            "raw_baseline": gov["raw"][0], "raw_bounds": list(gov["raw"][1:]),
            "production_weighted_score_observed": round(production_weighted[key], 6),
            "dynamic_raw_threshold": round(dynamic_raw, 6),
            "strategy_weight": round(strategy_weight, 6), "direction_weight": round(direction_weight, 6),
            "total_weight": round(total_weight, 6), "research_weighted_score": round(weighted_score, 6),
            "weighted_baseline": gov["weighted"][0], "weighted_bounds": list(gov["weighted"][1:]),
            "dynamic_weighted_threshold": round(dynamic_weighted, 6),
            "probability_gate_baseline": gov["prob"][0], "probability_bounds": list(gov["prob"][1:]),
            "regime_compatibility": market_safety, "readiness": round(readiness, 6),
            "health": round(health, 6), "freedom": round(freedom, 6),
            "contribution": round(contribution, 6), "shadow_pass": passed,
            "recommendation": status, **perf,
        }
    buy_pressure = sum(x["contribution"] for x in agents.values() if x["side"] == "buy")
    sell_pressure = sum(x["contribution"] for x in agents.values() if x["side"] == "sell")
    high, low = max(buy_pressure, sell_pressure), min(buy_pressure, sell_pressure)
    conflict = low / high if high > 0 else 1.0
    margin = abs(buy_pressure - sell_pressure)
    passed = [key for key, value in agents.items() if value["shadow_pass"]]
    research_decision = "ABSTAIN"
    if passed and conflict <= float(settings.get("max_conflict", .70)) and margin >= float(settings.get("min_pressure_margin", .05)):
        preferred = "buy" if buy_pressure > sell_pressure else "sell"
        choices = [key for key in passed if agents[key]["side"] == preferred]
        if choices:
            research_decision = max(choices, key=lambda key: agents[key]["safe_expected_r"])
    snapshot = {
        "schema_version": 1, "mode": "shadow_only", "apply_to_live": False,
        "created_at": datetime.now(timezone.utc).isoformat(), "regime": regime,
        "data_source": "shadow", "resolved_outcomes": len(outcomes), "newly_resolved": len(shadow_cycle.get("closed", [])),
        "cost_r_proxy": round(cost_r, 6), "buy_pressure": round(buy_pressure, 6),
        "sell_pressure": round(sell_pressure, 6), "pressure_margin": round(margin, 6),
        "conflict_ratio": round(conflict, 6), "challenger_decision": research_decision,
        "production_decision_unchanged": True, "agents": agents,
    }
    research_state["active_version"] = int(research_state.get("active_version", 0)) + 1
    research_state["last_resolved_count"] = len(outcomes)
    research_state["current"] = deepcopy(agents)
    research_state["last_snapshot"] = {key: value for key, value in snapshot.items() if key != "agents"}
    return snapshot
