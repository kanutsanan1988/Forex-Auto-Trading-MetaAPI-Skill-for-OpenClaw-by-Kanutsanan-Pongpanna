# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

"""Read-only OpenRouter connectivity and trading-signal schema check.

This script never initializes MT5 and never prepares or sends an order.
It uses the configured OpenRouter key and the project-locked model through
openrouter_agents.py.
"""

import argparse
import json
import time
from pathlib import Path

from openrouter_agents import MODEL, OpenRouterError, _call, get_signal, load_api_key


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_FILE = HERE / "auto_config.json"


def synthetic_frames() -> dict:
    """Small deterministic payload for schema testing; not live market data."""
    return {
        name: {
            "trend": "bullish",
            "rsi14": 55.0,
            "adx14": 28.0,
            "atr14": 2.0,
            "last_closed": 2500.0,
            "ema9": 2498.0,
            "ema21": 2495.0,
            "candle_direction": "bullish",
        }
        for name in ("M1", "M5", "M15", "H1")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test OpenRouter without MT5 or order execution")
    parser.add_argument(
        "--connection-only",
        action="store_true",
        help="Test one minimal API call; skip the trading-signal schema test",
    )
    args = parser.parse_args()
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    result = {
        "ok": False,
        "model": MODEL,
        "api_key_available": bool(load_api_key(config, ROOT)),
        "mt5_used": False,
        "order_sent": False,
    }
    if not result["api_key_available"]:
        result["error"] = "OpenRouter API key is not configured or could not be decrypted"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        started = time.perf_counter()
        response = _call(
            config,
            "Return a JSON object containing status set to ok.",
            {"task": "connectivity_test"},
        )
        result["connection"] = {
            "ok": True,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
            "response_is_json_object": isinstance(response, dict),
        }

        if not args.connection_only:
            started = time.perf_counter()
            signal = get_signal(config, synthetic_frames(), {})
            result["signal_schema"] = {
                "ok": True,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "side": signal["side"],
                "strategy": signal.get("strategy"),
                "confidence": signal["confidence"],
                "reason_present": bool(signal.get("reason")),
                "supporting_evidence_count": len(signal.get("supporting_evidence", [])),
                "risks_count": len(signal.get("risks", [])),
                "synthetic_data": True,
            }
        result["ok"] = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OpenRouterError, ValueError, TypeError) as exc:
        result["error"] = str(exc)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
