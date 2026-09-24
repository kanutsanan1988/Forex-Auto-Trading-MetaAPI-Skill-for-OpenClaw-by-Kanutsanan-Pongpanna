# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import msvcrt
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_FILE = HERE / "auto_config.json"
STATE_FILE = ROOT / "work" / "auto_trader_state.json"
AUDIT_FILE = ROOT / "work" / "auto_trader_audit.jsonl"
STOP_FILE = ROOT / "work" / "AUTO_TRADER_STOP"
LOCK_FILE = ROOT / "work" / "auto_trader.lock"
PID_FILE = ROOT / "work" / "auto_trader.pid"
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
BANGKOK = timezone(timedelta(hours=7))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import MetaTrader5 as mt5  # noqa: E402
from market_analyzer import market_frames  # noqa: E402
from strategy_engine import decide_market  # noqa: E402
from openrouter_agents import MODEL as OPENROUTER_MODEL, run_dual_agents  # noqa: E402
from adaptive_shadow import health_check, prepare_cycle, update_after_analysis  # noqa: E402


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def bangkok_trading_date() -> str:
    return datetime.now(BANGKOK).date().isoformat()


def bangkok_day_start_utc() -> datetime:
    local_now = datetime.now(BANGKOK)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(timezone.utc)


def account_hash(login: int, server: str) -> str:
    return hashlib.sha256(f"{login}:{server}".encode()).hexdigest()


def audit(event: str, **data) -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": now_utc(), "event": event, **data}
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    try:
        print(json.dumps(record, ensure_ascii=False, default=str), flush=True)
    except (OSError, UnicodeError):
        pass


def acquire_singleton():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("a+b")
    handle.seek(0, 2)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        handle.close()
        raise RuntimeError("Another auto_trader process is already running") from exc
    PID_FILE.write_text(str(os.getpid()), encoding="ascii")
    return handle


def release_singleton(handle) -> None:
    try:
        if PID_FILE.exists() and PID_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
            PID_FILE.unlink(missing_ok=True)
    finally:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            handle.close()


def load_config() -> dict:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    required = {
        "live_enabled", "symbol", "volume", "max_risk_pct", "daily_loss_limit_pct",
        "max_consecutive_losses", "min_reward_risk", "atr_stop_multiplier",
        "max_spread", "deviation_points", "cooldown_minutes", "poll_seconds",
        "position_monitor_seconds", "profit_exit", "reconnect_seconds", "magic", "strategy_router",
    }
    missing = required.difference(config)
    if missing:
        raise RuntimeError(f"Missing config keys: {sorted(missing)}")
    positive = (
        "volume", "max_risk_pct", "daily_loss_limit_pct",
        "min_reward_risk", "atr_stop_multiplier", "max_spread", "deviation_points",
        "poll_seconds", "position_monitor_seconds", "reconnect_seconds",
    )
    if any(float(config[key]) <= 0 for key in positive):
        raise RuntimeError("Risk, timing and volume configuration values must be positive")
    if float(config["max_consecutive_losses"]) < 0:
        raise RuntimeError("max_consecutive_losses cannot be negative")
    if float(config["cooldown_minutes"]) < 0:
        raise RuntimeError("cooldown_minutes cannot be negative")
    profit_exit = config["profit_exit"]
    if not isinstance(profit_exit, dict) or "enabled" not in profit_exit or "minimum_profit_usd" not in profit_exit:
        raise RuntimeError("profit_exit must define enabled and minimum_profit_usd")
    if not isinstance(profit_exit["enabled"], bool) or float(profit_exit["minimum_profit_usd"]) < 0:
        raise RuntimeError("profit_exit configuration is invalid")
    legacy = config.get("legacy_trend", {})
    if legacy:
        if int(legacy.get("required_votes", 0)) not in {2, 3}:
            raise RuntimeError("legacy_trend.required_votes must be 2 or 3")
        for lower, upper in (("buy_rsi_min", "buy_rsi_max"), ("sell_rsi_min", "sell_rsi_max")):
            if not 0.0 <= float(legacy[lower]) < float(legacy[upper]) <= 100.0:
                raise RuntimeError(f"legacy_trend RSI bounds invalid: {lower}/{upper}")
    router = config["strategy_router"]
    if not isinstance(router, dict) or "enabled" not in router:
        raise RuntimeError("strategy_router must define enabled")
    trade_enabled = router.get("trade_enabled", {})
    expected_strategies = {"trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal"}
    if not isinstance(trade_enabled, dict) or set(trade_enabled) != expected_strategies:
        raise RuntimeError(f"strategy_router.trade_enabled must define {sorted(expected_strategies)}")
    if any(not isinstance(value, bool) for value in trade_enabled.values()):
        raise RuntimeError("strategy_router.trade_enabled values must be boolean")
    score_threshold = float(router.get("agent_score_threshold", 0.60))
    if not 0.0 < score_threshold < 1.0:
        raise RuntimeError("strategy_router.agent_score_threshold must be in (0, 1)")
    if router.get("mode") not in {"technical_only", "legacy_h1"}:
        raise RuntimeError("strategy_router.mode must be technical_only or legacy_h1")
    openrouter = config.get("openrouter", {})
    if not isinstance(openrouter, dict) or not isinstance(openrouter.get("enabled", False), bool):
        raise RuntimeError("openrouter.enabled must be boolean")
    if openrouter.get("enabled", False):
        if not 1.0 <= float(openrouter.get("timeout_seconds", 25)) <= 120.0:
            raise RuntimeError("openrouter.timeout_seconds must be in [1, 120]")
        if not 1 <= int(openrouter.get("max_attempts", 2)) <= 3:
            raise RuntimeError("openrouter.max_attempts must be in [1, 3]")
        if not 0.0 <= float(openrouter.get("retry_delay_seconds", 1.0)) <= 5.0:
            raise RuntimeError("openrouter.retry_delay_seconds must be in [0, 5]")
        if not 100 <= int(openrouter.get("max_tokens", 1200)) <= 4000:
            raise RuntimeError("openrouter.max_tokens must be in [100, 4000]")
        if not 0.0 <= float(openrouter.get("temperature", 0.1)) <= 1.0:
            raise RuntimeError("openrouter.temperature must be in [0, 1]")
        if not 0.0 <= float(openrouter.get("cache_seconds", 90)) <= 300.0:
            raise RuntimeError("openrouter.cache_seconds must be in [0, 300]")
        if not 0.0 < float(openrouter.get("judge_min_confidence", 0.55)) <= 1.0:
            raise RuntimeError("openrouter.judge_min_confidence must be in (0, 1]")
        if not isinstance(openrouter.get("fallback_to_python", True), bool):
            raise RuntimeError("openrouter.fallback_to_python must be boolean")
    return config


def load_state(account, equity: float) -> dict:
    today = bangkok_trading_date()
    binding = account_hash(account.login, account.server)
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if state.get("account_hash") != binding:
            raise RuntimeError("Trading account changed; delete state only after reviewing the new account")
    else:
        state = {"account_hash": binding, "date": today, "day_start_equity": equity,
                 "consecutive_losses": 0, "last_exit_deal": 0, "last_trade_time": 0,
                 "adaptive": {"outcomes": {}, "gates": {}}}
    if state.get("date") != today:
        state.update(date=today, day_start_equity=equity, consecutive_losses=0,
                     last_exit_deal=0, last_trade_time=0)
    state.setdefault("adaptive", {"outcomes": {}, "gates": {}})
    state["adaptive"].setdefault("outcomes", {})
    state["adaptive"].setdefault("gates", {})
    return state


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def connect(symbol_name: str):
    if not mt5.initialize(path=TERMINAL):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    symbol = mt5.symbol_info(symbol_name)
    if not terminal or not terminal.connected:
        raise RuntimeError("MT5 terminal is disconnected")
    if not account:
        raise RuntimeError("Account unavailable")
    if not symbol:
        raise RuntimeError(f"Symbol unavailable: {symbol_name}")
    if not symbol.visible and not mt5.symbol_select(symbol_name, True):
        raise RuntimeError(f"Could not select {symbol_name}")
    return terminal, account, mt5.symbol_info(symbol_name)


def refresh_closed_trade_state(state: dict, config: dict) -> None:
    start = bangkok_day_start_utc()
    deals = mt5.history_deals_get(start, datetime.now(timezone.utc)) or ()
    exits = [
        deal for deal in deals
        if deal.symbol == config["symbol"]
        and int(deal.magic) == int(config["magic"])
        and deal.entry == mt5.DEAL_ENTRY_OUT
    ]
    exits.sort(key=lambda deal: deal.ticket)
    for deal in exits:
        if int(deal.ticket) <= int(state.get("last_exit_deal", 0)):
            continue
        net = float(deal.profit + deal.commission + deal.swap + deal.fee)
        state["consecutive_losses"] = state["consecutive_losses"] + 1 if net < 0 else 0
        state["last_exit_deal"] = int(deal.ticket)
        comment = str(getattr(deal, "comment", ""))
        strategy = comment.removeprefix("codex-").split("-")[0]
        if strategy not in {"trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal"}:
            strategy = "unknown"
        sample = state.setdefault("adaptive", {}).setdefault("outcomes", {}).setdefault(strategy, [])
        sample.append(net)
        del sample[:-40]
        audit("position_closed", ticket=deal.ticket, net=net,
              consecutive_losses=state["consecutive_losses"], strategy=strategy)


def apply_adaptive_gates(config: dict, state: dict) -> dict:
    """Adapt strategy availability from rolling results with conservative hysteresis."""
    adaptive = config["strategy_router"].get("adaptive", {})
    if not adaptive.get("enabled", True):
        return config
    minimum = int(adaptive.get("min_samples", 12))
    disable_pf = float(adaptive.get("disable_profit_factor", 0.85))
    enable_pf = float(adaptive.get("enable_profit_factor", 1.05))
    outcomes = state.setdefault("adaptive", {}).setdefault("outcomes", {})
    gates = state["adaptive"].setdefault("gates", {})
    enabled = dict(config["strategy_router"].get("trade_enabled", {}))
    weights = {}
    metrics = {}
    for strategy in ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal"):
        values = [float(v) for v in outcomes.get(strategy, [])]
        chart = state.get("adaptive", {}).get("chart_metrics", {}).get(strategy, {})
        if len(values) < minimum and chart.get("samples", 0) < minimum:
            gates[strategy] = True
            weights[strategy] = 1.0
            metrics[strategy] = {"samples": len(values), "chart_samples": chart.get("samples", 0), "pf": None, "gate": True}
            continue
        wins = sum(v for v in values if v > 0)
        losses = -sum(v for v in values if v < 0)
        live_pf = wins / losses if losses else 99.0
        chart_pf = chart.get("profit_factor")
        pf = live_pf if len(values) >= minimum else float(chart_pf or 0.0)
        # Bounded per-cycle preference: stronger recent evidence gets more
        # weight, but no strategy can dominate or disappear solely by scaling.
        weights[strategy] = round(max(0.75, min(1.25, 0.85 + 0.20 * min(pf, 2.0))), 4)
        previous = bool(gates.get(strategy, enabled.get(strategy, True)))
        gate = False if pf < disable_pf else (True if pf >= enable_pf else previous)
        gates[strategy] = gate
        enabled[strategy] = bool(enabled.get(strategy, True) and gate)
        metrics[strategy] = {"samples": len(values), "pf": round(pf, 4), "gate": enabled[strategy]}
    if not any(enabled.values()):
        enabled["breakout"] = True
        gates["breakout"] = True
    updated = copy.deepcopy(config)
    updated["strategy_router"]["trade_enabled"] = enabled
    updated["strategy_router"]["strategy_weights"] = weights
    audit("adaptive_update", metrics=metrics, strategy_weights=weights, trade_enabled=enabled)
    return updated


def bootstrap_chart_metrics(state: dict, config: dict) -> None:
    """Use recent closed M5/M15/H1 bars as a cold-start prior for adaptation."""
    adaptive = config["strategy_router"].get("adaptive", {})
    stored = state.get("adaptive", {})
    if not adaptive.get("chart_bootstrap", True) or (
        stored.get("chart_date") == bangkok_trading_date()
        and stored.get("chart_version") == 2
        and stored.get("chart_metrics")
    ):
        return
    try:
        from strategy_backtest import run_backtest
        backtest_config = copy.deepcopy(config)
        # Chart learning evaluates signal quality in R-multiples; the small
        # live account's dollar risk gate must not erase otherwise valid samples.
        backtest_config["max_risk_pct"] = 1000.0
        result = run_backtest(backtest_config, bars=int(adaptive.get("chart_bars", 1200)), spread=float(config["max_spread"]), max_hold_bars=24)
        grouped = result.get("by_strategy", {})
        state.setdefault("adaptive", {})["chart_metrics"] = {
            name: {"samples": int(data.get("trades", 0)), "profit_factor": data.get("profit_factor")}
            for name, data in grouped.items()
        }
        state["adaptive"]["chart_date"] = bangkok_trading_date()
        state["adaptive"]["chart_version"] = 2
        audit("adaptive_chart_bootstrap", bars=adaptive.get("chart_bars", 1200), metrics=state["adaptive"]["chart_metrics"])
    except Exception as exc:
        audit("adaptive_chart_bootstrap_failed", error=str(exc))


def latest_closed_m1_time(symbol_name: str) -> int:
    rates = mt5.copy_rates_from_pos(symbol_name, mt5.TIMEFRAME_M1, 0, 3)
    if rates is None or len(rates) < 3:
        raise RuntimeError(f"Cannot load M5 bars: {mt5.last_error()}")
    return int(rates[-2]["time"])


def analyze(config: dict, state: dict, account, symbol) -> dict:
    symbol_name = config["symbol"]
    tick = mt5.symbol_info_tick(symbol_name)
    if tick is None:
        raise RuntimeError(f"No current tick for {symbol_name}: {mt5.last_error()}")
    frames = market_frames(symbol_name)
    # Group 1: the existing deterministic Python signal pipeline.
    python_decision = decide_market(frames, config)
    decision = python_decision
    health_ok, health_reasons = health_check(
        frames, tick, float(config["max_spread"]), datetime.now(timezone.utc).timestamp()
    )
    if not health_ok:
        decision = copy.deepcopy(decision)
        decision.update(
            side=None, strategy=None, confidence=0.0, stop_distance=None,
            reward_risk=None, reason="health check blocked: " + "; ".join(health_reasons),
        )
    technical_decision = decision
    # Group 2 + final judge. The returned decision is fail-closed and contains
    # no order parameters; Python continues to calculate all execution values.
    dual_agents = run_dual_agents(config, frames, technical_decision)
    decision = dual_agents["trade_decision"]
    side = decision["side"]
    spread = float(tick.ask - tick.bid)
    entry = float(tick.ask if side == "buy" else tick.bid)
    stop_distance = decision["stop_distance"]
    reward_risk = decision["reward_risk"]
    if reward_risk is not None and bool(config.get("enforce_equal_tp_sl", False)):
        # Optional legacy safety mode. Normal operation keeps TP independent.
        reward_risk = min(float(reward_risk), 1.0)
        decision["reward_risk"] = reward_risk
    if side == "buy":
        sl, tp = entry - stop_distance, entry + stop_distance * reward_risk
        order_type = mt5.ORDER_TYPE_BUY
    elif side == "sell":
        sl, tp = entry + stop_distance, entry - stop_distance * reward_risk
        order_type = mt5.ORDER_TYPE_SELL
    else:
        sl = tp = order_type = None
    calculated_risk = None if side is None else mt5.order_calc_profit(
        order_type, symbol_name, config["volume"], entry, sl
    )
    if side is not None and calculated_risk is None:
        raise RuntimeError(f"Risk calculation failed: {mt5.last_error()}")
    risk_usd = None if calculated_risk is None else abs(float(calculated_risk))
    risk_pct = None if risk_usd is None else 100.0 * risk_usd / float(account.equity)
    return {"side": side, "entry": entry, "sl": sl, "tp": tp, "spread": spread,
            "stop_distance": stop_distance, "risk_usd": risk_usd, "risk_pct": risk_pct,
            "strategy": decision["strategy"], "strategy_confidence": decision["confidence"],
            "market_regime": decision["regime"]["regime"], "decision": decision,
            "technical_decision": technical_decision,
            "router_decision": decision,
            "router_events": [{"event": "dual_agent_result", "status": dual_agents.get("status"),
                               "cached": dual_agents.get("cached", False),
                               "fallback": dual_agents.get("fallback", False),
                               "judge": dual_agents.get("judge"), "openrouter_signal": dual_agents.get("openrouter_signal"),
                               "error": dual_agents.get("error")}],
            "dual_agents": dual_agents, "frames": frames,
            "health_ok": health_ok, "health_reasons": health_reasons,
            }


def compact_decision(decision: dict) -> dict:
    return {
        "side": decision.get("side"),
        "strategy": decision.get("strategy"),
        "confidence": decision.get("confidence"),
        "reason": decision.get("reason"),
        "regime": decision.get("regime", {}).get("regime"),
        "regime_scores": decision.get("regime", {}).get("scores"),
        "candidates": [
            {"strategy": c.get("strategy"), "side": c.get("side"),
             "eligible": c.get("eligible"), "confidence": c.get("confidence"),
             "buy_score": c.get("buy_score", 0.0), "sell_score": c.get("sell_score", 0.0)}
            for c in decision.get("candidates", [])
        ],
    }


def compact_analysis(analysis: dict) -> dict:
    technical = analysis["technical_decision"]
    return {
        "side": analysis["side"],
        "entry": analysis["entry"],
        "sl": analysis["sl"],
        "tp": analysis["tp"],
        "spread": analysis["spread"],
        "risk_usd": analysis["risk_usd"],
        "risk_pct": analysis["risk_pct"],
        "strategy": analysis["strategy"],
        "market_regime": analysis["market_regime"],
        "router_decision": compact_decision(analysis["decision"]),
        "dual_agents": {
            "status": analysis["dual_agents"].get("status"),
            "cached": analysis["dual_agents"].get("cached", False),
            "fallback": analysis["dual_agents"].get("fallback", False),
            "cached": analysis["dual_agents"].get("cached", False),
            "python_side": (analysis["dual_agents"].get("python_signal") or {}).get("side"),
            "openrouter_side": (analysis["dual_agents"].get("openrouter_signal") or {}).get("side"),
            "judge": analysis["dual_agents"].get("judge"),
            "error": analysis["dual_agents"].get("error"),
        },
        "technical_candidates": [
            {
                "strategy": candidate["strategy"],
                "eligible": candidate["eligible"],
                "side": candidate["side"],
                "confidence": candidate["confidence"],
                "strength": candidate.get("strength", candidate["confidence"]),
                "buy_score": candidate.get("buy_score", 0.0),
                "sell_score": candidate.get("sell_score", 0.0),
                "reason": candidate["reason"],
            }
            for candidate in technical["candidates"]
        ],
    }


def risk_gate(config: dict, state: dict, account, analysis: dict) -> tuple[bool, str]:
    if analysis["side"] is None:
        return False, analysis["decision"]["reason"]
    if analysis["spread"] > config["max_spread"]:
        return False, "spread limit exceeded"
    if analysis["risk_pct"] > config["max_risk_pct"]:
        return False, "risk limit exceeded at minimum configured volume"
    drawdown = max(0.0, 100.0 * (state["day_start_equity"] - account.equity) / state["day_start_equity"])
    if drawdown >= config["daily_loss_limit_pct"]:
        return False, "daily loss limit reached"
    projected_drawdown = drawdown + 100.0 * analysis["risk_usd"] / state["day_start_equity"]
    if projected_drawdown > config["daily_loss_limit_pct"]:
        return False, "projected daily loss limit exceeded"
    # A value <= 0 disables the consecutive-loss admission gate.  We still
    # track the streak for reporting/adaptive analytics, but it must not stop
    # trading when the user has explicitly disabled this safeguard.
    if config["max_consecutive_losses"] > 0 and state["consecutive_losses"] >= config["max_consecutive_losses"]:
        return False, "consecutive loss limit reached"
    cooldown = config["cooldown_minutes"] * 60
    if time.time() - state["last_trade_time"] < cooldown:
        return False, "cooldown active"
    return True, "passed"


def build_request(config: dict, analysis: dict) -> dict:
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": config["symbol"],
        "volume": config["volume"],
        "type": mt5.ORDER_TYPE_BUY if analysis["side"] == "buy" else mt5.ORDER_TYPE_SELL,
        "price": analysis["entry"], "sl": analysis["sl"], "tp": analysis["tp"],
        "deviation": config["deviation_points"], "magic": config["magic"],
        "comment": f"codex-{analysis['strategy'] or 'router'}", "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }


def evaluate_same_direction_cut_loss(position, analysis: dict | None) -> dict:
    """Score whether replacing a losing same-direction position is worthwhile.

    The four explicit outputs are directional cut/hold scores and their
    normalized probabilities.  Scores combine current loss-to-SL progress,
    the new signal confidence, and the new signal's reward/risk potential.
    Status 1=hold, 2=unclear, 3=cut and replace.
    """
    floating = float(position.profit) + float(position.swap)
    decision = (analysis or {}).get("router_decision") or {}
    confidence = float(decision.get("confidence", 0.0) or 0.0)
    reward_risk = float((analysis or {}).get("reward_risk") or decision.get("reward_risk", 0.0) or 0.0)
    entry = float(position.price_open)
    sl = float(position.sl)
    tick = mt5.symbol_info_tick(position.symbol)
    current = float((tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask) if tick else entry)
    sl_distance = abs(entry - sl)
    adverse_distance = max(0.0, entry - current) if position.type == mt5.POSITION_TYPE_BUY else max(0.0, current - entry)
    loss_to_sl = max(0.0, min(1.0, adverse_distance / sl_distance)) if sl_distance > 0 else 0.0
    confidence_edge = max(0.0, min(1.0, (confidence - 0.35) / 0.65))
    rr_edge = max(0.0, min(1.0, (reward_risk - 1.0) / 2.0))
    cut_score = max(0.0, min(1.0, 0.55 * loss_to_sl + 0.30 * confidence_edge + 0.15 * rr_edge))
    hold_score = max(0.0, min(1.0, 0.55 * (1.0 - loss_to_sl) + 0.30 * (1.0 - confidence_edge) + 0.15 * (1.0 - rr_edge)))
    total = cut_score + hold_score or 1.0
    cut_probability = cut_score / total
    hold_probability = hold_score / total
    status = 3 if cut_probability >= 0.60 else 2 if cut_probability >= 0.40 else 1
    return {
        "cut_score": round(cut_score, 6), "hold_score": round(hold_score, 6),
        "cut_probability": round(cut_probability, 6), "hold_probability": round(hold_probability, 6),
        "status": status, "loss_to_sl": round(loss_to_sl, 6),
        "signal_confidence": round(confidence, 6), "reward_risk": round(reward_risk, 6),
    }


def manage_profitable_positions(
    config: dict,
    live: bool,
    terminal,
    account,
    desired_side: str | None,
    analysis: dict | None = None,
    signal_reliable: bool = True,
) -> tuple[set[int], bool]:
    """Manage profitable positions as part of the signal-processing cycle.

    A same-direction signal leaves an existing position untouched.  An
    opposite signal closes the existing position immediately, regardless of
    whether its floating result is profitable, flat, or negative.  With no
    valid signal, the normal profit-exit rules remain in effect.
    """
    settings = config["profit_exit"]
    profit_exit_enabled = bool(settings["enabled"])
    closed_tickets = set()
    suppress_replacement = False
    positions = mt5.positions_get(symbol=config["symbol"]) or ()
    if not signal_reliable:
        managed = [int(position.ticket) for position in positions
                   if int(position.magic) == int(config["magic"])]
        if managed:
            audit("position_management_paused", tickets=managed,
                  reason="OpenRouter analysis failed; preserve existing positions and broker-side SL/TP")
        return set(), False
    threshold = float(settings["minimum_profit_usd"])
    for position in positions:
        if int(position.magic) != int(config["magic"]):
            continue
        position_side = "buy" if position.type == mt5.POSITION_TYPE_BUY else "sell"
        opposite_signal = desired_side is not None and position_side != desired_side
        floating_profit = float(position.profit) + float(position.swap)
        transition_same_direction_exit = (
            desired_side is not None and position_side == desired_side
            and str((analysis or {}).get("market_regime", "")) == "transition"
            and floating_profit > 0.0
        )
        same_direction_cut = False
        cut_loss_metrics = None
        if desired_side is not None and position_side == desired_side and floating_profit < 0.0:
            cut_loss_metrics = evaluate_same_direction_cut_loss(position, analysis)
            same_direction_cut = cut_loss_metrics["status"] == 3
            audit("same_direction_cut_loss_evaluation", ticket=position.ticket,
                  position_side=position_side, signal_side=desired_side,
                  **cut_loss_metrics)
        # Opposite-direction reversal is an explicit risk/position rule and
        # must not be gated by profit_exit settings or minimum profit.
        if (not opposite_signal and not same_direction_cut and not transition_same_direction_exit
                and (not profit_exit_enabled or floating_profit <= threshold)):
            continue
        no_signal = desired_side is None
        tp_progress = 0.0
        if no_signal and float(position.tp) > 0.0:
            tick_for_progress = mt5.symbol_info_tick(position.symbol)
            if tick_for_progress is not None:
                if position_side == "buy":
                    target_distance = float(position.tp) - float(position.price_open)
                    travelled = float(tick_for_progress.bid) - float(position.price_open)
                else:
                    target_distance = float(position.price_open) - float(position.tp)
                    travelled = float(position.price_open) - float(tick_for_progress.ask)
                if target_distance > 0.0:
                    tp_progress = max(0.0, min(1.0, travelled / target_distance))
        no_signal_tp_fraction = float(settings.get("no_signal_tp_fraction", 0.1))
        no_signal_exit = no_signal and tp_progress >= no_signal_tp_fraction
        if (not opposite_signal and not same_direction_cut
                and not transition_same_direction_exit and not no_signal_exit):
            audit("profit_exit_hold", ticket=position.ticket, position_side=position_side,
                  signal_side=desired_side,
                  tp_progress=tp_progress,
                  reason="same-direction signal" if desired_side else "profit below one-third TP")
            continue
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            audit("profit_exit_failed", ticket=position.ticket, reason="current tick unavailable")
            continue
        is_buy = position.type == mt5.POSITION_TYPE_BUY
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(position.ticket),
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "price": float(tick.bid if is_buy else tick.ask),
            "deviation": config["deviation_points"],
            "magic": config["magic"],
            "comment": "codex-profit-exit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        checked = mt5.order_check(request)
        if checked is None or checked.retcode != 0:
            audit("profit_exit_check_failed", ticket=position.ticket, profit=floating_profit,
                  result=str(checked), last_error=mt5.last_error())
            continue
        if not live or not config["live_enabled"]:
            audit("profit_exit_dry_run", ticket=position.ticket, profit=floating_profit, request=request)
            continue
        if not terminal.trade_allowed or not account.trade_allowed:
            audit("profit_exit_failed", ticket=position.ticket, profit=floating_profit,
                  reason="MT5 trading permission is disabled")
            continue
        result = mt5.order_send(request)
        done = result is not None and result.retcode in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL
        )
        exit_reason = ("opposite signal" if opposite_signal else
                       "transition same-direction profit exit" if transition_same_direction_exit else
                       "same-direction cut-loss status 3" if same_direction_cut else
                       "no signal; reached one-tenth TP")
        audit("profit_exit_result", ok=done, ticket=position.ticket, observed_profit=floating_profit,
              reason=exit_reason,
              result=None if result is None else result._asdict(), last_error=mt5.last_error())
        # Give the broker a moment to publish the closed position before the
        # same decision cycle checks whether a replacement order may be sent.
        if done and transition_same_direction_exit:
            closed_tickets.add(int(position.ticket))
            suppress_replacement = True
            time.sleep(0.25)
        elif done and (opposite_signal or same_direction_cut):
            closed_tickets.add(int(position.ticket))
            time.sleep(0.25)
    return closed_tickets, suppress_replacement


def wait_for_closed_positions(config: dict, closed_tickets: set[int], timeout: float = 3.0):
    """Wait until MT5 no longer reports positions just closed in this cycle."""
    if not closed_tickets:
        return mt5.positions_get(symbol=config["symbol"]) or ()
    deadline = time.monotonic() + timeout
    while True:
        positions = mt5.positions_get(symbol=config["symbol"]) or ()
        stale = [p for p in positions if int(p.ticket) in closed_tickets]
        if not stale:
            audit("position_close_confirmed", tickets=sorted(closed_tickets))
            return positions
        if time.monotonic() >= deadline:
            audit("position_close_pending", tickets=[int(p.ticket) for p in stale])
            return positions
        time.sleep(0.2)


def process_bar(config: dict, state: dict, live: bool) -> None:
    terminal, account, symbol = connect(config["symbol"])
    refresh_closed_trade_state(state, config)
    bootstrap_chart_metrics(state, config)
    cycle_config = apply_adaptive_gates(config, state)
    cycle_config["strategy_router"]["chart_metrics"] = state.get("adaptive", {}).get("chart_metrics", {})
    cycle_config, shadow_weights = prepare_cycle(cycle_config, state)
    if STOP_FILE.exists():
        raise RuntimeError(f"Kill switch present: {STOP_FILE}")
    analysis = analyze(cycle_config, state, account, symbol)
    shadow_cycle = update_after_analysis(
        state, analysis["technical_decision"], analysis["frames"], cycle_config
    )
    audit("adaptive_shadow_cycle", weighting=shadow_weights, shadow=shadow_cycle)
    # Position management is intentionally part of the same decision cycle:
    # analyze first, then decide whether a profitable position should be held
    # (same direction), closed (opposite direction), or exited when no trade
    # signal is available.
    closed_tickets, suppress_replacement = manage_profitable_positions(
        cycle_config, live=live, terminal=terminal, account=account,
        desired_side=analysis["side"], analysis=analysis,
        signal_reliable=analysis["dual_agents"].get("status") != "error",
    )
    positions_after_management = wait_for_closed_positions(config, closed_tickets)
    save_state(state)
    if suppress_replacement:
        audit("skip", reason="transition profit exit; replacement suppressed",
              router_decision=compact_decision(analysis["router_decision"]))
        return
    for event in analysis["router_events"]:
        event_data = {key: value for key, value in event.items() if key != "event"}
        audit(event["event"], **event_data)
    if positions_after_management:
        audit(
            "skip", reason="position already open",
            router_decision=compact_decision(analysis["router_decision"]),
        )
        return
    allowed, reason = risk_gate(cycle_config, state, account, analysis)
    compact = compact_analysis(analysis)
    if not allowed:
        audit("no_trade", reason=reason, analysis=compact)
        return
    request = build_request(cycle_config, analysis)
    checked = mt5.order_check(request)
    if checked is None or checked.retcode != 0:
        audit("order_check_failed", result=str(checked), last_error=mt5.last_error())
        return
    if not live:
        audit("dry_run_signal", request=request, analysis=compact, order_check=checked._asdict())
        return
    if not cycle_config["live_enabled"]:
        audit("blocked", reason="live_enabled is false")
        return
    if not terminal.trade_allowed or not account.trade_allowed:
        audit("blocked", reason="MT5 trading permission is disabled")
        return
    result = mt5.order_send(request)
    if result is None:
        audit("order_send_failed", last_error=mt5.last_error())
        return
    done = result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL)
    audit("order_result", ok=done, result=result._asdict(), analysis=compact)
    if done:
        state["last_trade_time"] = int(time.time())
        save_state(state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded fully automated MT5 trader")
    parser.add_argument("--live", action="store_true", help="Allow order_send when config also enables live")
    parser.add_argument("--once", action="store_true", help="Process one closed M5 bar and exit")
    args = parser.parse_args()
    lock_handle = acquire_singleton()
    try:
        config = load_config()
        audit(
            "started",
            mode="live" if args.live else "dry_run",
            live_enabled=config["live_enabled"],
            strategy_router_enabled=config["strategy_router"]["enabled"],
            strategy_router_mode=config["strategy_router"].get("mode"),
            strategy_trade_enabled=config["strategy_router"].get("trade_enabled", {}),
            openrouter={
                "enabled": config["openrouter"].get("enabled", False),
                "model": OPENROUTER_MODEL,
                "timeout_seconds": config["openrouter"].get("timeout_seconds"),
                "max_attempts": config["openrouter"].get("max_attempts"),
                "cache_seconds": config["openrouter"].get("cache_seconds"),
                "judge_min_confidence": config["openrouter"].get("judge_min_confidence"),
                "fallback_to_python": config["openrouter"].get("fallback_to_python", True),
            },
            profit_exit=config["profit_exit"],
            position_monitor_seconds=config["position_monitor_seconds"],
            pid=os.getpid(),
            trading_timezone="Asia/Bangkok",
        )
        last_bar = None
        next_bar_check = 0.0
        state = None
        while True:
            if STOP_FILE.exists():
                audit("stopped", reason="kill switch")
                return 0
            try:
                terminal, account, _ = connect(config["symbol"])
                state = load_state(account, account.equity)
                save_state(state)
                now_monotonic = time.monotonic()
                if args.once or now_monotonic >= next_bar_check:
                    next_bar_check = now_monotonic + float(config["poll_seconds"])
                    bar = latest_closed_m1_time(config["symbol"])
                    if args.once or bar != last_bar:
                        last_bar = bar
                        process_bar(config, state, live=args.live)
                if args.once:
                    return 0
                time.sleep(config["position_monitor_seconds"])
            except Exception as exc:
                audit("recoverable_error", error=str(exc), last_error=mt5.last_error())
                mt5.shutdown()
                if args.once:
                    return 1
                time.sleep(config["reconnect_seconds"])
    finally:
        mt5.shutdown()
        release_singleton(lock_handle)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        audit("stopped", reason="keyboard interrupt")
        raise SystemExit(0)
    except Exception as exc:
        audit("fatal", error=str(exc), last_error=mt5.last_error())
        raise SystemExit(1)
