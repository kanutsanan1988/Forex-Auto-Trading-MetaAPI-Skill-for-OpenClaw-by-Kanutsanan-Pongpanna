#!/usr/bin/env python3
"""Guarded MetaAPI RPC adapter for the Kanatsanan trading strategy."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MetaApi = None

HERE = Path(__file__).resolve().parent
DEFAULTS = {"symbol": "XAUUSD", "volume": 0.01, "max_spread": 0.6, "max_risk_pct": 1.0,
            "min_reward_risk": 1.8, "atr_stop_multiplier": 1.2}
TIMEFRAMES = {"M1": "1m", "M5": "5m", "M15": "15m", "H1": "1h"}


def out(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def error_payload(exc: BaseException) -> dict[str, Any]:
    return {"ok": False, "error": str(exc), "type": type(exc).__name__}


class Gateway:
    def __init__(self) -> None:
        global MetaApi
        if MetaApi is None:
            try:
                from metaapi_cloud_sdk import MetaApi as _MetaApi
                MetaApi = _MetaApi
            except ImportError as exc:  # pragma: no cover - host setup dependent
                raise RuntimeError("Install dependencies first: python3 -m pip install -r requirements.txt") from exc
        self.api = MetaApi(env("METAAPI_TOKEN"))
        self.account_id = env("METAAPI_ACCOUNT_ID")
        self.account = None
        self.connection = None

    async def __aenter__(self) -> "Gateway":
        self.account = await self.api.metatrader_account_api.get_account(self.account_id)
        if self.account.state not in ("DEPLOYING", "DEPLOYED"):
            await self.account.deploy()
        await self.account.wait_connected()
        self.connection = self.account.get_rpc_connection()
        await self.connection.connect()
        await self.connection.wait_synchronized()
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self.connection is not None:
            await self.connection.close()

    async def candles(self, symbol: str, timeframe: str, limit: int = 300) -> list[dict[str, Any]]:
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        rows = await self.connection.get_historical_candles(symbol, TIMEFRAMES[timeframe], None, limit)
        return [dict(row) for row in rows]


def load_config(args: argparse.Namespace) -> dict[str, Any]:
    config = dict(DEFAULTS)
    if args.config:
        config.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if getattr(args, "symbol", None):
        config["symbol"] = args.symbol
    if getattr(args, "volume", None) is not None:
        config["volume"] = args.volume
    return config


async def command_status(g: Gateway, _args: argparse.Namespace) -> dict[str, Any]:
    info = await g.connection.get_account_information()
    return {"ok": True, "account_id": g.account_id, "account_state": g.account.state,
            "connection": "synchronized", "account": info}


async def command_snapshot(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    symbol = args.symbol
    price = await g.connection.get_symbol_price(symbol)
    spec = await g.connection.get_symbol_specification(symbol)
    return {"ok": True, "symbol": symbol, "price": price, "specification": spec}


async def command_candles(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    rows = await g.candles(args.symbol, args.timeframe, args.limit)
    return {"ok": True, "symbol": args.symbol, "timeframe": args.timeframe,
            "closed_candles": rows, "note": "The newest returned candle may be forming; analysis drops it."}


async def command_read(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    method = {"positions": "get_positions", "orders": "get_orders"}[args.command]
    return {"ok": True, args.command: await getattr(g.connection, method)()}


async def command_history(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    return {"ok": True, "days": args.days,
            "orders": await g.connection.get_history_orders_by_time_range(start, end),
            "deals": await g.connection.get_deals_by_time_range(start, end)}


async def build_analysis(g: Gateway, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    from strategy_engine import decide_market, summarize_rows
    frames: dict[str, dict[str, Any]] = {}
    for tf in ("M1", "M5", "M15", "H1"):
        rows = await g.candles(config["symbol"], tf, 320)
        if len(rows) < 201:
            raise RuntimeError(f"Insufficient candles for {tf}: received {len(rows)}")
        frames[tf] = summarize_rows(rows[:-1])
    decision = decide_market(frames, config)
    price = await g.connection.get_symbol_price(config["symbol"])
    info = await g.connection.get_account_information()
    ask, bid = float(price["ask"]), float(price["bid"])
    entry = ask if decision.get("side") == "buy" else bid
    spread = ask - bid
    stop_distance = decision.get("stop_distance")
    stop = None if not decision.get("side") else entry - stop_distance if decision["side"] == "buy" else entry + stop_distance
    tp = None if stop is None else entry + abs(entry - stop) * decision["reward_risk"] if decision["side"] == "buy" else entry - abs(entry - stop) * decision["reward_risk"]
    return {"ok": True, "symbol": config["symbol"], "bid": bid, "ask": ask, "spread": spread,
            "equity": info.get("equity"), "decision": decision, "entry": entry, "stop_loss": stop,
            "take_profit": tp, "risk_checks": {"spread_ok": spread <= float(config["max_spread"]),
            "signal_present": decision.get("side") in ("buy", "sell"), "max_spread": config["max_spread"]},
            "frames": frames, "note": "Read-only closed-candle analysis; no order was sent."}


async def command_analyze(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    return await build_analysis(g, args, load_config(args))


async def command_trade(g: Gateway, args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args)
    plan = await build_analysis(g, args, config)
    if not plan["risk_checks"]["spread_ok"] or not plan["risk_checks"]["signal_present"]:
        plan["execution"] = "skipped"
        return plan
    if not args.live or not args.confirm_live:
        plan["execution"] = "dry_run"
        plan["note"] = "No order was sent. Add --live --confirm-live only after explicit user confirmation."
        return plan
    positions = await g.connection.get_positions()
    if any(p.get("symbol") == config["symbol"] for p in positions):
        plan["execution"] = "skipped_existing_position"
        return plan
    info = await g.connection.get_account_information()
    if not info.get("tradeAllowed", True):
        raise RuntimeError("MetaAPI account does not allow trading")
    options = {"comment": "kanatsanan-metaapi", "clientId": "kanatsanan-metaapi-v1"}
    if plan["decision"]["side"] == "buy":
        result = await g.connection.create_market_buy_order(config["symbol"], config["volume"], plan["stop_loss"], plan["take_profit"], options)
    else:
        result = await g.connection.create_market_sell_order(config["symbol"], config["volume"], plan["stop_loss"], plan["take_profit"], options)
    plan["execution"] = "sent"
    plan["result"] = result
    return plan


async def command_loop(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args)
    cycles = 1 if args.once else args.cycles
    results = []
    for index in range(cycles):
        async with Gateway() as g:
            results.append(await command_trade(g, args))
        if index + 1 < cycles:
            await asyncio.sleep(args.interval)
    return {"ok": True, "cycles": results}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Kanatsanan guarded MetaAPI RPC trading adapter")
    p.add_argument("command", choices=["status", "snapshot", "candles", "analyze", "positions", "orders", "history", "trade", "once", "loop"])
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--timeframe", choices=list(TIMEFRAMES), default="M5")
    p.add_argument("--limit", type=int, default=300)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--volume", type=float)
    p.add_argument("--config")
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--cycles", type=int, default=1)
    p.add_argument("--live", action="store_true")
    p.add_argument("--confirm-live", action="store_true")
    return p


async def main(args: argparse.Namespace) -> dict[str, Any]:
    if args.command in ("loop", "once"):
        args.once = args.command == "once"
        return await command_loop(args)
    async with Gateway() as g:
        if args.command == "status": return await command_status(g, args)
        if args.command == "snapshot": return await command_snapshot(g, args)
        if args.command == "candles": return await command_candles(g, args)
        if args.command == "analyze": return await command_analyze(g, args)
        if args.command in ("positions", "orders"): return await command_read(g, args)
        if args.command == "history": return await command_history(g, args)
        return await command_trade(g, args)


if __name__ == "__main__":
    try:
        out(asyncio.run(main(parser().parse_args())))
    except Exception as exc:
        out(error_payload(exc))
        raise SystemExit(1)
